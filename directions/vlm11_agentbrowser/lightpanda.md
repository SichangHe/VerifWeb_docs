# Lightpanda and agent-oriented headless browsers (factual study)
(authored by agents unless marked 🧑)

Source: clone of github.com/lightpanda-io/browser at HEAD 6cfc29e1df1b (2026-11-07), not b8e234a77; no clone existed. Read only, nothing built or run.
Paths below are under that clone's `src/`. [F]=fact, [I]=inference. GH = github.com/lightpanda-io/browser.
Prior finding on --block-urls vs WebSocket not repeated (out/cloud/p5_lightpanda_blockurls.md).

## 1. Architecture
- [F] Language/engine/libs. README:7 "A new browser, written in Zig." README:312-315 "HTTP loader ([Libcurl]...)", "HTML parser ([html5ever]...)", "Javascript support ([v8]...)". build.zig.zon:5 `minimum_zig_version = "0.17.0"`; V8 comes from a project fork (build.zig.zon:8 `lightpanda-io/zig-v8-fork`).
- [F] So the parser is Rust (html5ever, src/rust exists), not Zig; TLS is BoringSSL (build.zig.zon:29 `boringssl-zig`). Trusted base = Zig + Rust + C++ (V8) + C (curl, BoringSSL).
- [F] Licence AGPL-3.0 (header of src/browser/Browser.zig:4-8).
- [F] Protocols: README:325 "CDP/websockets server", "CDP and Webdriver Bidi"; also an MCP HTTP server (README:~250 `lightpanda mcp --port 9223`) and an `agent` mode (Config.zig:939 `.serve, .fetch, .mcp, .agent`).
- [F] DOM is native Zig, not WebKit/Blink: src/browser/webapi/*, Frame.zig (4759 lines), Session.zig, Page.zig, selector/xpath dirs.
- [F] Process/thread model. Server.zig:1293-1294 "One thread driving a Browser."; Server.zig:593-599 `std.Thread.spawn(.{}, Worker.start, ...)` then `thread.detach()`. Browser.zig:35-37 "You can create multiple browser instances. A browser contains only one session."
- [F] One V8 isolate per Browser. Env.zig:57 "The Env maps to a V8 isolate, which represents a isolated sandbox for executing JavaScript."
- [I] Multiplexing = one OS thread + one isolate + one Session per CDP/MCP connection, all in one OS process. Tabs inside a session are `Session.pages` (Session.zig:87 "Round-robin cursor for fair page iteration"). No per-origin process or isolate.
- [F] MCP isolation claim, README:257: "Each connection is routed to its own **browsing session** — its own page, cookies and memory".
- [F] Memory model: arena pools. ArenaPool.zig:30 `pub const BucketSize = enum { tiny, small, medium, large }`, free lists per bucket; Session takes one at Session.zig:167 `arena_pool.acquire(.small, "Session")`. Arena.zig:30 `SAFETY = lp.IS_DEBUG == true and lp.IS_TEST == false`: safety checks exist only in debug builds.
- [F] Same fact stated by GHSA-3jpq-xwf3-rwr6: "Release builds strip assertions". [I] Release builds drop bounds/arena checks; a verifier must target the release semantics.
- [F] V8 is told about arena bytes (Browser.zig:51 "Pinned-arena bytes we haven't told v8 about yet"; :267 `adjustAmountOfExternalAllocatedMemory`). Two allocators (V8 GC heap + Zig arenas) with cross-references managed by weak finalizers (Browser.zig:166-170 "V8 workers can post until the isolate is gone...").
- [F] Hang defence: Watchdog.zig thread, "How often the checker thread scans the entries", terminates JS via V8 interrupt; Watchdog.zig:27-30 says a stall in native code is only reported, not interrupted.
- [F] Crash policy: src/crash_handler.zig overrides Zig panic and calls `crash(...)` then abort (whole process, all sessions die).

## 2. What it drops vs Chrome
- [F] Not a Chromium fork (README:7). [F] No multiprocess: see threads above. [F] No OS sandbox code found: grep for sandbox in src/network, src/server, src/App.zig only hit an Origin test ("Sandboxed iframes and data: URLs", Server.zig:1607). [I] The OS-level seccomp/namespace sandbox is absent; the only "sandbox" is V8's isolate.
- [F] Site isolation: no per-site processes (above). Same-origin policy and cookie policy are reimplemented in Zig (see advisories, section 5).
- [F] Rendering: older versions had none. At HEAD there is a partial layout: src/browser/layout.zig (`boxWidth`), StyleManager.zig (4375 lines), screenshot.zig (1846 lines), RenderTree.zig. [I] Docs outdated vs README claim of "no rendering"; I did not run it, so the fidelity is unknown.
- [F] Workers off by default: Config.zig:297 "workers are now disabled by default, use \"--load-resources worker\" to enable".
- [F] CDP coverage partial; issue #3182 (GH/issues/3182): "fundamentally **single page-target + single browser-context**". #882 (open): "multi contexts and multi pages is not supported". #3347: "Page.createIsolatedWorld ... evaluates against the **main document**".
- [F] Added agent-facing, non-Chrome features: robots.txt (`--obey-robots`), adblock, URL/CIDR blocklists, `--block-private-networks` ("Defaults to false", help.zon:465), rate limiter, WebBotAuth, markdown/semantic-tree dump (src/network/*, src/markdown.zig, SemanticTree.zig).

## 3. Claimed performance
- [F] README:36-37 (AWS m5.large, 933 pages; table covers 100 pages): "Memory (peak, 100 pages) | 123MB | 2GB | ~16x less" and "Execution time (100 pages) | 5s | 46s | ~9x faster". Source: https://github.com/lightpanda-io/demo/blob/main/BENCHMARKS.md#crawler-benchmark. Vendor numbers, not reproduced.

## 4. Security model and docs
- [F] SECURITY.md: "Security fixes are applied to the latest `main` branch." and "Please **DO NOT** file a public issue, instead send your report privately to security@lightpanda.io." No threat model document found in the repo (ls: AGENTS.md, CLAUDE.md, CONTRIBUTING.md, SECURITY.md only).
- [F] CDP/MCP have no auth. Issue #3452 (open, https://github.com/lightpanda-io/browser/issues/3452): "accepts **any local connection with no authentication**. The only gate today is the Origin header check on the WebSocket handshake".
- [F] Obscura, for contrast, offers a token: README "export OBSCURA_CDP_TOKEN=\"$(openssl rand -hex 32)\"".
- [F] Server-side request filter exists (network/IpFilter.zig, `--block-cidrs`), but off by default (above). [I] SSRF to metadata/internal hosts is opt-in.

## 5. Known security issues (GitHub Security Advisories, all "published", API `gh api repos/lightpanda-io/browser/security-advisories`, URL pattern https://github.com/lightpanda-io/browser/security/advisories/<id>)
Eleven advisories, 2026-05-28 to 2026-11-04; 9 high, 2 critical (severity field):
- GHSA-mq6p-m9cc-q432 (critical): "URL parser misidentifies page origin for URLs containing @ in the path - Same-Origin Policy bypass". Text: "searched for `@` across the entire URL string".
- GHSA-36mm-v3c2-24cc (critical): "fetch() and XMLHttpRequest attach session cookies to cross-origin requests regardless of credentials mode".
- GHSA-4j5j-4ggv-2vgj: "Cookie Domain= attribute accepted by lookalike hosts due to suffix-only match".
- GHSA-rm33-829c-942c, GHSA-5gg3-f7j5-hfv4, GHSA-xxrm-48f7-h89p: three SameSite (Strict/Lax/nested iframe) cookie bugs. Quote: "computed the 'site for cookies' of an iframe from its immediate parent frame only".
- GHSA-mcw6-8p83-pm3h: "Credential headers leak across cross-origin redirects" (`applyRedirectTarget` in HttpClient.zig never compared origins).
- GHSA-wjwj-jrwg-3wgm: "Missing Origin / Host validation on the CDP WebSocket handshake allows Cross-Site WebSocket Hijacking".
- GHSA-rqpx-pxch-q2cm: "MCP HTTP server accepts any Origin / Host / content type - any web page can drive every MCP tool".
- GHSA-7c5w-p4q2-98gf: "WebSocket frame length integer overflow allows unauthenticated remote denial of service" ("unchecked `usize` addition", release build wraps).
- GHSA-3jpq-xwf3-rwr6 (2026-11-04): "Heap buffer overflow in `Frame.buf` via long element and tag names" (fixed 1024-byte scratch buffer, "never checked that the name fit").
- [F] No CVE ids (cve_id null for the first one fetched; `gh search issues CVE` returned nothing).
- [I] Pattern: 7 of 11 are policy bugs (origin, cookie, credential scoping) in re-implemented web security; 2 are memory-safety bugs in release-only unchecked paths (Zig integer overflow / missing bound); 2 are unauthenticated local control channels (CDP, MCP). Classes a prover can state precisely.

## 6. Issues mentioning crash/memory/isolation (gh search, open/closed as of 2026-11-07)
- #2622 (closed): "An `async` `<script>` whose fetch is retried/aborted with a non-200 ... use-after-free that ends in a **double release of the pooled arena**" ; "ReleaseFast: no fault ... RSS climbs to ~18 GiB". Directly in ArenaPool.
- #2460 (closed): "Frame.removeNode unlinks but never frees Node/Element memory (long-running-page leak)".
- #3636 (closed): "only the first 4 sessions ever load a page that stays busy. ... `goto` returns successfully" with empty document. Concurrency/multiplexing bug, silent failure.
- #1844 (closed): "CDP server becomes unresponsive after sustained rapid interactions (~80+ commands)".
- #3672 (closed): "linux/arm64: SIGILL while executing compiled regular expressions"; #4433 SIGILL on macOS x86_64 (build baseline); #1370 open "fatal on arm64 which is 64k page kernel".
- #3749 (closed): "Network.setUserAgentOverride & --disable-web-security".
- #1672 (open): "Scaling persistent browser instances for autonomous agents?".

## 7. Similar agent browsers
- Obscura, github.com/h4ckf0r0day/obscura (30511 stars, Rust). README: "a headless browser engine written in Rust, built for web scraping and AI agent automation. It runs real JavaScript via V8, supports the Chrome DevTools Protocol". Claims "Memory | **30 MB** | 200+ MB", "Page load | **85 ms** | ~500 ms". Has rendering feature flag, "Anti-detect | **Built-in**", stealth TLS via BoringSSL, optional CDP token, distroless non-root Docker. Advisories via API: `[]` (none published). [I] Same trust-base shape as Lightpanda (own DOM + V8) with Rust instead of Zig; fewer public security records.
- Steel (steel-dev/steel-browser, TypeScript): "Steel Browser is a batteries-included browser sandbox". Browserbase Stagehand (TypeScript): "The SDK to extract data and interact with any site". [F] Neither repo's description is an engine; [I] both drive Chrome (not verified by source read), so they inherit Chromium's multiprocess sandbox and are not own-engine targets.
- Not searched deeply: Servo-based agent browsers, Ladybird. [F] cx_servo dir exists in out/ from earlier work.

## 8. Candidate verification targets (inferences)
- [I] T1 ArenaPool acquire/release: no double release, no use after release (#2622). Small, self-contained Zig file.
- [I] T2 Origin and URL parsing (URL.zig 1704 lines): authority-only `@` search; origin equality used by cookies, CORS, redirects (GHSA-mq6p, -mcw6).
- [I] T3 Cookie jar policy: SameSite/Domain/credentials mode as pure functions of (request site, frame ancestry); spec is RFC 6265bis.
- [I] T4 Per-session isolation invariant: no state (cookie jar, arenas, caches, selector cache, `CorsStore`, `SingleFlight`) shared across Worker threads without a lock. Verify via ownership types; check shared `App` fields.
- [I] T5 WebSocket frame parser (WS.zig): checked arithmetic on 64-bit length (GHSA-7c5w).
- [I] T6 Request-filter completeness: every outbound path (fetch, XHR, WS, redirects, DNS rebinding after resolve) goes through IpFilter/UrlBlocklist; prior p5 finding shows WS bypass.
