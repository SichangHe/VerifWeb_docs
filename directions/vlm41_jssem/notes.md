# vlm41_jssem: how far are we from a machine-checked JS semantics usable for verifying real web code?
(authored by agents unless marked 🧑)

Labels: [F] fact with quote and pointer; [I] inference; [O] opinion; [?] I do not know.
Scholar was used for 11 queries (as_ylo=2018, files s1..s11.txt in this dir). Query 12 hit a CAPTCHA (`challenge_action_required`); I stopped and did not bypass it. So the prototype-pollution and Gillian/JSExplain/Featherweight searches are thinner than planned (those PDFs came from direct author/venue URLs). GitHub dates were fetched 2026-11-10 with `gh api`.

## Bottom line

[I] No machine-checked semantics of full modern JS plus DOM exists. Three separate gaps:
- Full-language semantics are mechanized from the spec but are executable specs, not proof-assistant developments (ESMeta, ECMA-SL). The proof-assistant ones stop at ES5 (JSCert, Coq) or cover only the regex chapter (Warblre/Linden, Rocq).
- Browser-API semantics (DOM, events) exist only as: an Isabelle/HOL core-DOM node tree (2018), and trusted JS reference implementations of DOM Core L1 / UI Events / Promises inside JaVerT.Click (ES5 strict, symbolic execution, not a proof assistant).
- Nothing found proves a JS rewriter or a web-archive rewriter correct.

[I] Wasm shows the route that worked: the spec itself became machine-readable (SpecTec) and proof-assistant mechanizations are generated or maintained against it. For JS the closest analog is ESMeta (extracts an executable model from ECMA-262 HTML), but nobody generates Rocq/Isabelle from it.

## Per project

