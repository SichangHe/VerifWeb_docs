# prior work: verified, automatic memory minimization for Rust→Wasm web apps

(authored by agents unless marked 🧑)

Survey for the human idea (🧑, verbatim): "What if we optimize for minimum memory usage? Let's say we have a web app. Can we rewrite it in Rust? And have some sort of automatic optimization that we formally verify to preserve the functionality of the app. And then that optimization would shrink the data structures and so on, so that it uses minimum memory on the user's device. And then we compile that to WebAssembly. ... I was thinking maybe we can pick some particular Rust frontend frameworks, like [Dioxus]. Or maybe even the more bloated ones like [Yew]. And make it so that out of the box, any apps written in that thing would be optimized for memory."

Method: Google Scholar (22 queries, mostly `as_ylo=2022`, older classics unfiltered), Semantic Scholar API for abstracts, primary web sources. Quotes are verbatim; "…" fragments are Google Scholar snippets, not full abstracts. Labels: fact = stated by source; inference/belief = mine.

## takeaway

- every ingredient exists separately: automatic layout shrinking (unverified, mostly Java/C), verified layout refinement (programmer-specified, not automatic), verified compilers to Wasm (no memory optimization)
- I found no work combining automatic + verified + memory-minimizing + framework-level for web apps; I believe the combination is new, but Scholar recall is limited, so "I don't know" for certain
- biggest open risk (inference): it is unmeasured how much of a Rust/Wasm frontend's memory is shrinkable Rust heap data vs. DOM/JS/Wasm-binary memory; no footprint study of Dioxus/Leptos/Yew/Sycamore found

## 1. automatic data-structure / layout shrinking (unverified)

- Sartor, Hirzel, McKinley, "No bit left behind: the limits of heap data compression", ISMM 2008, https://dl.acm.org/doi/abs/10.1145/1375634.1375651
  - limit study of heap compression in Java; snippet: "… of each object and … objects in one stream, and all objects (both JVM and application) in another …"
  - not verified; Java. open: tells how much headroom exists, not how to obtain it safely
- Chen, Kandemir, Irwin, "Exploiting frequent field values in Java objects for reducing heap memory requirements", VEE 2005, https://dl.acm.org/doi/abs/10.1145/1064979.1064990
  - snippet: "… object compression schemes that exploit frequent field values to reduce heap space consumption of Java … The first scheme is oriented towards compressing the fields that hold zero or …"
  - not verified; JVM-level
- Xu, "CoCo: Sound and adaptive replacement of Java collections", ECOOP 2013, https://link.springer.com/chapter/10.1007/978-3-642-39038-8_1
  - snippet: "… run-time bloat [6]—excessive memory usage and computation … in the Java Collections Framework that offers automated …"
  - "sound" per title, but no mechanized proof (my reading of title/snippet only); Java collections
- Lattner, Adve, "Transparent pointer compression for linked data structures", MSP 2005, https://dl.acm.org/doi/abs/10.1145/1111583.1111587, and "Automatic pool allocation", PLDI 2005, https://dl.acm.org/doi/abs/10.1145/1065010.1065027
  - snippet: "… compiler transformation, Automatic Pointer Compression, which … By shrinking pointers from 64-bits to 32-bits …"
  - not verified; C/LLVM. inference: wasm32 pointers are already 32-bit, so the gain moves to 16-bit indices into pools
- V8 pointer compression, https://v8.dev/blog/pointer-compression
  - "we observed that Pointer Compression reduces V8 heap size up to 43% ! In turn, it reduces Chrome's renderer process memory up to 20% on Desktop."
  - engine-level, not verified; evidence that pointer-width shrinking pays off on real websites
- Stephenson, Babb, Amarasinghe, "Bidwidth analysis with application to silicon compilation", PLDI 2000, https://dl.acm.org/doi/abs/10.1145/358438.349317
  - range analysis to narrow integer widths; thesis snippet: "… types, as denoted by the narrower 16, 8, and 1 bit bars …"
  - targets hardware, not heap layout; not verified
