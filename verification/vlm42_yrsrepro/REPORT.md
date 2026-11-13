# vlm42_yrsrepro: independent check of the Yrs duplicate-client crash
(authored by agents unless marked 🧑)

Verdict (fact): confirmed against the published crate. yrs = "=0.28.1" (latest on crates.io, 2026-11-10) panics on a 12-byte V1 update from a peer.

Program: repro/ (own Cargo project, written from scratch; no code from out/vlm42_yrs run).
- doc = Doc::with_client_id(1)
- u1 = [1,1,7,0,0,31,0]: valid; client 7, one GC block clock 0 len 31. After apply, state vector {7: 31}
- u2 = [2, 1,7,0,0,1, 1,7,50,0,1, 0]: client 7 listed twice, GC at clock 0 len 1 and GC at clock 50 len 1
- Update::decode_v1(u2) returns Ok; transact_mut().apply_update(..) panics:
  "thread 'main' panicked at .../yrs-0.28.1/src/update.rs:155:13: internal error: entered unreachable code" (exit 101)
- rerun: cd repro && cargo run

Source (0.28.1 and current main e0b476b0ce613453c70d0bb477b955808aa79a07 both have unreachable!() at update.rs:155)
- https://github.com/y-crdt/y-crdt/blob/e0b476b0ce613453c70d0bb477b955808aa79a07/yrs/src/update.rs#L131-L156 (find_index; binary search falls through to `unreachable!()` when no block covers `clock`)
- https://github.com/y-crdt/y-crdt/blob/e0b476b0ce613453c70d0bb477b955808aa79a07/yrs/src/update.rs#L837-L862 (Update::decode; groups entries via `.entry(client)` with no duplicate/contiguity check)
- I did not re-verify the earlier report's call path through transaction.rs; the panic location alone matches it

Existing reports (gh search "unreachable", "find_index", "duplicate client" in y-crdt/y-crdt and y-crdt/pycrdt): no report of this trigger found.
- related, generic: y-crdt#415 "use errors instead of panic" (open): "This often results in crashes of the processes on our production machines because we accept dynamic documents from users, which might contain malformed data."
- y-crdt#349 "`RuntimeError: unreachable` in applyUpdateV2" (open, ywasm 0.16.10, benchmark) — panic site not identified there; unknown if same

pycrdt (code reasoning only, not run)
- pycrdt Cargo.toml: `yrs = { version = "0.28.1", features = ["sync"] }`, `pyo3 = "0.30.1"`, no panic=abort profile seen
- src/doc.rs apply_update calls `Update::decode_v1` then `t.apply_update(u)`; the panic is not caught in Rust
- inference: pyo3 turns it into pyo3_runtime.PanicException, a BaseException subclass, so `except Exception` handlers will not catch it; a server loop may die unless it catches BaseException. Document/transaction state after the panic: unknown

Nothing filed or sent upstream.
