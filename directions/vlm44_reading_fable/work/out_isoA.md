(authored by agents unless marked 🧑)

Group isoA. All 11 papers read (abstract, intro, evaluation summary, conclusion/limits; via text search plus targeted reads, not every page). Terms: SFI = software fault isolation (code is rewritten or checked so it cannot touch memory outside its region). MPK = Intel memory protection keys (page tags, 16 per process, switched in user mode). TCB = the code you must trust.

Headline for the advisor (facts from the texts below): no paper here isolates many untrusted sessions inside one JS engine process with a proof of non-interference. Closest on scale: 07 (LFI, ~65,000 SFI sandboxes, no proof). Closest on proof: 06 and 10 (proofs that sandboxed code stays in its own memory region; proofs are about a model of the code, or about the compiler, not about sessions sharing an engine). Closest on JS engine: 08 (Mohabi) isolates the engine from the browser, with one sandbox per content process, not one per session. Spectre: 02 shows an attack that breaks language-level tenant isolation; 01 and 07 cover it only partly; the rest put it out of scope.

----
id 01: Donky- Domain Keys – Efficient In-Process Isolation for RISC-V and x86, David Schrammel, Samuel Weiser, Stefan Steinegger, Martin Schwarzl, Michael Schwarz, Stefan Mangard, Daniel Gruss, USENIX Security, 2020
SHOWS: A hardware plus software design (new RISC-V CPU feature, run on an FPGA; an MPK emulation on x86) that gives user-mode switching between memory domains, with a trusted monitor; used to put each V8 Isolate (one JS execution context) in its own domain, plus a software vault and an untrusted library. Isolates: V8 Isolates, libraries. Mechanism: hardware protection keys, 1024 keys on RISC-V, only 16 on x86. Overhead on V8 benchmarks 0-2%. No formal proof: the security argument is informal ("take-grant model" described informally). Spectre: out of scope in the threat model, but they show one Spectre V1 gadget is blocked once keys are enforced.
QUOTE: "Cross-domain switches are 16–116x faster than regular process context switches." (Abstract)
WHY: It is the closest hardware prior work to "one V8 Isolate per tenant in one process", but it stops at 16 domains on x86 and has no proof, so a proof of session separation is still open.
PRIORITY: high - closest V8-per-domain design
READ: abstract, intro, threat model, API/monitor design, Section 6 security and Spectre, V8 case study, Section 8.1 limitations

