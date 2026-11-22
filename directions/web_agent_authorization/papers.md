# ceLLMate and Atomicity for Agents: two browser-agent defenses

(authored by agents unless marked 🧑)

Quotes are verbatim from pdftotext of the PDFs (ligature-split words like "CE LLM ATE" rejoined as CELLMATE). `[I]` = my own observation. Section refs: ceLLMate = arXiv v2 section numbers; Atomicity = section and ACL page (pp. 14277-14291).
Local copies: see the two directories under /hdd1/sichanghe/paper_collection (names start with "ceLLMate-" and "Atomicity for Agents-").

Takeaway: the two papers defend different failures. ceLLMate limits what an agent may do (authorization at the HTTP layer; prompt injection). Atomicity limits acting on stale state (observation-to-action race; no attacker prompt needed). Neither proves anything; both are empirical.

## 1. ceLLMate: Sandboxing Browser AI Agents

- authors: Luoxi Meng, Henry Feng, Ilia Shumailov, Earlence Fernandes (UC San Diego; AI Sequrity Company)
- venue: arXiv:2512.12594v2 [cs.CR], 4 Mar 2026 (no peer-reviewed venue stated)
- url: https://arxiv.org/abs/2512.12594

### problem
- prompt injection in browser-using agents (BUAs) that hold the user's logged-in session
  - "Operating with full access to authenticated browser sessions, BUAs combine ambient privilege with untrusted input, a lethal trifecta [63]" (§2)
- semantic gap: agent tools (click, type) carry no meaning, so tool-level policy is brittle
  - "Because a browser state can be reached through many different action sequences, it is infeasible to exhaustively enumerate and block all of them." (§3.2)
  - "Expressing the policy and enforcing it do not occur at the same level of abstraction." (§1)

### threat model (§3.1)
- attacker: prompt injection via untrusted content on trusted domains, or on domains the agent is lured to
  - "attackers may control untrusted portions of otherwise trusted domains (i.e., they do not control amazon.com or github.com, but may control the title and description of a GitHub issue or product reviews on Amazon)."
  - goal: "exploit the ambient privilege of BUAs and violate the confidentiality and integrity of user data."
- trusted: browser runtime, web developers' sitemaps and policies, policy generator, the user prompt
  - "We assume a standard, trusted browser runtime." / "we must assume that no other malicious extensions are present that intercept/block HTTP requests."
  - "We trust pre-defined policies and functions supplied by trusted sources" (§4.3)
  - "BUAs are confined to actions within the webpage context ... and cannot alter browser settings, access local files, or use developer tools."
- non-goal: data/control-flow integrity
  - "if an agent reads untrusted data from a webpage and later makes an HTTP request, CELLMATE does not track whether that request was causally influenced by the untrusted data — it only enforces whether the request itself is permitted by policy."

### method: where and what is enforced
- layer: browser, at HTTP requests; implemented as a Chrome extension; agent-agnostic
  - "CELLMATE interposes on HTTP requests at the browser level and then evaluates a policy on the HTTP request and its parameters." (§1)
  - "Our key insight is that browser actions ultimately manifest as HTTP requests" (§3.3.1)
- not formal; no policy calculus. Three phases (§3.3): registration, policy instantiation, enforcement
  - "Registration: (a) Web developers provide an agent sitemap that maps HTTP messages to high-level semantic actions; and (b) trusted sources ... provide a policy generator"
- agent sitemap: (method, URL pattern, body) -> semantic action name, plus optional `args` read from the request or the DOM
  - "an agent sitemap outlines all security-relevant actions within a web domain." (§3.3.2)
- policy: named, effect allow/deny/condition, over semantic actions; condition = preloaded JS function
  - "Each policy includes (1) a unique name, (2) an effect set to "allow", "deny", or "condition", (3) an actions list ..., and (4) a natural-language description." (§4.1)
  - policies must form a partial order by allowed actions: "otherwise, "least privilege" is undefined."
