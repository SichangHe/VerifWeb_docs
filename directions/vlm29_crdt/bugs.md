# Sync-protocol bugs in CRDT libraries (2022-2026)
(authored by agents unless marked 🧑)
Source: `gh issue view` / `gh search issues` (read only). GitHub search quota ran out, so coverage is partial; diamond-types has no sync-bug issues (its issues are panics/questions: #50 load_from panic on malformed bytes, #35 "How should OpLogs exchange edits?"). Quotes are verbatim from the issue author or maintainer named.

## A. Sync-layer bugs

### A1. automerge/automerge#870 (2024) "Documents are not always eventually consistent: Synchronisation fails in specific scenarios" (closed)
- Symptom (svdvonde, issue body): "2 documents end up in a different state ... one document is `{"!!":false}` and the other document is `{"!!":"1"}` and they both claim to be in sync because their generated sync messages will be `null`."
- Root cause: not stated. Note the repro is concurrent puts on one key (maybe a merge-level cause); the symptom is a sync-layer one.
- Fixed: alexjg: "This is fixed in the latest beta (`3.0.0-beta.0`)". Related issue cited by reporter: #760.

### A2. automerge/automerge#772 (2023) "Dropped messages in the sync protocol cause infinite loops" (open)
- Symptom (author): "If this assumption is violated it is possible to cause an infinite loop of sync messages ... the receiver keeps asking for the changes that were in the dropped message and the sender keeps not sending them because it thinks it has already sent them."
- Root cause (ept): "The reason the sender suppresses sending a change it's already sent is that sometimes the recipient asks for the same change several times in a row, and we want to avoid wasting bandwidth".
- Fixed: open. Proposed fix is sequence numbers.

### A3. automerge/automerge#1284 (2026) "Rust sync can loop infinitely if a message is lost" (open)
- Symptom (dodomorandi): title; test case `infinite_sync_loop` with client<->server<->client.
- Root cause (alexjg): "The sync protocol requires a reliable in-order stream, I.e. you need to reset the sync state if there could have been a dropped message."
- Fixed: no; maintainers say "our ongoing work on a new sync system does not impose this constraint" (Subduction).

### A4. automerge/automerge#337 (2022) "Duplicate sync messages issues in `experiment` branch" (closed)
- Symptom (jeromegn): "I start getting the same non-empty sync messages over and over ... `generate_sync_message` always produces `Some(message)` ... so there's no way of breaking the loop."
- Root cause (ept, hypothesis): "the original message containing `895847d3` was lost for some reason, but the sync state remembered that this change was already sent, and so we avoid resending the change". Same mechanism as A2. Reporter used UDP gossip.
- Fixed: closed with the workaround "reset the sync state by encoding it to a byte array and decoding it again".

### A5. automerge/automerge#489 (2023) "Sync protocol takes one round trip per change in case of missing in-between changes" (closed)
- Symptom (philipmendels): "the sync protocol sends the missing changes one by one instead of in one go."
- Root cause (ept): "[this condition] suppresses the sending of a Bloom filter if there are currently missing dependencies that are not one of the remote node's heads ... requires round trips linear in the length of the longest hash chain." Bloom-filter handling, performance not correctness.
- Fixed: closed by FintanH as obsolete: "the work has been moved to https://github.com/inkandswitch/subduction."

### A6. automerge/automerge#760 (2023) "sync protocol not generating sync messages when changes to a list(array) are made to the document" (open)
- Symptom: "Automerge.change on a list(array), sync messages are somehow not being generated." Cause unclear (may be user error; I did not verify). Reporter of #870 called it "Potentially related".

### A7. automerge/automerge#1327 (2026) "MissingOps panic in ChangeCollector during generate_sync_message after fork_at + merge" (closed)
- Symptom: "panic in `op_set2/change/collector.rs` ... `unwrap()` ... The error is `MissingOps`" during `generate_sync_message()`. Peer cannot sync. Not stated whether it is sender-side change reconstruction (op-set bug, not protocol).
- Workaround (dman-os): `transaction_at` after merge, or save/load round trip.
- Fixed: closed; shikokuchuo: "The commit in #1366 appears to be good".

### A8. automerge/automerge#1160 (2025) "The need of a time/complexity limit on receive_sync_message()" (open) - performance only: "Which would make the app hang for a few seconds". Not a correctness bug.

### A9. automerge/automerge-repo#777 (2026) "Subduction: one slow or silent peer holds back every document's sync round" (open)
- Symptom: "a document that another peer can serve in milliseconds stays unloaded until the slow peer answers or the round deadline passes (`syncMs`, 60 s by default)."
- Root cause: "`syncWithAllPeers` resolves only after every connected peer has answered or timed out".

### A10. automerge/automerge-repo#343 (2024) "Repo and WebSocket provider send two responses for a "request" - the first unavailable, the second a sync" (closed; title only, body not read). #293 "An unavailable document may just not be found yet" (open; title only).

### A11. yjs/y-websocket#94 (2022) "WebsocketProvider needs to wait to send sync step 1 until after it knows the server is listening" (closed)
- Symptom: "Client never reaches 'synced' state because the server never responds to the client's sync step 1 (because the server wasn't listening at the time)".
- Root cause (author): server sets up the message listener late (async code in handleUpgrade), so the client's first message is lost; sync step 1 is not retried.
- Fixed: closed; users' workaround was to move async work before handleUpgrade.

### A12. yjs/y-websocket#203 (2026) "messageReconnectTimeout kills connections during large in-flight transfers" (closed)
- Symptom: "the client kills the connection mid-transfer, reconnects, and the server restarts the same send from byte 0 — a permanent loop ... 50–76 MB documents (close code 1005 every ~33s, forever)".
- Root cause: 30 s liveness check on "received a message", not configurable.
- Fixed: dmonad: "I implemented option 1 ... named `socketTimeout`" (v3 and v4).

### A13. yjs/y-websocket#204 (2026) "Handlers of a replaced socket keep mutating provider state (zombie connection applies updates / sets synced)" (closed)
- Symptom: "a connection the provider had abandoned completed a 69 MB sync in the background and flipped `synced`, double-transferring the doc and confusing the state machine".
- Root cause: "the old socket's `onmessage`/`onopen` closures stay attached".
- Fixed: dmonad: "I created a fix in v4.0.0-rc.3 and backported in to 3.1.0-rc.5".

### A14. yjs/y-websocket#122 (2022) "Reconnected client becomes visible to others only after some period" (open) - awareness layer (y-protocols awareness), not doc sync.
- Symptom: "if we call `provider.connect()` then no event will raise on the awareness instance of the first one."
- Root cause (author): "In our case `currClock === clock` but `state` is not null ... The problem as I can see it is that clock stays the same."

### A15. yjs/yjs#550 (2023) "Emit event when missing structs to apply entire update" (open, feature request). Quote: "Sometimes a message is dropped and the corresponding update does not reach a party. All following updates cannot be applied". dmonad: "It's good that this issue happened, because now you know that your communication layer in unreliable". Yjs also requires reliable delivery (pendingStructs never self-heals).

### A16. yjs/yjs#374 (2022) "encodeStateAsUpdate(doc1, vectorOfDoc2) don't return empty update between 2 equal docs" (closed, by design)
- Symptom: "Calculated update won't be empty It will have a `DeleteItem`". Cause (quoted from dmonad's earlier comment): "Deletes are not tracked by state vectors, hence clients always exchange all deletes with each other." So a state vector cannot prove two docs are equal; see also #419 "An easy way to know if two documents are in sync (including their internal state)" (closed; title only).

### A17. yjs/yjs#591 (2023) "Misordered updates result in temporarily missing Y.Map keys" (open)
- Symptom: "one of the modified properties will be entirely missing from document B. The documents will converge again when the first update is finally applied".
- Workaround (himself65): check `pendingStruct`. Transient state, not divergence.

### A18. yjs/yjs#829 (2026) "Delete sets, and v14 structs past a clock gap, are applied before the updates they depend on" (closed, rejected)
- Symptom: "a replica that receives the unbold before the insert it was issued after applies the unbold anyway, and shows a document that no causally consistent subset of the operations produces ... The replica converges when the missing update arrives."
- dmonad: "This is not a correctness issue." Report was AI-assisted. Weak.

### A19. loro-dev/loro#1040 (2026) shallow snapshot import "stalls as permanently pending when the snapshot root is a single-head frontier" (open)
- Symptom: "silently buffers the whole import as `pending` — `toJSON()` stays empty. The reported missing dependency is the snapshot's own root boundary op".
- Root cause: not stated.

### A20. loro-dev/loro#1215 (2026) "Importing a snapshot that supplies the dependencies of pending updates leaves the document state out of sync with its oplog" (open)
- Symptom: "the pending changes enter the oplog but are never applied to the document state ... a fresh document built from this one's oplog shows different text." Later panics: "poisoned LoroMutex".
- Root cause: not stated beyond the symptom. Strongest Loro sync-layer bug (silent state/oplog divergence).

### A21. loro-dev/loro#1068 (2026) "import() panics when a remote update depends on ops folded into a shallow snapshot ... panic poisons the doc mutex" (open; title only). #1118 "`import` with a reused peer id panics and poisons the doc" (closed; title only). #1046 "Movable list panics ... when a delete and a concurrent edit+move import as separate update batches — 1.13.7 regression" (open; title only). #944 "restored an older backed up loro doc - then tried to sync it with devices, it would keep crashing" (open; `assertion failed: slice_end > slice_from` at dag/iter.rs:299).

## B. Merge-function / data-structure bugs (not sync protocol)
- automerge/automerge#595 (2023, closed) "Automerge.save does not persist orphan changes, potentially leading to a loss of convergence". ConradIrwin: "when you save a doc it does not persist changes unless all their dependent changes are present." Storage layer; arguably sync-adjacent (pending changes lost on reload).
- yjs/yjs#699 (2025, open) "Y.Doc items integrated in different order after sync from server, possible corruption from UndoManager".
- yjs/yjs#811 (2026, open) "UndoManager: redo can produce a state that never existed, and a reloaded doc can differ from the live one"; #823, #794, #402, #487, #642 (UndoManager divergence); #382 (overlapping formatting); #828 (formatting markers); #461 (Y.Map element deleted after pendingStructs).
- yjs/yjs#417 (2022, closed) "Unreadable document created in certain cases"; #479 (closed) invalid update causes infinite loop in lib0.
- automerge/automerge#855 (2024, closed) malformed sync message crashes WASM: user error (wrong CBOR key `sync_message` instead of `data`).
- loro-dev/loro#1185, #1228, #1229, #1245 (UndoManager), #1157 (tree import misses Create event).