----
id 02: Dynamic Process Isolation, Martin Schwarzl, Pietro Borrello, Andreas Kogler, Kenton Varda, Thomas Schuster, Daniel Gruss, Michael Schwarz, arXiv, 2021
SHOWS: A measured Spectre attack that leaks 120 bit/h across tenants inside Cloudflare Workers (many tenants' V8 JavaScript in one process, JS timers removed), plus a defense that moves a tenant to its own process only when performance counters flag it as suspicious (0.61% false positives, about 2% cost). Isolated: tenants (Workers). Mechanism: V8 isolates, plus on-demand process isolation. No formal proof; security claim is statistical.
QUOTE: "we show that it is possible to mount a Spectre attack on such a restricted environment, leaking secrets from co-located tenants." (Abstract)
WHY: It is direct evidence that language-level isolation of many tenants in one JS process leaks through Spectre, so any in-process design needs either a side-channel story or a process-level fallback.
PRIORITY: high - Spectre limit on in-process tenants
READ: abstract, intro, contributions, discussion of false negatives, conclusion

----
id 03: Efficient Software-Based Fault Isolation, Robert Wahbe, Steven Lucco, Thomas E. Anderson, Susan L. Graham, SOSP, 1993
SHOWS: The original SFI paper: load an untrusted module into its own "fault domain" in the same address space and rewrite its machine code so every store and jump stays inside; measured about 4% slowdown on SPEC92 and cross-domain calls over ten times faster than RPC; a verifier checks the rewritten code; also a Postgres case study. Isolated: untrusted modules/extensions. Mechanism: SFI on MIPS (and Alpha). Full protection (checking reads too) costs more. No formal proof (a code verifier, not a proof); side channels not discussed.
QUOTE: "this approach delivers cross-fault-domain communication that is more than an order of magnitude faster than any RPC mechanism to date." (Section 7, Summary)
WHY: It is the root of the SFI line; useful as background, it settles nothing about many tenants or confidentiality (default mode protects writes and jumps only).
PRIORITY: low - background, 1993, no tenants
READ: abstract, intro, section 3 sandboxing and verifier, Postgres evaluation, section 7 summary

----
id 04: ERIM- Secure, Efficient In-process Isolation with Protection Keys (MPK), Anjo Vahldiek-Oberwagner, Eslam Elnikety, Nuno O. Duarte, Michael Sammler, Peter Druschel, Deepak Garg, USENIX Security, 2019
SHOWS: Uses Intel MPK plus scanning the program's binary for stray key-switch instructions, so a trusted part (e.g. crypto keys, runtime) is isolated from the rest in one process; under 1% overhead at 100,000 switches/s on NGINX and others. Isolated: trusted component from untrusted one (two sides, up to 16 domains max by hardware). Mechanism: MPK + binary inspection + call gates. No machine-checked proof (a security argument in prose); side channels and microarchitectural leaks explicitly out of scope.
QUOTE: "ERIM's measured overhead is less than 1% for 100,000 switches per second" (Abstract)
WHY: It sets the cost baseline for MPK isolation, but its 16-domain cap and need to scan code (hard with JIT-generated JS code) rule it out as is for many sessions.
PRIORITY: medium - MPK baseline, 16-domain cap
READ: abstract, intro, threat model, section on 16 domains/limits, NGINX evaluation, section 7 conclusion

----
id 05: Hodor- Intra-Process Isolation for High-Throughput Data Plane Libraries, Mohammad Hedayati, Spyridoula Gravani, Ethan Johnson, John Criswell, Michael L. Scott, Kai Shen, Mike Marty, USENIX ATC, 2019
SHOWS: "Protected libraries": mutually distrusting user-space libraries (network stack, database) each get a protection domain in one process, using MPK (or alternatives with separate page tables via system calls or VMFUNC), with watchpoints so that one application's failure does not break others sharing a library; Hodor-PKU reaches 90-98% of unprotected kernel-bypass throughput. Isolated: libraries from applications. Limit stated: at most 7 mutually distrusting libraries per application with MPK. No formal proof. Side channels (including transient execution) out of scope.
QUOTE: "Hodor-PKU, in particular, provides 90–98% of kernel-bypass throughput in all of our experiments." (Section 6, Conclusions)
WHY: It shows MPK domain counts are a real ceiling (7 mutually distrusting domains) and that sharing state between distrusting parties is possible but unproved.
PRIORITY: low - MPK, few domains, no proof
READ: abstract, intro, section 2 threat model, limitation paragraph (domain count), conclusions

----
id 06: Isolation Without Taxation- Near-Zero-Cost Transitions for WebAssembly and SFI, Matthew Kolosick, Shravan Narayan, Evan Johnson, Conrad Watt, Michael LeMay, Deepak Garg, Ranjit Jhala, Deian Stefan, POPL, 2022
SHOWS: Makes calls between host and a Wasm sandbox plain function calls (no register save/clear), under "zero-cost conditions"; builds a static binary checker (VeriZero) for x86 output of the Lucet Wasm compiler and proves it sound with a logical relation (a proof technique relating code behavior to a safety condition) against a formal model (a safety monitor on an abstract machine), not mechanically tied to real binaries beyond the checker; sped up Firefox image/font rendering up to 29.7% / 10%. Isolated: sandboxed library from host application. Mechanism: Wasm SFI (and a segmentation-based SegmentZero32). Number of sandboxes not the focus. Side channels out of scope.
QUOTE: "Wasm code verified by VeriZero never reaches an oerror state." (Section 6.1)
WHY: Gives the best formal-model proof here that sandbox transitions leak nothing (integrity and confidentiality of host registers/state), but it covers one sandbox against its host, not sandboxes against each other.
PRIORITY: high - proof style we may reuse
READ: abstract, intro, section 6.1 proof, section 8 limitations; proof details live in an appendix not in the text

----
id 07: Lightweight Fault Isolation- Practical, Efficient, and Secure Software Sandboxing, Zachary Yedidia, ASPLOS, 2024
SHOWS: An SFI system for ARM64 with 4GiB sandboxes, tens of thousands (about 65,000 by default) in one address space; it isolates loads, stores and jumps with 7% overhead on a subset of SPEC 2017; a small static verifier (about 300 lines for its core) checks machine code; measured on real hardware; includes a runtime that schedules sandboxes. Spectre: hardened against "basic" Spectre attacks, with a section listing what is and is not covered. No formal proof of the verifier (the paper says verification could be done later; it uses a formal ARM ISA definition in tooling).
QUOTE: "LFI, supports tens of thousands of 4GiB sandboxes in a single address space and does full software isolation of loads, stores, and jumps" (Abstract)
WHY: It is the strongest prior answer on "many sandboxes in one process" and on confidentiality (loads checked), but only as machine-level SFI, with no proof and no JS-engine integration.
PRIORITY: high - many sandboxes, one process
READ: abstract, intro, design (guards, sandbox count), verifier section, Spectre section, evaluation overview, conclusion

----
id 08: Mohabi- Disaggregating and Sandboxing the Firefox JavaScript Engine, Abhishek Sharma, Anand Balaji, Zachary Yedidia, et al., Deian Stefan, Hovav Shacham, Shravan Narayan, OSDI, 2026
SHOWS: A Firefox build where the SpiderMonkey JS engine (including its JIT-generated code) runs inside an SFI sandbox, separated from the rest of the browser; overhead 24.82% on JetStream and 24.43% on Speedometer, 5.9-6.6% on SPEC 2017 for the SFI toolchain; a binary validator checks the compiler-added checks. Isolated: JS engine from the browser. One sandbox instance per content process; all its threads (e.g. Web Workers) share it, so sessions inside one engine are not isolated from each other. The text only says SFI validators have been verified in prior work and "could enable further TCB reduction"; no proof here. Spectre not found in my search of the text.
QUOTE: "Mohabi sandboxes SpiderMonkey JS engine instances in the Mozilla Firefox browser." (Section 1, Introduction)
WHY: It proves it is feasible to sandbox a whole production JS engine with JIT, but it protects the browser from the engine, which is a different boundary from tenant-versus-tenant inside the engine.
PRIORITY: high - JS engine sandbox, closest practice
READ: abstract, intro, section 4 (threads/instances), section on validator, related work on formal verification and JIT sandboxes, conclusion

----
id 09: Native Client- A Sandbox for Portable, Untrusted x86 Native Code, Bennet Yee, David Sehr, Gregory Dardyk, J. Bradley Chen, Robert Muth, Tavis Ormandy, Shiki Okasaka, Neha Narula, Nicholas Fullagar, IEEE S&P, 2009
SHOWS: A browser plugin running untrusted 32-bit x86 modules in a sandbox: x86 segment registers bound data accesses, code is aligned in 32-byte chunks and validated before running (about 30 MB/s); average about 5% overhead on SPEC2000 (worst about 12%). Isolated: untrusted native modules from the browser/OS. Includes a short paper proof (by contradiction) that the validated code only reaches validated instructions. Not machine-checked; only for explicit control flow; side channels not discussed.
QUOTE: "Native Client provides sandboxed execution of native code and portability across operating systems, delivering native code performance for the browser." (Section 1)
WHY: It is the browser-sandbox ancestor of the validator-plus-segment approach and shows a small hand proof for control-flow safety; limited to 32-bit x86 and few modules.
PRIORITY: low - historical, 32-bit only
READ: abstract, intro, threat model, validator proof section, performance summary, conclusions

----
id 10: Provably-Safe Multilingual Software Sandboxing using WebAssembly, Jay Bosamiya, Wen Shih Lim, Bryan Parno, USENIX Security, 2022
SHOWS: Two compilers from Wasm to x64: vWasm, written in the F* proof assistant, with a machine-checked proof that its output stays inside the sandbox (the proof is on a model of x64 and a Wasm subset, and the trusted base includes F*, Z3 and OCaml); and rWasm, which emits safe Rust so that the Rust compiler gives the guarantee; performance competitive with standard runtimes (rWasm within 3-26% of some faster ones). Isolated: sandboxed code from host. Mentions sandboxes side by side in one host process in its architecture figure, but proves only the host-safety property. Side channels and speculative execution are explicitly out of scope.
QUOTE: "mathematically prove that the compiled Wasm code can only interact with its host environment via an explicitly provided API" (Section 1)
WHY: It shows the strongest proof style on real compiler code (mechanized, F*), but the property proved is "stays in its own sandbox", not "tenants cannot observe each other" in a shared engine.
PRIORITY: high - mechanized sandbox proof exists
READ: abstract, intro, threat model, section 4 vWasm theorem and TCB, evaluation overview, conclusions

----
id 11: Retrofitting Fine Grain Isolation in the Firefox Renderer, Shravan Narayan, Craig Disselkoen, Tal Garfinkel, Nathan Froyd, Eric Rahm, Sorin Lerner, Hovav Shacham, Deian Stefan, USENIX Security, 2020
SHOWS: RLBox, a C++ framework that lets Firefox sandbox third-party libraries (image, video, audio, font, zlib), using Wasm-based SFI or process isolation, with the C++ type system plus dynamic checks to force validation of data crossing the boundary; evaluated for per-library, per-origin and per-renderer grain; page latency impact 3% (SFI) and 13% (process isolation); libGraphite sandbox shipped in production Firefox. Isolated: libraries (optionally per content origin) from the renderer. Enforcement is by type checking, not a proof. Spectre explicitly out of scope; "leave the design of a Spectre-robust sandbox to future work".
QUOTE: "RLBox supports efficient sandboxing through either software-based-fault isolation or multi-core process isolation." (Section 1)
WHY: It defines the practical per-origin sandbox grain and shows data-crossing bugs are the main engineering risk, but it isolates libraries, not many sessions of an engine.
PRIORITY: medium - boundary-checking lessons, no proof
READ: abstract, intro, section 2 (grain and threat model, Spectre note), evaluation summary
