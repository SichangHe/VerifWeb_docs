# Prior work on sharing one OS process across mutually distrusting tenants or tabs
(authored by agents unless marked 🧑)

Labels: [F] fact, quoted from a page I fetched; [I] inference; [O] opinion.
Scholar result pages: `scholar/q1..q10.txt`, `scholar/s_*.json`, `scholar/c_*.json` (cited-by lists). Publisher pages: `scholar/u_*.json`, `a_*.json`, `w_*.json`.
Limits: a Google Scholar CAPTCHA (`challenge_action_required`) appeared after about 12 fetches; I did not bypass it. Not fetched because of it: Scholar cited-by of Mohabi, and Scholar pages for Hodor, VeriWasm, LFI, RLBox, Swivel (publisher pages for Hodor, Swivel, RLBox were fetched instead). PDF text extraction returned empty, so quotes come from abstracts, Scholar snippets and blog pages, not paper bodies. "Cited by" counts below are the Scholar numbers shown in the fetched pages.

## Verdict on the two ChatGPT claims
Icarus: exists, but the claim is partly wrong.
- [F] Smith, Sharma, Renner, Thien, Brown, Shacham, Jhala, Stefan, SOSP 2024, https://dl.acm.org/doi/abs/10.1145/3694715.3695949 : "We present Icarus: a new framework for implementing JIT compilers that are automatically, formally verified to be safe, and which can then be converted to C++ that can be linked into browser runtimes." and "We evaluate Icarus by using it to re-implement components of Firefox's JavaScript JIT."
- [I] It verifies the JIT implementation once, so all generated code is safe. It is not a checker run on each JIT output, and it targets language memory safety, not isolation between tenants. So it is not the same as my direction 2 (output checker with per-tenant cages), but it is the closest prior work on "prove the JIT, not the output".

Mohabi: exists, and the description is right.
- [F] Sharma et al., OSDI 2026, https://www.usenix.org/conference/osdi26/presentation/sharma : "Mohabi leverages software-based fault isolation (SFI) to ensure JavaScript engine bugs cannot affect the rest of the browser." and "Mohabi only incurs modest overheads on common benchmarks—24.82% on JetStream and 24.43% on Speedometer."
- [I] It isolates the whole SpiderMonkey from the browser, in one sandbox. The abstract says nothing about separating tenants or tabs from each other inside the engine; I did not read the paper body.

## 1. Intra-process isolation with hardware (MPK / PKU and relatives)
- ERIM, Vahldiek-Oberwagner et al., USENIX Security 2019 (cited by 425), https://www.usenix.org/conference/usenixsecurity19/presentation/vahldiek-oberwagner
  - [F] "The key idea is to combine protection keys (MPKs), a feature recently added to x86 that allows protection domain switches in userspace, with binary inspection to prevent circumvention."
  - why: the baseline MPK design; binary inspection for `WRPKRU` is what an MPK JIT checker must replicate.
- Hodor, Hedayati et al., USENIX ATC 2019 (cited by 75), https://www.usenix.org/conference/atc19/presentation/hedayati-hodor
  - [F] "if applications are mutually distrusting, then either each application must have exclusive access to its own device or else the device itself must implement resource management."
  - why: MPK for mutually distrusting applications sharing one process's libraries.
- Donky, Schrammel et al., USENIX Security 2020 (cited by 184), Scholar q2 result (usenix.org)
  - [F] (Scholar snippet) "We design memory protection keys from the ground up on RISC-V and repurpose the RISC-V N extension to implement secure call gates in userspace."
  - why: fixes MPK limits (few keys) with new hardware.
- EPK, Gu et al., USENIX ATC 2022 (cited by 75), Scholar q2: title "{EPK}: Scalable and efficient memory protection keys".
  - [F] title only; abstract not fetched.
  - why: MPK has about 16 keys, so many-tenant use needs virtualized keys.
- TME-Box, Unterguggenberger, Lamster, Schrammel, Schwarzl, Mangard, NDSS 2025, https://arxiv.org/abs/2407.10740 (via arXiv search page)
  - [F] "Without heavy-weight process isolation, memory safety errors pose a significant security threat by allowing an adversary to extract or corrupt the private data of other co-located tenants. Existing in-process isolation mechanisms are not suitable for modern cloud requireme…" (truncated in the page)
  - why: states the exact multi-tenant problem and proposes memory encryption keys instead of MPK.
