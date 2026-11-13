# Task: generate UNUSUAL formal-verification targets about the web
(authored by agents unless marked 🧑)
Context: CS PhD student (systems; past projects: LLM-assisted formal verification in Verus/Lean, web measurement, browser agents). Advisors asked for formal verification targets in the web context, bite-sized, with a differentiator. Advisor quote: "you need to have some differentiator".
Human (verbatim): "Yes, your ideas are not weird enough. How do we get ideas that people normally would not consider? Take inspiration from other things we've done"
Human (verbatim), correcting a previous attempt: "I think you misunderstood what I said about Think about weird ideas. I'm still talking in the sense around... Verifying things that are maybe related to the web."

DEFINITION OF A VALID IDEA (all three required, else drop):
1. a concrete web thing (a protocol, browser mechanism, web standard, server/CDN behavior, page/script property, web data artifact)
2. the exact theorem we would machine-check about it
3. why people normally would not think to verify it
Also give: closest prior work you know; a first bite-sized step (weeks, not years).
The OBVIOUS ideas below are already taken and count as NOT weird. Do not repeat them.
Give 8-12 ideas, each <=5 plain lines.

## Already-listed (NOT weird) ideas
### ../msg_candidates.txt
The original task (Nov 3 meeting): "Write down 10 different things that you might like to verify, either about individual JavaScripts or the engine itself", picked from real breakage. Here are our 13 candidates. Each: the real failure, what we would prove, and what we tried so far. "Model" means we proved a small hand-written copy, not the real engine code.

ABOUT THE ENGINE

1. JIT side effects (V8, SpiderMonkey)
- failure: CVE-2020-6418, exploited in the wild: the JIT assumed an operation had no side effects, but a Proxy could run code and change an array's type
- prove: any operation that may run JS invalidates the type facts the JIT inferred before it
- tried: a solver model catches the CVE's bug shape; model only

2. JIT range analysis (V8)
- failure: CVE-2021-21220: the JIT wrongly concluded a value is always 0 and removed a bounds check
- prove: the range the JIT computes for each operation contains every real result
- tried: a solver checked V8's integer range rules; multiplication could not be settled at 64 bits; model only

3. JIT phases keep earlier decisions valid (V8)
- failure: CVE-2021-4102: a later phase changed a value after an earlier phase decided a memory-write safety check was unnecessary
- prove: decisions made in an earlier phase stay true after later phases
- tried: toy proof; an independent review says it is a related but different bug

4. Garbage collector frees only dead objects (V8, Boa)
- failure: CVE-2021-37975, exploited in the wild: live objects stayed unmarked and were freed
- prove: when sweeping starts, every reachable object is marked
- tried: proofs of Boa's marking algorithm (model); found a real Boa use-after-free (an object revived by its finalizer is freed anyway), confirmed twice

5. Sandboxed code stays in its memory (Wasmtime, V8 sandbox)
- failure: CVE-2023-26489: Wasmtime computed 35-bit addresses where 33 were allowed, reaching outside the sandbox
- prove: every memory access an attacker can steer lands inside its own region
- tried: proofs on models of Wasm bounds checks and V8's pointer table; the CVE's bug is rejected

6. Tabs or tenants sharing one process cannot reach each other
- failure: vm2 CVE-2023-29017: sandboxed code got a host object and escaped
- prove: no object of context A is reachable from context B except through declared channels (Spectre out of scope)
- tried: proof on a two-context heap model, for any sequence of operations

7. URL parser follows the standard (rust-url, used by Servo)
- failure: parsers disagreeing on the same URL is a known attack source
- prove: for every input the parser gives the WHATWG standard's result
- tried: rust-url fails 69 of 896 standard tests; a proof pinned one bug class (Windows drive letters) that also crashes debug builds; two of its bugs were already reported upstream

8. Cleaned HTML stays clean (DOMPurify, ammonia)
- failure: DOMPurify CVE-2024-47875: cleaned HTML turned into script after being parsed again
- prove: parsing the cleaned output gives the same tree, and it has no script
- tried: ammonia's default settings stay script-free but are not a stable round trip; a non-default setting allowed real script injection

9. Event loop runs callbacks in the standard's order (Boa, Node)
- failure: Node 10 and earlier ran timers before promise callbacks
- prove: after each task, all queued promise callbacks run, in order, before the next task
- tried: found Boa gets the order wrong on 4,171 of 9,430 test programs; fix proved; confirmed twice

10. Servo's DOM-to-GC safety rules
- failure: Servo issues #24621, #15318: destructors touched freed objects during shutdown
- prove: destructors touch no other GC object, and every live GC pointer is tracked
- tried: bounded checks on a mock of Servo's API catch the #24621 pattern

ABOUT INDIVIDUAL SCRIPTS

11. Libraries do not change built-in prototypes
- failure: lodash CVE-2019-10744 (prototype pollution)
- prove: after any library call on untrusted input, built-in prototypes are unchanged
- tried: 46 of 120 package versions polluted (two current ones still do); 63 of 95 real sites change a built-in after loading

12. Third-party scripts do not send your data elsewhere
- failure: card-skimming scripts on checkout pages
- prove: no script reads password/payment fields and sends them to a site outside an allowlist
- tried: 0 of 68 pages leaked passwords; 11 of 139 sent the typed email to another site before submit (often hashed)

13. Regexes run in linear time
- failure: Cloudflare's 2019 outage from one backtracking regex
- prove: matching time grows linearly with input length, or the regex is flagged
- tried: about 12% of 28k real regexes are super-linear; about 75% can be proved linear

Later additions (not in the original 13)
- engine built-ins match the language spec: found 7 real Boa/Nova bugs this way, e.g. "abc".at(-1e300) crashes Boa
- the rule-checking code of an agent browser (cookies, URL origin, redirects, request blocking), from Lightpanda's 9 rule bugs
### ../vlm11_spread/REPORT.md
# Web/browser things worth formally verifying: a wide list
(authored by agents unless marked 🧑)

Labels: [F] fact, with a source; [I] inference; [O] opinion. Each item's verbatim quotes and URLs are in `notes/engine.md` (browser engine) and `notes/proto.md` (servers, protocols, standards). Caveat [F]: many quotes come from search-tool summaries, not fetched pages, and the notes mark those. No Scholar fetches were made. Searches on Wasm-engine CVEs, cookie parsing, cache deception and OAuth CVEs were blocked by a tool safeguard.

