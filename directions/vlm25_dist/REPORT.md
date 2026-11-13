# Distributed-systems problems on the web worth formally verifying

(authored by agents unless marked 🧑)

Task (manager, quoting human): "We are lacking some of the distributed system stuff. That we may be able to do. That may be more interesting and niche."

## The common pattern (why first)

Every top pick has the same shape. One party makes a decision, such as "revoke consent", "log out", "purge this page" or "rotate this token". Many independent parties must then act on it, over channels that lose, delay or reorder messages. The specs promise only best-effort delivery ("SHOULD", "MAY"). The parties that must act run on servers nobody outside can see. So:
- safety: nobody acts on the old decision more than Δ after the new one (Δ is a bounded delay)
- liveness: every party eventually learns the new decision
- measurement can show a violation exists, but it cannot show the absence of violations, because the interesting state sits on other machines and in rare interleavings. A model checker covers both gaps.

Opinion: these fit the human's existing skills directly (TLA+/Verus liveness under fairness). For all four, the searches found no formal model of the propagation property. Caveat: Google Scholar was not queried, so "none found" is weak.

## 1. Consent revocation reaching ad vendors (privacy niche)

Who is hurt: users who click "withdraw consent" are still tracked. Kancherla et al., PoPETs 2025 (https://arxiv.org/abs/2411.15414): "on 101 websites, third parties that have received consent upon user's acceptance, are not informed of revocation, leading to the illegal processing of users' data by such third parties" (out of 281 websites using IAB TCF, a standard consent-string format passed to ad vendors). They also admit the limit: "As the third-party notification happens server-side, this may result in some false-positives on our end." US side (https://arxiv.org/html/2611.02014v1): "82.7% of the advertisers in our dataset are never sent a USP or GPP String".
Why distributed: the "no" rides on whatever request the browser sends next. If a vendor never gets another request, it never learns of the revocation. Auctions also forward the consent string to vendors the site never listed.
Prove (TLA+): safety (no vendor processes data later than Δ after revocation), and liveness (every vendor told "yes" is eventually told "no"). I expect the protocol as written to fail liveness. The result would be which fix (consent TTL, push, re-signal) gives which Δ.
Prior: Pardo and Le Métayer, "Model-Checking the Implementation of Consent", TLA+ (https://arxiv.org/abs/2409.11803). It models a single controller, not multi-vendor propagation, though that judgment comes from the abstract only.
First step: a roughly 100-line TLA+ spec with 1 user, 1 consent manager and 3 vendors. Have TLC reproduce the "101 websites" failure as a counterexample.

## 2. CDN purge consistency across edge and shield caches (cache niche)

Who is hurt: users get stale pages after a fix, or another user's private page. Fastly's own docs (https://www.fastly.com/documentation/guides/concepts/cache/stale/) say that after a soft purge "the Shield POP marks its local cache entry as stale but continues to serve it", and an edge "may misinterpret the response headers and cache the stale data with a fresh TTL." Fastly blog: "If you purge Fastly before the upstream server has updated, we might just pull the old version of the content and re-cache it." Their advice is to "just purge twice." Railway incident 2026-03-30 (https://blog.railway.com/p/incident-report-march-30-2026-authenticated-user-data-cached): "cached responses may have been served to users other than the original requester".
Why distributed: purge messages, origin updates and in-flight refills between tiers race with each other. Meta on its own caches (https://engineering.fb.com/2022/06/08/core-infra/cache-made-consistent/): "The bug hides in the error handling code behind interleaving operations and transient errors." Meta measures violations, with no formal methods.
Prove (TLA+ to find bugs, Ivy for any number of POPs, i.e. edge sites): bounded staleness after a purge, plus "never give a fresh TTL to a copy from a stale source".
Prior: none found for CDN purge. The nearest work is hardware cache coherence, which has no TTLs and no origin.
First step: a TLA+ model with 1 edge, 1 shield and 1 origin. TLC should rediscover Fastly's documented race, and the documented fix should remove it.

## 3. Logout and token revocation across identity-provider apps (OAuth/OpenID)

Who is hurt: a user whose Google or Facebook account was hijacked cannot end the attacker's sessions at the apps where they "logged in with" it. Ghasemisharif et al., USENIX Security 2018 (https://www.usenix.org/system/files/conference/usenixsecurity18/sec18-ghasemisharif_0.pdf), 95 services: "most services lack the functionality that would allow users to remediate an account takeover".
Why distributed: the logout signal is one-shot by spec. OIDC Back-Channel Logout (https://openid.net/specs/openid-connect-backchannel-1_0.html) says the provider "SHOULD NOT retransmit", and how the app ends the session "is implementation specific." RFC 7009 says revocation "takes place immediately", yet the same RFC admits "a propagation delay, for example, in which some servers know about the invalidation while others do not." That is a contradiction a model can exhibit.
Prove (TLA+; Ivy for any number of apps): after logout, no app accepts the session past Δ, and Δ is a function of retry policy and token lifetime. Also check a login racing an in-flight logout.
Prior: Fett et al.'s formal analysis of OIDC (https://arxiv.org/abs/1704.08539) says outright: "We do not model less used features, in particular OIDC logout", and it never lets tokens expire. I found no formal work on delivery of the newer revocation-event standard (CAEP/Shared Signals).
First step: a TLA+ spec with 1 provider, 2 apps and a lossy one-shot logout message. It is the most tractable of the four. Weakness: the harm evidence is from 2018.

## 4. Tabs and service workers in one browser fighting over shared state

Who is hurt: users randomly logged out, or apps crashing after a deploy. Rotating refresh tokens (each use issues a new one, and reuse of an old one makes the server revoke them all) break with two tabs. From https://github.com/johannesjahn/chat-platform/issues/650: "having two active tabs can randomly log someone out about every 15 minutes." From https://github.com/soliplex/frontend/issues/670: "The IdP then revokes the whole token family, and the session dies in every tab." Service-worker update, from https://github.com/schlessera/brain-kit/issues/2569: "a new service worker activates under a busy page and deletes the lazy chunks it still needs".
Why distributed: tabs are separate processes that share only asynchronous storage and message channels (localStorage, BroadcastChannel, Web Locks), and they talk to a server that does its own reuse detection. Neither side alone can prevent a false logout. The bugs depend on tab suspend, crash and timing, which tests sample poorly.
Prove (TLA+, then maybe Verus on a real client library): at most one refresh in flight; no spurious revocation; some live tab eventually holds a valid token; a page's assets are not deleted while the page is alive.
Prior: none found for Web Locks, BroadcastChannel or the service-worker lifecycle. The nearest is a TLA+ model of a single-page app (https://arxiv.org/pdf/2005.05627).
First step: TLA+ with 2 tabs and 1 server. TLC should reproduce issue 650's logout trace, then check the lock-plus-grace-window fix.
Caveat (opinion): this is the most niche, but the evidence is small projects' issue trackers, not studies.

## Runners-up and rejects (one line each)

- Bluesky AT Protocol sync and deletion: no formal work found, and real gaps exist ("It is not the responsibility of a PDS, or a relay, to proactively detect if downstream consumers have gotten out of sync.", https://github.com/bluesky-social/proposals/blob/main/0006-sync-iteration/README.md). But the spec is still changing.
- Automerge/Yjs sync protocol, beyond the human's OT work: a real bug where both sides think they are synced but differ (https://github.com/automerge/automerge/issues/870). The CRDT field is crowded.
- Certificate Transparency witnesses: a clean crash-recovery model, but no exploit found and some prior formal work exists (probabilistic model checking of gossip).
- Rejected: cookie syncing (it leaks by design, so a proof restates the known), web push (the spec permits loss), DNS TTL (crowded: GRoot and others), payments (well understood), AI-agent sessions (blog-only evidence).

## Evidence notes

- Sources and full quotes: notes_privacy.md, notes_infra.md, notes_browser.md in this directory.
- Some quotes came through a summarizing fetch tool. Of those used above, these were not re-read at the source: the Back-Channel Logout and RFC 7009 wording. Re-check them before any external use.
- Google Scholar was not used, so prior-work gaps may be wrong.
