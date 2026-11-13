# Queue of ideas not yet walked through with the human
(authored by agents unless marked 🧑)

Scope: ideas from the source files listed by the manager, minus those already walked through (agent-browser rule core, shared caches/CDN as folded into it, HTTP smuggling, cookie consent, archive JS rewriting, cross-tab coordination, SSO sign-in/out, JS engines vs spec, third-party page scripts) and minus human rejections (C2PA, WARC dedup, measurement-only studies).
Ranking is opinion: fit to web-related, FV truly needed, verified Rust/Servo friendly, distributed-systems angle, privacy/cookie/cache niche, adoptable.
"In-depth" = we have breakage evidence and a concrete property. "Rough" = one-line idea.
Paths are relative to out/.
Judgment calls I made (manager may override): skipped HTTP/2→HTTP/1 downgrade and the two-hop framing proof as part of "HTTP smuggling"; skipped consent-string decoding, consent revocation and GPC as part of "cookie consent"; skipped regex linear time, prototype pollution and skimmers as part of "third-party page scripts"; folded agent-browser sub-ideas (control port, session reset, secret handles, Lightpanda WS) into the walked-through rule core.

## In-depth

1. Cache reuse respects `Vary`
- what: a CDN/proxy may reuse a stored response only if the request headers named in `Vary` match (RFC 9111)
- verify: the cache-key match function equals RFC 9111 for all header spellings; diff nginx/Varnish/Squid against it
- why: "2512 websites include some header names in the Vary response header but do not configure their web cache(s) to include them in the cache key" (arXiv 2407.16303) → one user's page served to another; small pure Rust-friendly function — vlm20_fvshape/REPORT.md 2.1

2. CDN purge consistency across edge and shield caches
- what: after a purge, edge and shield tiers race with origin updates and refills
- verify (TLA+, then Ivy for any number of sites): bounded staleness after purge; a copy from a stale source never gets a fresh TTL
- why: distributed + cache niche; Fastly docs admit the race ("just purge twice"); Railway 2026 incident served cached private data to other users; no formal prior found — vlm25_dist/REPORT.md 2

3. Cookie `Domain` vs the Public Suffix List
- what: the browser must refuse cookies scoped to public suffixes like `co.uk`, using a ~10k-rule list with wildcards/exceptions
- verify: a PSL matcher equals the publicsuffix.org + RFC 6265bis algorithm for every host and list
- why: cookie niche; Quark used only an abstract suffix predicate; crawlberg #762 sent such cookies to every site under the suffix; a natural Verus/Servo component — vlm20_fvshape/REPORT.md 2.3

4. CDN path confusion (web cache deception)
- what: CDN and origin read the same URL differently, e.g. `/myAccount;x.css` cached as a public stylesheet
- verify: for every URL, "CDN caches as public" ⇒ "origin serves a public resource"; or the two path normalizers are equivalent (SMT finds the breaking URL)
- why: 1188 vulnerable sites in top 10K (USENIX Sec 2022); cache/privacy niche — vlm20_imc/REPORT.md B; vlm11_spread item 12
- note: may overlap the shared-caches/CDN point already folded into the agent browser

5. Bounce-tracking deletion fires exactly when it should
- what: browsers delete storage of redirect-only tracker sites after a grace period without user interaction
- verify (timed model checking): purged iff bounced ∧ grace passed ∧ no activation, under any clock jumps and interleavings; purge covers all state
- why: privacy niche; the spec itself has "TODO: Consider if we should do anything when the clock is moved forward or backward." — vlm20_fvshape/REPORT.md 2.4

6. Clear-Site-Data really erases
- what: the `Clear-Site-Data` header across cookies, Cache Storage, service workers, live contexts
- verify: after clearing class C, no state created in C before the clear influences later execution
- why: privacy/cache; NDSS 2023 found incomplete removal by testing; no proof found — vlm19_weird2/IDEAS.md 8

7. A page load is a version-consistent snapshot
- what: HTML and hashed JS/CSS chunks pass through CDN, browser and service-worker caches during a deploy
- verify: each load uses one deployment's resources, or declared-compatible mixes; first show Workbox `skipWaiting` + `clients.claim` breaks it
- why: distributed snapshot + caches; Vercel: "version skew can break your app" — vlm19_weird2/IDEAS.md 2; same family as "behavioral fossils" (vlm17_weird/IDEAS.md 2)