- SpecMPK, Adak, Zhou, Rotenberg et al., 2025 (cited by 8), Scholar q2.
  - [F] title: "Specmpk: Efficient in-process isolation with speculative and secure permission update instruction".
  - why: hardware change for fast `WRPKRU`; shows MPK switch cost and speculation are open.
- ThreadLock, Blair, Robertson, Egele, CCS 2023, Scholar q2: "Native principal isolation through memory protection keys".
  - [F] title only.
  - why: per-principal MPK in native code.
- Nojitsu, Park, Dhondt, Gens, Na, Volckaert, Franz, NDSS 2020, Scholar q6.
  - [F] "…’s Memory-Protection Keys to secure SpiderMonkey against existing and newly synthesized …" (snippet is cut)
  - why: MPK inside a JS engine to separate JIT code regions; closest MPK-in-SpiderMonkey work, but about attacker vs. engine, not tenant vs. tenant.
- Hardware-assisted fault isolation, Narayan, Garfinkel, Taram et al., IEEE Micro 2024, Scholar q9.
  - [F] "…it allows the creation of isolated “sandboxes” … -switch overheads, slow cold starts, and scaling limitations. … If used efficiently, 128 TiB can support quite a lot of serverless …"
  - why: argues for hardware-assisted in-process sandboxes for serverless; framing paper for this whole area.

## 2. Software fault isolation (SFI), Wasm sandboxes, and verified checkers
- RLBox, Narayan et al., USENIX Security 2020 (cited by 165), https://www.usenix.org/conference/usenixsecurity20/presentation/narayan
  - [F] "RLBox supports efficient sandboxing through either software-based-fault isolation or multi-core process isolation."
  - why: production Firefox SFI for libraries; tenants are libraries, not websites.
- VeriWasm, Johnson, Thien, Alhessi, Narayan et al., NDSS 2021 (cited by 80), Scholar q7 (title "Доверяй, но проверяй: SFI safety for native-compiled Wasm").
  - [F] (via McLoughlin et al., Scholar q7) "VeriWasm [34] does not verify a compiler, but instead verifies that individual binaries compiled from Wasm do preserve the sandbox…"
  - why: the only existing post-hoc checker of machine code for a sandbox; it checks ahead-of-time Wasm output, not JS JIT output.
- WaVe, Johnson, Laufer, Zhao, Gohman et al., IEEE S&P 2023 (cited by 44), Scholar q3/q7.
  - [F] "When combined with a binary verifier like VeriWasm or with a verified Wasm compiler (or …" (truncated)
  - why: verifies the runtime that manages sandboxes, the "tenant-switch" layer in my direction 1, for Wasm.
- LFI proof, Sotoudeh and Yedidia, FMCAD 2025, https://arxiv.org/abs/2508.15898
  - [F] "we formally verify that programs accepted by the LFI verifier never read or write to memory outside of a designated sandbox region."
  - why: a proven verifier for a fixed sandbox region; my checker idea would have to generalize it to many regions chosen at run time.
- Isolation without taxation, Kolosick, Narayan et al., POPL 2022 (cited by 67).
  - [F] (Scholar q7) "We prove that compiled and verified Wasm …" (truncated); the abstract is not in my fetches.
  - why: cheap sandbox transitions; relevant because tenant switch cost dominates.
- CompCertSfi, Besson, Blazy, Dang, Jensen, Wilke, ESOP 2019 (cited by 26), Scholar q3.
  - [F] "We have presented CompCertSfi, a formally verified implementation of Software Fault Isolation based on the CompCert compiler."
  - why: earlier verified SFI, for AOT compiled C, not JITs.
- Provably-safe multilingual sandboxing with Wasm, Bosamiya, Lim, Parno, USENIX Security 2022, Scholar q7. [F] title only. Why: verified Wasm-based sandbox toolchain.
- Empirical Security Analysis of SFI through Controlled Fault Injection, Bars, Bernhard, Schloegel, Holz, 2025, Scholar q3/q6.
  - [F] "This framework is used by the Mozilla Firefox browser to isolate third-party libraries by executing them in a WebAssembly sandbox."
  - why: shows SFI sandboxes can be broken in practice; evidence for needing verified checkers.

