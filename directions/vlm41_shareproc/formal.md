# Prior work on in-process isolation with formal guarantees
(authored by agents)

Question: many browser or agent sessions in one process, provably one never sees another's data.
Labels: [F] fact quoted from the paper text I read (PDF saved in paper_collection, or the fetched abstract page); [I] my inference.
Builds on /hdd1/sichangheagent/vl_meeting_work/out/vlm10_share/prior_work.md (not repeated: Icarus, Hodor/ERIM blurbs, Cloudflare posts, Hydra, HypoVisor, Kilger 2026). Scholar was not used this time (no CAPTCHA risk); papers were located by WebSearch and read from PDFs.
Not found: a paper that proves isolation between many mutually distrusting tenants inside one engine/process end to end, covering Spectre. See "Bottom line".

## Bottom line
- [I] Proofs exist for pieces: the static checker for one sandbox (LFI proof, VeriWasm, VeriZero), the runtime's system-call layer (WaVe), Wasm compilation (vWasm), a browser kernel's tab and cookie isolation (Quark).
- [I] No proof covers: (a) a JS JIT's output checked for per-tenant regions, (b) the tenant create/destroy lifecycle of the sandbox runtime (WaVe does syscalls, not the runtime's sandbox lifecycle with many live tenants), (c) microarchitectural leaks between tenants.
- [F] Mohabi (2026) is the strongest recent system: its validator checks JIT output, but it is tested not proved, and it confines the engine, not tenants from each other.
- [F] The only Spectre-aware answers are Swivel (Wasm, not proved), LFI (partial, "basic"), and Site Isolation (separate processes).

## 1. SFI lineage

### Wahbe et al., SOSP 1993 (collection: yes)
https://dl.acm.org/doi/10.1145/168619.168635
- isolates: distrusted module inside one address space.
- [F] "we load the code and data for a distrusted module into its own fault domain, a logically separate portion of the application's main address space. Second, we modify the object code of a distrusted module to prevent it from writing or jumping to an address outside its fault domain."
- proved: nothing formal; mechanism and measurements. Trusted: the rewriter/loader.
- not covered: no tenants-vs-tenants threat model beyond "faults"; pre-Spectre.

### Native Client, Yee et al., IEEE S&P 2009 (collection: yes)
- isolates: untrusted x86 code in the browser.
- [F] "Native Client uses software fault isolation and a secure runtime to direct system interaction and side effects through interfaces managed by Native Client."
- proved: it argues control-flow integrity of the validated design ("prove the correctness of our design for controlflow integrity"), pen-and-paper; trusted: validator, runtime.
- not covered: Spectre (predates it); JIT code needed the later NaClJIT/RockJIT work, which Mohabi says used "pre-2015 ... standalone V8 JS engine" and "a 4 GiB memory limit".

### RockSalt, Morrisett et al., PLDI 2012 (collection: already there)
- [F] (Mohabi/VeriWasm cite it as the verified NaCl x86 checker.) VeriWasm: "unlike RockSalt, VeriWasm does not verify correct x86 disassembly."
- [I] first machine-checked SFI validator; fixed 4 GiB sandbox, no JIT.

