# vlm43: no-loss liveness of the Automerge sync model
(authored by agents)

Result: the requested proof cannot be completed, because the claim is false in the model. With no Drop, no duplicate, and every message delivered, Verus proves a world that is stuck forever with different docs. Liveness holds only under extra restrictions that I did not prove.

File: `proto.rs` = vlm42 `proto.rs` plus Part 4 at the end. Edits to the old part: `#[verifier::ext_equal]` on the four structs so that `=~~=` works (no change to any definition). Check: `verus --crate-type lib proto.rs` gives `67 verified, 0 errors`. `grep` finds no assume, admit or external_body.

## What is proved (facts, in the model)

`theorem_noloss_stuck` (Part 4) proves all of:
- `reachable_clean(d3, 3, W13, 13)`: the world W13 is reached by 13 steps using no Drop and no duplicate (every Recv has keep=false). Reordering is used once.
- `quiet`: both nets are empty (every message sent was delivered exactly once), and generate returns None on both peers for every bloom/fake argument.
- The docs differ: A has changes {0,1,2}, B has {0} and change 2 sits in B's queue waiting for change 1.
- For every k and every w2 with `runs_from(W13, k, w2)` (any run of Gen/Recv/Drop steps, no edits or resets), w2 == W13. So no schedule, fair or not, ever leaves W13.

Deps: 0 <- 1 <- 2. Trace (A=0, B=1):
1. B edits change 0.
2. A generates (empty doc), message m_a0.
3. B generates with bloom {0,1}: heads {0}, no changes (B has not heard from A). The bloom has a false positive on change 1, which B does not have and A does not yet have.
4. B receives m_a0.
5. B generates again, bloom {0,1}, sends change 0.
6. A receives that, so A has change 0.
7. A generates m_old (heads {0}, no changes).
8. A receives B's step-3 message, which clears A's in_flight and leaves A's their_have with the false-positive bloom.
9-10. A edits changes 1 and 2.
11. A generates m_new: change 1 is a bloom "hit", so only change 2 is sent.
12. B receives m_new: change 2 is queued, missing 1.
13. B receives the stale m_old (reordering). B's their_heads becomes {0}, which equals B's own heads, and B's send_set is empty, so B reports in sync and is silent. A is in_flight and silent.

Why nobody recovers: B's `need` would ask for change 1, but need is computed from their_heads, and the stale their_heads {0} no longer reaches change 2 in the queue. A believes it sent everything needed (change 2 in sent_hashes, change 1 hidden by the false positive).

## Fairness is not the issue

Every sent message is delivered. In W13 no step is enabled except Gen-returning-None, so the run is maximal: any fairness notion (weak, strong, "every pending message eventually delivered", "every enabled Gen eventually taken") is satisfied. Step 13 disables B's Gen after it had been enabled at step 12; weak fairness only constrains actions that stay enabled.

## Fidelity checks (facts from the code, inferences marked)

- Fact: in `bloom.rs`, `contains_hash` returns false when num_entries == 0, so an empty Bloom cannot have a false positive. A shorter 7-step trace on two changes exists in this model but needs a false positive on an empty filter, so I did not use it. The 13-step trace only uses false positives on non-empty filters ({0} plus the false positive 1).
- Fact: the model treats the Bloom filter as any superset of the true set. In real code the false positive on change 1 depends on its hash, so whether it occurs for a given pair of hashes is probabilistic. Inference: a real counterexample needs a hash collision pattern of this kind plus reordering of two A-to-B messages.
- Fact: the documented contract (alexjg, issue 1284) is a reliable in-order stream. The trace needs reordering, which that contract excludes. So this is not a bug against the documented contract. It does refute "reordering and duplication are harmless", the inference in vlm42 REPORT.md.
- Fact: the explorer (`../explorer/amsync.py`) only allows false positives on changes that exist in the initial state (`ufp` is built from the initial docs), not on changes created by later edits. Inference: that is why it reported 0 stuck states for the reliable configs. I re-ran bounded configs with this explorer (copies in `term.py`, `term2.py`): terminals with differing docs = 0 in all that finished, consistent with that limitation.
- Fact: with the reorder-only reliable config e1_reliable, the explorer finds 134 terminal states where docs are equal but one peer returns None through the in_flight branch instead of heads_equal. So "both peers report in sync (heads_equal)" is not even reached in all no-loss runs of that tiny config. Liveness must be stated as docs equal plus quiescence, not as report_in_sync on both sides. I did not prove that fact in Verus.

## What remains (not proved)

The positive claim "under no loss, fair delivery, every run ends with equal docs" needs a restriction that excludes the trace above. Candidates, none proved:
1. In-order delivery (FIFO per direction) with false positives allowed. Unknown if live.
2. Exact Bloom filters (no false positives) with reordering and duplication. Unknown if live; the explorer with no false positives shows no failure on small configs.
3. Finite duplication per message is also needed in any positive statement: a stale duplicate delivered infinitely often keeps resetting their_heads.
Sketch of a positive proof for (1) or (2) (inference, not tried): (a) invariant K: sent_hashes(X) is a subset of Y.doc plus Y.queue plus changes pending in net[X] (holds without Drop, preserved by every step, fails with Drop: this is the vlm42 invariant J); (b) a ranking over docs growth, then sent-but-undelivered changes, then ping-pong count; (c) a terminal-state lemma: no pending messages and both Gen None implies docs equal. Step (c) needs a history invariant for stale their_heads, which is exactly what fails in the trace under reordering. My estimate for (a)-(c) is more than a day (low confidence); I stopped because the stated claim is false.
