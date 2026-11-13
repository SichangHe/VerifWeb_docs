# Engine questions: verify the JS engine? verified JIT? monads? new language?
(authored by agents unless marked 🧑)

Labels: [F] fact with quote+URL, [P] quote relayed by a search/fetch tool (recheck before citing), [I] inference, [O] opinion. Full quotes: `notes_cpp.md`, `notes_jit.md`, `notes_lang.md`; PDFs as text in `pdf/`. Reading only; nothing run, nothing published.

## Direct answers

(a) 🧑 "If we do things like sharing processes for browser tabs, do we need to verify the JS engine?"
- [O] no, not the whole engine. What must hold is a short list of isolation properties, and these can be enforced by a small checked layer around an untrusted engine
  1. each tenant's heap and isolate state stay separate
  2. JIT code stays inside its tenant's region and cannot change memory protection or jump anywhere it likes
  3. code outside the sandbox treats every in-sandbox value as untrusted
  4. Spectre is handled separately; a memory-safety proof does not cover it

(b) 🧑 "We cannot really verify the ones written in C++ like we do for Rust, right? Or can we verify enough?"
- [I] right for full correctness: no verified C++ anywhere near JS-engine size was found. Verified C exists, but it is 10–100x smaller than an engine
- [O] "enough" is possible only for the properties above, at the sandbox boundary and JIT output, not for V8's or SpiderMonkey's logic

(c) 🧑 "write a new JS JIT ... achieve SoTA performance while being formally verified?"
- [O] not workable as stated. No verified JS engine or JIT exists, and verified compilers still trail unverified ones
- realistic subsets: verify one JIT component inside a real engine (as Icarus did), or a checker for JIT output

(d) 🧑 "make all side effects explicit in the core ... with Monads"
- [I] good for the spec and proofs, which is how seL4 and CakeML use monads. It does not make the engine fast. The speed-critical parts (inline caches, GC, code generation) are the effectful ones, where proofs are weakest

(e) 🧑 "Do we need a new systems language ... or ... a 'flavor' of Rust?"
- [I] a Rust flavor. Recent verified-systems work verifies Rust subsets (Verus, Aeneas, hax, Creusot). The new-language attempts (Cogent, Low*) faded. Two gaps remain in every option: f64 and verifying emitted machine code

## Evidence

