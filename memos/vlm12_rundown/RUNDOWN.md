# Verified browser for AI agents: a rundown
(authored by agents unless marked 🧑)

Labels: facts are sourced (see Sources at the end); "opinion" and "inference" mark agent judgment.

## 1. What we actually want

The setting. An "agent browser" is a headless browser (no screen) that AI agents drive by program, not by a person. Lightpanda is one: to stay cheap, it runs many agent sessions inside one operating-system process, each with its own V8 JavaScript engine instance. "Session" here means one agent's browsing state: its cookies, storage, open pages, network traffic.

The goal (opinion). Run many untrusted agent sessions in one cheap process, with mathematical proof that the browser's rules hold. "Formally verified" means a machine-checked proof that the code meets a written specification, for all inputs, not just tested ones.

The guarantees, each checkable by a non-specialist:

1. Session A can never read session B's cookies, storage, cache, or network responses.
2. Every outbound connection (page load, fetch, redirect hop, WebSocket) is checked against the operator's allow/block list before it is made.
3. A cookie is sent only to the sites the cookie rules (domain, SameSite, credentials mode) allow.
4. Login headers are not carried to another site when a request is redirected there.
5. The browser computes a page's "origin" (scheme + host + port, the unit of web security) exactly as the URL standard says, so one site cannot pose as another.
6. Only an authenticated controller can drive a session; a random web page cannot.

Who attacks (the adversaries): a malicious web page the agent visits, a prompt injected into page text that steers the agent, another tenant's session in the same process, and anyone on the network who can reach the control port.

What a proof would actually say (inference): "the six guarantees hold, assuming the JavaScript engine keeps its memory separate" (section 2). The guarantees concern the browser's own rule-checking code, which I call the "core" below; Quark's paper calls the same thing a "kernel" (not the OS kernel).

## 2. Do we need a formally verified JavaScript engine?

No (inference). All six guarantees are about code that sits between the engine and the outside world: the URL parser, the cookie jar, the network request path, the per-session state, the control port. If JavaScript can only reach the outside through that code, the engine can be buggy and the guarantees still hold. Quark (USENIX Security 2012), a small research browser, did this: it proved its core correct in Coq (a proof assistant) and ran each tab's untrusted engine in a separate OS process that could talk only to the core. Lightpanda puts all sessions in one process, so it lacks that OS barrier; that is the open problem below.

What the guarantees still depend on in the engine, stated as assumptions:

