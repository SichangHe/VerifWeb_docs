# Security of browser-using AI agents, survey as of 2026-11-06
(authored by agents unless marked 🧑)

Method: web search plus page fetches. Quotes marked [fetched] came from the fetched page or abstract (a fetch tool summarizer returned them, so they are not byte-checked against the raw page). Quotes marked [snippet] came only from a search-result summary. "UNCERTAIN" means I did not read the primary source or the claim looks odd. Nothing was posted or contacted.

## 1. Prompt injection via web content

- AgentDojo (Debenedetti et al., NeurIPS 2024): dynamic benchmark of injection attacks and defenses for tool-using agents. https://arxiv.org/abs/2406.13352
  "AI agents are vulnerable to prompt injection attacks where data returned by external tools hijacks the agent to execute malicious tasks." [fetched]
- InjecAgent (Zhan et al. 2024): indirect-injection benchmark for tool-integrated agents. https://arxiv.org/abs/2403.02691
  "InjecAgent comprises 1,054 test cases covering 17 different user tools and 62 attacker tools." [fetched]
- VWA-Adv (inside "Dissecting Adversarial Robustness of Multimodal LM Agents", Wu et al., ICLR 2025): 200 targeted adversarial tasks on VisualWebArena. https://arxiv.org/abs/2406.12814
  "inference-time compute that typically improves benign performance can open up new vulnerabilities and harm robustness" [fetched]. The abstract page does not use the name "VWA-Adv" (name-to-paper mapping UNCERTAIN, though the description matches).
- WASP (Evtimov et al., Meta, 2025): web-agent hijacking benchmark, 84 tasks, GitLab and Reddit sandboxes. https://arxiv.org/abs/2504.18575
  "Even top-tier AI models, including those with advanced reasoning capabilities, can be deceived by simple, low-effort human-written injections" [fetched]
- Brave, Comet disclosure part 1 (Aug 2025): hidden page text makes "summarize this page" act on other logged-in sites. https://brave.com/blog/comet-prompt-injection/ (URL from Brave's later post; I did not fetch it. No verbatim quote retrieved, UNCERTAIN.)
- Brave, "Unseeable prompt injections in screenshots" (Oct 2025): near-invisible text in images steers Comet and Fellou. https://brave.com/blog/unseeable-prompt-injections/
  "indirect prompt injection is not an isolated issue, but a systemic challenge facing the entire category of AI-powered browsers." [fetched]
- OpenAI, "Continuously hardening ChatGPT Atlas against prompt injection" (Dec 2025): RL-trained automated attacker feeds adversarial training. https://openai.com/index/hardening-atlas-against-prompt-injection/ (fetch returned 403; UNCERTAIN on exact wording.)
  "unlikely to ever be fully solved" [snippet, partial quote]
- Anthropic, Claude in Chrome pilot and safety page: red-team numbers and layered mitigations. https://claude.com/resources/articles/claude-for-chrome , https://support.claude.com/en/articles/12902428-use-claude-in-chrome-safely
  "reduce attack success rate from 35.7% to 0%" (challenge set) [snippet]. The reported "<0.08% with Claude Opus 4.8" figure is from a search summary only; UNCERTAIN. It is a vendor-internal number.
- ShadowPrompt (Claude Chrome extension zero-click chain via loose *.claude.ai origin trust, fixed in v1.0.41): https://socradar.io/blog/shadowprompt-zero-click-anthropics-claude/ [snippet only, UNCERTAIN]. Notable because it is an origin-validation bug.

## 2. Defenses with structural guarantees

- CaMeL (Debenedetti, Shumailov, ..., Tramèr, 2025): privileged LLM writes the plan, quarantined LLM reads untrusted data, an interpreter tracks capabilities. 67% of AgentDojo tasks with "provable security". https://arxiv.org/abs/2503.18813
  "the untrusted data retrieved by the LLM can never impact the program flow." [fetched]
- FIDES (Costa et al., Microsoft, 2025): planner with confidentiality and integrity labels, deterministic policy enforcement. Now an experimental feature in Microsoft Agent Framework. https://arxiv.org/abs/2505.23643
  "This paper explores the use of information-flow control (IFC) to provide security guarantees for AI agents." [fetched]
- Progent (Shi et al., Dawn Song group): LLM-written symbolic privilege policies, SMT-checked updates. https://arxiv.org/abs/2504.11703
  "ensuring that the agent's effective action space can only shrink without approval (monotonic confinement)" [fetched]