- enforcement: default-deny lookup table, plus content-script DOM reads for arguments, counters for stateful policies
  - "CELLMATE intercepts every HTTP message from a browser session, and allows or denies each request given the policy." (§4.3)
  - "Stateful Policies ... 'agent may check out a shopping cart under $50 only once'."
  - "Once the user approves instantiated policies, the permission level freezes until the user explicitly updates it."

### "intent" and "authorization" here
- intent = the user's natural-language task, treated as trusted configuration, mapped by an LLM to a policy set
  - "CELLMATE treats the user prompt as trusted configuration input, that is subject to explicit user confirmation, rather than as a perfect security oracle." (§3.3.3)
  - "Policy selection and instantiation operate only on trusted context — user prompts and predefined policies — and are therefore not influenced by prompt injection" (§4.2)
  - under-specified intent -> deny: "We reject under-specified prompts and grant no permissions by default."
- authorization = least-privilege set of semantic actions (plus parameters like maxAmount) for this task and session
  - "identifies the least-privileged subset of policies required to complete the task." (§4.2)
  - the policy layer is "one single point in the broader design space"; the enforcement layer is "independent of policy architecture"

### guarantees
- empirical plus informal argument; no proof, no mechanization
  - "ensuring safety even in worst-case execution scenarios, analogous to process-level sandboxing in operating systems." (§3.3)
  - "We experimentally confirmed that all the 12 attacks were blocked by the CELLMATE enforcement layer." (§5.2)
- explicit scope limit
  - "CELLMATE, like other permission-based systems, cannot prevent misuse of actions that are intentionally permitted by policy." (§5.2)
- failure mode: "If not, security gracefully degrades to the status quo" (§4.3)

### evaluation
- policy selection benchmark built from WebBench: retail 149, travel 36, version control 24 tasks; labels by two researchers (§5.1.1)
  - "all three models achieve an accuracy above 94% across all three task categories" (§5.1.3)
  - retail policy selection: gpt-5.1 96.64%, gemini-2.5-pro 97.32%, claude-opus-4-5 99.32%; with argument extraction on retail: 84.38%, 81.25%, 96.88% (Table 2)
  - domain prediction: 132 zero-, 205 one-, 410 multi-domain tasks; zero-domain failures when the model "infer[s] domains from prompt keywords" (Table 1, §5.1.2)
- attack case study: WASP GitLab, 2 user tasks, 12 scripted attacker goals
  - "we emulate a strong attacker who has fully compromised the agent." (§5.2)
  - "The accuracy in both steps was 100%." (domain + policy selection on these 2 tasks)
- overhead: Playwright, 11 navigations on GitLab, 30 trials
  - "baseline end-to-end latency (without CELLMATE) is 13.93 seconds ... 14.94 seconds (7.25% overhead) with 100 sitemap entries, 15.35 seconds (10.10%) with 200 entries, and 16.02 seconds (15.0%) with 300 entries." Memory "about 25MB". (§5.3)
- GitLab sitemap: "51 GitLab project APIs", built manually (§4.1)

### stated limitations
- "Our experimental sitemap is created manually" (§4.1); automated generation is future work (§7)
- WebSockets not covered: "designing a general interception approach for WebSocket traffic is challenging, and we leave it as future work." (§7)
- "CELLMATE currently focuses on single-turn tasks." (§3.1)
- extension assumption: "its enforcement guarantees rely on the assumption that no other privileged browser components or extensions concurrently influence network requests" (§4.3)
- weak benchmark: "evaluating empirical end-to-end ASR and utility across a wide range of websites and tasks is infeasible with existing benchmarks." (§5.2)
- freshness race: "Enforcing this property in general requires cooperation from web applications" (§4.3)
- policy selection errors: object confusion, over-permissiveness, over-restrictiveness (§5.1.3)

### [I] gaps
- [I] the 12 attacks are scripts that call actions the policy denies, so "all blocked" follows from default-deny by construction; it does not test the hard parts (sitemap coverage, wrong policy chosen, allowed-action abuse)
  - the paper concedes this: "focuses on attacker goals that require actions explicitly disallowed by the active policy"
