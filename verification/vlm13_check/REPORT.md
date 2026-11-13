# vlm13_check: fact-check of msg_answers.txt sections 3-4
(authored by agents unless marked 🧑)

Read-only check. Servo numbers come from a shallow clone of servo/servo (commit 3bf3e0bf, 2026-11-08), made in /tmp/vlm13, using grep.

## Section 3 (Servo / memory bugs)

1. "Servo has unsafe code (FFI, layout, GC glue)": mostly correct
   - fact (grep): 2255 lines contain `unsafe` in components/ + ports/. 2159 of them are `unsafe {`/`fn`/`impl`/`extern`. They sit in 203 of 1639 .rs files. Total Rust code is 569k lines.
   - fact: the biggest share is in the JS/DOM glue: script has 93 files, script_bindings 33, shared 17, fonts 10. Layout is not a main source, so "layout" in the belief is weakly supported.
   - Servo paper (Anderson et al., ICSE 2016, https://arxiv.org/abs/1505.07383), as paraphrased by the search tool, not my own verbatim quote: raw pointers used "to interoperate with the SpiderMonkey JavaScript engine ... are still a source of bugs and one of our largest areas of unsafe code"
   - Josephine (https://arxiv.org/pdf/1807.00067), as paraphrased by the search tool: "nearly 400 instances of unsafe code in the Servo DOM implementation"
2. "JS engine is SpiderMonkey, C++, plus JIT": correct
   - fact: Servo's Cargo.toml has `js = { package = "mozjs", version = "=0.26.14", ... }`. mozjs wraps SpiderMonkey, which is C++.
   - fact: Servo also links C libraries: harfbuzz-sys, freetype-sys, and fontconfig (yeslogic-fontconfig-sys)
3. "most real browser escapes are in engines and JITs": unsupported as stated
   - Chromium (https://www.chromium.org/Home/chromium-security/memory-safety/): "around 70% of our serious security bugs are memory safety problems" and "These bugs are spread evenly across our codebase." The count covers 912 high/critical bugs since 2015.
   - so vendor data says memory bugs are about 70% and spread across the codebase, not concentrated in engines or JITs. I found no vendor breakdown by component.
   - Mozilla, Firefox style component (https://hacks.mozilla.org/2019/02/rewriting-a-browser-component-in-rust/): "there have been 69 security bugs in Firefox's style component", "51 (73.9%) of these bugs would not have been possible" in Rust, "Of the 34 critical/high bugs, 32 were memory-related."
   - suggested fix: "about 70% of serious Chrome bugs are memory-safety bugs, spread across the codebase; the JS engine is a large C++ part that Rust does not cover"
4. "Spectre ignores memory safety": correct (common knowledge, no source fetched)
5. prior work arguing isolation for Rust browsers: exists
   - Servo design wiki (https://github.com/servo/servo/wiki/Design), as paraphrased by the search tool: Rust's type system does not make a sandbox less important "to defend against unsafe code, bugs in the type system, and third-party/host libraries"
   - RLBox, which isolates C libraries inside Firefox: https://arxiv.org/pdf/2003.00572
   - SDRaD-FFI, which uses MPK to isolate unsafe Rust and C inside one process: https://arxiv.org/pdf/2306.08127
   - the conclusion "isolate the engine or verify the glue" is consistent with these (opinion)

## Section 4 (Zig verification)

"no mature verifier exists for Zig": correct, but one experimental verifier exists
- zirakzigil (https://github.com/hotschmoe/zirakzigil) has 1 star and results dated 2026-10-28. Quotes as returned by the fetch tool: its SMT verifier zvc targets "Functional correctness and absence of every safety panic". Limits: "pointers other than to locals, floats, enums, unions and recursion are reported UNPROVEN". Its ownership checker: "four adversarial reviews and an overseer review found silent misses each time"
- linters/static analyzers only (Ziggit, "Does Zig have a static code analyzer?", https://ziggit.dev/t/does-zig-have-a-static-code-analyzer/16451): zlint, ziglint, zwanzig (CFG analysis, "not very advanced yet")
- not searched: Google Scholar, the Zig issue tracker. One web search only.

## Caveats
- Fetch/search results pass through a summarizing tool. Quotes marked "as paraphrased" are not guaranteed verbatim. The Chromium and Mozilla quotes came back marked as exact.
