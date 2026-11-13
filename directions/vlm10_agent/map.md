# Map of prior work: security for AI agents that use web browsers
(authored by agent, 2026-11-06. Every quote below was read from the real abstract or page via the human's browser; raw files in `raw/map_*`. Items marked [not read] were seen only as titles or snippets.)

Method note (fact): Google Scholar served a CAPTCHA once (after ~13 Scholar fetches); I did not touch it, waited, retried once later (worked), then paced Scholar and used arXiv, IEEE, vendor pages and `--source google`. Google "AI Overview" text was never used as evidence: it was wrong at least twice (it claimed a SPIDES noninterference proof that the paper does not contain, and linked an unrelated skills paper as "formal analysis").

## 1. Origin / same-origin confinement for browser agents

- Same-Origin Policy for Agentic Browsers (SOPGuard, SOPBench). Xilong Wang, Xiaoxing Chen, Patrick Li, Dawn Song, Neil Gong. arXiv 2606.14027, Jun 2026 (v3 30 Jun). https://arxiv.org/abs/2606.14027
  - what: measures SOP violations in existing agentic browsers, adds an SOP enforcement mechanism inside BrowserOS.
  - quote: "an agentic browser can itself serve as an automated channel for cross-origin data flows, potentially leading to SOP violations." and "Our evaluation shows that existing agentic browsers frequently violate SOP, both in benign settings and under attacks."
  - cited by (Scholar, 4): WAInjectBench (2510.01354), SPIDES, Hossen "The Agent Clicks Approve" (2610.15138), Maharaj SSRN 7276838.
- ceLLMate: Sandboxing Browser AI Agents. Luoxi Meng, Henry Feng, Ilia Shumailov, Earlence Fernandes. arXiv 2512.12594, Dec 2025 (v2 Mar 2026). https://arxiv.org/abs/2512.12594
  - what: browser extension that enforces policies on the agent's HTTP requests.
  - quote: "a browser-level sandboxing framework that restricts the agent's ambient authority and reduces the blast radius of prompt injections." / "Our core insight is to perform sandboxing at the HTTP layer"
  - cited by (Scholar, 32; first page of 10 read): Meta SecAlign, DataFilter, "CaMeLs Can Use Computers Too", "Systems security foundations for agentic computing", SecOPD, "Before the tool call" (2603.20953), Roesner and Kohno "Reflections on Trusting Trust, Revisited", "Rethinking agent security as a networking problem" (2608.12172), "Personalizing Agent Privacy Decisions via Logical Entailment". None of the ten is a browser-isolation paper. Pages 2-4 not read.
- SPIDES: Information-Flow Control for Browser Agents. Egor Zverev, Juhee Kim, Leon Trampert, Boris Köpf, Aashish Kolluri, Shruti Tople, Santiago Zanella-Béguelin. arXiv 2610.24277, 16 Oct 2026. https://arxiv.org/abs/2610.24277
  - what: IFC over primitive browser actions; labels come from site-supplied per-element HTML annotations.
  - quote: "We argue that restoring SOP is neither sufficient (a same-origin public sink can leak private data) nor necessary (legitimate tasks require authorized cross-origin flows)". Full text, section on labels: "operators of these origins annotate DOM (Document Object Model) elements with integrity and confidentiality labels; content from other origins is treated as untrusted." (attributes `data-ifc-integrity`, `data-ifc-readers`)
  - evaluation (full text): "SPIDES blocks all attacks, while 53.2 – 73.2 % succeed against SOPGuard and 4.6 – 6.8 % against UCM."
  - proof status: abstract says "0% attack success rate by design"; I grep'd the HTML for "theorem" and "noninterference": zero hits. So no stated proved theorem (fact for the text I could grep).
  - cited by: none listed in Scholar (new).
- What It Is, Not What It Says: Securing Agentic Browsing Interactions with Web Semantics (Intact, GenTree). Umar Iqbal. arXiv 2610.22697, 15 Oct 2026. https://arxiv.org/abs/2610.22697
  - what: per-element provenance tree (third-party scripts, iframes) and element-at-a-time planning on an unmodified browser.
  - quote: "Browsers enforce semantics under which what an element can do depends on what it is and where it comes from, not on what it says. Agents flatten these semantics" and "GenTree attributes 2.3x as many elements to third parties as the browser, which misattributes 58.7% of them to the first party."
  - full text: "The same-origin policy keeps one origin's code from reading or acting on another origin's content [23], and site isolation enforces this boundary with separate processes [24]. A representation that flattens the page into one text or one image erases these boundaries". Intact reuses the semantics but its "virtual isolation" is prompt-level (one element per LLM call), not Site Isolation processes.
- Agentic Browsers and the Same-Origin Policy. Franziska Roesner, David Kohlbrenner. ICLR 2026 AIWILD workshop. https://openreview.net/forum?id=eY39fMYy2F ; page https://agent-security.cs.washington.edu/agentic_browsers_sop.html
  - what: tests seven agentic browsers; PoC cross-origin theft on ChatGPT Atlas.
  - quote: "In the least restrictive cases, we find that if a malicious website can mount a successful prompt injection, then it can leverage the browser agent to circumvent the same-origin policy"
  - cited by (Scholar, 9): SOPGuard, Hossen, Maharaj, FP-Agent, Roesner-Kohno trusting-trust, others off-topic.
- Chrome, "Architecting Security for Agentic Capabilities in Chrome" (Agent Origin Sets, User Alignment Critic). Nathan Parker, Chrome security team. Google blog, 8 Dec 2025. https://blog.google/security/architecting-security-for-agentic/
  - what: gating function splits origins into read-only and read-writable sets per session; unrelated iframes are not shown to the model.
  - quote: "Site Isolation and the same-origin policy are fundamental boundaries in Chrome's security model and we're carrying forward these concepts into the agentic world." / "if an unrestricted agent is compromised and can interact with arbitrary sites, it can create what is effectively a Site Isolation bypass." / "This also gives the browser the ability to enforce some of that separation, such as by not even sending to the model data that is outside the readable set."
- Site Isolation is Dead: How Site Isolation is Broken in Agentic Browsers and Extensions. Suyoung Lee, Seongho Keum, Changoo Lee, Dongwon Shin, Sanghyun Hong, Byoungyoung Lee (+ Sooel Son per PDF header). IEEE S&P 2026 (18-21 May). https://ieeexplore.ieee.org/abstract/document/11573584/ ; PDF https://wsp-lab.github.io/papers/lee-sp26.pdf [PDF not machine-readable here; abstract and artifact README read] ; artifacts https://github.com/WSP-LAB/Site-Isolation-Is-Dead
  - what: attacks the IPC between untrusted renderers and the privileged agent process in 2 open-source agentic browsers and 7 agent extensions.
  - quote: "identifying a common architectural pattern: privileged processes manage user prompts and agent operations, while untrusted renderer processes are isolated, with inter-process communication (IPC) channels serving as their bridge." / "Our evaluation shows that all tested agentic browsers and extensions are vulnerable to these attacks, revealing that existing implementations often fail to properly account for IPC channels." / "We conclude with actionable defense guidelines for strengthening site isolation in agentic browsers and extensions."
  - README: attacks start from "arbitrary code execution within the renderer" (a compromised-renderer threat model); it ships "patches that implement our proposed guardrail system to detect and mitigate Indirect Prompt Injection (IPI) attacks" for Nanobrowser and BrowserOS.
  - cited by (Scholar, 1): Hossen 2610.15138 only.
  - relevance (inference): this is the one paper that is about Chromium Site Isolation and agents. It treats Site Isolation as the boundary the agent code must respect and attacks the agent-side IPC; it does not use Site Isolation processes to confine what the agent reads. Its guardrail is an IPI detector, not a process-level mechanism, as far as README says.
- WAAA! Web Adversaries Against Web Agents (Scholar title: "...Agentic Browsers"). Sohom Datta, Alex Nahapetyan, William Enck, Alexandros Kapravelos. arXiv 2605.05509, May 2026 (v2 29 Oct). https://arxiv.org/abs/2605.05509
  - what: web-focused threat model and 20-attack taxonomy for agentic browsers.
  - quote: "frames the agent as a confused deputy unable to distinguish task steps from traditional web attacks" and "demonstrating the need to rearchitect agentic browsers before they are ready for the current web."
- The Agent Clicks Approve. Md Imran Hossen. arXiv 2610.15138, 10 Oct 2026. https://arxiv.org/abs/2610.15138
  - what: injected page text makes an agent approve OAuth grants; fix is a server-side check against a task "authority envelope".
  - quote: "The authority envelope gate has the service accept a request only when it matches the task's envelope, the client and account or the webhook URL that the user's task named, fixed before the agent starts."
- Prismata: Confining Cross-Site Prompt Injection in Web Agents. Corban Villa, Alp Eren Ozdarendeli, Sijun Tan, Raluca Ada Popa. arXiv 2607.08147, 9 Jul 2026. https://arxiv.org/abs/2607.08147
  - what: infers per-content permission labels at runtime, then redacts content and restricts agent capabilities; no developer annotations.
  - quote: "Prismata's dynamic trust derivation produces permission labels for page content, with structural confinement guarantees, inspired by classical integrity models, that bound any labeling errors so that labels can only decrease in privilege and mislabelings are bounded."
- Untrusted Content Masking for Web Agents with Security Guarantees (UCM). Kristina Nikolić, Egor Zverev, Javier Rando, Matthew Jagielski, Edoardo Debenedetti, Florian Tramèr. arXiv 2607.05277, 6 Jul 2026. https://arxiv.org/abs/2607.05277
  - what: uses the DOM to redact untrusted regions before the agent sees them; sandboxed interface with privilege separation.
  - quote: "a webpage's Document Object Model (DOM) encodes sufficient information to distinguish trusted from untrusted regions without reading their content."
  - cited by (Scholar snippet): 5 [not opened].
- ROPE: Routed Origin Policy Enforcement against Indirect Prompt Injection. Xinhang Ma, Chaowei Xiao, William Yeoh, Ning Zhang, Yevgeniy Vorobeychik. arXiv 2608.27496, Aug 2026. https://arxiv.org/abs/2608.27496
  - what: "origin" here means data provenance for tool parameters (not web origins); deterministic check.
  - quote: "Our approach admits two provable guarantees: 1) at every step of a trajectory, no value whose only origin is attacker-writable content reaches an origin-guarded parameter, and 2) no rewording of an injection changes an admission decision."
- Cognitive Firewall (arXiv 2603.23791, Qianlong Lan, Anuj Kaul, Mar 2026): "a deterministic Guard that enforces execution-time policies" (edge visual sentinel plus cloud planner). https://arxiv.org/abs/2603.23791

## 2. Structural-guarantee defenses for generic agents (CaMeL line)

- Defeating Prompt Injections by Design (CaMeL). Debenedetti, Shumailov, Fan, Hayes, Carlini, Fabian, Kern, Shi, Terzis, Tramèr. arXiv 2503.18813 (v2 Jun 2025). https://arxiv.org/abs/2503.18813
  - what: plan from trusted query; capability-tracking interpreter.
  - quote: "the untrusted data retrieved by the LLM can never impact the program flow." Current v2 says "solving 77% of tasks with provable security (compared to 84% with an undefended system) in AgentDojo" (the survey's 67% is not on the page now).
- Securing AI Agents with Information-Flow Control (FIDES). Costa, Köpf, Kolluri, Paverd, Russinovich, Salem, Tople, Wutschitz, Zanella-Béguelin. arXiv 2505.23643 (v2 Sep 2025). https://arxiv.org/abs/2505.23643
  - quote: "We present a formal model to reason about the security and expressiveness of agent planners."
- Progent: Securing AI Agents with Privilege Control. Shi, He, Wang, Li, Wu, Guo, Song. arXiv 2504.11703 (v3 May 2026). https://arxiv.org/abs/2504.11703
  - quote: "ensuring that the agent's effective action space can only shrink without approval (monotonic confinement)."
- CaMeLs Can Use Computers Too (NOVA). Foerster, Blanchard, Nikolić, Shumailov, Zhang, Mullins, Papernot, Tramèr, Zhao. arXiv 2601.09923 (v3 Jun 2026). https://arxiv.org/abs/2601.09923
  - what: CaMeL-style single-shot branching plan for screen-based agents; names "Branch Steering" as residual attack.
  - quote: "Single-shot planning, where a trusted planner emits upfront a complete branching plan covering all anticipated runtime states, provides control flow integrity guarantees against arbitrary instruction injections."
- APPA: Recoverable Information-Flow Control for Real-World LLM Agents. Kravchenko, Liventsev, Konstantinov, Iskhakov, Kukuy. arXiv 2607.24625 (v2 Aug 2026). https://arxiv.org/abs/2607.24625
  - quote: "turns agent IFC from an abort-only barrier into a policy-governed recovery system." (tool-dispatch and MCP gateway level, not browser).
- Systems security foundations for agentic computing. Christodorescu, Fernandes, Hooda et al. arXiv 2512.01295. https://arxiv.org/abs/2512.01295 [Scholar snippet only; Google snippet: "security policies: Content Security Policy determines which ..."; not opened].

## 3. Vision / screenshot agents

- Towards Safe Autonomy for Computer Use (SA-CUA). Dominik Seip, Bartol Markovinović, Matthias Hein. arXiv 2610.18508, 13 Oct 2026. https://arxiv.org/abs/2610.18508
  - what: masks screenshot regions using the OS accessibility tree so the privileged LLM sees only trusted regions.
  - quote: "deriving conservative deterministic rules from the accessibility tree for unmasking trusted regions from the privileged LLM's screenshot, keeping trusted and untrusted content separated."
  - note: OS-level (windows, toolbars vs app content), not per-frame web origin.
- SnapGuard (screenshot injection detector, arXiv, Du et al. 2026), VPI-Bench, WebInject (Wang et al., ACL 2025), Brave screenshot post: detection/attack side, not provenance. Brave quote (verified on page): "indirect prompt injection is not an isolated issue, but a systemic challenge facing the entire category of AI-powered browsers." https://brave.com/blog/unseeable-prompt-injections/

## 4. Site-declared agent policies

- Permission Manifests for Web Agents (agent-permissions.json). Samuele Marro, Alan Chan, ... Philip Torr, Jiaxin Pei. arXiv 2601.02371 (Dec 2025, v2 Jan 2026). https://arxiv.org/abs/2601.02371
  - what: robots.txt-style site manifest of allowed agent interactions; cooperative, not browser-enforced.
  - quote: "a robots.txt-style lightweight manifest where websites specify allowed interactions, complemented by API references where available."
- SPIDES (above): site-supplied `data-ifc-*` labels, enforced by the agent harness.
- WebMCP spec (W3C Web Machine Learning CG draft). https://webmachinelearning.github.io/webmcp/
  - what: sites expose tools to agents; gated by a Permissions Policy feature; spec has threat sections.
  - quote: "Access to the APIs in this specification is gated behind the policy-controlled feature "tools", which has a default allowlist of 'self'." / "By default, WebMCP enforces strict same origin isolation: a tool registered via document.modelContext.registerTool() is only visible to and executable by Documents that are same origin with the registering Document" / annotation `untrustedContentHint`: "indicates that the tool's output contains data that is untrusted, from the perspective of the author registering the tool."
- Agent Security Policy (SSRN 6876926, P MK): Scholar snippet "Content Security Policy worked because browsers, not JavaScript, decided" [not opened; SSRN, not peer reviewed].
- Towards an Agent-First Web (Bandara et al., arXiv 2606.19116) is about access/economics, not security: "agent identification metadata in HTTP requests". Not relevant to enforcement.

## 5. WebMCP security

- WebMCP Tool Surface Poisoning. Lin-Fa Lee, Yi-Yu Chang, Chia-Mu Yu, Kuo-Hui Yeh. arXiv 2606.06387, 4 Jun 2026. https://arxiv.org/abs/2606.06387
  - quote: "attackers leverage third-party scripts to inject malicious tools during an active session."
- WebMCP-Phalanx. Lin-Fa Lee, Yi-Yu Chang, Kuo-Hui Yeh. arXiv 2608.24017, 25 Aug 2026 (AAAI 2027 per comments). https://arxiv.org/abs/2608.24017
  - quote: "a browser-native trust anchor that binds each tool to its registering principal through cryptographically protected capability credentials and propagates provenance labels throughout the tool lifecycle." It states a CSP analogy in the full text snippet seen on Scholar ("analogous to a Content Security Policy (CSP)"; context not read).
- WebMCP and the Browser As an MCP Server (Springer chapter) [Scholar snippet only].

## 6. Benchmarks and prompt-injection measurement (web agents)

- WASP. Evtimov, Zharmagambetov, Grattafiori, Guo, Chaudhuri. arXiv 2504.18575 (Apr 2025; Scholar also lists a NeurIPS proceedings version). https://arxiv.org/abs/2504.18575
  - quote: "even top-tier AI models, including those with advanced reasoning capabilities, can be deceived by simple, low-effort human-written injections in very realistic scenarios."
- WAInjectBench (Liu, Wang, Xu, Jia, Gong; arXiv 2510.01354); AgentDojo (2406.13352); InjecAgent (2403.02691); VPI-Bench (id 2506.02456 per survey, unchecked); BrowseSafe (2511.20597); Stakeholder-centric benchmark (Wang et al. 2026); Indirect prompt injection in the wild (Khodayari et al. 2026) [titles and Scholar snippets only; not opened this session].
- Measuring Indirect Prompt Injection in Autonomous Web Agents, S Maharaj, SSRN 7276838, 2026 (cites SOPGuard). Snippet: "Autonomous web agents collapse a security boundary that conventional browsers spent decades making explicit." [not opened].

## 7. Products and vendor posts

- OpenAI, "Continuously hardening ChatGPT Atlas against prompt injection", 22 Dec 2025. https://openai.com/index/hardening-atlas-against-prompt-injection/ . Quote (page now fetched fine): "Prompt injection, much like scams and social engineering on the web, is unlikely to ever be fully "solved"." Also "prompt injection remains an open challenge for agent security".
- Brave, unseeable prompt injections (Comet, Fellou), 21 Oct 2025 (quote in section 3).
- Chrome with Gemini: see section 1 (Chrome blog).
- Browserbase containment post (Feb 2026). https://www.browserbase.com/blog/ai-browser-prompt-injection-containment-security . Quote: "Each browser session runs in a dedicated VM through hardware virtualization isolation."
- Cloudflare Kitesurf, 6 Aug 2026. https://blog.cloudflare.com/kitesurf/ . Quote: "an agent is pointed at whatever a task demands: arbitrary code from arbitrary origins. So we built this browser on the assumption that every page load is untrusted input and every session starts fresh." Also: "Every next page or out-of-process iframe (OOPIF) uses Dynamic Workers to spin up a long-lived PageScript isolate". (Kitesurf reimplements an OOPIF-per-isolate model; it is a rendering engine, not an agent-confinement policy.)
- Anthropic Claude in Chrome safety pages: not re-fetched [survey only].
- Roesner/Kohlbrenner page (section 1) warns: "we recommend that users proceed with caution in choosing to use agentic browser features, as the security models have not yet been worked out. We particularly caution against the use of Claude for Chrome".

## (a) Quote check of out/vlm9_agentsec/REPORT.md

Quotes attributed to outside sources in REPORT.md:
1. Chrome blog: "This prevents a compromised agent from acting arbitrarily on unrelated origins" - VERIFIED, exact, at https://blog.google/security/architecting-security-for-agentic/ (Dec 8 2025). Context sentence before it: "Our design architecturally limits the agent to only access data from origins that are related to the task at hand, or data that the user has chosen to share with the agent."
2. SOPGuard: "existing agentic browsers frequently violate SOP" - VERIFIED (arXiv 2606.14027 abstract: "...frequently violate SOP, both in benign settings and under attacks.").
3. ceLLMate: "restricts the agent's ambient authority" - VERIFIED (abstract: "a browser-level sandboxing framework that restricts the agent's ambient authority and reduces the blast radius of prompt injections").
4. Kitesurf: "every page load is untrusted input" - VERIFIED (substring of the sentence quoted in section 7).
5. D3 and head quotes by the human (🧑) - not source-checkable; skipped.
6. gpt.md quotes ("restore browser security principals across the agent path"; "The web's origin principal is too coarse for agents") - VERIFIED against `out/vlm9_agentsec/gpt.md` lines 1 and 69 (that is a local file, not a web page).

Claims in REPORT.md that the real pages contradict or soften (fact):
- DIFFERENT: "All are label or policy layers, not the browser's own enforcement." Chrome's post describes browser-side enforcement: "This also gives the browser the ability to enforce some of that separation, such as by not even sending to the model data that is outside the readable set" and "Iframes from origins that aren't related to the user's task are not shown to the model." ceLLMate is an extension (browser-level but not browser-internal); SOPGuard is built into BrowserOS (a Chromium fork). So Chrome's is in-browser; whether it uses Site Isolation processes is not stated.
- DIFFERENT: "Chrome's post cites Site Isolation only as the boundary its origin sets protect." Real text also says an unrestricted agent "can create what is effectively a Site Isolation bypass" and "we're carrying forward these concepts into the agentic world." Same idea, stronger wording; the post still gives no process-level mechanism.
- DIFFERENT: "survey found no work using Site Isolation processes to confine agents" is still true of what I found, but "Site Isolation is Dead" (S&P 2026) now exists as a paper on Site Isolation vs agent architecture (attack side), and Intact cites Reis et al. Site Isolation. See sections 1 and (b).
- DIFFERENT: "SOPGuard is empirical" fits the abstract; but SPIDES (not in REPORT) now claims "0% attack success rate by design" and beats SOPGuard in its own testbed.
- DIFFERENT (survey.md, not REPORT): CaMeL "67%" is now "77% of tasks with provable security" (v2).
- DIFFERENT (survey.md): OpenAI quote with "solved" lacked quotation marks; real text is "unlikely to ever be fully "solved"" (the word solved is in scare quotes on the page).
- NOT FOUND (survey.md): "Roesner and Kohlbrenner ... recommends provenance tracking." The abstract, OpenReview page and UW project page contain no such recommendation (word "provenance" absent on the UW page); the PDF was not machine-readable here, so it is unverified rather than refuted.
- NOT CHECKED: REPORT states Kitesurf "per survey, reimplements the process model instead of reusing Site Isolation." The Kitesurf post does describe isolate-per-page and per-OOPIF, consistent with that; "instead of reusing Site Isolation" is an inference (Kitesurf is not Chromium).
Other survey.md quotes I re-checked and found VERIFIED exactly: Brave "systemic challenge"; Browserbase "dedicated VM"; WebMCP three quotes; CaMeL "can never impact the program flow"; FIDES "explores the use of information-flow control (IFC)..." (page: "This paper explores the use of information-flow control (IFC) to provide security guarantees for AI agents."); Progent "monotonic confinement"; UCM DOM quote; APPA quote; WASP quote; ceLLMate quote; SOPGuard quote. Not re-checked: AgentDojo, InjecAgent, VWA-Adv, Anthropic pages, ShadowPrompt, Brave Comet part 1.

## (b) What looks open (inference from absence in my searches; not proof)

Queries run (Scholar unless noted; date filter 2025+):
1. same-origin policy agentic browser
2. ceLLMate sandboxing browser AI agents (then cited-by of ceLLMate, SOPGuard, Roesner, Site Isolation is Dead)
3. site isolation agentic browsers (retry run)
4. "Content Security Policy" LLM agent browser prompt injection agents trust declared by website
5. WebMCP security tool poisoning browser agents
6. screenshot provenance web agent prompt injection (Scholar, second try after CAPTCHA)
7. [CAPTCHA, not bypassed] screenshot provenance ... per-frame origin
8. Google: agentic browser screenshot per-frame origin provenance prompt injection arxiv
9. Google: browser agent "Site Isolation" out-of-process iframe confine LLM agent prompt injection arxiv
10. Google: agent policy declared by website "Permissions Policy" OR CSP for AI agents browser agent trust regions arxiv
11. Google: noninterference proof browser agent origin model formal verification agentic browser information flow arxiv 2026
12. Google: computer use agent screenshot trust boundary pixel provenance untrusted regions screenshot masking prompt injection
13. Google: Roesner Kohlbrenner ...; "Site Isolation is Dead" pdf; agentic browser OOPIF ... per-origin agent instances; agentic browser prompt injection defense per-origin agent contexts ...
14. arXiv listing: "agentic browser site isolation"; "screenshot provenance web agent" (arXiv search is AND-of-words and returned nearly nothing useful).
Not searched at all: Permissions Policy/iframe `sandbox`/COOP/COEP + agent as exact phrases on Scholar; Chromium bug tracker and W3C issue trackers; Firefox/Edge/Safari agent docs; USENIX/CCS 2026 proceedings directly; Scholar pages 2+ of ceLLMate cited-by.

What looks open:
1. Using the browser's real isolation machinery as the enforcement. Closest: Chrome's origin sets (in-browser gating, no process claim), "Site Isolation is Dead" (attack, plus guardrail patches), Intact (reuses semantics, but "virtual isolation" is one-LLM-call-per-element), Kitesurf (isolate per page/OOPIF, but a browser engine). I found no paper that runs per-site agent instances inside Site Isolation processes or OOPIFs and measures it. Weaker than the REPORT's claim: the area is no longer empty of Site-Isolation-and-agents work.
2. Formal guarantee over a browser/origin model. ROPE ("two provable guarantees") and Prismata ("structural confinement guarantees") and CaMeL/FIDES are over tool-call or label models; SPIDES says "by design" with no theorem found by grep; SOPGuard, ceLLMate, Intact are empirical. A mechanized noninterference statement over frames, origins and requests was not found.
3. Per-frame provenance for pixels. Intact and SPIDES keep per-element provenance for DOM/accessibility snapshots, not for screenshots; SA-CUA masks screenshots via the OS accessibility tree (windows, not frames). No compositor-level, per-frame origin provenance for vision agents found.
4. Agent CSP / site-declared policy enforced by the browser. Declared-policy pieces exist but none is browser-enforced for agents' reads: SPIDES `data-ifc-*` (enforced by harness, trusted origins listed by user), agent-permissions.json (cooperative), WebMCP Permissions Policy `tools` (gates tool registration across frames, not what the agent reads), UCM discussion of "an honest site" as trust anchor (Scholar snippet). No CSP-like header that tells the browser which regions an agent may treat as trusted/untrusted was found.
5. WebMCP security: now two papers (Tool Surface Poisoning, Phalanx), both from one group; no independent group yet, no formal analysis. The REPORT's "little independent analysis" still holds, but "little analysis" no longer does.
6. Contested/converged space to treat as crowded: SOP for agents (SOPGuard, Roesner-Kohlbrenner, SPIDES, Intact, WAAA!, Site Isolation is Dead, Chrome), all within Jun-Oct 2026 apart from Chrome. SPIDES argues restoring SOP is "neither sufficient ... nor necessary", which directly challenges an "agent per origin" thesis (D1): a same-origin public sink can leak, and legitimate tasks need cross-origin flows.