- [I] no utility measure: no end-to-end agent success under enforcement, no false-block rate; only policy-selection accuracy (3-6% of tasks wrong on some models, up to ~19% with arguments on retail for two models)
- [I] correctness rests on sitemap completeness and URL-pattern matching; a missing or over-broad entry silently allows. No check that the sitemap matches the real server routes
  - the paper's answer: "CELLMATE falls back to the status quo when an agent sitemap is incomplete or incorrect" (§4.1). That is a fallback of protection, not a guarantee
- [I] "intent" is never formalized; the LLM-chosen policy set plus a consent dialog is the only link from task to authority. Consent fatigue is not evaluated
- [I] allowed channels can still leak: GET to an allowlisted or permitted domain can carry data in URL/body; policy args cover only declared parameters. Data-flow is explicitly out of scope
- [I] argument values come from DOM reads (cart total) cached until use, so the policy decides on a DOM-derived value, not necessarily the value the server will charge. Trust in the page DOM for the decision is not discussed
- [I] the claim that it "blocks all attacks that manipulate UIs (e.g., TOCTOU attacks)" (§4.3) holds only when the manipulation changes the request class. A TOCTOU that redirects a click to a different, still-allowed action passes (cf. Type I in paper 2)
- [I] needs web-developer adoption (sitemaps, policies); no deployment story beyond analogy to CSP/robots.txt

## 2. Atomicity for Agents: Exposing, Exploiting, and Mitigating TOCTOU Vulnerabilities in Browser-Use Agents

- authors: Linxi Jiang*, Zhijie Liu*, Haotian Luo* (equal contribution), Zhiqiang Lin (The Ohio State University)
- venue: Findings of the Association for Computational Linguistics: EMNLP 2026, pp. 14277-14291, October 24-29, 2026
- url: https://aclanthology.org/2026.findings-emnlp.680/ (code: https://github.com/OSUSecLab/TOCTOU-WebAgent)

### problem
- the page changes between the agent's observation and its action; the action was planned on stale state
  - "web pages can change between observation and action execution due to advertisements, asynchronous loading, and timed updates, causing agents to act on stale assumptions." (Abstract, p.14277)
  - root cause: "the lack of atomicity between observation and action execution ... provide no atomic check-and-use primitive" (§3.2, p.14279)

### threat model (§3.3, p.14279-14280)
- adversary controls page content, scripts, and update timing; cannot touch trusted components
  - "The user goal, agent model and implementation, browser action executor, and any enabled monitor and validator are trusted. The adversary controls page content and scripts, including the content and timing of page updates"
  - "We assume that the monitor and validator remain intact, excluding browser compromise and direct instrumentation tampering."
- exclusions: "We exclude prompt injection, deceptive content already present at observation, semantic planning errors, and page changes outside the TOCTOU window."
- success: a change "alters the binding, value, or validity of the planned action and produces an outcome inconsistent with the user goal."

### method
- formal definition (§3.1), semi-formal: window [t_c, t_u); signature sigma(a,s) = (Bind, Val, Valid)
  - "A TOCTOU violation occurs when sc != su and sigma(a, sc) != sigma(a, su), and executing a in su produces an outcome inconsistent with the user goal g." (§3.1; symbols rendered as in text)
  - types: I UI/target change, II data/value change, III expiring state (§3.4)
- DynWeb benchmark: 14 cases (9 synthesized, 5 real: eBay, Amazon, Yahoo Finance, CoinMarketCap, Google Sheets); per-case oracle (§4)
- mitigation, in the agent/automation layer with in-page observers: pre-execution validation (§5)
  - "During planning, the mechanism monitors DOM mutations and element-size changes using browser-native observer APIs. Immediately before action dispatch, a synchronous check determines whether any monitored change has been recorded since observation. If a change is detected, the action is aborted and the agent re-observes the page." (§1)
  - MutationObserver (nodes, text, id/class/href/disabled/hidden/aria) + ResizeObserver (Algorithm 1)
  - hook per framework: "In openai-cua-sample-app, validation wraps the coordinate executor. In Browser-Use, it wraps the shared Tools.act path. In Agent-E, it wraps the element-click skill" (§5.3)
  - no model access: "Because validation operates on browser state, it requires no access to model internals."

