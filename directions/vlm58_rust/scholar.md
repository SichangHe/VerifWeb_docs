# Prior-work check (Scholar via pb-browser-page-extract, as_ylo=2022, run 2026-11-19)
(authored by agents unless marked 🧑)
Queries run: 9 (22 s apart). No CAPTCHA. Raw JSON: /tmp/vlm58/s/q*.json; snippets: /tmp/vlm58/s/all.txt.
Scholar snippets are Google's excerpts; "..." marks Scholar's own elisions. I did not read the full papers except 2610.09198 (PDF text) and the rust-vmm repo (cloned).
Unsearched (budget): Iris/RustBelt tokio, EverParse DNS, "Rust Binder formal verification" (Q9 covered it loosely), Kani s2n-quic.

## Two items you asked for

### rust-vmm virtio-queue Kani coverage (FACT; cloned https://github.com/rust-vmm/vm-virtio, read README.md and virtio-queue/src/queue/verification.rs)
README, "Kani proofs": "We run Kani proofs for each PR and on merges to the main branch. The proofs check conformance of the virtio-queue implementation to requirements from the virtio specification. Different than a unit test, a proof is checked for every possible input thus enforcing conformance."
Actual harnesses (grep `kani::proof`): only 2 enabled, both `#[kani::unwind(0)]`:
- `verify_stubregion_write_read`: the Kani stub memory region round-trips bytes (tests the stub, not the product).
- `verify_device_notification_suppression`: virtio spec 2.7.7.2 (used-buffer notification suppression, event_idx).
- `verify_add_used` (spec 2.7.8.2, out-of-bounds index must fail, used idx not incremented) is DISABLED: "Re-enable this proof once https://github.com/rust-vmm/vm-virtio/issues/373 is fixed."
Model limits (verification.rs comments): memory is a single-region stub, chosen because "this only uses a single region. Eliminating this binary search significantly speeds up all queue proofs, because it eliminates the only loop contained herein, meaning we can use `kani::unwind(0)`"; `check_range()` is overridden "because the trait-provided method cannot be proven."
Not covered (INFERENCE from the above): vm-memory (multi-region, VolatileMemory bounds), vmm-sys-util, post-activation register writes, snapshot/restore, anything in Firecracker's device code, concurrency. Spec-conformance of the queue != "host never touches memory outside the grant".

### arXiv 2610.09198 (FACT; abs page + PDF text read)
"Modular Responsiveness Verification of Rust Async Runtimes", Yanze Li, Ivan Beschastnikh, Alexander J. Summers; ESOP 2027 per arXiv page. https://arxiv.org/abs/2610.09198
Abstract: runtimes are "critical infrastructure, yet verifying them has received little attention"; liveness is hard for libraries "both concurrent and highly optimized"; they propose "a lightweight and modular proof technique" for eventual progress, implemented "as static analyses for Rust" (tool "Jackdaw" in PDF), applied to components of smol, futures-rs, and tokio ("the most widely used production runtime").
Overlap with candidate net-1: it is an abstract-interpretation-style static analysis of runtime COMPONENTS (not a Verus-verified full runtime), and the PDF text has no hit for "work-stealing"; "multi-thread" appears only as "OS threads (even a single thread)" and "spawned as a background thread". Stated limitation: "Our model cannot handle tokio's fairness mechanism, which requires pollables to cooperatively yield." So work-stealing is not claimed. It does occupy "liveness of tokio components, modular", so a pitch must differ by (a) full-runtime functional proof, (b) cross-thread stealing and wakeups.