- Huang, Jiang, Gao, "Structure peeling based on link time optimization in the GCC compiler", 2022 (IEEE)
  - snippet: "… Structure field reordering creates a new structure definition …"
  - C/GCC; locality focus; not verified
- Rietveld, Wijshoff, "Automatic Compiler-Based Data Structure Generation", arXiv 2203.07109, 2022
  - "we propose to move towards the specification of programs without explicitly specifying the data structure. The compiler will automatically generate actual data structures and executable code starting from this specification."
  - sparse matrices; performance, not memory; not verified
- Hawkins, Aiken, Fisher, Rinard, Sagiv, "Data representation synthesis", PLDI 2011, https://dl.acm.org/doi/abs/10.1145/1993498.1993504
  - "We describe a language of decompositions that permit the user to specify different concrete representations for relations, and show that operations on concrete representations soundly implement their relational specification."
  - proven sound on paper; user picks representation; not memory-driven
- rustc's own layout (fact: Rust reference, https://github.com/rust-lang/reference/blob/master/src/type-layout.md): "The only data layout guarantees made by this representation are those required for soundness."
  - so rustc may already reorder fields and use niches; any new pass competes with this baseline
- Bartell-Mangel, "Filling a Niche: Using Spare Bits to Optimize Data Representations", POPL SRC 2022, https://noahlev.org/papers/popl22src-filling-a-niche.pdf
  - "Rust's compiler—and other compilers—record the niches in a type's representation so they can be used to encode tags of containing types. However, the algorithm has several subtleties … and to our knowledge, it has not before been formally described or proven correct."
  - goal includes "establish a proof of correctness (we sketch a proof in §3)": a sketch, not mechanized
- string interning, struct-of-arrays: I found no recent paper on automatic, verified versions for Rust; "Efficient Symbolic Computation via Hash Consing" (Zhu et al., arXiv 2025) is domain-specific. I don't know of more

## 2. verified compilers and transformations

- Chen, Lafont, O'Connor, Keller, et al., "Dargent: A silver bullet for verified data layout refinement", POPL 2023, https://dl.acm.org/doi/abs/10.1145/3571240
  - "a data layout description language and data refinement framework, called Dargent, which allows programmers to declaratively specify how algebraic data types are laid out in memory … The Dargent framework generates C code that manipulates data directly with the desired memory layout, while retaining the formal proof that this generated C code is correct with respect to the functional semantics."
  - verified (Isabelle); Cogent→C. open: layout is programmer-written, not chosen automatically to minimize memory; not Rust/Wasm
- Monniaux et al., CompCert work:
  - "Memory Simulations, Security and Optimization in a Verified Compiler", CPP 2024, https://dl.acm.org/doi/abs/10.1145/3636501.3636952: "the program after the insertion of the security feature, or after applying the optimization, must simulate the original program despite a different memory layout."
  - "Formally Verifying Optimizations with Block Simulations", OOPSLA 2023, https://dl.acm.org/doi/abs/10.1145/3622799: "we co-design our untrusted optimizations and their validators"
  - verified (Coq); C. relevance: memory-injection proofs and untrusted-optimizer + verified-validator are the reusable techniques; neither shrinks data types
- Meier, Jensen, Pichon-Pharabod, et al., "CertiCoq-Wasm: A Verified WebAssembly Backend for CertiCoq", CPP 2025, https://dl.acm.org/doi/abs/10.1145/3703595.3705879
  - "implemented and verified in the Coq proof assistant, and is mechanised with respect to the WasmCert-Coq formalisation of the WebAssembly standard"
  - verified end-to-end to Wasm; source is Gallina, not Rust; no memory minimization
