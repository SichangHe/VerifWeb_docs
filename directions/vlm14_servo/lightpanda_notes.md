(authored by agents unless marked 🧑)
# What makes Lightpanda efficient? (read-only; nothing built, run, or published)
Labels: [F] fact (quote+source), [I] inference, [O] opinion. Sources: README = out/cx_maint/lightpanda/upstream/README.md (clone, main d4ad6b07, 2026-11-04); BENCH = https://raw.githubusercontent.com/lightpanda-io/demo/main/BENCHMARKS.md (fetched 2026-11-08); other src refs are from out/vlm11_agentbrowser/lightpanda.md (clone HEAD 6cfc29e1df1b), which I reused, not re-verified.

## Takeaway
[I] The efficiency comes mainly from what it leaves out (no Chromium multiprocess architecture, no full compositor/GPU pipeline), plus arena allocation and one-process multiplexing. Not from a faster JS engine: it uses V8, same as Chrome.
I did not find a blog post or profile attributing the gain to specific causes. I don't know the breakdown. I did not fetch lightpanda.io blog posts.

## Architecture
- [F] Not a fork. README:5-6 "Not a Chromium fork. Not a WebKit patch. A new browser, written in Zig."
- [F] Components. README:312-315 "HTTP loader ([Libcurl]...)", "HTML parser ([html5ever](https://github.com/servo/html5ever))", "Javascript support ([v8]...)". So V8 (via a project fork of zig-v8: build.zig.zon:8 `lightpanda-io/zig-v8-fork`), libcurl, and html5ever (Rust, from Servo). TLS: BoringSSL (build.zig.zon:29). Answers your questions: V8 yes; libcurl yes; html5ever yes.
- [F] DOM is native Zig, own implementation: src/browser/webapi/*, Frame.zig, Session.zig.
- [F] Rendering: README says "headless browser built from scratch for AI agents and automation". At HEAD there is partial layout/style/screenshot code (layout.zig, StyleManager.zig, screenshot.zig, RenderTree.zig). [I] Not a full Chrome-grade layout/paint pipeline; fidelity unknown, I did not run it. Older docs said no rendering.
- [F] Process/thread model. Server.zig:1293 "One thread driving a Browser."; Server.zig:593-599 spawns and detaches a thread per Worker; Env.zig:57 "The Env maps to a V8 isolate". Browser.zig:35-37 "A browser contains only one session."
- [I] One OS process; one thread + one V8 isolate per connection. No per-site processes, no OS sandbox (grep found none). Chrome pays for that with extra processes; this is a plausible main memory saving, and also why a crash kills all sessions (crash_handler.zig aborts the process).
- [F] Memory model. ArenaPool.zig:30 `BucketSize = enum { tiny, small, medium, large }`, free lists per bucket; Session takes `arena_pool.acquire(.small, "Session")` (Session.zig:167). Arena.zig:30 safety checks are debug-only. [I] Pooled arenas make allocation/free cheap and bulk. Cost: release builds lack checks; issue #2622 "double release of the pooled arena".
- [F] Workers off by default: Config.zig:297 "workers are now disabled by default".
- [F] Protocol: CDP over websocket (so Puppeteer/Playwright/chromedp drive it).

## Benchmark (vendor's own, not reproduced)
- [F] README headline table: "Requesting 933 real web pages over the network on a AWS EC2 m5.large instance." "Memory (peak, 100 pages) | 123MB | 2GB | ~16x less"; "Execution time (100 pages) | 5s | 46s | ~9x faster". Tagline: "16x lighter and 9x faster than Chromium."
- [F] BENCH methodology: crawl of the Amiibo demo site ("crawl the first page and then all the subpages to retrieve 933 URLs"), Go crawler using chromedp, "through internet connexion". Memory by `smem` PSS ("take shared memory pages into account"), CPU by `ps`, sampled every 100 ms with `watch -n0.1`; "we take the peak memory with its CPU percent". Chrome 143.0.7499.169 `--headless=new`; Lightpanda commit 7b1f157c. Machine in BENCH: "AWS m5.xlarge (x86_64)".
- [F] BENCH summary rows (duration | peak mem | CPU): Lightpanda 1 process 0:51.68 | 27.2M | 11.1%; 5 proc 0:11.70 | 43.9M; 25 proc 0:04.81 | 123.0M | 204.7%; 100 proc 0:05.23 | 410.2M. Chrome 1 tab 1:22.83 | 1.3G | 124.9%; 25 tabs 0:46.70 | 2.0G | 254%; 100 tabs 1:09:37 | 4.2G.
- [I] README's 123MB/5s and 2GB/46s match the 25-process / 25-tab rows (123.0M/4.81s vs 2.0G/46.70s), so the "100 pages" label does not match the data (933 pages, 25 workers). Also README says m5.large, BENCH says m5.xlarge. Discrepancies in the vendor's own docs; I don't know which is right.
- [F] Single-worker comparison (BENCH): 27.2M vs 1.3G (~48x less memory) but 51.68s vs 82.83s (~1.6x faster). [I] The 9x speedup arises from running 25 Lightpanda processes vs 25 Chrome tabs in one browser: Chrome's time stops improving after ~5 tabs (45.66s) while Lightpanda scales across processes. So "9x" compares scaling configurations, not per-page speed.
- Caveats [I]: one synthetic static-ish demo site hosted by the vendor, same domain; JS-light pages; network-bound; Chrome tabs share one browser while Lightpanda uses separate processes (not the single-process multiplexing described above); Chrome's 1-process baseline excludes tuned flags; no page-fidelity/correctness check reported; CPU % sampled at memory peak only. Vendor-run, single machine, no variance reported.
- Compatibility caveats [F]: issue #3182 "fundamentally single page-target + single browser-context"; #882 "multi contexts and multi pages is not supported"; partial Web API coverage (beta). [F] 11 security advisories 2026-05..11 (see vlm11 notes).

## Unknowns
Exact per-feature contribution; real-world site (JS-heavy) results; independent reproductions; whether blog posts add numbers.
