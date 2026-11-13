# Q2: How much code can Verus handle today? (scale, proof effort, verification time)
(authored by agents unless marked 🧑)

Question (Nov 3 2026 meeting): "what is the size of code that today it can deal with?"
Participant: "existing various projects, they were, like. thousands of lines only, and it takes… what? I think they said less than a half an hour"

## Takeaway
- [Fact] Participant is roughly right on size: published Verus systems are ~0.4K-6K lines of executable code each (tens of K counting proof/spec/trusted). Largest: Anvil (3 Kubernetes controllers).
- [Fact] "Less than half an hour" is too pessimistic: whole projects verify in seconds to ~9 min (8.5 min = 511 s for one Anvil ZooKeeper proof, single-threaded), and ~1-3 min with parallelism.
- [Inference] The ceiling is not solver speed on the whole project but proof-writing effort (proof is 4-13x the code) and modular verification keeping each query small. No evidence found of Verus on >10K lines of executable code.

## Verus SOSP 2024 (primary)
URL: https://www.chajed.io/papers/verus:sosp2024.pdf (Lattuada et al., "Verus: A Practical Foundation for Systems Verification")
- [Fact] "together comprising 6.1K lines of implementation and 31K lines of proof. Verus verifies code 3-61x faster and with less effort than the state of the art." (abstract)
- [Fact] "In total, we verify over 6.1K source lines of Rust code, entailing over 31K source lines of proof." Machine: "AWS EC2 m5.8xlarge instance ... with 16 cores (with multithreading disabled) and 128GiB of memory." (Sec. 4)
- [Fact] Figure 9 rows (columns, my reading of the extracted table: Trusted, Proof, Exec lines, ratio, then times in seconds; the time column labels were lost in text extraction, so which column is 1-core/8-core/SMT is NOT verified): 
  "Page table 1117 5329 400 13.3 63 34 37"; "Mimalloc 282 13703 3178 4.3 262 55 152"; "P. log 1284 2913 739 3.9 12 6 9"; "→ Verus [NR] 369 5237 736 7.1 17 9 22"; "→ L.Dafny [IronSync NR] 104 7828 730 10.7 1089 228 2063"; "Verus total 4692 31231 6119 5.1".
  Caption: "Times are seconds to successfully verify the entire project. SMT is the total size of queries sent to Z3."
- [Fact] "our page table consists of 400 lines of executable code, which required 5329 lines of proof, resulting in a relatively high 13.3:1 proof-to-code ratio."
- [Fact] "Verus-mimalloc has about 3.1K lines of executable code, while the original is about 10K lines of code." "Figure 9 shows a favorable proof-to-code-ratio of 4.3."
- [Fact] "Verus verifies the log implementation in 12s with a proof-to-code ratio of 3.9"
- [Fact] NR port: "Verus also improves the verification time by two orders of magnitude. Such speed creates a qualitative advantage: Where we might verify one function at a time with a slower tool, we iterated while verifying the entire project, which provides an early warning when a change to a function contract breaks a proof elsewhere." (modular: contract change breaks callers)
- [Fact] IronKV port: "95% smaller query sizes and 10x faster verification."
- [Fact] Trade-off (small queries): "A major cause is Verus's emphasis on concise SMT queries" (vs. Dafny/Creusot 24-61x slower on doubly linked list). Linear in memory ops: "Verus remains linear (with a slope of ~1.6ms/push)".
- [Fact] Comparison: "Ironclad project [12] had a proof-to-code ratio of 5 : 1", "Hyperkernel reports 0.03:1" (push-button, low ratio).

## Anvil (OSDI 2024; largest Verus system per VeruSAGE)
URL: https://www.usenix.org/system/files/osdi24-sun-xudong.pdf (Sun et al.)
- [Fact] Table 1 totals: "Total (all) 2326 3940 23975 1208 (401)" = trusted 2326, exec 3940, proof 23975 lines, 1208 s (401 s in parallel). Caption: "Time in brackets is obtained by running the verifier in parallel (11 threads on 6 cores)."
- [Fact] "Verifying each controller takes under 3 minutes in real time on a 6-core 16 GB laptop with 11 parallel threads."
- [Fact] Per controller: ZooKeeper "Total 950 1134 8352 520 (154)"; RabbitMQ "Total 548 1598 7228 341 (151)"; FluentBit "Total 828 1208 8395 347 (96)". Hardest liveness proof: "Liveness (ESR) 94 – 7245 511" (s, ZooKeeper).
- [Fact] Per-function: "87% of proof functions verify in under ten CPU seconds, and the slowest of them takes 120 CPU seconds."
- [Fact] "The proof-to-code ratio ranges from 4.5 to 7.4 across three controllers." "Implementing and verifying each controller takes around 2.5 person-months."
- [Fact] Framework: "the Anvil framework consists of 5353 lines of reusable lemmas and 7817 lines of trusted code ... All the lemmas are verified in under one minute."
- [Fact] Incremental: new features cost e.g. "403 lines in total and 211 in the proof"; proof repaired per feature.
- [Fact] Largest-system claim: "Anvil is by far the largest Verus-verified system, consisting of multiple verified Kubernetes controllers." (VeruSAGE, https://arxiv.org/pdf/2512.18436, Dec 2025)

## Atmosphere microkernel
- [Fact, KISV'23 / project page] "On average our code has proof-to-code ratio of 7.5:1 which is significantly lower than in prior approaches." https://mars-research.github.io/projects/atmo/
- [Claim via search-engine snippet of ACM abstract; NOT verified by me, ACM returned 403] SOSP'25 "Atmosphere: Practical Verified Kernels with Rust and Verus": "On average, our code has a proof-to-code ratio of 3.32:1 and completes verification in less than 20 seconds on a modern laptop". Also snippet: ~6K lines executable, <2.5 person-years (not confirmed). https://dl.acm.org/doi/10.1145/3731569.3764821 . Check the paper before citing.
- [Fact] Unreleased in full: "the whole Atmosphere (OS) codebase was not released" at the time of VeruSAGE (Dec 2025).

## Other
- [Fact] VeruSAGE-Bench (https://arxiv.org/pdf/2512.18436) studies 8 open-source Verus systems: Anvil lib, Anvil controller, IronKV, mimalloc, Node Replication, NRKernel, Atmosphere, Storage, Vest; tasks avg "Avg. 496 ... 947" lines (Table 3, exec/proof columns not cleanly extracted). VeriSMo excluded: "VeriSMo uses a fork of a very old version of Verus."
- [Not found] VeriSMo (OSDI'24) numbers: PDF fetch failed. AWS/Microsoft industrial LoC: only the Verus SOSP'24 persistent log "integrated into a production codebase" (Microsoft, cloud-scale storage; 739 exec lines). vstd size and 2026 updates: not retrieved. 2026 papers seen in search (not read): KVerus arXiv 2605.03822, Verus-SpecGym 2605.26457, ExVerus 2603.25810.

## Answers to the participant's claims
- Modular verification [Fact, design]: callers use only callee pre/postconditions; VeruSAGE: "in F_verified.rs, we keep the signature of F', but replace its body with unimplemented!()... as that is all Verus needs to finish the proof."
- Proof-effort vs solver-time trade-off [Fact]: low-automation proofs are slow to write but fast to check (Verus "concise SMT queries"); Dafny-style heavy automation is slower (24-61x) and "degenerates" on failure feedback. [Inference] Verus shifts cost from solver time to human/LLM proof time.
