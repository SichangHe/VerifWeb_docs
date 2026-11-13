# Group isoB: isolation papers
(authored by agents unless marked 🧑)

Terms. SFI (software fault isolation): code is rewritten or checked so it can only touch its own memory region. MPK (Intel memory protection keys): 16 hardware memory tags per process. TCB (trusted computing base): the code you must trust. Spectre: a CPU speculation side channel.

## 12 Site Isolation is Dead- How Site Isolation is Broken in Agentic Browsers and Extensions, Suyoung Lee, Seongho Keum, Changoo Lee, Dongwon Shin, Sanghyun Hong, Byoungyoung Lee, Sooel Son, IEEE S&P, 2026
- SHOWS: Isolated: untrusted renderer processes (web pages) from privileged background processes that run the LLM agent. Mechanism: Chrome-style OS processes plus message passing (IPC) between them. Domains: not a design paper, so no count. The authors studied 2 open-source agentic browsers and 7 agent extensions, and wrote two attacks from a compromised page process: forged IPC prompts (prompt injection) and reading agent storage over IPC (API keys, chat history, identity). All 9 were vulnerable. No proof; empirical attack study plus 4 defense guidelines. Spectre: not covered.
- QUOTE: "a compromised renderer process can retrieve sensitive entries by issuing IPC requests." (Section 1, Introduction)
- WHY: It shows that process isolation between sites does not protect the agent layer, because the agent must cross sites by design; the agent-to-page channel is the gap our proof must cover.
- PRIORITY: high. Only agentic-browser isolation paper here.
- READ: abstract, introduction, conclusion, grep of attacks and defenses sections (not the full evaluation tables).

## 13 Site Isolation- Process Separation for Web Sites within the Browser, Charles Reis, Alexander Moshchuk, Nasko Oskov, USENIX Security, 2019
- SHOWS: Isolated: web sites from each other, one site per OS renderer process in Chrome (production, all desktop users). Mechanism: OS processes plus a privileged browser process that filters cross-site data (CORB). Domains: one process per site, not capped; process consolidation keeps cost to 9-13% memory overhead. No formal proof. Spectre: yes, discussed; process isolation is the mitigation for same-process Spectre, but the authors say it is not sufficient alone (cross-process and OS/hardware leaks remain).
- QUOTE: "Site Isolation locks each renderer process to documents from a single site and filters certain cross-site data from each process." (Abstract)
- WHY: It is the baseline: processes give strong, deployed, Spectre-resilient isolation but cost memory per site; our one-process design must say what it gives up against this.
- PRIORITY: medium. Baseline to cite, well known.
- READ: abstract, introduction, Section 5.1-5.2 (threat/Spectre comparison), part of evaluation and conclusion.

## 14 Swivel- Hardening WebAssembly against Spectre, Shravan Narayan, Craig Disselkoen, Daniel Moghimi, Sunjay Cauligi, Evan Johnson, Zhao Gang, Anjo Vahldiek-Oberwagner, Ravi Sahita, Hovav Shacham, Dean Tullsen, Deian Stefan, USENIX Security, 2021
- SHOWS: Isolated: Wasm tenants from each other and from the host, many sandboxes inside one process. Mechanism: compiler changes (Swivel-SFI, software only) or Intel CET + MPK (Swivel-CET, with just 2 MPK domains: host vs all sandboxes). Domains: thousands per process (FaaS use case); MPK alone gives only 16, so they do not rely on it for per-sandbox separation. Overhead under 10.3% for the randomized versions, 3.3-240% for deterministic ones, on SPEC 2006. No formal proof; security is argued and checked with proof-of-concept Spectre attacks. Spectre: this is the whole point (sandbox breakout, sandbox poisoning, host poisoning); remaining limits are discussed in Section 6.
- QUOTE: "Swivel ensures that a malicious Wasm tenant cannot speculatively access data outside their sandbox nor coerce another tenant or the host to divulge secrets of other sandboxes via poisoning." (Section 1)
- WHY: It settles that Wasm sandboxes in one process need extra Spectre defenses and that these can be cheap; it leaves a gap: no proof, and it is Wasm code, not JS-engine objects.
- PRIORITY: high. Spectre in-process, many tenants.
- READ: abstract, introduction, conclusion, related work (MPK paragraph), grep of limitations; not the full evaluation.