### JSCert / JSRef (Coq)
- [F] What: "JSCert, a formalisation of the current ECMA standard in the Coq proof assistant, and JSRef, a reference interpreter for JavaScript extracted from Coq to OCaml. We give a Coq proof that JSRef is correct with respect to JSCert" (Bodin et al., POPL 2014, https://www.doc.ic.ac.uk/~pg/publications/Bodin2014Trusted.pdf).
- [F] Version/coverage: "JSCert specifies the core language of ES5, but does not specify the parser nor many of the native libraries" (same paper).
- [F] test262: "There are 2782 tests associated with the core language (chapters 8–14): we pass 1796 tests; the others fail due to for-in, calls to libraries we have not specified, or the parser" (same paper, 2014).
- [F] Browser API: none in the paper.
- [F] Activity: last non-trivial commit 2019-04-09 (README); last push 2024-02-05 "TLC is now hosted on Github" (Martin Bodin), per `gh api repos/jscert/jscert/commits`. README pins Coq 8.4.6. [I] dormant; will not build on current Rocq without work.
- [F] Verified with it: the interpreter's correctness vs the spec, and 2014 paper's language properties; [?] I found no verified web program built on it.

### KJS (K framework)
- [F] "KJS, the most complete and throughly tested formal semantics of JavaScript to date. Being executable, KJS has been tested against the ECMAScript 5.1 conformance test suite, and passes all 2,782 core language tests ... We verified non-trivial programs and found a known security vulnerability." (Park, Ştefănescu, Roşu, PLDI 2015, http://fsl.cs.illinois.edu/pubs/park-stefanescu-rosu-2015-pldi.pdf). ES5.1 only; core tests only (the 8,080 library tests are listed separately in the paper).
- [F] Proof assistant: none; K is a rewriting framework with a reachability-logic prover. [I] the "verification" trust base is the K tool, not a kernel checker.
- [F] Browser API: none.
- [F] Activity: repo kframework/javascript-semantics last push 2016-10-13, last commit by Daejun Park 2015-02-19 (gh api). [I] abandoned.
- [F] Critique from JaVerT 2.0 authors: "KJS specifications are complex and error-prone, explicitly exposing all language internals. Furthermore, KJS is not compositional" (POPL 2019, https://www.doc.ic.ac.uk/~pg/publications/FragosoSantos2019JaVerT.pdf).

### JaVerT / JaVerT 2.0 / Gillian-JS
- [F] What: separation-logic-based verification and symbolic execution for JS; compiles JS to JSIL/GIL. "JS-2-JSIL has full support for the entire core of ES5 Strict, as well as most of the associated built-in libraries. We do not implement the Date, RegExp, and JSON libraries" (JaVerT 2.0, POPL 2019).
- [F] test262: "Out of the 10469 tests for ES5 Strict, we identify 8797 tests appropriate for our [evaluation]" and passes them (POPL 2019); Gillian "replayed and passed the 8797 concrete tests of the Test262" (Gillian Part I, PLDI 2020, https://vtss.doc.ic.ac.uk/publications/FragosoSantos2020Gillian.pdf).
- [F] Proof assistant: none (OCaml tool + Z3). [I] soundness is on paper; the trusted base is the OCaml tool and the compiler.
- [F] What verified: data-structure libraries; "whole-program symbolic testing to the real-world Buckets.js ... library, which has over 65K downloads on npm", reproducing known bugs (POPL 2019). Bounded symbolic testing, not full proofs.
- [F] Activity: JaVerT2.0 repo: "Deprected - Please use Gillian-JS instead" (last commit 2020-04-22, Petar Maksimović). Gillian main repo last commit 2026-10-15 (Nat Karmios, Sacha-Élie Ayoun); but Gillian-JS dir is ES5 Strict and the recent work is Gillian-C/Rust/debugger (gh api). [I] JS side stagnant, platform alive.

### JaVerT.Click (DOM + events; Gillian-family, Imperial)
- [F] "JaVerT.Click is a symbolic execution tool for JavaScript that, for the first time, supports reasoning about JavaScript programs that manipulate any/all of the DOM Core Level 1, DOM UI Events, JavaScript Promises, and the JavaScript async/await APIs." (https://github.com/javert-click/javert-click README, 2020). Built on JaVerT 2.0, so ES5 strict plus trusted JS reference implementations of these APIs.
- [F] DOM test pass: "tested ... against their test suites making sure that they pass all applicable tests. The number of applicable tests is 527 for the DOM Core Level 1, 56 for DOM Events, 344 for JS Promises ..." (Sampaio PhD thesis, Imperial 2022, https://www.doc.ic.ac.uk/~pg/publications/Sampaio2022Trusted.pdf).
- [F] What verified: symbolic tests of cash (jQuery-like DOM library), p-map, webworker-promise: "establish the bounded correctness of several functional properties ... uncover 6 previously unknown bugs" (thesis 2022). Bounded, not proof-assistant.
- [F] Activity: last commit 2020-06-08 (Gabriela Sampaio). [I] dormant. [I] this is the closest existing thing to "DOM + JS semantics used on real web library code", and it is not machine-checked.

### ESMeta / JISET / JSTAR / JEST (KAIST, Ryu / Park)
- [F] What: extracts "a mechanized specification" from ECMA-262 text: a parser from the EBNF syntax plus IR functions compiled from the English algorithms. "ESMeta is an ECMAScript Specification Metalanguage. It extracts a mechanized specification from a given version of ECMA-262 and automatically generates language-based tools: a JavaScript interpreter, a double debugger, a conformance test synthesizer, and a specification type analyzer." (README, https://github.com/es-meta/esmeta).
- [F] Version/test262: JISET (ASE 2020): "the extracted core semantics of the latest ECMAScript (ES10, 2019) passed all 18,064 applicable tests" after manual completion; "found nine specification errors in ES10" (https://plrg.korea.ac.kr/assets/data/publication/ase20-park-jiset.pdf). Current ESMeta targets the ecma262 submodule or a tag (`-extract:target=es2026`); CI job `test262EvalTest` exists in post-submit.yml. [?] I did not find a published current pass-rate number; README only says `esmeta test262-test` "check[s] that Test262 and ECMA-262 agree".
- [F] Bugs: JEST (ICSE 2021): "it detected 44 engine bugs in four different engines and 27 specification bugs in ES11"; JSTAR: "93 type-related specification bugs, which were confirmed by TC39" (CACM 2024, https://plrg.korea.ac.kr/assets/data/publication/cacm24-ryu-esmeta.pdf).
- [F] Adoption: "ESMeta was then integrated into ECMA-262's CI system on Nov. 3, 2022 and Test262's CI system on Nov. 25, 2022" (CACM 2024).
- [F] Proof assistant: none (Scala). The mechanized spec is executable, not a theorem-prover artifact. [I] this is "mechanized" in a weaker sense than JSCert.
- [F] Browser API: not in README; host-defined parts are modelled only for test262 harness needs [I, not checked].
- [F] Activity: very active. Last commit 2026-11-09 (Jihyeok Park); release v0.8.2 on 2026-11-09. Maintained by KAIST PLRG.
- [F] Verified with it: no program proofs. Used for testing engines and type-checking the spec. (Local note: out/poke_esmeta, vlm27_mapback.)

### JSExplain, ECMA-SL / ECMARef5 / ECMARef6
- [F] JSExplain (Inria, Schmitt, Charguéraud et al.): "An (unofficial) ECMAScript Reference Interpreter and Double-debugger." Repo says "This repository is not maintained anymore. It moved here : https://gitlab.inria.fr/star-explain". Last commit on GitHub 2019-07-04. [?] no test262 number found in what I read; the 2022 follow-up "A Faithful Description of ECMAScript Algorithms" (Khayam, Noizet, Schmitt, SAC/PPDP 2022, https://dl.acm.org/doi/10.1145/3551357.3551381) relates it to JSCert, not read (blocked PDF).
- [F] ECMA-SL (IST Lisbon, Fragoso Santos group): "ECMARef5, a reference interpreter for ECMAScript that follows the ECMAScript standard version 5.1 line-by-line and is thoroughly tested against Test262" (Loureiro MSc thesis 2021, https://scholar.tecnico.ulisboa.pt/api/records/ZDWabG9op99_-rtDCieeyHfkmW4KXPqmuYOI/file/8f46f22798b3614afa518168e01c170bbec88270af726b0a171af8d43a3a73dd.pdf). "Out of a total of 12,068 applicable tests, we pass 99.6%".
- [F] ES6: "ECMARef5 passed 99,6% and ECMARef6 passed 92%" of 12,068 and 20,655 tests (Pereira MSc thesis 2024). "the last ES version supported by the ECMA-SL project is the 6th (ES6), released in 2015" (Nascimento MSc thesis 2023). Same thesis: the standard's "rapid growth in size and complexity ... makes it difficult to keep the implementation up to date."
- [F] Proof assistant: none (OCaml). Has a symbolic-execution mode (`ecma-sl symbolic`, Z3).
- [F] Activity: formalsec/ECMA-SL-pub last push 2025-12-15; last commit 2025-07-23 (Filipe Marques). Contains JS-Interpreters/ecmaref5, ecmaref6, es6-sym. [I] alive but ES6 is the ceiling; no DOM.

### Lean / Isabelle / Iris efforts on JS 2018-2026
- [?] Scholar query 9 (JS semantics Isabelle OR Lean OR Iris) returned only JISET and the regex papers, plus unrelated Wasm items. I found no Lean, Iris, or Isabelle mechanization of the JS core language. This is weak negative evidence only (one query, then CAPTCHA).
- [F] JSkel: "Towards a Formalization of JavaScript's Semantics" (Inria HAL hal-03509431, 2021 per Scholar listing, https://inria.hal.science/hal-03509431/). Title seen in Scholar s1; PDF blocked, not read. [?] contents unknown.
- [F] Isabelle for DOM exists (below). Iris for Wasm exists (Iris-MSWasm, OOPSLA 2024, listed in s11; not read).

### Warblre / Linden (regex; Rocq)
- [F] Warblre: "an executable, proven-safe, faithful, and future-proof Coq mechanization of JavaScript regular expression (regex) matching, as specified by the latest published edition of ECMA-262 section 22.2" (De Santo, Barrière, Pit-Claudel, ICFP 2024, https://arxiv.org/abs/2403.11919). Version: ES2023 (repo: "A Rocq Mechanization of ECMAScript 2023 Regexes").
- [F] test262: "Test262 contains 498 tests of core regex-matching functionality ... We pass 495 out of 498; the remaining 3 tests time out." Other regex-related: "we pass 436 out of 445 tests" (ICFP 2024).
- [F] Verified: always terminates, no assertion failures; an optimization from a production engine; found "subtle corner cases that led to mistakes in previous publications".
- [F] Linden: "first mechanized, succinct, practical, complete, and proven-faithful semantics for a modern regular expression language with backtracking semantics ... proving it equivalent to a preexisting line-by-line embedding of the official ECMAScript specification" plus "a new notion of contextual equivalence for modern regular expressions, which we use to prove or disprove rewrites drawn from previous work" and "the first formal proof of the PikeVM algorithm" (Barrière, Deng, Pit-Claudel, POPL 2026, arXiv 2507.13091v3, 2026). Rewrites proved/disproved: anchors as lookarounds, quantifier merging, associativity/distributivity.
- [F] Third paper: "JavaScript regex matching with expanded lower-bounded quantifiers is PSPACE-complete ... formalized in Rocq" (Deng, Barrière, Pit-Claudel, arXiv 2603.26139, 2026).
- [F] Activity: very active. Warblre last commit 2026-11-10 (Clément Pit-Claudel); Linden 2026-11-10 (Aurèle Barrière); both under github.com/LindenRegex (EPFL).
- [I] This is the only proof-assistant JS component that is current, and the only one with proven rewrites. It is a regex rewriter-correctness precedent (rewrites of regexes inside JS), not of JS code.

### DOM formalizations
- [F] Gardner, Smith, Wheelhouse, "Local Hoare Reasoning about DOM" (PODS 2008): "We provide a compositional specification of a significant fragment of DOM." Paper logic, no proof assistant.
- [F] Featherweight Firefox (Bohannon, Pierce, WebApps 2010): "a formal specification of the core functionality of a web browser in the form of a small-step operational semantics ... windows, DOM trees, cookies, HTTP requests and responses, user input, and a minimal scripting language with first-class functions, dynamic evaluation, and AJAX requests"; "our model is presented in the form of an OCaml program (about 2,500 LOC)". Not in a proof assistant. The JS is a toy language, not ES.
- [F] Brucker and Herzberg, "A Formal Semantics of the Core DOM in Isabelle/HOL" (WWW Companion 2018, https://www.brucker.ch/bibliography/download/2018/brucker.ea-core-dom-2018.pdf): "a formalization of the core DOM, with focus on the node-tree and the operations defined on node-trees ... verify the functional correctness of the most important functions defined in the DOM standard", executable, based on "W3C DOM 4". AFP entry dated 2018-12-26 (https://www.isa-afp.org/entries/Core_DOM.html). Follow-ups on shadow DOM / web components are in Scholar s4 (Springer 2020, Herzberg thesis); not read. [?] activity since 2020 unknown.
- [F] Scholar s4 also listed "Webspec: Towards machine-checked analysis of browser security mechanisms" (IEEE, 2023) and "WebAPISpec" (TU Wien); not read, [?] what they cover.
- [I] No DOM model is connected to a mechanized JS core. The Isabelle DOM has no JS; JaVerT.Click has JS but its DOM is a JS reference implementation, trusted via test suites.
- [F, from collection] TAJS hand-models "the HTML DOM and browser API" for static analysis (Jensen, Møller): already local.

### WasmCert-Coq/Rocq, WasmCert-Isabelle, Wasm SpecTec (comparison)
- [F] "its official specification contains a complete formal semantics, ... and proved sound with machine-verified proofs" (Dagstuhl Seminar 25241 report, 2025, https://drops.dagstuhl.de/storage/04dagstuhl-reports/volume15/issue06/25241/DagRep.15.6.51/DagRep.15.6.51.pdf).
- [F] WasmCert-Rocq: "formalises Wasm 2.0 + tail call ... The extracted runtime now passes the Wasm 2.0 core test suite fully" (same report, Rao abstract). Rao thesis (Imperial 2025): started from Watt's Isabelle/HOL mechanization of pre-1.0 Wasm; "I have discovered several mistakes in the Wasm 2.0 specification and reported them to the specification editor, some of which have been fixed".
- [F] Activity: WasmCert-Coq last commit 2026-10-12 (Rao Xiaojia); WasmCert-Isabelle 2026-08-27 (Antanas Kalkauskas); WebAssembly/spec/spectec last commit 2026-11-04 (Minsung Lee).
- [F] SpecTec: "Defines and implements a domain specific language (DSL) for the formal specification of Wasm" with backends: "the Latex for the formal specification for the spec document, the prose specification pseudo-algorithms ..., the Coq and Isabelle definitions for mechanisation, a reference interpreter, a test suite" (https://github.com/WebAssembly/spec/blob/main/spectec/README.md). Paper: "Bringing the WebAssembly Standard up to Speed with SpecTec", PLDI 2024 (not obtained; ACM and Edinburgh copies returned HTML).
- [F] How the Wasm route differs: Wasm was designed with a formal core in the spec from the start; Watt's mechanization found spec bugs (CACM 2024: "the WebAssembly 1.0 specification had bugs detected by mechanized proofs of Conrad Watt"). Dagstuhl: SpecTec backends "lag behind"; Rao's thesis expects WasmCert-Coq to move to SpecTec only "in a longer future".
- [I] Why JS is harder: ES2026 text is prose pseudocode with host hooks; every year changes thousands of steps (JISET: "average number of updated steps ... is 9645.5" between ES7 and ES10 per JSTAR citing JISET). ESMeta already treats the prose as source of truth and is integrated in ECMA-262 CI; the missing piece is a verified backend (Rocq/Isabelle) and a host/DOM layer.

### Prototype pollution
- [F] Scholar s6 returned only detection tools: e.g. "Bullseye: Detecting Prototype Pollution in NPM Packages with Proof of Concept Exploits" — "a fully automated dynamic analysis framework" (Houis et al., NDSS 2026, http://users.encs.concordia.ca/~mmannan/publications/Bullseye-NDSS2026.pdf). Others listed: ODGen-type exploit generation (ACM 2025), fuzzing-based detection (ACM, listed s6), runtime mitigation (UFSC). No hit used a mechanized JS semantics. [?] Not found: a proof that a library or fix is pollution-free; one query only, second blocked by CAPTCHA.
- [I] KJS "found a known security vulnerability" (2015) and JaVerT 2.0 reproduces bugs on Buckets.js, so semantics-based tools could target this; I saw nothing published doing so for pollution.

### Verified JS compilers / translation validation
- [F] TurboTV: "an SMT-based translation validation ... We formally define the semantics of IR of TurboFan (JIT compiler of V8) as SMT encoding" and "TurboTV only supports loop-free functions" (Kwon, Kwon, Kang, Lee, Heo, ICSE 2024; already in collection). It validates TurboFan IR rewrites, not JS-source semantics; no proof assistant.
- [F] Optimuzz: "combine ... directed grey-box fuzzing and translation validation ... for two major compilers, LLVM and TurboFan" (Kwon, Jang, Lee, Heo, PLDI 2025, http://prosys.kaist.ac.kr/publications/pldi25.pdf). Found "55 new miscompilation bugs" in LLVM (not TurboFan).
- [?] Found no verified JS-to-X compiler in Coq/Isabelle/Lean in Scholar s8. Closest hits: CoreJIT speculation/deopt (POPL 2021, a JIT for a toy language, not JS) and CertiCoq-Wasm (Coq to Wasm, not JS). Both listed, not read.

### Provably correct web-archive rewriter
- [F] Not found. What exists is empirical: "on many modern pages, an archive's edits to crawled scripts result in a loss of fidelity ... we reduced the fraction of archived pages which violate fidelity from 15% to 9%" (Zhu, Sun, Madhyastha, NSDI 2026, https://www.usenix.org/conference/nsdi26/presentation/zhu-jingyuan; Jawa, OSDI 2022, both already in collection).
- [I] The Linden-style approach (equational/contextual equivalence of a rewrite, proved against a faithful semantics) does not exist for JS code. For the rewrites archives do (URL rewriting at runtime, wrapping `fetch`/`XMLHttpRequest`/`Date`/`Math.random`) the needed semantics must include host APIs, which no mechanized model has.

## Distance (opinion)
- [O] For builtin/regex/numeric string functions: close. Warblre/Linden prove properties of the actual ES2023 regex spec and are maintained; ESMeta gives an executable full-spec oracle.
- [O] For a language core in a proof assistant at ES2023+: far. JSCert is ES5 and dormant; ECMA-SL stops at ES6; ESMeta is not a proof development. Cost estimate: a Rocq backend over ESMeta IR plus semantics of host hooks, years of work [I, no source].
- [O] For verifying real web code (DOM, events, async): further. Only bounded symbolic testing (JaVerT.Click on ES5 strict, 2020) and a tree-only Isabelle DOM (2018) exist.

## Files
- Scholar outputs: s1..s11.txt; parsed with show.py; downloaded PDFs and text under dl/ (untrusted data, never executed).
- Papers added to /hdd1/sichanghe/paper_collection: see final report (22 PDFs, not committed).
- Not obtained (paywall/blocked): JaVerT POPL 2018, Gillian Part II CAV 2021, JaVerT.Click ECOOP 2020 paper, SpecTec PLDI 2024, Two Mechanisations of WebAssembly FM 2021, Khayam et al. SAC 2022, JSkel, JSExplain WWW 2018, Webspec 2023, WebAPISpec.
