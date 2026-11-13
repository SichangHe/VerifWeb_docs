# vlm43_amlive: liveness of Automerge sync, and a timeout fix
(authored by agents)

Short answer: (1) the no-loss liveness claim is false, in the model and on the real crate: with no message lost or duplicated, one reordering plus one Bloom false positive leaves two peers silent forever with different documents. (2) A two-line fix, `on_timeout` = clear `sent_hashes` and set `in_flight = false`, is proved in Verus to keep safety and to make the documents converge under a fair-lossy round scheduler. (3) The fix is written as a patch to a copy of the real code; on the published crate it repairs every stuck case I tested, and each of its two lines is needed.

This continues `../vlm42_amproto/REPORT.md`. An earlier agent produced the proofs and the patch; I re-ran both Verus files today and added the real-crate runs in `noloss_crate/`.

## 1. No-loss liveness is false

Fact (Verus, `live_noloss/proto.rs`, `theorem_noloss_stuck`; re-run: `67 verified, 0 errors`, no assume/admit/external_body): a world W13 is reached in 13 steps with no drop and no duplicate; both channels are empty; both peers generate nothing; the documents differ; every later run of protocol steps stays in W13. So no fairness assumption helps: nothing is enabled.

Fact (real crate, `noloss_crate/`, my own Cargo project on published `automerge =0.10.0`, output in `noloss_crate/run_output.txt`): the same 13 steps reproduce the stuck state.

    13 ... B heads==[c0]: true  B has c1: false  B has c2: false
       round 0: A sends None | B sends None
       after rounds: heads equal=false  nobody ever sent=true

How it happens (changes c0 <- c1 <- c2; A and B are the peers):
- B's Bloom filter, built from {c0}, also answers "yes" for c1 (false positive). The harness found such a c1 after 221 candidate edits in one run and 49 in the other, so about 1 edit in 100 qualifies for a one-entry filter.
- A therefore sends c2 without c1. B queues c2.
- An older A message with heads {c0}, sent before but delivered after, overwrites B's `their_heads`. B now sees its own heads equal to the peer's and nothing to send, so `generate_sync_message` returns `None` (`sync.rs` 0.10.0, `if (heads_equal || sync_state.read_only) && message_builder.is_empty() { return None; }`). A is `in_flight` and also returns `None`.

Limits of this result:
- Fact: the documented contract is a reliable in-order stream (alexjg, https://github.com/automerge/automerge/issues/1284: "The sync protocol requires a reliable in-order stream, I.e. you need to reset the sync state if there could have been a dropped message."). The trace needs reordering, so it does not violate that contract. It refutes the vlm42 inference that reordering is harmless.
- Fact: the trace also needs B not to call `generate_sync_message` between the two deliveries.
- Not proved: a positive theorem. Whether the protocol is live under in-order delivery with false positives, or under reordering with exact filters, I don't know. Bounded exploration found no failure, but that explorer only allows false positives on changes present at the start (`live_noloss/NOTES.md`).

## 2. The fix and its proof

Fix: `on_timeout(state)` clears `sent_hashes` and sets `in_flight = false`. The application calls it when a reply is overdue, then generates again.

Facts (Verus, `fix/proto_fix_live.rs`; re-run: `63 verified, 0 errors`, no assume/admit/external_body). The model is the vlm42 model plus a `Timeout` step.
- Safety kept (`theorem_safety`): if both peers report in sync, their documents are equal, with reorder, duplicate, drop and timeout steps allowed.
- Liveness (`theorem_liveness`, `theorem_liveness_reachable`, `theorem_stays_equal`): from any reachable world, in any infinite run of rounds that has 4 consecutive loss-free rounds infinitely often, the documents become equal and stay equal. A round is: both peers time out, both generate, each message is dropped or received.
- Not vacuous (`lemma_round_exists`): a loss-free round exists from every such world.

Facts (real crate, `noloss_crate/run_output.txt`, `crate_check/`, and independently `../vlm43_amloop/REPORT.md`):
- The fix also recovers the no-loss stuck state of section 1: "converged in round 2".
- Both lines are needed. Clearing only `sent_hashes` does not fix "drop both round 0"; clearing only `in_flight` does not fix "drop A->B round 1"; "drop both round 1" needs both. With both, all four loss patterns converge at round 2. Without the fix, three of the four never converge in 40 rounds.

This is evidence of minimality among subsets of these two fields only. I did not examine other small fixes (re-send on repeated `need`, sequence numbers as ept suggested in issue #772).

## 3. Patch to the real code

`fix/sync.rs.patch` adds `State::on_timeout` to `sync/state.rs` and a paragraph to the module docs of `sync.rs` (`*.orig`, `*.new` are the copies; the patch equals their diff).

- Fact (Verus, `EState::on_timeout` in `proto_fix_live.rs`): the body `sent_hashes.clear(); in_flight = false` equals the model's `Timeout` step under the abstraction, and changes no other field. `EState` uses `u64` and `Vec` in place of `ChangeHash` and `BTreeSet`.
- Fact: both fields are already public, so callers can apply the fix today without the patch; my crate runs do exactly that.
- Not done: the patched crate was not compiled (the clone is untrusted and nothing from it was built). The clone is 0.12.0, the runs used 0.10.0; that 0.12.0 behaves the same is an inference from reading the code.

## What the proof does not cover

- Fairness is stronger than the usual per-message one: lock-step rounds, 4 loss-free in a row, infinitely often. Per-message fair loss is unproved.
- Liveness runs have no reordering or duplication inside them (safety does). Section 1 shows reordering matters without the fix; with the fix under reordering I have one real-crate run, no proof.
- Timeout fires every round, so peers keep sending after convergence. The theorem says documents converge, not that the protocol goes quiet.
- The model is transcribed by hand from `sync.rs`; there is no refinement proof to the real `generate_sync_message` / `receive_sync_message`. The whole-document (v2) message path and read-only flags are not modelled. The two real-crate reproductions are the only check that model and code agree on these traces.
- Edits happen before the liveness run starts.

More detail: `live_noloss/NOTES.md`, `fix/NOTES.md`.

## Opinion

The no-loss stuck state on the real crate is the most reportable item: issues #772 and #1284 are about loss, and this one needs none. I did not search the issue tracker for an existing reordering report. Whether the maintainers would call it a bug is their call, since reordering is outside the documented contract.

Nothing was published, filed or sent. No papers relied on.
