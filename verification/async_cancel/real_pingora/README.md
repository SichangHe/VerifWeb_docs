# Pingora cancellation regression and compiler evidence
(authored by agents unless marked 🧑)

Empirical result, 2026-11-14 UTC: the same cancellation regression fails on the
production implementation before PR #1037 and passes on the proposed fix. This
is a real-library regression, not a proof of cancel-safety.

## Source and scope

[Kev Howard's PR #1037](https://github.com/cloudflare/pingora/pull/1037), commit
`b2aeef4875823ffa75b638ba586ed491a1fc851e`, is titled
“Fix cancelled cache lookup leaving stale lock”. Its parent is
`4487f7b2ab50f159e4a2cf4f6a6b813f61bb6e19`.

The PR's `CacheLockGuard` documentation says:

> Releases a [CacheLock] it owns when dropped, including when the owning future is cancelled
> while the lookup is still pending.

Source: [read_through.rs at the tested commit](https://github.com/cloudflare/pingora/blob/b2aeef4875823ffa75b638ba586ed491a1fc851e/pingora-memory-cache/src/read_through.rs),
search `CacheLockGuard` and `test_cancelled_writer_does_not_block_later_readers`.
The latter test starts an actual `RTCache::get`, waits until its lookup is
pending, aborts and joins the Tokio task, then requires a later request for the
same key to complete within five seconds. The lookup callback is deliberately
pending; the cache, task cancellation, semaphore, and lock are real library code.

## Executed results

On the PR, the targeted regression reported:

```text
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 22 filtered out; finished in 0.00s
```

On the parent production implementation with only this regression added:

```text
RTCache::get() is stuck: stale CacheLock left in lockers after writer cancellation
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 20 filtered out; finished in 5.00s
```

Cargo exited 101. Restoring the PR and running all library unit tests reported:

```text
test result: ok. 23 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.00s
```

`base-regression.patch` contains only the upstream PR's cancellation test and
its callback, applied to the parent. It does not change production code. Test
authorship remains Kev Howard's; extraction and this report are agent work.

Toolchain: `rustc 1.99.1 (58cf8f9c3 2026-10-13)`,
`cargo 1.99.1 (5f94df478 2026-08-27)`. Dependencies included Tokio 1.54.1,
async-trait 0.1.92, parking_lot 0.12.5, once_cell 1.21.4, and the checkout's
Pingora crates at 0.9.0. Both implementations used the same generated lockfile.
The upstream checkout does not track that lockfile; a fresh resolution may differ.

## Reproduce

Run from this directory. Set `EXPECTED_END` to the expected UTC finish time.
Each `run` invocation uses two cores and a 16 GiB/512-task scope. Set the user
D-Bus environment if the session has not provided it.

```sh
artifact_dir=$PWD
scratch=$(mktemp -d)
git clone https://github.com/cloudflare/pingora.git "$scratch/pingora"
cd "$scratch/pingora"
git fetch origin pull/1037/head
git checkout --detach b2aeef4875823ffa75b638ba586ed491a1fc851e
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
export CARGO_TARGET_DIR="$scratch/target"
export CARGO_BUILD_BUILD_DIR="$scratch/build"
export CARGO_BUILD_JOBS=2
run() {
  cpu-run LOW -c 2 -o vl_async_study.md -e "$EXPECTED_END" -- \
    systemd-run --user --scope -p MemoryMax=16G -p TasksMax=512 -- "$@"
}
run cargo test -p pingora-memory-cache --lib
git checkout --detach 4487f7b2ab50f159e4a2cf4f6a6b813f61bb6e19
git apply "$artifact_dir/base-regression.patch"
run cargo test --locked -p pingora-memory-cache --lib \
  read_through::tests::test_cancelled_writer_does_not_block_later_readers -- --exact
# The preceding test must fail after its five-second timeout.
git restore pingora-memory-cache/src/read_through.rs
git checkout --detach b2aeef4875823ffa75b638ba586ed491a1fc851e
run env RUSTC_BOOTSTRAP=1 cargo rustc --locked -p pingora-memory-cache --lib -- \
  --emit=mir -Zdump-mir=coroutine -Zdump-mir-dir="$scratch/mir"
```

If `cpu-run` exits 3, the LOW budget is full; retry later. MIR extraction uses an
unstable compiler inspection flag through `RUSTC_BOOTSTRAP`; it changes neither
the source nor the regression. Keep generated build files outside this repository.

## What the actual compiler emits

The extraction command succeeded on the PR source. In the dump directory, inspect
files beginning `pingora_memory_cache.read_through-{impl#3}-get-{closure#0}`
and ending `coroutine_resume.0.mir` or `coroutine_drop.0.mir`.
MIR is Rust's compiler intermediate representation. These are the generated
resume and destruction functions for the actual generic `RTCache::get` future.

The resume function's layout includes:

```text
field _s16: Option<CacheLockGuard<'_>>;
Suspend4 (7): [_s0, _s1, _s2, _s4, _s5, _s6, _s7, _s8, _s16, _s17, _s19, _s20],
```

The writer's lookup-pending return sets the coroutine discriminant to `7`.
In that suspended state the guard occupies field `8`, and the pending lookup
future occupies field `9`. Destruction dispatches state 7 to `bb74`, then
`bb1`, then `bb2`, which drops the lookup future. Normal return proceeds through
`bb3`, `bb4`, and `bb5`, where the compiler emits:

```text
drop((((*_1) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>)) -> [return: bb6, unwind: bb44];
```

If dropping the lookup future unwinds, `bb41` leads through `bb42` to `bb43`,
which also drops the guard; a further panic terminates cleanup. The other four
suspension variants hold reader waits or reader fallback lookup futures, not this
writer guard. Dropping an unpolled future returns directly.

This compiler output directly establishes that the guard is stored across the
writer's pending lookup and scheduled for destruction when that future is dropped.
It does not establish arbitrary callback termination, semaphore correctness,
concurrent-map invariants, or correspondence to a proposed formal model. In
particular, the callback future is destroyed before the guard: if its destructor
does not return or aborts the process, guard cleanup need not complete.
