# Replicated-state verification targets and users reached
(authored by agents unless marked 🧑)

Task (🧑, relayed by manager): "We don't have to be fixated on matrix. We have other alternatives. Have agents search for them. Also, how big would the community be? Basically, if we formally verify something, how many users would we have?"

Method and reliability. Four agents searched on 2026-11-13. Crates.io, npm and GitHub numbers come from their APIs (FACT). Quotes marked (S) are search-engine summaries, not text read from the page: treat their wording as unverified. Unmarked quotes were read from the page or are issue titles. Google Scholar returned a CAPTCHA on the first query; the agent stopped. Prior verification work is therefore not covered ("Scholar blocked"). Raw notes: /tmp/vlm50.2EBm/{fed,crdt,sync}.md (temporary).

Key distinction. "Protocol users" = people using any implementation of the protocol or product. "Rust users" = people whose state is actually computed by the Rust code we would verify. Only the second is reached by a verified Rust implementation. For most candidates it is much smaller, or unknown.

Takeaway. No candidate has both a large, sourced Rust user count and a documented divergence bug class. Firefox's bookmark merger comes closest: it is Rust code shipped to every Firefox user who turns on Sync, and it has a long history of bookmark loss. Matrix has the cleanest documented divergence bugs, but its Rust code reaches an unknown share of about 1M monthly users.

## 1. Firefox Sync bookmark merger (dogear, Rust)
- Failures: https://bugzilla.mozilla.org/show_bug.cgi?id=621584 "[meta] Bookmarks dataloss (duplicated, reordered, moved, lost, attributes changed, etc) caused by Sync" (old, JavaScript era; this history motivated the Rust merger). Rust era: bug 1530145 "Record telemetry for possible sync loops caused by the Rust merger", (S) "where the devices keep reuploading the same records, even though they haven't changed locally"; no confirmed incident found.
- Rust: mozilla/dogear, shipped on desktop (bug 1482608 "Ship a Rust bookmark merger on Desktop"), also in application-services for mobile.
- Protocol users: Firefox 203,426,928 MAU, June 2026 (S, summary of data.firefox.com; page not opened).
- Rust users: Firefox users with Sync on. Mozilla publishes no count; aggregator claims ("more than 22 million active users") are unsourced. I don't know.
- Prove: bookmark trees on all devices converge to one valid tree with no live entry dropped.

## 2. Signal (libsignal, Rust)
- Rust users: all Signal clients share libsignal (INFERENCE from my knowledge, not sourced here). Signal: "70-100 million" MAU, Whittaker to NZZ, April 2025 (S).
- Failures: no sync or divergence failure found (not searched in depth). The verifiable surface is mostly cryptography, which is already well studied, rather than replicated state. Weak fit for the story.

## 3. Bitwarden (Rust SDK, sdk-internal)
- Protocol users: "more than 15 million users and 80,000 businesses" (S, press release 2026-07-28).
- Rust users: 2026 clients moved to a Rust/WASM core (bex.co blog 2026-08-06), so INFERENCE: most new clients. Exact share: I don't know.
- Failures: https://github.com/bitwarden/server/issues/332 "\"Sync Vault\" does not really sync. Possible data loss". 2026 bugs are parse failures that showed an empty vault (clients #23540), not merge bugs.
- Fit: the server is authoritative and the last write wins, so there is little convergence logic to verify. Weak.

