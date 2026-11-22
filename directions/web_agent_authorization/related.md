# Related work: verifying that a web agent only does what it intends and is authorized to do
(authored by agents unless marked 🧑)

Scope: 2023+. Built on earlier maps (vlm9_agentsec, vlm10_agent/map.md, vlm11_agentbrowser/prior.md; items there are cited by pointer, not redone) plus 10 Scholar queries (as_ylo=2023, 25 s apart, no CAPTCHA hit) and arXiv API abstracts. Quotes are verbatim from arXiv abstracts fetched this session unless marked [Scholar snippet]. Cite counts are Scholar's, only where seen; "n/s" = not seen. Proof status comes from the abstract only (full texts not read) unless stated. [I] = inference. Layers: model / tool call / HTTP / browser (DOM, origin, process).

## A. Browser/origin-level confinement (already mapped in vlm10 map.md; layer = browser/HTTP)
Pointers, one line each, nothing proved:
- SOPGuard/SOPBench, Wang..Song, Gong, arXiv 2606.14027, 2026 (Scholar 4). Empirical. Browser (BrowserOS).
- ceLLMate, Meng, Feng, Shumailov, Fernandes, arXiv 2512.12594, 2025 (Scholar 32). Deterministic HTTP-request policies, no proof. HTTP.
- SPIDES, Zverev..Zanella-Béguelin, arXiv 2610.24277, Oct 2026 (new, no cites). "0% attack success rate by design"; earlier grep of full text found no theorem. Browser actions.
- Prismata, Villa..Popa, arXiv 2607.08147: "structural confinement guarantees ... labels can only decrease in privilege and mislabelings are bounded". Paper argument, no tool seen. Browser (text).
- UCM, Nikolić..Tramèr, arXiv 2607.05277; Intact/GenTree, Iqbal, arXiv 2610.22697; WAAA!, arXiv 2605.05509; "Site Isolation is Dead", Lee..B. Lee, IEEE S&P 2026 (Scholar 1); Roesner & Kohlbrenner, ICLR 2026 workshop (Scholar 9); Chrome Agent Origin Sets / User Alignment Critic, Google blog Dec 2025. All empirical or design, no proof.
- WebMCP: W3C CG draft (Permissions Policy `tools`, default allowlist 'self'); Tool Surface Poisoning arXiv 2606.06387; WebMCP-Phalanx arXiv 2608.24017 (Scholar 1): "a browser-native trust anchor that binds each tool to its registering principal through cryptographically protected capability credentials". Crypto binding, no mechanized proof seen.
- Permission Manifests for Web Agents (agent-permissions.json), Marro..Torr, arXiv 2601.02371. Cooperative, unenforced.

## B. IFC / capability designs with guarantees (tool-call layer unless noted)
1. Defeating Prompt Injections by Design (CaMeL). Debenedetti, Shumailov, ..., Tramèr. arXiv 2503.18813, 2025. Scholar n/s.
   "the untrusted data retrieved by the LLM can never impact the program flow." (v2: "solving 77% of tasks with provable security", per vlm10 map.)
   Guarantee: control flow independent of untrusted data, capability checks on data flow. Proved: argued by design, no machine-checked proof known [I]. Layer: tool call / interpreter.
2. Securing AI Agents with Information-Flow Control (FIDES). Costa, Köpf, Kolluri, Paverd, Russinovich, Salem, Tople, Wutschitz, Zanella-Béguelin. arXiv 2505.23643, 2025. Scholar 307.
   "We present a formal model to reason about the security and expressiveness of agent planners." [vlm10 map]; Scholar snippet: "we provide a noninterference guarantee for ... Despite providing a formal model and a proof of non-…" [truncated].
   Guarantee: noninterference for integrity/confidentiality labels in the planner. Proved on paper, no proof assistant seen. Layer: tool call.
3. Progent. Shi, He, Wang, Li, Wu, Guo, Song. arXiv 2504.11703, 2025 (v3 2026). Scholar n/s.
   "Each proposed update is determined by an SMT solver to be either a narrowing (applied automatically) or an expansion (requiring explicit approval), ensuring that the agent's effective action space can only shrink without approval (monotonic confinement)."
   Guarantee: every tool call checked against a symbolic policy; policy updates only narrow without approval. SMT checks one step; no proof of the system. Layer: tool call.
