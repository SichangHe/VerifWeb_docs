# Verifying Rust implementations of widely used distributed protocols other than Raft

(authored by agents unless marked 🧑)

Request (🧑, relayed by the manager): "identify other distributed systems like Raft that are commonly used, and proposed to also formally verify their Rust implementation. If they don't have a Rust implementation, try to find out how expensive would it be to port some other implementation"

Scope: openraft membership changes are excluded, because the vlm49_raft task covers them. Full evidence with verbatim quotes is in [vlm49_distsys/](vlm49_distsys/) (notes_a: Paxos, VR, Zab; notes_b: BFT; notes_c: gossip, leases; notes_d: transactions, chain replication).

Caveats (FACT): Google Scholar showed a CAPTCHA to all four research agents, and none of them bypassed it. The literature came from web search, so every "no prior verification found" below is weak evidence. All line counts are from `tokei` or `wc` on shallow clones. All cost figures are agent estimates (INFERENCE) and were not checked by building anything.

## Takeaway

Four protocols have a real, maintained Rust implementation with a small core, a recent public bug, and no proof that the code is correct. These are, in the order the agents ranked them (OPINION):

1. Percolator transactions in TiKV. These have the most severe real bugs.
2. OmniPaxos (Multi-Paxos). It is the cheapest target and has a fresh safety bug.
3. chitchat (Scuttlebutt gossip). Its bug is a convergence bug, which fits STORY.md.
4. Malachite (Tendermint BFT) and Aptos `safety-rules` (HotStuff). Their core logic is small.

Zab and Viewstamped Replication have no usable Rust implementation, so they need a port. The agents estimate 4–8 person-months for Zab and 3–6 person-months for VR. PBFT, CRAQ, primary-backup and leases/locks are weak candidates.

## Percolator / two-phase commit (TiKV)

- Where it is used (FACT): TiKV and TiDB.
- Rust code (FACT): about 53k lines in `src/storage/{txn,mvcc}`, `txn_types` and `concurrency_manager`. The core `txn/actions` is about 10.7k lines.
- Real bugs (FACT): tikv#8589, https://github.com/tikv/tikv/issues/8589, titled "Async commit does not ensure linearizability". Quote: "Read with max u64 immediately after an async commit transaction. Because the lock in the previous transaction may be not committed yet, and locks can be ignored if we read with max u64. So we may not read the latest changes from the last async commit transaction."
  - Also tikv#14551, "Stale pessimistic lock requests in force-lock mode may lead to data corruption or in consistency after resolving lock".
  - Also tikv#17415, "Flashback may break transaction atomicity".
- Prior verification (FACT): PingCAP has a TLA+ model of basic Percolator (`pingcap/tla-plus`). The agent found no models of async commit, one-phase commit (1PC) or pessimistic locking, and no link from the Rust code to any model (INFERENCE from one grep and a few searches).
- Proposed target (INFERENCE): the prewrite, commit, check_txn_status and rollback actions, about 2–3k lines, in Verus. The main risk is the generic `Snapshot`/`Engine` code.

## Multi-Paxos (OmniPaxos)

- Where it is used (FACT): OmniPaxos is a research library (Ng et al., EuroSys 2023). Clockwork Labs (SpacetimeDB) keeps a fork. The agent found no other named production user.
- Rust code (FACT): the core crate is 7.4k lines and does no networking or storage itself. It is actively maintained. paxakos is dead (last commit January 2023).
- Real bug (FACT): omnipaxos#172, https://github.com/haraldng/omnipaxos/issues/172, closed. Quote: "A follower's `decided_idx` can decrease from 1 to 0. No node crashes and no message is lost. After the decrease, `read(0)` on that node returns `Undecided` for an entry that it returned as `Decided` before."
  - The reporter wrote that the bug was "Found with a TLA+ model of Sequence Paxos", which Claude had built for them.
- Prior verification (FACT): IronFleet (Dafny, SOSP 2015, about 3.7 person-years) and Chand–Liu–Stoller (TLAPS, FM 2016) verify other Paxos implementations.
  - Bílý–Pereira–Müller (OOPSLA 2025) verify a small Paxos written in Rust, using Prusti.
  - None of these covers OmniPaxos.
