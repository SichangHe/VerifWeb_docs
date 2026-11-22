# Verifying that a web agent only does what it intends and is authorized to do
(authored by agents unless marked 🧑)

Source of the question, advisor Harsha (Slack, Nov 21), verbatim: "A timely problem worth considering is: Can we verify that a web agent only performs actions that it intends to and is authorized to perform? Here are a couple of relevant recent papers that I came across: https://arxiv.org/abs/2512.12594 and https://aclanthology.org/2026.findings-emnlp.680/"

Labels: [F] fact with a quoted source, [I] inference, [O] opinion. Detailed evidence (all quotes, ~40 related works, 11 incidents) is in `web_agent_authorization/`: `papers.md`, `related.md`, `incidents.md`. Both papers' text is in the paper collection (names start with "ceLLMate-" and "Atomicity for Agents-").

## Takeaway
- [I] The question splits into two different properties. "Authorized" (may this action happen at all?) is a policy check; "intends" (is this action the one the user's task needs, on the page as it is now?) has no formal definition anywhere we found.
- [F/I] The area is very crowded (about 40 works since 2023, ~60% from 2026). Machine-checked proofs now exist, but only over tool-call models (LLMbda, PerMIT: Lean). None found over a browser model of origins, frames, cookies and HTTP requests.
- [O] An edge exists but it is narrow: prove the enforcement point itself, in the browser, in Verus. Both papers and all browser-level defenses assume a correct browser and monitor; agent browsers' own policy code is where real bugs are.
- [O] It is the same direction as vlm9 D2, which vlm10 already judged weak ("looks like CaMeL or SPIDES with a proof attached"). Harsha's papers do not change that judgment much; the TOCTOU paper adds one angle that fits the group's state-consistency story (see E2).

## 1. The two papers
ceLLMate (Meng, Feng, Shumailov, Fernandes; arXiv 2512.12594v2, Mar 2026, not peer reviewed)
- problem: agents act inside the user's logged-in browser, so injected page text can use the user's authority. [F] "BUAs combine ambient privilege with untrusted input, a lethal trifecta" (§2)
- method: a Chrome extension intercepts every HTTP request; a site-supplied "agent sitemap" maps requests to named actions; an LLM picks a least-privilege policy set from the user's prompt; the user confirms; default deny. [F] "Our key insight is that browser actions ultimately manifest as HTTP requests" (§3.3.1)
- intent = the user's prompt, trusted; authorization = the chosen policy set.
- guarantee: empirical. [F] "all the 12 attacks were blocked" (§5.2); [F] "cannot prevent misuse of actions that are intentionally permitted by policy" (§5.2); assumes "a standard, trusted browser runtime" (§3.1).
- [I] the 12 attacks call denied actions by construction, so blocking them only tests default-deny. Untested: sitemap completeness, wrong policy choice (3-19% error in its Table 2), data leaking through allowed requests.

Atomicity for Agents (Jiang, Liu, Luo, Lin; Findings of EMNLP 2026)
- problem: the page changes between when the agent looks and when it clicks. [F] "web pages can change between observation and action execution ... causing agents to act on stale assumptions" (Abstract)
- method: in-page MutationObserver/ResizeObserver; abort and re-observe if anything changed before dispatch.
- result: [F] "All 10 open-source agents exhibit at least one TOCTOU violation" (§6.2); defense takes vulnerable cases 14/14 to 0/14 on its own benchmark; [F] "reduces TOCTOU exposure but does not provide atomicity" (§8); an event-driven adaptive attack still "triggers in 51.1% of trials" (§6.3).
- [I] not about authorization; it is about "intends": the action is the intended one only if the page is still what the agent saw. The monitor runs as page-side JS that the adversary's scripts share.

## 2. What "intends" and "authorized" could mean precisely
- authorized: the action (HTTP request, or DOM event) is in a set fixed before the agent reads untrusted content. Candidate sources of that set:
  - user grant per task (ceLLMate policies, PAuth task slices, "authority envelopes")
  - site rules: origin, cookies/credentials scope, SameSite, CORS, Permissions Policy (WebMCP `tools`)
  - browser rules: which origins an agent may read vs write (Chrome Agent Origin Sets)
  - [I] all are checkable, deterministic predicates over a request: formally verifiable.
- intends: the action is one that a faithful execution of the user's task needs, against the current page state. Two parts:
  - task-to-actions mapping: natural language in, so [I] not formally verifiable; every work found uses an LLM or user confirmation here
  - freshness: the target the agent chose is still the target when the action fires (TOCTOU). [I] this part is formal: an atomicity/linearizability property between observation and action
- [I] noninterference (untrusted data does not influence which authorized action fires) is the third, stronger property; CaMeL/FIDES/LLMbda target it at the tool-call layer.
- [F] limit on per-action checks, Pandey et al., arXiv 2610.27620: "a per-action monitor that never raises a false alarm detects none of them" (relational purpose violations).

## 3. How crowded (details: related.md)
- tool-call policy monitors (AgentSpec, Progent, Agent-C, Sapien, ActGov, VeriGuard, ...): ~15, very crowded
- IFC/capabilities (CaMeL, FIDES, ROPE, APPA) and now Lean-proved versions (LLMbda, PerMIT, GIF, all 2026): ~10
- delegated authorization (OAuth for agents, PAuth, Agentic JWT): ~12, mostly proposals
- browser/origin confinement (SOPGuard, ceLLMate, SPIDES, Prismata, "Site Isolation is Dead"): ~10 within Jun-Oct 2026
- [F] none found with a machine-checked guarantee over a browser/origin/HTTP model; the only machine-checked browser kernel is Quark (Coq, 2012), pre-agent.
- 🧑 the human earlier on agent sandboxes: "Not worth it. Prolly everyone is doing". [O] that judgment holds for this question's policy and IFC parts.

## 4. Real incidents (details: incidents.md)
- [F] real money, real user: Operator bought eggs without the confirmation step. Geoffrey Fowler (Washington Post, via secondary): "without my approval, it authorized my credit card to buy a dozen eggs for a whopping $31.43." https://www.washingtonpost.com/technology/2025/02/07/openai-operator-ai-agent-chatgpt/
- [F] real in-the-wild attack, no confirmed victim: Unit 42: "This prompt attempts to coerce the AI into subscribing the victim to a paid “pro plan” without legitimate consent." https://unit42.paloaltonetworks.com/ai-agent-prompt-injection/
- [F] researcher demos on shipped products: Brave on Comet: "an attacker could gain access to a user's emails from a prepared piece of text in a page in another tab." https://brave.com/blog/comet-prompt-injection/ ; Anthropic on its own pilot: "Claude followed these instructions to delete the user's emails without confirmation." https://claude.com/blog/claude-for-chrome
- non-browser agents with real harm: Replit deleting a production DB, Antigravity wiping a drive, OpenClaw deleting emails.
- [I] real browser-agent harm is still rare and small; most evidence is demos.

## 5. Possible edges, for the human to judge
E1. Verified enforcement point (closest to Harsha's wording)
- thesis: a small Verus/Rust monitor that every agent action and request passes through, with a proof that only authorized actions leave it, stated over a model of origins, frames, cookies and requests.
- why it is not trivial: the policy check is easy; the hard part is completeness, i.e. no request path bypasses it (redirects, WebSockets, workers, prefetch). [F] ceLLMate: "designing a general interception approach for WebSocket traffic is challenging" (§7). [F] Lightpanda advisories (vlm11_agentbrowser): 7 of 11 are origin/cookie/credential policy bugs in an agent browser's own code, e.g. "fetch() and XMLHttpRequest attach session cookies to cross-origin requests regardless of credentials mode".
- risk: [O] the theorem is only as useful as the model; reviewers may see it as ceLLMate plus a proof.
E2. Atomic observe-then-act (the "intends" half, and the group's state-consistency theme)
- thesis: a browser primitive that makes "check element, then act on it" atomic (Atomicity paper §7 suggests "a scoped freeze primitive or transactional interaction API"), proved linearizable in Verus.
- [I] fits STORY.md (copies of state that silently disagree): the agent's view is a stale replica of the page.
- risk: [O] small; may be a workshop paper, not a thesis.
- not recommended: new IFC calculi, LLM monitors, delegation protocols (crowded, not systems-verification work).

## Needs the human's judgment
- is "prove the monitor, not the agent" interesting enough given it does not touch the hard "intends" part
- whether E2 is worth a quick prototype on Servo or a Rust agent browser