4. The LLMbda Calculus: AI Agents, Conversations, and Information Flow. Garby, Gordon, Sands. arXiv 2602.20064, 2026. Scholar 10.
   "Our central result is a termination-insensitive probabilistic noninterference theorem over the whole calculus, including code-generating agents ... Our harness and all proofs are in Lean."  Also: "to our knowledge the first LLM agent harness whose executable is the subject of machine-checked security theorems".
   Guarantee: noninterference over an agent calculus with labeled values; insulated variant holds when attacker picks all untrusted inputs. Proved: Lean (machine-checked). Layer: model-harness / tool call. Not web.
5. PerMIT: Securing Persistent Memory for LLM Agents via Machine-Checked Integrity Theorems. Jiang, Bai, Shahriar, Du, Swamy. arXiv 2610.28987, Oct 2026. Scholar: no count.
   "we prove two integrity theorems that are also machine-checked in Lean 4, which together ensure that environment-derived memory reaches a sensitive action only if confirmed at the gate and influences the agent's behavior only through what the gate displays."
   Guarantee: action integrity (an exact authorization property) for memory-derived values; assumes only user-typed/gate-confirmed input is trusted. Lean 4. Layer: tool call / memory interface.
6. GIF: Locally Sound Geometric Information Flow Control for LLMs. Storek, Holzer, Zhang, Jana. arXiv 2606.23277, 2026. Scholar 2.
   "we provide a fully mechanized Lean 4 proof that it upper-bounds the true information flow induced by a given prompt under local regularity assumptions."
   Guarantee: bound on input-to-output flow through the model (local, under assumptions). Lean 4. Layer: model.
7. APPA, Kravchenko et al., arXiv 2607.24625: "turns agent IFC from an abort-only barrier into a policy-governed recovery system." Abstract-level claim of proofs (label non-laundering etc.) per vlm9 survey; tool not checked. Layer: tool dispatch/MCP.
8. ROPE, Ma, Xiao, Yeoh, Zhang, Vorobeychik. arXiv 2608.27496, 2026. "Our approach admits two provable guarantees: 1) at every step of a trajectory, no value whose only origin is attacker-writable content reaches an origin-guarded parameter, and 2) no rewording of an injection changes an admission decision." Paper proofs, tool n/s. "Origin" = data provenance, not web origin. Layer: tool call.
9. Design Patterns for Securing LLM Agents against Prompt Injections. Beurer-Kellner, ..., Debenedetti, ..., Tramèr et al. arXiv 2506.08837, 2025. "we propose a set of principled design patterns for building AI agents with provable resistance to prompt injection." Informal. Layer: architecture.
10. CaMeLs Can Use Computers Too (NOVA), Foerster et al., arXiv 2601.09923: "Single-shot planning ... provides control flow integrity guarantees against arbitrary instruction injections." Names Branch Steering as residual attack. Screen agents; no proof tool. 
11. Baya (arXiv 2611.06039, Nov 2026): "compiles the user's request into an executable Python program that calls a Trusted Website API" (per vlm10 gpt.md; not read).

## C. Runtime monitors, policy enforcement, action filters (tool-call layer)
12. AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents. Wang, Poskitt, Sun. arXiv 2503.18666; ICSE 2026. Scholar 417.
    "a lightweight domain-specific language for specifying and enforcing runtime constraints on LLM agents. With AgentSpec, users define structured rules that incorporate triggers, predicates, and enforcement mechanisms"
    Guarantee: rules enforced at runtime (code, embodied, driving). No proof. Layer: tool call.
13. ProbGuard, Wang, Poskitt, Wei, Sun. arXiv 2508.00500; ASE 2026. Scholar 31 (arXiv) / 21 (ACM). "triggers an intervention when this probability falls below a user-defined threshold." Probabilistic prediction; no hard guarantee. Layer: tool call.
14. Enforcing Temporal Constraints for LLM Agents (Agent-C). Kamath, Zhang, Xu, Ugare, Singh, Misailovic. arXiv 2512.23738, 2025. Scholar: seen, count n/s.
    "provides run-time guarantees ensuring LLM agents adhere to formal temporal safety properties ... translates specifications to first-order logic, and uses SMT solving to detect non-compliant agent actions during token generation."
    Guarantee: every generated tool call satisfies a temporal spec (conformance 100% on two apps). SMT per action; no machine-checked proof of the enforcer. Layer: tool call (token generation).
