# Infra candidates for formal verification: CDN purge, CT logs, DNS, web push

(authored by agents unless marked 🧑)

Method note: web-reading tool returned only short excerpts (under about 125 chars), so quotes are partial but verbatim. Google Scholar was not used. Nothing was run or published. Items marked OPINION are mine; items marked UNVERIFIED came from search summaries I did not confirm on the source page.

## Ranking (OPINION)

1. CDN purge with shielding and stale-while-revalidate (strongest: documented live bug class, no formal work found, small model).
2. CT witness cosigning on Static CT (good, but prior formal work exists and the safety property is mostly crypto plus monotonicity).
3. DNS TTL / ghost domain / serve-stale (formal work exists for zone files and end-to-end resolution; cache-time liveness less covered).
4. Web push (spec is deliberately weak; little to prove beyond a lossy-queue model).

## 1. CDN cache invalidation, purge consistency, tiered cache, SWR

### Who is hurt, with sources

Users get stale code or another user's private page.

- Fastly docs describe a shield/edge race after soft purge.
  - URL: https://www.fastly.com/documentation/guides/concepts/cache/stale/
  - Quote: "the Shield POP marks its local cache entry as stale but continues to serve it"
  - Quote: "it may misinterpret the response headers and cache the stale data with a fresh TTL."
  - Quote (mitigation): "disabling the use of stale content for asynchronous revalidation when a POP is acting as a shield."
- Fastly's own purge blog admits a purge/refill race and gives no formal guarantee.
  - URL: https://www.fastly.com/blog/is-purging-still-the-hardest-problem-in-computer-science
  - Quote: "If you purge Fastly before the upstream server has updated, we might just pull the old version of the content and re-cache it."
  - Quote: "the purged POPs might re-cache from the shield cache."
  - Quote: "every Fastly POP in the world should be done in around 150ms. It's almost always complete within 250ms."
  - Quote: "just purge twice."
  - Fact: the article says purge-all works by "increasing the cache version number" and "takes up to 1 minute to complete".
