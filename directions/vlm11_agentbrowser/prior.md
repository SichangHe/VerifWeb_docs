# Prior-work map: formally verifying parts of a browser (for lightweight agent browsers)
(authored by agent; nothing published or contacted)

Labels: [F] quoted from a fetched record, [I] inference, [O] opinion.
Source: OpenAlex API (citation counts are OpenAlex's, not Scholar's; they differ), USENIX page for Quark. Raw: `raw/`, script `oa.py`.
Not done: Scholar via pb-browser-page-extract (OpenAlex sufficed; no CAPTCHA risk taken). Only abstracts read, no full texts. Many 2026 items are arXiv preprints, unreviewed.

## Takeaway
- [I] Verified browser kernels (Quark, 2012) and formal web-security models (2010-2023) are old and cover isolation/policy logic; none found covers an agent-browser threat model.
- [I] No verified JS engine exists in any record found; JS has verified/mechanized semantics (JSCert) and a verified JIT framework (Icarus, in vlm10), but not an engine. Wasm has the strongest verified stack.
- [I] Agent-assisted proofs are now real at the 6k-line scale (one experience report); nothing found at engine scale.
- [F] Not found: any academic paper on a browser designed for AI agents. Closest are agent-security papers on retrofitted browsers.

## 1. Verified browser kernels, isolation, formal models
- Quark, Jang, Tatlock, Lerner, USENIX Security 2012 (OpenAlex cited 41), https://www.usenix.org/conference/usenixsecurity12/technical-sessions/presentation/jang
  - [F] "QUARK, a browser whose kernel has been implemented and verified in Coq. We give a specification of our kernel, show that the implementation satisfies the specification, and finally show that the specification implies several security properties, including tab non-interference, cookie integrity and confidentiality, and address bar integrity."
  - [I] the direct ancestor: verify a small kernel, leave the renderer/JS untrusted. Tab non-interference is the property an agent browser needs per session.
- Featherweight Firefox, WebApps 2010 (authors from memory) (cited 55), OpenAlex title "Featherweight Firefox: formalizing the core of a web browser"; [F] title only, no abstract in record.
- Towards a Formal Foundation of Web Security, Akhawe, Barth, Lam, Mitchell, Song, IEEE CSF 2010 (cited 229), https://doi.org/10.1109/csf.2010.27; [F] title/count only (abstract absent). [I] Alloy model of web mechanisms; follow-up: "Towards Further Formal Foundation of Web Security: Expression of Temporal Logic in Alloy" (IEEE Access 2019, cited 5).
- IBOS: A Correct-By-Construction Modular Browser, 2012 (cited 13), https://doi.org/10.1007/978-3-642-35861-6_14; [F] title only. Verification of IBOS in Reachability Logic, 2020 (cited 6), https://doi.org/10.1007/978-3-030-63595-4_10; [F] title only.
- WebSpec, IEEE S&P 2023 (cited 5), https://doi.org/10.1109/sp46215.2023.10179465
  - [F] "The complexity of browsers has steadily increased over the years, driven by the continuous introduction and update of Web platform components, such as novel Web APIs and security mechanisms. Their specifications are manually reviewed by experts to identify potential security issues. However, this process has proved to be error-prone..."
  - [I] machine-checked analysis of the spec level, not of an implementation.
- Formal methods for web security, Bugliesi, Calzavara, Focardi, JLAMP 2016 (cited 46), https://doi.org/10.1016/j.jlamp.2016.08.006; survey, [F] title only.
- Site isolation testing: "Are your Sites Truly Isolated? Automatically Detecting Logic Bugs in Site Isolation Implementations", NDSS 2026, https://doi.org/10.14722/ndss.2026.240902
  - [F] "The security of Site Isolation relies on process isolation provided by the operating system. It also relies on the security of the privileged browser process."
