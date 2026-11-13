## Nov 3–9: web things to formally verify
(authored by agents unless marked 🧑)

- [Last week](#last-week)
- [General directions: kept and dropped](#general-directions-kept-and-dropped)
- [Biggest problems in finding directions](#biggest-problems-in-finding-directions)
- [Detailed directions](#detailed-directions)
  - [1. Agent browser core on Servo, many sessions in one process](#1-agent-browser-core-on-servo-many-sessions-in-one-process)
  - [2. SSO: signed out exactly when you sign out](#2-sso-signed-out-exactly-when-you-sign-out)
  - [3. Collaborative editors: sync that provably ends up identical](#3-collaborative-editors-sync-that-provably-ends-up-identical)
- [Brief directions](#brief-directions)
- [Next steps and questions](#next-steps-and-questions)

By "formally verify" I mean proving with a tool (Verus for Rust code, TLA+ for protocol models) that code or a protocol meets a precise rule for every input and every ordering of events, not just the ones tests try.

### Last week

**On Nov 3 you asked me to pick something about the web to verify, because that is where our group has data and intuition.** In your words: "are there tools and techniques for verifying aspects of the web? Maybe JavaScript, maybe something else." You also asked for:

- a differentiator: "a lot of people are jumping onto the space, you need to have some differentiator"
- bite-sized problems: "You can define 10 different verification problems bite-sized problems and make slow headway"
- a list from real breakage: "Write down 10 different things that you might like to verify ... what are the problems that happen in the real world"
- tools to build on: "find out ... what tools there exist that you can use and build upon"

This week I went through about 30 candidates: 8 general directions, 21 rough ideas, and a few more from a search focused on verification. I kept three, which I describe in detail below.

### General directions: kept and dropped

**I kept two of the original eight directions and added two new ones; the rest I dropped, mostly because we cannot change the parties involved or because formal verification adds little.**

Kept:

- **Agent browsers sharing one process** (with process isolation folded in): one small verified core that every request passes through, so many users' sessions can share one browser process safely. Detailed below.
- **SSO sign-in/sign-out** (new): a distributed-systems problem where we can build and verify our own login provider. Detailed below.
- **Collaborative-editor sync** (new): distributed, in Rust, with real bugs. Detailed below.
- **JavaScript engines vs the language spec**, at low priority: you may find it too PL (my worry about the advisors' view). Bugs we found in the small Rust engines (e.g. a use-after-free in Boa's garbage collector) don't matter much. Boa is "kind of like a toy project, it's not even a JIT", and lots of bugs in V8 "would be big". So it only counts if a result from a Rust engine maps back to V8. There is precedent: EPFL's verified regex work found algorithm bugs, and some of their fixes were "merged in the V8 JavaScript implementation used in Chrome" ([PLDI 2024](https://arxiv.org/abs/2311.17620)).

Dropped:

- **Cookie consent**: not ready to share yet.
- **Shared caches and CDNs**: they feel a little remote from what we were previously doing. Purges reaching every edge server (a later distributed version of this idea): you asked why it hasn't been done, as with TLS revocation. [agents' read] Expiry bounds staleness anyway, so a proof of the purge path adds little; a Google Scholar search found no formal model of CDN purge (CDNs still sell instant purge as a feature, so this is weaker than for TLS). For TLS the CA/Browser Forum is cutting certificate lifetimes to 47 days because revocation lists "do not adequately protect relying parties" ([SC-081v3, 2025](https://cabforum.org/2025/04/11/ballot-sc081v3-introduce-schedule-of-reducing-validity-and-data-reuse-periods/)).
- **Web archive replay**: archives rewrite a page's JavaScript so it fetches saved copies, and about 9% of pages still replay wrongly (FidEx, NSDI 2026). A checker that proves each rewrite is correct needs JavaScript semantics, while our tools are verified Rust, and I don't see a huge gain.
- **Third-party page scripts**: proving a script can't read a card field before it loads. To me it sounds like a virus check, and I don't see what it has to do with formal verification. [agents' read] Most of the value would come from an analyzer that works without the proof, and the proof needs a JavaScript model.
- **HTTP parser disagreements** (request smuggling): skipped. A later version (proxy and server agreeing on where a request ends) fell under the "reaction to single bugs" problem below.

### Biggest problems in finding directions

**The hardest part has not been finding things that break; it has been finding things where a proof is the point and the result is big enough for a paper.** The problems I kept hitting:

1. **Many ideas are reactions to single bugs.** "This library had bug X, so let's verify the piece that had X" is too small for an entire research paper. HTTP/2 flow control was the clearest case: there are real 2026 deadlocks in Cloudflare's Pingora and in the Rust h2 library, but it is still one bug class in one component.
2. **Often the formal verification is decoration.** Many ideas are really a measurement or an analyzer with a proof attached. A critic agent that judged "is the proof the contribution?" cut most of a verification-focused candidate search on exactly this. For each idea we now require the exact statement we'd prove, why testing can't settle it, and the tool.
3. **Things on the hot path would already be found if broken.** If something runs on every page load in every browser and has no known bugs, then if it really had a problem, someone would probably have found it. Example: restoring pages from the back/forward cache.
4. **Much of the web needs JavaScript semantics, while our strength is verified Rust.** Archives, page scripts, and anything about a site's own code need a model of JavaScript. That is a big PL project, and possibly too PL for this group. Maybe we do need to handle JavaScript semantics at some point. For now I prefer targets written in Rust (Servo, Rust login providers, Automerge).
5. **We can't change the big players.** Google's login, IAB's consent standard, and commercial CDNs are out of our hands, so anything that requires them to adopt it is just a proposal. That is why SSO only works because we can build our own provider.
6. **"Why hasn't it been done?" often has a boring answer.** [agents' read] For TLS revocation the industry chose short-lived certificates over guaranteed delivery, and CDN purge looks similar because TTLs bound staleness, so a proof of the delivery path adds little.
7. **Ideas without a point.** Early on, many ideas had a huge lack of relationship to formal verification, and no clear "why". For every direction below I start with why.

### Detailed directions

#### 1. Agent browser core on Servo, many sessions in one process

**Why: a browser where many users share one process is cheap, but only safe if we can prove one session can never see another's data.** This is my idea from our Nov 3 meeting: "if we run two tabs in a single process ... Leak information, or steal information from each other. And if we could actually guarantee that the two tabs would be ... separated. Even within a single process. We can just use one process ... look at Chrome, every tab is, like, 300 megabytes." AI agents now browse for people, and agent browsers already put many sessions in one process to cut cost. Lightpanda, an agent browser built for bots, had 9 of its 11 security advisories in the rule-checking layer in 6 months (May–Nov 2026), e.g. "Credential headers leak across cross-origin redirects". We also reproduced (not reported) that its URL blocklist does not apply to WebSockets.

**What we'd prove:** many sessions share one process, and one session can never read another's data or send it where the URL, cookie and redirect rules forbid. The main assumption is that the JavaScript engine doesn't corrupt memory (the advisors' on-the-fly JavaScript verification would relax it). Servo, the browser engine written in Rust, is the easiest starting point. One of you noted this would also need "on-the-fly verification of the JavaScript code on the page you're loading", and another called that "really novel".

**Why proof, not testing:** Lightpanda's bugs surfaced as separate advisories. The rules (WHATWG URL, cookies, Fetch) are precise but full of corner cases, and tests only cover cases someone thought of.

**What is hard, and what would be the contribution [agents' read]:**

- the hard part is proving nothing goes around the core: fetch, redirects, WebSockets, workers, caches, storage. Lightpanda's WebSocket bug is exactly a path around the check, not a wrong check. Proving the URL/cookie functions correct is the easy part
- writing the standards as machine-checked specs is real work, and a wrong spec makes the proof meaningless
- every cache and store must be keyed by session, and a memory bug in Servo's C++ JavaScript engine (SpiderMonkey) can still break that
- the contribution would be making "everything goes through the core" provable in a real browser, e.g. by restructuring Servo so a network or storage access that skips the core can't be written. That is what makes it more than a verified proxy. The closest prior work, Quark (2012), verified a browser core with one process per tab, long before agents.

**Open:** whether reviewers see enough beyond Quark, and how much of Servo would have to change.

#### 2. SSO: signed out exactly when you sign out

**Why: with single sign-on, whether you are signed in should be one fact, but it is copied across your tabs, every app and the login provider, and the copies drift.** So you get signed out when you didn't ask, and stay signed in somewhere after you did ask. The second matters after an account hijack. The story we'd prove [agents' wording]: you are signed out everywhere exactly when you sign out, never before, never too late.

**The evidence is recent.** After the login provider revoked access, "only 8 RPs actually exhibited the logged out behavior" and "318 RPs continued accepting cookies 10 days after revocation" (RP = an app that accepts the SSO login; [Ghasemisharif and Kanich, IEEE S&P 2022](https://par.nsf.gov/servlets/purl/10339713)). Random sign-outs come from refresh-token rotation: two tabs refresh at once, one sends a just-invalidated token, and the server treats it as theft and kills the session. A 2026 paper calls concurrent refresh "the default behaviour of retrying mobile clients and multi-tab browsers" ([NEBULA, arXiv 2608.04115](https://arxiv.org/abs/2608.04115)). Vendors patch it with timing windows (Okta allows 30 s). We found no study measuring how often it happens. The standards promise only best effort: the logout standard says the provider "SHOULD NOT retransmit" a lost logout message (spec quotes came through a summarizing tool; to re-check).

**Why proof, not testing:** one decision (sign out, revoke) must reach many independent parties over messages that can be lost or delayed, while sign-ins race with it. The bad cases are rare timings.

**What we'd prove:** after sign-out, no app accepts the session for more than a bound Δ (safety); every app eventually learns (liveness); a sign-in racing a sign-out can't leave a zombie session; concurrent refreshes never kill a valid session. First a TLA+ model of what the standards can and can't guarantee, then verified Rust for parts we own. We don't need Google: we can make our own SSO provider. Kanidm, a Rust provider, has no back-channel logout at all, so a verified one would be new as far as we found. Apps and browsers are assumptions.

**Where the idea came from:** I noted we lacked distributed-systems angles. An agent then searched for web problems where one decision must reach many parties, and its sources for this one were the OpenID Connect logout standard and a 2018 study.

**Open:** the main formal model of OpenID Connect says "We do not model less used features, in particular OIDC logout" (Fett et al. 2017), and a Google Scholar search found no formal work on logout or revocation propagation. Three items found but not yet read could change that.

#### 3. Collaborative editors: sync that provably ends up identical

**Why: when people edit a shared document offline and reconnect, their copies must end up identical, and the part that breaks is the sync protocol, which we found no one has verified on real code.** The merge rules (CRDTs, data types designed so concurrent edits merge to the same result) have machine-checked proofs. Sync protocols decide which messages each side still needs to send, and those have, as far as we found, only paper proofs or small TLA+ models (from Google Scholar snippets; the 3 closest papers are not read in full yet).

**Real sync bugs exist:** Automerge's sync loops forever after a lost message ([#772](https://github.com/automerge/automerge/issues/772), 2023; [#1284](https://github.com/automerge/automerge/issues/1284), 2026; both open). Loro, a newer library, silently diverges (#1215, #1040, 2026, open). We have not run these.

**Why proof, not testing:** the failures depend on lost, duplicated and reordered messages. Random testing finds an ordering by luck; only a proof covers all of them. Waiting doesn't help either: unlike a stale cache, two copies that diverged stay diverged.

**What we'd prove:** in verified Rust (Automerge's core is Rust), if both sides say "in sync", their documents are identical (safety), and if the network eventually delivers messages, they reach "in sync" (liveness). It also links to TeamTypeV, a forked collaborative editor where agents wrote Verus proofs of its edit-merging (OT) logic, position conversion and protocol bookkeeping; Automerge sync and networking were assumed, not verified. This direction fills that gap.

**Open:** novelty against Blau 2020 (Isabelle), Nieto et al. 2022 (Coq) and Zhang et al. 2024 (TLA+).

### Brief directions

**Kept for mention:**

- **Clicks spent once, across processes, in Servo**: browsers allow popups, clipboard writes and fullscreen only right after a click, and a click used in one frame must be used up in all frames of the page. Servo's own code admits it doesn't do this across processes: "This wouldn't work if top level document is in another ScriptThread." It's a small distributed protocol in Rust, but too small alone unless it is part of a bigger story.
- **Proofs that expire with "web atoms"** (groups of URLs that change together): important for archives and for agents reusing offline knowledge, but it is a web-agents direction with no formal verification, so it is not part of this line.

**Left out or discarded:**

- keeping an AI agent's sites apart (text from site A can't steer actions on site B): simply impossible to prove
- back button can't revive a logged-out state: on the hot path, no bug evidence
- CDN purge reaching every cache: sidestepped by expiry (see above)
- which sites a cookie may be shared with (the Public Suffix List): too niche, unclear value
- HTTP/2 connections that can't deadlock, HTTP/1.1 framing agreement: reactions to single bugs, too small
- not yet discussed, at most one line each: a permission check behind every powerful action, the agent's view of a page matching the human's, "clear site data" really erasing, Storage Access API consistency, extension permissions, side-channel leak budgets for shared processes, checking JIT output per tenant, federated social network deletes, certificate transparency logs not forking, Encrypted Client Hello fallback, ad-blocker rule compilation, Chrome's ad-measurement privacy budget, bounce-tracking cleanup, invisible measurement shims, a re-registered domain inheriting nothing from the old owner

### Next steps and questions

[proposed, Sichang to confirm]

- read the closest prior work for SSO and CRDT sync before claiming novelty
- pick one bite-sized first piece per kept direction, e.g. a TLA+ model of back-channel logout, or the Automerge sync handshake in Verus

Questions for you [proposed, Sichang to confirm]:

1. Which of the three is the strongest "web verification" story for this group?
2. Is the agent-browser core enough beyond Quark (2012), or does it read as a verified proxy?
3. Should we eventually take on JavaScript semantics, or stay with targets written in Rust?
