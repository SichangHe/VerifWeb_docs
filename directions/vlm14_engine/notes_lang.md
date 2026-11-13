# vlm14: new systems language vs Rust "flavor" for a verified JS engine/JIT

(authored by agents unless marked 🧑)

Q (🧑, verbatim): "Do we need a new systems language for that or do we just write a \"flavor\" of Rust?"

Caveat: all quotes below come from WebFetch/WebSearch tool output. Quotes in double quotes inside a tool summary are
likely verbatim from the source; unquoted lines are tool paraphrase and are marked (P). No page was re-fetched raw. Dates
in results (2026) are as the tool reported them; unverified.

## Verus
- what: "Verus is a tool for verifying the correctness of code written in Rust." "currently supports a subset of Rust" — https://github.com/verus-lang/verus
- largest artifacts: Anvil "by far the largest Verus-verified system" (P, VeruSAGE) — https://arxiv.org/html/2512.18436v2 ; Anvil = verified k8s controllers (ZooKeeper, RabbitMQ, FluentBit) (P) — https://www.usenix.org/system/files/osdi24-sun-xudong.pdf
- Atmosphere (SOSP'25): "6K lines of executable code took less than 2.5 person-years"; proof:code "3.32:1" (P) — https://dl.acm.org/doi/10.1145/3731569.3764821 . [I] ~20K proof lines (my multiplication, not paper's).
- Verus SOSP'24 case studies: "6.1K lines of implementation and 31K lines of proof" (P) — https://dl.acm.org/doi/10.1145/3694715.3695952
- VeriSMo (OSDI'24, SEV-SNP security module): written in Rust, verified with Verus; uses a fork of a very old Verus (P) — https://arxiv.org/html/2512.18436v2
- verified x86-64 page table (NRKernel) in the Verus SOSP'24 paper (P) — same.
- f64: partial and still buggy. Tool summary: Verus models f32/f64 as IEEE bit patterns; PR #3285 (Oct 2026) tags ops by float width; "floats in generic code are still not supported"; open soundness issues on NaN equality (#3207) and -0.0 patterns (#3194) (P). — https://github.com/verus-lang/verus/pull/3285 , /pull/3207 , /issues/3194. Older Verustd list: "Floating point numbers unsupported" (P, likely stale) — https://github.com/KaminariOS/Verustd
- raw pointers: "its simplified model for 'raw pointers' only handles those that point into the global heap" (P of OOPSLA'23) — https://arxiv.org/pdf/2303.05491 ; now `vstd::raw_ptr` targets "real Rust pointers, including all their subtleties on the Rust Abstract Machine" (P) — https://docs.rs/vstd ; issue says new interface on `*mut T`/`*const T` — https://github.com/verus-lang/verus/issues/1227
- machine-code emission: not found. No Verus-based verified JIT/assembler found (search result, P). Ghost code erased; output goes through normal rustc, so rustc/LLVM unverified (P) — search summary, no primary URL.

## Aeneas / Charon -> Lean
- "a verification toolchain for Rust programs. It relies on a translation from Rust's MIR internal language to a pure lambda calculus." Backends "F*, Coq, HOL4 and LEAN"; Lean and HOL4 "most mature". — https://github.com/AeneasVerif/aeneas
- unsafe: "currently functionalizes a subset of safe Rust." Unsafe/concurrency to be lifted by "ongoing work on separation logic." — same URL.
- floats: not found on README.
- SymCrypt: "237 KLOC Lean development establishes safety, panic-freedom, and functional correctness of 16.7 KLOC of Rust code" (P) — https://arxiv.org/html/2609.15648v1 ; "complete proofs for the Rust ML-KEM and SHA3 code that is being used in insiders builds of Windows today" (P) — https://www.microsoft.com/en-us/research/blog/verifying-rust-cryptography-in-symcrypt-from-standards-to-code/
- [I] Strong for pure/safe code; the pure-functional model fits "explicit side effects" but not a JIT's unsafe code buffers.

## hax (Cryspen), libcrux
- "hax is a tool for high assurance translations of a large subset of Rust into formal languages such as Lean, F* or Rocq." F* backend "Stable."; "mutable references (aka `&mut T`) are forbidden on return types and when aliasing." — https://github.com/cryspen/hax
- libcrux ML-KEM "formally verified for panic freedom, correctness, and secret independence in F* using the hax toolchain" — https://github.com/pq-code-package/rust-libcrux ; they had to "avoid the usage of certain traits and iterators" (P) — https://cryspen.com/post/ml-kem-implementation/ ; "Not all the code in libcrux is formally verified yet" (P) — https://cryspen.com/post/strengths-and-limitations/
- Firefox deployment of libcrux: not found in primary source (only HACL* C code deployed; a third-party directory claims otherwise).

## Creusot / Prusti
- Creusot: "a deductive verifier for Rust code"; translates to "Coma, an intermediate verification language of the Why3 Platform." — https://github.com/creusot-rs/creusot . Unsafe: recently added linear ghost types "pioneered by Verus" for unsafe pointer code (P) — https://github.com/model-checking/verify-rust-std/issues/493 ; rust-bitcoin PR #6942 uses it on unsafe ArrayVec (P) — https://github.com/rust-bitcoin/rust-bitcoin/pull/6942 . Floats: not found.
- Prusti: pinned to ~Aug 2023 nightly; safe code only (P, third-party decision record) — https://github.com/greeng3/provablerequirements/issues/487 . ETH thesis added f32/f64 via bit-blasting; "not possible to verify it with f64's" for some programs (P) — https://ethz.ch/content/dam/ethz/special-interest/infk/chair-program-method/pm/documents/Education/Theses/Lukas_Friedlos_BA_report.pdf

## Kani / verify-rust-std
- "a bit-precise model checker for Rust"; "particularly useful for verifying unsafe code blocks" — https://github.com/model-checking/kani . Floats: not found in README.
- verify-rust-std: "to have a verified Rust standard library and prove that it is safe"; 10 of 29 challenges resolved (Kani 7, VeriFast 2); tools accepted: Flux, ESBMC, Kani, KMIR, VeriFast; flt2dec challenge open — https://github.com/model-checking/verify-rust-std
- [I] model checker = bounded; not a proof of an entire engine.

## Flux, RefinedRust
- Flux: "a refinement type checker for Rust." — https://github.com/flux-rs/flux . Targets safe code (P, from RefinedRust comparison below).
- RefinedRust (PLDI'24): "foundational semi-automated functional correctness verification of both safe and unsafe Rust code"; proofs checked in Coq/Iris; evaluated on Rust std `Vec` (P) — https://dl.acm.org/doi/10.1145/3656422 . "requires significantly more annotations and proof guidance, and handles a smaller subset of Rust" than Flux (P). Floats: not found. Machine code: not found.

## F*/Low*, HACL*, Vale, EverParse
- HACL* in Low*, "compiled to C by the KaRaMeL compiler"; "now in maintenance mode ... prior to the removal of the Low* toolchain" (P) — https://github.com/hacl-star/hacl-star ; https://project-everest.github.io/
- Vale: "a tool for constructing formally verified high-performance assembly language code" (P); ValeCrypt emits F*; Low* calls verified Vale asm (P) — https://project-everest.github.io/ , https://www.microsoft.com/en-us/research/publication/vale-verifying-high-performance-cryptographic-assembly-code/
- Deployed: "Mozilla Firefox, the Linux kernel, mbedTLS, the Tezos blockchain, ElectionGuard, Wireguard" (P; page "several years old") — https://project-everest.github.io/
- [I] Vale is the only found precedent for verified emitted assembly, but it verifies hand-written asm, not a runtime code generator.

## Dafny
- Rust backend: "not an officially supported backend yet" (P of issue); open bugs where generated crate fails to compile (#6623) — https://github.com/dafny-lang/dafny/issues/6623 , /6620 , /5561
- AWS: Cedar modeled in Dafny, later Lean; production engine in Rust with differential testing (P) — https://cacm.acm.org/practice/systems-correctness-practices-at-amazon-web-services/ ; AuthV2: proved DafnyLite compiled to Java (P) — https://assets.amazon.science/bb/40/22ac44f84f6d8eb625ac9666a00f/formally-verified-cloud-scale-authorization.pdf
- Encryption SDK in Dafny -> .NET/Rust: only from Grokipedia (weak source).

## Lean 4 compiled
- Compiles to C, ref counting: "the compiler supports only one backend where we emit C code" (2019) — https://arxiv.org/pdf/1908.05647 ; Perceus-style reuse (P).
- Runtime: "Lean needs the allocator in its runtime"; runtime large, GMP-dependent (P, 2021 Zulip) — https://leanprover-community.github.io/archive/stream/270676-lean4/topic/System.20programming.20using.20Lean.204.html
- Ray tracer: C was "about 30x faster" (P, 2021 anecdote) — https://news.ycombinator.com/item?id=25987949 . No recent benchmark found. f64: not checked. [I] Lean as spec/proof language, not engine implementation language.

## Verified JITs (prior art, none in a Rust flavor)
- Jitterbug (OSDI'20): verified BPF JIT for RISC-V, found 16 bugs in 5 deployed JITs (P) — https://www.usenix.org/conference/osdi20/presentation/nelson
- VeRA (range analysis for Firefox JS JIT) and Icarus (verified-safe JIT framework, re-implemented parts of Firefox JIT, output C++) (P) — https://cseweb.ucsd.edu/~dstefan/pubs/brown:2020:vera.pdf
- Crocus (ASPLOS'24): Cranelift instruction selection (P) — https://dl.acm.org/doi/pdf/10.1145/3617232.3624862
- FM-JIT: CompCert backend as verified JIT in Coq (P) — https://arxiv.org/pdf/2212.03129 ; CoreJIT: verified speculation/deopt (P) — https://janvitek.org/pubs/popl21.pdf

## New languages for verified systems: outcome
- Cogent: "purely functional, linearly typed"; "no support for recursion, iteration, borrowing, or mutable state" (P of RustBelt) — https://plv.mpi-sws.org/rustbelt/popl18/paper.pdf ; BilbyFs "0.6py/kLOC" vs 1.4 for seL4; file systems only partly verified (P) — https://dl.acm.org/doi/pdf/10.1145/2980024.2872404 ; project page under "OLD/" URL (P) — https://trustworthy.systems/projects/OLD/seL4-verification/ . "Discontinued": not found.
- Pancake (CakeML, PLOS'23): "ease of verification over achieving safety"; lesson: Cogent users "difficult to understand the language" (P) — https://cakeml.org/plos23.pdf
- Low*: a subset of F* -> C; now maintenance mode (see above).
- Ivy (McMillan), Mantle: not found (search returned unrelated Ivy).

## Takeaways [I]
- The trend found: verify Rust subsets (Verus, Creusot, Aeneas, hax) rather than a new language; new-language efforts (Cogent, Low*) are archived or in maintenance (P status).
- Gaps for a JIT: (1) f64 in Verus is immature; (2) generic float ops unsupported; (3) no tool verifies runtime machine-code emission; Vale/Jitterbug/FM-JIT are the nearest precedents; (4) unsafe in Aeneas unsupported.
