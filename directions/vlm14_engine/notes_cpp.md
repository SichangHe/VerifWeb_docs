# Can we verify a C++ JS engine enough for shared-process tabs? Evidence notes
(authored by agents unless marked 🧑)

Labels: [F] fact with quote+URL; [PT] quote came through a fetch/search tool summary, so paraphrased by tool (not guaranteed verbatim); [I] inference; [O] opinion. Read-only research; nothing published or filed.
Reused local notes (not redone): out/vlm10_share/REPORT.md, prior_work.md, out/vlm13_check/REPORT.md.

## Takeaway
- [I] No evidence found of verified C++ at JS-engine scale (V8/SpiderMonkey are millions of lines of C++ with a JIT). Verified C/C++ is kernels, crypto, small libraries.
- [I] "Verify enough" is plausible only as a narrow, layered set of properties (see section 2), not functional correctness of the engine.

## 1. State of the art: verifying C/C++

### seL4 (C, functional correctness)
- [PT] 2009 paper: "8,700 lines of C code and 600 lines of assembler"; proof "200,000 lines of Isabelle script". https://www.sigops.org/s/conferences/sosp/2009/papers/klein-sosp09.pdf (via search tool summary)
- [PT] effort: slides total ~25 person-years; later TOCS paper ~20 py of proof, 9 py in frameworks/tools. https://sel4.systems/Research/pdfs/comprehensive-formal-verification-os-microkernel.pdf
- [F] "Machine-checked mathematical proofs from high-level specifications to binary code." https://sel4.systems/Verification/ (via fetch tool; line counts not on that page)
- [I] ~10k lines C took ~20-25 py; scaling to V8 (order 10^6+ lines, JIT) is out of reach by that ratio.

### Frama-C (C, ACSL, WP/Eva)
- [PT] largest figure found: Eva+WP used on a "50 kloc" nuclear I&C code (2015 overview); WP used at Airbus on A380/A350/A400M code. https://list.cea.fr/en/page/frama-c/ , https://frama-c.com/download/framaCDay/FCSD17/talk/04_Correnson.pdf (via search tool)
- not found: a larger WP-proved codebase. The success-stories URL I tried returned 404.
- Frama-Clang (C++ frontend): [PT] "experimental C++ front-end"; "currently in an early stage of development. It is known to be incomplete and comes without any bug-freeness guarantees". https://frama-c.com/fc-plugins/frama-clang.html ; older manual: aims at C++11 only.

### VST + CompCert
- [PT] Verifiable C is sound w.r.t. CompCert Clight, so proofs carry to assembly. Verified: OpenSSL SHA-256 (Appel, TOPLAS 2015) and HMAC (USENIX Sec 2015); the HMAC code was OpenSSL 0.9.1c, 1999. https://www.usenix.org/system/files/conference/usenixsecurity15/sec15-paper-beringer.pdf
- not found: any VST proof of anything near a browser-engine size.

### CBMC at AWS (bounded model checking, not full proof)
- [PT] "171 entry points over nine modules in the AWS C Common library", by one full-time engineer plus two interns over 24 weeks; proofs run in CI on every PR; also s2n and FreeRTOS TCP/IP. https://assets.amazon.science/4d/b0/504a2bbf4f3db18d98e37b8580df/code-level-model-checking-in-the-software-development-workflow-at-amazon-web-services.pdf (via search tool)
- [PT] proof run times "seconds to tens of minutes, memory ... megabytes to tens of gigabytes".
- [I] shows memory-safety proofs per function with bounded inputs are cheap and CI-able; it does not scale to whole engines with unbounded heaps and JIT.
- [PT] "Verifying Verified Code" (arXiv 2107.00723): other tools found no new bugs but "problems in the proof specifications" - specs can be wrong. 

### RefinedC
- [PT] "RefinedC: Automating the Foundational Verification of C Code with Refined Ownership Types", PLDI 2021; Coq proofs via Iris; "our largest case study applies RefinedC to a version of the page allocator of the Hafnium hypervisor". https://plv.mpi-sws.org/refinedc/paper.pdf
- [I] C only, a subset; largest case = one allocator.

### Cerberus
- [PT] Cerberus-BMC "A Principled Reference Semantics and Exploration Tool for Concurrent and Sequential C"; PNVI pointer provenance; "open questions in what the C semantics and ISO standard are (or should be)". https://link.springer.com/chapter/10.1007/978-3-030-25540-4_22
- [I] C semantics itself has open questions; C++ is harder (not found: a Cerberus-style C++ semantics).

