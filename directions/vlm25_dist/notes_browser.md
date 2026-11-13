# Web distributed-systems problems worth verifying: browser/web candidates

(authored by agents unless marked 🧑)

Method: WebSearch + WebFetch only; nothing run, nothing published. Quotes come from WebFetch excerpts (a small model extracted them; treat as near-verbatim, re-check before citing externally). Google Scholar not used. Opinions are labeled OPINION.

## 1. Multi-tab / service-worker coordination

Who is hurt: users logged out; users of stale tabs hit broken lazy chunks.

Documented failures
- Refresh-token rotation, two tabs. https://github.com/johannesjahn/chat-platform/issues/650
  - "So having two active tabs can randomly log someone out about every 15 minutes."
  - "If they actually overlap, the server forks the family (case 1)."
  - "The second tab then calls clearSession(), and the shared localStorage session is gone in all tabs."
- Same with a real IdP (Authelia 4.39.28). https://github.com/soliplex/frontend/issues/670
  - "The IdP then revokes the whole token family, and the session dies in every tab."
  - "No code coordinates tabs"
- Service worker activates under a busy page. https://github.com/schlessera/brain-kit/issues/2569
  - "a new service worker activates under a busy page and deletes the lazy chunks it still needs"
  - "a second open tab that is busy loses chunks when an idle tab triggers the handover"
