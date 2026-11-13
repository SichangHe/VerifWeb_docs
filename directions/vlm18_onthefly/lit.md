# Lit: load-time verification of untrusted code; analysis/enforcement for page JS
(authored by agents unless marked 🧑)
Fetched 2026-11-08 with pb-browser-page-extract. "V" = quote copied from a fetched page. UNVERIFIED = not from a fetched page.
Note: fetched pages give abstracts only (PDFs not extractable). Scale/limit numbers inside paper bodies are mostly UNVERIFIED.

Author lists not shown in fetched text (e.g. Chugh et al., Schäfer et al., Richards et al., Jensen et al., Necula, Yee et al.) come from the task brief or memory: UNVERIFIED.
## A. Load-time / JIT verification of untrusted code

### PCC - Necula, "Proof-carrying code", POPL 1997
URL: https://dl.acm.org/doi/10.1145/263699.263712 (V)
- (a) "a mechanism by which a host system can determine with certainty that it is safe to execute a program supplied (possibly in binary form) by an untrusted source."
- (b) "The host can then easily and quickly validate the proof without using cryptography and without consulting any external agents." (no numbers in abstract)
- (c) none in abstract. Case studies only: "safe assembly-language extensions of ML programs", "network packet filters".

### Native Client - Yee et al., S&P 2009
URL: https://research.google/pubs/native-client-a-sandbox-for-portable-untrusted-x86-native-code/ (V, abstract only)
- (a) "Native Client is an open-source research technology for running x86 native code in web applications, with the goal of maintaining the browser neutrality, OS portability, and safety that people expect from web apps."
- (b),(c) UNVERIFIED: paper PDF not extractable. No validator speed/limit quotes obtained.

### RockSalt - Morrisett, Tan, Tassarotti, Tristan, Gan, PLDI 2012
URL: https://dl.acm.org/doi/10.1145/2254064.2254111 (V)
- (a) "Software-based fault isolation (SFI), as used in Google's Native Client (NaCl), relies upon a conceptually simple machine-code analysis to enforce a security policy. But for complicated architectures such as the x86, it is all too easy to get the details of the analysis wrong."
- (b) "We have built a new checker that is smaller, faster, and has a much reduced trusted computing base when compared to Google's original analysis."
- (c) Google search snippet only (not primary page, UNVERIFIED as to context): "The definitions for our x86 model and NaCl checker are about 5,000 lines of heavily commented Coq code, but the RockSalt proofs are another 10,000 lines." Abstract: "a formal model of a subset of the x86 instruction set architecture" (subset only).

### Linux eBPF verifier - kernel docs
URL: https://www.kernel.org/doc/html/latest/bpf/bpf_design_QA.html (V)
- (a) "Q: What are the verifier limits? A: The only limit known to the user space is BPF_MAXINSNS (4096)." and "The verifier has various internal limits."
- (b) "Currently, that limit is set to 1 million." / "Which essentially means that the largest program can consist of 1 million NOP instructions."
- (c) "There is a limit to the maximum number of subsequent branches, a limit to the number of nested bpf-to-bpf calls, a limit to the number of the verifier states per instruction, a limit to the number of maps used by the program." / "All these limits can be hit with a sufficiently complex program." / "There are also non-numerical limits that can cause the program to be rejected." / "The limits are being removed."
URL: https://www.kernel.org/doc/html/latest/bpf/verifier.html (V)
- (a) "Second step starts from the first insn and descends all possible paths. It simulates execution of every insn and observes the state change of registers and stack." First step: "DAG check to disallow loops and other CFG validation."

### PREVAIL - Gershuni et al., PLDI 2019
URL: https://dl.acm.org/doi/10.1145/3314221.3314590 (V)
- (a) "Extended Berkeley Packet Filter (eBPF) is a Linux subsystem that allows safely executing untrusted user-defined extensions inside the kernel. It relies on static analysis to protect the kernel against buggy and malicious extensions."
- (c) "the limitations of its current verifier, including high rate of false positives, poor scalability, and lack of support for loops, have become a major barrier for developers."
- (b) "our evaluation, based on hundreds of real-world eBPF programs, shows that the new tool generates no more false alarms than the existing Linux verifier, while it supports a wider class of programs (including programs with loops) and has better asymptotic complexity."

