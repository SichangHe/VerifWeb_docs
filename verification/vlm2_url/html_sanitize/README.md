# ammonia 4.2.1 sanitizer: roundtrip / script-capability check (TARGETS.md target 8)

Authored by agents. Everything local; nothing filed or sent upstream (per human instruction).
Motivation: DOMPurify CVE-2024-47875 / 45801 (nesting-based mXSS, depth-check bypass).

## Setup
- crates: ammonia =4.2.1, html5ever =0.40.1 (fz/Cargo.toml; release, overflow-checks on)
- fz/src/lib.rs: checker. For c = clean(x): (a) clean(c)==c; (b) html5ever fragment parse+serialize (div, body) == c;
  (c) reparse c in 15 contexts (div/body/td/li/select/svg/math/doc, scripting on/off), flag elements outside the
  allow-list, hard-bad elements (script, style, iframe, ...), on* attrs, js/data URLs, srcdoc/style attrs
- configs: Default; Foreign (+svg/math family); RawText (+noscript, textarea, xmp, title, template, noembed, select, listing)
- fz/src/payloads.rs: 157 known mXSS payloads (DOMPurify/mXSS corpora, ammonia's own tests)
- p5/diff.mjs: differential vs node parse5 (scripting on/off, div/body fragment, full document)

## Commands
- build: `cd fz && cargo build --release`
- fuzz (structure-aware, coverage-ish corpus, minimizer): `fz/target/release/hsfz fuzz <default|foreign|rawtext> <secs> <threads> <outdir>`
- exhaustive token strings: `hsfz exh <cfg> <maxlen> ...`; payloads: `hsfz payloads <outdir>`; depth: `hsfz deep <outdir>`
- single input: `fz/target/release/one <cfg> '<html>'`
- parse5 diff: `fz/target/release/ser s.txt > h.txt; node p5/diff.mjs s.txt h.txt <cfg>`

## Runs (counts, durations)
- payloads: 157 payloads x 3 cfgs, <1 min (res/payload_results.txt, earlier agent)
- exhaustive over token alphabets (earlier agent, logs/exh_*.log): Default 22 tokens len<=5 = 5,399,042 execs, 219 s;
  Foreign len<=4 = 551,880 execs (~21 s); RawText len<=4 = 732,540 execs (~37 s)
- fuzz this session, 40 threads, 600 s each (res2/): Default 1,174,600 execs; Foreign 1,191,200; RawText 1,134,600
  (corpus 20k, 318k-393k distinct shapes). Total ~3.5M fuzz execs + ~6.7M exhaustive.
- parse5 differential: 20,000 sampled fuzz outputs each for Default and RawText (res3/), 5 parse modes each
- deep nesting (`hsfz deep`, depths 1..50000, 26 unit tags, 4 shapes, 3 cfgs, 1500 s cap): see "Deep nesting" below
- Kani: v0.68.0 installed (kani_try/install.log, setup.log). Harness compile on ammonia+deps fails with Kani ICE
  (`kani-compiler/src/intrinsics.rs:243 assertion failed`, kani_try/kani_run.log). No bounded proof obtained. Not retried
  (ammonia pulls in html5ever/icu/url; unbounded loops make a CBMC bound meaningless anyway).

## Findings
Verdict key: REAL = reproducible violation of the stated property; HARMLESS = violation, not script-relevant; FP = checker over-approximation.

1. REAL, config-dependent, XSS: allowing `noscript` (RawText cfg). Not default.
   - in:  `<noscript><img src=x onerror=alert(1)></noscript>`
   - clean (RawText cfg) = identical string. ammonia parses with scripting on, so noscript content is raw text and is
     emitted unescaped. A parser with scripting off (DOMParser, template/inert doc, email clients, JS-disabled browser)
     builds `<img src="x" onerror="alert(1)">` (parse5 scripting=false confirmed). Default cfg gives `&lt;img src=x onerror=alert(1)&gt;` (safe).
   - Same mechanism: `<noscript><l srcdoc=""` (minimized), unallowed elements/attrs/comments appear under scripting-off parse.
   - Upstream: ammonia source (src/lib.rs ~L2218-2231) already lists noscript among tags that "is parsed in RCDATA/RAWTEXT"
     and is dangerous to allow, but its guard targets namespace changes, not scripting-off. Class is known; this exact
     noscript+scripting-off case not confirmed documented (no network lookup made; not filed).
2. REAL, non-idempotent (property a, b), default cfg, no script capability found.
   - `<h2><h32><h3>` -> `<h2><h3></h3></h2>`; reparse gives `<h2></h2><h3></h3>`
   - `<a><table><a>` -> `<a rel="noopener noreferrer"><a rel="noopener noreferrer"></a><table></table></a>`; reparse flattens nested a
   - Cause: ammonia serializes a DOM that the HTML parser could never build (nested a/heading via adoption-agency/foster
     parenting; the fix-up happens on the second parse). This is the same family as DOMPurify nesting mXSS (tree not
     reparse-stable), so it is a precondition for mXSS. In default cfg every one of ~3.5M fuzz outputs and the 157
     payloads, scanned in 15 contexts, produced no script-capable node. Verdict: real invariant break, currently harmless.
     Frequency: ~6.5% of fuzz outputs.
3. HARMLESS: `&#xd` -> `\r` (raw CR in output); reparse normalizes CR to LF. parse5 shows the same (2032/20000 default samples).
4. FP: `<a href="JaVaScRiP\u{c}t:">`, `<a href="&#1javasc ript:">` kept. Browsers (WHATWG URL) strip only tab/LF/CR inside a scheme,
   not FF/SOH, so these are relative URLs, not javascript:. My checker strips all C0 before matching.
5. RawText cfg, scripting-on: comments and rt mismatches appear after reparse (92 and 2402 of 20000 samples, e.g. xmp/select/template
   inputs). Untriaged beyond "mutation"; same cause as 1 (allowing rawtext-ish tags). No exploit minimized.
6. Foreign cfg (svg/math allowed): only items 2-4 found; the documented foreignObject/xmp/table mXSS payloads
   (ammonia tests, DOMPurify 2.0.x) are neutralised.

## Deep nesting
- earlier agent's deep run died with empty output. This session's run was killed by the 1500 s timeout before finishing
  (no "deep cases=" summary line; progress not logged). res2/deep_results.txt is empty = no violation was written before the
  kill, but coverage of the depth grid is unknown. Deep nesting is therefore NOT established either way. Next step: log
  progress, split by depth, and run per-depth in parallel. html5ever tree depth is bounded only by stack/ammonia's recursion;
  not checked for stack overflow at 50000.

## Not done
- No Kani result (ICE). No browser (only parse5 and html5ever); parse5 spec-matches but is not Chrome/Firefox.
- Findings 1 and 5 not minimized beyond the shown strings in all 15 contexts; nothing reported upstream.