15. VeriGuard. Miculicich, Parmar, Palangi, Dvijotham, ... Le (Google). arXiv 2510.05156, 2025. Scholar 63.
    "synthesizes a behavioral policy and subjects it to both testing and formal verification to prove its compliance with these specifications."
    Guarantee: the generated policy code meets a spec clarified from user intent (offline), then used as runtime monitor. Verifier is code-level (tool n/s). Layer: tool call.
16. Towards Verifiably Safe Tool Use for LLM Agents. Doshi, Hong, Xu, Kang, Kapravelos, Kästner. ICSE 2026 (ACM). Scholar 76. [Scholar snippet] "a temporal logic constraint. In practice, these specifications capture some necessary information, including sources and sinks for IFC." Abstract not read. Layer: tool call. (Kapravelos is also on WAAA!, a browser group link [I].)
17. Don't Make Models Guess Security and Safety: Symbolic Guardrails. Hong, She, Kang, Timperley, Kästner. arXiv 2604.15579, 2026. Scholar 2-3.
    "85% of benchmarks do not state verifiable requirements ... 74% of requirements are symbolically enforceable and 95% of these need only simple, low-cost checks"
    Guarantee: symbolic checks give "guarantees for some security and safety requirements"; no proof tool. Layer: tool call.
18. ShieldAgent. Chen, Kang, Li. arXiv 2503.22738, 2025. Scholar 216. "enforce explicit safety policy compliance for the action trajectory of other protected agents through logical reasoning." Probabilistic rule circuits, LLM in the loop; no proof.
19. Sapien. Tiffany, Zhang, Bagdasarian, Tsai. arXiv 2610.00797, 2026. "A Sapien policy specifies permitted tool-call sequences using a regular expression extended with stateful predicates" ; "rule out 93-95% of attacks on AgentDojo". Empirical, no proof. Builds on Conseca.
20. Contextual Agent Security (Conseca). Tsai, Bagdasarian. arXiv 2501.17070, 2025. "a framework to generate just-in-time, contextual, and human-verifiable security policies." No proof.
21. ActGov. Zhang, Peng, Jiang, Zhang. arXiv 2609.24446, 2026 (Scholar 4). "each update verified through SMT-based counterexample checking ... permits it only if it remains within the task-scoped authorization boundary". SMT; no proof of the whole. Layer: tool call.
22. Formal Runtime Verification for Tool-Using LLM Agents (MonPoly/MFOTL on AgentDojo, STAC). Kekatos et al. arXiv 2610.09793; ACM 2026 (Scholar 2). "five generic obligations flag 71.8% of STAC attack chains ... but also fire on 29.3% of benign runs"; "one planted line defeats a naive provenance check on 94-99% of the runs". Runs the "unmodified MonPoly monitor" offline, so the verified kernel (VeriMon, Isabelle) is not what is run [I]. Useful negative result.
23. Type-Checked Compliance (Lean-Agent Protocol). Rashie, Rashi. arXiv 2604.01483, 2026 (Scholar 3). "Every proposed agentic action is treated as a mathematical conjecture: execution is permitted if and only if the Lean 4 kernel proves that the action satisfies pre-compiled regulatory axioms." Lean 4 checks each action against auto-formalized policy; finance domain, single-author preprint; guarantee is only as good as auto-formalization [I]. Layer: tool call.
24. Provably Secure Agent Guardrail (ePCA). Wu, Zhang, Chen, Fang, Yu. arXiv 2605.29251, 2026 (Scholar 7). "forcing agents to losslessly formalize their intentions into first-order logical mathematical constraints before performing physical operations." Proof status not read; "verifiable unreachability" in snippet.
25. Lean4Agent. Wang, Huang, ..., Zhang. arXiv 2606.06523, 2026 (Scholar 1). "FormalAgentLib, an extensible Lean4 library for formally modeling and verifying agent workflows' semantic consistency under explicit assumptions". Lean 4, but verifies workflow consistency, not security; gains are empirical (+11.94%).
26. AgentLTL, Elkoussy, Perez, arXiv 2607.02599 (Scholar 8); Temporal Guardrails for LLM Conversations, Cohen, Havelund, Omer, Peled, 2026 (Scholar 5; past-time LTL runtime verification); AgentGuard, Koohestani, ASE 2025 workshop (Scholar 31; probabilistic temporal logic); AgentVerify, Fang, preprints.org 2026 (Scholar 5; LTL model checking); Causal Past Logic for LLM agent workflows, Bollig, arXiv 2605.20923. Logic specs; model checking / runtime verification; no mechanized soundness seen.
27. Lingering Authority (PORTICO). Santos-Grueiro. arXiv 2606.22504, 2026 (Scholar 13). "a reference monitor for revocable capabilities exposed to the planner ... The monitor assumes mediated tools and a sound typed catalog." Empirical on coding agents; no proof.
28. Local Allow, Global Deny: Why Per-Action Authorization Does Not Compose. Pandey, Jain, Chen, Maple. arXiv 2610.27620, 2026. "relational purpose violations form a 2-safety hyperproperty with no per-trace locus of blame, so a per-action monitor that never raises a false alarm detects none of them".
    Guarantee: impossibility result (theory) plus AL-SYNTH, a bounded SAT/SMT model. [I] Directly limits per-action filters, including browser ones.

