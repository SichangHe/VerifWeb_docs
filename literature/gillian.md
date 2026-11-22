# Gillian: what it is and what it means for VerifWeb
(authored by agents unless marked 🧑)

Why this exists: advisor Harsha wrote on Slack (Nov 21) 🧑 "github.com/GillianPlatform/Gillian is worth checking out, if you haven't already." It follows the Nov 19 meeting (transcript `/ssd1/sichangheagent/email/1119madhyastha_govindan_ardi.vtt`), where we weighed building a JavaScript verifier ourselves against building on Verus.

Labels: [F] fact (quoted or checked by me), [I] inference, [O] opinion, [?] unknown.
Paper list with verbatim abstract sentences and links: `/hdd1/sichangheagent/vl_meeting_work/out/vlm60_gillian/papers.md` (18 papers; 16 newly added as PDFs to `/hdd1/sichanghe/paper_collection`).

## Takeaways

1. Gillian already is the "JavaScript verification framework" Harsha asked whether we should build, but only for ES5 Strict (JavaScript as of 2009, strict mode). It has no `let`, classes, modules, Promises or `async`, and no browser APIs except a separate, dormant research prototype.
2. Its most relevant result is a verification of real JavaScript security code. Gillian Part II (CAV 2021) verified the AWS Encryption SDK's message-header parser and found a prototype-poisoning bug that AWS fixed. This is exactly the kind of "security-relevant part of JavaScript" Calvin suggested, so it is prior work we must cite and beat.
3. Using Gillian-JS for modern web code would mean writing a new ES2015+ front end and runtime library. That is the hard part, and the part Ramesh worried about. [O] Gillian saves us the symbolic engine and solver plumbing, not the JavaScript semantics.
4. Gillian-Rust (PLDI 2025) competes with Verus for verifying unsafe Rust, but it is a self-described "prototype" with no commits since May 2025. [O] It does not change the Verus choice for STORY.md.

## What Gillian is

[F] A platform for compositional symbolic execution: one engine, parametric in the memory model, plus per-language front ends that compile to an intermediate language, GIL. README: "Gillian-C # Instantiation of Gillian for CompCert-C. Gillian-JS # Instantiation of Gillian for ES5 JavaScript. ... wisl # Instantiation of Gillian for a small While language for research and teaching." Rust lives in a separate repo, `GillianPlatform/gillian-rust`.

[F] It has three modes (Gardner, PPDP 2018 talk): "full verification, whole-program symbolic testing, and automatic compositional testing based on bi-abduction."
- verification: per-function separation-logic specs written by the user, so it is compositional. It proves functional correctness, and the ECOOP 2023/2024 papers add "exact" specs usable for both proofs and true-bug finding.
- symbolic testing: bounded and whole-program, used to find bugs.
- [I] soundness is argued on paper, not machine-checked. The JS semantics is trusted, and its evidence is Test262. Gillian Part I: "filter the latest version of the test suite for the tests applicable to ES5 Strict, identifying 9013 and passing 9005 tests."

## JavaScript coverage

- [F] language: JaVerT 2.0 (POPL 2019): "JS-2-JSIL has full support for the entire core of ES5 Strict, as well as most of the associated built-in libraries."
- [F] checked by me with the nightly binary: `let x = 1` is rejected with "Parsing error: Using Let or Const is not authorized in ES5 !". Plain ES5 strict code runs.
- [F] browser APIs: only JaVerT.Click (ECOOP 2020), which adds reference implementations of DOM Core Level 1, DOM Events, Promises, async/await, WebMessaging and WebWorkers. Its scale: "symbolic testing of the events module of Cash, a widely-used jQuery alternative ... discovering two subtle, previously unknown bugs." [F] It is not in the main repo. The earlier note `directions/vlm41_jssem/REPORT.md` already lists it as "dormant since 2020".

## What has been verified, and at what size

- [F] JaVerT (POPL 2018): small data structures ("key-value map, priority queue ... BSTs and lists"). The examples in `Gillian-JS/Examples/JaVerT` are files such as `BST.js` and `DLL.js`.
- [F] Buckets.js (an npm data-structure library) was tested symbolically, and bugs were found (JaVerT 2.0, Gillian Part I).
- [F] largest JS proof: the AWS Encryption SDK header deserializer. CAV 2021: "We verify the JavaScript and C implementations of the AWS Encryption SDK message header deserialisation module ... and find two bugs in the JavaScript and three bugs in the C implementation." [F] The annotated file `deserialize_factory.js` is 886 lines, including specs. One JS bug is prototype poisoning (repo README): "the function throwing an error if the key coincides with a property of `Object.prototype`", fixed via `Object.create(null)` in https://github.com/aws/aws-encryption-sdk-javascript/pull/216.
- [F] I reran it: the current nightly verifies all its specs in 24 s on one core ("All specs succeeded"). The bug-reproduction variant `bugs/pp/` now fails earlier, in preprocessing ("TYPE ERROR: ... not typable"). [I] That is bit rot in the example, not a re-found bug.
- [F] C side: Collections-C and AWS code. Rust side: "real-world Rust standard library code with only minor annotations" (Gillian-Rust, no size stated).