### LFI, Yedidia, ASPLOS 2024 (collection: yes)
https://dl.acm.org/doi/10.1145/3620665.3640408
- isolates: many sandboxes in one address space (ARM64).
- [F] "supports tens of thousands of 4GiB sandboxes in a single address space and does full software isolation of loads, stores, and jumps with a runtime overhead of 7%" ... "has a small static verifier to reduce TCB size, is hardened against basic Spectre attacks".
- [F] Spectre section: "Sandbox breakout", "Cross-sandbox poisoning", "Host poisoning"; "LFI mitigates sandbox breakout attacks by construction." (the quote is about breakout only; cross-sandbox poisoning needs hardware support, e.g. Arm CSV2_2 "software context numbers", per the same section).
- proved: nothing; the checker is tested. Proof came later (next entry).
- not covered: x86-64 (Mohabi's MH-LFI handles x86), JIT.

### Automated Formal Verification of a SFI System, Sotoudeh and Yedidia, FMCAD 2025 (collection: already there)
https://arxiv.org/abs/2508.15898
- [F] "we formally verify that programs accepted by the LFI verifier never read or write to memory outside of a designated sandbox region."
- [F] "This paper considers only the LFI verifier, and so we assume the LFI runtime is implemented correctly."; "This work did not consider safety of the LFI runtime, which remains an unverified but trusted component of the system."
- [F] "The notion of memory isolation here is more coarse grained than memory safety". Spectre: "Speculation exploits have been discovered, and can be particularly dangerous for SFI systems, which run mutually untrusting code in the same address space."
- proved: per-instruction invariant (SMT, about 20 lines of SMT-LIB2) over ARM64 semantics. Trusted: ARM64 model, runtime, mapping assumptions.
- not covered: runtime, Spectre, cross-sandbox (the property is "outside a designated region"; with disjoint regions per tenant it implies tenant separation [I]).

### VeriWasm, Johnson et al., NDSS 2021 (collection: already there)
- [F] "we propose verifying memory isolation of Wasm binaries post-compilation. ... a static offline verifier for native x86-64 binaries compiled from Wasm; we prove the verifier's soundness". Context: "the Fastly and Cloudflare content-delivery networks (CDNs) use Wasm to isolate different tenants on their edge clouds."
- [F] "We only verify the analysis passes; we do not verify the disassembly, control-flow graph creation, or the translation from x86-64 to w64".
- not covered: "VeriWasm does not verify any part of this runtime"; Spectre not addressed.

### Isolation Without Taxation, Kolosick et al., POPL 2022 (collection: yes)
- [F] "companies like Fastly and Cloudflare use SFI to safely co-locate untrusted tenants on their edge clouds."
- [F] "we (1) develop a static binary verifier, VeriZero, which (in seconds) checks that binaries produced by Lucet satisfy our zero-cost conditions, and (2) prove the soundness of VeriZero by developing a logical relation that captures when a compiled Wasm function is semantically well-behaved".
- proved: soundness of a checker for cheap sandbox transitions. Spectre: [F] "protections from denial of service, speculative execution, and side-channel attacks are orthogonal and out of scope."
- [I] relevant: transition code is where tenant data can leak (registers); proved here for one sandbox at a time.

## 2. Wasm sandboxes

### vWasm and rWasm, Bosamiya, Lim, Parno, USENIX Security 2022 (collection: yes)
https://www.usenix.org/conference/usenixsecurity22/presentation/bosamiya
- [F] "we explore two distinct approaches to producing provably sandboxed Wasm code. One draws on traditional formal methods to produce mathematical, machine-checked proofs of safety. The second carefully embeds Wasm semantics in safe Rust code such that the Rust compiler can emit safe executable code".
- proved: vWasm: compiler output (F*) is sandboxed; rWasm: relies on Rust compiler safety. Trusted: proof tooling, Rust compiler (rWasm), runtime.
- not covered: Spectre (search for "spectre" in the text found none), many-tenant runtime. (Wasmtime itself is not formally proved; no paper read.)

### WaVe, Johnson et al., IEEE S&P 2023 (collection: already there, text only)
- [F] "We mechanically verify that interactions with WaVe (including OS side effects) not only maintain Wasm's memory safety guarantees, but also maintain access isolation for the host OS's storage and network resources." and "the runtime is trusted to correctly set up and tear down Wasm sandboxes" (as the problem statement, not claimed solved: the proof covers the WASI hostcalls).
- proved: WASI call layer (Prusti-verified Rust) with respect to a spec; runtime 4646 LoC untrusted for those properties.
- not covered: timing/Spectre; sandbox set-up/teardown across many tenants is described as trusted context [I: not verified here].

### Swivel, Narayan et al., USENIX Security 2021 (collection: yes)
https://www.usenix.org/conference/usenixsecurity21/presentation/narayan
- [F] "Spectre attacks can bypass Wasm's isolation guarantees. Swivel hardens Wasm against this class of attacks by ensuring that potentially malicious code can neither use Spectre attacks to break out of the Wasm sandbox nor coerce victim code—another Wasm client or the embedding process—to leak secret data." Attacker: "a FaaS platform client who can upload arbitrary Wasm code which the platform will then compile and run alongside other clients".
- proved: nothing formal; assumes "that our Wasm compiler and runtime are correct"; Meltdown/MDS/LVI out of scope; "deterministic implementations impose overheads between 3.3% and 240.2%."
- [I] the only paper here that models tenant-vs-tenant Spectre in one process, by construction not proof.

### RLBox, Narayan et al., USENIX Security 2020 (collection: yes)
- isolates: third-party libraries from the Firefox renderer.
- [F] "RLBox supports efficient sandboxing through either software-based-fault isolation or multi-core process isolation."; type system "static information flow enforcement, and lightweight dynamic checks".
- proved: nothing; tainted types catch missing checks. Not covered: tenants (sandboxes are libraries), Spectre.

## 3. Hardware (MPK and successors)
None proves isolation; they argue by design. [F] checked: ERIM and Hodor texts contain no theorem (grep on "formal/prove" found none relevant).

### ERIM, Vahldiek-Oberwagner et al., USENIX Security 2019 (collection: yes)
- [F] "The key idea is to combine protection keys (MPKs) ... with binary inspection to prevent circumvention." and "up to 16 domains" (from the hardware description).
- not covered: Spectre, more than 16 domains; JIT code is inspected only as the system defines it for loaded binaries [I].

### Hodor, Hedayati et al., USENIX ATC 2019 (collection: yes)
- [F] "current Intel hardware supports only 16 distinct memory keys. The need for a separate key for each of the regions of the 'protection domain Venn diagram' ... thus limits us to no more than 7 mutually distrusting protected libraries in any given application".
- [I] this is the sharpest statement of why plain MPK cannot give one domain per tenant.

### Donky, Schrammel et al., USENIX Security 2020 (collection: yes)
- [F] "efficient hardware-software codesign for strong in-process isolation based on dynamic memory protection domains" with "secure V8 sandboxing" as a use case; "Spectre attacks [40] are outside our threat model".
- not covered: formal proof; needs new RISC-V hardware.

### TME-Box, Unterguggenberger et al., NDSS 2025 (collection: yes)
https://arxiv.org/abs/2407.10740
- [F] "memory safety errors pose a significant security threat by allowing an adversary to extract or corrupt the private data of other colocated tenants. ... MPK's 16 protection domains are insufficient to isolate thousands of cloud workers per process." Supports "up to 32K concurrent sandboxes"; overhead "5.2 % for data isolation and 9.7 % for code and data isolation".
- not covered: formal proof; compiler instrumentation is in the TCB [I: stated approach "through compiler instrumentation"].

### Dynamic Process Isolation, Schwarzl et al., arXiv 2021 (collection: yes)
- [F] "it is possible to mount a Spectre attack on such a restricted environment, leaking secrets from co-located tenants."
- [I] shows in-process tenant isolation without Spectre defence fails in production; informal.

## 4. Verified or formal browser designs

### Quark, Jang, Tatlock, Lerner, USENIX Security 2012 (collection: already there)
https://goto.ucsd.edu/quark/
- isolates: tabs, via a Coq-verified kernel with each tab in its own process.
- [F] "We only formally prove inter-domain cookie isolation. Even this coarse guarantee prohibits a broad class of attacks, e.g., it protects all Google cookies from any non-Google tab." Also tab non-interference, address-bar integrity.
- [F] Trusted base: "Coq's core calculus and type checker; Our formal statement of the security properties; ... The Ocaml compiler and runtime; The underlying Operating System kernel; Our chroot sandbox"; effort: "we guaranteed our security properties for a million lines of code by reasoning just 859."
- [F] limit: "If a subframe is able to exploit the entire tab, then it could steal the cookies of its top-level parent tab ... This limitation arises because tabs are principles in Quark instead of frames."; leaking via GetURL treated "analogous to leaking cookie data over timing channels" (timing channels excluded).
- [I] Quark's isolation is process-per-tab, so it proves the kernel's message policy, not memory isolation. It does not do many sessions in one process. A web search found no direct successor and no machine-checked Site Isolation proof (the 2026 arXiv survey 2607.28551 cites only Quark and Bohannon's Rocq model of Firefox with reactive noninterference; I did not read either, [I] unverified).

### Gazelle, Wang et al., USENIX Security 2009 (collection: yes)
- [F] "Gazelle's browser kernel is an operating system that exclusively manages resource protection and sharing across web site principals." Each principal is a separate OS process. No proof; design and prototype, C# kernel of about 5,000 lines (per the search summary, [I] not re-checked in text).

### IBOS, Tang, Mai, King, OSDI 2010 (collection: yes)
- [F] "a new operating system and a new browser that reduces the trusted computing base for web browsers ... mapping browser abstractions to hardware abstractions directly." No formal proof; each app gets hardware-level separation, not in-process.

### Site Isolation, Reis, Moshchuk, Oskov, USENIX Security 2019 (collection: yes)
- [F] "it is no longer safe to render documents from different web sites in the same process. ... Site Isolation locks each renderer process to documents from a single site and filters certain cross-site data from each process."
- [F] "We find that this architecture offers the best path to protection against compromised renderer processes and same-process transient execution attacks, despite current limitations."
- no formal model; threat model is renderer exploit plus memory disclosure. Boundary is the site, so same-site tabs share a process [I]. Process count is the cost, the reason in-process designs are attractive.

### Site Isolation is Dead, Lee et al., IEEE S&P 2026 (collection: yes)
- [F] "privileged processes manage user prompts and agent operations, while untrusted renderer processes are isolated, with inter-process communication (IPC) channels serving as their bridge. ... all tested agentic browsers and extensions are vulnerable to these attacks, revealing that existing implementations often fail to properly account for IPC channels."
- [I] lesson for the design: the proof boundary must include the agent/tool channel that crosses tenants; memory isolation alone is not the property users want. Not a formal paper; an attack study of two browsers and seven extensions.

## 5. Mohabi (OSDI 2026) in detail (collection: yes)
https://www.usenix.org/conference/osdi26/presentation/sharma
- isolates: SpiderMonkey instances from the rest of Firefox, with JIT code inside the sandbox.
- [F] "Mohabi leverages software-based fault isolation (SFI) to ensure JavaScript engine bugs cannot affect the rest of the browser." "even if the JS engine is compromised, it is confined, and cannot arbitrarily corrupt memory in the rest of the browser or invoke disallowed system calls".
- [F] JIT: "MH-LFI provides a separate validator to check that all sandboxed code has been correctly instrumented. This allows us to ensure that SFI instrumentation added by the JIT and AOT compilers is correct, removing the compilers from the trusted computing base (TCB)." and "the runtime always checks compiled code using the binary validator before it is copied into" executable memory.
- [F] TCB: "the MH-LFI runtime, MH-LFI validator and data sanitizers at the sandbox boundary": runtime 6,200 lines of C, validator 991 lines of C plus the Fadec decoder (1,894-line table and 1,276 lines of C), 650 plus 80 lines of C++ for sanitizers.
- [F] proof status: "SFI runtimes and validators have been shown to be formally verifiable by prior work [88, 89, 99], and could enable further TCB reduction." So Mohabi's own validator is not proved.
- [F] not covered: sanitizer "does not cover the full JSAPI interface"; WebAssembly is "treated as effectively unsandboxed". The text has no "Spectre" and no tab or origin separation beyond engine-vs-browser (grep: no hits for spectre, per-tab, per-origin).
- [F] contrast with industry: "V8's Ubercage and Safari's JITCage have so far been unsound and frequently bypassed"; Ubercage "has proposals ... a binary validator [75] ... that ensures JIT-compiled code can never violate sandboxing guarantees".
- [I] Gap to the target question: Mohabi gives one cage per engine instance. Many sessions per engine (or per process) would need one cage per session, with LFI's "tens of thousands" of sandboxes as the substrate, and the unproved validator proved by extending the 2025 LFI proof to x86-64 and JIT code.

## 6. Other recent items noticed (not read)
- [F, abstract-level via search] WAVEN, NDSS 2025: Wasm instances of several users share one SGX enclave. https://www.ndss-symposium.org/wp-content/uploads/2025-746-paper.pdf (not downloaded).
- [F, via search summary] arXiv 2509.11242 (2025), resource-isolation attack surface of Wasm containers. Not read.
- TickTock, SOSP 2025 (collection: already there): verified process isolation for the Tock embedded OS (MPU-based, Rust, Flux). [F] first page: Tock "relies on memory protection units (MPUs) to ensure that each user process can only access its own region of memory". [I] a template for a proof of a memory-isolation allocator/lifecycle, the missing item (b) above; the settings differ (MPU, kernel, not JIT code).

## Gap checklist for "provably one never sees another's data"
- checker proved for a fixed region: yes (LFI proof, VeriWasm, VeriZero).
- checker proved for JIT output with per-tenant regions: no paper found.
- sandbox runtime lifecycle proved (alloc, free, reuse of tenant memory): WaVe covers syscalls only; none found for the lifecycle [I].
- tenant switch: VeriZero proves transitions for one design.
- more than 16 tenants in hardware: TME-Box (not proved), LFI (software).
- Spectre between tenants: Swivel (Wasm), LFI (partial), process split (Site Isolation, DPI); none proved.
- channels outside memory (agent IPC, tools, cookies from frames): Quark and "Site Isolation is Dead" show these break the property first.
