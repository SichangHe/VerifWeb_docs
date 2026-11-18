# Hyper HTTP/2 cancellation hand-off check
(authored by agents unless marked 🧑)

result, 2026-11-18 UTC
- conditional safety check, buggy vs fixed: Verus proves a hand-reviewed transition system whose facts are extracted from the real compiled MIR; not a refinement proof of Hyper
  - prior work (h2 fuzzing, Lion's assumed peer signal): see [REPORT.md, Claims and prior work](REPORT.md#claims-and-prior-work); we found no prior verification of this Hyper code
  - fixed [`5b17a69`](https://github.com/hyperium/hyper/commit/5b17a69ebcf969471c1a19b25ed2cb81299d1be6): all MIR facts hold; Verus proves the hand-off obligation (`9 verified, 0 errors`)
  - parent `7211ec25`: MIR facts fail; Verus rejects (`8 verified, 1 errors`)
- Hyper's own regression `conn::h2_pipe_task_cancelled_on_response_future_drop`
  - fixed: `test result: ok. 1 passed`
  - parent + test only ([patch](real_hyper/base-regression.patch)): fails with “server should receive RST_STREAM”, `test result: FAILED`, exit 101
- eventual delivery of RST_STREAM is not proved; see open gaps

obligation proved
- 🧑 “when send_task detects that the response future was dropped, it either hands a reset obligation to a live task (pipe_task) or resets the stream itself”
- formal statement, in every reachable state of the composed system
  - once `SendWhen::poll` has taken the `poll_canceled` Ready arm,
  - if a spawned `PipeMap` still holds the request's `SendStream`,
  - then that `PipeMap` is live, its `cancel_rx` is `Some`, and its paired channel holds the sent `()`
  - and every later `PipeMap::poll` reaches `send_reset(CANCEL)` on that stream before returning
- otherwise no Hyper task holds the stream through the pipe
  - send_task then drops its own handles; the reset comes from h2's last-reference drop (trusted, below)
- holds for arbitrary interleavings and numbers of pipe polls, body completion before or after detection, and the eager-pipe/no-body/CONNECT paths (no pipe spawned)

connection to the real code
- `real_hyper/build.sh` emits whole-crate MIR from rustc 1.100.0 for both commits (`--features client,http2`, `RUSTC_BOOTSTRAP=1 --emit=mir`)
  - generic bodies, not monomorphized; same fresh lockfile for both sides
- `hyper_mir.py` checks these facts on every normal-return path of the actual functions
  - F1 `<SendWhen as Future>::poll`: the arm where `discriminant(poll_canceled result) == 0` (Ready) calls `ResponseFutMap::cancel` on `Pin::as_mut(&mut project(self).0)` before every return
  - F2 `ResponseFutMap::cancel`: `Option::take` of projection field 4 (`Option<oneshot::Sender<()>>`); its `Some` arm calls `Sender::send(tx, ())`
  - F3 `<PipeMap as Future>::poll`: every return path first maps field 3 (`Option<oneshot::Receiver<()>>`) through the closure that polls the receiver; the `Some(Ready(Ok))` arm calls `PipeToSendStream::send_reset(as_mut(field 0), CANCEL)` on every path
  - F4 `PipeToSendStream::send_reset` calls `h2::SendStream::send_reset` on its field 0 with that reason
  - F5 `ClientTask::poll_pipe`: the single `PipeMap` is built from `PipeToSendStream::new(body, FutCtx.3 SendStream)` and spawned; its `cancel_rx` and `ResponseFutMap.cancel_tx` are `Some` of opposite ends of one `oneshot::channel()` result
- `hyper_obligations.py` writes these booleans into a Verus transition system and runs Verus
  - steps: send_task detection then drop (F1, F2), pipe poll (F3, F4), nondeterministic body completion
  - Verus proves the invariant inductively and lifts it to every finite trace
  - on the parent, F1–F5 pairing facts are false; the auxiliary invariant fails at the initial state with a live stream-holding pipe and no receiver, so no step can establish the hand-off
- `hyper_mir_test.py`: four checker-input mutations (renamed cancel call, drop instead of send, `NO_ERROR` reason, receiver from another tuple) each break their fact

trusted
- rustc MIR is faithful to the compiled code; Poll/Option/Result discriminants follow declaration order
- regex MIR parser and path enumeration in `hyper_mir.py`; generic function selection by header text
- pin-project-lite projection field order equals declaration order; projection fields alias `self`
- `Option::take/as_mut/map`, `Pin::as_mut/new` have standard semantics
- futures_channel oneshot: after `send(())` with a live receiver, the receiver's poll returns `Ready(Ok(()))`; if the sender is dropped unsent, `Ready(Err)`; receiver drop makes `send` fail harmlessly
- no other code touches these fields: at the fixed commit, `grep cancel_tx\|cancel_rx src/` finds only `poll_pipe`, `cancel`, `PipeMap::poll` and the unrelated `ConnTask.cancel_tx: Option<oneshot::Sender<Infallible>>`; not machine-checked
- the Verus transition system abstracts each function to the facts above; that abstraction is reviewed by hand, not derived
- h2: `SendStream::send_reset` schedules RST_STREAM; dropping the last stream reference of an open stream schedules an implicit CANCEL reset
- the executor drops a task after it returns Ready
- unwinding/panic paths, `expect` panics, and h2 internals are out of scope here; follow-up [UNWIND.md](UNWIND.md) covers unwinding

open gaps
- eventual delivery: needs the executor to poll pipe_task after the oneshot wake, h2 connection task progress and flushing, and the peer receiving the frame; only the runtime regression covers it, empirically
- the no-pipe branch relies on h2's last-reference reset, not on Hyper code
- MIR-to-Verus abstraction and parser are unverified; this is a compiler-derived check, not a refinement proof
- exclusivity of `cancel_tx`/`cancel_rx` access is a source search, not a whole-crate MIR check

run
- `bash real_hyper/build.sh SCRATCH END` under `cpu-run` (inside the script); delete SCRATCH after
- from the repository root, with `VERUS_Z3_PATH` set to a compatible Z3 if needed
  - `uv run --no-project python -m verification.async_cancel.hyper_obligations SCRATCH/hyper-fixed.mir VERUS` exits 0
  - same with `hyper-parent.mir` exits 1
  - `uv run --no-project python -m verification.async_cancel.hyper_mir_test SCRATCH/hyper-fixed.mir` exits 0