- Agentic-browser isolation: see vlm10 `prior_work.md` section 5 ("Site Isolation is Dead", IEEE S&P 2026). WebMCP-Phalanx, arXiv 2608.24017 (2026, cited 1): [F] "integrating agent execution into a browser security model centered on the Same-Origin Policy (SOP) leaves insufficient provenance and lifecycle guarantees for agent-accessible tools". [I] attack/defense, not proof.
- [F] Not found: Coq/Alloy model of SOP/CSP covering headless-agent sessions; any Quark successor verified since 2012.

## 2. Verified request filtering and policy enforcement
- CSP formal semantics: Calzavara, Rabitti, Bugliesi, "Semantics-Based Analysis of Content Security Policy Deployment", ACM TWEB 2018 (cited 42), https://doi.org/10.1145/3149408
  - [F] "we introduce a formal semantics for the latest stable version of the standard, CSP Level 2. We then perform a systematic, large-scale analysis of the effectiveness of the current CSP deployment"
  - Calzavara et al. "Semantically Sound Analysis of Content Security Policies", 2019 (cited 2); [F] title only.
- Adblock/URL-filter engine verification: [F] OpenAlex query "verified adblock URL filter engine" returned only measurement papers (CV-Inspector, Missed by Filter Lists). [F] not found: any verified filter-list matcher.
- Regex (used in filter lists, CSP, URL patterns): "Formal Verification for JavaScript Regular Expressions: A Proven Mechanized Semantics and Its Applications", 2026 (cited 1), https://doi.org/10.1145/3776710
  - [F] "We present the first mechanized, succinct, practical, complete, and proven-faithful semantics for a modern regular expression language with backtracking semantics." Earlier: "A Coq Mechanization of JavaScript Regular Expression Semantics", 2024 (cited 9), https://doi.org/10.1145/3674666.
- [F] not found: formalized/verified WHATWG URL parser; verified HTML parser (only generic verified parsers: TRX 2011, verified LL(1)/packrat/Earley parsers).
- Agent policy engines (2026, mostly arXiv, unreviewed, none browser-network-level):
  - Sapien, arXiv 2610.00797 (cited 0): [F] "a policy engine for enforcing stateful contextual policies. A Sapien policy specifies permitted tool-call seq..."
  - Before the Tool Call, arXiv 2603.20953 (cited 32): [F] "AI agents today have passwords but no permission slips... no standard mechanism to enforce authorization before the action executes."
  - ceLLMate (HTTP-layer enforcement): see vlm10 `other_directions.md`.
- eBPF/packet filters:
  - [F] "End-to-End Mechanized Proof of a JIT-Accelerated eBPF Virtual Machine for IoT", CAV 2024 (cited 19), https://doi.org/10.1007/978-3-031-65627-9_16: "RIOT's rBPF uses a slower but memory-isolating interpreter (a virtual machine) which implements a defensive semantics of BPF".
  - [F] "Heimdall: Formally Verified Automated Migration of Legacy eBPF Programs to Rust", arXiv 2605.25411 (2026): "The in-kernel eBPF verifier checks low-level memory safety and termination on eBPF programs, but it does not enforce many higher-level source-level properties".
  - Firewall verification: "Firewall verification and redundancy checking are equivalent" INFOCOM 2011 (cited 23); [F] title only. Jitterbug (OSDI 2020) not returned by search: [F] not found in OpenAlex.
  - [I] these verify the enforcement mechanism for fixed rule languages; a browser request-policy checker would be a small analogue. No browser-specific work found.

## 3. Verified JS semantics/engines, Wasm, agent-assisted verification
JS:
- JSCert, Bodin et al., POPL 2014 (cited 120 / 17 two records), https://doi.org/10.1145/2535838.2535876
  - [F] "The time is ripe for a formal, mechanised specification of JavaScript, to clarify ambiguities in the ECMA standards, to serve as a trusted reference..."
- JSExplain, Charguéraud, Schmitt, Wood, Companion WWW 2018 (cited 20), https://doi.org/10.1145/3184558.3185969
  - [F] "a reference interpreter for JavaScript that closely follows the specification and that produces execution traces."
