Task d: 2PC / Percolator / chain replication / primary-backup / multi-Raft, Rust verification targets

(authored by agents unless marked 🧑)
Date 2026-11-13. F = fact (source), I = inference.

Scholar status: Google Scholar returned CAPTCHA twice via pb-browser-page-extract (challenge_action_required); not bypassed; recorded failed. Literature below came from WebSearch, not Scholar.

1. Percolator (TiKV, TiDB)
Used in: TiKV/TiDB (F: tikv.org deep-dive "Percolator"). Spanner-style 2PC over Paxos groups is not open Rust (I).
Rust impl: tikv/tikv, src/storage/{txn,mvcc} + components/txn_types + concurrency_manager. F (clone 2026-11-13, LOC by wc): txn 32.9k, mvcc 14.4k, txn_types 4.1k, concurrency_manager 2.1k; core actions/ (prewrite, commit, check_txn_status, cleanup, acquire_pessimistic_lock) 10.7k, commands 11.3k; whole src/ 131k; raftstore 81k, raftstore-v2 30k. Last commit 2026-11-12; 16.9k stars. Client: tikv/client-rust 43.6k LOC src, 433 stars, last commit 2026-11-11.
Real bugs (F, GitHub issues, tikv/tikv):
- #8589 https://github.com/tikv/tikv/issues/8589 "Async commit does not ensure linearizability": "Read with max u64 immediately after an async commit transaction. Because the lock in the previous transaction may be not committed yet, and locks can be ignored if we read with max u64. So we may not read the latest changes from the last async commit transaction."
- #14551 https://github.com/tikv/tikv/issues/14551 "Stale pessimistic lock requests in force-lock mode may lead to data corruption or in consistency after resolving lock": "Allowing locking with conflict introduces more corner cases if we consider the posibility of stale RPC requests."
- #17415 https://github.com/tikv/tikv/issues/17415 "Flashback may break transaction atomicity" (steps: PK committed, SK not yet, flashback starts).
- #11187 https://github.com/tikv/tikv/issues/11187 "Stale non-pessimistic lock may be incompatible with CDC and possibly affect data correctness": "Pessimistic transactions may contain keys that don't need pessimistic locks."
- #19891 https://github.com/tikv/tikv/issues/19891 (2026-07) panic "txn record found but not expected": a committed Write and a Lock coexist at same start_ts.
Pattern (I): bugs are in extensions (async commit, 1PC, pessimistic force-lock, flashback, CDC), not base Percolator.
Prior verification (F): pingcap/tla-plus Percolator dir, https://github.com/pingcap/tla-plus/tree/master/Percolator : "This directory contains the TLA+ specification of Percolator, the transaction protocol of TiKV." TLC model 3 keys, 3 clients. TiKV blog Nov 2019 (https://tikv.org/blog/monthly-november-2019/): TLA+ used in 2017 to check the prewrite-primary-and-secondaries-together variant; first implementation had problems. No refinement from the Rust code (F: no TLA/refinement in src/storage/txn grep; I: none exists). Not found: async commit / 1PC / pessimistic formal models (I: absence from my searches only).
Proposed target: Verus (or Creusot) on the pure MVCC state-transition functions in txn/actions (prewrite, commit, check_txn_status, rollback) over an abstract CF_LOCK/CF_WRITE map; prove snapshot isolation + "txn committed iff primary committed" as inductive invariant including async-commit min_commit_ts and max_ts rules. Reason: these functions take a MvccTxn buffer and a Snapshot reader, so are near-pure (I, not read in depth). Cost estimate (I): 10.7k LOC actions is too large; start with prewrite+commit+check_txn_status+rollback, ~2-3k LOC. Risk: heavy trait generics (Snapshot, Engine) and RocksDB-backed readers must be abstracted.

2. Two-phase commit
Used in (F): MongoDB sharded transactions "executes a two-phase commit based protocol for ensuring atomic commit across shards" (Schultz and Demirbas, VLDB 2025). Also TiDB (Percolator is 2PC variant), CockroachDB (parallel commits), Spanner (I from general knowledge; no source fetched).
Rust impls: no standalone widely used crate found (I; one search). The relevant Rust 2PC is TiKV's (item 1) and its client in client-rust.
Prior verification (F): Gray and Lamport, "Consensus on Transaction Commit" (TODS 2006), Paxos Commit refines 2PC in TLA+ (via search summary of acolyer blog, not read the paper). MongoDB VLDB 2025 TLA+ spec ~332 lines; model-based test generation from the storage model to check WiredTiger conformance; no trace checking. Artifact https://github.com/mongodb-labs/vldb25-dist-txns . Trillium/Aneris: 2PC AnerisLang implementation proven to refine TLA+ (via search snippet from arXiv 2607.15877 related work; not verified by me).
Proposed target: a small Rust 2PC (coordinator + participants, WAL) verified in Verus with a network spec; cheap (I: ~1k LOC) but it is a toy; the useful claim is atomic-commit under crash recovery. Weak value unless it is TiKV's.

