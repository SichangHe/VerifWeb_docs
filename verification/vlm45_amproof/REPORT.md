# vlm45_amproof: convergence of Automerge sync with the timeout fix
(authored by agents unless marked 🧑)

Short answer: no counterexample; the convergence proof holds and is now stronger. The earlier proof (`../vlm43_amlive/fix/proto_fix_live.rs`) only covered runs made of lock-step rounds. I added theorems that also allow any stale, reordered or duplicated delivery, drop, extra send or extra timeout between rounds. What remains assumed is a strong "quiet window" form of "messages stop being lost"; the usual per-message fairness is still unproved.

File: `proto_fix_live2.rs` = the vlm43 file plus Part 10. Fact: `71 verified, 0 errors` (was 63), 0 occurrences of assume/admit/external_body. Rerun: `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus --crate-type lib proto_fix_live2.rs` (about 30 s).

## What is proved (facts)

Model: two peers; changes are ints with smaller ints as deps; per-sender set of pending messages; steps Edit, Gen, Recv (optionally keeping the message = duplicate; any pending message = reorder), Drop, SetReset, Timeout. Timeout is the fix: `sent_hashes = {}`, `in_flight = false`. Bloom filters may give false positives.

A round is: Timeout A, Timeout B, Gen A, Gen B, then each of the two new messages is dropped or received. A round is loss-free if neither is dropped.

A run is an infinite sequence of blocks starting from any world reachable in the model. Each block is either a round or one arbitrary model step other than Edit.

- `theorem_gliveness` (new): if, infinitely often, 4 consecutive blocks are loss-free rounds, then at some point the two documents are identical.
- `theorem_gstays_equal` (new): once identical, they stay identical under any blocks.
- `theorem_safety` (old, re-verified): in every reachable world, if both peers report in sync, the documents are identical.
- Corollary of the first two (inference, not a separate Verus theorem): "messages stop being lost" in the sense "from some point on, every block is a loss-free round" implies convergence, whatever stale messages were delivered before.

Why the extension was cheap: the old measure (changes missing on each side, plus those not yet queued) never increases under any non-Edit step, so only the 4-round window has to be clean.

## What is assumed (facts about the theorem statements)

- No Edit during the run. Edits may happen any time before it.
- Inside each 4-round window: lock-step, both peers time out every round, both messages delivered, and no other step interleaved (so no stale or duplicate delivery inside the window).
- Such windows occur infinitely often. This follows with probability 1 from independent loss, but it is not implied by "every message sent infinitely often is delivered infinitely often".
- Edit guard: no queued change depends on the new local change (justified by hash freshness; assumption).
- The model is hand-transcribed from `sync.rs`; no refinement proof to the real code. Whole-document (v2) messages and read-only flags are not modelled.

## Not proved / I don't know

- Existence of an infinite run is not a theorem; only one-step existence is (`lemma_round_exists`, `lemma_block_exists`).
- Convergence under per-message fairness, or when stale or duplicate deliveries hit every window forever: I don't know. Inference (unchecked, low confidence): an adversary that re-delivers one old duplicate each round might block progress, since an old message can overwrite `their_heads`; real networks do not duplicate forever, so this matters for the theorem's shape more than for practice.
- The protocol going quiet after convergence: not claimed; with a timeout every round peers keep sending.
- Minimality of the fix: only the crate runs in vlm43_amlive (each field alone fails some case), no proof.

Nothing was published, filed or sent. No papers relied on. Not a git repository, so nothing committed.

Feedback: the task said "continue the proof", but the lock-step proof was already complete in vlm43_amlive; pointing at that directory would have saved the lookup.