8. Storage Access API: three answers agree
- what: `hasStorageAccess()`, the `requestStorageAccess()` promise and the real cookie jar must agree for an embedded iframe
- verify: ~6-variable state model; `hasStorageAccess()` true iff cookies are actually unpartitioned
- why: cookie niche; WebKit 193277 showed disagreement — vlm20_fvshape/REPORT.md 2.7

9. Cookie/storage partition key (CHIPS)
- what: partitioned cookies keyed by top-level site, incl. service workers
- verify: extend WebSpec's Coq model with the partition key and check the service-worker invariant
- why: cookie niche; a CHIPS spec patch for service workers exists; Chromium bugs need login (evidence thin) — vlm11_spread/REPORT.md 20; vlm21_map

10. Ad-blocker rule compilation preserves meaning
- what: Manifest V3 forces blockers to compile filter rules into Chrome's declarative format
- verify: translation validation: compiled rule matches a URL iff source rule does
- why: privacy; AdGuard #3615 silently leaks the first query param while the URL bar looks clean — vlm20_fvshape/REPORT.md 2.5

11. Attribution Reporting budget filter
- what: Chrome's ad-conversion API caps each source's contribution before adding noise
- verify: the budget filter in Chromium keeps the cap for any trigger sequence (DP theorem as hypothesis)
- why: privacy; Chrome authors: "neither ARA nor PAA has been backed by a rigorous DP proof" (arXiv 2412.16916) — vlm20_fvshape/REPORT.md 2.6

12. Prerendering is a transaction
- what: Speculation Rules prerender runs unclicked third-party JS
- verify: until activation, cookies/storage/SW/permissions unchanged; cancel = abort; activation = normal navigation
- why: privacy/state; no proof found — vlm19_weird2/IDEAS.md 6

13. bfcache cannot refresh user activation ("arrow of time")
- what: back/forward cache, session restore and replay bring old page state back
- verify: chosen security facts (logout, revoked permission, expired activation) stay monotone across every restore path
- why: Servo-modelable; no proof found — vlm19_weird2/IDEAS.md 7; vlm17_weird/IDEAS.md 1

14. Server speaks only for origins it owns (HTTP/2 push, Signed Exchanges)
- what: shared TLS certificates let a co-tenant deliver content "as" another origin
- verify (Alloy): content is stored under origin O only from a peer authorized for O under SOP's check
- why: "11 out of 14 popular browsers ... are vulnerable" (NDSS 2025) — vlm20_imc/REPORT.md D

15. Agent DOM pruners keep what humans see
- what: DOM-to-text pruners decide what a browser agent sees
- verify (Verus): kept nodes are visible/uncovered; visible interactive elements are kept
- why: Rust-friendly, agent-adjacent; heuristic-only prior — vlm19_weird2/IDEAS.md 10; vlm21_map

16. Verified tenant-switch kernel / JIT-output checker for shared processes
- what: many tenants (tabs, Workers) in one process; verify the boundary, not the engine
- verify: while tenant t runs only t's pages are accessible; or each JIT output stays in t's cage with no WRPKRU
- why: 🧑 process-sharing idea; pitch C; pilot found 32% raw 64-bit pointers without pointer compression — vlm15_pitch/PITCHES.md C; vlm9_shareproc/REPORT.md 1–2; vlm10_share
- note: on the map as "pitched"; human has not walked through it in this series as far as the delegation lists

17. Multi-vantage domain validation is sound
- what: CAs check domain control from k-of-n network locations
- verify (SMT): no attacker controlling fewer than a given route set gets k wrong answers
- why: distributed quorum; rules change 2026-12-15 (snippet, unverified) — vlm20_imc/REPORT.md F

18. OAuth bound to one app on multi-app platforms
- what: integration hubs act as one OAuth client for many apps
- verify (Tamarin/ProVerif): a token granted to app X cannot be redeemed for app Y
- why: 16 of 18 platforms vulnerable, CVE-2023-36019; formal OAuth work assumes one client per app — vlm20_imc/REPORT.md E
- note: may overlap the kept SSO item

19. Sanitized HAR files hold no secrets
- what: HAR logs shared in bug reports still contain session tokens
- verify: no value from a credential position appears in sanitized output (taint model)
- why: small, adoptable; Okta 2023 leak (recalled, unchecked) — vlm19_weird2/IDEAS.md 9

20. Web probate (expired domain re-registered)
- what: cookies, permissions, saved passwords, HSTS, service workers pass to a domain's new owner
- verify: authority created under owner A is unusable by owner B
- why: browser-state angle not covered by prior server-side measurements — vlm17_weird/IDEAS.md 3

