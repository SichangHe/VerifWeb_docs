# Current Hyper and Pingora master: cancellation checks
(authored by agents unless marked 🧑)

Earlier checks ([HYPER.md](HYPER.md), [CONDITIONAL_CHECK.md](CONDITIONAL_CHECK.md), [UNWIND.md](UNWIND.md)) covered bug-fix commits only. This file reruns them on current master, 2026-11-19 UTC. Prior work and claim limits: [REPORT.md, Claims and prior work](REPORT.md#claims-and-prior-work).

Hyper master `21da6a59` (2026-11-17), HTTP/2 client cancel hand-off
- result: holds under the trust of [HYPER.md](HYPER.md); no counterexample on normal paths
  - Hyper's #4040 regression `conn::h2_pipe_task_cancelled_on_response_future_drop`: `test result: ok. 1 passed`
  - F1–F5 MIR facts all `True`; Verus `9 verified, 0 errors` on the master transition system
  - `hyper_mir_test.py` on master MIR: all 4 checker-input mutations rejected
- the old checker no longer applied unchanged; code changed, not the property
  - 121 commits since `5b17a69`; `ResponseFutMap` gained field `is_head` before `cancel_tx`, `FutCtx` gained `is_head`, and the `PipeMap` closure moved to line 489
  - the old checker hard-coded field indices (4, 3) and the closure's source location, so on master it reported `cancel_sends`, `pipe_resets_on_cancel` and `pipe_holds_stream` as failed: a checker artefact, not a bug
  - fix: [hyper_mir.py](hyper_mir.py) now reads each field index from the `Projection { … }` literal that pin-project-lite's `project` builds (MIR prints fields in index order), the `FutCtx` index from its unique literal, and the closure location from the `Option::map` call
  - the refactored checker reproduces the old results on rebuilt `5b17a69` (all facts true, `9 verified, 0 errors`) and parent `7211ec25` (facts false, `8 verified, 1 errors`)
- other master changes read in source, not checked: `PipeToSendStream::poll` now polls `poll_reset` first and buffers one chunk; `ClientTask::poll` waits for `req_rx.poll_close`. Neither touches `cancel_tx`/`cancel_rx`; `grep cancel_tx\|cancel_rx src/` finds the same sites as at `5b17a69`
- tracing-unwind gap: still exists on master
  - `SendWhen::poll` (`src/client/dispatch.rs:370`) still runs `trace!("send_when canceled")` before `this.when.as_mut().cancel()`
  - the unchanged [harness](real_hyper/h2_unwind_gap.rs) on master: `test result: ok. 2 passed` (control gets RST_STREAM; with the panicking subscriber the panic is observed and no RST_STREAM arrives within 2 s)
  - `hyper_unwind.py` on master MIR (no `tracing`): same 5 library unwind points as before; `U3` (sender dropped unsent never reaches `send_reset`) still `True`

Pingora master `3f87e92` (2026-11-09), cache lock in `RTCache::get`
- result: counterexample; the bug fixed by PR #1037 is present on master
  - PR #1037 is still open (`gh pr view`: `"state":"OPEN"`, `"mergedAt":null`); `pingora-memory-cache/src/read_through.rs` on master is byte-identical to the buggy parent `4487f7b`; the only crate change since is a test in `lib.rs`
  - reproduced by a running test: the PR's regression ([patch](real_pingora/base-regression.patch), test only) on master prints `RTCache::get() is stuck: stale CacheLock left in lockers after writer cancellation` and `test result: FAILED. 0 passed; 1 failed`, exit 101
- the old checkers apply unchanged (impl index in dump names moved from `{impl#3}` to `{impl#2}`; nothing else) and reject master as they rejected the parent
  - `check_pingora.py`: `ownership translation rejected: saved field lacks matching typed compiler identity` (no guard exists), exit 1
  - `unwind_mir.py --assume all`: resume `13 violating` exits, drop `3 violating`, including `return in P after normal path` (cancellation leak) and unwinds out of `CB::lookup`'s `poll`, `T::clone`, `force_put`; Verus `6 verified, 2 errors`
- no "holds" result exists for any shipped Pingora code; the earlier positive result is for the unmerged PR head `b2aeef4`

trusted (unchanged from the earlier docs)
- Hyper: rustc MIR faithful; regex parser; pin-project field order (now derived, still parser-trusted); futures-channel oneshot and h2 `send_reset`/last-reference semantics; hand-reviewed Verus abstraction; exclusivity of channel ends by source search
- Pingora: the counterexample needs no trust beyond the test's 5 s timeout meaning "stuck"; the checker rejections inherit [UNWIND.md](UNWIND.md) trust

what is new compared with prior work
- Hyper: first check of this hand-off on current master (prior work: h2 fuzz targets, none for client dispatch; our own `5b17a69` check). Still a compiler-derived check with trusted extraction, normal paths only, not liveness, not a refinement proof
- Hyper: the tracing-unwind loss of RST_STREAM is shown to persist on master by a running test
- Pingora: the cancellation leak exists in current Pingora master, shown by a running test; we found no prior report other than PR #1037 itself, which states the bug. Nothing was filed or published upstream

run (from the repository root; delete each SCRATCH afterwards)
- `bash verification/async_cancel/real_hyper/master.sh SCRATCH END`: regression, `SCRATCH/hyper-master.mir`, unwind-gap harness
  - `python3 -m verification.async_cancel.hyper_obligations SCRATCH/hyper-master.mir VERUS` exits 0; `hyper_mir_test` and `hyper_unwind` take the same MIR
- `bash verification/async_cancel/real_pingora/master.sh SCRATCH END`: MIR dumps in `SCRATCH/master/`, regression log in `SCRATCH/test.log`
  - `unwind_mir RESUME DROP SCRATCH/master/crate.mir VERUS --assume all` and `check_pingora RESUME DROP CRATE VERUS` both exit 1
- executed with rustc 1.100.0, Verus 0.2026.11.02.8bf68ee, Z3 4.16.0 (`VERUS_Z3_PATH`), `RUST_MIN_STACK=67108864` for `unwind_mir`