## D. Intent / authorization specs, delegation (HTTP/service layer)
29. PAuth / Beyond OAuth: Task-Scoped Authorization for AI Agents via Natural Language Slices. Sharma, Jiang, Chen, Lin. arXiv 2603.17170, 2026. Scholar 8.
    "submitting a concrete NL task implicitly authorizes exactly the operations its faithful execution requires, even when the agent is compromised ... Each server independently derives an NL slice, a symbolic specification of the expected call". Server-side, signed value envelopes. Guarantee: every operation (operator plus operands) consistent with task. Proof n/s. Layer: HTTP/web service. Closest to "OAuth for operands".
30. The Agent Clicks Approve. Hossen. arXiv 2610.15138, 2026. "The authority envelope gate has the service accept a request only when it matches the task's envelope". "Without a defense the unauthorized action completed in all 73 attack runs." Empirical; browser agent, HTTP/service check.
31. Authenticated Delegation and Authorized AI Agents. South, Marro, Hardjono, Mahari, ... Chan et al. arXiv 2501.09674, 2025 (ICML position version, Scholar 190 and 67). "extending OAuth 2.0 and OpenID Connect with agent-specific credentials and metadata". Protocol proposal; no proof.
32. Agentic JWT. Goswami. arXiv 2509.13597, 2025. Scholar 22. "a dual-faceted intent token that binds each agent's action to verifiable user intent and, optionally, to a specific workflow step". Crypto tokens; no proof.
33. Before the Tool Call (Open Agent Passport). Uchibeke. arXiv 2603.20953, 2026. Scholar 32 (from vlm10 map). "a declarative policy ... produces a cryptographically signed audit record"; 0% success over 879 attempts on a bounty testbed. Empirical.
34. Cryptographically Verifiable Authorization for Autonomous AI Agents. Llambí-Morillas, Fernández-Fernández. arXiv 2607.21325, 2026. "a cryptographically verifiable relation ... authorization soundness, principal binding, request binding, policy binding, and replay resistance"; Groth16 zk-SNARK PoC. Crypto, not mechanized.
35. Identity management for agentic AI, South et al., arXiv 2025 (Scholar 46); OAuth Is Not Enough, Chopra, TechRxiv 2025 (Scholar 5); Authorization architectures for tool-using AI agents, arXiv 2026 (Scholar 8); Rethinking Access Control for AI Agents, Zhou, Zhang, arXiv 2611.06764 (survey). Position/architecture papers.
36. Compromise Is Not Consequence: task-scoped authorization with paired replay. Hagverdiyev. arXiv 2610.05840 (Scholar 1). Evaluation study.

## E. Intent-alignment monitors (model-based, no guarantee)
37. When Actions Go Off-Task (DeAction, MisActBench). Ning, ..., Sun. arXiv 2602.08995, 2026. Scholar 9. "a practical and universal guardrail that detects misaligned actions before execution". Model-based. Layer: computer-use actions.
38. ST-WebAgentBench. Levy et al. ICLR 2026 (Scholar 181). Web-agent safety/trust benchmark.
39. Bypassing AI Control Protocols via Agent-as-a-Proxy. Isbarov, Kantarcioglu. arXiv 2602.05066. "current monitoring-based agentic defenses are fundamentally fragile regardless of model scale." Attack on LLM monitors (AlignmentCheck etc.).
40. Task-tampering IPI benchmark, arXiv 2611.07640: "A tool-policy defense still allows 15.4% attack success, close to 17.0% without a defense, because these attacks generally retain expected tools and manipulate values obtained during execution." Shows tool-name policies miss value-level attacks.
41. Verisafe Agent (mobile GUI agent, logic-based action verification), Lee et al., 2025 (Scholar, ACM); not read.

