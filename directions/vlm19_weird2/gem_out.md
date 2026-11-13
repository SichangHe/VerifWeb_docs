(authored by agents unless marked 🧑)

**1. DOM-to-Accessibility-Tree Distillers for Web Agents — Concrete web thing:** Browser accessibility serializers and agent DOM pruners (e.g., Chromium `AXObjectCache`, Prune4Web, AgentOccam) that compress raw HTML/CSS into text trees for LLM browser agents.

* **Theorem:** Every node in the pruned tree has a non-zero, unoccluded hit-test box in the layout tree (no invisible prompt injection), and every viewport-visible interactive element maps to a distinct node in the pruned tree (no dropped dark-pattern/cancel buttons).
* **Why unusual:** DOM pruning is treated as lossy UI compression or screen-reader scaffolding rather than a security compiler, even though agents act solely on its output (inspired by your `browser_agent.md` notes on Prune4Web and dark patterns).
* **Closest prior work:** VizAssert / Cassius (formal CSS layout verification, PLDI 2016/2018), which verify layout rules rather than visibility-preserving DOM distillation.
* **First step:** Model AgentOccam/Lightpanda's DOM-to-text pruner in Verus against a simplified bounding-box/z-index layout tree and check it on 50 dark-pattern and hidden-text pages (2–3 weeks).

**2. Speculative Prerendering Capability Gates — Concrete web thing:** The WICG/WHATWG Speculation Rules prerendering state machine in Chromium and Servo (`speculationrules` prerender buffer before user navigation activation).

* **Theorem:** Observational non-interference before activation: for any prerendered browsing context discarded without user navigation, persistent browser state (cookies, storage, service workers, credentialed fetches, permissions) is bit-for-bit identical to a trace where prerendering never ran.
* **Why unusual:** Prerendering is viewed as a pure latency optimization ("load the next page early"), not a sandbox where unclicked search results execute arbitrary third-party JS in the background.
* **Closest prior work:** WebSpec (Coq browser model, S&P 2023), which models standard navigation and cookies but omits speculative execution and capability deferral tables.
* **First step:** Mechanize the WICG Prerendering API capability-deferral state machine in Lean/Verus and check Servo/Chromium's gate table for unguarded stateful Web APIs (2 weeks).

**3. Service Worker & Bundler Atomic Rollover — Concrete web thing:** The WHATWG Service Worker lifecycle (`installing` to `waiting` to `activated`, `skipWaiting()`, `clients.claim()`) paired with content-hashed dynamic `import()` chunk manifests (Workbox/Webpack).

* **Theorem:** Deployment snapshot serializability: across any interleaving of Service Worker updates, cache evictions, and dynamic module loads in a live tab, every subresource fetched by a document belongs to a single deployment manifest version $V_i$, never mixing chunks from $V_i$ and $V_j$.
* **Why unusual:** Service worker update hooks and chunk loaders are treated as caching plumbing, yet mixed-version "tearing" silently breaks live single-page apps (turning your `web_atoms.md` co-change concept into a client-side serializability invariant).
* **Closest prior work:** Workbox (unverified Google library) and formal Service Worker origin-isolation models (Fett et al.), which check security origins rather than cross-version atomic consistency.
* **First step:** Model the Service Worker lifecycle and a Workbox precache table in Lean, prove `skipWaiting()` plus `clients.claim()` violates snapshot serializability, and verify a gated rollover handler (3 weeks).

**4. C2PA JUMBF Hash-Exclusion Byte Ranges — Concrete web thing:** The ISO 19566-5 (JUMBF) box parser and hard-binding byte-range exclusion calculator in `c2pa-rs` that hashes JPEG/WebP/MP4 files while excluding the embedded signature manifest box itself.

* **Theorem:** Coverage completeness: for any media buffer accepted by `c2pa-rs` with a valid hard-binding signature, every byte read by the target image decoder to produce rendered pixels lies strictly inside the hashed byte intervals (disjoint from the excluded JUMBF manifest range).
* **Why unusual:** Everyone trusts C2PA's ECDSA signature and ignores the byte-interval exclusion arithmetic; a parser disagreement between `c2pa-rs` and the JPEG decoder lets an attacker hide replacement pixel scans inside the "excluded" metadata range (inspired by your `c2pa` notes).
* **Closest prior work:** EverParse / 3D (verifies binary parsers for memory safety and non-malleability, not cross-parser hash-coverage completeness against a media decoder).
* **First step:** Verify `c2pa-rs`'s JPEG segment and JUMBF exclusion-range calculator in Verus against a minimal JPEG scan-data parser to prove no pixel segment overlaps the excluded hash range (3 weeks).