### Agni - Vishwanathan, Shachnai, Narayana, Nagarakatte, "Verifying the Verifier: eBPF Range Analysis Verification", CAV 2023
URL: https://link.springer.com/chapter/10.1007/978-3-031-37709-9_12 (V)
- (a) "an automated method to check the correctness of range analysis used in the Linux kernel's eBPF verifier."
- (b) "Our prototype automatically checks the soundness of 16 versions of the eBPF verifier in the Linux kernel versions ranging from 4.14 to 5.19."
- (c) "When we discover instances where the eBPF verifier is unsound, ..." / "we have discovered new bugs in older versions and proved the soundness of range analysis in the latest version" (only range analysis, not whole verifier). (Author list from memory: UNVERIFIED.)

### eBPF verifier false rejections (usability)
Rex, Jia et al., USENIX ATC 2025. URL: https://www.usenix.org/conference/atc25/presentation/jia (V); also arXiv 2502.18832 (V)
- (c) "We identify significant usability issues—safe extensions being rejected by the verifier—due to the language-verifier gap, a mismatch between developers' expectation of program safety provided by a contract with the programming language, and the verifier's expectation."
bpfix, Zheng et al., arXiv 2607.02748 (Jul 2026, preprint). URL: https://arxiv.org/abs/2607.02748 (V)
- (c) "an empirical study of 235 reproduced rejections, showing that 47% of rejections return only EINVAL, one error string maps to as many as nine distinct root causes" (studies diagnostics, not false-rejection rate).

### eBPF verifier CVEs (soundness bugs: unsafe accepted)
- CVE-2023-2163, https://nvd.nist.gov/vuln/detail/cve-2023-2163 (V): "Incorrect verifier pruning in BPF in Linux Kernel >=5.4 leads to unsafe code paths being incorrectly marked as safe, resulting in arbitrary read/write in kernel memory, lateral privilege escalation, and container escape."
- CVE-2022-23222, https://nvd.nist.gov/vuln/detail/CVE-2022-23222 (V): "kernel/bpf/verifier.c in the Linux kernel through 5.15.14 allows local users to gain privileges because of the availability of pointer arithmetic via certain *_OR_NULL pointer types."

### VeriWasm - Johnson et al., NDSS 2021 ("Доверя́й, но проверя́й: SFI safety for native-compiled Wasm")
URL: https://www.ndss-symposium.org/ndss-paper/%D0%B4%D0%BE%D0%B2%D0%B5%D1%80%D1%8F%D0%B9-%D0%BD%D0%BE-%D0%BF%D1%80%D0%BE%D0%B2%D0%B5%D1%80%D1%8F%D0%B9-sfi-safety-for-native-compiled-wasm/ (V)
- (a) "we propose verifying memory isolation of Wasm binaries post-compilation. We implement this approach in VeriWasm, a static offline verifier for native x86-64 binaries compiled from Wasm"
- (c) "subtle bugs in the Wasm compiler can break---and have broken---isolation guarantees." / "we prove the verifier's soundness, and find that it can detect bugs with no false positives."
- (b) UNVERIFIED: a Google AI-overview snippet claimed "a median time of 1.85s for Fastly binaries"; not from a primary page. A search snippet also said VeriWasm "cannot check ... may produce false positives (§VI)" (luneresearch, not fetched): UNVERIFIED. Note "offline", not load-time.

### LFI - Yedidia, "Lightweight Fault Isolation: Practical, Efficient, and Secure Software Sandboxing", ASPLOS 2024
URL: https://dl.acm.org/doi/10.1145/3620665.3640408 (V)
- (a) "does full software isolation of loads, stores, and jumps" ; "has a small static verifier to reduce TCB size"
- (b) "supports tens of thousands of 4GiB sandboxes in a single address space ... with a runtime overhead of 7% on the compatible subset of the SPEC 2017 benchmark suite."
- (c) "compatible subset" of SPEC; ARM64 only ("revisit classic SFI in the context of ARM64"); "hardened against basic Spectre attacks". Author name (Zachary Yedidia) from Google snippet / URL, not the ACM page text.

### CoreJIT - "Formally verified speculation and deoptimization in a JIT compiler", POPL 2021 (authors not on fetched text; Barrière et al. per task, UNVERIFIED)
URL: https://dl.acm.org/doi/10.1145/3434327 (V)
- (a) "This paper presents a model just-in-time compiler with an intermediate representation that explicits the synchronization points used for deoptimization and the assumptions made by the compiler's speculation. ... The optimizations are proved correct with the help of a proof assistant."
- (c) "While our work stops short of proving native code generation, we demonstrate how one could use the verified optimization to obtain significant speed ups in an end-to-end setting."
(Verifies compiler optimizations, not untrusted input.)