## 15 The Multi-Principal OS Construction of the Gazelle Web Browser, Helen J. Wang, Chris Grier, Alexander Moshchuk, Samuel T. King, Piali Choudhury, Herman Venter, USENIX Security, 2009
- SHOWS: Isolated: web site principals (origins) from each other, plus the browser kernel, plugins and display. Mechanism: separate OS processes per principal instance, with a browser kernel (about 5k lines of C#) mediating all resources (messages over named pipes). Built on Internet Explorer's engine. Domains: not capped; one or two processes per principal instance. No formal proof; security analysis with a vulnerability study of IE 7 and Firefox 2 (47 and 77 bugs). Spectre: not covered (2009). Browsed 19 of top 20 sites tested; overhead mostly from their IE interposition layer.
- QUOTE: "Unlike previous browsers, Gazelle puts web site principals into separate protection domains, completely segregating their access to all resources." (Section 1)
- WHY: It is the origin of the "browser as OS with a kernel" idea; useful for naming what a session boundary needs (display, events, plugins), but it uses processes, not one process.
- PRIORITY: low. Old, process-based, no proof.
- READ: introduction, related work start, vulnerability study, implementation and performance (via grep), concluding remarks heading only.

## 16 TME-Box- Scalable In-Process Isolation through Intel TME-MK Memory Encryption, Martin Unterguggenberger, Lukas Lamster, David Schrammel, Martin Schwarzl, Stefan Mangard, NDSS, 2025
- SHOWS: Isolated: cloud tenant sandboxes inside one process. Mechanism: Intel TME-MK memory encryption keys (a different key per sandbox) plus compiler instrumentation (LLVM) so each sandbox only uses its own key; a wrong key triggers a hardware fault (MAC mismatch). Domains: up to 32K concurrent sandboxes (vs 16 for MPK). Overhead 5.2% (data isolation) and 9.7% (code and data) on SPEC CPU2017. No formal proof; trusts the compiler instrumentation. Spectre: side channels and fault injection are stated as out of scope. Mentions JIT (V8 sandbox style) as future work.
- QUOTE: "the design of TME-Box allows the efficient isolation of up to 32K concurrent sandboxes." (Abstract)
- WHY: It shows hardware can give tens of thousands of in-process domains cheaply; gap: no proof, no Spectre, needs recent Intel server CPUs, and JIT-compiled code is not handled.
- PRIORITY: high. Scales to many in-process domains.
- READ: abstract, introduction, design overview (grep), threat model line, conclusion and JIT discussion; not evaluation detail.

## 17 Trust and Protection in the Illinois Browser Operating System, Shuo Tang, Haohui Mai, Samuel T. King, OSDI, 2010
- SHOWS: Isolated: web page instances (labeled by origin) from each other and from OS components such as drivers and network stack. Mechanism: new OS built on the L4Ka::Pistachio microkernel; one process per web page instance; the kernel enforces browser policies on messages. TCB about 42K lines of code. Domains: not capped (one process per instance). Measured: prevents 27 of 28 relevant bugs from Linux/X/GTK/glibc lists (the one miss is a driver bug); page loads about as fast as other browsers. Proof: none; the paper only says its small TCB "makes formal verification possible" (a different microkernel was verified before). Spectre: not covered (2010).
- QUOTE: "Because the IBOS TCB has only around 42K LOC, it is possible to formally verify or manually review the entire IBOS TCB." (Section 6.1)
- WHY: It argues that shrinking the trusted base is the route to assurance, which is our aim (a small trusted core), but the isolation is by processes and it is unproved.
- PRIORITY: low. Process-based, old, no proof.
- READ: introduction, implementation, TCB and vulnerability evaluation, performance passage, conclusions.

## 76 Automated Formal Verification of a Software Fault Isolation System, Matthew Sotoudeh, Zachary Yedidia, FMCAD, 2025
- SHOWS: Isolated: untrusted native ARM64 code from the host, in-process (SFI). Mechanism: the LFI verifier is an instruction whitelist; the authors prove with an SMT solver (Yices2) that each whitelisted instruction keeps the SFI invariant, using the ARM ASL formal instruction model. Proof is about the real verifier's whitelist, against a formal ARM64 model, about 20 hours on a 160-core machine, invariant written in about 20 lines. Not verified: the LFI runtime (assumed to set up memory mappings correctly), the compiler. Domains: each sandbox is a 4GiB region; the number of sandboxes is not discussed. Spectre: not covered.
- QUOTE: "we formally verify that programs accepted by the LFI verifier never read or write to memory outside of a designated sandbox region." (Abstract)
- WHY: It shows a proof of memory isolation for a real SFI verifier can be mostly automatic; gap: it covers only the verifier and the sandbox-memory property, not data confidentiality between many sessions or JS.
- PRIORITY: high. Newest, automated proof, real verifier.
- READ: abstract, introduction, Sections III-V (proof setup, results, limitations); skipped the instruction-level details.

## 77 Establishing Browser Security Guarantees through Formal Shim Verification, Dongseok Jang, Zachary Tatlock, Sorin Lerner, USENIX Security, 2012
- SHOWS: Isolated: browser tabs from each other, cookies by domain, and the address bar. Mechanism: separate OS processes for tabs, cookies, input and display, all talking only through a small browser kernel (QUARK). The kernel (a few hundred lines) is written and proved in Coq and run as extracted code; WebKit and the rest are untrusted inside sandboxes. Proof is about the real kernel implementation (not a model), proving tab non-interference, cookie confidentiality and integrity, and address-bar integrity. Domains: not capped (a process per tab). Assumes tab processes can be fully compromised but the process sandbox holds. Timing channels are not covered (the paper calls leaking via URL requests analogous to a timing channel). Spectre: not covered (2012).
- QUOTE: "Tab Non-Interference: no tab can ever affect how the kernel interacts with another tab" (Section 1)
- WHY: It is the closest prior art for "formal proof that sessions cannot see each other's data", but its isolation comes from OS processes and the proof only covers the small kernel, not the code that runs in a shared process.
- PRIORITY: high. Closest proof of tab isolation.
- READ: abstract, introduction, architecture and security properties (Sections 3.1-3.6), discussion and conclusion; not the Coq details of Section 4-5.

## 82 RockSalt- Better, Faster, Stronger SFI for the x86, Greg Morrisett, Gang Tan, Joseph Tassarotti, Jean-Baptiste Tristan, Edward Gan, PLDI, 2012
- SHOWS: Isolated: untrusted native code (Native Client) from the browser, in one process using x86 segment registers. Mechanism: SFI checker (a table-driven DFA, about 80 lines of Coq plus tens of lines of trusted C) proved in Coq against a new Coq model of 32-bit x86 (parses over 130 instructions, defines meaning for over 70; model tested against real CPUs). Proof says: if the checker accepts, the binary only reads and writes its data segments and jumps only inside its code segment. Faster than Google's checker: 0.24 s vs 0.90 s on about 200,000 lines of code. Domains: one sandbox policy; counts not discussed. Spectre: not covered (2012). Gaps: the C code derived from Coq is not itself verified; floating point not modeled.
- QUOTE: "we wanted a proof that if the checker returns TRUE for a given input binary, and if that binary is loaded and executed in an appropriate environment" (Section 4)
- WHY: It is the classic proof that an SFI checker enforces memory isolation, against a machine model; shows how much work a real ISA model takes.
- PRIORITY: medium. Classic precedent, x86-32 only.
- READ: abstract, introduction, Sections 3-4 (checker, proof statement), related work, conclusions; not the DSL details.

## 87 Доверя́й, но проверя́й- SFI safety for native-compiled Wasm, Evan Johnson, David Thien, Yousef Alhessi, Shravan Narayan, et al., Stefan Savage, Deian Stefan, NDSS, 2021
- SHOWS: Isolated: Wasm tenants from each other and the host, many clients inside one process (Fastly and Cloudflare edge clouds, Firefox library sandboxing). Mechanism: VeriWasm, a static checker run on the x86-64 binary produced by the Lucet Wasm compiler (the compiler is no longer trusted). Proof: soundness of the checker's analysis, checked in Coq (1800 lines, 500 of proof), about a model of the x86-64 subset Lucet produces; the Rust tool itself (about 3000 lines), and the disassembler are not verified. Evaluation: found all bugs in a suite of known SFI/Wasm compiler bugs, no false positives on SPEC, Firefox libraries and 103 real Fastly client binaries. Domains: many per process (count not given here). Spectre: not covered.
- QUOTE: "A formal proof that our verifier is sound, i.e., it only labels programs safe if they are indeed safe." (Section I)
- WHY: It shows how to avoid trusting an optimizing compiler by checking its output, and it is a deployed in-process multi-tenant case; the proof is on a model, and Spectre and cross-tenant data flow are left open.
- PRIORITY: high. Deployed multi-tenant in-process Wasm.
- READ: abstract, introduction, Sections III and V (verifier, Coq proof), Section VI evaluation start; not the full per-benchmark results.
