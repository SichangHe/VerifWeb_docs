# Security for AI agents that use browsers: directions
(authored by agents unless marked 🧑)

🧑 "I was thinking that maybe we should do something about security with the agents using the browsers. Although that is also somewhat crowded."

Sources and full quotes: `survey.md` (a subagent's web survey; items it marked UNCERTAIN are not used here). Quotes below came through a summarizing fetch tool, so check them against the pages before citing.

## The map
- Crowded (fact: many papers/products): prompt-injection benchmarks (AgentDojo, WASP, InjecAgent, BrowseSafe, ...), model-based defenses (classifiers, adversarial training, critic models), generic tool-call policy/IFC systems (CaMeL, FIDES, Progent), hosted sandboxes (Browserbase, Cloudflare).
- Converging fast: "same-origin policy for the agent". Chrome Agent Origin Sets ("This prevents a compromised agent from acting arbitrarily on unrelated origins", https://blog.google/security/architecting-security-for-agentic/), SOPGuard ("existing agentic browsers frequently violate SOP", https://arxiv.org/abs/2606.14027), ceLLMate ("restricts the agent's ambient authority", https://arxiv.org/abs/2512.12594). All are label or policy layers, not the browser's own enforcement.
- Open as far as the survey found (inference: absence in searches, not proof of absence):
  - using the browser's real isolation machinery (Site Isolation processes, out-of-process iframes, CSP, Permissions Policy) to enforce what an agent reads and writes
  - a formal guarantee stated over a browser/origin model; CaMeL/FIDES prove things over tool-call models, SOPGuard is empirical
  - WebMCP (sites exposing tools to agents) security; the draft spec lists threats, little independent analysis

Core insight (opinion): the agent's context window is a new cross-origin channel. Browsers spent 15 years building Site Isolation to stop exactly this kind of leak between origins, and every agent then merges all origins into one model context. Today's fixes re-invent origin labels in software above the browser.

## D1. The agent as a site-isolated principal
- Thesis: split the agent per origin (or origin set) like the renderer: one agent context per site, inside that site's process; cross-site data moves only through an explicit, small, checked channel.
- Why web-specific: reuses Chromium's process model and origin rules as the enforcement, not an LLM or a label layer.
- New: survey found no work using Site Isolation processes to confine agents; Chrome's post cites Site Isolation only as the boundary its origin sets protect.
- First step: in Chromium or a headless harness, run WASP/AgentDojo-browser tasks with per-origin agent instances plus a typed cross-origin message, and measure attacks blocked vs tasks lost.
- Risk: many useful tasks are inherently cross-site (copy flight info into calendar); the channel may become the whole problem again.

## D2. A proved-noninterference agent monitor over an origin model
- Thesis: a small monitor (Verus/Rust) between agent and browser, proved: data labeled origin A never reaches a write to origin B unless the user declassifies.
- Why special: ties to the group's Verus work; first guarantee stated over origins, frames, and requests rather than abstract tool calls.
- New: CaMeL/FIDES/APPA prove things in tool-call models; SOPGuard and ceLLMate are empirical.
- First step: write the origin/request model and a tiny proved monitor; plug into ceLLMate-style HTTP interception; replay WASP.
- Risk: the proof is only as good as the model; the hard part (what counts as a "flow" through an LLM) is assumed, not proved, so it may look like CaMeL with a browser coat.

## D3. Shared-process isolation for agent browsers (🧑's process-sharing idea)
- 🧑 "we have been using process isolation across browser tabs because we have no confidence that the massive amount of junk that browsers can do would stay in each tab. I think maybe that would be interesting for Cloudflare workers or something like that to share processes."
- Thesis: agents load huge numbers of short, untrusted pages; one process per site is too expensive at that scale. Make many sites share one process (V8 isolates) safely by verifying the small part that must hold: the boundary.
- Evidence it is live: Cloudflare Kitesurf runs an agent browser in Workers isolates, "every page load is untrusted input" (https://blog.cloudflare.com/kitesurf/); per survey, it reimplements the process model instead of reusing Site Isolation.
- First step: measure cost of per-site processes vs shared isolates for an agent crawling workload; list which browser features escape an isolate.
- Risk: verifying a real isolate boundary (V8, Spectre) is very large; may shrink to measurement. Overlaps sibling task vlm9_shareproc.

## Recommendation (opinion)
D1 is the most web-specific and least crowded; D2 is the natural formal add-on to D1, not a separate thesis. A story: "agents break Site Isolation; restore it, with a proved channel". Biggest shared risk: Chrome may ship a process-level version first; the origin-confinement area has converged within about 8 months.

## Independent check (GPT, `gpt.md`)
- GPT, given only the human's quote and the rejected stories, independently picked the same core as D1: "restore browser security principals across the agent path", and recommended it first.
- Two extra ideas worth keeping as D1 add-ons:
  - agent CSP: the web's "origin principal is too coarse for agents" (ads, user content inside one origin); sites declare which regions an agent may trust
  - Site Isolation for screenshots: vision agents get one flattened screenshot of all frames; keep per-frame origin provenance through the compositor