## B. Analysis / enforcement for web-page JS

### Staged information flow - Chugh, Meister, Jhala, Lerner, PLDI 2009
URL: https://dl.acm.org/doi/10.1145/1542476.1542483 (V)
- (a) "We present an information-flow based approach for inferring the effects that a piece of JavaScript has on the website in order to ensure that key security properties are not violated."
- (b) "Our framework propagates information flow through the currently known code in order to compute a minimal set of syntactic residual checks that are performed on the remaining code when it is dynamically loaded." / "evaluate our system's performance on a variety of large real-world websites. Our experiments show that static information flow is feasible and efficient for JavaScript, and that our technique allows the enforcement of information-flow policies with almost no run-time overhead."
- (c) "We describe our techniques for handling some difficult features of JavaScript" (limits not in abstract).

### Dynamic determinacy analysis - Schäfer, Sridharan, Dolby, Tip, PLDI 2013
URL: https://dl.acm.org/doi/10.1145/2491956.2462168 (V)
- (a) "identifying determinate variables and expressions that always have the same value at a given program point" ; "specialize uses of dynamic language constructs such as eval, replacing them with equivalent static constructs."
- (b) "In some cases scalability of static pointer analysis was improved dramatically, and that many uses of runtime code generation could be eliminated."
- (c) "Our analysis is completely dynamic and only needs to observe a single execution of the program, yet the determinacy facts it infers hold for any execution." (formal proof only "for a simple imperative language")

### ConScript - Meyerovich, Livshits, S&P 2010 (MSR-TR-2009-158)
URL: https://www.microsoft.com/en-us/research/publication/conscript-specifying-and-enforcing-fine-grained-security-policies-for-javascript-in-the-browser/ (V)
- (a) "ConScript allows the hosting page to express fine-grained application-specific security policies that are enforced at runtime."
- (b) "we compare the overhead of ConScript enforcement and conclude that it is significantly lower than that of other systems proposed in the literature, both on micro-benchmarks as well as large, widely-used applications such as MSN, GMail, Google Maps, and Live Desktop."
- (c) "built on top of Internet Explorer 8" (needs browser modification); runtime enforcement, not verification.

### Gatekeeper - Guarnieri, Livshits, USENIX Security 2009 (fetched: MSR-TR-2009-43 abstract; same authors)
URL: https://www.microsoft.com/en-us/research/publication/gatekeeper-mostly-static-enforcement-of-security-and-reliability-policies-for-javascript-code/ (V; USENIX page/PDF not fetchable)
- (a) "a mostly static approach for soundly enforcing security and reliability policies for JavaScript programs" ; "the hosting site has the authority to reject the submission of widgets that do not meet the site's security policies."
- (b) "Statically checking these policies results in 1,341 verified warnings in 684 widgets, no false negatives, due to the soundness of our analysis, and false positives affecting only two widgets."
- (c) Restricted to widgets (JavaScript subset; eval etc. excluded - UNVERIFIED, not in abstract).

### ADsafety - Politz, Eliopoulos, Guha, Krishnamurthi, USENIX Security 2011
URL: https://www.usenix.org/conference/usenix-security-11/adsafety-type-based-verification-javascript-sandboxing (V)
- (a) "We use a novel type system for JavaScript to encode and verify sandboxing properties. The resulting verifier is lightweight and efficient, and operates on actual source."
- (c) "applying it to ADsafe, which revealed several bugs and other weaknesses." (verifies the sandbox, not the guest code)
- Caja: no page fetched. UNVERIFIED.

### JSand - Agten, Van Acker, Brondsema, Phung, Desmet, Piessens, ACSAC 2012
URL: https://dl.acm.org/doi/10.1145/2420950.2420952 (V)
- (a) "JSand enforces a server-specified policy on included scripts without requiring server-side filtering or rewriting of scripts."
- (b) "more than half of the Alexa top 10000 sites include scripts from more than 5 different origins." ; "performs sufficiently well" (no number). Authors from memory: UNVERIFIED.

### TreatJS (JS contracts) - Keil, Thiemann, ECOOP 2015
URL: https://arxiv.org/abs/1504.08110 (V)
- (a) "a language embedded, higher-order contract system for JavaScript which enforces contracts by run-time monitoring."
- (c) "The library relies on JavaScript proxies to guarantee full interposition for contracts." (overhead sentence truncated in extract). Disney/Flanagan Contracts.js: not fetched, UNVERIFIED. TypeScript runtime checks: not fetched, UNVERIFIED (TS types are erased - from memory).

