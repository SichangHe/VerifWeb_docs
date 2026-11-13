# vlm42_amproto: Automerge sync protocol in Verus
(authored by agents unless marked 🧑)

Short answer: safety holds and is proved. Liveness fails once a message is lost, and Verus proves this with a concrete trace. That failure is exactly the cause of the two open sync-loop issues. The real have/need code (get_hashes_to_send) is also proved correct over an abstract change DAG. What is still open is a liveness proof for the case where every message is eventually delivered.

Target: rust/automerge/src/sync.rs, commit 40063d6, the same shallow clone used in out/vlm41_tract/src/automerge. Nothing was built or run.

## 1. Protocol model (verus_proto/proto.rs: "30 verified, 0 errors", no assume/admit)

The model (facts about the file):
- There are two peers.
- A change is an int, and its deps are smaller ints. A doc is a dependency-closed set of changes.
- The network is a set of pending messages per sender:
  - any pending message may be delivered, which models reordering
  - delivery may keep the message pending, which models duplication
  - Drop removes a message
- The Bloom filter is an arbitrary superset of the true set, so false positives are allowed.
- gen and recv follow generate_sync_message and receive_sync_message field by field: sent_hashes, in_flight, have_responded, needs_reset, the queue drain, and missing_deps.
- "Reports in sync" means gen returns None through the heads_equal branch.

Proved:
- Safety (theorem_safety): in every reachable world, under any number of drops, duplicates and reorderings, if both peers report in sync then their docs are identical.
  - Why it holds: a message's heads are always the heads of a closed sub-doc, and heads determine a closed set.
- Liveness under loss is false, by two counterexamples. Each comes with a concrete Verus trace and a proof that it stays stuck forever under every later step except local edits and resets:
  - Lost change (invariant J, theorem_J_forever): A sends change 0 and the message is lost. Change 0 is now in A's sent_hashes, so A never sends it again, even though B keeps asking for it. Delivery, duplication or reordering of the remaining messages cannot help.
  - in_flight deadlock (theorem_stuck_forever): both peers have sent a message and both messages are lost. Both peers are now in_flight with nothing pending, so gen returns None on both sides forever while the docs differ.

Not proved: liveness when every message is eventually delivered (reordering and duplication allowed, no loss).
- Evidence (fact, from a bounded explicit-state check in explorer/amsync.py, results in explorer/results/): configs with reordering, duplication and false positives but no drops (e1_reliable, e1_dup, fp_reliable) have 0 deadlocks and 0 livelocks. Every config with drops has both.
- e1_fp_dup hit the state limit and gave no result.
- Inference: the no-loss case is probably live. A Verus liveness proof needs a fairness/ranking argument over the whole state machine. I estimate that at days (my guess, low confidence). It was not attempted.

## 2. have/need code (verus_havesneed/hn1.rs: "14 verified, 0 errors", no assume/admit)

get_hashes_to_send and make_bloom_filter are copied with labelled minimal changes (CHANGE G1–S5 in the file). The main changes are u64 hashes, while-loops with indices, and Vec instead of Cow/iterators. Executable logic is unchanged apart from S4 (seeding the stack at insert time) and S5 (dropping a Result that is never Err).

Proved:
- The output lies inside our doc.
- The output contains every needed hash we have.
- With empty `have`, the output is exactly need ∩ doc.
- With non-empty `have`, the output is need ∩ doc plus a set s with these properties:
  - s lies outside the closure of all last_sync
  - s contains every Bloom miss
  - s is closed under dependents
  - every member of s is a miss or depends on a member of s
- The worklist loop terminates.
- Inference: in a DAG these properties pin s down to exactly "the misses plus all their dependents".

Trusted (external_body, specified, not proved): ChangeGraph::{has_change, get_hashes, deps}, plus the Bloom interface. The Bloom interface was itself proved earlier in out/vlm41_tract/verus/bloom1.rs.

## 3. The open issues

Both issues match the lost-change counterexample (inference, from comparing their test traces with the model):
- automerge #772 (open, 2023-10-17), titled "Dropped messages in the sync protocol cause infinite loops". The issue author says "the receiver keeps asking for the changes that were in the dropped message and the sender keeps not sending them because it thinks it has already sent them".
- automerge #1284 (open, 2026-02-13), titled "Rust sync can loop infinitely if a message is lost". Collaborator alexjg replied: "The sync protocol requires a reliable in-order stream, I.e. you need to reset the sync state if there could have been a dropped message."

What the model adds beyond the issues:
- The bug is specific to loss. Safety holds even under loss.
- Reordering and duplication alone produced no failure in the bounded check.
- There is a second, quieter failure under loss: the in_flight deadlock. Here both sides go silent instead of looping.
- So the "in-order" half of the documented requirement looks unnecessary in this model (inference, bounded evidence only).

Issue texts are saved in issues/. Nothing was posted.

## Effort and blockers

- Effort: an earlier attempt wrote the model, the explorer and most of both proofs before it stopped. This session took about 1 hour of agent time, mostly two subagents closing the remaining proof obligations. I don't know the earlier attempt's time.
- Blockers:
  - The no-loss liveness proof, as above.
  - The model is hand-transcribed from sync.rs, with no refinement proof connecting it to the code. Its fidelity rests on review.
  - No papers were relied on, so nothing was added to the paper collection.

Rerun: `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus --crate-type lib FILE` (z3 per out/vlm_servo/SUMMARY.md).
