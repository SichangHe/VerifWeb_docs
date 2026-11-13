# vlm43_yrsproto: Yrs sync protocol in Verus
(authored by agents unless marked 🧑)

Short answer: safety holds and is proved. Liveness holds when no message is lost; this is proved for a fully connected mesh with no relay, and for a star with relay. A single lost Update leaves the receiver stuck while the connection stays up. Verus proves this with a concrete trace, and the published yrs crate reproduces it. Only a new SyncStep1 repairs it, sent on reconnect or by a periodic resync. Unlike Automerge, Yrs keeps no "already sent" state, so one SyncStep1 always repairs the loss.

Target: y-crdt commit e0b476b (src/y-crdt, a shallow clone; nothing built or run from it). Repro: my own Cargo project in repro/ that depends on yrs =0.28.1 from crates.io.

## 1. Model (verus/*.rs; all four files re-checked today, no assume/admit/external_body)
The single grep hit for "assume" in each file is the comment "the CRDT is assumed to make the visible doc a function of closed(R)". That is the abstract-merge assumption below, written as a definition, not as an assume() call.
- An op is an int, and anc(o) is its causal ancestors. A peer's received set R includes pending structs. Its visible doc is closed(R), the ops in R whose ancestors are all in R. This matches Yjs's store.pending.
- Abstract merge (assumption): the visible doc is a function of closed(R) only.
- Messages follow yrs/src/sync/protocol.rs:
  - SyncStep1(sv) gets a SyncStep2 reply carrying R minus sv. The reply includes pending data (transaction.rs:140-144: "check for pending data", merge_pending_v1).
  - SyncStep2 and Update are applied; no reply is sent.
  - On connect, both peers send SyncStep1.
- The network is a set of pending messages. Any message may be delivered (reorder) or delivered while kept pending (duplicate), and Drop removes one (loss).
- The relay variant adds this: when a peer integrates new ops, it broadcasts them to its connected peers. Assumption: y-websocket, pycrdt-websocket and AppFlowy-Cloud servers broadcast like this. I did not read their code. Fact: Yrs emits an update event only when the transaction changed state (store.rs:588-590, event.rs:14 new_v1).
- Awareness is not modelled.

Results ("N verified, 0 errors"):
- yproto.rs (16): safety, plus the loss counterexample (theorem_counterexample, theorem_stuck_forever). A edits o0 and then o1, which depends on o0. Update(o0) is dropped and Update(o1) is delivered. B now holds o1 as pending, and B's doc stays without o0 and o1 under every later step except Connect or Disconnect, including further edits, deliveries, duplicates and drops.
- yproto_live.rs (23): two theorems for a fully connected mesh with no drops. Convergence: once every pair is connected and nothing is pending, all peers hold every op. Liveness: from any drop-free reachable state, every schedule of plain deliveries ends within mu(w) steps, and some schedule empties the network, after which all docs are equal.
- yproto_relay.rs (18): with relay, the convergence theorems for neighbours and for a star, plus the loss counterexample again.
- yproto_relay_live.rs (33): liveness for a star (server 0) after any drop-free history. Delivery terminates within a bound, the network can always be drained, and then every peer shows every op.
- Safety (all files): equal received sets give equal docs. Applying updates is set union, so order and duplicates do not matter.

## 2. Bounded check (explorer/, Python explicit-state search of the relay model)
- Stuck states (states from which convergence is unreachable without drops or reconnects) are 0 in every config that has no drops, whether or not it has disconnects. The configs are 2 peers with concurrent or chained edits, and 3 peers in a star.
- The same configs with drops have stuck states (7518, 234 and 2890).
- A variant with a periodic Resync action (any peer may resend SyncStep1) has 0 stuck states with drops, but only for 2 peers with chained edits. The 2-peer concurrent config hit the state cap.
- All 3-peer mesh configs (and the 3-peer star with a dependent edit) hit the 400k state cap. The "not enough values to unpack" error in results2.jsonl is how the cap shows up, not a bug. A rerun with a larger cap was skipped because the host had 58 GiB free, below the 60 GiB floor. So mesh with relay is unchecked, and I don't know whether it is live.

## 2b. Liveness under message loss (summary)
- Without reconnect or resync, liveness fails. Verus proves it: after one dropped Update the stuck state is closed under every Edit, Deliver, duplicate and Drop (theorem_stuck_forever, both files).
- With reconnect or resync, the bounded check shows recovery for 2 peers. Reason (inference): one SyncStep1 followed by its SyncStep2 sends R minus sv, which covers every lost op. Liveness then needs a fairness assumption: some SyncStep1 and its reply eventually get through. This is not proved in Verus.
- Lost SyncStep1 or SyncStep2 at connect time: nothing resends them, so the peer never reaches synced (y-websocket #94). The model allows this, but there is no separate Verus theorem for it.

## 3. Real crate (repro/output.txt, yrs 0.28.1, DefaultProtocol)
- After Update(o0) is lost and Update(o1) is delivered twice, B's text is "", it has pending data, its state vector is empty, and it has relayed 0 updates. A's later edit "z" also stays invisible at B. Meanwhile B's own edit reaches A, so A shows "xyzB" and B shows "B". The docs diverge silently.
- A new SyncStep1 from B, answered by A's SyncStep2, fixes it: both show "xyzB".
- Side fact: a SyncStep2 from a peer whose only ops are pending still carries those ops, so they spread to the other peer (D shows "xy").

## 4. Relation to real reports (inference; issue texts in issues/)
- y-websocket #94 (closed): the issue reporter wrote "Client never reaches 'synced' state because the server never responds to the client's sync step 1 (because the server wasn't listening at the time)". This is the same class of failure: a lost sync message, and nothing in the protocol resends it. Because the lost message was SyncStep1, there is no reply and no "synced". The model predicts this (inference).
- jupyter-collaboration #219 (open): "After a break of several hours the connection is re-established ... jupyterlab does not save the changes anymore". It fits the model's loss case (a lost message around reconnect leaves the server doc without the client's ops). The issue does not show that a message was lost, so this is unconfirmed.
- AppFlowy #8455 (open): "items that I had added on my phone were missing". It is consistent with the silent divergence in section 3, but there is no trace, so this is unconfirmed. AppFlowy's sync code (I believe it is a custom layer over Yrs, unchecked) was not modelled.
- Contrast with Automerge (vlm42): Automerge stays stuck because its sent_hashes state records the dropped change as already sent, so it is never resent (vlm42). Yrs recovers on any new SyncStep1 because SyncStep1 carries only the state vector and Yrs keeps no per-peer sync state. In Yrs, safety under loss comes from the CRDT, and liveness depends on transport reliability or on a resync timer. Belief, unchecked: y-websocket has a resyncInterval option that would cover this case.

## Open
- Liveness for mesh with relay.
- A Verus proof of liveness with resync under fair loss.
- Resync liveness for more than 2 peers.
- Awareness.
- No Google Scholar search was done, and no papers were added to paper_collection.
