# Unusual web verification targets
(authored by agents unless marked 🧑)

These are formal verification targets in the web, written for advisors who asked for a "differentiator". Ideas already listed in msg_candidates, vlm11_spread, vlm15_pitch and WebSpec-style CSP/CORS/cookie models are excluded.

Sources: two Claude subagents (an attacker/archivist persona in gen_attacker.md and a PL persona in gen_pl.md), Gemini (gem_out.md) and ChatGPT (gpt_out.md).
Novelty: Google Scholar, one query per idea, judged from result snippets only (raw pages in scholar/, summary in scholar_summary.md). "No proof found" means no snippet showed a proof. It does not mean we confirmed that none exists.

Pattern [opinion]: each idea takes something people treat as plumbing, a log, or a speed optimization and states it as a theorem from another field, such as snapshot isolation, transactions, erasure, or undetectability.

Ranking is by unusualness × feasibility [opinion].

1. Measurement shims are invisible
- thing: the JS wrappers that crawlers and RUM SDKs install around `fetch`, `eval` and DOM APIs (OpenWPM, JSphere-style instrumentation)
- theorem: for any page script, running with the shim gives the same return values, exceptions, property descriptors and `Function.prototype.toString` results as running without it, ignoring timing
- unusual: measurement researchers assume their instrument does not disturb the page. Here we prove the instrument is invisible, rather than proving a sandbox contains code.
- prior: Scholar shows empirical detection of instrumentation and no proof. SES/Caja membranes prove containment, which is a different property.
- step: model descriptors and Proxy traps in Lean, find a visible leak in one existing wrapper, then prove a fixed wrapper template

2. A page load is a version-consistent snapshot
- thing: HTML plus hashed JS/CSS chunks, served through CDN, browser and service-worker caches while a site deploys a new version
- theorem: every completed page load uses resources from a single deployment, or every mixed-version dependency edge is declared compatible
- unusual: this treats one page load as a distributed snapshot. It turns web_atoms "things that change together" into an invariant.
- prior: industry fixes exist. Vercel says "version skew can break your app" (quoted by ChatGPT). Scholar shows no proof.
- step: model the Workbox precache, `skipWaiting` and `clients.claim` in Lean. First show that the common setup breaks the invariant, then verify a gated rollover.

3. Archive replay shows one moment in time
- thing: replaying a page from mementos captured at different times (pywb, Memento)
- theorem: the mementos the replayer picks all lie in one window of width d in which each URL was unchanged, or the replayer reports "inconsistent"
- unusual: replay is judged by eye. Here it is snapshot isolation for the past web. It differs from the taken idea of archive JS rewriting.
- prior: Ainsworth, Nelson and Van de Sompel define "composite memento temporal coherence" (arXiv 2014), but no proof that a replayer preserves it was found.
- step: write pywb's memento-selection rule as a small Lean model, then prove the property or get a counterexample

4. WARC deduplication cannot substitute bytes
- thing: WARC revisit records, which skip storing a body because it is "identical to a previously recorded version" (WARC spec, quoted by ChatGPT)
- theorem: resolving any revisit chain terminates at a payload whose digest equals the declared payload digest. Replay never substitutes another capture.
- unusual: this verifies the web dataset itself, not the browser or crawler
- prior: Aturban et al., "Hashes are not suitable to verify fixity of the public archived web" (PLoS One 2023), is a measurement, not a proof
- step: build a verified revisit resolver in Verus and run it over real WARCs to count violations

5. C2PA signatures cover every pixel
- thing: c2pa-rs computing which byte ranges to exclude from the hash, so the JUMBF manifest can be embedded inside the JPEG it signs
- theorem: every byte the image decoder reads to produce pixels lies inside the hashed ranges
- unusual: everyone checks the signature. The real gap is the disagreement between two parsers, c2pa-rs and the image decoder.
- prior: Golaszewski et al., "Verifying provenance of digital media: Security analysis of C2PA and its implementation" (ePrint 2026). The snippet does not say whether it is machine-checked, so the paper needs reading.
- step: in Verus, prove that the JPEG segment walk and the exclusion range never overlap scan data

6. Prerendering is a transaction
- thing: Speculation Rules prerender, with activation and cancellation
- theorem: until activation, persistent state (cookies, storage, service workers, permissions) is unchanged. Cancellation is an abort. Activation equals an ordinary navigation.
- unusual: prerendering is seen as a latency feature, but it runs unclicked third-party JS
- prior: Franken et al., "Exposing cookie policy flaws…" (IEEE S&P 2019), is measurement. No proof found.
- step: model the deferral table for cookies, history and one deferred API, then check Chromium's list of gated APIs against it

7. Back/forward cache cannot refresh user activation
- thing: bfcache freeze and restore, combined with transient user activation (popups, clipboard, fullscreen)
- theorem: freeze, then wait, then restore never increases activation privilege. Activation that expired or was used before restore stays that way.
- unusual: the browser time-travels whole documents. This is the sharpened "monotone security facts across restore paths" idea from vlm17.
- prior: Scholar found only 2004–2009 web-navigation model checking. No proof found.
- step: model activation timestamps and bfcache transitions in Lean, then compare with Chromium's tests

8. Clear-Site-Data really erases
- thing: the `Clear-Site-Data` header across cookies, Cache Storage, service workers and live contexts
- theorem: after clearing class C, no state created in C before the clear can influence any later execution of the origin
- unusual: this treats "delete my site from this browser" as erasure in the information-flow sense, including paths by which data comes back
- prior: Ali et al., "Navigating murky waters…" (NDSS 2023), found incomplete removal by testing. No proof found.
- step: prove erasure for Cache Storage plus service-worker registrations in a small model

9. Sanitized HAR files hold no secrets
- thing: HAR files shared in bug reports. The Okta 2023 support leak came from HARs that still held session tokens (recalled by a subagent, not checked).
- theorem: no value from a credential position in the input (cookies, Authorization, URL tokens, POST and base64 bodies, redirect URLs) appears in the sanitized output
- unusual: a HAR is thought of as a log, not an attack surface
- prior: Scholar found no sanitizer papers. Google's har-sanitizer is heuristic.
- step: define a taint model over the HAR schema, prove a small sanitizer, and show where the existing tool leaks

10. Agent DOM pruners keep what humans see
- thing: the DOM-to-text and accessibility-tree pruners that browser agents act on (AgentOccam, Lightpanda)
- theorem: every node kept is visible and not covered, and every visible interactive element is kept
- unusual: pruning is treated as compression, but for an agent it acts as a security compiler that decides what the agent sees (hidden prompt injection, dropped cancel buttons)
- prior: Scholar shows heuristic and empirical work only. VizAssert and Cassius verify CSS layout, not pruning.
- step: verify a pruner in Verus against a simplified box and z-index layout model, then run it on 50 dark-pattern pages

Runners-up (in gen_*.md, gem_out.md and gpt_out.md): 103 Early Hints cannot gain authority early; Sec-Fetch-* headers as browser attestation; blob URLs as revocable capabilities; HTML parse unchanged by network chunking (partial prior: Frost 2026 proves a similar property for LLM streaming); redirect-rule termination; robots.txt agreeing with the server router; TCF "Reject All" soundness.