21. Archive replay shows one moment in time
- what: replay mixes mementos captured at different times
- verify: the replayer's picks lie in one window where each URL was unchanged, or it reports "inconsistent"
- why: advisor's archive data; "composite memento temporal coherence" defined (2014) but not proved — vlm19_weird2/IDEAS.md 3

22. Servo DOM-to-GC safety rules
- what: Servo destructors touched freed objects at shutdown (#24621, #15318)
- verify: destructors touch no other GC object; every live GC pointer is tracked
- why: Servo-native; bounded mock checks catch #24621 — msg_candidates.txt 10

23. Spec-sensitivity via real bug-fix commits
- what: replay Boa/Servo past fix commits as mutants against our proofs
- verify: every real bug-fix commit breaks some proof obligation; survivors = weak specs
- why: answers "is the spec strong enough"; generic mutation is crowded — vlm17_weird/IDEAS.md 5; vlm5_capture/README.md 2

24. JIT side effects / range analysis / phase invariants
- what: V8 CVE shapes (2020-6418, 2021-21220, 2021-4102)
- verify: models done; real-code proof not attempted
- why: crowded (VeRA, Icarus); weak web fit — msg_candidates.txt 1–3

25. Sandboxed memory bounds (Wasmtime, V8 sandbox) and two-context heap
- what: attacker-steered accesses stay in region; context A objects unreachable from B
- verify: model proofs done (35-bit Wasmtime bug rejected)
- why: feeds item 16; standalone is crowded — msg_candidates.txt 5–6

26. WGSL/WebGPU shader translation
- what: browsers translate shaders to HLSL/MSL/SPIR-V
- verify: per-shader translation validation for a WGSL subset (Naga is Rust)
- why: DarthShader found 39 faults, 15 Chrome CVEs; no verification found — vlm11_spread/REPORT.md 6

## Rough (one line each)
- logout/token revocation propagation (OIDC back-channel "SHOULD NOT retransmit") — vlm25_dist/REPORT.md 3; likely inside kept SSO item
- double-entry ledger of browser authority: no tab spends permission it never received — vlm17_weird/IDEAS.md 6
- agent context window as a renderer process: origin-labelled text cannot steer actions on another origin — vlm17_weird/IDEAS.md 7; vlm9_agentsec D1/D2
- proofs that expire: proofs keyed to web atoms, voided when an atom member changes — vlm17_weird/IDEAS.md 4
- evolving pages whose fitness is a failed proof — vlm17_weird/IDEAS.md 10
- archive replay as courtroom evidence: per-fact chain of custody — vlm17_weird/IDEAS.md 8
- measurement shims are invisible to page scripts — vlm19_weird2/IDEAS.md 1
- leakage-budgeted co-location instead of Spectre detection — vlm9_shareproc/REPORT.md 3
- inline-cache / shape-transition invariants — vlm5_capture/README.md 3; vlm21_map
- verified cookie jar / ORB / CSP decisions in Rust — vlm5_capture/README.md 5; vlm11_spread 3
- parallel style/layout race freedom, IPC validation, structured clone — vlm5_capture/README.md 6
- HTML sanitizer round trip (ammonia non-default setting allowed script) — msg_candidates.txt 8
- Servo blob slice overflow — vlm21_map
- IndexedDB lifetime/transaction model (repeated UAF CVEs) — vlm11_spread 7
- extension MV3 permission model — vlm11_spread 8
- Fetch spec / Permissions Policy mechanized — vlm11_spread 21–22
- site isolation invariants at Chrome scale (Quark successor) — vlm11_spread 4
- edge config/rule-language compiler verified — vlm11_spread 13
- HTTP/2 stream state resource bounds (Rapid Reset) — vlm11_spread 14
- hostname IDNA normalization; HTTP Range in proxies — vlm21_map
- ECH / DNS HTTPS-record client fallback — vlm20_imc finding 6; vlm11_spread 16
- QUIC ECN count validation (bit mix-up) — vlm20_imc finding 9
- passkey revocation / synced passkeys origin checks — vlm11_spread 18
- Topics API noise; UID smuggling vs partitioning; double-keyed cache exemption — vlm21_map
- 103 Early Hints gain no early authority; Sec-Fetch-* as attestation; blob URLs as revocable capabilities; HTML parse independent of network chunking; redirect-rule termination; robots.txt vs server router — vlm19_weird2/IDEAS.md runners-up
- Bluesky AT Protocol sync/deletion; Automerge sync divergence; CT witnesses — vlm25_dist runners-up
- agent CSP; per-frame screenshot provenance — vlm9_agentsec GPT add-ons