## Takeaway [O]
The most web-specific gap is "two programs must agree on how to read the same bytes". Today that is checked only by fuzzing, and the disagreements are real attacks: request smuggling, cache poisoning, URL confusion, HTTP/2 downgrade. One proof framework, "this translator or this pair of parsers preserves meaning", covers several of the top 5.

## Candidates (22; bug evidence / prior verification / what is new)
Browser engine
1. JIT range analysis: CVE-2019-9793 / done: VeRA (PLDI 2020), V8 translation validation (ICSE 2024) / new: little; crowded
2. WHATWG URL parser vs RFC 3986: CVE-2021-32786 / done: only a partial, unreviewed Lean proof of one path rule / new: full parser proof plus a differential theorem
3. browser security mechanisms (CORS, CSP, cookies, service workers): WebSpec found flaws / done: WebSpec (Coq model of the spec, not the code) / new: link the model to engine code
4. site isolation and the browser kernel: none gathered / done: QUARK (2012, toy browser) / new: Chrome-scale isolation invariants
5. WebAssembly semantics: CertiCoq-Wasm found a WasmCert modeling bug / done: WasmCert, WasmRef, vWasm / new: little; crowded
6. WGSL/WebGPU shader translation: DarthShader found 39 faults, 15 got Chrome CVEs / done: none found / new: WGSL semantics plus a verified or validated translator to HLSL/MSL/SPIR-V
7. IndexedDB: repeated use-after-free CVEs, e.g. CVE-2026-15107 / done: none found / new: lifetime and transaction model
8. extensions: none gathered / done: IBEX (pre-Manifest V3) / new: MV3 permission model
9. HTML/CSS parsing and cookie parsing: not searched (gap)

Servers, CDNs, edge
10. HTTP/1.1 framing agreement (smuggling): HTTP Garden "substantial parsing discrepancies exist between nearly all pairs" / done: fuzzing only; EverParse verifies single parsers / new: agreement proof between pairs
11. HTTP/2-to-HTTP/1 downgrade translator: PortSwigger, AWS ALB accepted Transfer-Encoding / done: none found / new: meaning-preserving translator
12. cache keys (poisoning, deception): PortSwigger / done: none found / new: a cache-key soundness property, "same key implies the origin gives the same response"
13. edge isolation and edge config languages: Cloudflare Spectre (vlm10) / done: vWasm, WaVe for Wasm; none for V8 isolates or rule languages / new: verified edge rule compiler
14. HTTP/2 stream state and resource bounds: Rapid Reset, CVE-2023-44487 / done: none found / new: resource-bound proofs

Protocols
15. QUIC/HTTP/3: Ivy found spec ambiguities / done: Ivy testers (draft-29) / new: QPACK, WebTransport, RFC 9000
16. TLS ECH in browsers: done: ProVerif (CCS 2022) / new: browser fallback and DNS interaction
17. DoH fallback: weakly searched

Standards
18. WebAuthn/passkeys: done: several proofs / new: synced passkeys, browser-side origin checks
19. OAuth/OIDC in browsers: done: pen-and-paper (Fett, Küsters, Schmitz, CCS 2016) / new: a mechanized proof
20. SameSite and storage partitioning: CHIPS spec patch for service workers / done: none found; a 2019 Tamarin model lacks them / new: model of the partition key
21. Fetch spec algorithms: done: none found / new: mechanize Fetch, as WasmCert did for Wasm
22. Permissions Policy: not searched

## Top 5 (special and web-specific) [O], each with a first small step
1. HTTP/2-to-HTTP/1 downgrade (11)
   - step: write a reference meaning for requests in Lean or Dafny, then prove a small downgrader keeps it; run it against HTTP Garden's inputs
2. parser agreement for HTTP framing and URLs (2, 10)
   - step: prove the WHATWG URL host/path rules equal RFC 3986 where both are defined, and list the exact inputs where they differ
