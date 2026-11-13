# Other web directions (vlm10_other)
(authored by agents unless marked 🧑)

Scope: web-specific, non-PL directions, excluding agent-browser security and cross-tab process sharing.
Method: Scholar via the human's browser, arXiv, and 2025-26 programs of IMC, NSDI, OSDI, SOSP, CCS, NDSS, S&P.
Not readable: WWW 2025/26, USENIX Security 2025, SIGCOMM 2025 program pages (connection errors / blank). No CAPTCHA seen.
Evidence with quotes + URLs: raw/findings_agent.md, raw/findings_programs.md. Scholar quotes are snippets.

## Takeaway (opinion)
The strongest fit is directions 1+2: web archives as a trustworthy evidence substrate for agents.
- fact: the advisor's group is publishing archive fidelity now (NSDI 2026 "Detecting and Diagnosing Errors in Serving Archived Web Pages"; IMC 2025 "Toward Better Efficiency vs. Fidelity Tradeoffs in Web Archives")
- fact: agent benchmarks started using archives (WARC-Bench, ICLR 2026; TimeWarp, arXiv 2026)
- inference: nobody joins the two; this gives a differentiator with existing group data and tools

## 1. Web atoms: co-changing URL groups as invalidation units
- source: human note web_atoms.md 🧑 "group of URL that change together with high probability"
- novelty evidence (fact, shallow search): no hit for co-change groups; closest are per-URL recrawl schedulers, e.g. an RMIT thesis snippet "stateless crawl ordering schemes that have no past change", and "Neural prioritisation for web crawling" (SIGIR 2025)
- use: recrawl for archives, cache invalidation for agents, staleness of agent benchmark tasks
- first step: from existing group crawls (or Internet Archive CDX), mine co-change of resources across snapshots; measure how many probes an atom-based recrawl saves at equal staleness
- risk: may reduce to known correlation mining; co-change may be dominated by trivial cases (same template/site-wide deploys)

## 2. Faithful, verifiable archives for agents
- evidence: CCS 2025 "The Power to Never Be Wrong" shows evasions and anachronistic attacks: users assume archives "provide reliable ground truth for comparing the past to the present"; "How Benchmarks Mis-Score Computer-Use Agents" (arXiv 2026): "15.3% of FAIL verdicts are wrong"
- gap (inference): no replay-time check that agents see what a live browser saw; benchmarks on archives inherit fidelity errors silently
- first step: replay WARC-Bench/TimeWarp tasks through the NSDI 2026 fidelity detector; count tasks whose pass/fail flips from archive errors
- risk: may be judged a benchmark-hygiene paper unless it yields a general fidelity guarantee

## 3. Page loading and caching for browser agents
- evidence: only adjacent work: "Are LLM Web Search Engines Sustainable?" (WWW 2026), NSDI 2026 CacheCatalyst ("latency involved in re-validation requests"), agent serving papers ("non-LLM components dominating latency in 5 of 10")
- gap (inference): no top-venue paper on what agents fetch/render vs humans, or load paths designed for agents (agents read accessibility trees, not pixels)
- first step: trace Browser-Use-style agents on 100 sites; measure bytes/time spent on resources never used by the agent's observation
- risk: weakest-searched topic; fast-moving industry (agent-specific endpoints, llms.txt) may preempt it

## 4. Crawler/agent access control at the edge
- evidence: IMC 2025 "Scrapers selectively respect robots.txt directives", "Somesite I Used To Crawl"; NDSS 2026 ExpShield: "Existing protections require compliance from crawlers"
- gap (inference): crawler blocking measurement is crowded; open is user-delegated agents vs training crawlers, and verifiable identity enforced at CDN; ties to the human's Cloudflare interest
- first step: measure how top sites respond to the same task by human browser, browser agent, and declared AI crawler
- risk: crowded; needs CDN-side data for depth

## 5. Answer-engine source ecology, longitudinally
- evidence: mostly arXiv/marketing: "Synthetic Sources?" (arXiv 2026), "What Drives AI Citations?" (arXiv 2026); human note web_user_facing.md 🧑 "measuring retrieval of Perplexity, ChatGPT, etc. in search mode"
- gap (inference): no IMC/WWW-style longitudinal study linking publisher blocking, synthetic content, and what gets cited
- first step: daily queries to 3 answer engines on volatile topics; archive cited pages; classify source type
- risk: platform ToS and API drift; results date quickly

## Other themes seen, not recommended (opinion)
- cross-browser behavior differences (CCS 2025 ×2, IMC 2025): snapshot studies; longitudinal version is incremental
- WebGPU performance (IMC 2025), WebView guarantees (NDSS 2026): narrow

## Limits
- search depth: 1-2 query rounds per topic; "no hit" ≠ no prior work
- vlm5 clusters.md: all verification/PL-oriented; nothing reused
