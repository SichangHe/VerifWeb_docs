# vlm46_amfollow: model corrected against the code; fix still not live under per-message fairness
(authored by agents unless marked 🧑)

File: `proto_fix_live4.rs` (from `proto_fix_live3.rs`). Verification: `verification results:: 111 verified, 0 errors` (~1 min). `grep -c "assume\|admit\|external_body"` gives 0.
Rerun: `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus --crate-type lib proto_fix_live4.rs`
Source compared against: automerge 0.10.0 `src/sync.rs`, `src/sync/bloom.rs`, `src/sync/state.rs`, `src/sync/message_builder.rs` (unpacked in `vlm43_amloop/crate_src`). Not re-checked: that 0.10.0 equals main 40063d6.

## What changed in the model (facts, read off the code)
1. Bloom (`bloom.rs`): `contains_hash` returns false if `num_entries == 0`, and `from_hashes` gives `num_entries` = number of hashes = |doc minus closure(shared_heads)| (`make_bloom_filter`). New `bloom_ok` in the Gen guard: filter ⊇ H, and H empty implies filter empty (no false positive); H nonempty allows a false positive on anything.
2. `Msg.sync_reset` flag; `Peer.caps` (their_capabilities is Some after any receive). Recv clears `sent_hashes` on `SYNC_RESET`. Gen sets the flag when `needs_reset`, and the old-peer fallback (heads = []) is now forced by `fake == !caps` instead of free.
3. `Message::reset` carries `have = [Have::default()]` (was an empty have list). That makes the receiver send its whole doc, as in the code.
4. Send side: if `their_heads == Some([])` (`send_doc`) or the send set is more than 1/3 of the doc (integer division), the message carries the whole doc and ignores `sent_hashes` (`chg`). If a needed hash is not in the doc, `get_changes_by_hashes(..).ok()?` returns None (`bad`). New invariant `ninv` proves this never happens in reachable worlds (need ⊆ holder's doc).
5. `SetReset` now resets the whole State as `set_read_only(true)` then `(false)` does (keeps only capabilities).
Proof edits only where forced: round existence picks the exact filter H and `fake = !caps`; `lemma_window` got `rlimit(60)`.

## Not modeled (still differ from the code; fact)
read-only mode (`read_only`, `peer_read_only`, `READ_ONLY` flag), message versions V1/V2 as such, more than one `Have` per message, Have `last_sync` hashes not in the doc (code would panic via `expect`), `sent_hashes` as BTreeSet vs set (same), actual hash-based false-positive pattern (model: any superset), bloom parse quirk (`get_bit` out of range counts as set). `State::new()` has `their_have = None`, model init has `Some([])`; behaviour is the same until the first receive (their_need is None either way).

## Outcome per theorem (all re-verified, same statements)
- `theorem_safety`, `theorem_inv_reachable`, `theorem_sinv_reachable`: hold.
- `theorem_liveness`, `theorem_stays_equal`, `theorem_liveness_reachable` (fair-lossy rounds): hold.
- `theorem_gliveness`, `theorem_gstays_equal` (general runs, infinitely often 4 clean rounds): hold.
- `theorem_no_liveness_under_message_fairness`: the old counterexample (n = 1) is invalid (it needed a false positive from an empty filter). A new one, n = 2, is proved in the corrected model.

## New counterexample (Part 11), n = 2, no dependencies
Statement: there are a run and a start world such that the start is reachable (7 steps), every step is a legal step, no Edit, `msg_fair` and `act_fair` hold, and the docs differ at every time (A = {0,1}, B = {1}). (`msg_fair`: every message in a net at time k is received at some j >= k. `act_fair`: each peer times out and generates infinitely often. Nothing is dropped.)
Idea: B's doc is nonempty, so B's filter (built from {1}) may falsely contain 0. B's `shared_heads` is reset to {} each cycle by a stale message m0 from A (heads {}), so B's filter is rebuilt from {1} each cycle.
Prefix: A gen (m0, empty filter); B edits 1; B receives m0; B gen (mb: heads {1}, filter {0,1}, changes {1}); A receives mb; A edits 0; A gen (ma: heads {0,1}, filter {0}, no changes: A believes B holds 0 because of the filter).
Cycle (7 steps, all receives keep the message): B recv ma; B recv m0 (B forgets that A has anything); B timeout; B gen (mb again); A recv mb; A timeout; A gen (ma again). Messages ever sent: m0, ma, mb; each is received once per cycle.
Verified by an independent Python mirror of the model (`dev/py/run.py`, not part of the proof); it reproduces the same 7-step cycle.

## Inferences / what I don't know
- Not checked: whether a counterexample with n = 1 exists in the corrected model (the old one does not survive).
- The counterexample uses duplicate and stale delivery forever (`keep = true`), as before. Convergence under fairness that forbids unbounded redelivery (finitely many receives per message, or in-order, or no duplicates): I don't know. No proof, no counterexample.
- Whether the false positive on 0 (filter {0,1} for a set {1}, 7 probes, 10 bits per entry) can occur with real hashes: the model allows any false positive; real filters have ~1% rate per hash and the hashes are chosen by the content, so an adversarial/lucky pair of changes is plausible but unchecked. Also unchecked: that real code reaches the cycle's `their_heads == []` state from a stale message (needs a replayed or reordered old message from A).
- No positive theorem under per-message fairness.
