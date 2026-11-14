Scope: Multi-Paxos (incl. EPaxos, Flexible Paxos), Viewstamped Replication (VR), Zab. Raft excluded.

(authored by agents unless marked 🧑)
Tags: [F] fact with source, [I] my inference. LOC = tokei "Code" column, shallow clones taken 2026-11-13.
Literature note: Google Scholar via pb-browser-page-extract returned
  {"error":{"code":"challenge_action_required", ... "message":"a CAPTCHA or browser challenge requires manual action"}}
  on the first request. I did not bypass it. All literature below came from WebSearch/WebFetch (not Scholar), so
  coverage is unranked by citations. Redo via Scholar after the human clears the challenge if needed.

== 1. Multi-Paxos (and EPaxos / Flexible Paxos)

Used in practice [F, from my background knowledge, not re-checked this session]: Google Chubby/Spanner (Paxos), Cassandra LWT (single-decree Paxos), Microsoft Azure Storage/Autopilot. Not verified by a source here; verify before citing.

Rust implementations
- OmniPaxos (Sequence Paxos + ballot leader election), github.com/haraldng/omnipaxos
  - [F] 228 stars, pushed 2026-10-24 (gh api). Core crate omnipaxos/omnipaxos: 7,389 code lines Rust; whole repo 27,066 (includes tests, storage, runtime, UI, benchmarks).
  - [F] Dependencies of core are optional and light (serde, slog, lru, uuid...); sans-IO: user supplies network and storage (docs.rs/omnipaxos).
  - [F] Users: Clockwork Labs (SpacetimeDB) keeps a fork, github.com/clockworklabs/omnipaxos PR #9. [I] this suggests real use; deployment not confirmed.
  - [F] Academic basis: Ng et al., "Omni-Paxos: Breaking the Barriers of Partial Connectivity", EuroSys 2023, https://dl.acm.org/doi/pdf/10.1145/3552326.3587441
  - [F] Supports flexible quorums (config field `flexible_quorum`), so it covers Flexible Paxos.
- paxakos, github.com/benschulz/paxakos: [F] 117 stars, last commit 2023-01-15, GPL-3.0, 13,748 code lines incl. docs/md (tokei Total code; Rust ~11K per lib.rs). [I] dead; GPL blocks reuse.
- EPaxos in Rust: Nugine/epkv (16 stars, last commit 2026-04-01, 8,225 code lines Rust, README: "An experimental distributed key-value database using EPaxos protocol ... uses a modified version of epaxos"); datenlord/r-epaxos (26 stars, last push 2022-05, 2,577 code lines). [I] research-grade, no known production users.
- Others (CASPaxos "paxos" crate for sled, multi-paxos-rs, etc.): hobby scale, last push mostly 2018-2023. [F] gh search results.