## 3. JIT correctness and sandboxing a JS engine
- Icarus, see verdict above. Cited by 6; citers include Mohabi (Scholar `c_icarus.json`).
- Mohabi, see verdict above. Scholar `c_icarus.json` lists it as a citer of Icarus.
- Sandboxing the Firefox JIT compiler, A. Kannan, UT Austin thesis 2025, Scholar q6.
  - [F] "focus on contiguous memory, Spidermonkey’s (Firefox’s JavaScript engine) … problem. In order to contiguously allocate the JavaScript heap(s), we must first understand Spidermonkey…"
  - why: the memory-layout work that precedes Mohabi.
- Verifying JavaScript JIT Compilers, D. Vos, Utrecht thesis 2026, Scholar q5.
  - [F] "We use the … an ICARUS verification note for each of our CacheIR generator methods."
  - why: someone is extending Icarus to more of SpiderMonkey.
- Translation validation for the V8 JIT, Kwon, Kwon, Kang, Lee, Heo, ISSTA 2024 (cited by 50), Scholar q5.
  - [F] "…(JIT compiler of V8) as SMT encoding. For efficient validation, we design a staged strategy for JS JIT compilers."
  - why: per-compilation checking for V8 (correctness, not isolation).
- JITBULL, Decourcelle, Teabe, Hagimont, IEEE DSN 2024, Scholar q6.
  - [F] title: "Securing JavaScript Runtime with a Go/No-Go Policy for JIT Engine"
  - why: policy gate on JIT use; related to runtime JIT policy.
- War on JITs survey, Ducasse, Cotret, Lagadec, ACM Computing Surveys 2025, in ERIM cited-by list (`c_erim.json`).
  - [F] title: "War on JITs: Software-Based Attacks and Hybrid Defenses for JIT Compilers-A Comprehensive Survey"
  - why: starting survey for JIT defenses.
- V8 sandbox, https://v8.dev/blog/sandbox
  - [F] "A clear attacker model: it is assumed that an attacker can read and write arbitrarily inside the V8 Sandbox. The goal is to prevent memory corruption outside of the sandbox."
  - why: sandbox is one per isolate heap and protects the process, not other tenants in it. Not a peer-reviewed paper.

## 4. Production multi-tenant isolates and process sharing
- Cloudflare Workers security model, https://developers.cloudflare.com/workers/reference/security-model/
  - [F] "Importantly, this means Cloudflare can run many isolates within a single process."
- Cloudflare hardening blog, https://blog.cloudflare.com/safe-in-the-sandbox-security-hardening-for-cloudflare-workers/
  - [F] "we assume that the attacker does not have the ability to execute arbitrary machine code. If they did, they could disable memory protection keys."
  - why: states the MPK threat boundary that a JIT output checker would address.
- Faasm, Shillaker and Pietzuch, ATC 2020 (cited by 545), Scholar q1.
  - [F] "software-based isolation using WebAssembly and V8 Isolates, … of softwarebased isolation alone does not isolate resources."
  - why: Wasm in-process isolation for stateful serverless.
- TinyKVM, Walla, Rowe, 2026, Scholar q1/q4.
  - [F] "…, making V8 isolates unsuitable for per-request isolation. While V8 does not support process forking…"
  - why: alternative: fork-like per-request VM isolation.
- HypoVisor, Neugschwandtner, Horn, Fiedor et al., 2026, Scholar q1.
  - [F] "for intra-process memory isolation: ERIM [23] and Hodor [12] isolate … Isolation Substrates Cloudflare Workers [1] leverage the V8 …"
  - why: 2026 work on multi-tenant native code in one process; cites ERIM, Hodor and Workers.
- Hydra, Ivanenko, Lanko, Horn, Jovanovic, 2025 (cited by 6), Scholar q9.
  - [F] "isolates, which we extend to support on-demand sandbox cre… as well as in-process memory sandboxes, which are faster to …"
  - why: same group (Horn, Fiedor) as HypoVisor; multi-language high-density runtime.
- Memory, Address Spaces, Intra-Process-Isolation and Noodles, N. Hossle, ETH thesis 2025, Scholar q1.
  - [F] "intended for lightweight multi-tenant serverless platforms. … a suspicious email is running in one process while the pdf viewer … Javascript Engine V8 [91]’s so called isolates to isolate each …"
  - why: thesis surveying this exact design space; read for more citations.
- Nano-MCP, Goumih, Dalli, 2026, Scholar q1.
  - [F] "Every isolate is hosted in a single process, has a completely …"
  - why: applies V8 isolates to AI-agent tool execution; a new use of the same sharing.