### Pulse / F*, Low*/HACL*
- [F] "Code from HACL*, ValeCrypt and EverCrypt is deployed in several production systems, including Mozilla Firefox, the Linux kernel" ; "Low* programs are compilable to C by KaRaMeL." https://project-everest.github.io/ (via fetch tool, quotes as returned)
- [PT] Pulse: "Pulse programs are run by extracting them to OCaml, C and Rust"; EverCBOR "proven memory safe, arithmetically safe, and functionally correct". https://arxiv.org/pdf/2505.17335
- [I] this is "verified code generated as C", not verification of existing C++. Shipping scale = crypto/parsers, not engines. Rewriting a JS engine in Low*/Pulse: not found.

### Is there verified C++ of significant size?
- BRiCk / SkyLabs (Coq/Rocq, Iris): [F] "Formalization of C++ for verification purposes." https://github.com/bedrocksystems/BRiCk (fetch tool)
  - [PT] NOVA microhypervisor C++ verified: "The formal proof (nova_proof) covers the specs for internal C++ structures and functions and proves that the implementation satisfies those internal specs." https://bluerocksec.gitlab.io/formal-methods/blogs/2025-11-18-NOVA-proof-spec/
  - [PT] earlier tech report: proof covered "a sequentially-consistent version" of NOVA, which uses weak-memory atomics. https://bluerocksec.gitlab.io/formal-methods/tech_reports/towards-modular-specification-and-verification-of-concurrent-hypervisor-based-isolation.pdf
  - [PT] SkyLabs HCSS 2026: "Users of Brick have carried out interesting verifications drawn from an industrial hypervisor stack and the C++ standard library." https://sos-vo.org/group/hcss_conference/2026/beringer-malecha
  - line counts of NOVA proof/code: not found.
  - [I] best evidence that real C++ systems code can be verified; a microhypervisor is far smaller and simpler than a JS engine (no JIT, GC, templates-heavy code) [I, size unverified].
- ESBMC: [F] checks "single- and multi-threaded C, C++, CUDA, CHERI, Kotlin, Python, Rust, and Solidity programs"; "The Clang compiler as its C/C++/CHERI/CUDA frontend". https://github.com/esbmc/esbmc (fetch tool). C++ feature limits: not found on that page. [I] bounded checking only.
- Pulse analyzer in Infer (Meta): not found in my searches.

## 2. What "verify enough" could mean for V8 / SpiderMonkey

### V8 sandbox: stated threat model
- [F] "The sandbox assumes that an attacker can arbitrarily and concurrently modify any memory inside the sandbox address space ... it is assumed that an attacker will be able to read memory outside of the sandbox, for example through hardware side channels." https://raw.githubusercontent.com/v8/v8/main/src/sandbox/README.md (curl, verbatim)
- [F] "The goal is to prevent memory corruption outside of the sandbox." https://v8.dev/blog/sandbox (fetch tool)
- [PT] "only the V8 heap is inside the sandbox"; "there are still a number of issues to resolve before it becomes a strong security boundary"; overhead "around 1% or less on typical workloads". same blog.
- [PT] blog does not discuss multiple isolates; Spectre appears only as argument against memory tagging. same blog.
- Design doc (Google Doc): fetch returned only page shell; not read.
- [I] the sandbox is a per-process (one cage per process by default) boundary against the engine's own memory-corruption bugs. It assumes the attacker already controls in-cage memory; it does not separate two tenants' heaps unless each isolate gets its own cage [I, not verified in source]. Its trusted part (the pointer-table and the out-of-sandbox C++ that handles in-sandbox values) is exactly the C++ that would be verified: a small, well-defined slice rather than the whole engine.
- [PT] "Out-of-sandbox code can still be undermined by corrupted in-sandbox values" e.g. tampered property count -> OOB on std::vector, fixed with `SBXCHECK`. Same blog. This is a verifiable-interface property: all out-of-sandbox code must treat in-sandbox data as untrusted.

### Mohabi, Icarus (from local notes, quotes already in prior_work.md)
- [F] Mohabi (OSDI 2026): "Mohabi leverages software-based fault isolation (SFI) to ensure JavaScript engine bugs cannot affect the rest of the browser." ~24.8% JetStream, 24.4% Speedometer. https://www.usenix.org/conference/osdi26/presentation/sharma
  - [I] SFI shrinks the trusted base to the SFI checker/runtime; engine is untrusted. Isolates engine from browser; tenant-vs-tenant inside one engine not stated in abstract.