3. cache-key soundness at CDNs (12)
   - step: state the property formally; check it on one open cache (e.g. Varnish's default key) against an origin model
4. WGSL shader translation (6)
   - step: per-shader translation validation for a small WGSL subset to SPIR-V in Tint or Naga; replay the DarthShader bugs
5. cookie/storage partition model (20)
   - step: extend WebSpec's Coq model with the CHIPS partition key and check the service-worker invariant

## Is a verified JS engine doable now? [O]
I don't know. Evidence: Wasm took years of spec mechanization (WasmCert). JS is much larger, and only spec-level work (e.g. JSCert, older) exists. Agents may cut the cost, but no result shows it. The top 5 are each far smaller.
### ../vlm15_pitch/PITCHES.md
# Three verification pitches for the advisors
(authored by agents unless marked 🧑)

Labels: [F] fact with a source, [I] inference, [O] opinion. Origin of each idea: "ours" = earlier agent reports in `out/`; "GPT" = `gpt_out.md` / `gpt_PITCHES.md`; "Gemini" = `gem_out.md` (both consults in this directory). Durations are opinions. Reading and search only; nothing was run or published.

Terms. Verified = a machine-checked proof that code meets a written specification. Replay = serving an archived page offline from saved copies. Fidelity = the replayed page behaves like the original. JIT = the engine's just-in-time compiler, which emits machine code at run time. Tenant = one untrusted party (a tab, agent session or customer script) sharing a process. Core = the small rule-checking code (URLs, cookies, redirects) a proof would cover.

What the advisors asked for (Nov 3 transcript; the transcript labels speakers by number, not name):
- Speaker 5: "Verification targets that you can think of in the web context. Because we have lots of data, we have lots of experience"
- Speaker 1: "you need to have some differentiator ... Otherwise ... 3 months later, somebody else put it on the archive already"
- Speaker 5: "The trick will be to pick interesting ones, pick bite-sized problems and make slow headway. The key thing, I think, is to find out whether… what tools there exist that you can use and build upon."
- Speaker 5: "the runtime verification has the dynamic state context, and that's the difference. The question is, for the given state, what is the behavior of this? As opposed to, for any given state"
- Speaker 1, on tab sharing: "it would also require, like, on-the-fly verification of the JavaScript code on the page you're loading"

Advisors' recent work that the pitches connect to [F] (Google Scholar, fetched 2026-11-08, saved in `scholar/`):
- Madhyastha: FidEx, "Detecting and Diagnosing Errors in Serving Archived Web Pages" (Zhu, Sun, Madhyastha, NSDI 2026); IMC 2025 archive efficiency vs fidelity; "DeGenTWeb: A First Look at LLM-dominant Websites" (with Govindan, arXiv 2026)
- Govindan: "Blackbox Performance Analysis of LLM-based Network Control" (with Ghavidel, arXiv 2026); "Near-optimal Online Traffic Engineering"
- Ghavidel: "ZENITH: Towards A Formally Verified Highly-Available Control Plane" (Namyar, Ghavidel, et al., 2025): "it is formallyverified" (Scholar snippet). [I] so the group already verifies a real control-plane design (the snippet says "architecturally similar to Orion, ONOS, and ODL"); I did not check which tool ZENITH uses or whether the proof covers code or a model

Ranking [O]: A has the strongest group fit and matches the "dynamic state" remark; B is the smallest proof target with the clearest bug record; C answers the 🧑 tab-sharing idea but is the most crowded and riskiest.

## A. Certified JavaScript rewrites for web-archive replay (origin: GPT; Gemini proposed a broader version)

Problem. Archives rewrite each page's JavaScript so it replays offline, and wrong rewrites silently break pages; FidEx [F] "reduced the fraction of archived pages which violate fidelity from 15% to 9%" (NSDI 2026 abstract, https://www.usenix.org/conference/nsdi26/presentation/zhu-jingyuan), so 9% still fail. Why now [F]: agent benchmarks now run on archives (WARC-Bench, ICLR 2026; TimeWarp, arXiv 2026), and a separate arXiv 2026 study of computer-use agent benchmarks reports "15.3% of FAIL verdicts are wrong" (10.7% evaluator false negatives, 4.7% broken tasks; `vlm10_other/raw/findings_agent.md`). [I] that study is not about archives; it shows that benchmark errors are already large, so replay errors matter.

What we verify. A checker for one family of archive rewrites, starting with URL construction and `location` reads.
- guarantee: if the checker accepts a rewrite, and the runtime conditions it inserts hold (e.g. "this operand is a plain string, not an object whose conversion runs code"), then the original and rewritten code give the same results and side effects, up to the archive's URL mapping
- the checker's soundness is proved once; each page is then checked against its own concrete state, which is exactly Speaker 5's "for the given state" distinction [I]
- not guaranteed: whole-page fidelity, missing resources, rendering; the JavaScript model's faithfulness is an assumption

Differentiator.
- FidEx finds errors by [F] "tracking and comparing the execution of scripts between when a page is crawled and when its copy is loaded"; A would certify a rewrite without that paired run [I]
- translation validation (checking each compiler output against its input rather than proving the compiler) exists for the V8 JIT (Kwon et al., 2024; `vlm10_share` says ISSTA, `vlm11_spread` says ICSE, venue unchecked), not for archive rewriting [I, from our searches only]

Fit. Uses Madhyastha's archive failures and FidEx as baseline; the group's data is the moat a PL group lacks [O]. Open: whether FidEx code and failure data are shareable (see end).

First paper (~4-6 months) [O].
- build: checker for the most common rewrite family, plugged into the archive's existing rewriting pipeline (not yet inspected)
- prove: acceptance implies equivalence for that family, in Lean or Rocq (or Verus if the checker is Rust)
- evaluate: historical FidEx failures and fixes; fraction of rewrites certified; false rejections; replay overhead
- first 2 weeks: classify FidEx failures; continue only if several fit one small semantic model

Biggest risk. Getters, dynamic dispatch and browser state may make most real rewrites uncheckable locally. If so we learn which shared replay functions should be verified instead; that alone is likely not a paper [O].

## B. A verified request and session core for agent browsers (origin: ours; Gemini agreed; GPT's "permission lifetime" sharpening)

Problem. Agent browsers cut cost by running many sessions in one process, so a rule bug in URLs, cookies or redirects leaks between sessions or sites. Evidence [F] (all 11 advisories checked via GitHub API 2026-11-07, `vlm12_rundown`; the earlier `vlm11_agentbrowser` counted 7 of 11, the 9 is the later count and includes the two control-port bugs): Lightpanda (an open-source headless browser for agents) had 11 GitHub advisories May-Nov 2026, 9 of them rule bugs, e.g. GHSA-mq6p-m9cc-q432 "URL parser misidentifies page origin for URLs containing @ in the path - Same-Origin Policy bypass", GHSA-mcw6-8p83-pm3h "Credential headers leak across cross-origin redirects", plus unauthenticated control ports (CDP, the Chrome DevTools Protocol, and MCP, the agent-tool protocol). We also reproduced (not reported) that `--block-urls` does not apply to WebSockets.

What we verify. A small Rust core, verified in Verus, that every request and every piece of session state passes through; the JS engine and renderer stay untrusted.
- every connection (page load, fetch, redirect hop, WebSocket, worker) passes one allow/block check before it opens
- a page's origin is computed exactly as the WHATWG URL standard says
- cookies are stored and sent only as the cookie rules allow; login headers are dropped when a redirect changes site
- session A's cookies, storage, cache and responses never reach session B; a reused session inherits nothing
- only an authenticated controller drives a session, and only its own
- GPT's sharper variant: each credentialed request must carry a still-valid permission for its session, page, destination and operation; navigation or revocation kills pending permissions
- assumed: the engine keeps its memory separate; Spectre is out of scope

Differentiator.
- Quark (USENIX Security 2012) verified a browser kernel in Coq with one process per tab [F, `vlm11_agentbrowser`]; it predates SameSite, WHATWG URLs and agents [I]
- WebSpec models the rules in Coq but not code [F, via `vlm11_spread`]
- 2026 agent-security papers: SPIDES, Intact and Prismata defend against prompt injection with labels or guardrails; "Site Isolation is Dead" (S&P 2026) attacks the renderer-to-agent channel of 2 agentic browsers and 7 extensions. None verifies the browser code [F, `vlm10_agent`]
- [I] the gap: a verified core for sessions that share a process; no Quark successor found since 2012 (`vlm11_agentbrowser/prior.md`)

Fit. Small verified systems code like ZENITH; real-site evaluation with the group's crawls [O].

First paper (~4-5 months) [O].
- build: Verus core for URL origin, cookie jar, redirect handling, and single request gate; attach to Servo (Rust) or to Lightpanda through C calls (Lightpanda is written in Zig; `vlm13_check` found no mature Zig verifier, only one experimental SMT tool with 1 GitHub star)
- prove: the guarantees above, no `assume` in the policy path
- evaluate: all 9 rule advisories and the WebSocket bypass become impossible; WPT (web-platform-tests) URL/cookie pass rate (the Rust `url` crate fails 69 of 896 standard URL tests [F, ours; `msg_candidates.txt` item 7]); load and memory on group-crawl pages with many sessions

Biggest risk. Reviewers may call it "a verified firewall" or say an ordinary proxy suffices (unanswered; the answer must be that a proxy cannot see in-process state such as cookie jars and caches), and an unverified engine bug still breaks session isolation. If it fails we learn exactly which engine-boundary properties must be enforced by other means, i.e. the input to pitch C [I].

## C. Checking JIT output so tenants can share a process (origin: ours; both consults agreed)

Problem. Chrome and edge platforms (e.g. Cloudflare Workers) pay memory for process-per-tenant isolation (🧑 "every tab is, like, 300 megabytes"); sharing a process relies on JIT code staying in its tenant's memory. Cloudflare [F]: "we assume that the attacker does not have the ability to execute arbitrary machine code. If they did, they could disable memory protection keys" (https://blog.cloudflare.com/safe-in-the-sandbox-security-hardening-for-cloudflare-workers/); Spectre on Workers leaked [F] "up to 12 bit/s with a 99% accuracy".

What we verify. A checker that runs on each piece of machine code the JIT emits, before it becomes executable (Speaker 1's "on-the-fly verification").
- accepted code reads and writes only its tenant's memory region
- it contains no instruction that changes memory protection, and jumps only to its own code or allowed entry points
- code is checked before running, cannot change while executable, and is retired when the tenant ends
- not covered: the interpreter, GC and builtins (need an existing sandbox such as V8's or Mohabi's) and Spectre

Differentiator.
- Icarus (SOSP 2024) verifies Firefox's SpiderMonkey JIT stub generators once, not each output, and targets JIT correctness, not tenants [F/I; wording not re-checked against the paper]
- Mohabi (OSDI 2026) uses software fault isolation to separate the whole Firefox engine from the rest of the browser at ~25% slowdown, not tenant from tenant [F, `vlm14_engine`]
- VeriWasm and LFI check fixed ahead-of-time sandboxed code; LFI's verifier is proved (Sotoudeh and Yedidia, FMCAD 2025) [F]; "not JIT" for both is [I, GPT-relayed]
- [I] candidate gap: many tenant regions, a real JIT's changing code, tenant reuse; novelty checked from abstracts only

Fit. Directly the 🧑 idea; the group's page corpus is the realistic workload [O]. Weakest fit of the three: machine-code proofs are specialist work and the UCSD/Stanford group (RLBox, VeriWasm, Icarus, Mohabi) owns this area [F names, O judgment].

First paper (~6-9 months, after a 4-week feasibility gate) [O].
- build: checker for one V8 tier on x86-64 with pointer compression and sandbox on (our pilot, on Node 22 with pointer compression off, found 32% of memory operands use raw 64-bit pointers, so without it the checker cannot bound accesses [F, `vlm10_share`])
- prove: checker soundness against an x86 subset model, reusing LFI/VeriWasm machinery
- evaluate: synthetic escapes modeled on CVE-2023-26489 (Wasmtime computed 35-bit addresses where 33 were allowed); check latency; tenants per GB vs separate processes on real pages

Biggest risk. The unchecked engine parts or Spectre dominate, so sharing stays unsafe anyway; or the fallback erases the savings. Then the result is a measurement of where the real trust and cost boundary sits, which is weak as a paper [O].

## Re-answering the open questions

🧑 "It needs to be something special, something ideally to do with the web, not just PL": A and B make the web part of the theorem itself (archive URL mapping; origins, redirects, cookies), and both evaluate on the group's data, which a PL group cannot copy [O]. C is runtime-systems work that happens to host web code, so it is the least web-specific.

🧑 "maybe we should do something about security with the agents using the browsers. Although that is also somewhat crowded": agreed that the prompt-injection side is crowded [F: SPIDES, Intact, Prismata and others, 2026, `vlm10_agent`]. B avoids that crowd by assuming the agent can be fully fooled and proving what the browser still prevents [O]; none of those papers verifies the browser code underneath [I].

🧑 "process isolation across browser tabs ... interesting for Cloudflare workers or something like that to share processes": this is pitch C. Cloudflare Workers already share processes [F: "can run many isolates within a single process", Cloudflare security model], so the contribution must be stronger isolation at the same cost. A verified engine is not needed, but the whole boundary around it is, and no proof removes Spectre [I]. B is its cheaper first half: it removes the logic leaks between sessions.

🧑 "We could argue for agent infrastructure ... efficient browsers ... However, that just are used for light panda": efficiency is the motivation, not the contribution [O]. Lightpanda is mostly efficient by omission (no rendering, one process, one V8 per connection) [I, `vlm14_servo`], and its advisories show the shared core is where it breaks [F]; B turns that into a proof target independent of Lightpanda.

🧑 "I thought we are trying to find things we want to formally verify, right?": yes. Each pitch has one machine-checked theorem about real code: A the rewrite checker, B the request/session core, C the JIT-output checker. The 13 earlier candidates (`msg_candidates.txt`) become supporting evidence (e.g. URL parser, cookie rules feed B), not a shopping list [O].

🧑 "Not sure ... how we turn them into research projects that my advisors would like": bring each pitch as one real failure, one precise guarantee, the closest prior system, and a short test that could kill it [O, GPT's framing]. Suggested first step: the two-week FidEx failure classification for A, because it costs little and uses Madhyastha's own data.

## I don't know
- whether ZENITH's tool or methods carry over to A or B
- full-text novelty for A and C (only abstracts and our searches)
- whether the archive team's failure data is shareable at the granularity A needs
## Previous rejected attempt (off-target: not web-verification). Keep only verification-shaped parts
# Weird web + verification ideas
(authored by agents unless marked 🧑)

How made: read the human's notes (JSphere, DeGenTWeb, C2PA/photo auth, web atoms, Verus proof-agent studies, browser agents) and this project's odd findings; one generator was ChatGPT (`gpt.txt`, prompt `prompt.txt`, told to avoid msg_candidates.txt and vlm11_spread), plus my own. Novelty checks are one Google Scholar first page each (`scholar/*.txt`); "no hit" means only that, not proof of novelty. Ranking is weirdness x feasibility, my opinion.

1. arrow of time for browser security
- pitch: some facts may only move forward (logout, revoked permission, rotated key), even when back/forward cache, session restore, or archive replay brings old page state back
- builds on: archives replaying wrong; proofs surviving behavior changes
- why unusual: browsers deliberately restore the past; nobody states which facts must be exempt
- verify: chosen security facts are monotone across every restore path in a model of navigation + caches
- scholar ("bfcache logout permission revocation"): no relevant hit
- first step: list the restore paths in one engine (Servo/Lightpanda) and write the monotonicity property for "logged out"

2. behavioral fossils
- pitch: code a site removed can still run from service workers, caches, old tabs, or archives
- builds on: web atoms (what changes together), archive replay, JSphere (what scripts do)
- why unusual: deleting code is assumed to kill the behavior
- verify: after version N drops behavior X, no stored state can resurrect X
- scholar ("service worker persistence after site update"): no relevant hit
- first step: a toy PWA with one banned fetch; enumerate resurrection paths by model checking

3. web probate
- pitch: when a domain expires and someone else buys it, browser state (cookies, permissions, saved passwords, HSTS, service workers) passes to the new owner
- builds on: C2PA (identity of who produced content), site isolation work
- why unusual: origin is treated as timeless; owners are not
- verify: authority created under owner A cannot be used by owner B
- scholar: residual trust is measured (Lever et al. S&P 2016 "Domain-Z"; Lauinger et al. 2016), but those study servers/services, not browser-held state; no formal treatment seen
- first step: list which browser stores survive a simulated ownership change

4. proofs that expire
- pitch: a proof about a live site's scripts carries an expiry key = its web atom; when any atom member changes, the proof is void and re-checked
- builds on: web atoms (the human's notes already call them "evidence invalidation units"), JSphere, advisors' "on-the-fly verification" remark
- why unusual: proofs are assumed permanent
- verify: per-site script properties (no prototype change, no field exfiltration) re-proved incrementally as atoms change
- scholar: not checked
- first step: on crawled sites, measure how often atom changes would void a property, i.e. proof shelf life

5. proofs suspiciously hard to kill
- pitch: if a proof survives a real behavior change, the spec is probably weak; use history of engine commits as free mutants
- builds on: our proofs that survived behavior changes; Boa bugs found by failing proofs; LeetProof/StarVerus spec-quality gaps
- why unusual: robust proofs are seen as good
- verify: spec sensitivity: real past bug-fix commits must break some obligation
- scholar: spec mutation exists (IronSpec, OSDI 2024; MutDafny); using real commit history of web engines as mutants not seen
- first step: replay Boa's past fix commits against our existing Boa proofs; count survivors

6. double-entry ledger of browser authority
- pitch: treat permissions like money; every grant (user click, popup, postMessage, worker) is a ledger entry, and spending needs a matching credit
- builds on: Lightpanda's 9 rule bugs; agents breaking site isolation
- why unusual: browser rules are scattered checks, not a conservation law
- verify: no tab/script/agent spends authority it never received
- scholar: only LLM-agent capability papers (2026 preprints); none for browser internals
- first step: 200-line ledger model of user activation + window.open + postMessage; replay real traces

7. agent context window as a renderer process
- pitch: an LLM agent's context mixes text from many sites; treat it as a process that site isolation must govern
- builds on: our finding that agents' context breaks site isolation; browser_agent notes
- why unusual: isolation is proved for memory, not for prompt text
- verify: text labelled origin A cannot influence actions on origin B except through declared channels
- scholar: getting crowded (Christodorescu et al. 2025; WebMCP-Phalanx 2026; "agentic browsers and the same-origin policy"); mechanized proof not seen
- first step: label context chunks by origin in a toy agent loop; prove the action filter in Verus

8. archive replay as courtroom evidence
- pitch: instead of "replay looks right", compute which facts on a replayed page are provably what users saw
- builds on: archives replaying wrong; C2PA provenance
- why unusual: replay quality is treated as engineering, not chain of custody
- verify: each displayed fact has a checked path to captured bytes, time, origin
- scholar: WEFT (2025, forensic web evidence) and Nelson 2019 exist; per-fact admissibility not seen
- first step: on 100 captures, mark page regions "provable" vs "unverifiable"

9. C2PA that survives being stripped
- pitch: assume social sites delete signatures (X, Facebook do, per the human's notes); spread authenticity over k-of-n witnesses
- builds on: photo_crypto_auth, c2pa notes
- why unusual: provenance designs protect one metadata box
- verify: any k surviving witnesses authenticate the same lineage; mixes of two originals fail
- scholar: not checked
- first step: protocol model in ProVerif/Tamarin with three witnesses

10. evolving pages whose fitness is a failed proof
- pitch: generate HTML/JS (DeGenTWeb-style generation) and keep variants that break a stated theorem, not ones that crash
- builds on: DeGenTWeb, proof failures that found Boa bugs, Lightpanda bugs
- why unusual: fuzzers aim at crashes or disagreement, not theorem violation
- verify: the target invariant (e.g. event-loop order) on generated inputs
- scholar: not checked
- first step: evolve programs against our existing Boa event-loop property

Dropped: notarized rendering (vWitness, DSN 2023 is close; low feasibility); privacy policies as specs (likely known; unchecked).
## Inspiration: the human's past projects (how they found unusual angles)
### web_atoms.md
# Web Atoms

web atom: group of URL that change together with high probability

- no need to probe every URL, just probe every member of the group when
    one change

## 🤖 Agent-added research direction (2026-06-07)

- 🤖 Insight: web atoms are useful for agents because they define evidence
  invalidation units. If one member changes, linked claims, crawls, generated
  scripts, UI/API equivalence tests, and receipts may need revalidation.
- 🤖 Why not merely engineering: the paper question is causal validity: can atom
  graphs predict which web evidence and automation artifacts are stale?
- 🤖 Transfer: dependency graphs, incremental computation, active automata
  learning, model-based testing, and dynamic web exploration.
- 🤖 Evaluation sketch: build atom graphs from CDP resource traces, crawl diffs,
  link/resource structure, and deployment metadata; compare atom-based
  invalidation with fixed recrawl schedules on stale-claim prevention, cost,
  and repair precision.
- 🤖 Anchors: Web Dependency Analyzer, WebREC, Browsertrix, Fable, dynamic web
  exploration state-flow graphs.
### web_user_facing.md
# Web User-Facing

- [Investigating influencer VPN ads on
    YouTube](https://par.nsf.gov/servlets/purl/10353407), Omer Akgul,
    Richard Roberts, Moses Namara, Dave Levin, Michelle L. Mazurek, IEEE SP,
    2022
    - scrape YouTube & analyze video
- [Evolving Bots: The New Generation of Comment Bots and
    their Underlying Scam Campaigns in
    YouTube](https://dl.acm.org/doi/abs/10.1145/3618257.3624822), Seung Ho Na,
    Sumin Cho, Seungwon Shin, IMC, 2023
    - scrape YouTube comment & cluster to find user w/ URL in profile
        - fine-tune BERT variant to generate embedding for DBSCAN clustering
        - filter URL: discard most common domain (twitter) and
            very rare domain (personal website)
    - match URL w/ blocklist to find social scam bot (SSB)
        - most are "romance scam" or "game scam"
    - SSB strategy: steal top comment, self-engagement
- [As Advertised?
    Understanding the Impact of
    Influencer VPN Ads](https://arxiv.org/abs/2406.13017), Omer Akgul,
    Richard Roberts, Emma Shroyer, Dave Levin, Michelle L. Mazurek,
    USENIX Security, 2025
- [Reviving Dead Links on the Web with
    Fable](https://dl.acm.org/doi/abs/10.1145/3618257.3624832), Jingyuan Zhu,
    Anish Nyayachavadi, Jiangchen Zhu, Vaspol Ruamviboonsuk,
    Harsha V. Madhyastha, IMC, 2023
    - heuristic to find mapping between dead link and
        new link after page moved

## Search Engine Optimization (SEO)

- ❓ [The influence of search engine optimization on Google’s results:
    A multi-dimensional approach for detecting
    SEO](https://www.researchgate.net/profile/Dirk-Lewandowski/publication/352675578_The_influence_of_search_engine_optimization_on_Google's_results_A_multi-dimensional_approach_for_detecting_SEO/links/60f6f0599541032c6d546fd2/The-influence-of-search-engine-optimization-on-Googles-results-A-multi-dimensional-approach-for-detecting-SEO.pdf),
    Dirk Lewandowski, Sebastian Sünkler, Nurce Yagci, ACM WebSci, 2021
    - insight from interview w/ "SEO expert"
    - questionable heuristics (e.g., HTTPS, manual website classification)
    - dataset: Google Trends, radical right, coronavirus
    - most search result likely have SEO
- ⭐ [Is Google Getting Worse?
    A Longitudinal Investigation of SEO Spam in Search
    Engines](https://downloads.webis.de/publications/papers/bevendorff_2024a.pdf),
    Janek Bevendorff, Matti Wiegmann, Martin Potthast, Benno Stein,
    Springer ECIR, 2024
    - search result on product review & spot affiliate link
        - query: `best <category>` where `<category>` is in
            GS1 Global Product Classification/ Google Product Taxonomy
        - filter review based on keyword regex, but 80% accuracy in test
        - manual classification of top 30 domain:
            authentic review/ magazine&news/ content farm/ spam/ shop/ social
            media/ other
    - top SEO content: repetitive, less readable, shallower URL,
        longer content, more heading, less heading-content overlap
        - lots of SEO metric based on HTML
        - > They are also indicators of lower-quality,
            > possibly mass-produced, or even AI-generated content.
    - comparison w/ BM25 search engine ChatNoir: much more affiliate link
- [Adversarial Search Engine Optimization for
    Large Language Models](https://arxiv.org/abs/2406.18382), Fredrik Nestaas,
    Edoardo Debenedetti, Florian Tramèr, arXiv, 2024
    - embed instruction/defamation in web content to
        manipulate RAG LLM search engine (answer engine)
        - can imply other content is bad
    - test by searching w/ `site:` for owned domain

examples:

- AI SEO spam content when searching for "AI SEO" in Google Scholar:
    [AI Revolutionizes Seo: How Chatgpt & Gemini Can Supercharge Your
    Rankings](https://www.webdesignplusseo.com/ai-revolutionizes-seo-how-chatgpt-gemini-can-supercharge-your-rankings/)
- leading SEO company is huge: [ahrefs](https://ahrefs.com/big-data)

ideas:

- ranking based on user feedback
- measuring retrieval of Perplexity, ChatGPT, etc. in search mode

## 🤖 Agent-added generated/synthetic web directions (2026-06-07)

- 🤖 Source-critical agents: search and answer agents should model source
  ecology, not just rank pages. Live pages, archives, AI-generated pages,
  answer-engine summaries, consent-gated pages, and logged-in pages carry
  different evidence status.
- 🤖 Generated web artifacts: generated sites/components should be treated as
  executable supply-chain claims with provenance, security obligations, tests,
  and runtime monitors. This is more useful than another AI-text detector.
- 🤖 Why now: `Retrieval Collapse` reports synthetic sources can dominate
  retrieval exposure; LLM-generated web-app studies report exploitable auth,
  session, validation, XSS, upload, and HTTP-header failures; AI SEO/content
  spam changes what web-grounded agents see.
- 🤖 Evaluation sketch: crawl a volatile topic daily, classify source types,
  archive evidence, and test whether agent answers shift toward synthetic or
  stale evidence. For generated artifacts, generate sites, attach obligations,
  run security checks, and measure review/repair quality.

🤖 See `literature_directions.md` candidate 4 and candidate 5 for the
question-first versions of these ideas.

## Web Dependency

- [Poster: Web Dependency Analyzer to Identify Resource Dependencies and
    their Impact on Rendering](https://dl.acm.org/doi/10.1145/3646547.3689683),
    Yasin Alhamwy, Paul Mertens, Oliver Hohlfeld, IMC, 2024
    - which domain provide which assets, contribute how much to
        rendered content
    - ablation: what happens to rendering when block some domains (or down)

## Phishing

- [Phishing in the Free Waters: A Study of
    Phishing Attacks Created using Free Website Building
    Services](https://dl.acm.org/doi/pdf/10.1145/3618257.3624812),
    Sayak Saha Roy, Unique Karanjit, Shirin Nilizadeh, IMC, 2023
    - description of free website buildin### browser_agent.md
# Browser Agent

- [WebVoyager: Building an End-to-End Web Agent with
    Large Multimodal Models](https://arxiv.org/abs/2401.13919), Hongliang He,
    Wenlin Yao, Kaixin Ma, Wenhao Yu, Yong Dai, Hongming Zhang, Zhenzhong Lan,
    Dong Yu, ACL, 2024
    - vision-first end-to-end web agent on real websites
    - useful mainly bc benchmark uses real rendered sites,
        not static snapshots
    - good historical starting point;
        later papers usually have sharper systems ideas
- [Towards Specialized Web Agents Using Production-Scale Workflow
    Data](https://arxiv.org/abs/2411.15004), Junhong Shen, Atishay Jain,
    Zedian Xiao, Ishan Amlekar, Mouad Hadji, Aaron Podolny, Ameet Talwalkar,
    arXiv, 2024
    - main claim: real workflow data + finetuning matter more than
        prompt engineering
    - paper reports specialized open models can beat proprietary baselines
    - good paper if you care about data + training,
        not just inference-time scaffolding
- [AgentOccam: A Simple Yet Strong Baseline for
    LLM-Based Web Agents](https://openreview.net/pdf?id=oWdzUpOlkX), Ke Yang,
    Yao Liu, Sapana Chaudhary, Rasool Fakoor, Pratik Chaudhari, George Karypis,
    Huzefa Rangwala, ICLR, 2025
    - simple but important: align action space + observation space to
        model priors
    - remove low-value actions, compress page, use planning-tree memory
    - nice "simplicity wins" baseline
- [Navigating the Infinite Dynamic Web Space:
    Effective In-Context Exploration via
    Cognitive Multi-Agent
    Collaboration](https://aclanthology.org/2026.eacl-long.384.pdf),
    Guozhao Mo, Yanjiang Liu, Yafei Shi, Jiawei Chen, Yang Li, Yaojie Lu,
    Hongyu Lin, Ben He, Le Sun, Bo Zheng, Xianpei Han, EACL, 2026
    - split "history": environment observation vs action trajectory
        - 2 separate agent
    - backtrack using "go back" or "go to"
        - to avoid getting stuck/trapped
    - argue state backtrack often impossible bc irreversible actions
        - by citing "Is your llm secretly a world model of the internet?
            model-based planning for web agents"
    - achieve better performance w/ open source than
        previous methods + proprietary LLMs
    - contain good list of prior web agents
- [WebRL: Training LLM Web Agents via
    Self-Evolving Online Curriculum Reinforcement
    Learning](https://arxiv.org/abs/2411.02337v1), Zehan Qi, Xiao Liu,
    Iat Long Iong, Hanyu Lai, Xueqiao Sun, Jiadai Sun, Xinyue Yang, Yu Yang,
    Shuntian Yao, Wei Xu, Jie Tang, Yuxiao Dong, ICLR, 2025
    - online curriculum RL for open web agents
    - tackles task scarcity, sparse rewards, and unstable online training
    - paper reports a large jump on WebArena-Lite; read if
        you care about training agents
- [WebCoach: Self-Evolving Web Agents with
    Cross-Session Memory Guidance](https://arxiv.org/abs/2511.12997),
    Genglin Liu, Shijie Geng, Sha Li, Hejie Cui, Sarah Zhang, Xin Liu,
    Tianyi Liu, arXiv, 2025
    - adds cross-session episodic memory w/o retraining
    - condenser + memory store + runtime coach retrieve past lessons
    - good "memory helps" paper; more practical than foundational
- [Building Browser Agents: Architecture, Security, and
    Practical Solutions](https://arxiv.org/abs/2511.19477v1), Aram Vardanyan,
    arXiv, 2025
    - strongest point is architectural / security perspective,
        not benchmark novelty
    - paper argues prompt injection makes open-ended browser autonomy unsafe
        in production
    - pro specialized constrained tools, anti general browser-first agent
- [BrowserAgent: Building Web Agents with
    Human-Inspired Web Browsing Actions](https://arxiv.org/abs/2510.10666v2),
    Tao Yu, Zhengbo Zhang, Zhiheng Lyu, Junhao Gong, Hongzhu Yi, Xinming Wang,
    Yuxuan Zhou, Jiabing Yang, Ping Nie, Yan Huang, Wenhu Chen, arXiv, 2025
    - pushes direct browser interaction instead of converting web to
        static text
    - staged finetuning + explicit memory
    - seems more useful for browse-for-information / open QA than
        transactional web tasks
- [Prune4Web: DOM Tree Pruning Programming for
    Web Agent](https://arxiv.org/abs/2511.21398), Jiayuan Zhang, Kaiquan Chen,
    Zhihao Lu, Enshen Zhou, Qian Yu, Jing Zhang, AAAI, 2026
    - nice low-level idea: use generated program to
        prune DOM before grounding
    - paper reports a large grounding boost by
        shrinking candidate elements aggressively
    - read if you care about DOM/action grounding details
- [Investigating the Impact of Dark Patterns on
    LLM-Based Web Agents](https://arxiv.org/abs/2510.18113v1), Devin Ersoy,
    Brandon Lee, Ananth Shreekumar, Arjun Arunasalam, Muhammad Ibrahim,
    Antonio Bianchi, Z. Berkay Celik, IEEE S&P, 2026
    - paper positions itself as a first systematic dark-pattern eval for
        web agents
    - paper reports stronger agents can be more vulnerable bc they bulldoze
        through UI traps
    - paper reports vision can hurt and
        prompt countermeasures help only a bit
- [From Super-Apps to Agent Economies:
    Delegated AI Requires Transaction
    Closure](https://www.preprints.org/manuscript/202604.1860), Chaoyue He,
    Xin Zhou, Di Wang, Hong Xu, Wei Liu, Chunyan Miao, preprints.org, 2026
    - position paper, not core web-agent algorithm paper
    - main idea: judge agent systems by transaction closure,
        not just task completion
    - useful for governance / ecosystem framing
- [WebOperator: Action-Aware Tree Search for Autonomous Agents in
    Web Environment](https://arxiv.org/abs/2512.12692), Mahir Labib Dihan,
    Tanzima Hashem, Mohammed Eunus Ali, Md Rizwan Parvez, arXiv, 2026
    - ICLR 2026 Rejected
        - "most of the individual components have been explored in
            prior work"
    - still useful: explicit safe/speculative backtracking is the key idea
    - best-first tree search ranks actions by reward + safety, then
        filters / merges actions
    - paper claim### JSphere
classification_results.md
eval_trick.md
execution.md
literature.md
notable_apis.md
popular_api_calls_analysis.md
sketch.md
youtube_scripts_api_calls_overview.md
# Classification Results
# The eval Trick
# Execution
# Literature
# Notable APIs
# Analysis of popular API calls
# JSphere
# Analysis of selected YouTube scripts API calls
### DeGenTWeb
ad_extraction.md
arguments.md
baseline_sites.md
CHANGELOG.md
classifying_site.md
common_crawl.md
deprecated.md
execution.md
filter_non_article.md
google_trends.md
# Ad Extraction
# Arguments
# Baseline Websites
# Changelog
# Classifying Websites
# Common Crawl
# Deprecated
# DeGenTWeb
# Filter out Non-Article
# Google Trends
# Literature
# Preliminary Binoculars Evaluation
### c2pa
camera_apps.md
gen_ai_problems.md
papers.md
peripheral_literature.md
# C2PA Camera Apps Investigation

"Click", "Capture Cam" and "ProofMode" in [Peripheral Literature for
C2PA](peripheral_literature.html#c2pa-implementation). Photos taken:

| Click        | Capture Cam                                                   | ProofMode  |
| ------------ | ------------------------------------------------------------- | ---------- |
| [1733499304] | [bafybeiaq7b5fyime2l3lb6niajrmksfipe26r2rycxius3twog7vcarjma] | [IMG_4717] |

## Signers and public key

<details><summary>
Click issued a certificate through ContentSign for me, presumably by
adding a reference on the blockchain.
</summary>

```sh
$ c2patool --certs 1733499304.jpg | openssl x509 -text -noout
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 7991087401548139538 (0x6ee60ba732604c12)
        Signature Algorithm: ecdsa-with-SHA256
        Issuer: CN=Click Camera, O=ContentSign by Nodle
        Validity
            Not Before: Dec  6 15:31:26 2024 GMT
            Not After : Dec  6 15:31:26 2025 GMT
        Subject: CN=0xF0Ed23507BC598b1eA0FdB7c31517B26538829F9, O=Click Camera
        Subject Public Key Info:
            Public Key Algorithm: id-ecPublicKey
                Public-Key: (256 bit)
                pub:
                    04:ad:da:20:bd:92:b7:95:e9:7c:82:0f:51:b6:79:
                    6b:35:4c:44:27:d1:04:83:f8:fa:10:84:40:8c:b1:
                    73:35:75:f8:59:1b:d9:f6:7a:ab:be:7d:90:21:4d:
                    c0:98:40:fd:5c:3a:ab:bf:48:5b:08:7d:2b:f7:3e:
                    87:3a:7b:f2:63
                ASN1 OID: prime256v1
                NIST CURVE: P-256
        X509v3 extensions:
            X509v3 Basic Constraints: 
                CA:FALSE
            X509v3 Key Usage: critical
                Digital Signature, Key Encipherment
            X509v3 Extended Key Usage: 
                TLS Web Client Authentication, E-mail Protection
            X509v3 Subject Key Identifier: 
                13:5D:2D:9D:71:F0:A5:D5:17:41:0E:79:29:C5:2C:35:13:1F:46:DC
            X509v3 Authority Key Identifier: 
                keyid:4C:F9:B3:FD:D5:E6:6B:C3:0D:EB:2C:0E:53:AF:2B:22:30:B5:DA:0F
                DirName:/O=Click App/CN=Click App ContentSign CA 1
                serial:8C:DF:B9:CC:33:D1:F8:58:97:28:5C:95:14:C5:38:2D:CF:80:63
    Signature Algorithm: ecdsa-with-SHA256
    Signature Value:
        30:46:02:21:00:8a:72:fe:22:a4:67:84:20:b8:90:e7:b9:2a:
        36:b2:4a:bf:5d:f8:1a:56:f8:89:30:82:b8:0f:ab:6a:4a:ae:
        c2:02:21:00:92:e4:ef:6f:2f:41:a0:54:81:19:f9:89:f1:3c:
        ea:02:ef:11:4f:4b:0d:02:a6:68:6e:e3:72:14:63:fe:6e:81
```

</details>

- must have how changed C2PA verify works

<details><summary>
Capture Cam seems to reuse its own pubkey w/ certificate issued by DigiCert.
</summary>

```sh
$ c2patool --certs bafybeiaq7b5fyime2l3lb6niajrmksfipe26r2rycxius3twog7vcarjma.jpg | openssl x509 -text -noout
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number:
            0c:59:4a:96:f5:77:2e:e9:55:f3:02:4b:21:98:82:86
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: C=US, O=DigiCert Inc, OU=www.digicert.com, CN=DigiCert Assured ID Client CA G2
        Validity
            Not Before: Feb 26 00:00:00 2024 GMT
            Not After : Feb 26 23:59:59 2025 GMT
        Subject: organizationIdentifier=NTRTW-82885990, C=TW, ST=Taipei City, O=Numbers Co., Ltd., SN=Chen, GN=Bofu, CN=Bofu Chen
        Subject Public Key Info:
            Public Key Algorithm: id-ecPublicKey
                Public-Key: (384 bit)
                pub:
                    04:c2:4e:fc:1a:84:99:0c:4e:43:03:40:87:ed:86:
                    96:a6:ed:14:22:99:dd:b6:86:e5:98:a1:30:6f:e0:
                    25:7d:71:08:78:86:ff:7e:68:d3:1d:a3:ac:43:67:
                    90:3e:dd:de:49:d1:5f:64:0e:92:7e:48:17:d2:ce:
                    cb:f2:a2:b1:e8:fd:08:81:78:6e:49:2c:b6:45:0b:
                    e5:a7:16:d4:87:ef:39:fd:e0:c3:1b:de:61:73:7b:
                    81:58:ec:bc:f5:d6:65
       ## Surprising findings in this project so far (inspiration)
- proofs that found real bugs by failing to go through (e.g. in JS engines Boa/Servo/Lightpanda, URL parsing)
- proofs that survived real upstream behavior changes
- integer-width gaps between the JS spec (ESMeta) and engine implementations
- Lightpanda (headless browser) rule bugs
- web archives replaying pages wrong
- monotone security facts across restore paths (bfcache, session restore)
