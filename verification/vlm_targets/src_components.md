# Non-JIT browser failures suited to Rust verification (Servo / Lightpanda)
(authored by agents unless marked 🧑)

Date of research: 2026-11-03. Quotes verbatim from fetched pages. "UNVERIFIED" = not confirmed from a primary source this session.
Servo source checked by shallow clone (HEAD 2026-11-04): `components/{url,net,script,script_bindings,layout,...}`. `url`, `html5ever`, `stylo` are external crates (rust-url, servo/html5ever, servo/stylo), not in servo/servo.

## Servo status
- Releases: GitHub API lists v0.7.0 (2026-10-05) and v0.6.0 "(LTS)" (2026-09-29). Release note: "Servo v0.7.0 is ready, containing all the changes from September." https://github.com/servo/servo/releases/tag/v0.7.0 . Cadence: monthly-ish. The 6-day gap between the two tags is odd; UNVERIFIED which dates are right (search snippet gave inconsistent age).
- WPT: https://servo.org/wpt/ renders dynamically; no current number retrieved (UNVERIFIED for 2026). Last figure found: Igalia "Servo 2025 Stats", Jan 1 to Dec 31 2025: score 48.2% -> 61.6%; subtests 69.9% -> 93.4% (1866247/1998146). Servo runs only enabled tests, so not comparable to wpt.fyi. https://blogs.igalia.com/mrego/servo-2025-stats/ (figures via search snippet, UNVERIFIED by direct fetch).

## 1. URL parser differential (SSRF): Orange Tsai, "A New Era of SSRF" (BH USA 2017)
- URL: https://www.blackhat.com/docs/us-17/thursday/us-17-Tsai-A-New-Era-Of-SSRF-Exploiting-URL-Parser-In-Trending-Programming-Languages.pdf
- Quote (slide): "It's all about the inconsistency between URL parser and requester"; also "The problem relied on URL parser and URL requester use different IDNA standard".
- Class: two components parse one string with different grammars (validator vs fetcher), so the validated host differs from the contacted host.
- Property: for all input s, host(parse_check(s)) == host(parse_fetch(s)); equivalently the parser equals the WHATWG URL state machine on all inputs.
- Servo: `url` crate (external, servo/rust-url); wrapper `components/url/lib.rs` (ServoUrl), `components/url/origin.rs`; fetch in `components/net/fetch/`.

## 2. URL: rust-url vs WHATWG, servo/rust-url#1130 (also hit Lightpanda #2794)
- URL: https://github.com/servo/rust-url/issues/1130 (open)
- Quote: "rust-url tries to remove the trailing slash, but last_slash_can_be_removed("/y/z/C:/") sees the last dir is a drive letter (/C:/)"
- Class: file-scheme-only special case (Windows drive letter) applied to all schemes.
- Property: for non-file base, parse("..", base="abc://x/y/z/C:/") == "abc://x/y/z/". More generally, Url::join == WHATWG basic URL parser.
- Related open rust-url issues (titles only, same class): #1155 "A backslash wrongly ends the port of a non-special URL", #1156, #1160, #1144 "`set_host(Some(\"\"))` produces a URL that then fails to re-parse" (round-trip property parse(serialize(u)) == u violated), #1174 "Invalid slice range on `password()` after `set_host(\"\")`" (panic/index OOB), #1163 quadratic parse.
- Lightpanda #1111 (https://github.com/lightpanda-io/browser/issues/1111), title "Invalid URL parsing": accepts `new URL("://foo.bar/path?query#fragment")` with protocol ":", Chrome throws TypeError. Class: missing scheme-start validation. Property: scheme matches [A-Za-z][A-Za-z0-9+.-]*.

