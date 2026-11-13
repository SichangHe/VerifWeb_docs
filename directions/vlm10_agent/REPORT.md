# Security for browser-using AI agents: deeper map and new directions
(authored by agents unless marked 🧑)

Evidence files: `map.md` (prior-work map, verbatim quotes + URLs, cited-by lists), `directions.md` (other directions, ranked), `exp/RESULTS.md` (pilot crawl). Raw pages: `raw/`. Labels: [F] fact with source in those files, [I] inference, [O] opinion.

## Takeaway
- [I] D1 and D2 from vlm9 are much weaker than vlm9 thought: the area filled up between Jun and Oct 2026.
- [O] The best fresh direction that uses the group's web data is measuring how real sites treat agents. A pilot found no agent-targeted injection on homepages, but did find widespread agent-specific blocking and serving.
- [O] The 🧑 process-sharing idea stays the best thesis-scale bet. It is now better motivated, but it is about isolation cost, not agent security as such.

## What changed since vlm9
- [F] "Site Isolation is Dead" (Lee et al., IEEE S&P 2026) attacks the channel between renderers and the agent process in 2 agentic browsers and 7 extensions: "all tested agentic browsers and extensions are vulnerable". Its fixes are prompt-injection guardrails, not process confinement.
- [F] SPIDES (arXiv 2610.24277) does IFC for browser agents using site-supplied labels. It argues that restoring SOP is "neither sufficient … nor necessary" and reports that SOPGuard can be beaten 53–73% of the time in its own testbed.
- [F] Intact (2610.22697) keeps per-element provenance, Prismata (2607.08147) claims "structural confinement guarantees", and UCM and SA-CUA mask DOM regions or screenshots.
- [F] Chrome's own post already says the browser can enforce some of this separation ("not even sending to the model data that is outside the readable set"). It also says an unrestricted agent "can create what is effectively a Site Isolation bypass".
- Quote check: the 4 outside quotes in vlm9 REPORT are verified. vlm9's claim "all are label or policy layers" is too strong (Chrome quote above). survey.md has a stale CaMeL number (the page now says 77%) and one unfound claim (Roesner/Kohlbrenner "recommend provenance tracking").

## Still open (inference from search absence; queries in map.md)
- per-origin agent instances inside real Site Isolation processes or OOPIFs (out-of-process iframes), measured
- a mechanized proof over a frame/origin/request model; existing guarantees are over tool-call or label models
- per-frame pixel provenance for screenshot agents
- browser-enforced "agent CSP"; the nearest things are WebMCP's Permissions Policy `tools` feature and SPIDES labels enforced by its harness
- [O] D1 survives only in narrowed form: "enforce agent confinement with the browser's process model, and show how far it gets". After Lee et al. and SPIDES that is a hard sell. D2 alone looks like CaMeL or SPIDES with a proof attached.

## Ranked directions (details in directions.md)
1. Shared-process isolation at agent scale (🧑 idea)
   - [F] no work found on which origins may safely share a renderer or isolate; related: Site Isolation, Workers isolates, Spectre-on-Workers, Mohabi
   - [I] Lee et al. show agents already erode Site Isolation, so cost vs safety per trust class is a live question
   - first step: count renderers needed per policy (per-site vs shared within a trust class) on the group's crawl, then measure memory in Chromium
   - risk: weak link to agents; Spectre may make sharing indefensible (itself a result)
2. Measurement: how the web treats agents (cloaking, blocking, injections in the wild)
   - [F] Zychlinski formalized agent-targeted cloaking without measuring it; Khodayari et al. found 15.3K injections in 1.2B URLs and note that agent-targeted cloaking "would not be captured by Common Crawl"
   - fits the group's crawl infrastructure directly
3. WebMCP exposure in the wild (two lab papers, no measurement; adoption may be near zero)
4. Agent identity (Web Bot Auth, signed agents): do sites verify signatures, or is a spoofed UA enough
- dropped as crowded: UI deception against vision agents, robots.txt/llms.txt, agent fingerprinting

## Pilot experiment (direction 2), exp/RESULTS.md
- method: Tranco top 500 homepages, plain HTTP without JS; Chrome UA (fetched twice for noise) vs ChatGPT-User, Claude-User and GPTBot UAs
- coverage: 264 of 500 sites usable; 236 failed even for Chrome (no `www.` retry)
- [F] 38/264 blocked at least one agent UA (GPTBot 36, ChatGPT-User 28, Claude-User 22)
- [F] reddit.com and pinterest.com return 403 to the OpenAI UAs but 200 to Claude-User; google.com serves agents a reduced page (Jaccard 0.24, a word-overlap score where 1 means identical)
- [F] 23 sites show content differences beyond noise; 0 genuine instruction-like injections (1 false positive)
- [F] some sites challenged Chrome but served agents the full page (microsoft.com, booking.com)
- limits: UA only (no TLS/IP fingerprint), homepages only, no JS, one vantage point; agent UA strings were written from memory and not checked against vendor docs
- [I] cloaking aimed at agents, if it exists, is not visible at this level; a real test needs JS rendering, deep pages, real agent fingerprints/IPs and hidden-text checks

## Needs the human's judgment
- whether direction 1 should be framed as agent infrastructure (a cost and isolation thesis) rather than as agent security
- whether a measurement-first paper (direction 2) is an acceptable bite-sized start
