# Web-specific security directions for browser/web AI agents (excluding per-origin confinement / IFC)
(authored by an agent; nothing published or contacted)

Method. 15 Google Scholar queries via `pb-browser-page-extract` (raw: `raw/dir_1/s1..s15.txt`; queries `scripts/q.sh`), plus arXiv API abstracts. No login wall or CAPTCHA appeared (`login_required: false`, `challenge_action_required: false` in all files). Scholar snippets are fragments; where an abstract is quoted it is from export.arxiv.org. Labels: [F] fact from a quoted source, [I] my inference, [O] opinion.

## Ranking
1. Cheap isolation at agent scale (sharing processes/isolates across origins) -- the human's idea
2. Measuring agent-targeted cloaking in the wild
3. WebMCP exposure measurement (third-party scripts as tool injectors)
4. Agent identity verification: gaps between signed-agent specs and deployment
5. Dropped or crowded: UI deception, robots/llms.txt, fingerprinting/privacy

## 1. Cheap isolation at agent scale
Question: when one agent (or one cloud provider) drives thousands of browser sessions, what is the minimum isolation that still contains "the massive amount of junk" a page can do, and can the boundary be proved?

Prior work.
- [F] Process-per-site is the browser baseline: "Locking each sandboxed renderer process to a single site" ... "no process sharing and having at most one process per site." Reis, Moshchuk, Oskov, "Site isolation: Process separation for web sites within the browser", USENIX Security 2019. https://scholar.google.com/scholar?q=Site+Isolation+process-per-site+memory+overhead+browser+sandbox+scaling+many+tabs
- [F] Its cost is known: "4 GB of RAM we could spawn 31 new tabs before any renderer" (Vila, Köpf, "Loophole", USENIX Sec 2017, same URL).
- [F] Edge platforms already share a process: "Cloudflare Workers run many tenants as V8 isolates in one" process (Abrahams, Kronos); "Cloudflare Workers run V8 isolates in-process" (Abrahams, Li, Khronos). https://scholar.google.com/scholar?q=V8+isolates+multi-tenant+isolation+Cloudflare+Workers+security+process+sharing
- [F] That sharing is attacked: Schwarzl et al., "Remote-Timer-as-a-Service", arXiv 2026: "In a single-process-multi-tenant systems, Spectre [38] particularly … threat of in-process Spectre at Cloudflare Workers is higher … unavailable inside the Cloudflare Workers JavaScript sandbox." (same URL; https://arxiv.org search by title).
- [F] In-process browser sandboxing exists for components: Sharma et al., "Mohabi: Disaggregating and Sandboxing the Firefox JavaScript Engine", USENIX Sec 2026: "a sound, in-process sandbox for JS engines". Narayan et al., Segue & ColorGuard: "overhead of Wasm-sandboxed font rendering in Firefox by 75%". https://scholar.google.com/scholar?q=in-process+isolation+browser+renderer+sandboxing+without+process+boundaries+Wasm+SFI+JavaScript+engine
- [F] Agent angle exists only for tool code, not browsers: "Nano-MCP: V8 Isolates as a Lightweight Alternative to Containers for AI Agent Tool Execution" (Goumih, Dalli, 2026), same V8-isolates URL.

Open [I]: I found no paper that asks which origins a renderer/isolate may safely share, under what trust classes, for browser sessions (as opposed to tool code or fonts). Absence in 3 Scholar queries, not proof.

Why web-specific [I]: the threat surface is the full browser (JS, DOM, GPU, media, extensions), the thing the human distrusts; Workers-style isolates only expose a small API surface.

Why agents [I]: an agent is one principal visiting many origins, driven at high concurrency by hosted-browser vendors; per-tab processes cost memory per session. Weak link: this is "isolation cost", agent-specific only via workload. [O] Honest framing: web-platform isolation research motivated by the agent workload.

First experiment (days): from the group's crawl data, per page load record number of distinct sites/frames, memory per renderer, and which frames are third-party; compute how many renderers a process-per-site policy needs for an agent task trace vs. a policy sharing across a trust class (e.g. same-eTLD+1 or same declared tenant). Then measure Chromium with `--process-per-site` variants vs. isolates. Verus angle [I]: prove a narrow boundary (e.g. isolate heap/handle table, or a capability layer between isolates), not the browser.

Group data helps: yes (page structure, frames, third-party inclusion).
Risk: Spectre-class channels (cited above) may make sharing indefensible; then the result is a measured negative/lower bound on cost.

## 2. Measuring agent-targeted cloaking in the wild
Prior work.
- [F] Attack formalized, not measured: Zychlinski, arXiv 2509.00124: "A malicious website can identify an incoming request as originating from an AI agent and dynamically serve a different, "cloaked" version of its content." https://arxiv.org/abs/2509.00124
- [F] Large static measurement: Khodayari et al., arXiv 2604.27202: "Analyzing 1.2B URLs from 24.8M hosts, we identify 15.3K validated instances across 11.7K pages." and "about 70% appear in non-rendered HTML (e.g., headers, comments, metadata)". https://arxiv.org/abs/2604.27202 (Scholar: https://scholar.google.com/scholar?q=measurement+in+the+wild+hidden+prompt+injection+websites+LLM+agents)
- [F] The gap is stated by those authors: "agent-targeted cloaking would not be captured by Common Crawl and represents a broader data …" (Scholar snippet of the CISPA version, https://scholar.google.com/scholar?q=agent-targeted+cloaking+web+measurement+crawl+sites+serve+different+content+to+AI+user+agents).
- [F] Agents are detectable: FP-Agent: "FP-Agent detects all seven AI browsing agents, whereas Cloudflare detects only one." https://arxiv.org/abs/2605.01247
Open [I]: differential crawling (agent-like vs human-like vs declared-bot clients) to measure whether sites actually serve different content to agents. Searches surfaced no such study.
Why web-specific: it is a measurement of server behavior; needs fingerprint-faithful crawling.
First experiment: 10k-site crawl with 3 clients (stock Chrome; Chrome with agent-framework signatures/CDP flags and an agent-like UA; declared GPTBot-style UA); diff rendered text, hidden text, headers for instruction-like strings. Control for ordinary bot-blocking and geo/AB variance by repeating each client twice.
Group data helps: strongly (crawl infrastructure, baselines). Risk: low base rate; injections could be 0.0x% (Khodayari found 11.7K pages in 1.2B URLs).

## 3. WebMCP exposure measurement
Prior work.
- [F] Mid-session injection: Lee et al., arXiv 2606.06387: "attackers leverage third-party scripts to inject malicious tools during an active session." https://arxiv.org/abs/2606.06387
- [F] Defense: Lee et al., WebMCP-Phalanx, arXiv 2608.24017: "integrating agent execution into a browser security model centered on the Same-Origin Policy (SOP) leaves insufficient provenance and lifecycle guarantees for agent-accessible tools". https://arxiv.org/abs/2608.24017 (Scholar: https://scholar.google.com/scholar?q=WebMCP+security+tools+exposed+by+websites+to+agents)
Open [I]: both are lab implementations; I saw no measurement of how many real sites run third-party script in an origin that could register tools, or any deployment count. WebMCP is young, so deployment may be near zero [I]; the measurable proxy is exposure, not adoption.
First experiment: from existing crawl, count sites where third-party scripts execute in the top-level origin (they could call the registration API) and sites using navigator-level feature detection for WebMCP.
Group data helps: yes for the exposure proxy. Risk: reviewers may call it speculative; overlaps with Phalanx authors' follow-ups.

## 4. Agent identity verification gaps
Prior: [F] "Web Bot Auth checks HTTP request signatures against" keys (Xu, Li, "Proof-of-Agentness", arXiv 2610.35288, https://arxiv.org/abs/2610.35288); AgentShield: "declared AI User-Agents and signed-agent attestations only" (https://scholar.google.com/scholar?q=Web+Bot+Auth+signed+agents+HTTP+message+signatures+AI+agent+authentication); terms.txt: "main systems risk because verification consumes CPU on every" request. Also "Agents in Disguise-Weaknesses in Authentication and Authorization in Public AI Ecosystems" (Stanek, Kencl, ESORICS 2026).
Open [I]: measuring which sites verify signatures and whether verification can be bypassed by an unsigned UA spoof; delegation to sites (OAuth-style) is crowded by protocol papers.
Group data: partial. Rank low: protocol-heavy, closer to crypto/IETF than systems+web measurement. First experiment: send signed vs unsigned vs spoofed-UA requests to sites advertising bot allowlists and compare responses.

## 5. Crowded or weak (not recommended)
- UI deception/clickjacking vs vision agents [F]: "Clickjacking and visual deception attacks target the perceptual …" (Jones et al., arXiv 2025); "Don't Click That: Teaching Web Agents to Resist Deceptive Interfaces" (ACL 2026); TOCTOU "Visual Atomicity Violation" (arXiv 2604.18860). https://scholar.google.com/scholar?q=clickjacking+UI+deception+attacks+on+vision+screenshot+computer-use+agents . Mostly benchmarks/training. Possible niche [I]: browser-side screenshot/DOM atomicity guarantee, but PL/OS flavored.
- robots.txt/llms.txt [F]: SIGCOMM CCR 2026 "From robots.txt to ai.txt: Mapping the Evolution of Web Permissions in the Age of AI", several SSRN measurements, "Permission manifests for web agents". https://scholar.google.com/scholar?q=robots.txt+llms.txt+AI+agents+compliance+measurement+websites . Saturated; fold into #2 as a covariate.
- Fingerprinting/privacy [F]: FP-Agent, "Whose Agent Are You? Multi-Layer Fingerprinting and Attribution of Autonomous Web Agents", "On the Internet, Nobody Knows You're an LLM Bot", "Privacy practices of browser agents". https://scholar.google.com/scholar?q=browser+fingerprinting+detect+AI+agents+bot+detection+agentic+browsers+measurement . Saturated.

## Recommendation [O]
Start with #2 (fastest, uses existing infrastructure, clear gap quoted by the prior authors) as a measurement paper. Pursue #1 as the thesis-scale bet: it matches the human's own thesis (process isolation exists because browser junk cannot be trusted per tab) and Verus fits a narrow boundary. Check first that #1's agent link is not just a cost study; ask whether to frame it as agent infrastructure.
Caveats: Scholar returned snippets, not full texts; claims about "no prior work" are from few queries. Titles such as 2026 arXiv IDs came from search results and were not otherwise verified.