- Dual-LLM pattern (Simon Willison, 2023): the origin of CaMeL's privileged/quarantined split. I did not search for or fetch the source; cited from memory, UNCERTAIN on URL. Look up simonwillison.net "dual LLM pattern" before citing.
- Chrome "User Alignment Critic" and "Agent Origin Sets" (Chrome security, Dec 2025): second Gemini model vetoes actions using only action metadata; gating function picks readable and read-writable origins. https://blog.google/security/architecting-security-for-agentic/
  "If the action is misaligned, the Alignment Critic will veto it." [fetched]
  "This prevents a compromised agent from acting arbitrarily on unrelated origins." [fetched]
  "Site Isolation and the same-origin policy are fundamental boundaries in Chrome's security model…" [fetched, partial]
  Note: the critic is a model-based check (no proof). Origin Sets are a policy layer on top of Site Isolation, not a change to the process model as far as the post says (inference).
- Same-Origin Policy for Agentic Browsers / SOPGuard (Wang, Chen, Li, Song, Gong, arXiv 2606.14027): propagates origin labels through agent output, blocks cross-origin writes; SOPBench; built in BrowserOS. https://arxiv.org/abs/2606.14027
  "Our evaluation shows that existing agentic browsers frequently violate SOP, both in benign settings and under attacks." [fetched]. Empirical, no proof; abstract does not mention Site Isolation.
- Roesner and Kohlbrenner, "Agentic browsers and the same-origin policy" (ICLR 2026 workshop): argues SOP fails when the agent is a data-flow channel; recommends provenance tracking. https://homes.cs.washington.edu/~franzi/pdf/roesner_kohlbrenner_2026_agentic_sop.pdf [snippet only, no quote, UNCERTAIN on details]
- Untrusted Content Masking (Nikolić, ..., Debenedetti, Tramèr, arXiv 2607.05277): use the DOM to find untrusted regions and mask them before the agent sees them; claims guarantees. https://arxiv.org/abs/2607.05277
  "a webpage's Document Object Model (DOM) encodes sufficient information to distinguish trusted from untrusted regions" [fetched]. Whether guarantees are proofs or empirical: not clear from the abstract, UNCERTAIN.
- APPA (Kravchenko et al., arXiv 2607.24625): recoverable IFC; claims proofs of label non-laundering, branch isolation, contained recovery. https://arxiv.org/abs/2607.24625
  APPA "turns agent IFC from an abort-only barrier into a policy-governed recovery system." [fetched]. Evaluated on OWASP AgentThreatBench, not browsers.
- Others seen only as titles (not read): Web Agents Should Adopt the Plan-Then-Execute Paradigm (2605.14290), Aligning Provenance with Authorization (2605.26497), LACUNA (2605.28617), Agent-as-a-Proxy attacks on monitors (2602.05066), IsolateGPT (2404.17095), WebSentinel (2602.03792), Ward (2605.15030). UNCERTAIN.
  The Agent-as-a-Proxy paper matters: it reportedly attacks monitor/critic designs like the User Alignment Critic.

## 3. Sandboxes and isolation

- ceLLMate (Meng, Feng, Shumailov, Fernandes, arXiv 2512.12594): browser extension that sandboxes the agent at the HTTP layer with deterministic policies; blocks WASP attacks at 7.25 to 15% latency overhead. https://arxiv.org/abs/2512.12594
  "a browser-level sandboxing framework that restricts the agent's ambient authority" [fetched]. A search summary says it contrasts itself with Chrome's Agent Origin Sets as coarse (read-only vs read-write).
- Cloudflare Kitesurf (Aug 2026), agent-first browser in V8 isolates on Workers; part of Browser Run (formerly Browser Rendering). https://blog.cloudflare.com/kitesurf/
  "we built this browser on the assumption that every page load is untrusted input and every session starts fresh." [fetched]
  Each page or out-of-process iframe gets its own isolate; one outbound component fetches. This reimplements the process model rather than reusing Chrome Site Isolation.
- Cloudflare Agents browser-agent example: LLM code in isolated Worker sandboxes with outbound network blocked. https://developers.cloudflare.com/agents/examples/browser-agent/ [snippet only, no quote]
- Browserbase containment post (Feb 2026): per-session hardware-virtualized VM, zero-trust framing. https://www.browserbase.com/blog/ai-browser-prompt-injection-containment-security
  "Each browser session runs in a dedicated VM through hardware virtualization isolation." [fetched]
  Isolation here protects the host and other tenants. It does not stop an injected agent from misusing the session's own credentials.
- WebMCP (W3C Web Machine Learning CG draft; Chrome origin trial from 149; getter moved from navigator.modelContext to document.modelContext, per search summaries, UNCERTAIN on versions). https://webmachinelearning.github.io/webmcp/
  "gated behind the policy-controlled feature "tools", which has a default allowlist of 'self'." [fetched]
  "This API is designed for so-called "in-page" agents written in JavaScript, and possibly living in iframes." [fetched]
  Spec TOC has sections on prompt injection, tool poisoning, "Enforcing Same-Origin Isolation via Two-Sided Opt-In", and Permissions Policy. I could not read their bodies (page truncated).
