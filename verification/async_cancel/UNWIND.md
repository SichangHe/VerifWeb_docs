# Panic and unwind paths: Pingora writer lock and Hyper hand-off
(authored by agents unless marked 🧑)

result, 2026-11-18 UTC
- 🧑 “the human requires proving the real code conforms to the spec, not only a model”
- Pingora fixed (PR #1037, `b2aeef4`): the writer-lock invariant holds on every unwind path of the real compiled `RTCache::get`, except at exactly these places
  - 4 unwind edges between `lockers.insert` and guard construction: drop of the old map value, drop of the map write guard, `Option::as_ref`, the guard constructor (`Option::map` → `Arc::clone`)
  - unwinding inside `CacheLockGuard::drop` itself; which effects then ran is listed below
  - with “these calls do not unwind” as an explicit assumption, Verus accepts the extracted resume and drop graphs (`8 verified, 0 errors`)
  - user code is covered without assumptions: a panic in `CB::lookup`, the lookup future's `poll` or destructor, `T::clone`, `force_put` or error construction unwinds through a cleanup block that drops the guard
- Pingora parent (`4487f7b`, buggy): fails, as it should
  - with the same and more assumptions (every listed library call cannot unwind), a panic in `CB::lookup`, the lookup `poll`, the lookup-future drop, `T::clone`, `force_put`, error construction, or the Arc drop leaves the published lock in the map with zero permits (resume: 12 unwind exits plus the known normal-return cancellation leak; drop: 2 unwind exits plus that leak)
  - Verus rejects (`6 verified, 2 errors`)
- Hyper fixed (`5b17a69`): hand-off survives unwinding only if 5 calls between detection and `Sender::send` do not unwind (`Pin::as_mut`, `cancel`, its `project`, `Option::take`, `Sender::send`)
  - if send_task unwinds there, the unsent `cancel_tx` is dropped; the compiled `PipeMap::poll` treats `Ready(Err)` as normal completion and never reaches `send_reset` (checked in MIR); the body keeps streaming with no RST_STREAM
  - unwinding in pipe_task drops `PipeMap` and its `SendStream`; the reset then depends on h2's last-reference drop, as in the no-pipe branch of [HYPER.md](HYPER.md)
  - Python-only fact extraction; no Verus model for this part

what “the invariant on unwind” means
- obligation phases of one `get` activation
  - U: this activation has published no lock
  - P: `HashMap::insert` into `lockers` returned; no guard holds the lock
  - G: the frame's `Option<CacheLockGuard>` slot (variant 7, field 8) was assigned by the guard constructor and not yet dropped
  - X: dropping that slot unwound
  - D: discharged; fixed: the guard-slot drop returned; parent: the explicit `remove` after `add_permits` returned
- safe exits
  - `return` in U or D, or in G with the frame suspended in variant 7 (later cancellation runs the drop function, also checked)
  - `resume` (unwinding out of `poll` or out of the drop function) only in U or D
    - the compiler sets the frame to Panicked (`discriminant = 2` before `resume`) and its drop does nothing, so a guard still in the frame is never dropped
  - `unwind terminate` is a process abort (panic during cleanup); reported, not counted
- D in the fixed side means the destructor returned; its effect on the map is the existing [cleanup proof](CLEANUP_SEMANTICS.md)

method ([unwind_mir.py](unwind_mir.py))
- input: the compiler's `coroutine_resume` and `coroutine_drop` dumps and crate MIR from one build ([build_unwind.sh](real_pingora/build_unwind.sh))
- explores every normal and every cleanup edge, including `unwind continue` (exit by unwinding) and `unwind terminate` (abort)
- entries come from the compiler's discriminant dispatch; variant 7 starts in G (fixed) or P (parent), all others in U
- branch conditions are ignored, except one path-sensitive fact derived from the instructions
  - a place assigned `Option::None`, directly or through a tuple field, has discriminant 0; a switch on it takes only its 0 edge
  - this excludes the reader branch after the writer's own insertion (reader slot `None`), without trusting earlier checks
- guard-slot writes other than the constructor, or other uses of the slot, are rejected
- `--assume` removes unwind edges of named call patterns (`NO_UNWIND`); the printout lists which were used
- Verus certificate: Python proposes the reachable (block, phase, saved state) set and its edges; Verus proves closure, exit safety, and safety of every finite path by induction
  - like [DROP_OBLIGATIONS.md](DROP_OBLIGATIONS.md), Verus checks the extracted graph, not the extraction

destructor `CacheLockGuard::drop` on unwind (real MIR, fixed)
- unwinding at `Arc::deref` or `add_permits`: nothing done; lock stays in the map, no permits
- unwinding at `write`: readers notified; entry stays; later `get` callers acquire a permit and proceed (inference from source, not checked)
- unwinding at deref, `get`, `is_some_and`, `deref_mut`, `remove`: notified; write lock released by cleanup bb12; entry may stay
- unwinding while releasing the write lock: entry removed or not-owner, lock release unwound
- a second panic while cleanup bb12 releases the lock aborts

trusted, Pingora
- rustc 1.100.0 MIR (`--emit=mir`, `-Zdump-mir=coroutine`, panic=unwind) is faithful; the build uses one fresh lockfile for both sides
- with panic=abort none of these unwind paths exist; the result is for the default panic=unwind
- the parser and phase transitions in `unwind_mir.py`; pattern matching on call text
- no-unwind assumptions, all library code, inferred from source, not proved
  - `drop-lock-values`: dropping `Option<Arc<CacheLock>>` (Semaphore drop) and parking_lot `RwLockWriteGuard` (unlock) does not panic
  - `option-as-ref`: trivially
  - `guard-ctor`: `Option::map` and the closure; `Arc::clone` aborts rather than panics on overflow
  - `guard-drop`: the destructor's calls do not unwind; `add_permits` panics only past `MAX_PERMITS`; only this guard adds 10 to a lock created with 0
- the Tokio task harness catches the panic and drops the Panicked future; nothing else runs the frame's guard
- entry phase of variant 7 and the single insertion site are from the earlier [conditional check](CONDITIONAL_CHECK.md); unwind exploration rejects a second insertion

trusted, Hyper ([hyper_unwind.py](hyper_unwind.py))
- same MIR and parser trust as [HYPER.md](HYPER.md)
- the executor drops a panicked task's future; dropping `SendWhen` drops `ResponseFutMap.cancel_tx` unsent, so the receiver sees `Ready(Err(Canceled))`
- no-unwind of the 5 calls above is an inference from source (futures-channel `send` asserts its slot is empty; one `Sender` sends once)
- h2's last-reference reset on `SendStream` drop

open gaps
- no-unwind assumptions above are not proved; the assumption list is precise, but each item is a source reading
- the Pingora destructor's unwind leaves stale state; not repaired, only located
- Hyper: sender-dropped-unsent is indistinguishable from normal completion in `PipeMap::poll`, so any send_task unwind after detection and before `send` loses the reset; a robust design would reset on `Err` while the response is unfinished (proposal only; nothing filed)
- extraction and phase transitions are Python, not proved; the Verus step checks the extracted graph only
- abort paths (double panic) end the process; no in-process invariant is claimed for them

run
- `bash real_pingora/build_unwind.sh SCRATCH END` (uses `cpu-run`; delete SCRATCH afterwards)
- from the repository root, `D=SCRATCH/fixed/dump`, `R=$D/*-get-{closure#0}.*.coroutine_resume.0.mir`, `P=…coroutine_drop.0.mir`
  - `uv run --no-project python -m verification.async_cancel.unwind_mir R P SCRATCH/fixed/crate.mir VERUS --assume drop-lock-values,option-as-ref,guard-ctor,guard-drop` exits 0
  - same with `--assume none` lists the 5 places and exits 1
  - parent with `--assume all` exits 1
  - `uv run --no-project python -m verification.async_cancel.unwind_mir_test SCRATCH/fixed/dump SCRATCH/parent/dump`: 6 checks, including 3 checker-input mutations (skip resume-cleanup guard drop, skip drop-cleanup guard drop, reader slot not None); each is rejected
- Hyper: emit `hyper-fixed.mir` as in [real_hyper/build.sh](real_hyper/build.sh), then `uv run --no-project python -m verification.async_cancel.hyper_unwind hyper-fixed.mir`
- executed with Verus 0.2026.11.02 and Z3 4.16.0; Verus needs `RUST_MIN_STACK` (set by the script) for the large certificate
