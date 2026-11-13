# Other PhD directions adjacent to web + systems (beyond shared-process tabs/tenants)

(authored by agents unless marked 🧑)

Labels: [F] fact quoted from a source, [I] inference, [O] opinion.
Method: Google Scholar via the human's browser (as_ylo=2024), plus arXiv abstract pages. Raw files: /hdd1/sichangheagent/vl_meeting_work/out/vlm10_share/other/ (s1..s13.txt = Scholar pages, abs/ = arXiv abstracts).
Limits: no CAPTCHA or login appeared. I did NOT open individual "Cited by" pages or read full PDFs; crowdedness uses the "Cited by" counts shown in Scholar snippets and abstracts only. "Nothing found" means nothing in ~13 queries, not proof of absence. Nothing was published or contacted.

Takeaway: the least crowded options are the ones where the systems cost of agents is measured at web scale. Agent prompt-injection defense itself is crowded.

## 1. What does it cost to run browsers for agents? (browser-as-agent-runtime)

Idea: agent fleets each drive a full browser; measure and cut the CPU/memory/latency cost per agent session (snapshot, fork, share engine state, headless vs full). 
Ties to the main thread (process sharing) but the tenant is an agent session, not a tab.

Crowdedness
- Systems cost is barely studied; security and benchmarks dominate. [I]
- [F] "A Comprehensive Survey of AI-Powered Web Browsers", Lokhar et al., 2026: "frameworks and APIs must be optimized for latency and …" (Scholar snippet, https://ieeexplore.ieee.org/abstract/document/11590288/). Survey-level only.
- [F] Vardanyan, "Building Browser Agents": "findings from building and operating a production browser agent … architectural decisions determine success or failure." https://arxiv.org/abs/2511.19477 (practitioner report, no resource accounting in abstract).
- [F] Meng et al. ceLLMate reports "7.25--15% latency overhead" for its sandbox, https://arxiv.org/abs/2512.12594, so overhead is measured only for security add-ons.
- Security side is hot: [F] "Site Isolation is Dead: How Site Isolation is Broken in Agentic Browsers and Extensions", S Lee et al., IEEE S&P 2026, "Cited by 1" (https://ieeexplore.ieee.org/abstract/document/11573584/). It argues agentic browsers weaken the very process isolation the main thread wants to relax. [I] Read it before committing: it may constrain the main thread.

Open [I]
- No paper found that profiles resource use per browser-agent session or proposes agent-specific browser multi-tenancy.
- Whether agent sessions need rendering at all (accessibility tree only) changes the engine design.

First step (bite-sized): run 3-4 open browser agents on 100 sites from the group's crawl; log per-session CPU, RSS, process count, wall time, LLM tokens; compare with a scripted visit of the same page.

Web data helps: the crawl gives realistic page weights and the distribution of site complexity, so cost curves are for real pages, not WebArena toys.

## 2. HTTP-layer enforcement for browser agents: does it hold on the long tail?

Idea: ceLLMate-style policies at the HTTP layer assume side effects are visible as requests. Measure at web scale how often that is true, and what policy language is feasible.

Crowdedness: high for defenses, low for the web-scale feasibility question.
- [F] ceLLMate: "Our core insight is to perform sandboxing at the HTTP layer because all side-effecting UI operations will result in network communication to the website's backend." https://arxiv.org/abs/2512.12594 ("Cited by 32" on Scholar).
- [F] Prismata (Popa group), arXiv 2607.08147: "these mechanisms require no developer annotations, so Prismata supports the long tail of websites." https://arxiv.org/abs/2607.08147
- [F] WASP benchmark, "Cited by 221": https://proceedings.neurips.cc/paper_files/paper/2025/hash/1c9818387f5dd0a0bc151214660f059d-Abstract-Datasets_and_Benchmarks_Track.html
- [F] BrowseSafe, "Cited by 33": "synthesize a benchmark of attacks embedded in realistic HTML payloads." https://arxiv.org/abs/2511.20597
- [F] Pirch et al.: "We argue that both face strikingly similar challenges in isolating resources, separating privileges, and mediating communication." https://arxiv.org/abs/2605.14932 (the OS-for-agents framing is taken).

Open [I]
- Evaluations use WASP/WebArena-style sandboxes, a few self-hosted sites. Whether GET-with-side-effects, GraphQL-over-POST, websockets etc. break HTTP-layer policy across real sites is unmeasured in what I found.
- Cost/benefit of enforcement points (extension vs browser vs network proxy).

First step: from existing crawl, classify state-changing requests on top-N sites after scripted form/click interactions; report % that an HTTP method/path rule could distinguish.

Web data helps: the long-tail claim of Prismata and the "all side effects are HTTP" claim of ceLLMate are empirically testable only with a crawl.

## 3. Measuring AI agent traffic on the real web

Idea: longitudinal, vantage-point measurement of agent/assistant traffic and how sites react (robots.txt, bot walls, fingerprints), using the group's measurement infrastructure.

Crowdedness: moderate and growing fast, mostly small controlled studies.
- [F] "Do Generative AI Assistants Respect robots.txt?": "a controlled empirical study of ten widely used AI assistants … across 200 trials." https://arxiv.org/abs/2607.14447
- [F] Cui et al., CCS 2025: "measuring LLM bots deployed by leading LLM vendors". https://dl.acm.org/doi/abs/10.1145/3719027.3765063
- [F] "Broken Gates": "a systematic measurement study … Our evaluation spans seven solver services and six agents … tested against hCaptcha, reCaptcha v2, reCaptcha v3, and Cloudflare Turnstile." https://arxiv.org/abs/2607.18659
- [F] "On the Internet, Nobody Knows You're an LLM Bot": "deploying multiple honeysites protected by one or more anti-bot mechanisms". https://arxiv.org/abs/2606.30119
- [F] Borysenko: "AI agent access compresses multi-page navigation into a single or two requests, making traditional engagement metrics … unreliable". https://arxiv.org/abs/2604.02544
- [F] Marro et al., "Permission Manifests for Web Agents": "website owners increasingly rely on blanket blocking and CAPTCHAs". https://arxiv.org/abs/2601.02371

Open [I]
- All found studies use honeysites, a few vendors, or one doc portal. Large-scale passive data (CDN/ISP/server logs) on agent traffic share and behavior is absent in my results; it needs a data partner.
- Crawl-side: how many top sites block agents, and does it change over time (robots.txt/llms.txt/agent-permissions adoption).

First step: weekly crawl of top-N sites for robots.txt AI-agent rules, llms.txt, and bot-wall responses with a stock Playwright vs an LLM agent; publish nothing, just a trend table.

Web data helps: this is directly the group's skill set. [O] Risk: it is measurement-only and not "systems" unless coupled with a mechanism (e.g. cheap agent identification protocol).

## 4. Page-to-agent cost: how heavy is the web for agents?

Idea: agents pay per token and per second to ingest DOM/accessibility trees. Measure at crawl scale the token cost and a11y quality of real pages, then build a server/edge-side or client-side page reducer.

Crowdedness: low-moderate; mostly position papers and small evals.
- [F] webMCP: "reduces processing requirements by 67.6% while maintaining 97.9% task success rates" over "1,890 real API calls" https://arxiv.org/abs/2508.09171
- [F] Lù, "Build the web for agents, not agents for the web": "the fundamental mismatch between human-designed interfaces and LLM capabilities". https://arxiv.org/abs/2506.10953
- [F] "A11y-CUA Dataset: Characterizing the Accessibility Gap in Computer Use Agents", https://dl.acm.org/doi/abs/10.1145/3772318.3791896
- [F] Yang et al., "Agentic web: Weaving the next web with ai agents", "Cited by 117", https://arxiv.org/abs/2507.21206 (vision paper).

Open [I]
- No crawl-scale distribution of agent-visible page size (DOM, a11y tree, screenshot tokens) found.
- Caching/dedup of page state across agent sessions (shared infrastructure) not found.

First step: for 10k pages from the crawl, compute raw HTML, DOM, a11y-tree token counts and the fraction of interactive elements lacking accessible names.

Web data helps: needs real pages; strongest fit with existing data. [O] Smaller-scoped; may be a paper, not a thesis, unless it grows into a protocol/runtime.

## 5. (Lower priority) Wasm edge serverless, web energy, HTTP/3

- Wasm edge runtimes: crowded with benchmarking papers. [F] e.g. "HybridServe: Adaptive WebAssembly-Container Runtime Selection for Edge Serverless Computing" https://dl.acm.org/doi/abs/10.1145/3774899.3775011; "Lumos: Performance characterization of webassembly as a serverless runtime in the edge-cloud" https://dl.acm.org/doi/abs/10.1145/3770501.3770515; "WebAssembly and Unikernels: A Comparative Study for Serverless at the Edge" https://arxiv.org/abs/2509.09400. [O] Skip unless it merges with the main thread (multi-tenant isolation).
- Web energy/resource cost: results are small tools and surveys, e.g. "Challenges related to approximating the energy consumption of a website" (IEEE Access 2025, "Cited by 7"). Related niche: "In-the-Wild JavaScript Dead-Code Elimination via HTTP Range Requests" (Varvello et al., 2026) https://dl.acm.org/doi/abs/10.1145/3777912.3839817. [I] Possible add-on, not a thesis.
- HTTP/3 performance: results were low-quality/thin in Scholar for 2025; not investigated further.

## Ranking [O]
1. Direction 1 (agent browser runtime cost): least crowded, fits "something special", reuses browser-isolation thinking from the main thread. Must first read "Site Isolation is Dead".
2. Direction 2 (HTTP-layer enforcement feasibility): crowded topic but a measurable gap; good fit for web data.
3. Directions 3 and 4: quick wins using crawl data; combine as one measurement-first paper to build intuition.
