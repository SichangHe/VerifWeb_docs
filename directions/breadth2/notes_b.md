(authored by agents unless marked 🧑)

Notes B: (1) leases, fencing, clock assumptions; (2) Raft/Paxos membership reconfiguration.
Quotes were fetched with WebFetch (a small model extracted them; treat as near-verbatim, not byte-checked). Items marked "search-summary only" were not fetched.

## 1. Leases, leader election, fencing tokens, clock/pause assumptions

### Real failures
1. etcd 3.4.3 locks, Jepsen (Kingsbury, 2020-01-30). https://jepsen.io/analyses/etcd-3.4.3 , PDF https://jepsen.io/analyses/etcd-3.4.3.pdf
   - FACT: "However, etcd locks (like all distributed locks) do not provide mutual exclusion." Also: "we could reliably induce the loss of ~18% of acknowledged updates" (2 s lease TTL, 5 processes, pauses every 5 s).
   - FACT (report abstract): "those risks were exacerbated by a bug which failed to check lease validity after waiting for a lock." Server did "not re-check to make sure the lease was still valid" before telling the client it held the lock (etcd issue #11456).
   - FACT (etcd blog, search-summary only, https://etcd.io/blog/2020/jepsen-343-results/): recommended fix is to use the lock key's revision as a fencing token that the resource checks.
2. keel (lease reads timed in ticks), issue #77, opened and closed 2026-11-01. https://github.com/laiwf94/keel/issues/77
   - FACT: "When `NodeLoop` is blocked, for example by an fsync that hangs or a long garbage collection, it misses ticks." "When the old leader wakes up it still thinks its lease is valid, so it answers a queued `LEASE` read from its own state" "That breaks linearizability." "The lease bound in DESIGN.md covers clock _rate_ drift only. It does not cover a paused process."
   - Language not stated on the page; looks like Java (INFERENCE). Small project; weak as "widely used".
3. d-engine (Rust Raft), jepsen issue #28, 2026-10-04. https://github.com/deventlab/d-engine-jepsen/issues/28
   - FACT: "Lease reads, election and replication timers use the monotonic clock (tokio Instant)." "The risk is a slow leader clock: the leader believes its lease is valid after the followers have elected a new leader." "No Jepsen scenario injects clock faults, so this is untested." This is a risk report, not an observed violation. Related #27 (search-summary only): a lease bug visible only with 5+ voters.
4. Consul "consistent" reads, Jepsen etcd/Consul 2014 (older than 2019; context only). https://aphyr.com/posts/316-jepsen-etcd-and-consul . Search-summary only, not fetched.
5. Kibisis PR #3 (tiny project, search-summary only): lease deadline stored as whole seconds, TTL under 1 s gave an already-expired lease. https://github.com/Perseus-Computing-LLC/kibisis/pull/3
- Gap: I found no 2024-2026 postmortem from a large vendor where clock skew caused a lease split brain. The web search returned none. FACT about my search, not about the world. Recent evidence is small Rust/Java projects plus Jepsen 2020.

### Property to verify (INFERENCE: my formulation)
Lease-read safety: for every read r served by node n under lease L, every write acknowledged before r's start is in n's state, assuming (A1) each clock rate lies in [1-eps, 1+eps] of real time, (A2) the process is not paused between its lease check and the reply, or the check is re-done after the last blocking call. Refinement: state a proof where A1/A2 are explicit hypotheses, then show the Rust code discharges A2 (e.g., lease check happens after every .await/blocking point, with monotonic Instant read adjacent to the state read). Fencing: if a resource rejects tokens lower than the highest seen, and tokens are issued monotonically, no write from a deposed holder is applied. Etcd failure 1 is exactly "lease check not adjacent to use".

### Closest prior verification work
- LeaseGuard: Raft Leases Done Right, Davis, Demirbas, Deng, SIGMOD 2026 (arXiv 2512.15659; already in paper_collection). FACT: "rigorously specified in TLA+", relies on bounded-uncertainty clocks. Open: spec only; no code-level link; no pause model.
- Scalable Leader Leases for Multi Consensus Groups in CockroachDB, ACM 2026, https://dl.acm.org/doi/pdf/10.1145/3788853.3803081 (search-summary: properties "formally verified using TLA+"). Paywalled; not downloaded. Open: TLA+ only, Go code.
- PaxosLease Revisited: A Checked Model of Diskless Distributed Leases, Trencseni, arXiv 2026 (already in collection). Model checking only.
- T-Lease, arXiv 2101.06485 (TLA+ lease primitive). Not read in detail.
- Muratdem/RaftLeaderLeases TLA+ models: https://github.com/muratdem/RaftLeaderLeases
- Jepsen etcd 3.4.3 report saved to paper_collection.

### Tractability
- FACT: the specs above exist; hence protocol-level work is done. OPINION: a protocol-level TLA+ lease paper is not novel as a PhD.
- OPINION: the open piece is the code-to-assumption gap: pauses, async cancellation, tokio timers, monotonic vs wall clock. A verified Rust Raft node with a time/pause model (e.g., Verus or Creusot with a ghost clock; Aeneas/Lean) is novel but needs a time model for async Rust, which is hard. Risk: reviewers may see it as "assume bounded drift, prove, done".
- Hot-path filter: lease reads are a performance optimization (hot path), but real bugs exist (items 1-3), so allowed under the human's filter. OPINION.

### Rust targets
openraft (lease read / `get_read_log_id`), TiKV raft-rs + TiKV lease reads (`LocalReader`), d-engine, TiKV PD leader election, tikv/raft-engine not relevant. Not verified by me which of these has lease code: check before committing.

## 2. Membership reconfiguration in Raft/Paxos implementations

### Real failures
1. openraft #2169, opened 2026-10-17, closed 2026-10-21 (fix #2196). https://github.com/databendlabs/openraft/issues/2169
   - FACT: "`next_coherent` bridges with `[A, B].bridge_to(C)`, which is `[B, C]`. The leader is in neither half." "the second step at index 334 panicked its core." A removed leader "keeps leading for a short window, (150 ms by default)"; a second membership request in that window "passes every check and panics the core." Release builds do not panic: six debug-panicking runs "pass in release." Found by an added Jepsen scenario.
2. openraft #1395, opened 2025-07-24, closed 2026-11-09 (PR #2284). https://github.com/databendlabs/openraft/issues/1395
   - FACT: "The second step of `change_membership()` recomputes learner retention from the joint membership." "It can restore nodes that the original batch explicitly removed, even when the call succeeds." Response had voters {0}, learners {1,2,3}; expected learners {2,3}. Fix: "Preserve the exact validated target from the first step through finalization."
   - A user-visible wrong final configuration, reported success. Open 15 months.
3. etcd #19557, 2025-03-08 to 2025-03-28. https://github.com/etcd-io/etcd/issues/19557
   - FACT: "When promoting a learner, the change is only persisted in v2store, not in v3store." "In 3.5, the v2store is the source of truth for the membership data. In 3.6, v3store (bbolt) is the source of truth" "All etcd patch versions in `v3.5.1 - v3.5.19` are affected." With two or more promoted learners "the upgrade will fail, because the etcdserver will crash on bootstrap". Priority critical-urgent; delayed Kubernetes 1.33 timing. Follow-up #20793 (snapshot from old member propagates wrong membership).
4. openraft early joint-consensus bugs (changelog, search-summary only): leader "decide it could commit without replication by checking only the first config", data loss in joint config, fixed v0.6.2. https://github.com/databendlabs/openraft/blob/main/change-log.md
5. raft-rs / TiKV (search-summary only, not fetched): TODO in `commit_apply`: "it may never auto_leave if leader steps down before enter joint is applied." TiKV #17602 (2024): BatchSplit hangs in joint state until PD runs leave-joint. https://github.com/tikv/tikv/issues/17602 . No raft-rs data-loss bug found.
6. Ongaro 2015, single-server change bug: data loss and permanent split brain (raft-dev, https://groups.google.com/g/raft-dev/c/t4xj6dJTP6E). Older than 2019; context. Joint consensus not affected (FACT per post, search-summary).

### Property to verify (INFERENCE: my formulation)
(a) Safety: at most one leader per term and committed entries never lost, across all interleavings of change_membership calls, leader failures, and retries, including the intermediate joint states. (b) Functional correctness of the API: if change_membership(T) returns Ok, then the committed config equals T (voters and learners) unless a later change was committed. Bug 2 violates (b) while (a) holds, so (b) is a separate, API-level property that safety proofs do not cover. (c) Liveness: a joint config is eventually left or the caller is told it is stuck (bugs 1, 5).

### Closest prior verification work
- Design and Analysis of a Logless Dynamic Reconfiguration Protocol, Schultz, Zhou, Dardik, Tripakis, OPODIS 2021, arXiv 2102.11960 (saved). FACT: TLA+ spec and safety proof for MongoRaftReconfig.
- Formal Verification of a Distributed Dynamic Reconfiguration Protocol, Schultz, Dardik, Tripakis, CPP 2022, arXiv 2109.11987 (saved). FACT: TLAPS proof; notes Ongaro's TLA+ spec omitted reconfiguration and Verdi did not verify Raft reconfiguration. Open: MongoDB's protocol, not Raft joint consensus; spec not code.
- Federated Formal Verification, arXiv 2606.02019 (2026, search-summary only): says Verdi-Raft excludes reconfiguration. Not read; quality unknown.
- Verus Raft core in makodb/mako PR #92 (search-summary only): membership change not in verified scope. https://github.com/makodb/mako/pull/92
- Interactive Safety Verification of Distributed Protocols by Inductive Proof Decomposition, arXiv 2404.18048 (search-summary only).
- Open: no verified Rust implementation with joint consensus + learners + API-level result found. FACT about my search only; verify with Scholar before claiming.

### Tractability
- FACT: bugs 1 and 2 were found by testing (Jepsen scenario, review), not proof; 3 is a persistence/versioning bug between two stores, not protocol logic.
- OPINION: promising and feasible. A mechanized spec of openraft's actual two-step change_membership (including learners, retain flag, interrupted/retried calls) with refinement to the Raft safety spec is a bounded scope; the real novelty is verifying API-level postconditions and interrupted-call states. Bug 2 shows the gap concretely.
- OPINION: the etcd bug family (state migrated between two sources of truth across versions) is a different, upgrade-compatibility direction; possibly out of scope here.
- Risk (OPINION): openraft changes fast (3 membership fixes in Oct-Nov 2026), so a proof target must be pinned to a version; maintainer is active and responsive, which helps.

### Rust targets
openraft (databendlabs/openraft: membership.rs, change_membership), tikv/raft-rs (joint consensus, `auto_leave`), TiKV raftstore conf change, PD. Others (not checked): async-raft forks, Rabia/other Rust Raft crates.
