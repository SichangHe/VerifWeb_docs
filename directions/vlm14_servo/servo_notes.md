(authored by agents unless marked 🧑)
# Is Servo a good base for a Verus-verifiable agent browser?
Labels: [F] fact (quote + source), [I] inference, [O] opinion. Nothing built or run; nothing published.
Web tools return summaries, so quotes marked "(tool)" are not guaranteed verbatim.

## Answer
- [O] Servo is the best candidate for "Rust, so Verus can apply", but Verus reaches only a small slice of it. The JS engine, the unsafe DOM/JS glue, floats and interior mutability are outside what Verus handles today.
- [I] Building on Servo gives Rust code for layout, style, net and policy, not for the engine that runs untrusted JS. A Quark-style plan (verify a small policy kernel, keep the engine untrusted) fits Servo as well as Lightpanda.
- [O] Cheaper alternative: use Servo as an untrusted renderer/JS host behind a small new Rust kernel written in Verus.

## Servo facts
Maturity
- [F] "Servo is a prototype web browser engine written in the Rust language." (https://github.com/servo/servo README, tool). MPL-2.0, 38.4k stars, 59,206 commits.
- [F] "v0.1.0 of the servo crate"; "this release is not a 1.0 release."; "breaking changes in the regular monthly releases are expected" hence an LTS. (servo.org blog 2026-04-13, listed at https://servo.org/blog/; tool)
- [F] Wikipedia lists the latest stable as 0.4.0 / 31 July 2026 (via web search; I did not open it).
- [F] "64-bit Linux, 64-bit macOS, 64-bit Windows, Android, and OpenHarmony" (https://book.servo.org/, tool).
- [F] "Work is still ongoing to make Servo consumable as a webview library." (https://book.servo.org/, tool)

Size and non-Rust parts (local shallow clone /tmp/vlm13/servo, commit 3bf3e0bf, 2026-11-08)
- [F] 1738 .rs files, 577,528 lines of Rust (`git ls-files | grep '\.rs$' | xargs cat | wc -l`). vlm13 said ~569k for components/ + ports/ only.
- [F] Tracked test data: 77,779 .html and 63,520 .js files (WPT), 3,460 .py.
- [F] Only 5 tracked C/C++ files; none under components/.
- [F] SpiderMonkey is external: Cargo.toml:146 `js = { package = "mozjs", version = "=0.26.14", default-features = false, features = ["intl", "libz-sys"] }`. It is C++ with a JIT. Servo also links C libs harfbuzz, freetype, fontconfig (out/vlm13_check/REPORT.md).
- I don't know SpiderMonkey's line count (not measured). [I] It is likely larger than Servo's own Rust.

Unsafe
- [F] 2255 lines in components/ + ports/ contain the word `unsafe` (grep): script 851, script_bindings 657, webgl 274, fonts 127, servoshell 72, media 48. Same as vlm13.
- [F] ~0.4% of Rust lines by keyword (2255/577k). This counts comments and `unsafe impl`/`extern`, and says nothing about how much code depends on unsafe invariants.
- [I] script + script_bindings = 1508 of 2255 (67%): unsafe sits at the DOM/SpiderMonkey boundary, where untrusted JS meets Rust.
- [F] Servo paper (ICSE 2016, https://arxiv.org/abs/1505.07383; paraphrase via tool): raw pointers for SpiderMonkey "are still a source of bugs and one of our largest areas of unsafe code".

Embedding API
- [F] components/servo/ is the library crate: servo.rs, webview.rs, webview_delegate.rs, site_data_manager.rs, user_content_manager.rs, network_manager.rs, javascript_evaluator.rs.
- [F] components/servo/webview.rs:744 `pub fn evaluate_javascript<T: ToString>(`; :773 `pub fn take_screenshot(`. Both are what an agent driver needs.
- [F] One example: components/servo/examples/winit_minimal.rs.
- [F] Sovereign Tech Fund grant "Total Funding: €545,400.00, Managing Organization: Igalia", covering WebView API completion, accessibility, maintenance (https://biggo.com/news/202510101915_servo-sovereign-tech-fund-accessibility-webview; secondary, via search).
- I don't know whether Servo ships a CDP or WebDriver server for agents; I did not check.

Headless
- [F] ports/servoshell/prefs.rs:71-73: "Whether or not to run servoshell in headless mode. While running in headless mode, image output is supported."
- [F] components/servo/tests/common/mod.rs:13,37 use `SoftwareRenderingContext` (no window).
- [I] Headless is possible via servoshell and a software rendering context. I did not run it; I don't know its robustness.

Activity and funding
- [F] Monthly posts, latest "September in Servo: <progress>, rounded rectangles, and more!" dated 2026-11-05 (https://servo.org/blog/, tool).
- [F] "Servo is an independent project hosted at Linux Foundation Europe and managed openly by the Technical Steering Committee." and "The project finally moved to Linux Foundation Europe in 2023" (https://servo.org/about/, tool).
- [F] Donations via "GitHub, Open Collective, thanks.dev, and Benevity"; "at 10,000 USD/month, we can sponsor a developer to make Servo their top priority"; "There are currently no members of the Linux Foundation Europe Directed Fund's Governing Board." Infra sponsors: GitHub, Zulip, AWS Open Source. (https://servo.org/sponsorship/, tool)
- [F] Post 2026-09-15 "Your Donations at Work: One Year of Sponsored Servo Development", summary "Looking back on Servo's first donation-funded role." I could not read its body, so I don't know the amount.
- [F] "Igalia got external funding in 2023 to work on Servo" (search summary of https://blogs.igalia.com/mrego/servo-revival-2023-2024/). Igalia is not named on servo.org /about or /sponsorship (tool).
- [I] Funding is small versus Chromium/Gecko (one donation-funded role, one grant, Igalia/Huawei staff). It is a dependency risk.

Web compatibility (WPT)
- [F] "The overall pass rate went from 40.8% in April 2023 to 62.0% by late 2024." (search summary, secondary).
- [F] A third-party blog (May 2026) puts Servo at about 78% and says "a general-purpose desktop browser is 5+ years out" (https://ttlab.hopto.org/blog/culture/2026-05-14-browser-engines-2026-chromium-gecko-webkit-servo-ladybird-comparison-deep-dive, via search; not Servo's number, metric unknown, treat as weak).
- [F] servo.org/wpt scores "total enabled tests within the suite that pass" (tool). Its charts and wpt.fyi are JS-rendered, so I could not read current figures. I don't know the current overall rate or comparable numbers for Ladybird.
- [I] Recent post titles (CSS Grid, SharedWorker, user scripts, text selection) show core features still landing, so gaps remain.

## Verus applicability to Servo (local work)
- [F] out/vlm_servo/SUMMARY.md: bounded arithmetic safe-Rust pieces took "about 25–35 min of agent time and 6–14 verify runs"; code with unsafe, raw pointers, generic numeric traits or floats "has to be rewritten first".
- [F] out/vlm3_servo/SUMMARY.md: proofs on cssparser tokenizer, layout fragment tree/algorithms, pixels, smallbitvec (96 obligations); 4 likely bugs found (not filed). Blockers: floats not modelled; "interior mutability (atomics, `Cell`, `OnceCell`, `ArcRefCell`) is unsupported"; missing vstd specs for raw-pointer/mem functions.
- [F] out/vlm11_jsengine/REPORT.md: "a whole verified engine is not doable now; a verified slice is".
- [I] Reachable: pure leaf logic (style, layout geometry, parsers, MIME sniffing). Not reachable: script/script_bindings, SpiderMonkey, webgl, font FFI.
- [I] A verified crate linked to unverified SpiderMonkey proves nothing across the JS boundary unless that boundary is specified and trusted.

## Candidate comparison
Servo
- Rust; JS SpiderMonkey (C++) via mozjs; pre-1.0 (0.x, monthly breaking changes); MPL-2.0; Verus: partial (above).
Lightpanda
- [F] "A new browser, written in Zig."; "Javascript support (v8)"; "AGPL-3.0 license"; CLA required; 41.6k stars; nightly builds (https://github.com/lightpanda-io/browser, tool).
- Verus: not applicable to Zig. vlm13: only an experimental Zig verifier (zirakzigil, 1 star). Needs a model or Rust rewrite.
- Built for agents; 11 security advisories in 6 months (out/vlm11_agentbrowser/REPORT.md).
Ladybird
- [F] "Truly independent web browser"; "Ladybird is licensed under a 2-clause BSD license."; "LibJS: JavaScript engine."; "Ladybird is in a pre-alpha state, and only suitable for use by developers." 66.9k stars (https://github.com/LadybirdBrowser/ladybird, tool).
- Language: C++ from my background knowledge, not verified here; the tool saw Rust config files, so some Rust may exist (extent unknown). Verus: no for C++. Own JS engine (LibJS).
Chromium headless / CEF
- [F] "Since Chrome 132.0.6793.0 the old Headless mode is only available as a standalone binary named chrome-headless-shell." and new mode "unified Headless and headful modes" (https://developer.chrome.com/docs/chromium/headless, tool).
- C++ with V8, BSD-style license, most compatible and mature (background knowledge; CEF page fetch failed, so unverified). Verus: no. Best compat, worst for verification.
Blitz (Dioxus)
- [F] "A radically modular HTML/CSS rendering engine"; "Blitz is currently in a beta state."; "We don't yet have Blitz bindings for other languages (JavaScript, Python, etc)"; "dual licensed under the Apache 2.0 and MIT licenses." 4.4k stars (https://github.com/DioxusLabs/blitz, tool).
- Rust, no JS engine. Verus: friendliest but cannot run most real sites. Headless/screenshot: not documented on the page; I don't know.

## Needs the human's judgment
- Goal A "agents browse the real web" needs JS and compat (Chromium, Servo, Lightpanda). Goal B "agents get a verifiable kernel" works over any base.
- I don't know: SpiderMonkey LOC, current Servo WPT %, Servo CDP/WebDriver status, the Sept 2026 funding amount.