## 3. HTML sanitizer mXSS: DOMPurify CVE-2024-47875
- URL: https://github.com/advisories/GHSA-gx9m-whjm-85jf
- Quote: "DOMpurify was vulnerable to nesting-based mXSS" (advisory gives nothing more).
- Companion CVE-2024-45801 (https://github.com/advisories/GHSA-mmhx-hmjr-r674): "malicious HTML using special nesting techniques can bypass the depth checking"; "It was also possible to use Prototype Pollution to weaken the depth check."
- Class: parse-serialize-reparse is not idempotent; sanitized DOM serializes to a string that parses to a different tree, and the depth guard is bypassable.
- Property: for sanitizer S, parse(serialize(S(parse(h)))) == S(parse(h)) (tree fixed point), and S output has no script-capable nodes.
- Servo: html5ever (external) tree builder; glue `components/script/dom/servoparser/{html.rs,async_html.rs,mod.rs}`; serialization in html5ever serialize + `components/script/dom/element.rs` (innerHTML; path UNVERIFIED).

## 4. Rust-in-browser memory safety: Servo GC/finalizer bugs (unsafe + SpiderMonkey interop)
- servo/servo#24621 "Crash during final GC with webgl content": https://github.com/servo/servo/issues/24621
  Quote (truncated by me at 125 chars): "This is another instance of the problem with doing things in DOM object destructors that requires interacting with other DOM…"
- servo/servo#15318 "Shutting down Servo with a native Promise object alive crashes during GC": https://github.com/servo/servo/issues/15318
  Quote: "When we do the final GC when shutting down a JS runtime, if there's a native `Rc<Promise>` alive then its destructor will run…"
- Class: Drop code dereferences GC-managed objects that the collector may already have finalized (use-after-free through unsafe trace/finalize contract).
- Property: Drop of a DOM-reflector-backed type touches no other GC object; every reachable GC pointer is rooted or traced (Trace is complete).
- Servo: `components/script` (dom_struct, `JSTraceable` derive in `components/jstraceable_derive`, `components/script_bindings`, `components/dom_struct`).
- Firefox: no specific unsafe-Rust CVE found. Only: Mozilla Hacks 2019 "Implications of Rewriting a Browser Component in Rust" (https://hacks.mozilla.org/2019/02/rewriting-a-browser-component-in-rust/): style component had 69 security bugs, 51 of them "not possible" in Rust (my search-snippet summary, UNVERIFIED quote). WebRender CVEs exist (e.g. CVE-2026-118023, Bug 2079499) but language of the bug UNVERIFIED.

## 5. Servo layout/script crash and cookie/CSP items (Servo tracker)
- #30116 "Unexpected CRASH in /html/semantics/forms/the-input-element/input-form-detach-style-crash.html": https://github.com/servo/servo/issues/30116 . Quote: "This only seems to trigger in Layout 2013:" ; panic in window.rs on condition PaintPostponed. Class: unreachable-state assertion violated after DOM detach. Property: layout/paint state machine total over detach events. Code: `components/script/dom/window.rs`, `components/layout`.
- #25600 "Implement SameSite cookies" : https://github.com/servo/servo/issues/25600 . Quote: "Servo currently has no concept of them at all." (old; state in the 2026 tree is open per search; partial support likely, UNVERIFIED). Property: Cookie accept/send decision matches RFC 6265bis (SameSite, Secure prefix, partitioned). Code: `components/net/cookie.rs`, `cookie_storage.rs`, `components/script/dom/cookiestore`.
- #45255 partitioned-cookies-samesite WPT intermittent: https://github.com/servo/servo/issues/45255 . Quote: "In embedded cross-site contexts, partitioned cookies can only be set with explicit SameSite=None". Same property/code.
- #8700 "Investigate first party cookies, cookie prefix, and insecure modification of secure cookies": https://github.com/servo/servo/issues/8700 . Property: a non-secure origin cannot overwrite a Secure cookie (RFC 6265bis 5.6 leave-secure-cookies-alone).
- CSP parsing: no concrete bug retrieved (one search was blocked by a safeguard). GAP; UNVERIFIED. Servo code: external `content-security-policy` crate usage in `components/script` (path UNVERIFIED).
- Stylo: external repo servo/stylo; no issue pulled. GAP.

## 6. Lightpanda correctness gaps vs Chrome
- #1180 "Tasks executed in incorrect order": https://github.com/lightpanda-io/browser/issues/1180 . Quote: "The following code executes microtasks (promises are also microtasks) and then macrotasks (timeouts) on Chrome, Firefox and Safari." Cause (issue text, paraphrased): single shared queue so timeouts run between microtasks. Property: HTML event-loop: after each task, microtask queue drains to empty before the next task. (Zig codebase, not Rust.)
- #1483 "`console.count` crashes the program": https://github.com/lightpanda-io/browser/issues/1483 (repro: `console.count();`). Property: Web IDL default-argument handling is total.
- #1480 segfault on Yahoo Finance after InvalidAttributeSelector exception: https://github.com/lightpanda-io/browser/issues/1480 . Property: error paths in selector engine leave no dangling state.
- #1515 "Improve CSS selectors": https://github.com/lightpanda-io/browser/issues/1515 . Quote: "we have couple of unsupported CSS selectors which you can encounter on `querySelector`, `querySelectorAll` and `matches`". Property: selector matching == Selectors L4 semantics.
- #1848 closing one CDP connection kills others (multiclient). Concurrency isolation property.
- Note: Lightpanda is Zig + V8, so Verus applies only to Servo-side analogues or reimplemented Rust pieces (url crate is the shared point: #2794 is a rust-url bug surfacing in Lightpanda).

## Best Verus targets (inference)
1. rust-url path normalization (`..`, drive letter, set_host round-trip): pure, small, specification is the WHATWG algorithm. Items 2.
2. HTML parse/serialize idempotence on a restricted grammar (item 3).
3. Event-loop microtask-drain invariant (item 6 #1180) as a state-machine model.
4. Cookie accept/send predicate in `components/net/cookie.rs` (item 5).
