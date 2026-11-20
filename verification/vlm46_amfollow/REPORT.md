# vlm46_amfollow: three follow-ups on Automerge sync liveness
(authored by agents)

Short answer: (1) the `on_timeout` patch compiles against published automerge 0.10.0 and, called through the new method, fixes all three stuck cases; without it they stay stuck. (2) The reorder + Bloom-false-positive stall with no loss was not found upstream; a different no-loss false-positive stall was reported and fixed in 2023 (#702/#703). (3) Under per-message fairness the fix is not live in the model, now corrected against current code: Verus proves a counterexample. It needs one Bloom false positive and a stale message re-delivered forever. Whether the fix is live when each message is delivered a finite number of times, or delivered in order: I don't know.

## 1. Patched crate (facts)

- `patched/automerge-0.10.0` = crates.io 0.10.0 source plus `../vlm43_amlive/fix/sync.rs.patch`. The patch applied without conflicts. Diff against 0.10.0: `on_timeout_0.10.0.patch` (only `src/sync.rs` docs and `src/sync/state.rs` change).
- `noloss/` and `loss/` are copies of the vlm43 repros, depending on the patched crate by path. The fix now calls `State::on_timeout()` instead of setting fields directly. Both build (`cargo build --release`). Outputs: `*/run_output.txt`.
- Reorder + false positive, no loss: without fix "round 0: A sends None | B sends None ... heads equal=false nobody ever sent=true"; with fix "converged in round 2".
- Lost change (#772): without fix "NOT CONVERGED after 40 rounds: 42 msgs sent, 1 dropped"; with fix "CONVERGED after 7 rounds".
- Both first messages lost: without fix "NOT CONVERGED after 40 rounds: 2 msgs sent, 2 dropped, silent for last 39 rounds"; with fix "CONVERGED after 8 rounds".
- Not done: the crate's own test suite was not run.

## 2. Upstream search (facts; GitHub search via `gh` and the arXiv paper only, no Discord/forums)

- https://github.com/automerge/automerge/pull/703 (merged 2023-08-14, fixes issue #702, "Sync Protocol Stops Working"): "the false positive in the bloom filter which Node 1 initially sent means that Node 2 thinks Node 1 already has the change it just added and so it doesn't send that change… End result, the two documents appear to be in sync but are in fact not." Trigger there: a local change while a message is in flight. No reordering, no `their_heads` overwrite.
- https://github.com/automerge/automerge/issues/489 (closed 2023-01-10), ept: "we're in a sync where we just received a batch of changes, but the odd change here or there is missing due to a Bloom filter false positive." About slow resolution, not a stall.
- arXiv 2012.00472 assumes need/response round trips recover false-positive misses; says nothing about reordering.
- Verdict: our case (stale message overwrites `their_heads`, queued c2) was not found. A related no-loss false-positive stall is known and fixed.

## 3. Weaker fairness, on a model corrected against the code (facts from `proof/proto_fix_live4.rs`, `proof/NOTES.md`)

Which code the model follows: the model header says it was transcribed from automerge main commit 40063d6 (2026-11-09). That code already has #703 (receive always clears `in_flight`; the model did too) and the July 2026 need-filtering commits. "Hand-transcribed" means no refinement proof, not an old version. A line-by-line recheck against 0.10.0's bloom.rs, sync.rs, state.rs and message_builder.rs found these differences, now fixed in the model:
- an empty Bloom filter never matches (`num_entries == 0`); the old model let it have false positives, and the earlier counterexample (`proto_fix_live3.rs`, now invalid) relied on that
- a reset message carries one default `Have`, not an empty list
- the whole document is sent, ignoring `sent_hashes`, when `their_heads == []` or the send set exceeds 1/3 of the document; a need for an absent hash makes generate return None (proved unreachable)
- capability flag and `sync_reset` flag (receiver clears `sent_hashes`); SetReset resets the whole peer state
Not modelled: read-only mode, more than one `Have` per message, V1/V2 encodings. The recheck read 0.10.0, not 40063d6 itself (inference: same for these paths).

Results (re-run by me: `111 verified, 0 errors`; no assume/admit/external_body):
- safety, the 4-clean-rounds liveness (`theorem_liveness`, `theorem_gliveness`) and stays-equal theorems all still hold with the same statements
- `theorem_no_liveness_under_message_fairness`: new counterexample with two changes. A holds {0,1}, B holds {1}; no drop, no edit in the cycle; every message is delivered again every cycle; both peers time out and generate forever; documents differ forever. B's filter, built from {1}, falsely contains 0, so A never sends 0; a stale first message from A resets B's `their_heads` to {} each cycle.
- Inference (unchecked): realistic in its false positive (about 1% per hash), unrealistic in needing one old message replayed forever.
- I don't know: liveness when each message is delivered finitely often, or in order.

Nothing was published, filed or sent. No papers relied on beyond arXiv 2012.00472 (cited in prior reports).