## F. Older verified browser/web models (from vlm11 prior.md; not agent-aware)
- Quark, Jang, Tatlock, Lerner, USENIX Sec 2012. Coq-verified browser kernel. "specification implies several security properties, including tab non-interference, cookie integrity and confidentiality, and address bar integrity." Proof: Coq. Layer: browser kernel (tabs, cookies, address bar). Pre-2023, but the only machine-checked browser-origin guarantee found.
- WebSpec, IEEE S&P 2023; Akhawe et al. CSF 2010 (Alloy); CSP semantics, Calzavara et al.; IBOS. Spec-level or Alloy/Isabelle-style models, none agent-aware.

## (a) How crowded
[I] Counts from this table: about 40 entries, plus about 10 pointers; roughly 85% dated 2025-2026, about 60% dated 2026. Subareas:
- Tool-call policy/monitor/guardrail (C): about 15 works; very crowded, mostly 2026. Many near-duplicates (AgentSpec line, Sapien, ActGov, Progent, Agent-C, symbolic guardrails).
- IFC/capability (B): about 10; CaMeL/FIDES lineage, now being mechanized (LLMbda, PerMIT, GIF all 2026 and Lean).
- Authorization/delegation (D): about 12; mostly protocol proposals and position papers, many unreviewed single-author preprints. Only PAuth and Hossen are web-service-specific and evaluated.
- Browser/origin confinement (A): about 10 within Jun-Oct 2026 (SOPGuard, SPIDES, Prismata, UCM, Intact, WAAA!, Site Isolation is Dead); converging fast. Chrome Agent Origin Sets and ceLLMate are the 2025 anchors.
- Trend: 2023-2024 was benchmarks (AgentDojo, InjecAgent, WASP). 2025: CaMeL, FIDES, Progent, AgentSpec. 2026: browser-specific work, then machine-checked proofs (Lean) of agent IFC. Scholar cite counts are high only for AgentSpec (417), FIDES (307), ShieldAgent (216), South et al. (190), ST-WebAgentBench (181); the browser items are 0-32 [I: too new to read as importance].

## (b) Machine-checked guarantees over a browser/origin/HTTP model
None found for 2023+. Evidence:
- Lean/Coq/Verus results exist only at the agent-harness or tool-call layer: LLMbda (noninterference, Lean), PerMIT (action integrity, Lean 4), GIF (model-level flow bound, Lean 4), Lean-Agent Protocol (per-action Lean check, finance), Lean4Agent (workflow consistency).
- Browser/origin/HTTP works (SOPGuard, ceLLMate, SPIDES, Prismata, UCM, Intact, PAuth, Hossen, Chrome) are empirical or "by design"; SPIDES had no theorem by grep (vlm10), Prismata states paper-level confinement properties. SMT is used by Progent, Agent-C, ActGov per step, not to prove the system.
- The only machine-checked browser model is Quark (Coq, 2012), which predates agents and has no LLM or cross-origin data-flow channel.
- Caveat: I read abstracts and Scholar snippets, not full texts, for most of the above; APPA, ROPE, Provably Secure Agent Guardrail and Doshi et al. may contain proofs whose tool I did not see. Google Scholar and arXiv searches cannot show absence with certainty.

## (c) Gaps seen
1. No mechanized noninterference or authorization theorem stated over frames, origins, cookies, and HTTP requests of a browser that an agent drives. LLMbda's Lean harness is the nearest template [I]: its labels could be origins and its sinks browser actions or requests.
2. "Intends" vs "authorized" is unformalized for the web: PAuth derives per-operation expectations server-side, Hossen uses a task envelope, but nothing proves the envelope equals the user's intent; the spec-to-intent step stays an LLM (VeriGuard, Lean-Agent Protocol, ePCA all rely on auto-formalization).
3. Composition: Pandey et al. show per-action authorization cannot catch relational purpose violations; browser monitors (ceLLMate, Origin Sets) are per-action [I].
4. Monitor soundness: LLM critics are bypassable (Agent-as-a-Proxy); Kekatos et al. show trace-provenance itself is attackable; value-level attacks pass tool-name policies (2611.07640).
5. Trusted computing base: verified policy checkers are not paired with a verified or minimal enforcement point (the extension, BrowserOS patch, or Chrome gating function); Quark-style small verified kernel for an agent browser is not found.
6. WebMCP: no formal model of `tools` Permissions Policy, tool registration across frames, or Phalanx credentials.
7. Vision agents: no per-frame provenance for screenshots (vlm10).