- JaVerT (POPL 2018, cited 32), JaVerT 2.0 (POPL 2019, cited 34): [F] titles "JaVerT: JavaScript verification toolchain", "JaVerT 2.0: compositional symbolic execution for JavaScript". [I] verifies JS programs, not engines.
- KJS (Park et al., PLDI 2015): [F] not returned by OpenAlex; not verified here.
- ESMeta: [F] not returned as its own record. Related, "JavaScript Language Design and Implementation in Tandem", CACM/OOPSLA 2024 (cited 8), https://doi.org/10.1145/3624723; [F] snippet "Proposing a new approach to programming language development." MiniPoly 2026 [F]: "Because developers rely on them to run modern features everywhere, strict conformity to the official language specification (ECMA-262) is crucial." [I] ESMeta-style extraction makes a spec-derived executable reference, an oracle for testing, not a proof of an engine.
- Icarus (SOSP 2024), Mohabi (OSDI 2026), Utrecht thesis "Verifying JavaScript JIT Compilers" 2026: see vlm10 `prior_work.md` section 3.
- Translation validation for V8 JIT, ISSTA 2024 (cited 50): vlm10.
- [I] size of a verified JS engine: no record found reports one. Reasoning from comparables: CompCert-class compilers are person-years each; JSCert models the spec only. Treat "full verified engine" as unprecedented; a verified subset (parser, interpreter core for a spec-conformant subset, no JIT) is the plausible unit. [O] not a number from a source.
Wasm:
- Two Mechanisations of WebAssembly 1.0, FM 2021 (cited 35), https://doi.org/10.1007/978-3-030-90870-6_4 (WasmCert-Coq and Isabelle). [F] title only.
- WasmRef-Isabelle, 2023 (cited 14), https://doi.org/10.1145/3591224: [F] "a monadic interpreter for WebAssembly written in Isabelle/HOL and proven correct with respect to the WasmCert-Isabelle mechanisation... deployed as a fuzzing oracle in the continuous integration infrastructure of Wasmtime".
- Progressful Interpreters for Efficient WebAssembly Mechanisation, 2025 (cited 5), https://doi.org/10.1145/3704858.
- Wasm SpecTec / "Bringing the WebAssembly Standard up to Speed with SpecTec", PLDI 2024 (cited 37), https://doi.org/10.1145/3656440: [F] "Its specification is unusually rigorous – including a full formal semantics for the language".
- Iris-MSWasm 2024 (cited 6); Iris-WasmFX 2026 (cited 0).
- VeriWasm (NDSS 2021, cited 14 in OpenAlex): [F] "To implement isolation, the compiler inserts safety checks when it compiles Wasm to native machine code. While this approach is cheap, it also requires trust in the compiler's correctness". Crocus, ASPLOS 2024 (cited 9), https://doi.org/10.1145/3617232.3624862, and Arrival (2025, cited 0, https://doi.org/10.1145/3764383): [F] "an instruction-selection verifier for the Cranelift production Wasm-to-native compiler." Isolation without taxation, POPL 2022 (cited 18).
- vWasm (Bosamiya et al.), "Provably-safe multilingual sandboxing": see vlm10; not returned by OpenAlex.
- [F] not found: a Wasm engine written in Verus or Lean (query "Wasm engine verified in Lean or Verus" returned nothing relevant).
LLM/agent-assisted verification at scale (2025-2026):
- Machine-Generated, Machine-Checked Proofs for a Verified Compiler, ICFP 2026 (cited 11), https://doi.org/10.1145/3828700
  - [F] "using an agentic coding assistant (Claude Code, powered by Claude Opus 4.6) to mechanize a substantial Rocq correctness proof from scratch, with human guidance but without any human-authored proof code... approximately 6,000 lines of Rocq proof (larger than the 4,200-line CPS proof) and was developed in 94.5 hours."
  - [I] strongest scale datapoint; template proof existed, so it is adaptation, not discovery.
- Claims vs. Evidence, Zenodo 2026, https://doi.org/10.5281/zenodo.22985925 (RunuX, AI-assisted Rust kernel with Lean specs)
  - [F] "Static measurement at a fixed commit found 316 crates, of which 141 are placeholders of at most 25 lines... 249 open sorry obligations with 138 axioms across 36 Lean modules."
  - [I] warns that agent-produced "verified systems" overclaim; non-peer-reviewed.
