# Lightpanda verification feasibility
(authored by agents unless marked 🧑)

Date 2026-11-03. Binary: nightly `1.1.0-nightly.11647+b8e234a77` (downloaded, untrusted, run only against localhost). Source: shallow clone of lightpanda-io/browser (HEAD commit dated 2026-11-03).

## Built
- `js/server.mjs`: two localhost origins, A (:8801, allowed) and B (:8802, forbidden), logs every request; 14 generated test pages
- `js/run.mjs <lightpanda|chrome>`: loads each page through puppeteer-core (CDP) and records DOM probe, termination, requests to B
- `js/diff.mjs`: differential Lightpanda vs Google Chrome 150 (headless); output in `js/diff_output.txt`
- `js/enforce.mjs`: runtime monitor in `fetch` mode: "no request reaches origin B", with and without `--block-urls`; output `js/enforce_output.txt`

## Run
`cd js; node run.mjs lightpanda; node run.mjs chrome; node diff.mjs; node enforce.mjs` (needs `npm i puppeteer-core`, done; Chrome at /usr/bin/google-chrome).

## Measured (fact, one run, 14 pages)
- all 14 pages terminated in both engines; Lightpanda ~410 ms, Chrome ~435 ms per page (dominated by my 400 ms settle sleep, so not a speed result)
- DOM/JS state identical on 8 pages incl. `dom_semantics` (implicit li/td/p closing, template, insertAdjacentHTML, classList) and `js_semantics` (flat, toSorted, structuredClone, MutationObserver, etc. exist)
- requests to B: Lightpanda issued a subset of Chrome's on every page. It did not issue: `<img>`, `<iframe>`, CSS `@import`/`url()`, `sendBeacon`. Cause (fact, from `help`): `--load-resources` default is none of them in `serve`/`fetch`. Script, fetch, XHR, document.write script, meta refresh, 302 redirect, WebSocket all reached B.
- `display_contents`: `getBoundingClientRect().width` of a table under `display:contents`: Lightpanda 5, Chrome 29.09. Lightpanda has a `layout.zig` but no real layout (belief: estimates sizes). This is the same family as the "visible descendants lose their box" failure in `WEB_FAILURE_TARGETS.md` section 1.
- meta_refresh/redirect: node-count diff 4 vs 3 on the empty B document (Lightpanda adds one node; not investigated)
- origin monitor, `fetch --wait-ms 500`: no flag: B received 6/7 attack pages. With `--block-urls '*127.0.0.1:8802*'`: 1/7 still reached B: the WebSocket upgrade `GET /ws` from `new WebSocket('ws://127.0.0.1:8802/ws')`. Fact for this one pattern and build; belief: `--block-urls` is not applied to WebSocket. Not reported upstream; check before claiming a bug.

## Codebase (fact, `wc -l`)
- Zig: 690 files, 300k lines; 10k is `public_suffix_list.zig` data, so ~290k real. Largest: `network/HttpClient.zig` 6.9k, `browser/Frame.zig` 4.7k, CDP `input.zig` 4.3k, `StyleManager.zig` 4.0k.
- Rust: 4.4k lines under `src/rust` (html5ever wrapper, `render`). 603 HTML test files in `src/browser/tests`.
- Dependencies (build.zig.zon): V8 (zig-v8-fork), curl, nghttp2, boringssl, brotli, zlib, zstd, sqlite3. Needs Zig 0.17.0 (not installed; I did not build from source).

## Architecture
- Zig: process/CLI, CDP server (`server/cdp`, 22 domains), HTTP stack glue (`network`), DOM and Web API (`browser/webapi`, ~116k lines), script loading (`ScriptManager`), V8 bindings (`browser/js`, 74 files mention v8), cookies, MCP/agent modes.
- C++/Rust: V8 (JS execution, GC, Promise/microtask), curl/BoringSSL, html5ever (HTML parsing).
- So the DOM is reimplemented in Zig; only the JS language is V8. JS-visible DOM behaviour is Zig code exposed through bindings.

## Verification targets by size (belief)
- small, pure, good first targets: `URL.zig`, `Mime.zig`, `cookies.zig`, `datetime.zig`, `string.zig`, `Regex.zig`, `Arena*.zig`, `css/` selector parsing, `data_url.zig`, `referrer.zig` (URL/cookie/CORS logic is crawler-relevant and spec-defined)
- medium: block-list/URL filter and request interception (`network`, `fetch.zig`); this is where the WebSocket miss lives
- not tractable: `Frame.zig`, V8 bindings, HttpClient
- Zig verification tools: none found. `verus/dafny/cbmc/klee` not installed here. Belief (from memory, not rechecked): no mature Zig verifier exists. Realistic routes: Zig `test` + fuzzing (std.testing.fuzz), differential testing against a reference (Chrome, WHATWG tests / WPT), or reimplement a pure module in Rust/Dafny and check conformance.

## Blockers
- no Zig toolchain, no verifier; building needs Zig 0.17 + V8 prebuilt download (not attempted)
- Chrome as oracle only approximates the spec; Lightpanda intentionally differs (no layout, resources off)
- single run, 14 hand-made pages, localhost only; no real-site testing; timing nondeterminism not examined

## Differentiators (belief)
- smaller target than Chromium (300k vs ~35M lines), actively developed (HEAD today) but company-backed project; meeting's "alive in a year" is unknowable
- crawler/agent threat model is explicit and checkable: egress control, termination, state fidelity, deterministic semantic tree; Chrome has no such narrow contract
- DOM in memory-unsafe-ish Zig with manual allocators: bug class (memory, URL/origin parsing) differs from Chromium's, and is testable without V8
- natural next step: WPT URL/cookie/DOM subset differential run, and the `--block-urls` vs WebSocket/redirect-chain enforcement check