(a) minimum for process sharing
- [F] V8 sandbox threat model: "The sandbox assumes that an attacker can arbitrarily and concurrently modify any memory inside the sandbox address space ... it is assumed that an attacker will be able to read memory outside of the sandbox, for example through hardware side channels." (https://raw.githubusercontent.com/v8/v8/main/src/sandbox/README.md)
  - [I] V8's own design already treats the engine as untrusted inside its cage, so isolation does not need a correct engine
- [P] property 3 failed in practice: "Out-of-sandbox code can still be undermined by corrupted in-sandbox values" (https://v8.dev/blog/sandbox)
- [P] Cloudflare runs tenants in one process but adds layers: "V8 itself cannot defend against Spectre"; timers frozen during execution; free and enterprise tenants never share a process (https://developers.cloudflare.com/workers/reference/security-model/)
- [F] Spectre in production: "leaking up to 12 bit/s with a 99% accuracy" (https://blog.cloudflare.com/revisiting-spectre-attacks-on-workers/)
- [F] earlier local measurement (vlm10_share): about a third of V8 JIT memory accesses use raw 64-bit pointers when pointer compression is off, so an output checker needs the sandbox build

(b) verifying C/C++ at scale
- seL4 [P]: "8,700 lines of C code and 600 lines of assembler"; proof "200,000 lines of Isabelle script" (https://www.sigops.org/s/conferences/sosp/2009/papers/klein-sosp09.pdf)
- Frama-C [P]: largest found is "50 kloc" nuclear control code, proving absence of runtime errors, not full correctness (https://list.cea.fr/en/page/frama-c/)
- CBMC at AWS [P]: "171 entry points over nine modules in the AWS C Common library", one engineer and two interns, 24 weeks (Amazon Science paper, URL in notes_cpp.md)
- RefinedC [P]: "our largest case study applies RefinedC to a version of the page allocator of the Hafnium hypervisor" (https://plv.mpi-sws.org/refinedc/paper.pdf)
- HACL*/Low* [F]: "deployed in several production systems, including Mozilla Firefox, the Linux kernel" (https://project-everest.github.io/)
  - [I] this is crypto written in F* and compiled to C, not verification of existing C
- C++
  - [P] BRiCk/SkyLabs verified NOVA hypervisor C++, but "a sequentially-consistent version" (tech report, URL in notes); size not found
  - [P] Frama-Clang: "known to be incomplete and comes without any bug-freeness guarantees" (https://frama-c.com/fc-plugins/frama-clang.html)
- partial assurance for V8/SpiderMonkey
  - Mohabi [F]: "leverages software-based fault isolation (SFI) to ensure JavaScript engine bugs cannot affect the rest of the browser", ~25% slowdown on JetStream/Speedometer (https://www.usenix.org/conference/osdi26/presentation/sharma)
  - JIT translation validation for V8 (Kwon et al., ISSTA 2024) checks semantic correctness, not isolation
  - Fuzzilli finds JIT bugs but proves nothing (https://github.com/googleprojectzero/fuzzilli)

(c) verified JITs
- Icarus [F]: "automatically, formally verified to be safe, and which can then be converted to C++ that can be linked into browser runtimes" (https://dl.acm.org/doi/abs/10.1145/3694715.3695949)
  - [F, local PDF] scope is SpiderMonkey's inline-cache stub generators; "no performance overhead"; tool is "roughly 20K SLOC of Rust"
- Barrière et al. POPL 2023 [F, local PDF]: "around 15K lines we wrote, and includes more than 160K lines from CompCert"; "up to 40 times speedups ... compared to running our extracted interpreter alone"
  - [I] a toy language compared only with its own interpreter; nowhere near V8
- CompCert [F, local PDF]: "only 7% slower than gcc -O1 and 12% slower than gcc -O2" (gcc 4.0.1-era measurement)
- CakeML [F, local PDF]: "relatively close" on small pure benchmarks; "we do not currently have any optimisations to remove bounds checks"
- Jitk/Jitterbug/Serval: verified eBPF JITs; eBPF programs are small and loop-bounded
- JS semantics (JSCert, KJS, JISET/ESMeta) formalize the spec; none models a JIT, inline caches or GC
- cost [P]: V8 ~2.3M lines (stale Open Hub figure); largest Verus systems ~6K code lines (Atmosphere: "less than 2.5 person-years")
  - [I] V8 is ~400x Atmosphere's size; the 2023 Coq JIT shows the proof gap even for a toy
- [O] realistic subsets, best first
  1. checker for JIT output enforcing the isolation properties in (a); this connects to process sharing
  2. Icarus-style verified components inside SpiderMonkey/V8
  3. verified interpreter core for a Rust engine (Boa/Nova), no JIT (vlm11_jsengine)

(d) explicit effects / monadic core
- seL4 [P]: "We formalise the nondeterministic state monad with exceptions and failure in Isabelle/HOL." The monad is in the spec; shipped C is proved to refine it
- CakeML monadic translator [P]: supports "references, exceptions, I/O"; the effects become ordinary state passing
- Interaction trees [P]: "A coinductive variant of 'free monads'"; used for compiler proofs, no performance claim
- Perceus/Koka [F, local PDF]: functional code "within 10% of" in-place C++ on one tree benchmark; "we currently do not supply a cycle collector"
  - [I] JS heaps have cycles, so this does not carry over directly
- Cogent [P]: no "recursion, iteration, borrowing, or mutable state"; worked for file systems
- [I] pros: effects become visible, so proofs can say what each step touches; matches Aeneas/hax, which turn Rust into pure functions
- [I] cons: a JIT engine is mostly in-place mutation and generated code; a monadic layer either compiles away (no gain at run time) or costs speed. Haskell-written JS engine benchmarks: not found

(e) language
- Verus [F]: "currently supports a subset of Rust" (https://github.com/verus-lang/verus); f64 partial: [P] "floats in generic code are still not supported", open NaN and -0.0 soundness issues (#3207, #3194)
- Aeneas [P]: "currently functionalizes a subset of safe Rust"; SymCrypt: "237 KLOC Lean development" for "16.7 KLOC of Rust code" (https://arxiv.org/html/2609.15648v1)
- hax [F]: "a large subset of Rust into formal languages such as Lean, F* or Rocq"; used for libcrux ML-KEM
- Creusot, RefinedRust, Kani handle some unsafe Rust; float support not found
- Low* [P]: "now in maintenance mode ... prior to the removal of the Low* toolchain" (https://github.com/hacl-star/hacl-star)
- Pancake [P]: Cogent users found it "difficult to understand the language" (https://cakeml.org/plos23.pdf)
- Lean 4 compiled: no recent performance data found; [I] fit for specs, not the engine
- machine-code emission: no Rust verifier handles it; precedents are Vale (hand-written assembly) and Jitterbug (eBPF)

## I don't know
- whether a JIT-output checker for many tenants is novel (only abstracts searched in vlm10)
- V8/SpiderMonkey/JSC team sizes; current V8 line count
- whether advisors value (c)-style "verified component in real engine" over a new engine; human judgment