- Agentic Verification of Software Systems, 2026 (cited 17), https://doi.org/10.1145/3808164: [F] "Reasoning about computer programs (software) can be accomplished via general mathematical reasoning; however, it tends to be more structured and richer in contexts."
- VeriSoftBench, arXiv 2602.18307 (cited 9): [F] "proofs in software verification are developed inside definition-rich codebases with substantial project-specific libraries" (repo-scale Lean benchmark, 500 obligations).
- ProofWright (CUDA, arXiv 2511.12294, cited 15); VeriStruct (Verus data structures, 2026, cited 10); Verus-SpecGym (arXiv 2605.26457, cited 6): [F] "there is no guarantee that the formal spec itself matches the user's intent."; RAIN (Rocq agent, arXiv 2610.30759); Automating Formal Verification with Agent-Guided Tree Search (arXiv 2605.27485, thesis).
- "Don't Trust the Code, Check Its Effects: Runtime Refinement for Regenerated Systems Code", 2026, https://doi.org/10.1145/3843967.3844678: [F] "Recent work uses large language models to generate systems code from specifications, treating the specification as the durable artifact and the implementation as disposable."
- "Escaping the Quicksand: A Call to Arms", arXiv 2608.19674 (2026): [F] "AI-enabled engi[neering]..." (truncated); argues for verified foundations.
- [F] not found: any record of an agent-produced verified system the size of a JS engine, browser, or OS kernel with complete proofs. SECOMP (CCS 2024, cited 4): verified compartmentalization compiler, human-built.

## 4. Multi-tenant in-process isolation
- Reuse `/hdd1/sichangheagent/vl_meeting_work/out/vlm10_share/prior_work.md` (V8 isolates, Cloudflare, SFI, Mohabi OSDI 2026, ERIM, Hodor, Swivel, Dynamic Process Isolation) and `REPORT.md`. Not redone.
- Add: SECOMP above [F] "mutually distrustful compartments... machine-checked proofs guaranteeing that the scope of undefined behavior is restricted to the compartments that encounter it" (CCS 2024) - machine-checked compartment isolation for C, not JS.

## 5. Browsers designed for AI agents (academia)
- [F] OpenAlex queries "browser designed for AI agents headless agent-oriented", "agentic browser architecture ... lightweight", "browser for LLM agents token-efficient DOM", "agent-native browser LLM-oriented rendering engine" returned no paper that designs a browser (engine/kernel) for agents.
- Nearest, all agents on top of existing browsers:
  - In-Browser LLM-Guided Fuzzing for Real-Time Prompt Injection Testing in Agentic AI Browsers, arXiv 2510.13543 (cited 4): [F] "These attacks can bypass traditional web security boundaries, as the AI agent operates with the user privileges across..."
  - Agentic Compilation, arXiv 2604.09718 (2026): [F] "Autonomous web agents that operate through continuous inference loops... exhibit a fundamental scalability constraint when applied to repetitive, high-volume tasks."
  - WebMCP-Phalanx (section 1); Site Isolation is Dead (vlm10); WASP, BrowseSafe, ceLLMate, Prismata (vlm10 `other_directions.md`).
- [I] "agent-oriented browser" appears as industry products (not searched; grey literature outside scope). The academic gap is real for what OpenAlex indexes; Scholar/DBLP not checked, so absence is not proven.

## Novelty read [O]
- Likely novel: a verified small kernel for an agent browser that enforces per-session non-interference plus per-session request policy, with proofs agent-assisted (Quark's design + 2026 tooling + new threat model). No competing record found.
- Crowded/old: generic browser-kernel verification (Quark), CSP/SOP models, Wasm mechanization.
- Risky: verified JS engine (no precedent, scale unknown); the verified-subset route is untested.
## Gaps
- Not fetched: Scholar counts; Featherweight Firefox, Akhawe CSF, IBOS, KJS, ESMeta, vWasm, Jitterbug abstracts; full texts; DBLP.