**5. JavaScript Measurement & Telemetry Membranes — Concrete web thing:** Monkey-patching instrumentation wrappers (`Proxy` and descriptor shims around `fetch`, `eval`, `Function`, and DOM APIs) used by web measurement crawlers (JSphere, OpenWPM, FidEx) and RUM SDKs (Sentry).

* **Theorem:** Observational transparency: for any page script $P$ (modulo timing), executing $P$ under the instrumentation shim produces the exact same host calls, return values, exceptions, property descriptors, and `Function.prototype.toString` outputs as an uninstrumented engine.
* **Why unusual:** Measurement researchers treat their own logging shims as invisible passive observers, even though leaky wrappers trigger getters twice, alter descriptor flags, or trip bot-detection checks and change page behavior (inspired by your `JSphere` `eval_trick.md` notes).
* **Closest prior work:** Caja / SES membrane confinement proofs (Maffeis et al., CSF 2010), which prove untrusted code cannot escape a sandbox rather than proving a logging shim is undetectable to page code.
* **First step:** Model JS property descriptors, `Proxy` traps, and `Reflect.apply` in Lean, find transparency violations in OpenWPM/JSphere wrappers, and verify a transparent wrapper template (2–3 weeks).

**6. CDN & Server Redirect/Rewrite Rule Cascades — Concrete web thing:** Declarative URL redirect and rewrite engines (Cloudflare Bulk Redirects, Netlify `_redirects`, Nginx `rewrite` regex/template cascades) used during site migrations and dead-link recovery.