- Spec-level tension, unresolved. https://github.com/w3c/ServiceWorker/issues/993
  - "Surprisingly, the updated service worker doesn't even take control of the tab after refreshing the page."
  - "I want all tabs to share the same cache, until the last tab is refreshed."
  - Author closed it: "This thread is too much full of my own confusions" (continued in #1238).
- Practitioner sources (blogs, weaker): search results state localStorage "has no atomic compare-and-set" and the Web Locks fix; also "The lock only coordinates who performs the refresh". Not fetched; do not cite as verbatim.

Why distributed systems: tabs are independent processes sharing only async storage and messaging. Properties:
- Safety: at most one refresh in flight per token family across tabs and server; a tab never reads a cache entry its code version needs that was deleted (version-compatibility invariant); no two tabs both believe they hold the lock.
- Liveness: a crashed lock holder never blocks refresh forever; a waiting SW eventually activates.
- Composition issue: client lock plus server rotation/reuse detection must jointly avoid false revocation. Neither side alone is sufficient (a refresh may come from a non-browser client).

Why testing cannot settle it: interleavings of tab lifecycle (crash, bfcache, throttled background tabs, suspend), browser differences ("fails in Firefox, where registration.waiting is always null" in #993), and server timing. Bugs "difficult to understand and reproduce" (search snippet on w3c discussion).

What to prove / tool
- TLA+ (TLC for small N, then Apalache or TLAPS) model: N tabs, one SW, one IDB/localStorage, Web Locks with crash release, BroadcastChannel (at-most-once, no ordering assumptions), server with rotation + reuse-detection + optional grace window.
- Properties: NoSpuriousRevocation (a family is revoked only if an attacker replay occurred), SingleFlight, EventualAuth (some live tab eventually holds a valid token), SWVersionSafety (every live page's required assets remain available until the page unloads).
- Result most likely: a concrete counterexample to naive designs plus a proved-safe protocol (lock + re-read-then-refresh + server grace window).

Closest prior formal work (found): none specific.
- Search found no TLA+/Coq/K model of Web Locks, BroadcastChannel, IndexedDB, or the SW lifecycle (the W3C spec is prose and algorithms: https://www.w3.org/TR/service-workers/).
- Adjacent: "Specifying and Model Checking Workflows of Single Page Applications with TLA+" https://arxiv.org/pdf/2005.05627 (single page, not multi-context).
- Adjacent, from my memory, unverified here: Web Infrastructure Model (Fett, Kuesters, Schmitz) for OAuth/OIDC; Akhawe et al. Alloy web model. Neither covers multi-tab.

First bite: 1-page TLA+ spec of refresh-token rotation with 2 tabs, with and without a lock; show TLC reproduces #650's logout trace (2 tabs, 1 server). Then add the SW activation/cache-deletion model.

Niche rating (OPINION): high; no prior formal model; real bugs are everywhere; small state space.

## 2. Federated protocols

Documented failures
- Delete does not propagate. https://github.com/mastodon/mastodon/issues/22154
  - "Currently, posts deleted over a week earlier on one server are still visible on others."
  - Contributor: "in a federated network, how can my server possibly guarantee what's going on elsewhere?"
  - Maintainers treat it as a suggestion, not a bug (OPINION: this is by design, so a "bug" framing is weak; the specification question is what guarantee to promise).
- https://github.com/mastodon/mastodon/discussions/37955: "The "Delete" command is a request (a Delete activity) sent to those remote servers, which may or may not be honoured"
- Opposite hazard: https://github.com/mastodon/mastodon/issues/37730 (Delete is permanent and later activities for the object are ignored; proposal to re-fetch per FEP-4f05).
- AT Protocol: https://github.com/bluesky-social/proposals/blob/main/0006-sync-iteration/README.md
  - "It is not the responsibility of a PDS, or a relay, to proactively detect if downstream consumers have gotten out of sync."
  - "However, the `blocks` can not be fully verified against the `ops`." (motivation for Sync 1.1 "inductive firehose")
  - Account deletion path (https://github.com/bluesky-social/atproto/discussions/3175, via search snippet): relays "should ignore #account and #commit events which are not coming from the currently declared PDS instance"; interaction with migration is unexamined.

Distributed-systems property: eventual deletion (liveness) and no-resurrection (safety) under best-effort delivery, forwarding, migration, and caches; firehose gap detection and resync convergence (consumer state eventually equals repo state).

Why testing is weak: open network, heterogeneous implementations; but a model abstracts that.

Prove: TLA+; "tombstone beats later Update/Create"; "consumer that follows sync 1.1 rules converges to repo state after any loss of events"; no-resurrection after account migration.

Prior formal work: search found none for ActivityPub or AT Protocol (nearest: GossipSub model https://arxiv.org/pdf/2212.05197).

First bite: TLA+ of Sync 1.1 #commit/#sync/#account with lossy firehose and a consumer; check convergence and that deleted accounts end deleted.

Niche rating (OPINION): high novelty, but the spec is moving and the guarantee is weakly specified, so "what to prove" needs work. Second strongest.

## 3. Collaborative editors (beyond OT)

Already verified (human): OT code. Remaining gaps found:
- Yjs: lean-yjs verifies the YATA algorithm. https://github.com/yjs/yjs README: "lean-yjs provides a formal verification of the YATA CRDT algorithm that Yjs implements…" and "While the CRDT algorithm itself is correct (currently proven for preservation and commutativity)…". It also shows the original paper's pseudocode has errors. Sync protocol (state vectors, pending structs, awareness) is not covered.
- Automerge sync protocol bug: https://github.com/automerge/automerge/issues/870
  - "2 documents end up in a different state, whereas it seems like after a full synchronisation they should have exactly the same state."
  - Both sides report synced "because their generated sync messages will be `null`."
  - Maintainer: "This is fixed in the latest beta (`3.0.0-beta.0`)" (found by fast-check property testing; fixed 14 months after report).
- Automerge overlapping sync: https://github.com/automerge/automerge/issues/536: errors "duplicate seq found for actor, invalid changes: changes out of order, mismatching heads".
- Newer: https://github.com/inkandswitch/subduction/issues/306 (sync cannot replace fragments that erased their head).
- Peritext: convergence proof is a paper proof (Appendix A) https://dspace.mit.edu/bitstream/handle/1721.1/147641/3555644.pdf; validated by randomized testing; no machine-checked proof found.
- Undo for CRDTs: papers exist (Stewen and Kleppmann, arXiv 2404.11308; Yu 2019 OPODIS) but I found no verified undo in Yjs/Automerge.
- Related verification: Isabelle op-based CRDTs (Gomes, Kleppmann et al.; from memory), MET (TLA+ driven testing) https://arxiv.org/pdf/2204.14129, Certified MRDTs https://arxiv.org/pdf/2203.14518.

Properties: sync-protocol termination and "no-message implies equal state" (safety of the quiescence test, liveness of convergence); undo restores intent.

Testing limits: property testing found #870 but only after a user hit it; exhaustive assurance needs a model.

Prove: Automerge/Yjs sync handshake: if both sides emit no message, heads equal (and states equal). Tool: TLA+ for protocol, Verus/Lean/Isabelle for the Bloom-filter/heads logic.

First bite: TLA+ of Automerge's sync state machine (sentHashes, theirHeads, Bloom false positives) with the #870 scenario as the regression check.

Niche rating (OPINION): medium; crowded academic space (CRDTs), but sync protocol and undo/rich-text still thin.

## 4. Payments / checkout

Documented
- https://docs.stripe.com/webhooks: "Webhook endpoints might occasionally receive the same event more than once."; "Stripe doesn't guarantee the delivery of events in the order that they're generated."; "In some cases, two separate Event objects are generated and sent."; retries "for up to three days".
- Race write-ups (blogs, weaker evidence): TOCTOU check-then-process in webhook handlers, and two writers (webhook plus checkout-return) double-processing. Search snippets only.
- Informal contract (blog): same key and body returns the same response with one set of side effects; same key with a different body is an error; concurrent same-key requests never both execute.

Property: exactly-once effect from at-least-once delivery plus idempotent handlers; crash window between "pending" row and gateway call.
Prior formal work: none found for payment idempotency; IETF draft draft-ietf-httpapi-idempotency-key-header is a semi-formal spec.
Prove: TLA+ model of client, API with key store, webhook, handler, DB; Alloy also fine.
First bite: TLA+ spec of the IETF draft semantics with crashes and retries.
Niche rating (OPINION): low niche. Well understood by practitioners; value in a clean reusable spec, not discovery.

## 5. Session/state consistency across AI-agent sessions

Evidence thin and mostly blogs (search snippets only): lost updates when two agents read version 1 and the later writer overwrites ("Agent A's work is silently lost"); Agno fix for duplicate MCP sessions under parallel tool calls. No primary bug-tracker evidence fetched.
Property: serializable or merge-defined shared state; lease/lock liveness.
Prior work: none found; the problem reduces to optimistic concurrency plus CRDTs (known).
Niche rating (OPINION): trendy, little novelty; evidence not yet solid. Weakest.

## Ranking (OPINION)
1. Candidate 1 (multi-tab auth refresh + SW activation): real recurring bugs, no prior formal model found, small bounded model, genuine client-server composition.
2. Candidate 2 (AT Protocol sync/deletion).
3. Candidate 3 (Automerge/Yjs sync protocol, undo).
4. Candidate 4. 5. Candidate 5.

Gaps: Scholar not queried; "no prior work found" means only that these searches found none.
