# Automerge sync: a timeout fix, proved live under fair-lossy rounds

(authored by agents)

Why: vlm42 showed that after a lost message the protocol can be stuck forever (automerge #772, #1284). This directory has the smallest fix I found, a Verus proof that the fixed model converges under a fair-lossy scheduler without losing safety, and a patch to the real code.

## The fix

`on_timeout(state)`: set `sent_hashes = {}` and `in_flight = false`. The application calls it when a reply is overdue, then calls `generate_sync_message` again. Nothing else changes.

Why these two fields (facts from the vlm42 counterexamples): a lost change stays in `sent_hashes`, so the sender never resends it; two lost messages leave both sides `in_flight`, so both stay silent. Each field causes one of the two stuck states.

## Files

- `proto_fix_live.rs`: Verus, `63 verified, 0 errors`, no assume/admit/external_body.
- `sync.rs.patch`: patch for `rust/automerge/src/sync.rs` (docs only) and `sync/state.rs` (new `State::on_timeout`). Applies cleanly (`patch -p1 --dry-run`). The method lives in `state.rs` because `State` is defined there. `*.orig` and `*.new` are the copies the patch was made from.
- `../crate_check/`: my own Cargo project against published `automerge =0.10.0` (not the clone).
- `v.sh`: runs Verus.

## What is proved (facts, in proto_fix_live.rs)

The model is vlm42's `proto.rs` plus a `Timeout{who}` step (`tmo`: clears the two fields).

1. Safety is kept (`theorem_safety`): if both peers report in sync, their docs are equal. Reorder, duplicate, drop and timeout steps are all allowed.
2. Extra invariant `sinv` holds in every reachable world (`theorem_sinv_reachable`). It adds, per peer: queued changes are not yet applicable, lie in the other doc, and are in range; `shared_heads` and received `last_sync` lie in the right doc; sent messages carry only changes of the sender's doc.
3. Liveness (`theorem_liveness`, `theorem_liveness_reachable`, `theorem_stays_equal`). A round is Timeout A, Timeout B, Gen A, Gen B, then each message is dropped or received (`rvalid`, `lemma_round_is_model_steps`: every round is a sequence of model steps). A run is any infinite sequence of valid rounds from a world satisfying `sinv`. Fair-lossy is `fair_lossy`: for every m there are 4 consecutive loss-free rounds at some k >= m. Then the docs become identical and stay identical.
   - Measure `phi` = sizes of (docB minus docA), (docA minus docB), and of the parts of those not yet even queued. It never increases (`lemma_rel_step`), and 4 loss-free rounds with unequal docs decrease it (`lemma_window`). Round 1 consumes a pending reset flag; round 2 sends true heads; round 3 sends a `need`; round 4 sends the needed change.
   - Not vacuous: `lemma_round_exists` shows a loss-free valid round exists from every `sinv` world (a drain always exists, `lemma_drain_exists`).
   - Worlds stuck in vlm42 (lost change, `in_flight` deadlock) are reachable in this model, so they are covered.
4. Code level (`EState::on_timeout`): the body `sent_hashes.clear(); in_flight = false` satisfies `abs(new) == tmo(abs(old))` for the model's abstraction, and leaves every other field unchanged. `EState` uses `u64` and `Vec` in place of `ChangeHash` and `BTreeSet`; `doc` and `queue` live in the Automerge doc, not `State`, so `abs` takes them as arguments.

## Crate-level check (facts, published automerge 0.10.0, release build)

Two docs, one put each, lock-step rounds, 40 rounds, dropping the listed messages. Without timeout:

    drop A->B round 1, no timeout      converged_at=None messages_sent=42 heads_equal_at_end=false
    drop both round 0, no timeout      converged_at=None messages_sent=2  heads_equal_at_end=false
    drop both round 1, no timeout      converged_at=None messages_sent=4  heads_equal_at_end=false

The 42-message case is the #772 loop; the 2- and 4-message cases are the `in_flight` deadlock. With `sent_hashes.clear(); in_flight = false` before each round, every case converged (`converged_at=Some(2)`, or `Some(3)` for two lossy rounds, 8 to 10 messages).

## Limits (read before relying on this)

- The fairness assumption is stronger than "a message resent infinitely often is delivered infinitely often". Mine is lock-step rounds with 4 consecutive loss-free rounds infinitely often. It follows with probability 1 from independent loss below 1, but not from the per-message definition. I did not prove the per-message version. A bloom filter can vary per resend, so per-message fairness may need a deterministic filter plus a stabilisation argument.
- Within a run there is no reordering or duplication: each round starts with an empty effective channel. Safety covers reordering and duplication; liveness with them is unproved (inference: the old bounded check found no failure without loss).
- The scheduler calls Timeout every round. With the fix the peers still keep sending after convergence, because the peer that never hears a reply times out and resends. Liveness here means "docs converge", not "the protocol goes quiet". Inference: quiet cannot be guaranteed under loss (two generals); I did not prove that.
- The model's `Edit` guard now also requires that no queued change depends on the new local change. Justification (assumption): a fresh local change has a new hash, so no earlier received change can depend on it. Needed so queued changes stay unapplicable.
- Edits and `SetReset` are finite and happen before the run starts (the theorem starts from any reachable world). `needs_reset`, which `SetReset` sets, may still be pending at the start and is handled in round 1.
- Minimality is not proved: my proof uses both fields, and I did not show that either alone, or a smaller change (for example resend on repeated `need`), fails or works.
- The model is still hand-transcribed from `sync.rs`; there is no refinement proof from the real `generate_sync_message` and `receive_sync_message`. The v2 whole-document path, read-only flags and the sync-reset flag are not modelled.
- The patch was not compiled (the clone is untrusted, nothing from it was built). The crate check used published 0.10.0, while the clone is 0.12.0; that 0.12.0 behaves the same is an inference from the unchanged field and `generate_sync_message` logic I read, not tested. `on_timeout` touches only fields that are already `pub` in both, so the same effect is available today without the patch.
- Cost (inference): each timeout makes the sender resend changes the peer may already have.

Nothing was published, filed or sent upstream.
