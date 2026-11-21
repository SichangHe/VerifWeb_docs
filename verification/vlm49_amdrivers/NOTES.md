# vlm49_amdrivers: can deployed Automerge sync drivers reach the no-loss stuck case?
(authored by agents unless marked 🧑)

Short answer. Fact: I found no deployed driver that reaches it. The stuck case needs (a) delivery of an older message after a newer one and (b) no `generate_sync_message` between the two receives. Every JS driver I read does (b)-defeating generate after each receive, and every shipped transport I read is in-order per connection; the repo also drops messages from a superseded adapter. The one driver that does batch receives (Rust `automerge-repo-rs`) rides on TCP (in-order) and is deprecated in favour of samod. Inference: not reachable in practice over TCP/WebSocket/BroadcastChannel/MessageChannel; I did not test real network faults. Positive evidence the state exists in JS wasm, and that batching + reordering reaches it, is below (own harness, not a deployed driver).

Sources (cloned under `src/`, untrusted, only read; npm packages installed only in `harness/`):
- automerge-repo HEAD `6e2101acbf1151cf35d6bd17b7dc61a6384fc828` (2.6.0-alpha.5, rewritten DocSynchronizer)
- automerge-repo tag v2.5.6 `38d06b9d9ef0bbe1e0693d3b859015f38897f34b` (`src/amrepo-hist`)
- automerge-repo-sync-server `c357887cb7295ddd2399a679e4e75def2a284801`
- automerge-repo-rs `2ae6b224bb7b4511c99a2b81b66a71817a400728`
- inkandswitch/patchwork `3528f15d1b07fed3e3f3d8d4dcc0f3012a93d8d7`, tiny-essay-editor `ba24a2f37b6535bf3bfedb031d57bfa1ba27a620`
- automerge-swift `658cb91e914cabca4cba75557ed35a7de6ad1bfc`, automerge-go `6fb4f2d0824411287925acfc0232948b46d899f8` (only grepped)

## 1. JS automerge-repo
Fact: sync-server depends on `"@automerge/automerge-repo": "^2.5.6"`, `"@automerge/automerge-repo-network-websocket": "^2.5.6"`: it is plain Repo + WebSocketServerAdapter. Patchwork and tiny-essay-editor call neither `generateSyncMessage` nor `receiveSyncMessage` themselves (grep: only a vendored wasm copy in TEE); they use automerge-repo with websocket/BroadcastChannel/MessageChannel adapters (package.json: `"@automerge/automerge-repo": "^1.1.12"` in TEE). So the question reduces to automerge-repo.

Generate after every receive.
- v2.5.6 `DocSynchronizer.ts:405` (inside `#processSyncMessage`, right after `A.receiveSyncMessage`): `this.#sendSyncMessage(message.senderId, doc)`. Queued messages are drained one by one through the same function (`:444` `this.#processSyncMessage(message.message)`), so each still generates.
- HEAD: `receiveSyncMessage` ends with `this.#evaluate()` (`DocSynchronizer.ts:306`), and `#receiveSyncMessage` sets `peer.dirty = true` ("Mark this peer dirty so #evaluate sends a response."). Exception (inference from reading): `#evaluate` can `continue` past a dirty peer (no generate) for share-policy loading, "defer availability", or "awaitingSupplierData"; those skips apply to peers that have not yet sent heads, and a stale-heads message sets status "has" first, so I judge this does not give the needed pair. Not tested. In `#activatePeer` queued messages are drained in a loop (`this.#receiveSyncMessage(msg)`) with ONE `#evaluate` after: that is a batch of receives without generate, but in arrival order, and HEAD's version has no stale-heads reorder source (see transports).
- Throttling (`asyncThrottle(..., syncDebounceRate=100)` on the handle "change" event) only delays extra generates; it never replaces the generate-after-receive.
- Unknown/side observation (v2.5.6 `:144,:174,:180`): when the sync state is still loading from storage, queued callbacks all get the loaded `syncState` object and `#syncStates[peerId]` is set to it after the loop, i.e. a state reset, not a stale-heads overwrite. Not pursued; it does not match the stuck pattern as far as I can tell.

Reconnect / multiple connections.
- Persisted/reused state keeps only shared heads: `rust/automerge/src/sync/state.rs` `encode` writes `encode_hashes(&mut buf, &self.shared_heads)`; `parse` sets `their_heads: None, sent_hashes: BTreeSet::new(), in_flight: false`. v2.5.6 `beginSync` round-trips the state through encode/decode (comment "round-trip it through the encoding system"). So reconnect forgets `their_heads`: no stale overwrite across connections (fact, from reading).
- HEAD `NetworkSubsystem.ts:59` `this.#adaptersByPeer[peerId] = networkAdapter` routes to the newest adapter, and `:96` `this.#log.debug(\`ignoring stale message from ${msg.senderId}\`)` drops messages from older adapters of the same peer id. Two relays to the same peer: later one wins, so interleaving is cut. v2.5.6 lacks this check (not verified in detail): I don't know if an old connection's late message could be delivered after a new one there.
- WebSocketServerAdapter `:227` `if (this.sockets[senderId] !== socket) { return }` drops messages from replaced sockets.

