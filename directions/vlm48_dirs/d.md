# 18 candidate directions (web platform, sync, identity, desktop web apps)
(authored by agents unless marked 🧑)

Written 2026-11-13 by vlm48_dirs_d. For each direction, "Broken" is one real failure with a link and a verbatim quote, and "Prove" is the theorem we would prove. Full evidence, extra bugs and gaps follow in sections A, B and C.

Caveats (FACT): Google Scholar showed a CAPTCHA after 4 queries and was not bypassed, so prior work was checked only for A1-A3. Many quotes came through a summarizing fetch tool and must be re-checked against the raw page before anyone cites them. Every "Prove" line is the agents' inference.

Agents' strength guess (OPINION):
- stronger: B2 Matrix state resolution, A6 navigation/session history, C2 Tauri IPC capabilities, C4 refresh-token rotation, A4 IndexedDB (Servo Rust), B5 MLS epoch forks
- middle: C3 Servo CORS, A3 passkey Signal API, A2 storage partitioning, B1 offline-first sync engines
- weak (thin or old bugs): A1, A5, B3, B4, B6, C1, C5, C6


---


Notes on method. Quotes below were returned by a page-fetch tool that sometimes trims; I did not re-verify them against raw HTML. Scholar: the A1 query (service worker update, run first) and two more (storage partitioning; passkeys) returned results. Every later query returned challenge_action_required (CAPTCHA). My batch script kept going after the first block, so 8 further attempts hit the CAPTCHA; I did not bypass it or retry. Scholar is blocked for A4, A5, A6 and for a second A2/A3 query.

A1. Service worker update/lifecycle
Broken: https://github.com/mentria-ai/website/issues/1163 (Jul 2026): "Old page + new module = an API-contract lottery after every deploy." (FACT)
Prove: INFERENCE: for a model of page, SW versions, caches and skipWaiting/claim/controllerchange, every client eventually runs one consistent app version, and no page ever mixes old code with new cache contents; target code is an app's SW plus a generic SW library (Workbox/Serwist), testing misses it because the bad interleavings need deploy-during-open-tab timing.
Evidence:
- https://github.com/OffCrazyFreak/Disscount/issues/171 (Aug 2026): "The next navigation 'can then combine the old client runtime with a React Server Component response from the new deployment'" and crashed in production.
- https://github.com/chaxus/ran/pull/400: the old-cache lookup issue: "caches.match(url) on CacheStorage, which searches every cache rather than just CACHE_NAME" (as relayed by search summary, not verified verbatim).
- https://github.com/404-heisenberg/unilogs/issues/346 "Service worker serves a stale app shell that breaks navigation after deploys" (title).
- Opposite failure: https://github.com/sven1103-agent/pi-central/issues/120 "Installing the PWA must not preserve a stale bundle: `index.html` is never cached" (title); stale forever.
- Implementations: SW spec is in browsers (C++/Rust none significant); Workbox is JS; Rust: Servo has a service worker implementation in progress (not checked). 
- OPINION: these are mostly app-level bugs in small repos; the class is real but each is a solo-developer fix, not a browser failure. Weak-to-medium.
Prior work: Scholar q "service worker update lifecycle formal verification" (2022+) returned nothing relevant (top hits: industrial life-cycle UML verification papers). FACT. No evidence anyone verified SW update protocols; INFERENCE only.
Gaps: no browser-level (Chromium/WebKit) SW update bug found; did not check spec issues in w3c/ServiceWorker; did not check Servo SW status.