### "intent" and "authorization" here
- intent = user goal g, a per-case natural-language instruction with a fixed oracle (e.g. "Buy if price <= $600", Table 1); the agent's plan is assumed to match it at observation time
  - "semantic planning errors" are out of scope (§3.3)
- authorization: not a concept in the paper. There is no policy or permission check; the defense only tests "has the page changed since I looked?"

### guarantees
- empirical only; explicitly not atomic
  - "pre-execution validation reduces TOCTOU exposure but does not provide atomicity." (§8, p.14285)
  - "The final validation step narrows but does not eliminate the TOCTOU window because validation and action dispatch remain separate operations." (§5.3)
- no proof, no mechanization

### evaluation
- 10 open-source agents + Codex computer-use; each synthesized case run 10 times; "vulnerable" = any run violates (§6.1)
  - "All 10 open-source agents exhibit at least one TOCTOU violation" (§6.2); Codex "violations on 0/5 Type I cases, 7/7 Type II cases, and 2/2 Type III cases, for 9/14 overall."
  - coordinate-based agents vulnerable to all types; element-level agents avoid Type I, still hit by II and III
- defense: vulnerable cases 14/14 -> 0/14 (openai-cua-sample-app, screenshot/coordinate); 9/14 -> 0/14 for Browser-Use and Agent-E (Table 4). Prompt-only warning baseline: still 14/14 (Fig. 4)
- window: "reduces the exploitable TOCTOU window from approximately 10 s of planning time to 0.13 s, a roughly 77x reduction." (§1)
- overhead: "below 0.05 s per action cycle"; re-planning: "average numbers of abort-and-replan cycles per execution are 2.4 and 1.0" for Browser-Use and Agent-E (§6.4)
- adaptive attacks, 1,000 trials each, simulated planning delay U[5,10] s, 0.13 s validation-to-dispatch delay (§6.3, Table 5)
  - stealthy fixed 1.50%, random 2.20%, probe-then-strike 1.60%; high-frequency 0/1,000; "Event-driven timing ... triggers in 51.1% of trials."

### stated limitations (Limitations, p.14286; Discussion §7)
- "approximately 0.13 s remains between the final validation check and action dispatch."
- "The evaluation does not cover authenticated services or complex multi-page workflows"
- "The current monitor also does not directly capture position-only changes that leave both the DOM and observed element sizes unchanged."
- "The validator conservatively treats every monitored DOM mutation or element-size change as a reason to re-observe" -> unnecessary aborts; benign-site cost not measured
- "Faster inference narrows the TOCTOU window but does not eliminate it"; waiting for settle "shifts the window rather than removing it"
- needs browser support: "A scoped freeze primitive or transactional interaction API could instead bind the two operations within the browser." (§7)

### [I] gaps
- [I] threat model is thin: the adversary runs page scripts, yet the monitor is also page-side JS (observers in the page). "excluding ... direct instrumentation tampering" assumes away the obvious attack (page code that mutates then restores, or races observer callbacks). No analysis of in-page vs extension/CDP isolation
- [I] headline 0/14 is on author-designed cases with deterministic schedules; metric is "any of 10 runs", so it does not say how often violations happen, and 0/14 does not extrapolate to real sites
- [I] the 77x figure compares planning time (~10 s) to 0.13 s; it is a window length, not a success probability. The event-driven attack (51.1%) shows the window is exploitable by a motivated attacker; real LLM latency was simulated in the adaptive test
- [I] the defense detects change, not harm. Any DOM mutation aborts; no notion of which change matters to the action (no link to what the user authorized). High-churn pages could livelock; no max-retry or utility numbers
- [I] Type III (OTP, CAPTCHA) is a liveness failure (retry loops), not a safety violation; grouping it with safety TOCTOU inflates "vulnerable" counts
- [I] relation to paper 1: ceLLMate's `args` read from the DOM and cached "until they are consumed" (§4.3) have the same check/use gap that this paper studies. Mirror image: paper 1 constrains which actions are allowed, not whether the target is still the observed one; paper 2 does the reverse. Combining them would cover Type I redirection to an allowed-but-wrong action only if validation sits at the same dispatch point. This is my inference, not tested by either paper