- Real stale-after-deploy in production, 2026-11-06 (a user's repo, so anecdotal).
  - URL: https://github.com/mitodl/ol-concourse/pull/154
  - Quote: "at 17:51 UTC a news page still returned the pre-deploy HTML with `x-cache: MISS, HIT`, `age: 57361`"
  - Quote: Fastly "treats the header's presence, not its value, as the soft flag"
  - Quote (author's uncertainty): "I have not confirmed it against Fastly logs."
  - Inference: a config bug, not a protocol bug; but it shows soft purge plus SWR plus shielding is hard to reason about even for operators.
- Private content served to other users (safety violation, not just staleness).
  - Railway, 2026-03-30. URL: https://blog.railway.com/p/incident-report-march-30-2026-authenticated-user-data-cached
    - Quote: "On March 30, 2026 between 10:42 UTC and 11:34 UTC (52 minutes)"
    - Quote: "cached responses may have been served to users other than the original requester"
    - Quote: "accidentally enabled caching on domains that had it disabled."
    - Quote: "The change was fully reverted and all cached assets were purged globally."
    - Quote (remediation): "Aggressive shard-ing of CDN rollouts over hours as opposed to minutes"
  - Bunny CDN, June 2023. URL: https://httptoolkit.com/blog/bunny-cdn-caching-vulnerability/
    - Quote: "private HTTP responses intended for one authenticated user could be served to other users instead"
    - Quote: "ignores the mismatched Authorization headers, and serves the private data straight back up to the wrong person."
    - Quote (vendor): skipping the cache would "open up a potentially worse vector of complete downtime and financial loss for any client"
  - Zulip 2021-03-20 (CloudFront request collapsing), Klarna 2021-05-27, Steam 2015-12-25, Loom 2023-03-07: listed at https://github.com/0xdabbad00/security_incidents_from_caching
    - Quote: Zulip note: "Result of Cloudfront request collapsing"
    - Quote: Steam note: "Cache change was made in response to a DDoS, which caused a different problem"

### Why it is a distributed-systems property

- Safety S1 (privacy): a response generated for request context A is never served to context B. Depends on cache key, Vary, request collapsing, and Cache-Control.
- Safety S2 (purge): after a purge completes at time t, no POP serves an object fetched from origin before t beyond a bounded window (bounded staleness), including through shields and SWR refills.
- Liveness L: every purge eventually reaches every POP, and a POP does not re-cache a stale copy from a peer with a fresh TTL.
- Fact: S2 can fail through the Fastly race quoted above (stale copy gets "a fresh TTL").
- Inference: S2 is an ordering property between purge messages, origin updates, and in-flight refills, like the Meta race below.

### Why testing/measurement cannot settle it

- Meta describes the same class for its own caches, URL: https://engineering.fb.com/2022/06/08/core-infra/cache-made-consistent/
  - Quote: "The bug hides in the error handling code behind interleaving operations and transient errors."
  - Quote: the bug fires "only when all steps above occur and happen specifically in this sequence."
  - Quote: "it's almost impractical to log and trace every cache state change."
  - Quote: "Polaris focuses on measuring the violations of client-observable invariants."
  - Fact: the article says nothing about TLA+ or formal verification (checked: the fetch found no mention).
- OPINION: measurement can find a violation in your own fleet, but an outside party cannot observe POP-internal timing, and a rare interleaving over thousands of POPs will not show up in black-box probes.

### What to prove, with what tool

- Model: POPs (edge and shield), origin with versioned objects, purge messages (hard, soft, by surrogate key), in-flight fills, TTL/SWR/SIE timers, request collapsing, cache key function.
- Properties:
  - Bounded staleness after purge (S2) with explicit window as a function of SWR and TTL.
  - Fresh-TTL-only-from-fresh-source: an edge never assigns TTL > 0 to an object it got from a stale shield copy.
  - Cache-key soundness: two requests share an entry only if the origin response is equal under a declared "response depends on" relation (S1).
- Tool (OPINION): TLA+ with TLC for bounded POP counts (2 edges, 1 shield, 1 origin, 2 versions) to find races, then TLAPS or Apalache for an inductive invariant. Ivy is a fit for the parametric (any number of POPs) version.

### Closest prior formal work

- Not found for CDN purge specifically. Search "formal verification CDN cache consistency model checking invalidation" returned hardware coherence results and CausalMesh.
- CausalMesh (arXiv 2508.15647), distributed cache, TLA+ then Dafny. UNVERIFIED claim from search summary: a violation was missed by TLC but found in Dafny. URL: https://arxiv.org/pdf/2508.15647
- Hardware cache coherence (MESI, FLASH). Different failure model (no TTLs, no origin).
- Related, not formal: Meta Polaris (above).

### First bite-sized step

Write a 100-line TLA+ spec of one edge, one shield, one origin, with soft purge, SWR, and the edge-fills-from-shield step. Check S2 with TLC. Expected: TLC finds the Fastly race as a counterexample; the fix (SWR=0 on shield requests) should make S2 hold. This validates the model against a documented behavior before any novelty claim.

## 2. Certificate Transparency: gossip, split view, witnesses, Static CT

### Who is hurt, with sources

Domain owners and browser users, if a log shows different trees to different parties and a mis-issued certificate hides in the unseen view. No documented case of this attack being exploited was found. Documented failures are of other kinds.

- Ayer on log failures. URL: https://www.agwa.name/blog/post/how_ct_logs_fail
  - Quote: Yeti 2022 failure due to "a single bit flip, likely due to a hardware error or cosmic ray"
  - Quote: "its database was rolled back during a botched backup restore."
  - Quote: "will have zero impact on Web users and website operators"
  - Quote: monitors flag tampering when there are "two STHs for the same tree size with different root hashes"
  - Quote (limit): with a compromised key, "SCTs could have been forged"
  - Inference: the database-rollback failure is a real equivocation-by-accident case (the log shows an older tree after a larger one).
  - Fact: the article does not discuss gossip (checked).
- Google Aviator exceeded its Maximum Merge Delay in October 2016, per search summary (UNVERIFIED on the source page). URL: https://groups.google.com/a/chromium.org/g/ct-policy/c/ZZf3iryLgCo/m/mi-4ViMiCAAJ
- Dahlberg: gossip is not deployed (UNVERIFIED from search summary). URL: https://arxiv.org/pdf/1806.08817

### Why it is a distributed-systems property

- Safety: no two clients accept inconsistent tree heads for the same log (no split view), under a log that can lie to each client separately.
- Liveness/detection: if the log equivocates, some honest monitor or witness eventually holds two inconsistent heads (detection within a bound).
- Static CT / witness spec facts (C2SP), URL: https://c2sp.org/tlog-witness@v1.1.0
  - Per search summary (UNVERIFIED verbatim): the witness's old size MUST match the latest checkpoint it cosigned, and it MUST persist the new checkpoint before responding.
  - Per search summary, tlog-cosignature: "Checkpoint cosignatures MUST be monotonically increasing" (paraphrase of UNVERIFIED text). URL: https://c2sp.org/tlog-cosignature@v1.1.0
- Inference: the witness is a small replicated state machine (persist-then-sign, crash recovery, rollback). That is a classic TLA+ shape.

### Why testing/measurement cannot settle it

- Equivocation is only visible if you hold both views; measurement of one vantage cannot show absence of a hidden view.
- OPINION: crash/restore bugs in a witness (sign, crash before persist, restore old state, sign a smaller or conflicting head) appear only under rare crash timing, which is what model checking explores.

### What to prove, with what tool

- Model: log (adversarial, Byzantine), n witnesses (crash-recover, honest), clients that require k-of-n cosignatures, monitors.
- Properties:
  - Safety: if a client accepts head H1 and another accepts H2 for the same origin, with the same tree size, then roots are equal, assuming at most f witnesses are dishonest and honest witnesses persist before sign.
  - Crash safety: an honest witness never cosigns two inconsistent heads, even across crash and restart (persist-before-sign).
  - Detection: under fair gossip, an equivocation is detected within bounded rounds.
- Tool (OPINION): TLA+/TLC for the witness state machine with crashes; Tamarin or ProVerif for the signature/consistency-proof layer (hash-chain abstraction); PRISM-style quantitative work for detection probability exists already.

### Closest prior formal work

- Quantitative verification of CT gossip with probabilistic model checking.
  - URL: https://etheses.bham.ac.uk/id/eprint/11578/
  - Quote: thesis uses "probabilistic model checking, a collection of techniques for formally verifying properties of stochastic systems."
  - Quote: analyses "the success rate of detecting inconsistencies in gossip messages"
  - Paper URL: https://www.prismmodelchecker.org/papers/spc20.pdf (PDF text not readable by the tool; abstract not quoted)
- Agentic Witnessing (arXiv 2604.24203): TLA+ and Tamarin with a "Forked History" model, for TEE auditing, not CT. UNVERIFIED (search summary). URL: https://arxiv.org/pdf/2604.24203
- No formal model of the C2SP witness protocol found. Search for "formal verification transparency log witness protocol Tamarin OR TLA+ OR ProVerif" returned nothing direct. (Absence in one search only.)

### First bite-sized step

TLA+ spec of one witness with a persisted store and a crash/restore action (restore may return an older store, as in the botched-backup-restore failure). Check the monotonic-cosigning invariant. Expected: counterexample unless persist-before-sign and rollback protection are modeled.

## 3. DNS propagation and TTL

### Who is hurt, with sources

- Stale delegation of removed domains (ghost domains) and long outages from long TTLs.
  - URL: https://ohdear.app/news-and-updates/the-ghost-domain-problem-in-dns-and-what-were-doing-about-it (search summary; not fetched)
  - Summary (not verbatim): cached resolvers serve a stale delegation for days after the registry removes the domain.
  - RFC 8767 (serve-stale), URL: https://www.rfc-editor.org/rfc/rfc8767.xml
    - Per search summary: a resolver "MUST set the TTL of each expired record in the message to a value greater than 0, with a RECOMMENDED value of 30 seconds."
    - Per search summary: stale data "can be used to co-opt security -- for example, to get domain-validated certificates fraudulently issued to an attacker."
- A user-written incident with long TTL (anecdotal): https://dev.to/upordownonline/your-dns-ttl-is-why-the-outage-lasted-2-hours-set-it-before-you-need-it-meh
  - Per search summary: A record fixed at 14:21, half of users still on the dead IP at 16:00, TTL 86400.
- No vendor postmortem was found in this pass.

### Distributed-systems property

- Safety: bounded staleness of a record at any resolver, at most TTL plus resolver clamp plus serve-stale extension.
- Liveness: a deleted delegation eventually disappears from all resolvers (fails with ghost-domain refresh of NS sets).

### Why testing cannot settle it

- OPINION: resolver fleets are heterogeneous and closed (clamps, serve-stale, prefetch), so a bound must be proved per modeled policy, not measured.

### What to prove and tool

- Prove: with policy parameters (max-cache-ttl, serve-stale, NS-refresh), staleness bound; show ghost-domain refresh makes the bound infinite under a malicious authoritative server.
- Tool (OPINION): TLA+ for time-parameterized resolver cache; this is small and more textbook than novel.

### Closest prior formal work

- GRoot (SIGCOMM 2020), URL: https://www.microsoft.com/en-us/research/uploads/prod/2020/07/sigcomm2020-final157.pdf
  - Per search summary: "first verifier that performs static analysis of DNS configuration files" and develops "a formal semantic model of DNS resolution."
  - Per search summary: later work notes GRoot abstracts away "caching and recursive queries".
- Liu et al., SIGCOMM 2023, end-to-end DNS resolution framework (UNVERIFIED: title and scope from one search summary; not opened).
- arXiv 2411.10188 "Reachability Analysis of the Domain Name System", https://arxiv.org/html/2411.10188v1 (not opened).
- Verdict (OPINION): crowded by networking-verification groups; lower niche value.

### First bite-sized step

Open Liu et al. 2023 and check whether it models TTL expiry and ghost-domain refresh. If not, specify the cache with time in TLA+ and check the ghost domain scenario.

## 4. Web push delivery

### Who is hurt, with sources

Users miss time-sensitive notifications; senders cannot know. The spec makes this explicit, so it is design, not bug.

- RFC 8030, URL: https://www.rfc-editor.org/rfc/rfc8030.html
  - Quote: "This does not indicate that the message was delivered to the user agent." (section 5)
  - Quote: "MAY retain a push message for a shorter duration than requested." (5.2)
  - Quote: "the push service MAY later expire the message prior to its advertised Time-To-Live." (7.2)
  - Quote: "A push message with a topic replaces any outstanding push message with an identical topic." (5.4)
  - Quote: "A push service MAY expire a subscription at any time." (7.3)
  - Quote: "The push service SHOULD continue to retry delivery of the message until its advertised expiration." (6.2)
  - Quote: "Intentional failure to deliver messages is difficult to distinguish from faults" (8.4)
- No academic delivery-rate study or documented incident was found in one search.

### Property

- At-most-once-or-expire with optional receipts; safety: a message is never delivered after TTL ("MUST NOT attempt to deliver" after TTL elapses, 5.2); liveness is only SHOULD, so nothing strong is provable.
- Property of interest: topic replacement plus receipts consistency (a receipt is never 204 for a replaced message; receipts "SHOULD be suppressed").

### Why testing cannot settle it

- The spec lets the service drop, so any measured loss is conforming; nothing to falsify.

### Tool and prior work

- TLA+ small model possible (OPINION), but value is low: the protocol permits loss. No prior formal work searched beyond one query.

### First step

Not recommended as a lead. Only possible niche: model receipts, topics, and TTL together and check the 202/204/410 receipt semantics for contradictions.

## Open questions for the human

- Is the aim a publishable verification result or a bug-finding case study? For CDN purge, a TLC counterexample matching Fastly's documented race is cheap; a parametric proof is expensive.
- Not checked: Akamai and Cloudflare purge semantics, CDN-specific papers outside the one search, RFC 5861 (stale-while-revalidate) wording, RFC 9111 text.