- Fernandes blog on WebMCP and same-origin (earlence.com/blog.html#/post/webmcp-sameorigin): cited by 2606.14027; I could not fetch it. UNCERTAIN on content.
- Chromium Site Isolation applied to agents: I found no paper that uses the process model for agent confinement. Chrome's post mentions it only as the boundary Origin Sets protect.

## 4. Permission and capability systems

- Chrome agent origin sets plus user confirmation gates (banking, medical, passwords, purchases): same Chrome post as above.
- Claude in Chrome site-level permissions, action confirmations, high-risk site blocklist, two classifiers: support page above. [snippet]
- Progent (policy language over tool names and arguments) and CaMeL capabilities: see section 2.
- ceLLMate HTTP-request policies (per-request, per-parameter): see section 3.
- WebMCP Permissions Policy "tools", plus tool annotations for untrusted output and consequential actions: spec above. Quote: "indicates that the tool's output contains data that is untrusted, from the perspective of the author registering the tool." [fetched]
- Other access-control papers seen as titles only: Mandatory Access Control framework for agents (2601.11893), AgentGuardian (2601.10440), Lingering Authority revocable capabilities for coding agents (2606.22504). UNCERTAIN.
- MCP authorization and OAuth scoping: not searched. Gap in this survey.

## 5. Benchmarks (beyond section 1)

- AgentDojo, InjecAgent, WASP, VWA-Adv: section 1.
- Agent Security Bench (ASB): https://arxiv.org/abs/2410.02644 (ID from search, not read).
- VPI-Bench: visual injection, 306 cases. https://arxiv.org/abs/2506.02456 [snippet]
- BrowseSafe and BrowseSafe++: injection detection in realistic HTML and screenshots. https://arxiv.org/abs/2511.20597 ; BrowseSafe++ ID given as "2610.17457" by one search summary, UNCERTAIN.
- TRAP (persuasion attacks): https://arxiv.org/abs/2512.23128 ; StakeBench: https://arxiv.org/abs/2606.13385 ; SOPBench: in 2606.14027 ; MUZZLE 2602.09222 ; WAInjectBench 2510.01354 ; RedTeamCUA ; Domain-Conditioned Safety 2606.05233. All from snippets, not read.
- ceLLMate's critique: static attack sets fail to stress defenses as models get more aligned. Adaptive attackers (OpenAI RL attacker, MUZZLE) are the trend.

## Crowded vs open

Crowded (many papers, many vendors):
- Injection benchmarks and detectors/classifiers (AgentDojo, WASP, BrowseSafe, VPI-Bench, TRAP, StakeBench, SnapGuard).
- Model-based defenses: adversarial training, classifiers, critics. Every browser vendor ships these.
- Tool-level IFC and policy for generic agents (CaMeL, FIDES, Progent, APPA and many follow-ups). Browser-specific use is thinner.
- Container/VM/isolate sandboxes for hosting (Browserbase, Cloudflare). These isolate the host, not the user's authority.

Moving fast but young (browser-native, a few groups):
- Origin-based confinement of the agent: Chrome Agent Origin Sets, SOPGuard, ceLLMate, Roesner/Kohlbrenner. Several groups converged within about 8 months. A tight area, but each piece is a policy or label layer.

Open (my reading; "open" means I found none in these searches, not that none exist):
- Using Chromium's real isolation machinery for agents: Site Isolation process boundaries, out-of-process iframes, CSP/COOP/COEP/Origin-Agent-Cluster, Permissions Policy, as enforcement for an agent's reads and writes. Current work stays at the label or extension layer. Chrome's post cites Site Isolation but describes a gating function, not a process-level mechanism.
- Agent context as an isolation domain: what an LLM's context window means across site-isolated processes. SOP papers show the agent breaks SOP by being a cross-origin channel; no one has a browser-enforced fix (inference).
- Formal guarantees in the browser setting: CaMeL, FIDES and APPA prove things in tool-call models. SOPGuard and UCM are empirical. A noninterference-style statement for a DOM/origin model of the page-agent system looks absent.
- Third-party-content problems inside one origin (ads, user-generated content in iframes, same-origin untrusted regions): UCM touches it via DOM masking; CSP/iframe sandbox/Permissions Policy as a trust-labeling primitive for agents is unexplored in what I found.
- WebMCP security: the spec lists threats; I found little independent analysis (one blog, one citation). Tool poisoning and third-party script hijacking appear open.
- Critic soundness: Agent-as-a-Proxy suggests monitors can be bypassed; no structural alternative for the critic's role in browsers.
