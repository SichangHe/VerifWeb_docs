# sizes: is a formally verified js engine doable now with ai agents?

(authored by agents unless marked 🧑)

notes
- LOC = non-blank non-comment lines from `tokei` (v from nix profile) unless I say `wc -l`. clones are `--depth 1`, in out/vlm11_jsengine/src/. pdfs/texts in out/vlm11_jsengine/pdf/.
- "quote" = verbatim from the source. items marked [search-relayed] were quoted by the web-search tool, not read by me in the pdf; recheck before reuse.
- nothing was published or filed.

## 1. small real js engines (measured)

- boa (rust). github.com/boa-dev/boa @329e897 2026-10-31
  - `tokei boa/core -t=Rust`: 166,679 rust code lines in core/ (includes inline `#[cfg(test)]` unit tests; not separable cheaply)
  - by crate (`tokei boa/core/<crate> -t=Rust`): engine 105,548 (of which src/builtins 51,491), parser 24,669, ast 17,579, runtime 6,240, string 3,762, gc 2,968, interner 665
  - separate tests dir `tokei boa/tests`: 3,910 (mostly js)
  - test262: README.md line 20: "Boa is an experimental JavaScript lexer, parser and interpreter written in Rust, it has support for **more** than 90% of the latest ECMAScript specification."
  - test262: https://boajs.dev/blog/2025/10/22/boa-release-21 : "In this release, our conformance has grown from 89.92% to 94.12% in the official ECMAScript Test Suite (Test262)."
  - newer figure: 96.03% (51,450 of 53,578 pass, 1,648 ignored, 480 fail) from a CI bot report in a third-party fork PR https://github.com/hassidan/boa/pull/1 dated 2026-10-31 [search-relayed; fork, not official]. 95.5% from a maintainer talk https://gitnation.com/contents/building-a-javascript-engine-in-rust-lessons-from-boa [search-relayed]
  - caveat: "ignored" tests are excluded from the denominator.