* **Theorem:** Termination and origin confinement: for every input URL $u$, repeated evaluation of the rewrite cascade terminates in at most $K$ hops (no redirect loops), preserves declared query/auth parameters only within allowlisted origins (no open redirects), and maps deprecated paths deterministically.
* **Why unusual:** Redirect tables are treated as disposable sysadmin/SEO config files rather than programs, until a regex edge case causes a global redirect loop outage or open-redirect token leak (inspired by your group's Fable dead-link paper).
* **Closest prior work:** Network control-plane verifiers (Batfish, Minesweeper, ZENITH), which verify IP/BGP packet forwarding tables rather than string-rewriting HTTP URL automata.
* **First step:** Build a translator from Netlify/Cloudflare `_redirects` and Nginx `rewrite` rules to Z3/Lean and check termination and open-redirect freedom on 500 real open-source web configs (2 weeks).

**7. Crawler Exclusion (`robots.txt` RFC 9309) vs. Origin Router Equivalence — Concrete web thing:** RFC 9309 `robots.txt` and `X-Robots-Tag` wildcard/percent-encoding matchers in crawlers/AI answer engines paired with origin web framework route tables (Express, Nginx, Next.js).

* **Theorem:** Policy-router agreement: no URL $u$ that resolves to a sensitive handler in the origin server's router after URL normalization (percent-decoding, dot-segment removal, trailing-slash folding) is classified as `Allow` by the RFC 9309 `robots.txt` state machine.
* **Why unusual:** `robots.txt` is dismissed as a trivial 1990s text file, so nobody checks whether RFC 9309's longest-match wildcard and percent-encoding rules agree with how the web server actually routes URLs (inspired by your `DeGenTWeb` and `web_user_facing.md` crawler notes).
* **Closest prior work:** Header Space Analysis for firewall ACLs (NSDI 2012) and Google's unverified C++ `robotstxt` parser; never applied to cross-checking `robots.txt` against web routers.
* **First step:** Verify a Rust RFC 9309 matcher in Verus and build an automaton-intersection check against Express/Next.js route tables to find `Disallow` bypasses on 200 top sites (2 weeks).

**8. IAB TCF v2.2 Consent Bitstring Encoders & Script Gates — Concrete web thing:** Client-side Consent Management Platform (CMP) state machines (`__tcfapi`, Google Consent Mode v2) and IAB TCF v2.2 base64 bitstring encoders (OneTrust, Cookiebot, open-source CMP SDKs).

* **Theorem:** Reject-All soundness: if the user invokes the "Reject All" transition, the serialized TCF v2.2 bitstring contains `0` for every non-essential Purpose and Vendor bit, and no script tag or network beacon gated on those purposes can transition to the executing state.
* **Why unusual:** Cookie banners are studied empirically by privacy crawlers as legal/UX artifacts, never treated as a security reference monitor whose bit-packing code and script-loader gate can be formally verified (inspired by your `web_user_facing.md` consent-gated page notes).
* **Closest prior work:** Empirical GDPR measurement crawlers (Matte et al. S&P 2020; Bollinger et al. USENIX Security 2022), which detect violations dynamically without verifying the CMP state machine.
* **First step:** Verify an open-source Rust/TypeScript IAB TCF v2.2 bitstring encoder and script-gate state machine in Verus/Lean and test real CMP traces against the spec (2–3 weeks).

**9. Keyed Virtual DOM Diffing & SSR Hydration Reconcilers — Concrete web thing:** Keyed list reconciliation (`reconcileChildren`) and Server-Side Rendering (SSR) hydration algorithms in frontend frameworks (e.g., Rust's Dioxus/Leptos, Preact, React Fiber).

* **Theorem:** Reconciliation isomorphism: for any old VDOM $T_1$, new VDOM $T_2$, and live DOM $D$ matching $T_1$, applying the diff patch $\Delta(T_1, T_2)$ to $D$ yields a DOM identical in tree structure, attributes, form values, and event handlers to rendering $T_2$ from scratch.
* **Why unusual:** VDOM diffing and hydration are viewed strictly as UI rendering speedups, yet reconciliation bugs leave stale event handlers or `href`/CSRF attributes attached to the wrong DOM nodes after list reorders or hydration mismatches.
* **Closest prior work:** Featherweight DOM / formal React hooks semantics (POPL/ECOOP), which model component execution rules rather than verifying a keyed DOM diff-and-patch or SSR hydration algorithm.
* **First step:** Verify the ~200-line keyed children diffing algorithm from Dioxus (Rust) in Verus and prove patch equivalence to fresh rendering across arbitrary key permutations (3 weeks).

**10. Browser Password & Payment Autofill Form-Grouping Engines — Concrete web thing:** Browser autofill form-extraction and credential-fill state machines (Chromium `FormDataParser` / `PasswordAutofillAgent`, Bitwarden content scripts) that group form-less `input` elements and populate saved secrets.

* **Theorem:** Form-boundary and visibility confinement: credential bytes are written only to `input` elements that share the focused trigger element's form owner and origin, have been rendered visible in the viewport prior to fill, and have not undergone DOM ancestry mutation between preview and commit.
* **Why unusual:** Autofill is treated as a fuzzy UX heuristic ("find nearby username/password boxes"), allowing hidden third-party inputs or dynamic DOM splicing on shared pages to siphon autofilled passwords and credit cards.
* **Closest prior work:** Empirical autofill leakage measurements (Lin et al., USENIX Security 2024; Silver et al., CCS 2014), with zero formal verification of the browser's form-clustering and fill state machine.
* **First step:** Port Chromium/Servo's form-control grouping and visibility-check state machine to a 300-line Verus module and prove that unrendered or cross-form inputs cannot receive autofill writes (2–3 weeks).

**11. HTTP `206 Partial Content` Range Coalescers in CDNs — Concrete web thing:** RFC 9110 `Range`, `Content-Range`, and `If-Range` byte-slice parsers and partial-cache combiners in CDN proxies and browsers (e.g., Cloudflare Pingora, Varnish, Chromium media cache).

* **Theorem:** Slice-reassembly integrity: any sequence of `206 Partial Content` slices merged by the cache produces a byte buffer identical to a single `200 OK` payload from one strong-`ETag` origin version, with memory and copy work bounded linearly by the requested range size.
* **Why unusual:** Byte-range serving looks like trivial interval math for video scrubbing, yet off-by-one overlap coalescing or weak-`ETag` splicing silently corrupts signed binaries/Wasm/C2PA media or enables range-amplification DoS.
* **Closest prior work:** Verified TCP stream reassembly (FreeBSD/CompCert) and HTTP/1.1 framing fuzzers (HTTP Garden); never applied to HTTP `206` cache-slice merging and validator matching.
* **First step:** Verify Pingora or Hyper's Rust HTTP `Range`/`Content-Range` parser and interval merger in Verus against RFC 9110 Section 14 (2 weeks).