- [F] Icarus (SOSP 2024): "a new framework for implementing JIT compilers that are automatically, formally verified to be safe, and which can then be converted to C++ that can be linked into browser runtimes." https://dl.acm.org/doi/abs/10.1145/3694715.3695949 . "We evaluate Icarus by using it to re-implement components of Firefox's JavaScript JIT."
  - [I] verifies part of the JIT (components), emitting C++; the rest of the engine stays unverified C++.
- [F] Vos, Utrecht thesis 2026: "We use the ... an ICARUS verification note for each of our CacheIR generator methods." (per prior_work.md)

### JIT output checking / translation validation
- [F] VeriWasm: "does not verify a compiler, but instead verifies that individual binaries compiled from Wasm do preserve the sandbox" (prior_work.md, via McLoughlin et al.). AOT Wasm only.
- [F] Kwon et al., ISSTA 2024, translation validation for V8 JIT: "(JIT compiler of V8) as SMT encoding. For efficient validation, we design a staged strategy for JS JIT compilers." (prior_work.md) Checks semantic correctness, not isolation.
- [F] Local experiment (vlm10 REPORT): ~32% of JIT memory operands used raw heap pointers; a static checker needs the V8 sandbox build. 1 small run, Node 22, pointer compression off.
- not found: a deployed per-output JIT isolation checker.

### Fuzzing as non-proof assurance
- [F] Fuzzilli: "A (coverage-)guided fuzzer for dynamic language interpreters" ; showcase includes "CVE-2019-8518: OOB access in FTL JIT due to LICM moving array access before the bounds check" and "CVE-2019-11707: IonMonkey incorrectly predicts return type of Array.prototype.pop, leading to type confusions". https://github.com/googleprojectzero/fuzzilli (fetch tool)
- [I] fuzzing finds bugs but gives no absence guarantee; real JIT bugs keep appearing (see the CVEs above, all JIT-originating).

### Cloudflare Workers isolate model
- [PT] "V8 isolates 'prevent that code from accessing memory outside the isolate — even within the same process.'" ; "Cloudflare 'can run many isolates within a single process'". https://developers.cloudflare.com/workers/reference/security-model/
- [PT] V8's complexity creates "a wider attack surface than virtual machines"; "the Workers patch gap is now under 24 hours."
- [PT] "V8 itself cannot defend against Spectre"; mitigations: `Date.now()` "returns the time of the last I/O. It does not advance during code execution"; no threads/shared memory; suspicious/CPU-heavy Workers moved to own process; periodic restarts; free vs enterprise never share a process ("cordons").
- [PT] outer layer: "Linux namespaces and `seccomp`" per process.
- [F] Cloudflare 2026: "remote Spectre attack reliably leaking up to 12 bit/s with a 99% accuracy in the production environment" ; "integrated the V8 Sandbox and an in-process isolation mechanism" https://blog.cloudflare.com/revisiting-spectre-attacks-on-workers/ (prior_work.md)
- [F] Chromium: "around 70% of our serious security bugs are memory safety problems" https://www.chromium.org/Home/chromium-security/memory-safety/ (vlm13)

### Minimum properties when tenants share a process [I] (derived, not from one source)
1. Heap isolation: no code of tenant A can read/write tenant B's heap or isolate state, even given arbitrary memory corruption in A's JS heap (V8 sandbox's attacker model, extended per tenant). Needs: bounded pointers (cage base+offset), checked entry points to out-of-cage code, per-isolate state swap (r13 root register per local experiment).
2. JIT code integrity: generated code stays inside its cage and cannot flip protections or call arbitrary targets (Cloudflare quote in prior_work: arbitrary machine code "could disable memory protection keys"; checker idea open).
3. Trusted C++ boundary (runtime, builtins, GC, embedder glue) validates all data from in-cage memory: the part a verifier/BRiCk-style proof or CBMC-style bounded proofs could target [I].
4. Side channels: Spectre is not covered by memory safety proofs; need timer coarsening, no shared memory, process separation for suspicious tenants, and separate processes for different trust levels.
5. Resource isolation (CPU, memory, GC pauses) is separate from memory isolation [I].

## Gaps / not found
- verified C++ of JS-engine scale: not found.
- NOVA verified-LOC numbers: not found.
- largest Frama-C WP proof size: not found (only the 50 kloc Eva+WP figure).
- V8 sandbox design doc body: not readable via fetch.
- Mohabi/Icarus paper bodies not read (PDF extraction failed earlier).