- memory isolation between engine instances: a memory-corruption bug in V8 lets attacker code escape and read anything in the process, which breaks guarantee 1. Proof cannot cover this unless the engine is verified or each session runs in its own OS process.
- the binding layer (the ~10k lines, written in Zig, a C-like language, of Zig that connect V8 to Lightpanda's own code) must not hand one session's objects to another. This layer is small enough to be in scope.
- side channels such as Spectre (timing attacks that read memory across a boundary) are below any such proof.

Is a whole verified engine doable now? No (opinion). Engines are 77k–167k lines; the largest verified systems are 10–30 times smaller; the largest agent-written proof found is about 6k–8k lines. A verified slice is doable: we verified one Boa number-conversion function against the JavaScript spec for all inputs.

## 3. Lightpanda's published security advisories

Lightpanda has 11 GitHub security advisories (May–November 2026). In plain words:

Rule-checking bugs (9):
- the URL parser got a page's origin wrong when the path contained "@", so one site could act as another (critical)
- fetch and XMLHttpRequest sent the session's cookies to other sites even when told not to (critical)
- login headers were carried to another site after a redirect
- a cookie could be set for a lookalike domain because only the end of the name was compared
- "SameSite=Strict" cookies (meant for same-site use only) were sent on navigations from other sites
- the same cookies were sent to a nested frame under another site's page
- "SameSite=Lax" cookies were sent in cross-site frames and cross-site form posts
- the debugging control port (CDP, Chrome DevTools Protocol) did not check who connected, so any web page could take control of the browser
- the AI-tool control server (MCP, Model Context Protocol) had the same flaw

Memory bugs (2):
- a WebSocket message length could overflow an integer, letting anyone crash the browser
- long element or tag names overflowed a heap buffer

Our own finding (fact: reproduced on a Lightpanda nightly by two independent agents; not reported to Lightpanda): the `--block-urls` option does not apply to WebSockets, so a blocked host is still reachable that way. This breaks guarantee 2.

Takeaway (inference): the 9 rule bugs map to guarantees 3–6 (cookies: 3; redirect: 4; URL: 5; control ports: 6), and all 9 are in the small rule-checking code a proof would cover.

## 4. The 22 candidates from the earlier wide search

These are web components where a proof could help, regardless of agents. Grouped by where they run. Terms: CORS = rules for when one site may read another's responses; CSP = a page's own list of allowed script sources; SameSite = a cookie flag limiting cross-site sending; use-after-free = using memory after releasing it.

Inside the browser:
1. JIT range analysis (the compiler step that decides which array checks to skip): already well studied
2. URL parser: prove it matches the standard; no full proof exists
3. CORS, CSP, cookie rules: a Coq model of the spec exists (WebSpec); not tied to real code
4. site isolation (one OS process per website): only Quark (2012, a toy browser); different from our per-session isolation
5. WebAssembly: already well studied
6. WebGPU shader translation: translators have real bugs (15 Chrome CVEs); no proof exists
7. IndexedDB (in-browser database): repeated use-after-free bugs; no proof exists
8. extension permissions: only pre-2020 work
9. HTML/CSS/cookie parsing: not searched

Servers and CDNs (content delivery networks: caching servers in front of websites):
10. HTTP request framing: two servers can disagree where a request ends ("request smuggling"); only fuzzing exists
11. HTTP/2 to HTTP/1 conversion: can change a request's meaning; no proof exists
12. cache keys: a cache can serve one user's page to another; no proof exists
13. edge computing isolation and rule languages: none for V8-based edges
14. HTTP/2 resource limits: denial-of-service bugs (Rapid Reset); no proof exists

Protocols:
15. QUIC/HTTP/3: tested against models, not proved
16. encrypted TLS hello (ECH): protocol proved; browser fallback not
17. DNS-over-HTTPS fallback: barely searched

Web standards:
18. passkeys: proved, except new synced passkeys
19. OAuth login: proved on paper, not by machine
20. cookie/storage partitioning by site: no model includes it
21. Fetch spec: not mechanized
22. permissions policy: not searched

Opinion: only 2 and 3 serve the goal directly (guarantees 3 and 5). 10, 11, 12 share one idea, "two programs must read the same bytes the same way", but are server-side, not agent-browser work.

## 5. More web-oriented directions

These are new to this rundown, mostly about agents, from Gemini and agent brainstorming. Prior-work names from Gemini are unchecked. A Google Scholar search ("formal verification browser AI agent web security") found agent-browser security papers but none with formal proofs on page one.

1. what the agent sees: the text given to the agent includes only elements that layout draws on screen with nonzero size and opacity (hard to specify; feasibility unknown), so hidden text cannot inject instructions
2. control-port permissions: a controller allowed to drive tab A cannot read or touch tab B (generalizes the CDP/MCP advisories)
3. click-time check: an agent's click lands only if the target element is still the one the agent saw, so a page cannot swap it at the last moment
4. secret handles: a password the agent types is readable by no page script, and is sent only to the site it belongs to
5. session reset: a recycled engine instance holds nothing left over from the previous agent
6. HTML round trip: sanitized HTML parsed, saved, and parsed again yields the same tree, so cleaned content cannot turn into a script
7. bounded work per page: one page's event loop cannot starve other sessions in the same process
8. engine–DOM boundary: no DOM object is freed while JavaScript can still reach it (use-after-free freedom)

Opinion: 2, 4, and 5 fit the multi-session core best; 1 and 3 are new problems that only exist because agents drive browsers.

## Needs your judgment
- whether "a verified multi-session core for agent browsers" is the direction you want
- whether to build on Lightpanda (proof tools for Zig do not exist, so a proof would cover a model or a rewrite in Rust/Verus) (Zig, AGPL license, changing fast) or write a small new core

## Sources
- Lightpanda advisories: https://github.com/lightpanda-io/browser/security/advisories (all 11 checked via GitHub API on 2026-11-07; IDs: GHSA-mq6p-m9cc-q432, GHSA-36mm-v3c2-24cc, GHSA-mcw6-8p83-pm3h, GHSA-4j5j-4ggv-2vgj, GHSA-rm33-829c-942c, GHSA-xxrm-48f7-h89p, GHSA-5gg3-f7j5-hfv4, GHSA-wjwj-jrwg-3wgm, GHSA-rqpx-pxch-q2cm, GHSA-7c5w-p4q2-98gf, GHSA-3jpq-xwf3-rwr6)
- Lightpanda design and WebSocket finding: out/vlm11_agentbrowser/REPORT.md, lightpanda.md, ../cloud/p5_lightpanda_blockurls.md
- Quark: "a browser whose kernel has been implemented and verified in Coq … including tab non-interference, cookie integrity and confidentiality, and address bar integrity", https://www.usenix.org/conference/usenixsecurity12/technical-sessions/presentation/jang
- engine sizes, proof scale, Boa attempt: out/vlm11_jsengine/REPORT.md
- 22 candidates and their sources: out/vlm11_spread/REPORT.md, notes/engine.md, notes/proto.md
- section 5: out/vlm12_rundown/gem_out.md (Gemini), scholar1.txt