## C. Static analyzers and real-page scale; eval

### TAJS - Jensen, Møller, Thiemann, SAS 2009 "Type Analysis for JavaScript"
URL: https://link.springer.com/chapter/10.1007/978-3-642-03237-0_17 (V)
- (a) "sound type information for JavaScript programs using abstract interpretation"
- (b/c) "Preliminary experiments conducted on real-life JavaScript code indicate that the approach is promising regarding analysis precision on small and medium size programs, which constitute the majority of JavaScript applications."
Determinacy for jQuery (Andreasen, Møller, OOPSLA 2014), https://cs.au.dk/~amoeller/papers/jquery/ (V): "a major obstacle is the prevalence of libraries, in particular jQuery, which apply programming patterns that have detrimental consequences on the analysis precision and performance." ; "evaluated on a collection of small programs that use jQuery."
Madsen, Livshits, Fanning, MSR-TR-2012-66 (FSE 2013), https://www.microsoft.com/en-us/research/publication/practical-static-analysis-of-javascript-applications-in-the-presence-of-frameworks-and-libraries/ (V): "most JavaScript applications rely on large and complex libraries and frameworks" ; "25 Windows 8 JavaScript applications, averaging 1,587 lines of code, together with about 30,000 lines of library code" (scale far below ~600 KB page JS).

### SAFE - Lee, Won, Jin, Cho, Ryu, FOOL 2012
URL: https://2012.splashcon.org/details/fool-2012-papers/3/SAFE-Formal-Specification-and-Implementation-of-a-Scalable-Analysis-Framework-for-EC (V: title/authors only). Abstract UNVERIFIED.

### Jelly - Laursen, Xu, Møller, PLDI 2024 "Reducing Static Analysis Unsoundness with Approximate Interpretation"
URL: https://dl.acm.org/doi/10.1145/3656424 (V)
- (c) "To ensure scalability and precision, existing state-of-the-art analyses for JavaScript mostly ignore these operations although it results in missed call edges and aliasing relations."
- (b) "experiments on 141 real-world Node.js-based JavaScript applications and libraries" ; "average analysis recall is improved from 75.9 % to 88.1 %" (so baseline recall ~76 %: unsound). Node.js, not web pages.

### Richards, Hammer, Burg, Vitek, "The Eval That Men Do", ECOOP 2011
URL: https://link.springer.com/chapter/10.1007/978-3-642-22655-7_4 (V)
- (c) "Any ahead-of-time analysis, to remain sound, is forced to make pessimistic assumptions about the impact of dynamically created code. This pessimism affects ... the kinds of errors that can be caught statically and the security guarantees that can be enforced."
- (b) "We have recorded the behavior of 337 MB of strings given as arguments to 550,358 calls to the eval function exercised in over 10,000 web sites."

### Richards, Lebresne, Burg, Vitek, "An analysis of the dynamic behavior of JavaScript programs", PLDI 2010
URL: https://dl.acm.org/doi/10.1145/1809028.1806598 (V)
- "Many of these techniques aim to reign in some of the most dynamic features of the language, yet little seems to be known about how programmers actually utilize the language or these features." ; "compare that with assumptions commonly made in the literature and accepted industry benchmark suites."

### "Static analysis of JavaScript on real web pages" (specific paper): not found / not fetched. UNVERIFIED.

## D. Real page JS size
HTTP Archive Web Almanac 2024, JavaScript chapter. URL: https://almanac.httparchive.org/en/2024/javascript (V)
- "In 2024, this upward trend resumed, with the median JavaScript payload rising by 14%, reaching 558 kilobytes on mobile and 613 kilobytes on desktop." (Figure: "Median JavaScript kilobytes per page"; compressed vs decoded not stated in the extract.)
- "In 2024, the median mobile page is making 22 JavaScript requests, while those in the 90th percentile soar to 68." Desktop: "the median jumps to 23 JavaScript requests, with the 90th percentile climbing to 70 requests."
- 2025 edition has no JavaScript chapter in its TOC (fetched TOC lists Fonts, WebAssembly, Third Parties, ...).

## E. Recent (2018-2026) load-time verification of page JS in browser
No paper found/verified. Searches returned only vendor blogs (CSP/SRI/monitoring). Closest verified: JSand (2012), Rex (kernel), VeriWasm (offline). UNVERIFIED: any 2018-2026 browser load-time page-JS verifier.