- nova (rust). github.com/trynova/nova @591bf7b 2026-11-07
  - `tokei nova/nova_vm`: 117,421 rust code lines (src/ecmascript/builtins alone: 57,395). tests/ dir holds the test262 runner, not counted.
  - test262, self-reported at https://trynova.dev/test262 (as of 2026-05-10): "40515 (79.9%)" pass, "6785 (13.4%)" fail, "3326 (6.6%)" skip.
  - repo file nova/tests/metrics.json (my arithmetic): pass 40692 / total 53616 = 75.9%; 83.9% if the 5127 skipped are excluded.
  - caveat (HN thread https://news.ycombinator.com/item?id=44126264, maintainer aapoalas, per search tool [search-relayed]): runner skips Annex B and Intl; test262.fyi showed 58.7% then vs ~70% self-reported.
- quickjs (c). github.com/bellard/quickjs @092277a 2026-11-07
  - `tokei quickjs`: C 148,517 + C headers 8,580 + js 7,349 (whole repo, includes tests/, examples, unicode tables, fuzz)
  - `wc -l` (incl. blanks/comments) core files: quickjs.c 65,783; libregexp.c 3,448; libunicode.c 2,131; quickjs-libc.c 4,500; cutils.c 641 = 76,503
  - tests: `tokei quickjs/tests` 5,189 lines
  - test262: no % stated in the repo (readme.txt, Changelog). repo has test262_errors.txt (19 lines, `wc -l`) of known failures and test262.conf (335 lines).
- lightpanda (zig). github.com/lightpanda-io/browser @6cfc29e 2026-11-07
  - embeds google v8, not its own engine. browser/README.md: "- [x] Javascript support ([v8](https://v8.dev/))"; build.zig.zon fetches "zig-v8-fork".
  - `tokei browser/src/browser/js -t=Zig`: 10,108 zig code lines = the v8 binding glue layer (Isolate, Context, Local, Module, Promise, Snapshot...)
  - for scale: `tokei browser/src/browser -t=Zig` 142,821; `tokei browser/src -t=Zig` 233,542 (includes the web-api bindings outside js/)
  - test262: no figure (v8 passes whatever v8 passes).
- engine262 (typescript). github.com/engine262/engine262 @18cdeb0 2026-11-05
  - `tokei engine262/src`: 53,999 typescript code lines (src/intrinsics = builtins: 16,168); `tokei engine262/test`: 4,236
  - README.md: "- 100% Spec Compliance" (a goal, listed under "Goals"; not a measured test262 %).
- takeaway (inference): a conformant-ish engine in a safe language is ~55k-170k LOC; builtins are ~1/3 to 1/2 of it. no JIT in any of them except v8.

## 2. largest verified systems (code LOC / proof LOC / ratio / effort)

- verus sosp'24 (Lattuada et al.), pdf https://www.jaybosamiya.com/publications/2024/sosp/verus-sys.pdf
  - abstract: "6.1K lines of implementation and 31K lines of proof."
  - fig 9 rows (columns as I read them: trusted, proof, code, ratio): "Verus total 4692 31231 6119 5.1"; "Page table 1117 5329 400 13.3"; "Mimalloc 282 13703 3178 4.3"; "P. log 1284 2913 739 3.9"; IronKV Verus port "369 5237 736 7.1" vs the original Dafny "104 7828 730 10.7"
  - "of 400 lines of executable code, which required 5329 lines of proof, resulting in a relatively high 13.3:1 proof-to-code ratio."
  - cites atmosphere: "Verus to verify a full microkernel [26]; the authors report a 7.5:1 proof-to-code ratio."
  - "Hyperkernel reports 0.03:1" (restricted/automated style; low ratio by limiting expressivity).
- atmosphere sosp'25 (Chen et al.) https://dl.acm.org/doi/10.1145/3731569.3764821 [search-relayed; acm 403 to me]
  - "Development and verification of 6K lines of executable code required an effort of less than 2.5 person-years (only 1.5 years were spent on verification, another person-year was spent developing non-verified parts of the system)."
  - ratio "3.32:1" average. older 2023 figure 7.5:1 on https://mars-research.github.io/projects/atmo/ : "On average our code has proof-to-code ratio of 7.5:1".
- anvil osdi'24 (Sun et al.) https://www.usenix.org/system/files/osdi24-sun-xudong.pdf
  - "The verification effort is manageable, with the proof-to-code ratio ranging from 4.5 to 7.4 across the controllers."
  - per controller (usenix ;login: article, [search-relayed]): zookeeper verified impl 1134 / proof 8352; rabbitmq 1598 / 7228; fluentbit 1208 / 8395.
- verismo osdi'24 (Zhou et al.) https://sishuaigong.github.io/pdf/osdi24-verismo.pdf
  - "On average, the proof and specification annotations are approximately twice the size of the executable code for the implementation layer."
  - "Verification of both model and implementation layers takes around 6 minutes". no person-years stated that I found.
- ironfleet sosp'15 https://sigops.org/s/conferences/sosp/2015/current/2015-Monterey/250-hawblitzel-online.pdf
  - "At the implementation layer, our ratio of proof annotation to executable code is 3.6 to 1."
  - "In total, developing the IronFleet methodology and applying it to build and verify two real systems required approximately 3.7 person-years."
  - (cacm version reports 7.7:1 incl. liveness [search-relayed])
- sel4 sosp'09 https://www.sigops.org/s/conferences/sosp/2009/papers/klein-sosp09.pdf
  - "comprises 8,700 lines of C code and 600 lines of assembler."
  - "The overall size of the proof, including framework, libraries, and generated proofs (not shown in the table) is 200,000 lines of Isabelle script."
  - "The cost of the proof is higher, in total about 20 py. This includes significant research and about 9 py invested in formal language frameworks, proof tools, proof automation, theorem prover extensions and libraries. The total effort for the seL4-specific proof was 11 py."
  - ratio ~23:1 (200,000 / 8,700; my arithmetic).
- compcert (leroy, cacm 2009) https://xavierleroy.org/publi/compcert-CACM.pdf
  - "The whole Coq formalization and proof represents 42000 lines of Coq (excluding comments and blank lines) and approximately 3 person-years of work." (2009 snapshot; compcert is bigger now, not re-measured)
- cakeml icfp'16 https://cakeml.org/icfp16.pdf
  - "...development is approximately 100 000 lines of HOL4 proof scripts." (backend paper; not the whole project). no person-years found.
- takeaway (inference): human-written proof:code ratios are 3:1 (verus/dafny) to 23:1 (seL4 isabelle). verified systems stay at 6k-10k lines of code for ~2-4 person-years. a 100k-LOC engine at 5:1 would be ~500k proof lines.

### agent-written proofs (2025-2026)
- autoverus (Yang et al.) https://arxiv.org/pdf/2409.13082 : "AutoVerus can automatically generate correct proof for more than 90% of them [150 tasks], with more than half of them tackled in less than 30 seconds or 3 LLM calls." (small tasks: 137/150; gpt-4o baseline 67/150)
- vericoding benchmark (Bursuc et al.) https://arxiv.org/pdf/2509.22908 : "We find vericoding success rates of 27% in Lean, 44% in Verus/Rust and 82% in Dafny using off-the-shelf LLMs." (function-level specs)
- veruSAGE https://arxiv.org/pdf/2512.18436 : benchmark "consists of 849 proof tasks extracted from eight open-source Verus-verified Rust systems"; abstract: best combination "80% of system-verification tasks". (proof-only; code given)
- cryptoprover (Sun et al., 2026-10) https://arxiv.org/pdf/2608.00965 : "The original developers report a focused five-month, three-person effort to verify curve25519-dalek." and CryptoProver "synthesizes the internal specifications and proofs in 11.4 hours with $466.99 in recorded API cost." (given api contracts + trusted spec library; proofs for existing code)
- paraskevopoulou (2026-02) https://arxiv.org/pdf/2602.20082 : "The resulting ANF proof comprises approximately 7,800 lines of Rocq (larger than the 5,300-line CPS proof) and was developed in approximately 96 hours." (claude code + opus 4.6, "human guidance but without human proof writing"; template = existing human proof)
- rinard (2026-05) https://arxiv.org/pdf/2605.08927 : "the first verified compiler developed by a coding agent (operating under human supervision)"; "verification requires roughly an order of magnitude more development effort than credible compilation". table rows e.g. "CP VF 15 sessions ... +1,079 code, +6,131 proof (lean)"; "UCE+DAE VF 14 ... +734 code, +8,158 proof".
- vero (2026-08) https://arxiv.org/pdf/2608.13522 : "The strongest agent fully solves only 27 of 43 instances and closes no specifications on the hardest repositories."
- takeaway (inference): agents now write thousands of proof lines (~8k) in days when a template exists; no source shows an agent producing a 100k-line verified system from scratch. the hardest repos still fail.

## 3. formal js semantics, verified pieces

- spec size: `pdfinfo` on https://ecma-international.org/wp-content/uploads/ECMA-262_16th_edition_june_2025.pdf (ecmascript 2025): Pages: 847 (measured).
- algorithm steps (jiset, ase'20) https://plrg.korea.ac.kr/assets/data/publication/ase20-park-jiset.pdf : "the most recent version of ECMAScript (ES10, 2019) [7] has 2,026 abstract algorithms consisting of 10,101 steps." (es2019, not 2025)
- jscert/jsref (popl'14) https://www.chargueraud.org/research/2013/js/jscert_popl.pdf : es5 semantics in coq + extracted ocaml interpreter. "The proof of this theorem [jsref correct wrt jscert] consists of 3500 lines of Coq". test262: "There are 2782 tests associated with the core language (chapters 8-14): we pass 1796 tests". total jscert size not found in text.
- jsexplain (www'18) https://dl.acm.org/doi/10.1145/3184558.3185969 : ocaml-based es5 reference interpreter with double debugger. no LOC found.
- kjs (park/stefanescu/rosu, pldi'15) https://fsl.cs.illinois.edu/publications/park-stefanescu-rosu-2015-pldi.pdf : "KJS, the most complete and throughly tested formal semantics of JavaScript to date... has been tested against the ECMAScript 5.1 conformance test suite, and passes all 2,782 core language tests." (es5.1, k framework, executable, not proof-carrying). jiset paper: "it took four months to implement an AST-IR translator for 1,370 steps out of 2,932 steps in 368 abstract algorithms [24]".
- jiset/esmeta (spec-extracted) : jiset: "automatically compiled 95.03% of the steps in abstract algorithms on average" (es7-es10); "(ES10, 2019) passed all 18,064 applicable tests" after fixing spec errors. esmeta is its successor and is run in tc39 ci ("ESMeta was integrated into the continuous integration (CI) system of ECMA-262 on November 3, 2022" [search-relayed], github.com/es-meta/esmeta). it is an executable semantics, not a proof.
- lambda-js (guha et al. esop'10): not fetched; no numbers.
- warblre (de santo et al., icfp'24) https://arxiv.org/pdf/2403.11919 : coq mechanization of ecmascript regex (§22.2), "we have included as a comment, for each line of Coq code, the corresponding pseudocode line". paper's loc table: coq semantic mechanization 1810; infrastructure/types 788; termination+safety proofs 1392; nullable-opt proofs 477 (= 4,467 coq lines; my sum).
- linden (barriere et al., popl'26) https://arxiv.org/pdf/2507.13091 : "Our Rocq development, consisting of over 15k lines of definitions and proofs"; one key proof "over 6000 lines of Rocq". proves a backtracking-tree semantics and a pikevm faithful to warblre.
- vera (brown et al., pldi'20) https://cseweb.ucsd.edu/~dstefan/pubs/brown:2020:vera.pdf : smt-verifies firefox jit range analysis vs js semantics; "in 1384 lines of Haskell"; ported 22 routines (per search tool [search-relayed]); found a 6-year-old confirmed bug. one jit pass, not a whole jit.
- jit verification: coreJIT (popl'21) https://janvitek.org/pubs/popl21.pdf : "more than 12k lines of Coq" [search-relayed], toy speculation/deopt model. fm-jit (popl'23) https://arxiv.org/pdf/2212.03129 : "The entire Coq development represents around 15K lines we wrote, and includes more than 160K lines from CompCert." (model jit reusing compcert backend; no js).
- wasm: watt fm'21 https://conrad-watt.github.io/papers/watt2021.pdf : coq binary-format parser "come to ~800 lines of non-comment, non-whitespace code"; wasmcert-coq/isabelle are mechanizations of wasm 1.0 with verified interpreters (wasmref-isabelle used as a fuzzing oracle for wasmtime [search-relayed]). total sizes not found.
- searched, found nothing: a verified full js engine, a verified js jit, or a 2024-2026 effort to verify a js interpreter/builtins in a proof assistant (only regex, range analysis, model jits).

## bottom line (inference)
- target size: ~60-170k LOC engine (boa/nova class), or v8-embed glue ~10k (lightpanda).
- best verified-with-verus precedents: 6-7k LOC code, 3-13:1 proof, 2.5-4 person-years.
- best agent results: ~8k proof lines in 96 h with a human-written template; 90%/80% on small/medium proof tasks; failures on repo-scale from-scratch.
- existing js assets to reuse: executable spec (esmeta, 10,101 steps), regex (warblre+linden), parser-free coq semantics (jscert es5 only). no verified es2025 semantics.
