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