## net.md candidate 1: verified multi-threaded async runtime
Closest papers:
1. Lion: Modular Verification of Async Runtime Liveness. T Zhou, Z Zhang, O Chowdhury, S Mu. SOSP/SIGOPS 2026. https://dl.acm.org/doi/abs/10.1145/3830418.3843879 (Scholar q1 snippet) "verified async runtime can serve as a practical drop-in replacement for Tokio in production Rust ... The goal of this section is to quantify the cost of that choice: when does work-stealing ..." (Cited by 1). Core is single-threaded (per net.md quote).
2. Modular Responsiveness Verification of Rust Async Runtimes. Li, Beschastnikh, Summers. ESOP 2027, arXiv 2610.09198 (above).
3. Formal verification of chase-lev deque in concurrent separation logic. J Choi. arXiv:2309.03642, 2023. Snippet: "thread possesses its own work-stealing deque to store tasks, ... extend our verification to support safe memory reclamation".
4. BWoS: Formally Verified Block-based Work Stealing for Parallel Processing. Wang, Trach, Fu, Behrens, et al. OSDI 2023 (usenix.org). Snippet: "have formally verified and optimized BWoS on weak memory ... atomic primitives (eg, atomic compare-and-swap and ... implementing concurrent work-stealing queues on weak memory".
5. A Verified Parallel Scheduler for OCaml 5. C Allain, G Scherer. PACMPL 2026. Snippet: "this effort, we verify the Chase-Lev work-stealing deque, as ...".
6. Saturn: a library of verified concurrent data structures for OCaml 5. Allain, Karvonen, Morel. OCaml Workshop 2024. Snippet: "queue, skiplist, hash table, workstealing deque, etc. It is well ...".
7. Validating a High-Performance Cloud Object Store with Lightweight Formal Methods. Joshi, Kragl, et al. 2026 (dl.acm.org; ShardStore-style, AWS). Snippet: "did not support the async Rust runtimes used in our production ... , we check cancellation safety by injecting cancellations at ... when the future is dropped, restoring cancellation safety."
What remains new (INFERENCE): a machine-checked proof for a Rust runtime that includes work-stealing across threads + cross-thread wakeups, on Rust atomics. The pieces exist separately (Chase-Lev in Iris/Coq; verified parallel scheduler in OCaml 5; single-thread Rust runtime in Lion), but I found no Rust, tokio-compatible, multi-threaded verified runtime. The OCaml 5 paper (item 5) is the nearest "verified parallel scheduler" and must be read; it weakens a pure "first verified work-stealing scheduler" claim. Verus weak-memory atomics question: Q3 returned no Verus-specific hit (UNRESOLVED; Verus is "linear ghost types", PLDI/OOPSLA'23 snippet, Q9: "express low-level code like doubly linked lists or safe implementations of reader-writer locks").

## net.md candidate 2: memory-bound proof for QUIC/HTTP2 state machines
Closest papers (Q4, no formal-verification hit among the top 10):
1. Identifying Logical Vulnerabilities in QUIC Implementations. Wang, Chen, Chen, Zhuge, Bai, Duan. NDSS 2026. "resource exhaustion and assertion failures, enabling denial-of-service attacks on major QUIC ... We hope this work raises awareness of resourceexhaustion logic bugs" (testing/bug finding, not proof).
2. An automated blackbox noncompliance checker for QUIC server implementations. Ang, Farrelly, Pope et al. 2025. (testing)
3. Exploring quic security and privacy: ... Joarder, Fung. IEEE TNSM 2024. "measures, such as formal verification and rigorous testing of QUIC protocol to ensure it ..." (survey calls for it).
4. Not on Scholar but from net.md: s2n-quic Kani harnesses; EverParse QUIC-LowParse (parsing only).
What remains new (INFERENCE, weak evidence: one query): proof of bounded memory / counter conservation for a QUIC or h2 state machine. Search was shallow (no "IVy QUIC", "HTTP/2" query run); IVy-based QUIC spec work (McMillan/Zuck) predates 2022 and concerns protocol correctness, not resource bounds [memory, unverified].

## net.md candidate 3: Hickory DNS parser totality + DNSSEC validation
Closest papers (Q5):
1. Proving DNSSEC Correctness: A Formal Approach to Secure Domain Name Resolution. Q Zhang, Z Shen, I Karim, E Bertino, Z Li. arXiv:2512.11431, 2025. "formally verify a critical vulnerability in the DNSSEC standards caused by the insecure coexistence of NSEC and NSEC3. We validate ..." Strongest overlap on the DNSSEC half, but at standard/model level, not implementation.
2. A formal framework for end-to-end DNS resolution. Liu, Duan, Heimes, Bearzi, Vieli, et al. SIGCOMM 2023 (ETH). "We have validated and confirmed all our new attacks on real DNS software." (model + attacks)
3. Resolve the Unresolved: Systematic Work Profiling for DNS Resolvers. Xu, Duan, Cai, Perrig. IEEE S&P 2026. "of DNS resolution in Maude, enabling the formal verification of ..."
4. ResolverFuzz. Zhang et al. USENIX Sec 2024: "G-Root performs formal verification to prove the correctness ..." (GRoot is zone-config).
5. Declarative DNS-Resolving Recursive Resolution. Linker, Huang, Basin, Duan. arXiv:2611.11689, 2026. "as signature verification, our constraint solver caches the ..."
What remains new (INFERENCE): a code-level proof for a Rust resolver (hickory) of decode totality/allocation bound and NSEC3 denial-proof checking. All hits are model-level or testing. EverParse (not searched) already covers verified parsers in general. DNSSEC code proof is plausible-new but item 1 is close on the NSEC/NSEC3 spec side.

## net.md candidate 4: cancellation safety of async Rust
Closest papers (Q2):
1. Validating a High-Performance Cloud Object Store with Lightweight Formal Methods. Joshi, Kragl, Fernando, Skotåm, et al. 2026 (ACM). "we check cancellation safety by injecting cancellations at ... when the future is dropped, restoring cancellation safety." Testing by injection, not proof, but it is the closest prior art on checking it.
2. Concurrency in Systems Programming. A Pathak, vajradevam.in (informal). "One important caveat is cancellation safety. An ... may be cancelled at any .await point if its future is dropped without ..." (tutorial, not research).
No paper found on formally verifying cancel-safety per async fn. What remains new (INFERENCE, one query): a formal drop-at-await model + proofs/lint. Risk: the Joshi et al. approach (bounded cancellation injection in a stateless model checker) pre-empts "systematic checking"; novelty must be proof/ spec of cancel-safety contracts.

## sys.md candidate 1: rust-vmm guest-memory + virtqueue layer
Closest papers (Q6-Q8):
1. Verifying dynamic trait objects in Rust. VanHattum, Schwartz-Narbonne, Chong, Sridhar. ICSE-SEIP 2022 (amazon.science). "a simple proof harness using the serial device behavior in ... The guest VM allocates a set of virtqueue data structures in ..." / "Our Firecracker case study highlights how this semantic ..." Kani on Firecracker virtio.
2. VeriSMo: A verified security module for confidential VMs. Zhou, Chen, Gong, Hawblitzel, et al. OSDI 2024. "Rust compromises the memory safety ... We utilize the state-of-the-art Rust-based verification ..." (Verus; SVSM, not VMM device emulation).
3. Verifying Rust implementation of page tables in a software enclave hypervisor. Dai, Liu, et al. SOSP 2024. "any guest physical address from untrusted ..." (Verus; page tables).
4. MicroVMM: AI-Assisted Verification-Oriented Virtual Machine Monitor. T Do, nyanwith.me (thesis-style). "VirtIO PCI transport together with split virtqueue support and a virtio-rng device" and "we derive queue activation invariants directly from the Firecracker VirtIO ..." and "our proofs establish correctness relative to the modeled ..." Closest hit: a new verification-oriented VMM with virtio queue activation invariants. Not read; venue unclear (not peer-reviewed as far as I can tell).
5. Fuzzing virtual machine monitors for improved security. Pavel, Florescu et al. 2023. "vulnerabilities in the Virtio device implementation from rust-vmm/vm-virtio using fuzzing."
6. Plus rust-vmm Kani harnesses (above).
What remains new (INFERENCE): a Verus (unbounded) proof of the REAL vm-memory/virtio-queue/vmm-sys-util code, with multi-region memory, post-activation guest writes (CVE-2026-5747 class), and snapshot/restore. Currently Kani covers 2 small proofs on a single-region stub with unwind(0), and add_used is disabled. Not new: "Kani/virtqueue conformance", "Verus VMM components" (VeriSMo), "verification-oriented VMM" (MicroVMM, if credible). Check MicroVMM before claiming.

## sys.md candidate 2: Rust Binder
Closest papers (Q9):
1. An empirical study of Rust-for-Linux: The success, dissatisfaction, and compromise. H Li, L Guo, Y Yang, S Wang, M Xu. USENIX ATC 2024. "data structures such as a doublylinked list, where each node is ... Interestingly, we find that binder driver in Rust introduces ... , eg, using formal verification to verify the correctness of using ..." (calls for verification; also TOCS 2026 extension "Rust Meets Linux").
2. Rust for Linux: Understanding the security impact of Rust in the Linux kernel. Li, Narayanan, Chen, Zhang, et al. ACSAC 2024. "in RFL, we analyze kernel branches of Binder, AGX, and NVMe for ... We argue that low-burden verification of Rust code can ..."
3. Verus: Verifying Rust programs using linear ghost types. Lattuada, Hance, Cho, Brun, et al. OOPSLA 2023. "express low-level code like doubly linked lists or safe implementations of reader-writer locks ..."
No hit for verification of kernel::list or Binder. What remains new (INFERENCE, one query): verified intrusive-list abstraction as used in Rust Binder. Prior art only motivates it. Search was thin (no Atmosphere/Asterinas/RustBelt-intrusive-list query).

## sys.md candidate 3: sudo-rs
Not searched (the file itself rejects it).