- Bosamiya, Lim, Parno, "Provably-Safe Multilingual Software Sandboxing using WebAssembly", USENIX Security 2022 — verified Wasm→native for safety, not memory
- translation validation for LLVM (Alive2 line; e.g. "Translation Validation for LLVM's AArch64 Backend", 2025, https://dl.acm.org/doi/abs/10.1145/3729322 is not it — see Scholar query "translation validation LLVM Alive2 memory")
  - inference: Alive2 validates IR-level rewrites within one function; data-layout changes across a whole program are outside its usual scope; I don't know of Alive2 work on type-layout changes
- Rust verifiers (Verus, Aeneas, Creusot, Kani): I found no paper using them to verify a layout-changing transformation; I don't know if one exists

## 3. Rust/Wasm size and memory work

- Ayers et al., "Tighten Rust's Belt: Shrinking Embedded Rust Binaries", LCTES 2022, https://dl.acm.org/doi/abs/10.1145/3519941.3535075
  - "We find four major causes of this growth: monomorphization, inefficient derivations, implicit data structures, and missing compiler optimizations."
  - binary size, manual principles; not verified, not heap memory
- Liu et al., "Exploring missed optimizations in WebAssembly optimizers", ISSTA 2023, https://dl.acm.org/doi/abs/10.1145/3597926.3598068 — wasm-opt missed optimizations: snippet "… size and runtime performance of the generated wasm binary …"; code size, not data
- Wen, Dietrich, "Wasmslim: Optimizing WebAssembly binary distribution via automatic module splitting", 2023 (IEEE) — code size/download
- fact (my knowledge of the Wasm spec, not from search): linear memory can grow but not shrink, so peak heap use sets the footprint; this favors shrinking peak data

## 4. footprint of web apps and Rust frontend frameworks

- Asegehegn, "Evaluation of Rust and WebAssembly when building a Progressive Web Application: An analysis of performance and memory usage", thesis 2022, https://www.diva-portal.org/smash/record.jsf?pid=diva2:1668630
  - snippet: "… Yew was used as the Wasm framework when conducting the … Wasm frameworks could be evaluated to take a broader look …"
  - only Yew; student thesis
- Nilsson, Trattner, "Analyzing front-end performance using WebAssembly", Lund MSc 2022; Eerola, Tampere thesis on Leptos/Dioxus (Finnish) — no memory focus seen in snippets
- js-framework-benchmark, https://github.com/krausest/js-framework-benchmark — includes Rust frameworks and memory metrics, e.g. "run memory: Memory usage after adding 1,000 rows."
  - the only systematic Dioxus/Leptos/Yew/Sycamore memory comparison I found; not peer-reviewed
- Naseer, Benson, "JS capsules", SIGMETRICS — fine-grained JS memory measurement on mobile web; JS-only
- gap: no paper found breaking down a Rust/Wasm frontend's memory into Wasm heap vs. DOM vs. JS glue

## closest works and novelty

1. Dargent (POPL 2023): verified layout refinement; missing automatic choice, memory objective, Rust/Wasm
2. Bartell-Mangel niche (2022): Rust's existing layout optimization, proof only sketched; missing mechanized proof and further shrinking
3. CoCo (ECOOP 2013) / Sartor et al. (ISMM 2008): automatic memory shrinking with real savings; missing formal verification, Rust, web
4. CertiCoq-Wasm (CPP 2025) + CompCert memory-injection proofs (CPP 2024): verified compilation to Wasm and verified layout-changing proofs; missing memory minimization
5. V8 pointer compression: evidence of up to 43% heap savings on real sites; engine-level, unverified

verdict (belief): the full combination (framework-level, out of the box for every app, formally verified, memory-minimizing, Rust→Wasm) appears new. Weakest premise (inference): rustc already reorders fields and uses niches, and wasm32 already halves pointers, so remaining headroom must come from range-based narrowing, index compression, interning, and collection choice; whether that headroom is large on real Dioxus/Yew apps is unknown and should be measured first.