Real bugs in OmniPaxos (github issues, verbatim)
- https://github.com/haraldng/omnipaxos/issues/172 "Follower's decided_idx can decrease when a late Promise triggers AcceptSync" (closed; opened 2026-10-17 by Asmod4n). Quote: "A follower's `decided_idx` can decrease from 1 to 0. No node crashes and no message is lost. After the decrease, `read(0)` on that node returns `Undecided` for an entry that it returned as `Decided` before." Also quote: "i am currently trying out the new project mode of claude and asked it to look for good implementations of distributed consensus, yours stood out to be very good, but i didnt see a TLA+ proof of it, so i asked it to build one. Here is its only finding so far." and "Found with a TLA+ model of Sequence Paxos." So a TLA+ model of Sequence Paxos exists (made by Claude for the reporter) but is not linked in the issue body I read. [F] Safety-relevant: it is a violation of decided-prefix monotonicity as seen by the app, though the value comes back.
- https://github.com/haraldng/omnipaxos/issues/129 "trim is broken in omnipaxos_storage::persistent_storage" (closed): "the trim implementation of `omnipaxos_storage::persistent_storage` doesn't seem to set the length of the log correctly"
- https://github.com/haraldng/omnipaxos/issues/156 "Leader sends `Prepare` to non-existing Peers." (closed): "`promises_meta` is a PID-indexed array. During enumeration, all indexes are marked as `NotPromised`, which later results in incorrect `NodeId` values."
- https://github.com/haraldng/omnipaxos/issues/96 "Implicitly decided stopsign during prepare phase" (closed): "It is not clear to me if this is a critical bug or just a quirk of the implementation"
- https://github.com/haraldng/omnipaxos/issues/136 "Lost `ForwardProposals` messages are not recovered" (open): "This means that using the `append(_)` method might fail to eventually decide the entry." (liveness)
- [F] paxakos: only 1 issue ever filed (#1, praise). No bug record; [I] absence of reports reflects low usage, not correctness.

Bugs in the protocol itself (EPaxos)
- Sutra, "On the correctness of Egalitarian Paxos", Information Processing Letters 156 (2020), arXiv 1906.10917. [F, per repo otrack/on-epaxos-correctness]: bug in "both the TLA+ specification and the Golang implementation"; "each process needs to maintain the last ballot at which it voted". Violates agreement on dependencies and linearizability.
- Ryabinin, Gotsman, Sutra, "Making Democracy Work: Fixing and Simplifying Egalitarian Paxos", OPODIS 2025, arXiv 2511.02743. [F] Appendix E reports a liveness bug (recovery can deadlock); proposes EPaxos*. [I] any EPaxos port (epkv, r-epaxos) must be checked against these; epkv says it is "modified", unclear if it fixes them.

Prior formal verification
- IronFleet / IronRSL (Dafny, Multi-Paxos safety + liveness, ~3.7 person-years [F, quoted from arXiv 2606.02019 related work]). Hawblitzel et al., SOSP 2015, https://www.andrew.cmu.edu/user/bparno/papers/ironfleet.pdf
- Verus port of IronRSL: github.com/saikiranreddy2710/Verus-IronRSL. [F] 16,264 code lines Rust + 2,156 C#; 1 commit in history (shallow clone; may be truncated), last 2026-02-28 "Fix all build errors for Verus version compatibility". README: "Our goal is to implement and formally verify the Multi-Paxos protocol via refinement". Also used as a course lab: http://mpaxos.com/teaching/sf/26sp/labs/labv.html (Spring 2026) with "21 protocol action functions" to prove. [I] status of completeness unknown; I did not run Verus on it.
- Chand, Liu, Stoller, "Formal Verification of Multi-Paxos for Distributed Consensus", FM 2016, arXiv 1606.01387 (TLAPS, safety).
- Padon et al., Ivy proofs of Paxos variants and Multi-Paxos liveness (2018) [F via arXiv 2606.02019 related work, secondhand].
- Bílý, Pereira, Müller, "A Refinement Methodology for Distributed Programs in Rust", OOPSLA 2025 (PACMPL 9, OOPSLA2, art. 341), https://pm.inf.ethz.ch/publications/BilyPereiraMueller25.pdf. [F] Verifies "a version of Paxos" (roles leader/acceptor) with Prusti; method compatible with Creusot/Verus. Distinguished Artifact Award; artifact doi:10.5281/zenodo.15753818. [I] this is the closest prior art to "verify Rust Paxos code"; it targets a small Paxos written for the paper, not a library.
- Sutra / Ryabinin et al. above: EPaxos* is "first provably correct" per their abstract summary [F secondhand].

Proposed verification target
- OmniPaxos core crate (7.4K LOC, sans-IO, optional deps, no `unsafe` in omnipaxos/src [F: grep count 0]).
  - Sans-IO message-in/message-out structure makes it a pure state machine. [I] ideal for Verus/Creusot or for model-based testing against a TLA+ spec, and for refinement to the Bílý et al. methodology.
  - Concrete first property: decided_idx monotonic and decided prefix agreement across nodes (exactly the property violated in issue #172). Then: Sequence Paxos safety (agreement on decided log prefix), then leader-election-independent.
  - [I] Cost: IronRSL took 3.7 person-years in Dafny; a scoped proof of safety only on sync/accept/decide paths is far smaller. Estimated 1 to 2 person-years for the full core; 2 to 4 months for monotonicity + prefix agreement of the accept/decide path only. Unvalidated guess.
- Alternative: bring the Verus-IronRSL port to completion (it already has a spec and protocol layer) and compare with OmniPaxos by conformance testing. [I] lower risk for proof, but IronRSL has no users.

== 2. Viewstamped Replication

Used in practice
- TigerBeetle (financial DB) uses VSR. [F] "TigerBeetle uses VSR rather than Raft" (arXiv 2606.02019 summary); source in repo: tigerbeetle/src/vsr/. Language is Zig, not Rust.
- Other well-known users: [I] none I can name with a source (VR Revisited is cited widely but few products).

Rust implementations
- viewstamped-replication crate (github.com/misalcedo/vr): [F] 0 stars, pushed 2024-08-26, 2,438 code lines Rust. Last crates.io release 0.9.0, 2024-03-10 (libraries.io via search).
- arriqaaq/vsr: 2 stars, pushed 2024-07-14, 461 code lines Rust. Hobby.
- viewstamp-proto (docs.rs): sans-IO state machine; docs say "TigerBeetle's src/vsr/replica.zig is the correctness reference". [F via docs.rs search snippet; I did not read the repo.]
- gterzian/understand-vsr: TLA+ spec + Rust + Automerge, educational.
- [I] none is production-grade.

Bugs
- [F] Vanlightly found a state transfer defect in the "VR Revisited" paper itself (per awesome-tlaplus entry; repo github.com/Vanlightly/vsr-tlaplus, README says VSR.tla "is based solely on the paper and does not implement any fixes"). I did not read the exact wording; fetch before quoting.
- No Rust-implementation bug reports found: the crates have essentially no users/issues. [F: by search]

Prior formal verification
- Vanlightly TLA+ specs (above), model checking only.
- TigerBeetle: [F] jorangreef (HN, via search): "to my limited knowledge, I've not found any existing formal proofs for VSR". arXiv 2606.02019 (Falda, Bullish, 2026-06) says TigerBeetle "ships without published mechanical verification" and that its VSR challenge "excluded reconfiguration and snapshot transfer".
- [I] No mechanized proof of VR safety that I could find. (Not exhaustive: Scholar blocked.)

Porting cost (no usable Rust implementation) 
- Best implementation: TigerBeetle VSR (Zig), production, heavily tested with deterministic simulation.
  - [F] src/vsr: 25,673 code lines Zig; replica.zig alone 12,459 lines (wc), journal 2,585, superblock 1,611, grid 1,741, client 790.
  - [I] a protocol-only port (view change, normal op, state transfer, repair; no grid/LSM/superblock/storage faults) is ~6 to 10K Rust LOC. Zig is explicit, no-alloc, no-hidden-control-flow, so translation to Rust is nearly mechanical; the hard part is that replica.zig is entangled with storage (journal, superblock, grid) and the state machine; separating them is the work.
  - Dependencies: std only for core; no external libs. Tests: TigerBeetle's own VOPR simulator would need port too (large; [I] 5K+ LOC).
  - [I] Estimate 3 to 6 person-months to a faithful consensus-only Rust port, plus 2 to 3 months for a simulator/test harness. Faster alternative: start from viewstamp-proto (sans-IO, aimed at replica.zig parity) and audit it; I did not assess its quality.
- Proposed target: protocol core only, sans-IO, view change + repair + state transfer, prove: committed-op agreement across view changes (the property with the known paper defect). Cost [I]: comparable to OmniPaxos, higher because no accepted spec exists to refine; Vanlightly TLA+ is the starting spec.

== 3. Zab (ZooKeeper)

Used in practice
- Apache ZooKeeper: Hadoop/HBase, Kafka (legacy mode), Solr, etc. [F from background knowledge; not re-sourced.] ZooKeeper is Java.
- [F] No standalone Rust Zab library of note.

Rust implementations
- JustinAWei/rust-zab: "Zookeeper's Atomic Broadcast protocol in Rust", fork of a-yun/zookeeper, 2,134 code lines Rust (tokei). Course-project scale. [I] unusable as a base.
- No Rust ZooKeeper server rewrite found in search (client crates exist; not relevant).
- Other: riak_zab (Erlang), go-zab, aoriani/zab (Java).

Bugs in ZooKeeper (real, verbatim)
From Ouyang et al., "Multi-Grained Specifications for Distributed System Model Checking and Verification", EuroSys 2025, https://doi.org/10.1145/3689031.3696069 , arXiv 2409.14301 (Appendix A):
- ZK-4643 (data loss): "The implementation fails to guarantee that the follower atomically updates the history with the epoch (an atomic action in the original Zab protocol). It manifests when a follower crashes after updating its epoch, becomes the new leader with stale committed history, and then truncates the committed data of others." "This is a new bug we detected."
- ZK-4646 (data loss): "The root cause lies in the asynchronous logging of the followers when the leader starts serving clients, which is assumed to be synchronously done by the protocol." "This is a new bug we detected."
- ZK-4685: "the leader fails to recognize an ACK, which blocks the leader and then leads to the shutdown of all nodes from the Synchronization phase." "This is a new bug we detected."
- ZK-4712 (inconsistency): "a follower keeps extra transactions in its log even after data recovery, making clients obtain inconsistent views from different servers. It was caused by the asynchronous logging during the follower's shutdown."
- ZK-4394 (known, unfixed): "if the follower receives the COMMIT message after the NEWLEADER message, it will throw an unexpected NullPointerException and terminate the Synchronization phase."
- ZK-3023 (data sync failure), also found. Total: "six severe bugs"; footnote lists ZK-2776, ZK-3336, ZK-3707, ZK-4040, ZK-4416, ZK-4781 as known bugs still present.
- [F] Table 4 says all but ZK-4394 need the finer-grained specs (they model non-atomic actions and local concurrency).
- [I] Lesson: the bugs live in the model-code gap (non-atomic persistence, threading), exactly what code-level verification of a Rust port would force into the open.

Prior formal verification
- Same EuroSys '25 paper (TLA+, TLC, conformance via Remix). Specs written by one person, amortized; model checking only, not proof.
- Ouyang et al., "Leveraging TLA+ Specifications to Improve the Reliability of the ZooKeeper Coordination Service", arXiv 2302.02703 (ABZ 2023 [I, venue from memory]).
- Mocket (Wang et al., EuroSys 2023), SandTable (Wei et al., EuroSys 2024, https://dl.acm.org/doi/pdf/10.1145/3627703.3650077, found 23 bugs across systems incl. Zab [F via search; per-system split unknown]).
- Zab paper itself: Junqueira, Reed, Serafini, DSN 2011; and "Vive La Difference: Paxos vs. Viewstamped Replication vs. Zab" (van Renesse, Schiper, Schneider, IEEE TDSC 2015, arXiv 1309.5671) relates all three. [I] That paper's refinement mapping is a basis for sharing proof infrastructure between the three protocols.

Porting cost (no usable Rust implementation)
- Best implementation: Apache ZooKeeper (Java), github.com/apache/zookeeper.
  - [F] Whole zookeeper-server main: 50,778 code lines Java (tokei; 397 files).
  - [F] Zab-relevant files (wc -l): Leader 1,824; Follower 288; Learner 959; LearnerHandler 1,183; QuorumPeer 2,859; FastLeaderElection 1,219; Observer 304; QuorumCnxManager 1,487; persistence FileTxnSnapLog 669 + FileSnap 288 (+ FileTxnLog); quorum/flexible 833. Sum of quorum core ~ 10K lines Java; with DataTree (2,040) and ZKDatabase (806) ~ 13K.
  - [I] Consensus-only port (election, discovery, sync, broadcast, txn log, snapshot; no sessions/ACL/watches/JMX/auth/SASL) ~ 5 to 8K Rust LOC. Dependencies: tokio-ish net stack and a log format; skipped if sans-IO. Java threads + queues (CommitProcessor, SyncRequestProcessor) must become explicit state machines; this is where ZK-4646/4712 come from, so the port must decide sync vs async persistence explicitly.
  - Tests: ZooKeeper has large JUnit suites ([I] unmeasured here); porting tests is likely as costly as the code. Estimate 4 to 8 person-months for a faithful consensus-only port + tests (unvalidated).
  - [I] Cheaper: write a fresh sans-IO Zab from the Remix TLA+ spec (public in the EuroSys paper artifact) rather than translate Java. Estimate 2 to 4 person-months, but then fidelity to ZooKeeper's actual behavior is lost, which is where the bugs were.
- Proposed target: Zab discovery+synchronization+broadcast core with explicit persistence actions; prove the 10 Zab safety invariants (from Table 2 of Ouyang et al.) with epoch/history update atomicity as an explicit assumption/obligation (ZK-4643, ZK-4646).

== 4. Ranking for the human's goal [I]
1. OmniPaxos: existing, maintained, small (7.4K), sans-IO, real bugs found by a model (issue #172) in Oct 2026, a TLA+ model already exists in someone's hands, no existing proof. Lowest cost.
2. Zab: no Rust impl, but best-documented real bug record and existing TLA+ specs. Porting cost 2 to 8 person-months.
3. VR: no production Rust impl; TigerBeetle in Zig is the reference. Highest distance to code, thinnest bug record in Rust.
4. EPaxos: Rust impls exist (epkv) but the protocol itself had published safety and liveness bugs; verifying means choosing EPaxos* first.
Caveat: none of these cost estimates were validated by building anything.

== 5. Open items
- Scholar blocked, so no citation-count ranking and possibly missed recent (2025-2026) papers on verified Rust consensus.
- I did not read viewstamp-proto, epkv, or Verus-IronRSL beyond size/README; no claim about their quality.
- Issue #172's TLA+ model location is unknown.