- Proposed target (INFERENCE): decided-index monotonicity and agreement on the decided prefix (no two nodes decide different entries at the same index). These are the properties #172 violated. Estimated cost is 2–4 months for this path and 1–2 person-years for the whole core.
- EPaxos variant (FACT): Sutra (IPL 2020) found an agreement bug in both the EPaxos spec and its Go code. Ryabinin–Gotsman–Sutra (OPODIS 2025) report a recovery liveness bug. The Rust EPaxos crates are small or stale (`epkv` 8.2k lines, `r-epaxos` 2.6k). The protocol itself needs fixing before its code is worth verifying (INFERENCE).

## Gossip: Scuttlebutt (chitchat) and SWIM (foca)

- Where it is used (FACT): Quickwit uses chitchat, and Cassandra uses Scuttlebutt-style gossip. Fly.io's Corrosion uses foca. HashiCorp memberlist (Go) implements SWIM/Lifeguard for Consul.
- Rust code (FACT): chitchat is about 8.5k lines, last commit 2026-11-09. foca is about 7.8k lines, does no I/O and is no_std, last commit 2026-08-02.
- Real bugs (FACT): chitchat#121, https://github.com/quickwit-oss/chitchat/issues/121. Quote: "The current key GC logic is broken. It relies on heartbeat, assuming that all keys that were updated before the last heartbeat have been received. This is however incorrect." The result is that a deleted key comes back.
  - foca#29 says a suspected member "would never go back to a non-suspect state".
- Prior verification (FACT): there is a TLA+ simulation of SWIM (Vanlightly and Kuppe, TLA+ Conf 2022). The agent found no proof of either crate.
- Proposed target (INFERENCE): first, chitchat's delta, digest and GC logic, proving that replicas converge and deleted keys do not come back. Second, foca's incarnation monotonicity and that it never resurrects a Down member.

## BFT consensus: Tendermint (Malachite), HotStuff (Aptos), Mysticeti (Sui)

- Where they are used (FACT):
  - Malachite is the consensus engine of Circle's Arc chain.
  - Aptos runs a HotStuff-family protocol.
  - Sui runs Mysticeti.
- Rust code (FACT):
  - Malachite is 96k lines in total, but its votekeeper and state machine together are about 3.4k.
  - The Aptos `safety-rules` crate is 4k lines, out of 96k in `consensus`.
  - Sui's `consensus/core` is 52k lines.
- Real bugs (FACT): aptos-core#20801, https://github.com/aptos-labs/aptos-core/issues/20801, is open. Quote: "the validator is deadlocked: it cannot sign a proposal as leader because SafetyRules::guarded_sign_proposal ... fails with IncorrectPreferredRound, and it cannot sign a timeout because SafetyRules::safe_to_timeout ... fails with NotSafeToTimeout."
  - malachite#1201: "Consensus gets stuck waiting for a response". This bug is in glue code, not the core.
- Prior verification (FACT):
  - Malachite ships Quint specs and model-based tests, but no proofs.
  - There is an Agda proof of a HotStuff-based protocol (Carr et al., NFM 2022).
  - Yale FLINT has a mechanized Mysticeti proof (sp26.pdf), which the agent could not open.
- Proposed target (INFERENCE): Malachite's votekeeper and state machine, checked in Verus against its Quint spec. A second target is Aptos `safety-rules` together with the BlockStore invariant that #20801 breaks.
- PBFT (FACT): the only production Rust PBFT, `sawtooth-pbft`, is archived. Skip it (OPINION).

## Zab (ZooKeeper): no Rust implementation, port needed

- Where it is used (FACT): Apache ZooKeeper, which Kafka (before KRaft), HBase and Hadoop depend on.
- Rust code (FACT): only a 2.1k-line course project.
- Real bugs (FACT): Ouyang et al. (EuroSys 2025) found six severe ZooKeeper bugs. For example, ZK-4643: "The implementation fails to guarantee that the follower atomically updates the history with the epoch."
- Prior verification (FACT): that paper, Mocket and SandTable, which are all model checking. None is a proof.
- Port cost (INFERENCE): ZooKeeper is 50.8k lines of Java, of which about 10–13k are on the consensus path. A consensus-only Rust port would be 5–8k lines and take 4–8 person-months including tests. Writing it fresh from the TLA+ spec would take 2–4 months, but the result would no longer be the real ZooKeeper code.

