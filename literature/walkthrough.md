# VerifWeb reading walkthrough
(authored by agents unless marked 🧑)

Notes of the papers walked through with the human, in order, and the human's takeaways.

## 1. Verifying Strong Eventual Consistency in Distributed Systems (Gomes et al., OOPSLA 2017)

- status: presented Nov 13; agent read the full paper
- human's takeaways: (pending)
- human asked (Nov 16): is this the state of the art; do real systems (editors, databases) reach agreement without consensus?
  - answered: Gomes 2017 is the foundation, not the latest; pointed to Nieto 2022, Peepul 2022, Propel 2023, Sal 2026; real systems: Automerge/Yjs/Loro, Riak, Cassandra (no consensus) vs Google Docs (central server)

## Priority for Nov 17 advisor meeting
Order from vl_meeting_work's out/reading_priority_1117.md: Nieto 2022, AMC 2023, Lion (SOSP 2026), Vest (USENIX Sec 2026); if time: ESMeta, WebSpec, Verdict.

## 2. Modular Verification of Op-Based CRDTs in Separation Logic (Nieto et al., OOPSLA 2022)
- status: presented Nov 16; agent read the full paper
- points for advisors: safety only, no eventual delivery (liveness) proved; no text CRDT, no Rust, no deployed library; ~30 Coq lines per OCaml line (Table 2)
- human's takeaways: (pending)

## 3. AMC: Automerge Model Checker (Jeffery, Mortier, PaPoC 2023)
- status: presented Nov 16; agent read the full paper
- points for advisors: authors say mechanized CRDT proofs "cannot aid more optimized implementations"; checking is bounded (1 key/index, 3 servers, depth 19) on a reliable ordered network; bugs found were app-level (list move duplicates, ID clashes)
- human's takeaways: (pending)

## 4. Lion: Modular Verification of Async Runtime Liveness (Zhou et al., SOSP 2026)
- status: presented Nov 16; agent read main text (not appendices)
- points for advisors: real-Rust liveness precedent (runtime never drops a task, not app progress); 39.6k spec+proof vs 3.4k verified code (11.7x), Claude-assisted; assumes no cross-task cancel and single-threaded core
- human's takeaways: (pending)
- Lion also: "whole-application liveness is out of scope ... task abort mid-wait is unmodeled" (Sec. 5.2)

## 5. Vest (Cai et al., USENIX Security 2025; file name says 2026)
- status: presented Nov 16; agent read main text
- points for advisors: verified Rust beats Rustls/rust-bitcoin; generates new verified code rather than verifying existing libraries; RFC ambiguity needed "occasional corrections"
- human's takeaways: (pending)

## 6. WebSpec (Veronese et al., IEEE S&P 2023)
- status: presented Nov 16; agent read main text + feature appendix
- points for advisors: formal model found 2 new flaws from mechanism interactions, validated on Chrome/Firefox; single session, no network, security only (no multi-tab/sync/liveness); model tied to browsers by tests
- human's takeaways: (pending)

## 7. Verdict (Lin et al., USENIX Security 2025)
- status: presented Nov 16; agent read main text
- points for advisors: correctness parametric in a user policy because "there is no one true spec"; found OpenSSL/Chrome RFC deviations and a malleability bug in Rust crate der; ~13k Verus lines, Firefox policy 6% faster; new replacement, not proof of existing code
- human's takeaways: (pending)

## 8. JEST (Park et al., ICSE 2021; stands in for ESMeta)
- status: presented Nov 16; agent read main text
- points for advisors: spec is not the oracle; 44 engine bugs + 27 ES11 spec bugs, confirmed by TC39; testing not proof
- suggested meeting line (agent opinion): models of text merge proved (Gomes), real code of simple CRDTs proved safety-only (Nieto), real-Rust liveness now feasible at runtime layer (Lion); nobody proved convergence + liveness of real Rust sync libraries
- human's takeaways: (pending)
- human asked (Nov 18): do synced editors like Google Docs already use formally verified protocols?
  - answered: no; deployed editors run deployed code that no paper here verifies; proofs cover models (Gomes RGA, OT TP1 proofs) or small CRDTs (Nieto); Automerge only bounded-checked (AMC)

## Pace change (Nov 18)
🧑 Human, verbatim: "You went over all the papers too quickly, and I cannot, taking all of them at the same time. We need to, slow down and, go over them one by one. Step by step, instead. First thing I'm interested in is the, async runtime paper."
- from now: one paper at a time, back-and-forth Q&A; restarting with Lion (SOSP 2026)
- Lion Q (Nov 18): "that cannot be the whole paper. There must be something else, right?" -> answered with the paper's 5 contributions (theorem, log method, async contracts, explicit assumptions, evaluation)
- Lion Q (Nov 18): how they prove it; LLM use; token cost and "power" -> explained ghost log + async contracts + chaining (Sec. 4); LLM use = Claude assistant + mutation study (App. B); paper reports no tokens, person-time, verification time, or compute/energy, only LOC
- standing rule (🧑 Nov 18, verbatim): "You need to go slower. And break it down even more." -> one concept per message, concrete examples, wait for the human
- 🧑 takeaway (Nov 18, verbatim): "we should inject fault to formally verified programs, and see if verifiers and testing, would each spot them." (from Lion App. B: verifier caught all 10 injected bugs; stress tests missed the 4 timer bugs)
- Lion Q (Nov 18): what the states, log and transitions are, and how they give liveness -> walked through Example 1 (simplified executor, Sec. 4.2)
- open: discuss Lion's LLM use later (human's request)
- Lion Q (Nov 18): how they ensure ticks pop/run, infinite polls, why one queue -> tick checked by Verus (cached=>poll, terminating loops); bounded polls is an unverified assumption; real executor has 4 queues
- standing rule (🧑 Nov 18): reply through one channel only (amh or final output), never split one answer across both
- Lion (Nov 18): human done with the proof method ("learned enough about how to prove liveness"); asked for the remaining important pieces
- standing rule (🧑 Nov 18, verbatim): "Don't go over multiple things all at once. Do it one by one."
- 🧑 takeaway (Nov 18, verbatim): "Assumptions look pretty standard, and if we write a paper like this, we just should refer to existing work in terms of how we [do] assumptions"
- Lion Q (Nov 18): how much simpler does dropping work-stealing make the runtime and proofs? -> paper gives no number; proof only covers single thread, multi-thread is future work; perf cost: >3x Tokio p99 inline, <=1.5x with yield chunking, throughput within 1%