## 4. Matrix room state resolution (ruma-state-res; matrix-rust-sdk)
- Failures: Project Hydra post https://matrix.org/blog/2025/08/project-hydra-improving-state-res/: "This fixes state resets observed in public rooms including: #rust, the Office of the Matrix.org Foundation, the TWIM room"; symptoms "users being re-added into a room they have left". CVE-2025-49090. Follow-up: matrix-spec issue #2447 "Bug in v2.1 state resolution causes apparent state rollback" (state: closed; resolution not read). gomatrixserverlib #471 (2026-11-08): "State resolution v2.1 drops conflicted events and panics for room version 12".
- Rust: ruma 1,384,929 crates.io downloads; ruma-state-res 138,096; matrix-sdk 961,635 (used by Element X); servers Conduit, continuwuity, tuwunel.
- Protocol users: arathorn (Matrix project lead), Lobsters 2025-06-16 (S): "there are 1.04M monthly actives based on synapse phonehome stats on the network and 389K on matrix.org". Government networks (BwMessenger "100K+", Tchap ~350K active, both (S)) are private; the Hydra post says they were unaffected.
- Rust users: servers running Rust homeservers: I don't know. Element X MAU: I don't know.

## 5. Bluesky / AT Protocol (rsky, Rust)
- Failures: atproto #4583: an account was wrongly "marked as 'deactivated' on a large number of independent relay instances". rsky #278 "AppView has stale identity data for an account migrated to another PDS" (S).
- Protocol users: about 47M registered accounts (S, Wikipedia, 2026-10). Bluesky publishes no active-user count; third-party estimate ~3M mobile DAU (S, TechCrunch citing Similarweb, July 2026).
- Rust users: only Blacksky runs rsky; its user count: I don't know. Nearly all users are on the TypeScript reference stack.

## 6. Collaborative editing: CRDT libraries
- Yjs/Yrs: yjs (JavaScript, not Rust) 15,618,798 npm downloads per week; yrs (Rust) 4,820,080 crates.io downloads total. End users mostly run JavaScript Yjs. Failures in yrs are crashes on bad input: y-crdt #733 "apply_update panics ... on a well-decoded but malformed WeakLink update". No divergence report found.
- Automerge and Loro: npm packages wrap the Rust core as WASM, so every npm user runs Rust. Weekly npm downloads: @automerge/automerge 119,957, loro-crdt 260,697. Failures: automerge PR #342 "duplicate changes in the queue could corrupt internal state"; loro #907 "`forkAt` inside subscription during `checkout` event corrupts document state". End-user product counts: I don't know.
- Zed: Rust editor with its own CRDT. "hundreds of thousands of daily developers" (S, unverified); share that uses collaboration: I don't know. No divergence bug found.
- AFFiNE: "200K+ Pro users" (S); Rust y-octo runs on native clients and the server, while the web client uses Yjs. Rust share: I don't know.

## 7. Smaller or unknown
- Lemmy (Rust ActivityPub): 26K-32K MAU (S, FediDB and fedistats). Failures: Lemmy #3588 "Lemmy 0.18.2 instances are not federating deletion of a post by user who created post". The fediverse overall has about 1.2-1.6M MAU, mostly Mastodon (Ruby).
- MLS (OpenMLS): the only confirmed production user is Wire, user count unknown. Discord's DAVE uses C++ (Cisco mlspp), not OpenMLS.
- PowerSync (Rust core in all its SDKs), iroh-docs, Atuin, Delta Chat (Rust core), 1Password (closed source): no user counts found.
- Nostr: most-downloaded Rust crates (nostr-sdk 1,941,888) but relays are independent stores with no shared state to converge. Not a fit.

## Ranking by users reached by the Rust implementation (INFERENCE where noted)
1. Firefox bookmark merger: up to 203M Firefox MAU; the real number is Sync-enabled users, which I don't know
2. Signal libsignal: 70-100M MAU (S), but a weak fit (no replicated-state bugs found)
3. Bitwarden SDK: up to 15M users (S); share running Rust: I don't know; weak fit
4. Matrix: protocol about 1M MAU (S); Rust share: I don't know
5. Automerge/Loro, Zed, AFFiNE: unknown; download counts only
6. Bluesky via rsky, Lemmy (~30K MAU), OpenMLS: small or unknown

If both fit and reach matter, INFERENCE: Firefox bookmark sync first, Matrix second. Matrix has better documented, recent divergence bugs; Firefox reaches more users.