## How active it is

- [F] the repo has 104 stars and its last push was 2026-11-20. There were 66 commits since 2025-01-01, 30 of them in 2026, mostly by Nat Karmios and Sacha Ayoun, with Andreas Lööw contributing. Releases: "LAB-2026" (2026-11-19, a student lab) and nightly binaries for JS, C, C2 and WISL.
- [F] JS work restarted in 2026: commits "Revive the JS verification (#365)" (2026-06-28) and "JS: Add check for division by zero (#339)". Most recent work is in the core (predicates, debugger, LSP) and in C.
- [F] papers 2020-2026: Gillian I (PLDI 2020), JaVerT.Click (ECOOP 2020), Gillian II (CAV 2021), Exact SL (ECOOP 2023), two ECOOP 2024 papers, Gillian-Rust (PLDI 2025), "Next 700 Memory Models" (OOPSLA 2025), debugger (TACAS 2026), and Ayoun's PhD thesis (2025). Since Gillian II, no paper's evaluation targets JavaScript.
- [F] Soteria (PLDI 2026, Ayoun et al.) is a new engine by a Gillian author and is "not built on Gillian" (subagent's reading, from papers.md). [?] Whether the group's effort is moving there is unknown.

## What using it would take

- [F] cheap to try: a static Linux binary (`gillian-js-nightly-linux-x86_64`) runs with no OCaml install. It is in `/hdd1/sichangheagent/vl_meeting_work/out/vlm60_gillian/bin`.
- [I] for ES5 code (old libraries): write separation-logic specs in Gillian's predicate language (see the AWS example). That takes days per module, plus learning separation logic.
- [I] for modern code: either write an ES2015+ to JSIL front end with built-ins (the JaVerT compiler is ES5-only), or transpile to ES5 with Babel and verify the output. Transpiling is plausible for syntax but loses the Promise and async semantics and links proofs to generated code. [?] Nobody has published the transpile route.
- [I] browser APIs: revive JaVerT.Click or write new models, all trusted.

## What it changes for our directions

(a) JavaScript semantics as a foundation
- [I] it weakens "nothing exists" framing: an executable, Test262-tested ES5 Strict semantics with a symbolic verifier exists and is maintained. A new foundation must be justified by modern JavaScript (ES2015+) and by machine-checked trust, the gap `vlm41_jssem` identified.
- [I] it also gives a cheaper option than Harsha's "build our own": build an ES2015+ front end for Gillian, possibly generated from ECMA-262 via ESMeta. [O] This is still PL-heavy, which matches Ramesh's worry (L163-164: "the ability to develop a verifier that requires understanding language semantics ... add to that ... the complexity of the JavaScript semantics"). [?] Talk to the Gillian group before starting; they may plan this.

(b) Calvin's security-relevant part of JavaScript
- [F] Gillian II already did "verify a security-relevant JS module and find prototype pollution" on AWS code. [I] So a paper of the form "we verify JS module X is free of prototype pollution" must beat this on scale (many npm packages, not one), on modern JS, or on automation. [I] Bundler/minifier semantics preservation (`directions/js_bundler_security_1119.md`) is not covered by Gillian, which verifies one program and not a transformation, so that angle stays open.

(c) current directions
- [I] STORY.md (proving real Rust sync protocols converge and finish): Gillian-Rust targets unsafe-Rust memory safety and functional specs, not distributed liveness. Its repo is a prototype, so [O] Verus remains the better base. Cite Gillian-Rust as related work for Rust verification.
- [I] engine and archive-rewriter ideas in `vlm41_jssem`: no change. Gillian verifies JS programs, not engines or rewriters.

## Prior work we must cite before claiming novelty

- for any JS verification claim: JaVerT (POPL 2018), JaVerT 2.0 (POPL 2019), Gillian Part I (PLDI 2020), Gillian Part II (CAV 2021)
- for anything with DOM, events or Promises: JaVerT.Click (ECOOP 2020) and Sampaio's thesis (2022)
- for prototype pollution or security of JS modules: Gillian Part II's AWS bugs
- for compositional bug finding plus proof: Exact SL (ECOOP 2023), Lööw et al. (ECOOP 2024)
- for Rust verification: Gillian-Rust (PLDI 2025), alongside Verus and others

## Not done

- [F] I did not read the papers fully. Claims come from abstracts, the repo, and two runs. I did not test a Babel-transpiled modern library.
- [F] DBLP showed a bot check and Semantic Scholar rate-limited the subagent, so the paper list may miss work by people outside the group who use Gillian.
