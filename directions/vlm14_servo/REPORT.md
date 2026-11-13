# Browser base for an agent browser: Servo, Lightpanda, alternatives
(authored by agents unless marked 🧑)

Labels: [F] fact (quote + source in the notes files), [I] inference, [O] opinion. Evidence with verbatim quotes and URLs: `servo_notes.md`, `lightpanda_notes.md` (this directory). Reading/search only; nothing built, run, or published.

## Direct answers
🧑 "Is Servo a good target?"
- [O] Yes, as the best Rust option, but not as "verify the browser". Verus can reach only small leaf parts of it.
- [F] it is a prototype: README "prototype web browser engine"; crates.io v0.1.0, "not a 1.0 release"
- [F] its JS engine is SpiderMonkey (C++), via the `mozjs` crate; 67% of Servo's `unsafe` lines sit at the DOM/JS boundary (`script`, `script_bindings`)
- [I] so a Verus proof on Servo code says nothing about what crosses into SpiderMonkey

🧑 "would it be a good idea to develop a browser for agents on top of Servo?"
- [O] only in a Quark-style split: a small Verus-verified Rust kernel (session isolation, request policy, cookies, URL origin) that treats Servo as an untrusted renderer + JS host
- [I] this reuses Servo's Rust ecosystem (url, cssparser, html5ever) where Verus applies, without needing Servo itself to be correct
- [O] risks: unstable embedding API, unknown web-compat level, small funding

🧑 "What's special about lightpanda that makes it so efficient?"
- [I] mostly what it leaves out, not a faster engine: no Chrome multiprocess design, no full rendering pipeline, one process with one thread + one V8 isolate per connection, pooled arena memory
- [I] its headline "~9x faster" compares 25 Lightpanda processes vs 25 tabs in one Chrome; with one worker each it is ~1.6x faster and ~48x less memory
- [F] the benchmark is the vendor's own: one synthetic demo site, one machine; no variance or correctness check reported

## Servo facts
- [F] size: 577,528 Rust lines (local clone, commit 3bf3e0bf, 2026-11-08); 2255 lines contain `unsafe` (~0.4%)
- [F] embedding: `components/servo` library crate with `WebView::evaluate_javascript`, `take_screenshot`; book: "Work is still ongoing to make Servo consumable as a webview library."
- [F] headless: servoshell headless flag + software rendering context; robustness unknown (not run)
- [F] funding/activity: hosted at Linux Foundation Europe; GitHub Sponsors + Open Collective; "first donation-funded role" (2026-09-15 post); monthly posts through 2026-11-05
- web compat: I don't know the current WPT pass rate; only a 62.0% figure (late 2024) and a third-party ~78% were found
- I don't know whether Servo exposes CDP (what Puppeteer/Playwright speak); WebDriver status is also unknown

## Alternatives
- Lightpanda: Zig + V8, AGPL-3.0, built for agents (speaks CDP); Verus does not apply; 11 security advisories 2026-05..11; issue #3182 "fundamentally single page-target + single browser-context"
- Ladybird: own engine and JS (LibJS), BSD-2, "pre-alpha state"; C++ (agent background knowledge, not checked) so no Verus
- Chromium headless / CEF: best compat (background knowledge); C++, no Verus; cost is the 1.3G-per-worker class footprint Lightpanda measured
- Blitz (Dioxus): Rust, Apache-2.0/MIT, "beta", no JS engine; most Verus-friendly, cannot run most real sites

## Takeaway
- [O] the verifiable, novel piece is the policy/isolation kernel, whatever engine sits below; Servo is the natural engine if the kernel is in Rust/Verus
- [I] Lightpanda shows the efficiency target is reachable by deleting rendering + process overhead; its bug record shows that same policy core is where it breaks