A2. Storage partitioning
Broken: https://github.com/privacycg/CHIPS/issues/88 (Jul 2024): "It's only Chrome where the problematic situation happens: shared partitioned storage, different storage access." (wordpress.com reverted a rollout; logged-in state leaked between iframes.) FACT
Prove: INFERENCE: for a model of partition key (top-level site, ancestor bit, storage access state) over cookies, IndexedDB, SW, BroadcastChannel, blob URLs, state written under one key is never readable under another; code is the key-derivation and lookup paths in each browser; testing fails because the key space (embedding chains x storage-access grants) is large.
Evidence:
- https://github.com/privacycg/storage-partitioning/issues/44 (Feb 2024): "Correct, we postMessage but onmessage handler never receives a message." (BroadcastChannel across iframe and popup after requestStorageAccess.)
- Mozilla bug 1731999 / 1784900 and Chrome blink-dev "Intent to Ship: Partitioning Storage, Service Workers, and Communication APIs": browsers shipped partitioned SW at different times and with different rules (Firefox: "partitioned Service Workers... will remain partitioned even when storage access is granted", search-summary quote). Chrome: unpartitioned SWs intentionally inaccessible in 3P (privacy-sandbox-dev-support #409, summary).
- Spec PRs: whatwg/storage#144, whatwg/dom#1142, whatwg/html#8447, #7567, #7995.
- Implementations: Chromium (C++), Gecko (C++/Rust partly), WebKit (C++). Rust: Servo storage-key support not checked.
Prior work: Scholar hits (FACT, titles verbatim): "Measuring the privacy vs. compatibility trade-off in preventing third-party stateful tracking" (J Jueckstock et al., ACM 2022); "{Pool-Party}: Exploiting browser resource pools for web tracking" (Snyder et al., USENIX Security 2023); "WebAPISpec: An extensible, machine checked model of secure browser specifications" (year/venue not captured; closest to this direction, worth reading). Nobody found proving partition noninterference across APIs; INFERENCE, based on one query.
Gaps: did not find a single cross-browser disagreement spec issue; partition-key table per browser not built.

A3. Passkey/WebAuthn credential state
Broken: https://github.com/zitadel/zitadel/issues/12987 (Oct 2026): "When a passkey is removed through User v2 `RemovePasskey`, the credential stays in the user's passkey manager." and "The manager keeps offering it, and the sign-in fails." FACT
Prove: INFERENCE: for a model of RP database, client Signal API calls and authenticators/sync providers with message loss and reordering, the set of credentials offered by authenticators eventually equals the RP's accepted set (convergence), and a signal never deletes a credential of another account (safety). Code: RP server logic plus a model of the platform provider. Testing fails because providers are closed and sync is asynchronous.
Evidence:
- https://www.corbado.com/blog/signal-api-ios-passkey-deletion-bug (Aug 2026): "deleting a passkey for one account can delete the passkey of a completely different account." Filed as WebKit bug 322267 (per article), "no fix exists yet".
- https://bugs.webkit.org/show_bug.cgi?id=278339 comment: "await window.PublicKeyCredential.signalAllAcceptedCredentials() never resolves" in Safari 26 (search-summary quote).
- W3C explainer https://github.com/w3c/webauthn/blob/main/explainers/signal-api.md: non-goal that "Signal methods do not allow credential providers to update information stored by relying parties" (search-summary quote; convergence is thus one-directional by design).
- Implementations: Chrome/Edge 132+ shipped; Safari 26; RP libraries in Rust exist (webauthn-rs, not checked for Signal API). 
Prior work: Scholar (FACT titles): "Passkeys in Practice: An Empirical Evaluation of FIDO2/WebAuthn Compliance and Interoperability" (2026, venue not captured); "The state of passkeys: Studying the adoption and security of passkeys on the Web"; "Server-Side Passkey Implementation in Java: Pitfall Detection and Backend Support Evaluation". Empirical only; no verification of signal/sync convergence seen. Second query: Scholar blocked (CAPTCHA).
Gaps: sync-provider (iCloud/Google/1Password) internals are closed, so the model's authenticator side is assumption; WebKit 322267 not opened.

A4. IndexedDB transactions
Broken: https://bugzilla.mozilla.org/show_bug.cgi?id=1458342 (open, 8 years): "IndexedDB bfcache behavior is broken: window will successfully go in bfcache but active transactions will be silently aborted" (title). FACT
Prove: INFERENCE: IndexedDB (spec plus an implementation) gives serializable transactions whose committed writes survive a crash per the durability mode, and a page lifecycle event (bfcache, navigation) never aborts a transaction silently; testing fails because bugs need lifecycle/crash interleavings.
Evidence:
- https://bugs.webkit.org/show_bug.cgi?id=216769 (Safari 12-14): transaction outdated right after creation; closed citing the spec (a spec-vs-expectation disagreement, tool-summarized).
- https://github.com/simolus3/drift/issues/3864 (Sep 2026): "the committed transaction is silently lost." (library bug, not browser; fixed next day.)
- https://bugzilla.mozilla.org/show_bug.cgi?id=1112702 non-durable by default: complete event "potentially before that data has actually been flushed" (summary).
- Implementations in Rust: Servo (components/script/dom/indexeddb, components/storage/indexeddb with SQLite engine; PRs servo#33044, #41508 "Indexeddb: transaction lifecycle", #43900); Ladybird PR #13287 "LibWeb: Implement IndexedDB in Rust" (title). So a Rust target exists and is under active change.
- OPINION: the Servo angle is the most concrete; browser bugs are old and diffuse.
Prior work: Scholar blocked; not checked. 
Gaps: no recent (2024+) browser-level data-loss bug found; Chromium tracker not searched.

A5. Web Locks / BroadcastChannel / bfcache
Broken: https://bugs.webkit.org/show_bug.cgi?id=239614 (Apr 2022, fixed): "Web Locks held in a Worker are not released on page refresh or exit"; reporter: "This has the potential to cause deadlock in any application that uses Web Locks in a Worker." FACT
Prove: INFERENCE: in a model of documents, workers, bfcache freezing and lock requests, every held lock is eventually released or its holder destroyed, and no pending request waits forever when holders are frozen or gone (liveness); code: a browser's lock manager. Testing fails because it needs freeze/destroy interleavings.
Evidence:
- https://github.com/whatwg/html/issues/11445 (Jul 2025): a SharedWorker that needs a message from a bfcached document "will end up holding that lock forever if the document in question is destroyed" ; asutherland: a lock held by a SharedWorker "frozen because all of its connected documents are in BFCache."
- https://bugzilla.mozilla.org/show_bug.cgi?id=1754689: intermittent timeout in web-locks/bfcache/abort test (title only).
- Rust: Servo Web Locks not checked.
- OPINION: small, well-bounded spec; a plausible tractable proof, but only one real bug (fixed) plus a spec discussion; BroadcastChannel half has no bugs found. Medium-weak.
Prior work: Scholar blocked.
Gaps: no Chromium bugs; no user-visible 2024+ failure found.

A6. Navigation / session history traversal
Broken: https://github.com/whatwg/html/issues/12861 (Aug 2026, shannonbooth): "the iframe never fires its load event, and waitForLoad waits forever." (a queued same-document finalization overwrites the ongoing-navigation ID and aborts a later cross-document navigation; spec as written, found via Ladybird). FACT (quote from tool summary)
Prove: INFERENCE: in a model of the traversable/navigable tree with the session history traversal queue and synchronous navigation steps, every navigation or traversal terminates (fires load or is aborted observably) and each navigable's active entry is in its entry list; code: spec algorithm, then an implementation such as Ladybird/Servo. Testing fails: these are races between queued and queue-jumping steps.
Evidence:
- https://github.com/whatwg/html/issues/12961 (Sep 2026): "the entry that gets activated and the state derived for it can disagree"; "Ladybird, which follows the spec as written, crashed".
- https://github.com/whatwg/html/issues/12362 (Apr 2026): steps are "deferred without any guarantee that the same 'ongoing navigate event' is still active when they run."
- https://github.com/whatwg/html/issues/6927 (Aug 2021, label "Implementations are not interoperable with each other"): "Ignore first traversal (Safari)", "Ignore second traversal (Firefox)", "Coalesce the traversals, potentially to a no-op (Chrome)".
- Implementations: Ladybird (C++, porting to Rust in places), Servo (Rust, spec-following navigation; not checked in detail).
- Older: arXiv 1608.05444 "A model of navigation history" (title, search result): browsers disagree with each other and the spec. Prior formal model exists but predates the rewrite. 
- OPINION: strongest of the six: recent (2026), many open spec bugs in the same algorithm, spec-following implementations crash, and a formal model would fix the spec, not only one browser.
Prior work: Scholar blocked; only the 2016 arXiv model found via web search (pre-2022, outside the brief's window).
Gaps: unknown if bugs are concurrently being fixed (noamr's commits on #12362); not checked whether anyone is already model-checking the rewritten spec.

---



Labels: FACT = quoted from a source; INFERENCE; OPINION. Quotes were fetched with WebFetch (a small summarizing model) and may be trimmed, so re-check before citing. The GitHub API was rate-limited, so searches were via web search. Dates are as shown on the pages.
Scholar: the first query (B1, after the 10-minute wait) returned a CAPTCHA/browser-challenge page. Per the brief I stopped. Prior work is "Scholar blocked" for all six; no Scholar query ran for B2-B6.

## B1 offline-first sync engines (Replicache/Zero, PowerSync, Electric, Triplit)
Broken: Zero 0.26 release notes list "Fix duplicate mutations when retry transaction succeeds" (PR #5634, rocicorp/mono). https://zero.rocicorp.dev/docs/release-notes/0.26 (FACT; no release date on page; one line, no detail).
Prove: after any sequence of disconnects, retries and server restarts, every mutation the server acknowledged was applied exactly once, in per-client order, and the client state equals server state plus its pending mutations. Code: push endpoint with lastMutationID, pull/rebase logic, client queue. Testing does not suffice because failures need a specific interleaving of lost response, retry and concurrent pull.
Evidence:
- Replicache docs, Database Isolation Level (https://doc.replicache.dev/concepts/db-isolation-level), FACT as returned: "We end up running the mutation twice." Occurs if the push endpoint lacks snapshot isolation (design hazard, not an observed incident).
- Replicache Push Endpoint Reference (https://doc.replicache.dev/reference/server-push): "Replicache will continue retrying a mutation until the server marks the mutation processed." Exactly-once rests on the app server advancing lastMutationID atomically with the effects: a checkable contract.
- powersync-native PR #26 (https://github.com/powersync-ja/powersync-native/pull/26, Sep 2026, Rust SDK): "That trigger is dropped, leaving offline writes queued until another local write occurs." Stuck, not lost.
- powersync-swift #204 (https://github.com/powersync-ja/powersync-swift/issues/204): uploads stop after disconnect()/connect() (search summary, not quoted from the page).
- rocicorp/mono PR #6687 (https://github.com/rocicorp/mono/pull/6687): pending mutations kept across disconnect; no loss claimed.
- Real Rust: PowerSync Rust SDK (powersync-native) and sqlite-core extension. Zero/Replicache are TypeScript. Electric and Triplit trackers not examined.
Prior work: Scholar blocked.
Gaps/unknowns: found NO confirmed lost or double-applied mutation in an engine's own repo; found bugs are liveness (stalled upload) plus one unexplained Zero duplicate fix. INFERENCE: weak as "real bug" evidence; strong part is the clear atomicity contract. Did not read PR #5634.

## B2 Matrix state resolution (v2, room v12)
Broken: Matrix.org, Project Hydra post (https://matrix.org/blog/2025/08/project-hydra-improving-state-res/): "This unexpected class of rollbacks is called a “state reset”." and "delayed federation traffic could cause key-value state associated with a room to revert to an earlier state." It says v2.1 fixes "state resets observed in public rooms including: #rust, the Office of the Matrix.org Foundation, the TWIM room". Also "users being re-added into a room they have left". FACT. CVE-2025-49090.
Prove: for any set of events and any delivery order, all honest servers holding the same events compute the same room state (convergence), and v2.1 never lets an event revert state without a valid auth chain. Code: ruma-state-res / homeserver state-res (Rust), also Synapse (Python), gomatrixserverlib (Go). Testing does not suffice: failures occur in rare event-DAG shapes with delivery delays across servers.
Evidence:
- gomatrixserverlib #471 (https://github.com/matrix-org/gomatrixserverlib/issues/471, Nov 8 2026): "State resolution v2.1 drops conflicted events and panics for room version 12"; "every conflicted non-control event is dropped." FACT.
- Continuwuity release v26.8.1 (https://forgejo.ellis.link/continuwuation/continuwuity/releases, 2026-08-22): "Fixed event tracking forgetting to mark soft-failed/rejected events as referenced"; the fetch summary says this led to "frequent dummy squashes and state resets" (that part not verified as a verbatim quote).
- Continuwuity PR #943 "Implement room v12" (https://forgejo.ellis.link/continuwuation/continuwuity/pulls/943): marked as not working because state resolution did not resolve correctly (search summary, not quoted).
- Nheko #1931 (https://github.com/Nheko-Reborn/nheko/issues/1931, Aug 11 2025): "clients must support room version 12 in order to address CVE-2025-49090 (State Resolution 2.0 deficiencies)".
- Real Rust: ruma-state-res, conduwuit/continuwuity, Conduit.
Prior work: Scholar blocked.
Gaps/unknowns: did not confirm whether v2.1 convergence has a published proof; did not read MSC4297; Continuwuity "netsplit" quote not found.

## B3 Firefox Sync / application-services
Broken: Bugzilla 621584 (https://bugzilla.mozilla.org/show_bug.cgi?id=621584), title: "[meta] Bookmarks dataloss (duplicated, reordered, moved, lost, attributes changed, etc) caused by Sync". FACT, but old (opened 15 years ago, closed WONTFIX); not 2022-2026.
Prove: after any interleaving of edits, syncs and offline periods on N devices, the merged bookmark tree converges across devices, is a valid tree, and no bookmark present and not deleted is dropped. Code: dogear merger and bookmark/logins/tabs engines in application-services (Rust). Testing does not suffice: bugs need rare tree shapes (moves plus deletes under concurrent edits).
Evidence:
- Bugzilla 1586172 (https://bugzilla.mozilla.org/show_bug.cgi?id=1586172, about 7 years old): "Fix handling of duplicate and missing child GUIDs in the bookmarks mirror"; telemetry "NOT NULL constraint failed: structure.guid" and "UNIQUE constraint failed: structure.parentGuid, structure.guid". FACT, pre-2022.
- application-services #1930 (https://github.com/mozilla/application-services/issues/1930): "`moz_bookmarks.type` can be null, causing bookmark merges to fail" (title from search result; merge failure, not loss).
- Bugzilla 812348, 1286786 (thousands of duplicate bookmarks), 1301580 (deleted bookmarks return as duplicates): historical, pre-Rust.
- dogear docs (search summary): conflicts are resolved at item level, not property level, so a title edit on one device and a URL edit on another loses one. INFERENCE: a designed loss, i.e. a spec question.
- Real Rust: dogear, application-services sync15 (bookmarks, logins, tabs).
Prior work: Scholar blocked.
Gaps/unknowns: found NO 2022-2026 user-visible loss bug in the Rust code. Weak on "recent real bugs"; stronger as a spec exercise (what "no loss" means when merge is item-level).

## B4 password manager vault sync
Broken: bitwarden/server #332 (https://github.com/bitwarden/server/issues/332, Aug 3 2018), title "\"Sync Vault\" does not really sync. Possible data loss"; steps "Edit existing Item in Vault 1 [e.g. Browser] (Add OTP)", "Edit same Item there (Upload an attachment)"; actual "Item has only Atachment" and "OTP is lost". FACT (2018; Bitwarden later added a stale-copy check per forum posts).
Prove: no acknowledged edit is lost: for concurrent edits to one item, either both merge or the second writer is rejected and told to resync (compare-and-swap on revisionDate), and clients converge. Code: server cipher update path plus client sync. Testing does not suffice: needs two-device interleavings including offline edits.
Evidence:
- Bitwarden forum, Dec 14 2025 (https://community.bitwarden.com/t/edit-error-cypher-out-of-date-2025-12-0-clients-unofficial-third-party-server/91957): "The client copy of this cipher is out of date. Resync the client and try again." On the first save the change "is successfully committed" despite an error toast. FACT. Vaultwarden (Rust) issue, fixed in 1.35.1 per the thread.
- bitwarden/clients #22013 (https://github.com/bitwarden/clients/issues/22013, 2026.7.0): "After upgrading to version 2026.7.0, my vault data has completely disappeared/empty" (search summary; display loss with Vaultwarden, not data loss).
- vaultwarden #341 (https://github.com/dani-garcia/vaultwarden/issues/341): editing an item without syncing after sharing it to an organization leaves fields as "[error: cannot decrypt]" (search summary).
- Real Rust: Vaultwarden (server), Bitwarden SDK. KeePassXC is C++.
Prior work: Scholar blocked.
Gaps/unknowns: no 2022-2026 confirmed silent loss in official Bitwarden; the revisionDate guard is simple, so the proof is small. 1Password closed source; KeePassXC not examined. INFERENCE: weak-to-moderate.

## B5 MLS group state (RFC 9420, OpenMLS)
Broken: CIRISEdge #604 (https://github.com/CIRISAI/CIRISEdge/issues/604, Sep 15 2026, Rust, MLS): "Two concurrent commits against the same group fork the epoch"; "both committers believe they own N+1; one of them is wrong and its peers will reject its subsequent messages". FACT. Small downstream project; bug unseen because rooms had two parties.
Prove: given a delivery service ordering commits per epoch, all members accepting a commit reach the same epoch secrets and membership, and a member never merges its own commit before acceptance (no unrecoverable fork). Code: OpenMLS group state machine plus application commit handling. Testing does not suffice: forks need concurrent commits across members.
Evidence:
- xmtp/libxmtp PR #4894 (https://github.com/xmtp/libxmtp/pull/4894, Nov 5 2026): "fix(mls): reject membership, proposal and sender attacks that stall or fork groups"; "a committer more than 1000 handshake generations ahead splits from the other members, and readds repair neither side." FACT (production messaging app, Rust core).
- openmls_dart PR #57 (https://github.com/djx-y-z/openmls_dart/pull/57): fork when a committer merges a second commit after the first was accepted; later messages fail AEAD (search summary).
- Phoenix R&D post (https://blog.phnx.im/making-mls-more-decentralized/): commits are not commutative, so members must agree on order (search summary). Known limit of RFC 9420, which relies on a delivery service for ordering.
- openmls/openmls #1412 "External commit returns `MlsGroup` with pending commit" (Jun 2023): relevance unconfirmed.
- Real Rust: OpenMLS, mls-rs (AWS), libxmtp.
Prior work: Scholar blocked.
Gaps/unknowns: no bug found in OpenMLS core; forks are in apps that mis-order commits. "Web messaging" link not established. INFERENCE: property depends on delivery-service assumptions, so the proof target is app+DS, not OpenMLS alone.

## B6 AT Protocol repo/firehose sync
Broken: atproto #4583 (https://github.com/bluesky-social/atproto/issues/4583, Jan 28 2026), title "Relays stopped picking up PDS"; "I was able to write to the PDS via my ATproto account... but the Bluesky relay itself wasn't picking it up."; maintainer bnewbold: "it looks like your account was marked as 'deactivated' on a large number of independent relay instances." FACT. One self-hosted PDS, fixed by migrating to a new PDS.
Prove: a relay or appview following Sync v1.1 ends with the same repo state as the PDS for every non-desynchronized repo, and any gap or invalid commit marks the repo desynchronized rather than silently diverging. Code: indigo relay (Go), rsky (Rust), consumers, MST commit verification. Testing does not suffice: loss, reorder and migration races are timing dependent.
Evidence:
- atproto Sync spec (https://atproto.com/specs/sync): "Any #commit or #sync messages received for a repo which is in desynchronized state are ignored (dropped)." FACT. Dropping is by design; the property to prove is that re-sync eventually restores equality.
- Streamplace PDS "randomly dropped" by the relay, per issue #4583 (search summary).
- jetstream-oxide #15 (https://github.com/videah/jetstream-oxide/issues/15): Rust consumer "impropertly disconnects on receiving throttled or desynchronized account statuses" (title from search).
- Proposal 0006 (https://github.com/bluesky-social/proposals/blob/main/0006-sync-iteration/README.md): "Relays do not perform the re-synchronization process." (search summary quote).
- Real Rust: rsky, jetstream-oxide.
Prior work: Scholar blocked.
Gaps/unknowns: no issue found showing a consumer permanently diverging from the repo; #4583 is operational. indigo/rsky trackers not searched directly.

## Overall (OPINION)
Best evidenced: B2 (CVE, named public rooms, 2026 Rust/Go implementation bugs) and B5 (two 2026 fork bugs, but in apps). B1, B3, B4, B6 had no confirmed 2022-2026 loss/duplication in the engine itself. No Scholar check done for any direction.

---



Notes: Scholar not queried: blocked (CAPTCHA, other agents), per coordinator. Quotes marked [via search tool] came from a search-tool summary, not fetched verbatim; re-check. Two searches (C5 cache keying, PNA) were refused by the tool safety filter and not retried.

## C1 MV3 service-worker termination
Broken: MetaMask MV3 migration: terminating the service worker floods errors and drops messages. https://github.com/MetaMask/metamask-extension/issues/15970 "There have been various causes for this error." and "Even 100+ times from a single service worker restart." (FACT, quoted from the fetch result.)
Prove: Model the extension (SW + content scripts + storage + ports) with nondeterministic SW kill/restart; prove every message either is delivered exactly once or the sender learns of failure, and persisted state is recovered after any restart. Testing can't cover all kill points (timing dependent, kill is browser-controlled).
Evidence:
- Chromium 40733525 (title) "ServiceWorker is shut down every 5 minutes for manifest V3 extension" https://issues.chromium.org/issues/40733525 (page body not fetchable; title only, FACT).
- Chromium 40805401 (title) "MV3 service worker broken after auto-update and manual refresh" https://issues.chromium.org/issues/40805401 (title only).
- mv3-extension.com says Chrome "logs nothing when a message is dropped" [via search tool; paraphrase-risk] https://mv3-extension.com/core-apis-cross-browser-data-management/message-passing-architecture/messages-sent-while-the-worker-is-starting/
- Real Rust implementation: none for browsers' extension runtimes (C++/Rust-free). INFERENCE: verification would target a model/TLA+ of the app protocol, or an extension written in Rust/wasm; weak Rust link.
Prior work: Scholar blocked (CAPTCHA, other agents).
Gaps/unknowns: no verbatim quote from Chromium trackers; unclear that a proof of a user app adds value over a library/pattern; Firefox MV3 uses non-persistent event pages (not checked). OPINION: moderate user impact, weak Rust fit.

## C2 Electron/Tauri IPC permission model
Broken: Tauri 2 origin check accepts attacker pages. https://github.com/tauri-apps/tauri/security/advisories/GHSA-7gmj-67g7-phm9 (CVE-2026-42184, versions >=2.0 <=2.11.0, fixed 2.11.1) "The attacker page can invoke backend commands that the developer intended to be accessible only to the app's own frontend" (FACT, fetch excerpt; ellipsis in original). Also "causes it to incorrectly classify remote URLs as trusted local origins on Windows and Android".
Prove: For Tauri's IPC dispatcher, a command invocation from origin o with capability set C executes only if C grants (command, o, scope args); nothing outside granted scope is read/written (noninterference between ungranted resources and webview output). Testing misses path-canonicalization/origin-parsing edge cases, which is exactly where bugs occur.
Evidence:
- GHSA-57fm-592m-34r7 (CVE-2024-35222) https://github.com/tauri-apps/tauri/security/advisories/GHSA-57fm-592m-34r7 "Remote origin iFrames in Tauri applications can access the Tauri IPC endpoints without being explicitly allowed in the" (FACT, truncated at 125 chars).
- GHSA-q9wv-22m9-vhqh (CVE-2022-41874) https://github.com/tauri-apps/tauri/security/advisories/GHSA-q9wv-22m9-vhqh fs scope partial bypass via path escaping [via search tool].
- GHSA-28m8-9j7v-x499 (CVE-2022-39215) https://github.com/advisories/GHSA-28m8-9j7v-x499 "missing canonicalization when readDir is called recursively" [via search tool].
- Electron context isolation bypass GHSA-h7rp-cf8h-j98x (CVE-2026-70601) https://github.com/electron/electron/security/advisories/GHSA-h7rp-cf8h-j98x ; GHSA-jfqg-hf23-qpw2 (CVE-2026-34780) https://github.com/electron/electron/security/advisories/GHSA-jfqg-hf23-qpw2 (Electron is C++/JS; bugs are engine-boundary, hard to verify).
- Rust: Tauri core is Rust (tauri-apps/tauri). Pentest: https://fossies.org/linux/tauri/audits/Radically_Open_Security-v2-report.pdf
Prior work (changed 2026-11-14, Scholar, 5 queries, snippets only): no paper on Tauri's IPC or capability model. Nearest: "Buzz to Boom: Detecting Message Progression Vulnerabilities in Electron Applications via Segmented Directed Fuzzing" (arXiv 2607.20698, 2026) and CoInDef, "A comprehensive code injection defense for the electron framework" (IEEE S&P 2025): Electron, fuzzing/defense, no proof. Deno: "Welcome to Jurassic park: A comprehensive study of security risks in Deno and its ecosystem" (AlHamdan, Staicu, CISPA 2025), Cage4deno and NatiSand (2023): sandbox studies and extensions, no verification of the permission checks. Verdict: still open.
Gaps/unknowns: the pure-Rust ACL/origin/scope-matching layer is verifiable; webview and OS path semantics are not. Classes of bugs are string/path parsing and origin logic: INFERENCE that these suit Rust verification tools (Kani, Verus) well. OPINION: strongest of C1-C6 for Rust fit and a real recurring CVE class (2022, 2023, 2024, 2026).

## C3 Fetch/CORS/PNA in Servo's net crate
Broken: Servo delivered the body of a response that failed the CORS check. https://github.com/openharmony-rs/servo-ohos/pull/42 "`test_body_of_a_response_that_fails_the_cors_check_is_not_delivered` with all 19 body bytes delivered" and "kept its channel, so its body was still delivered to the consumer." (FACT, fetch excerpts; PR is on a downstream fork, upstream status unchecked.)
Prove: Servo's main_fetch/CORS check refines the Fetch spec's algorithm: a script observes a cross-origin response body/headers only if the CORS check passed (or response is opaque and unreadable). Testing (WPT) is finite; this bug shows state-flow leaks WPT did not catch.
Evidence:
- Servo HTTP cache Vary bug https://github.com/L-K-M/servo/pull/41 (downstream backport of upstream 44deea18cfa): a header counted as matching "when the new request carries it but the stored request did not"; consequence "the CORS check fails." 
- Servo spec-compliance history, e.g. https://github.com/servo/servo/issues/14519 "Allow for redirects after a CORS-preflight" (2016, title).
- Browsers disagree on Local Network Access (successor of PNA): https://bugzilla.mozilla.org/show_bug.cgi?id=2059274 title "Firefox stopped asking to allow Local Network Devices permission for some sites in March 2026 but Chrome allows the access"; https://github.com/WICG/local-network-access/issues/60 (Chrome behavior not covered by spec) [via search tool].
- Rust: Servo components/net (Rust). Chrome/Firefox C++.
Prior work: Scholar blocked (CAPTCHA, other agents).
Gaps/unknowns: Fetch spec is prose with mutable state; formalizing it is itself the large cost. Whether upstream Servo had the body leak is unconfirmed. OPINION: good Rust fit, high effort, class real.

## C4 OAuth refresh-token rotation races (Kanidm)
Broken: Kanidm destroys a legit session when a client's rotated token is lost on a cancelled request. https://github.com/oauth2-proxy/oauth2-proxy/issues/3586 title "a cancelled request loses the rotated refresh token and ends the session"; server log "Attempt to reuse a refresh token detected, destroying session" (FACT, fetched). Server side is Kanidm (Rust); client bug is oauth2-proxy (Go), so the server behaved by design: the design, not code, kills the session.
Prove: Model AS + clients with lost responses/concurrent refreshes; prove (a) a stolen, replayed token is always detected and the session revoked, (b) with a grace/idempotent-retry rule, no honest client following the protocol is logged out. Testing can't enumerate interleavings of retries and lost responses; the trade-off (a) vs (b) is the actual theorem.
Evidence:
- better-auth https://github.com/better-auth/better-auth/issues/8512 "any reuse of a rotated refresh token (even from legitimate clients) logs the user out of that client."
- https://github.com/StellarEdu/StellarEduPay/issues/1529 title "Refresh-token rotation is not atomic — concurrent refreshes race, and multi-tab users trigger false "token reuse" revocations"; both "read valid metadata and **both** mint new refresh tokens".
- https://github.com/OxygnCorp/home-ops/pull/5295 (title "defuse OIDC refresh-token rotation race and harden Kanidm"): multi-pod Envoy races Kanidm [via search tool].
- Kanidm design https://kanidm.github.io/kanidm/stable/developers/designs/oauth2_refresh_tokens.html "when refresh token reuse is detected then all tokens of the session should be canceled" (trimmed). It also asks "is there a concern with the refresh being issued but a slight delay before it's recorded?" (FACT: author flagged the exact race).
- Rust: Kanidm, Rauthy (Rauthy not examined). Go: Hydra, Zitadel.
Prior work: Scholar blocked (CAPTCHA, other agents).
Gaps/unknowns: no Kanidm server-side bug filed that I found, only client/deployment consequences. OPINION: clean, small, realistic distributed-state theorem with user-visible logouts; the BCP's own "(a) vs (b)" tension makes it novel to state formally.

## C5 HTTP cache keying (RFC 9111)
Broken: Servo's HTTP cache served a response stored for a request without Origin to a request with Origin (Vary mismatch). https://github.com/L-K-M/servo/pull/41 "when the new request carries it but the stored request did not" (FACT). This is a cache-key correctness bug, benign here (a CORS failure) but the same shape yields cross-user serving.
Prove: The cache returns a stored response r for request q only if r's Vary-nominated request headers equal q's (RFC 9111 4.1), plus partition key equal; hence responses keyed to user A (via Cookie/Authorization/Vary) are never served to B. Testing: cache-tests.fyi covers many cases but not interleavings of revalidation and replacement.
Evidence:
- Spec ambiguity: https://github.com/httpwg/http-core/issues/1109 "Caching: Vary, Conneg, and choosing the latest response" (title); RFC 9111 allows reuse with mismatched Vary if revalidated, and Chrome/Firefox send ETags from mismatched responses per https://danburzo.ro/http-caching-refresher/ [via search tool].
- https://github.com/whatwg/fetch/issues/1770 "redirects and etag/if-none-match" (title); 304 behavior "inconsistent among browsers" [via search tool].
- Cache-deception CVEs: not found (search refused); no CVE evidence here.
- Rust: Servo net http_cache; also hyper/pingora caches (not examined).
Prior work: Scholar blocked (CAPTCHA, other agents).
Gaps/unknowns: no user-visible cross-user leak in a browser cache confirmed. OPINION: weak as a standalone; modest extension of C3 (substitute framing: Servo http_cache refinement of RFC 9111).

## C6 Push subscription liveness
Broken: Server keeps dead Web Push subscriptions because the browser event carries no identity of the old one. https://bugzilla.mozilla.org/show_bug.cgi?id=1223202 title "Only send subscription change events if the Push permission is granted" and, per search summary, Firefox fired the event before deleting the old record (racy). Spec: https://github.com/w3c/push-api/issues/325 "pushsubscriptionchange event doesn't have oldSubscription in it." (title, FACT).
Prove: Client+push-service+app-server protocol (renew, change event, 404/410 prune) guarantees eventually the server's live set equals the client's live set, no duplicates, even with lost events. Testing cannot trigger the event on real workers (brain-kit #2568 notes no automation API fires it [via search tool]).
Evidence:
- https://github.com/OneUptime/oneuptime/pull/4558 service worker resubscribed with applicationServerKey: null, so devices "kept the dead subscription" [via search tool].
- FCM: https://firebase.google.com/docs/cloud-messaging/manage-tokens "invalid token response if a token for an Android device has expired after 270 days of inactivity" [via search tool]; one blog claims 8-10% monthly rotation (unverified).
- Rust: web-push crate, push servers (autopush is Rust/Python; not verified).
Prior work: Scholar blocked (CAPTCHA, other agents).
Gaps/unknowns: mostly app-level bugs; browser-side behavior closed. OPINION: protocol is simple, bugs are mundane; limited research novelty.

## Ranking (OPINION)
C2 > C4 > C3 > C1 > C6 > C5. C2 and C4 have Rust implementations and recurring real failures; C5 evidence is thin.