## 5. Browser process sharing and site isolation
- Site Isolation, Reis, Moshchuk, Oskov, USENIX Security 2019 (cited by 192), https://www.usenix.org/conference/usenixsecurity19/presentation/reis
  - [F] "it is no longer safe to render documents from different web sites in the same process."
  - why: the decision this topic argues against; includes the memory-overhead evaluation.
- Spook.js, Agarwal, O'Connell, Kim et al., IEEE S&P 2022 (cited by 56), Scholar q8.
  - [F] title: "Attacking Chrome strict site isolation via speculative execution"
  - why: even separate processes leak via Spectre when sites share a process (same-site).
- State of Browser Process-Isolation: The Same-Site Weakness, Kilger, Fischer, Staeves et al., IEEE S&P 2026, Scholar q8.
  - [F] "that all browsers implementing site isolation also isolate by … websites opened in private browsing mode never share a …"
  - why: 2026 measurement; shows site isolation grain is coarse.
- Isolated and Exhausted, Gierlings, Brinkmann, Schwenk, USENIX Security 2023, Scholar q8.
  - [F] "Since each process induces overhead in the OS, Site Isolation in Chrome has been …"
  - why: process-per-site cost is an attack surface itself.
- Site Isolation is Dead: Site Isolation in Agentic Browsers and Extensions, Lee, Keum, Lee et al., IEEE S&P 2026, Scholar q10.
  - [F] "two open-source agentic browsers and seven Chrome extensions that integrate LLM …"
  - why: agent tools reintroduce shared-process trust problems.
- JSIsolate, Zhang and Meng, 2021, Scholar q8.
  - [F] "current browser architecture allows all scripts to access a shared …"
  - why: in-browser JS isolation within a page.

## 6. Spectre in multi-tenant JS and Wasm
- Dynamic Process Isolation, Schwarzl, Borrello, Kogler, Varda, Schuster, Gruss, Schwarz, arXiv 2110.04751 (cited by 49 per `c_dpi.json`), https://arxiv.org/abs/2110.04751
  - [F] "we show that it is possible to mount a Spectre attack on such a restricted environment, leaking secrets from co-located tenants." and "Dynamic Process Isolation, a process isolation mechanism that only isolates suspicious worker scripts following a detection mechanism."
  - why: the defense deployed in Workers.
- Cloudflare 2026, "A revisit of remote Spectre attacks on Cloudflare Workers", https://blog.cloudflare.com/revisiting-spectre-attacks-on-workers/ (page dated August 19, 2026)
  - [F] "we managed to demonstrate a remote Spectre attack reliably leaking up to 12 bit/s with a 99% accuracy in the production environment of Cloudflare Workers." and "we improved DyPrIs, integrated the V8 Sandbox and an in-process isolation mechanism to further reduce the risk of memory disclosure attacks."
  - why: shows detection-based isolation was bypassed and that Cloudflare now layers in-process isolation.
- Remote-Timer-as-a-Service, Schwarzl, Xiao, Pedersen, Ainsworth, Topham, Schwarzl, arXiv 2026 (paper behind the blog), Scholar q4.
  - [F] "In a singleprocess-multi-tenant systems, Spectre [38] …"
  - why: the 2026 attack paper; abstract was not fetched (the arXiv search fetch failed).
- Swivel, Narayan, Disselkoen, Moghimi et al., USENIX Security 2021 (cited by 132), https://www.usenix.org/conference/usenixsecurity21/presentation/narayan
  - [F] "Spectre attacks can bypass Wasm's isolation guarantees. Swivel hardens Wasm against this class of attacks by ensuring that potentially malicious code can neither use Spectre attacks to break out of the Wasm sandbox nor coerce victim code—another Wasm client or the embedding process—to leak secret data." and "deterministic implementations impose overheads between 3.3% and 240.2%".
  - why: compiler-side Spectre fix for Wasm; no counterpart for JS JIT output.
- Hacky Racers, Xiao and Ainsworth, ASPLOS 2023, in `c_dpi.json`.
  - [F] "Side-channel attacks pose serious threats to many security models, especially sandbox- based browsers."
  - why: timers without clocks; undermines timer-removal defenses.
- Microarchitectural security of Firecracker VMM, Weissman, Tiemann, Eisenbarth, ICISSP 2024, Scholar q4.
  - [F] "We identify Spectre-PHT and Spectre-BTB variants which …"
  - why: even VM-per-tenant leaks; the problem is not limited to in-process.