## Viewstamped Replication: no usable Rust implementation, port needed

- Where it is used (FACT): TigerBeetle (in Zig).
- Rust code (FACT): hobby projects only, such as `misalcedo/vr` at 2.4k lines.
- Prior verification (FACT): only Vanlightly's TLA+ models, which found a state-transfer defect in the VR Revisited paper. The agent found no mechanized proof.
- Port cost (INFERENCE): TigerBeetle's `src/vsr` is 25.7k lines, of which `replica.zig` is 12.5k. A consensus-only Rust port would be 6–10k lines and take 3–6 person-months, plus 2–3 months to build a simulator for testing.

## Weak candidates

- Chain replication and CRAQ (FACT): the only Rust implementation, `zowens/chain-replication`, is marked "Experimental" and was last committed 2024-03-04. There is no Rust CRAQ, and the agent found no prior verification.
- Primary-backup (FACT): there is no standard Rust implementation. The prior art is Grove's GroveKV, verified in Go with Coq/Iris (SOSP 2023).
- Leases and locks (FACT): there is no Rust implementation. Jepsen's etcd 3.4.3 report says "multiple clients may hold the same etcd lock simultaneously". The etcd lease code is 2.8k Go lines but depends on raft, mvcc and bbolt, so a faithful port would exceed 10k lines (INFERENCE).
- tikv raftstore (multi-Raft) (FACT): 81k lines plus 30k in raftstore-v2, with bugs such as #20000. Its split/merge logic is a target, but an expensive one (INFERENCE).

## Papers kept in paper_collection

These are new this task: Lifeguard (DSN 2018), the consensus-verification SoK (Bondarev et al., arXiv 2026), and folders with extracted text for the MongoDB transactions paper (PVLDB 2025) and the DAG-consensus paper (NFM 2025). These were already in the collection: Ouyang et al. (EuroSys 2025), the EPaxos fix (2025), Bílý et al. (OOPSLA 2025) and SandTable (EuroSys 2024).

## Scholar update, 2026-11-14 (changed in this pass)

Google Scholar worked again; 7 queries, snippets only. Changes per protocol:
- Percolator: "Formalization and verification of percolator using CSP" (Wang, Su, Zhu, IEEE COMPSAC 2024) models basic Percolator, a model and not the TiKV code. Not checked whether it covers async commit or pessimistic locks. Verdict: still open for the Rust code (unchanged); protocol-level model now partly done.
- OmniPaxos: no verification paper; only the EuroSys 2023 design paper and users as a baseline. Verdict: still open. New neighbour: AutoMan (Zhang, Zhou, Jenkins, Chowdhury et al., 2025), "Facilitating Verified Distributed Systems Development Through Automatic Code Generation", generates verified distributed-system code; check whether it targets Rust/Verus before claiming novelty.
- Gossip (chitchat, foca): no verification paper found. Verdict: still open.
- Tendermint (Malachite): model checking of the protocol exists (Yu, Hou, Dong, Dong, "International Conference on Engineering of Complex …" 2025, "Model Checking Nondeterministic Behaviours in the Tendermint Byzantine Fault Tolerant Blockchain Consensus Protocol"); "Revisiting Fast Tendermint: An Agreement Violation and Two Repairs" (arXiv 2610.16442, 2026) found a protocol bug in a 2026 variant. No implementation proof. Verdict: still open for the code.
- HotStuff (Aptos safety-rules): only the Agda proof already cited (Carr et al., NFM 2022) and the consensus-verification SoK (arXiv 2608.21935, already in paper_collection). Verdict: still open.
- New general neighbour: "Agora: Toward Autonomous Bug Detection in Production-Level Consensus Protocols with LLM Agents" (arXiv 2026), bug finding, not proofs.
