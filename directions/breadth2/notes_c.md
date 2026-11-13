(authored by agents unless marked 🧑)

Scope: two directions. Quotes below are what WebFetch returned; the fetch tool often returned short excerpts (it limits quote length), so the quotes are fragments, not full paragraphs. Nothing was published anywhere.

# Direction 1: claimed isolation level does not hold (Jepsen-style anomalies)

## Real failures

1. ParticleDB 1.1.4 to 1.1.18 (Rust), Jepsen, 2026-10-31. https://jepsen.io/analyses/particledb-1.1.4
   - FACT: page says it was "Written from the ground up in Rust."
   - FACT quotes: the "Full ACID" claims "were somewhat premature."; it "allowed internal anomalies and Lost Update with `serializable`."; G-Single (violates snapshot isolation) appeared "from rc-1 through rc-22 (#73)"; in rc-18 `strict-serializable` "infrequently but regularly exhibited Stale Read," even with WAL mode `sync` (#109).
   - FACT: 96 issues, most needing "just a single server, single client, and no faults."
   - Caveat: single-node bugs mostly; it is a young startup product, not a widely used system.
2. MariaDB Galera Cluster 12.1.2, Jepsen, 2026-03-16. https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2
   - FACT quotes: "Even without faults, MariaDB Galera Cluster allows P4 (Lost Update)"; it misses its claimed level "between Serializable and Repeatable Read"; "It also regularly exhibits Stale Read." Issues MDEV-38977, MDEV-38999.
   - FACT: also lost committed transactions "with process crashes and network partitions" (MDEV-38976). All four issues unresolved at report time.
3. RavenDB 6.0.2, Jepsen, 2024-01-31. https://jepsen.io/analyses/ravendb-6.0.2
   - FACT quotes: "Transactions lose updates by default."; stronger modes "allow fractured read: a serious anomaly forbidden by Snapshot Isolation."; cluster-wide transactions documented as Serializable "routinely exhibited fractured reads."
4. TiDB 2.1.7 on TiKV (Rust storage), Jepsen, 2019-06-12. https://jepsen.io/analyses/tidb-2.1.7
   - FACT quote: "Despite promising snapshot isolation, TiDB 2.1.7 through 3.0.0-beta.1-40 allowed read skew and lost updates by default."
   - FACT (report summary, paraphrased by the fetch tool): cause was two automatic retry mechanisms that re-applied updates without regard to transaction boundaries. Fixed by disabling retry (default in 3.0.0-rc.2).
   - Note: the bug was in the Go SQL layer (TiDB), not in TiKV.
5. TxCheck (OSDI 2023) found a snapshot-isolation (G-SIb) bug in TiDB per a search summary; not verified from the paper itself. Treat as unconfirmed.
6. Not found: I searched and found no Jepsen report for SurrealDB, Materialize, Neon, or CockroachDB (post-2019). FACT per the Jepsen analyses index at https://jepsen.io/analyses (24 analyses 2019 onward, none for them). Jepsen did test CockroachDB in 2017 (outside range).

## Property to verify (OPINION: my formulation)
For a Rust transaction layer (MVCC + commit protocol), every history of committed transactions produced by any execution, including crashes and message loss, has a dependency graph with no cycle forbidden by the claimed level. For snapshot isolation (Adya): no G1a/G1b/G1c, no G-single, and first-committer-wins (no P4 lost update). Stated at the implementation level: the code refines a transition system whose reachable histories are SI-valid (Crooks et al. client-centric model, as used by the MongoDB TLA+ work).
Common root causes in the reports (INFERENCE from the 4 above): automatic retry re-applying writes, read snapshot not fixed per transaction, conflict check skipped on a code path (modes/flags). These are code-level, not protocol-level.

## Closest prior verification work
- Design and Modular Verification of Distributed Transactions in MongoDB, Schultz, Demirbas, PVLDB, 2025 (already in paper_collection). TLA+ model checking (TLC) of snapshot isolation and read committed on small instances. FACT (from search summary): it includes model-based testing of the WiredTiger API against the spec. Leaves open: no proof of the real code; bounded instances; C++.
- Verifying vMVCC, Chang, Jung, Sharma, Tassarotti, Kaashoek, Zeldovich, OSDI, 2023. https://www.usenix.org/system/files/osdi23-chang.pdf . FACT: "vMVCC is implemented in Go, stores data in memory". Proves serializability of a single-node in-memory library in Perennial/Coq. Leaves open: distributed commit, durability across nodes, Rust, weaker levels (SI).
- Elle, Kingsbury, Alvaro, VLDB, 2020 (in collection) and PolySI (Efficient Black-box Checking of Snapshot Isolation in Databases, Huang et al., VLDB 2023, https://arxiv.org/abs/2301.07313). Black-box testers of histories. Find bugs, give no guarantee.
- Percolator/TiKV, Spanner, CockroachDB: my searches found no mechanized proof of their implementations (absence of evidence from a few searches only, not a literature survey).

## Tractability (OPINION unless marked)
- Tractable slice: pick one Rust MVCC+2PC component (e.g. a Percolator-style prewrite/commit in a small Rust store), specify in Verus or Creusot (or model in TLA+ and refine), prove SI (first-committer-wins + snapshot read) including retry paths and crash recovery. PhD-scale: yes if the novelty is a refinement from protocol to Rust code over a network/crash model, with the SI definition tied to Adya cycles. Risk: vMVCC already did the single-node serializable version in Go; novelty must come from distribution plus Rust plus SI.
- Risk: the real bugs above are often "configuration mode X skips the check" and "retry"; a verified core may not cover them unless modes are in the spec. Also the Jepsen findings mostly concern DBs that are not Rust (except ParticleDB, which is young), so "real Rust bug" evidence is thin. This conflicts with the filter "no hot-path ideas without real bugs": the bugs are real, but their Rust relevance is weak.

## Rust targets
TiKV (txn module, Percolator), https://github.com/tikv/tikv ; SurrealDB https://github.com/surrealdb/surrealdb ; Materialize https://github.com/MaterializeInc/materialize ; Neon https://github.com/neondatabase/neon (safekeeper is Raft-like WAL consensus, not a txn layer) ; RisingWave ; Databend ; ParticleDB (closed source as far as I know, unverified).

# Direction 2: partial partitions and gray failures breaking replication and failover

## Real failures

1. Cloudflare, 2020-11-02, etcd. https://blog.cloudflare.com/a-byzantine-failure-in-the-real-world/
   - FACT quotes: the switch "was in a partially operating state: network control plane protocols such as LACP and BGP remained operational"; its data plane "was not processing and forwarding all the packets received from connected devices."; "node 1 repeatedly initiated leader elections, voting for itself, while node 2 repeatedly voted for node 3"; etcd went "read-only until the faulty switch recovered".
   - FACT: that triggered "the automatic promotion of a synchronous database replica" and a bug "requires a rebuild of all database replicas when a new primary database is promoted." Cloudflare says "the cure may be worse than the disease".
   - FACT: postscript says it was "an omission fault rather than a Byzantine fault."
   - Note: the 6-hour duration and the 2020 date come from a search summary of third-party text; the Cloudflare page text I fetched gave ~6 minutes for the switch fault. The outage length is not verified by me.
2. Raft liveness analysis, Howard and Abraham, 2020-12-12. https://decentralizedthoughts.github.io/2020-12-12-raft-liveness-full-omission/
   - FACT quote: "Unfortunately, Raft, as described in the original paper, does not guarantee liveness in all such cases." and "This system will not be able to establish a stable leader." PreVote alone "introduces new liveness issues"; PreVote plus CheckQuorum is claimed to give liveness (their answer: "Yes.").
3. TiKV/PD (Go PD, Rust TiKV), GitHub issues found by Jepsen: pingcap/tidb#10576 "PD can get stuck electing a leader during a n/2+1 network partition" (https://github.com/pingcap/tidb/issues/10576); pingcap/tidb#10643 "TiDB can take 500+ seconds to recover from a single-node partition isolating a PD leader" (https://github.com/pingcap/tidb/issues/10643). Both 2019 era. Titles are FACT (from search listing); I did not open the issues. PD is Go, not Rust.
4. Studies of real failures:
   - Alquraan et al., OSDI 2018: "a comprehensive study of 136 system failures attributed to network-partitioning faults from 25 widely used distributed systems. We found that the majority of the failures led to catastrophic effects, such as data loss, reappearance of deleted data, broken locks, and system crashes."
   - Alfatafta et al., OSDI 2020 (Nifty): "a comprehensive study of system failures caused by this fault in 12 popular systems. Our study reveals that the studied failures are catastrophic (e.g., lead to data loss), easily manifest, and can manifest by partially partitioning a single node." and "implemented fault tolerance techniques are inadequate for modern systems".
5. Jepsen NATS 2.12.1 (2025-12-08): FACT it did not mention asymmetric or partial partitions (per the fetch summary); data loss came from fsync/power failure, which is covered elsewhere. Not a case for this direction.
6. Gap: I found no 2023-2026 postmortem of a Rust system failing under a partial partition. Candidates exist only for etcd (Go) and PD (Go). Rust evidence is thin. A related recent mention (search summary, unverified): Cloudflare chose QuePaxa for "Meerkat" citing this pattern.

## Property to verify (OPINION: my formulation)
Safety is easy and usually already holds: at most one leader per term. The open property is liveness under a quantified fault model: if there exists a set of at least a majority of nodes that is pairwise (or via the leader) connected for long enough, and the connectivity graph is arbitrary otherwise (links may be one-way or lossy), then a stable leader is eventually elected and stays, and client requests commit. Plus a failover-side property: no automatic promotion or demotion decision depends on a single node's local view of liveness (distinct from "hidden failover dependencies", already covered; here the focus is the connectivity graph being non-transitive).

## Closest prior verification and design work
- Verdi (Raft in Coq, PLDI 2015), IronFleet (SOSP 2015), per search summary: they prove safety and not liveness under partial connectivity. (From memory-level knowledge, not fetched here; I did not download them.)
- Nifty, OSDI 2020 (downloaded to collection): a detour layer, 575 lines of C++, evaluated by testing; no proof.
- Howard and Abraham 2020: informal argument for PreVote+CheckQuorum.
- OmniPaxos (search summary: blog https://omnipaxos.com/blog/how-omnipaxos-handles-partial-connectivity-and-why-other-protocols-cant/) designs a protocol for partial connectivity (Rust implementation exists, FACT per its project; I did not verify its verification status). Leaves open: no mechanized liveness proof that I found.
- "Examining Raft's behaviour during partial network failures", Jensen, Cambridge: reproduces the Cloudflare case (search summary).
- Leaves open (INFERENCE): mechanized liveness proofs of real Raft implementations (raft-rs, openraft) under non-transitive connectivity; proving the timers/PreVote/CheckQuorum code, not only the algorithm.

## Tractability (OPINION unless marked)
- Proving liveness needs fairness and timing assumptions: harder than safety; Ivy/Verus-style tools are weaker there, TLAPS/Coq/Isabelle handle it but with high effort. Feasible slice: prove for a Raft variant (PreVote+CheckQuorum) in a connectivity-graph model that a stable leader exists whenever a quorum-connected clique with a leader exists, then refine to a Rust implementation. PhD-scale: plausible but liveness-on-code is risky; fallback is model checking with a bounded graph set plus a conformance test harness against openraft/raft-rs.
- Strength: the failure is real, recent, and has a clear theory gap. Weakness: the fix (PreVote+CheckQuorum) is known and already in raft-rs/etcd (INFERENCE from the Howard post and issue #4 of signalapp/SecureValueRecovery, per search listing), so the contribution would be proof, not bug finding; reviewers may see it as a re-verification of known fixes.

## Rust targets
openraft https://github.com/databendlabs/openraft ; raft-rs https://github.com/tikv/raft-rs ; omnipaxos https://github.com/haraldng/omnipaxos ; Neon safekeepers https://github.com/neondatabase/neon ; TiKV https://github.com/tikv/tikv ; Materialize/Persist (consensus via external store, less relevant).

# Papers added to /hdd1/sichanghe/paper_collection (open access, pdftotext)
- Efficient Black-box Checking of Snapshot Isolation in Databases (PolySI), VLDB 2023
- An Analysis of Network-Partitioning Failures in Cloud Systems, OSDI 2018
- Toward a Generic Fault Tolerance Technique for Partial Network Partitioning, OSDI 2020
- Verifying vMVCC, OSDI 2023
- Already present, skipped: Elle (VLDB 2020), MongoDB distributed transactions (PVLDB 2025)
Note: author lists in the directory names for PolySI I took from the arXiv text; collection CONVENTIONS.md was not read, so please check naming.