## Who works on it
- UCSD / UT Austin / Stanford SFI and Wasm group: Deian Stefan, Hovav Shacham, Shravan Narayan, Tal Garfinkel, Evan Johnson, Zachary Yedidia, Craig Disselkoen. [F] They appear as authors of RLBox, VeriWasm, Swivel, WaVe, Hardware-assisted fault isolation, and Mohabi (authors list on https://www.usenix.org/conference/osdi26/presentation/sharma: "Abhishek Sharma and Anand Balaji, The University of Texas at Austin; Zachary Yedidia, Stanford University; ... Iain Ireland, Jan de Mooij, and Matthew Gaudet, Mozilla; Tal Garfinkel, Google; Deian Stefan and Hovav Shacham, University of California, San Diego; Shravan Narayan, The University of Texas at Austin").
- Icarus authors: Smith, Sharma, Renner, Thien, Brown, Shacham, Jhala, Stefan (same group plus Ranjit Jhala, verification). [F] Scholar `s_icarus.json`.
- Max Planck (Peter Druschel, Deepak Garg, Anjo Vahldiek-Oberwagner): ERIM; Vahldiek-Oberwagner is also an author of Swivel and of Pegasus (cited ERIM, `c_erim.json`). [F]
- Graz (Daniel Gruss, Stefan Mangard, Martin Schwarzl, Michael Schwarz): Dynamic Process Isolation, TME-Box, Remote-Timer-as-a-Service; Donky (Schrammel, Weiser, Mangard). Martin Schwarzl co-authors the 2026 Cloudflare post with Albert Pedersen. [F]
- Cambridge/Edinburgh (Sam Ainsworth, Haocheng Xiao, Nigel Topham): Hacky Racers, 2026 remote-timer work. [F]
- Cloudflare (Kenton Varda, Albert Pedersen): production deployment and co-authors. [F]
- Rochester (Hedayati, Criswell, Scott): Hodor. [F]
- USI/Lugano-linked group (Horn, Fiedor, Neugschwandtner, Jovanovic): HypoVisor, Hydra. [I] affiliation not shown in fetched snippets; only names are [F].
- Verified SFI in France (Besson, Blazy, Jensen): CompCertSfi. [F]
- Chrome security (Reis, Moshchuk, Oskov): Site Isolation. [F]

## Open problems
Quotes are the authors' own statements; items without a quote are my inference [I] and marked.
1. Detection-based co-location is not enough.
   - [F] Cloudflare 2026: "Detection cannot happen only after a script finishes. A Durable Object or a WebSocket-heavy Worker can run long enough that post-execution isolation arrives too late."
2. Compiled JIT code can defeat MPK, so MPK alone does not protect tenants from each other.
   - [F] Cloudflare: "If they did, they could disable memory protection keys." (arbitrary machine code assumed absent)
   - [I] No fetched paper checks JS JIT output for per-tenant cages. VeriWasm and LFI check one fixed sandbox of AOT code; Icarus verifies the JIT, not its output per tenant. Not proven absent: I could not search full texts, and the Scholar queries hit a CAPTCHA.
3. Cost of fine-grained isolation is still high for JS.
   - [F] Mohabi: "24.82% on JetStream and 24.43% on Speedometer."
   - [F] Swivel: "deterministic implementations impose overheads between 3.3% and 240.2%."
4. Sandbox grain: one engine versus many tenants.
   - [I] Mohabi isolates the JS engine from the browser; the abstract does not say how multiple tenants or tabs in one engine are separated. Needs a read of the paper body.
5. MPK scale and speculation.
   - [F] EPK is titled "Scalable and efficient memory protection keys" and SpecMPK "Efficient in-process isolation with speculative and secure permission update instruction"; both exist because plain MPK has few keys and a `WRPKRU` that serializes. [I] the explanation of why is from my knowledge, not from the fetched snippets.
6. Spectre defenses for compiled JS.
   - [F] Swivel is only for Wasm: "Spectre attacks can bypass Wasm's isolation guarantees." [I] I found no comparable fetched result for JS JIT output.
7. Verified lifecycle of tenant allocation (keys, pages, teardown).
   - [I] I found no paper on this in the Scholar results; same caveat as item 2.
8. Site Isolation weakness persists at same-site granularity.
   - [F] Kilger et al. 2026 title: "State of Browser Process-Isolation: The Same-Site Weakness".
