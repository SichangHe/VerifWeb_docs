# Scoping: a verified multi-threaded (work-stealing) async runtime
(authored by agents unless marked 🧑)

Request, from the Nov 19 advisor meeting (transcript `1119madhyastha_govindan_ardi.vtt`, lines 471-493):
- 🧑 Steven, L471: "the multi-threaded event loop async runtime?"
- 🧑 Ramesh, L476: "You can certainly look in that space."
- 🧑 Ramesh, L490-493: "not so much ... bugs and bug finding, because that's easy to do nowadays, but sort of what a principled fix to all of this might be ... developing some sort of verified Systems"

Short answer: the space is open but contested. The cheapest real first piece is Lion's own cross-thread wake path, which Lion currently trusts. A full verified work-stealing runtime with liveness is a multi-year effort, and Lion's core proof technique does not carry over directly.

## What Lion says about multi-threading

Lion (Zhou, Zhang, Chowdhury, Mu, SOSP '26; paper text at <https://coladog.github.io/assets/lion-sosp26.pdf>) verifies a single-threaded runtime only. Section 6, verbatim:
- "Lion's verified core is single-threaded: one executor, one reactor, and one event loop per thread."
- "For multi-core deployments, Lion launches independent per-core instances. The liveness guarantees proved for a single instance carry over to every core."
- "Extending the verification to cover cross-thread work-stealing, where tasks migrate between cores and shared queues require concurrent reasoning, is a challenging direction for future work."
- "the majority of the confirmed liveness bugs in Tokio occur in single-threaded scheduling logic, not in multi-threaded synchronization."

Its key technique depends on single-threadedness (Section 3, verbatim): "Our key insight is that in a single-threaded runtime, execution forms a deterministic sequence of events. We model this sequence as an append-only logical event log". Inference: with work-stealing, events from several workers interleave, so this one-log, one-sequence argument must be redesigned, not just reused.

Lion's own measurement argues work-stealing matters mainly for tail latency (Section 7.3, Figure 9 caption): "Run inline, Lion pays >3× Tokio's p99 at high utilization; cooperative yield-chunking, using Lion's verified yield_now, reduces this to ≤1.5×". "Throughput is within 1% across all three". This weakens the performance motivation; a reviewer may ask why work-stealing is needed at all.

Lion already contains cross-thread code, all trusted. From `TCB_and_limitations.md` at commit `d728be2` (<https://github.com/stonysystems/lion/blob/d728be220d82ce7c1a0bd2515c43d1c31933b3b8/TCB_and_limitations.md>):
- `InterruptHandle::wake`: "no ensures (opaque effect) — cross-thread mio wake, dedup via AtomicBool"
- `Executor::reset_and_drain_cross_thread_action`: "no ensures (opaque effect) — resets interrupt, drains cross-thread queue into TLS"
- `Executor::try_recv_raw`: "no ensures — plain mpsc `try_recv`, no executor access, no claims about what comes out"

## Who else works on it

Found by a search subagent; quotes below are verbatim only where marked so, since some items were seen only through search snippets.
- Lion authors: no multi-threaded follow-up found. Harsha (L472): "I mean, the authors themselves, probably." Expect them to compete.
- Allain and Scherer, "A Verified Parallel Scheduler for OCaml 5 (Parabs)", PLDI 2026 (<https://doi.org/10.1145/3808337>)
  - verbatim: "this is the first verified implementation of a parallel work-stealing task scheduler (for any language) using realistic implementation techniques."
  - verbatim limitation: "it relies on a sequentially consistent memory model whereas OCaml 5 has a relaxed memory model"
  - real OCaml code, Iris/Rocq, includes a Chase-Lev deque; safety/linearizability; progress not confirmed
  - consequence: "first verified work-stealing scheduler" is already claimed; we cannot claim it
- Li, Beschastnikh, Summers, "Modular Responsiveness Verification of Rust Async Runtimes", ESOP 2027 (arXiv 2610.09198)
  - abstract, verbatim: "verify eventual progression of several key components of multiple Rust async runtime implementations"
  - liveness on real Rust components via static analysis; whether it covers multi-threaded executors is unconfirmed
- Drodt, "A Complete, Formal Semantics for Rust Source Code" (arXiv 2610.06003)
  - verbatim: "Based on our more abstract formalization, we establish the fairness of Tokio's scheduler."
  - a model of Tokio, not its code
- Chase-Lev deque proofs in Iris (Choi, KAIST, arXiv 2309.03642; OOPSLA 2023 reclamation paper): safety/linearizability of a model-language implementation, not Rust
- bounded checking of real Rust code, safety only: Tokio's loom, RustMC (GenMC-based, arXiv 2502.06293), Kani on s2n-quic
- networking layer: no verification of hyper, h2, rustls or quinn found; nearest are EverParse/EverQUIC (F*, generated C) and Verus-based Vest/Verdict (names only, unchecked)

## What would be new, stated precisely

Per the Nov 18 human note on careful verification claims, a claim here would need all of:
- real Rust code, checked in Verus (Parabs is OCaml; the Iris deques are model languages)
- liveness ("a woken task is eventually polled, on some worker"), not only safety or linearizability (Parabs, deques, loom)
- composed with Lion's single-worker guarantee
- stated memory model: Parabs assumes sequential consistency; whether Verus atomics reasoning handles relaxed orderings soundly I do not know and would check first

## A first verified piece

Recommendation (agent opinion): verify Lion's cross-thread wake/injection path, the three trusted functions listed above.
- property: a wake or spawn sent from another thread is eventually drained and enqueued by the target executor; no wake is lost to the AtomicBool dedup
- why first:
  - small, real code, already inside a verified system
  - removes concrete trust from Lion's TCB, so the "what is new" statement is exact
  - exercises the core difficulty (concurrent reasoning feeding Lion's event log) without stealing
- second piece: a Chase-Lev-style stealable queue in Verus with linearizability, then "no task lost or duplicated under steals"
- third: liveness of the stealing scheduler (every runnable task eventually polled); this is the hard research part

## How hard

All estimates below are my opinion, not measured.
- first piece: weeks to a few months for someone fluent in Verus; main risk is expressing "eventually" across threads in Verus, which Lion avoided via its single sequential log
- deque in Verus: months; Parabs and Iris proofs give a template, but porting proofs across tools is not mechanical
- full work-stealing liveness: a PhD-thesis-scale effort; Parabs needed a whole framework (Zoo) for safety alone
- verified HTTP library on top: separate, also large; nothing exists for hyper-class libraries
- competition risk: the Lion authors named this as their future work, and Parabs and Li–Beschastnikh–Summers are adjacent and recent

Open questions for the human:
- is the Lion trusted-glue-first scope acceptable as a "principled fix", or is a full runtime required to meet Ramesh's bar?
- talk to Arvin (vl_todo, L501) before committing