3. Chain replication / CRAQ
Used in (F from search): research/experimental; original CRAQ code jterrace/craq (C++, "currently not being maintained"). Production use (e.g. Azure Storage, FAWN, Hibari) from my memory, not verified here.
Rust: zowens/chain-replication (F: README "Development Status: Experimental"; 42 stars; no license shown; "Must be using Rust nightly"; 192 commits; last commit 2024-03-04; 14.4k Rust LOC incl. client, storage-server, management-server, cli). hderms/kefka: toy, chain replication itself on TODO list. No CRAQ in Rust found (F: one search).
Real bugs: none found in the Rust impls (no issue search done; I: too small to have a bug record).
Prior verification: no formal chain replication proof found in one search. Grove (Sharma, Jung, Tassarotti, Kaashoek, Zeldovich, SOSP 2023, arXiv 2309.03046) verifies GroveKV, primary/backup with reconfiguration and leases, in Go/Coq-Iris. F: "GroveKV supports reconfiguration, primary/backup replication, and crash recovery."
Porting cost (I): choose C++ jterrace/craq (unmaintained, Thrift-era, ties to ZooKeeper (I)); not worth porting. Better: write chain replication fresh in Rust (~1-2k LOC for protocol core) or use zowens as a base (14k LOC but nightly and unmaintained). Verification would need a new spec; Verus + IronFleet-style refinement from a TLA+ chain spec; ~ weeks for protocol w/o reconfiguration (I).

4. Primary-backup
Used in: Redis replication, MySQL/PostgreSQL streaming replication, ZooKeeper-style masters (general knowledge, I).
Rust: none standard; Rust projects are products (e.g. no crate identified). Prior verification (F): Grove GroveKV in Go; Verdi PLDI 2015 primary-backup (my memory, not verified here).
Target: Verus port of GroveKV-style primary/backup with leases; hard because leases need time model; Verus async support still immature (F: S-Bus arXiv 2605.17076 states it "async support... remains under active development").

5. tikv/raft-rs multi-Raft (not plain Raft)
raft-rs itself is a plain Raft library: 11.0k LOC src (F), last commit 2026-05-13 (so quiet). The multi-Raft part is TiKV raftstore (81.3k LOC) and raftstore-v2 (30.0k): region split/merge, snapshots, conf change per region, lease reads, apply pipeline, async IO (F: dir listing). Bugs (F): #20000 https://github.com/tikv/tikv/issues/20000 "raftstore panic in `post_pending_read_index_on_replica` when a mid-queue `MsgReadIndexResp` is lost"; #18570 "Jepsen monotonic fails due to snapshot after peer is destroyed"; #17868 panic "assertion failed: cached_last < trunc_to_idx". Prior verification: none found for raftstore (I from absence). Existing multi-Raft TLA+? not searched.
Target: split/merge atomicity and read-index/lease read linearizability; model-check first in TLA+ then Verus on apply state machine; high cost (I).

Recommendation (I): most valuable target is Percolator in TiKV: real, widely used Rust, real correctness bugs in extensions, TLA+ spec exists to refine from, and the core is near-pure.

Papers to keep:
- Design and Modular Verification of Distributed Transactions in MongoDB; Schultz, Demirbas; PVLDB 18(12) 2025; https://www.vldb.org/pvldb/vol18/p5045-schultz.pdf
- Grove: a Separation-Logic Library for Verifying Distributed Systems; Sharma, Jung, Tassarotti, Kaashoek, Zeldovich; SOSP 2023; https://arxiv.org/pdf/2309.03046
- Verus: A Practical Foundation for Systems Verification; Lattuada et al.; SOSP 2024; https://dl.acm.org/doi/pdf/10.1145/3694715.3695952
- Consensus on Transaction Commit; Gray, Lamport; TODS 2006; (PDF URL not fetched)
- Trace Validation of Unmodified Concurrent Systems with OmniLink; arXiv 2601.11836 2026; https://arxiv.org/pdf/2601.11836 (not read)
Unverified (seen only in snippets): Systematization of Knowledge: Formal Verification of Consensus Protocols, arXiv 2608.21935.
