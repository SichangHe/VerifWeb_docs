# Proof maintenance across upstream commits
(authored by agents unless marked 🧑)

A real Smallbitvec overflow fix required **zero proof repair** because the existing proof excluded the affected inputs. A Cranelift bitset control also needed zero repair: its source had not changed. These two small experiments demonstrate a coverage problem for proof-maintenance benchmarks, not evidence that repairs are generally cheap.

## Smallbitvec: changed behavior outside the proof's bounds

Starting artifact: [`../vlm4_sbvfix/sbv_full.rs`](../vlm4_sbvfix/sbv_full.rs), the corrected pointer-spec version of the Smallbitvec 2.5.3 model developed under `vlm_servo` and `vlm3_servo`. It is a rewritten, bounded model, not verification of the upstream crate itself.

Upstream transition: parent [`b17ba46`](https://github.com/servo/smallbitvec/commit/b17ba46bde544240dad820f98ace48314af44e2a) → [`5d195c9`](https://github.com/servo/smallbitvec/commit/5d195c909130a732a8b9520d129af36446711a6a), authored April 24, 2026. Sungjin Kim's commit message is “Fix integer overflow in buffer_len and add regression tests.” Exact source snapshots and the complete change are in [`upstream/sbv.patch`](upstream/sbv.patch).

The changed helper previously computed:

```rust
(cap + bits_per_storage() - 1) / bits_per_storage()
```

It now computes:

```rust
let bits = bits_per_storage();
cap.checked_add(bits - 1)
    .expect("capacity overflow")
    / bits
```

I replaced only that executable expression in the existing model, retaining its existing 64-bit specialization. [`sbv_retarget.rs`](sbv_retarget.rs) adds two executable lines and removes one; no specifications, lemmas, trusted items, or callers changed. The helper's existing restriction is exactly `requires cap <= 64 * 1000000`. Both baseline and retarget logs report “verification results:: 96 verified, 0 errors” ([baseline](logs/sbv-baseline.log), [retarget](logs/sbv-retarget.log)). The first retarget attempt passed; two timed repetitions also passed. Final timed runs took 3.36 s and 3.35 s respectively, about 375 MiB peak RSS each. Applying the change and obtaining the first result took under one minute; annotation-repair iterations: zero.

The upstream change has observable behavior. I compiled the **unmodified complete upstream library source** at both pinned commits with `rustc -O`, then linked the same [`crate_behavior.rs`](crate_behavior.rs) against each. Calling `SmallBitVec::with_capacity(usize::MAX)` produced:

- Old: “with_capacity(usize::MAX): Ok((0, 0))” ([log](logs/crate-old.log)); the tuple is `(len, capacity)`.
- New: “capacity overflow” followed by “with_capacity(usize::MAX): Err(Any { .. })” ([log](logs/crate-new.log)); the harness catches the panic.

Thus the old release build returned an empty vector with zero capacity despite the enormous capacity request; the new build rejects it. This directly exercises the crate, without attempting a huge allocation or dereferencing an out-of-bounds element. It does not establish a memory-safety consequence.

To expose the excluded arithmetic, [`overflow_old.rs`](overflow_old.rs) removes the capacity bound from the old helper. Verus reports “error: possible arithmetic underflow/overflow” at `cap + 64`, then “verification results:: 0 verified, 1 errors” ([log](logs/overflow-old.log), 0.80 s). [`overflow_new.rs`](overflow_new.rs) proves the checked calculation for every `usize`, representing the upstream panic branch as `None`: `Some(r)` iff `cap + 63 <= usize::MAX`, with `r == (cap + 63) / 64`. It reports “verification results:: 1 verified, 0 errors” ([log](logs/overflow-new.log), 0.79 s), first attempt. This is a separate outcome model; it does not prove Rust unwinding or extend the full container proof to arbitrary capacities.

The extracted-helper experiment [`behavior.rs`](behavior.rs) also checks the boundary: in an optimized build, `usize::MAX - 62` changes from zero to a panic. With overflow checks enabled, `usize::MAX - 63` changes from a panic to the correct quotient: the old left-associated expression overflows at `cap + 64` before subtracting one. Exact outputs: [optimized](logs/runtime.log), [checked](logs/runtime-debug.log).

## Cranelift bitset: unchanged-source control

Starting artifact: [`../vlm_servo/jit_piece/bitset.rs`](../vlm_servo/jit_piece/bitset.rs), specialized to `u64`, originally based on `cranelift-bitset` 0.125.0. New target: Wasmtime [`0147096`](https://github.com/bytecodealliance/wasmtime/blob/0147096be6dbf53971f2f56f7403aa5774704ec1/cranelift/bitset/src/scalar.rs), the fetched main commit.

The entire original and new `scalar.rs` files are byte-identical (`cmp`); both SHA-256 digests are `cb85685c57691c39932d6327a98ecc1d8743efab444ef262d19bf7d892b4253d`. The existing proof, reused unchanged, reports “verification results:: 17 verified, 0 errors” ([log](logs/bitset-control.log), 1.16 s, about 320 MiB peak RSS). Source/spec/proof edits: zero. This is an unchanged-code control, not a successful repair of changed code. The existing `lo < 64` precondition still excludes `from_range(64, 64)`; this experiment does not newly test that upstream bug.

## Interpretation and limits

Fact: neither retargeting broke the retained proof. The only deliberately failing run removed a precondition; it was a coverage probe, not a naturally broken proof from an upstream update. The Smallbitvec fix lies outside the retained proof's domain, so successful verification alone cannot distinguish the old behavior from the new behavior there. Its specifications did not drift; their coverage was already incomplete.

Recommendation: pair each upstream change with a test that reaches the changed behavior, then check whether that input satisfies the old proof's preconditions. Count unchanged code, changes outside the proof's domain, and actual proof failures separately. This sample contains no actual proof-repair failure and cannot estimate repair difficulty. Boa GC and the other Servo proofs were inspected only for candidate selection; they were not retargeted. No whole-browser claim follows.

## Reproduce and effort

From the workspace root: `bash out/vlm6_repair/run.sh`. Logs and elapsed time/peak RSS are saved under `logs/`. The script records each command's exit status; the old unbounded arithmetic probe is expected to fail. It checks `free -g` available memory before every verifier/build/runtime invocation and stops below 60 GiB. Final timed run readings were at least 160 GiB. Verus: `0.2026.11.02.8bf68ee`, x86_64, Rust toolchain override `1.99.1`; the loader emits a weak `GLIBC_2.39` warning, but verification completes with the recorded exit statuses.

Measured solver times above are wall time, not agent labor. Approximate agent effort: 5 minutes through the initial report, including candidate discovery, pinned-source retrieval, adaptations, runtime experiments, and writing; review time is additional. This is one agent's small, selected experiment, not a controlled comparison. No upstream reports or contacts were made.