Transports (reorder possible?).
- WebSocket (client/server adapters): one socket per peer, TCP in-order. Sends on non-OPEN sockets are dropped silently (`:149` "Drop silently"); that is loss, not reorder, and a closing socket triggers `peer-disconnected` -> removePeer -> fresh state next time.
- BroadcastChannel: one `postMessage` per message; browsers deliver in order per channel (inference; HTML spec for MessagePort ordering, I did not test). `targetId` filter only. MessageChannel: `postMessage` over a MessagePort, ordered (inference, same).
- So no shipped transport reorders. Custom adapters could; out of scope.

## 2. Other drivers
- automerge-repo-rs (`src/repo.rs`): this one batches. `:1815` `per_remote.push_back(message.clone())` collects all messages from a drain per remote; `:1029-1031` `for message in messages { conn.receive_sync_message(&mut document.automerge, message)` receives all of them, then generates once afterwards (`info.generate_sync_messages()`). Pending-auth drain (`:686`) also receives several before one generate. Transport in its example is TCP (in-order); README: "An experimental Rust implementation ... is being developed in the [alexjg/samod] repo" and says its protocol is not JS-compatible. It uses `automerge = "0.7.0"` (Cargo.toml:30), older than the studied 0.10. Reachable only with a reordering transport; I did not run it.
- samod: already done (vlm48), generates after every receive.
- automerge-swift, automerge-go: only bindings exposing generate/receive; the repo layer for swift (automerge-repo-swift) and others I did not read. I don't know about them. Same for third-party servers (e.g. hosted sync services) whose source I could not see.

## 3. Experiments (own harness, `harness/`)
Packages: `@automerge/automerge-repo@2.5.6` with `@automerge/automerge` 3.5.0.

(a) Bare JS wasm, the 13-step trace (`harness/bare.mjs`; FP edit found by searching candidates):

    none (no generate between the two receives)  tries=58  converged=false  silentRounds=30
    new  (generate after each receive)           tries=275 converged=true
    old  (generate with pre-receive doc)         tries=571 converged=true

Fact: JS wasm 3.5.0 also gets stuck, and generating after each receive repairs it (same as samod/crate). The "old" variant mirrors v2.5.6 passing the pre-update `doc`; it converged (the old doc object shares the wasm handle, I did not look into why).

(b) Two real Repos v2.5.6 with an in-memory adapter (`harness/repo_net.mjs`, results `repo_2.5.6_results.txt`): A edits 25 times, B 6 times at random 0-150 ms gaps, 300 runs per row, stalled = heads differ after 3 s.

    loss 0, reorder 0    0/300 stalled
    loss 0, reorder 0.5  0/300  (8541 of 17369 sync msgs delayed 5-60 ms)
    loss 0, reorder 1    0/300  (all 18655 delayed)

Fact: no stall. Caveat: a loss run crashed with a `find` timeout (the first request dropped), so I have no positive control at the Repo level; and the FP is not forced (about 1% per change, 31 changes per run, so FPs occurred in some runs by inference, not counted).

(c) Bare fuzz of schedules (`harness/fuzz.mjs`, random edits and generate/deliver, no loss, no dup, 8 edits, up to 60 steps then drain under the same policy). Stuck = heads differ at silence:

    order      generate policy        stuck / runs
    in-order   after each receive      0 / 3000
    in-order   batch (k recv, 1 gen)   0 / 23000
    reordered  after each receive      0 / 13000
    reordered  batch                   5 / 13000

Fact: batching plus reordering reaches the stuck state at about 4 per 10,000 random schedules; eager generate with reordering: 0; batching in-order: 0. This matches the vlm43/vlm48 account and is consistent with the claim that both ingredients are needed (not a proof; in-order+batch bounded evidence only). A 20,000-run reorder+each run crashed in node (V8 fatal) and was replaced by smaller chunks.

## Not done / I don't know
- No test of real mid-connection TCP faults, real browsers, or the HEAD (2.6 alpha) Repo; no run of automerge-repo-rs; automerge-repo-swift and closed-source servers unread.
- The share-policy `continue` paths in HEAD `#evaluate` are argued, not tested.
