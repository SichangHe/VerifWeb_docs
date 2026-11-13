# Breadth survey 2: further verification directions from real failures

(authored by agents unless marked 🧑)

Task (manager, relaying the human): 🧑 "we need to explore other directions as well". This report gives 8 directions that do not repeat vlm41_breadth, vlm4_writeup, vlm42_config, vlm43_ctlrace or vlm43_oidc. Full evidence, with more quotes and the caveats on each, is in notes_a.md (upgrades, HTTP), notes_b.md (leases, reconfiguration), notes_c.md (isolation, partitions) and notes_d.md (streaming, durable execution). FACT means sourced in those notes. OPINION and INFERENCE are mine.

Caveat for all quotes: they came through WebFetch, which summarizes pages, so some are fragments. Re-check them before quoting in a paper. Prior-work claims ("no proof exists") come from web searches only, not from Scholar.

Ranking (OPINION), with how each direction scores on the human's filters (distributed, Rust, real bugs):
1. Raft membership reconfiguration in Rust. Distributed, Rust, fresh real bugs.
2. HTTP framing agreement across proxy chains. Rust, real CVEs; only weakly distributed.
3. Mixed-version rolling upgrades. Distributed, real bugs; Rust evidence is mostly from small projects.
4. Durable execution / exactly-once effects (Restate). Rust; bug evidence is thin.
5. Lease and fencing safety under process pauses. Distributed; few recent bugs in big systems.
6. Liveness under partial network partitions. Distributed; the fix is known, so the work would be a proof only.
7. Transactional streaming (Kafka-protocol transactions). Real bugs; implementations are not Rust, and Vanlightly is already working on it.
8. Claimed isolation levels in distributed databases. Real bugs; mostly single-node and not Rust.

1. Raft membership reconfiguration (Rust)
Failures (FACT):
- openraft #2169 (Oct 2026), https://github.com/databendlabs/openraft/issues/2169: "a second membership request" in that window "passes every check and panics the core". "That window" is the time after its removal during which the removed leader "keeps leading for a short window, (150 ms by default)". Found by a Jepsen scenario.
- openraft #1395 (open Jul 2025 to Nov 2026), https://github.com/databendlabs/openraft/issues/1395: change_membership "can restore nodes that the original batch explicitly removed, even when the call succeeds."
- etcd #19557 (2025), https://github.com/etcd-io/etcd/issues/19557: "When promoting a learner, the change is only persisted in v2store, not in v3store", so the 3.5 to 3.6 "upgrade will fail, because the etcdserver will crash on bootstrap".
Property: safety of joint consensus with learners, plus an API postcondition: change_membership returns Ok only if the committed config equals the one requested.
Prior work: MongoRaftReconfig (Schultz et al., OPODIS 2021; CPP 2022 proof) covers MongoDB's protocol in TLA+, not Raft joint consensus or code. I found no verified Rust implementation of joint consensus.
Tractable (OPINION): yes. The scope is bounded (one module, pinned openraft version), and the bugs are logic errors in the protocol code, not in the algorithm. That fits "verify the real Rust implementation" in STORY.md. Targets: openraft, raft-rs.

2. HTTP framing agreement across proxy chains (Rust)
Failures (FACT):
- Pingora CVE-2025-4366, https://blog.cloudflare.com/resolving-a-request-smuggling-vulnerability-in-pingora/: "when caching was enabled, this logic was skipped on cache hits", leaving an unread body as "a vector for request smuggling."
- Pingora CVE-2026-2833 (Critical 9.3), https://github.com/cloudflare/pingora/security/advisories/GHSA-xq2h-p299-vjwv: Pingora "would immediately forward bytes following a request with an Upgrade header to the backend ... without waiting for a 101 Switching Protocols response."
- Pingora CVE-2026-2835, https://github.com/cloudflare/pingora/security/advisories/GHSA-hj7x-879w-vrp7: it "incorrectly handled multiple Transfer-Encoding values", which let an attacker "desync Pingora's request framing from backend servers".
- actix-http RUSTSEC-2026-0446 (Nov 2026), https://rustsec.org/advisories/RUSTSEC-2026-0446.html: it "accepts a bare line feed after the final chunk as the start of a trailer instead of rejecting the malformed request."
Property: for every byte stream the proxy accepts, the backend sees the same message boundaries the proxy saw; otherwise the proxy rejects the stream. The distributed version asks which normalization at the first proxy makes a whole chain of different parsers agree.
Prior work: HTTP Garden (Kallus et al., arXiv 2024) and T-Reqs (CCS 2021) are differential fuzzers. I found no machine-checked HTTP/1.1 framing proof.
Tractable (OPINION): grammar agreement is tractable but only moderately novel. Half of the bugs are connection-state bugs (cache-hit path, Upgrade), which need a state-machine proof. This is the closest direction to "web". Targets: pingora, hyper/httparse, actix-http.

3. Mixed-version rolling upgrades
Failures (FACT):
- TiKV #10774 (Rust, 2021), https://github.com/tikv/tikv/issues/10774: "TiKV with Titan enabled upgrade from 3.x versions to >=4.0 versions." The new version could not read the old files. TiKV #11226 is a rollback panic.
- tellus #261 (Rust, Nov 2026), https://github.com/tellus-rs/tellus/issues/261: "postcard writes a struct's fields in declaration order, with no names and no field numbers", so swapped fields arrive "silently wrong."
- TiDB #72744 (Nov 2026), https://github.com/pingcap/tidb/issues/72744: in a mixed 8.5.8/8.5.9 cluster, "reading the ADDDATE view fails", closed as "not a regression".
Property: for every version pair the rollout policy allows, everything one version writes (on the wire or on disk), the other decodes to the same meaning. A second, stronger property: the protocol's invariants hold while nodes run different versions.
Prior work: Zhang et al., SOSP 2021 (an upgrade-failure study plus testing), UpFuzz (NSDI 2026, fuzzing), Chait-Roth/Namjoshi/Wies (arXiv 2025, stateless workers only). I found no machine-checked rolling-upgrade proof.
Tractable (OPINION): the codec layer is tractable over serde types, but risks reading as engineering. The protocol layer is the PhD part. The weakness is that the Rust evidence comes from small projects, apart from TiKV in 2021.

4. Exactly-once effects in durable execution (Restate, Rust)
Failures (FACT):
- Restate docs #410 (Sep 2026), https://github.com/restatedev/docs-restate/issues/410: the docs claim "Side effects are executed exactly once", but "The receiver applied the request twice in 30 of 30 trials" when the worker was killed before journaling. The reporter thinks the docs, not the engine, are wrong.
- Temporal (dev.to blog, likely 2026), https://dev.to/remdore/temporal-finished-my-workflow-exactly-once-and-ran-its-first-step-four-times-59dh: "The workflow finished exactly once, as promised, and its first step ran four times". Temporal documents this behavior.
Property: under any crash/retry schedule, journaled steps take effect exactly once, and external calls take effect exactly once when they use an idempotency key derived from the journal.
Prior work: Durable Functions semantics (Burckhardt et al., OOPSLA 2021) assumes a single atomic store, and has no external effects and no implementation proof.
Tractable (OPINION): yes, as a conditional theorem over Restate's journal/replay code. The risk is that I found no confirmed engine bug, which conflicts with the human's filter.

5. Lease and fencing safety under process pauses
Failures (FACT):
- Jepsen etcd 3.4.3 (2020), https://jepsen.io/analyses/etcd-3.4.3: "etcd locks (like all distributed locks) do not provide mutual exclusion"; "loss of ~18% of acknowledged updates"; plus "a bug which failed to check lease validity after waiting for a lock."
- keel #77 (Nov 2026, small project, probably not Rust), https://github.com/laiwf94/keel/issues/77: "The lease bound in DESIGN.md covers clock _rate_ drift only. It does not cover a paused process."
Property: no stale read or write is accepted after a lease expires, with clock drift and unbounded pauses both modeled.
Prior work: LeaseGuard (SIGMOD 2026), CockroachDB leader leases (2026), and PaxosLease Revisited are protocol-level TLA+ work, not code.
Tractable (OPINION): a protocol-level paper would not be novel. Code-level verification with time and pauses modeled is novel but hard, and I found no recent big-vendor incident.

6. Liveness under partial network partitions
Failures (FACT):
- Cloudflare etcd (Nov 2020), https://blog.cloudflare.com/a-byzantine-failure-in-the-real-world/: a switch kept "LACP and BGP" up but "was not processing and forwarding all the packets"; "node 1 repeatedly initiated leader elections ... while node 2 repeatedly voted for node 3"; the replica failover that followed made "the cure ... worse than the disease".
- TiDB/PD, https://github.com/pingcap/tidb/issues/10576: "PD can get stuck electing a leader during a n/2+1 network partition".
Property: under non-transitive connectivity where a quorum can talk to each other, a leader is eventually elected and stays leader (PreVote plus CheckQuorum).
Prior work: Howard and Abraham (2020 blog analysis), Alquraan et al. (OSDI 2018) and Nifty (OSDI 2020) are studies and tools. OmniPaxos (Rust) designs the protocol for partial connectivity.
Tractable (OPINION): a liveness proof on openraft or OmniPaxos is feasible, but the fix is already known, so the result would be a proof without new bugs. It also partly overlaps the metastability item in vlm41.

7. Transactional streaming
Failures (FACT):
- Jepsen Bufstream (2024), https://jepsen.io/analyses/bufstream-0.1.0: the Kafka protocol has "no sequence number to order requests from the same client"; the torn-transaction issues "affect Kafka, Bufstream, and (presumably) other Kafka-compatible systems, and remain unresolved".
- Jepsen Redpanda (2022), https://jepsen.io/analyses/redpanda-21.10.1: "transactions routinely exhibited aborted reads and circular information flow under normal operation".
- Apache Iggy #3635 (Rust, 2026), https://github.com/apache/iggy/issues/3635: "it's actual data loss" (search-tool text, not fetched).
Property: acknowledged messages are neither lost nor duplicated, and transactions are atomic across failures.
Prior work: Vanlightly's TLA+/Fizzbee specs of Kafka transactions (2024, blog).
Tractable (OPINION): risky. The main bugs are in C++ and Go systems, and an industry expert is already modeling the protocol.

8. Claimed isolation levels in distributed databases
Failures (FACT):
- Jepsen ParticleDB (Rust, Oct 2026), https://jepsen.io/analyses/particledb-1.1.4: it "allowed internal anomalies and Lost Update with `serializable`". Most of its 96 issues needed "just a single server, single client, and no faults."
- Jepsen also tested MariaDB Galera 12.1.2 (2026), RavenDB 6.0.2 (2024) and TiDB 2.1.7 on Rust TiKV (2019).
Property: every execution satisfies the advertised isolation level, by refinement to an Adya-style specification.
Prior work: vMVCC (OSDI 2023; Go, single node, in memory). Elle and PolySI are black-box checkers.
Tractable (OPINION): a distributed snapshot-isolation proof for TiKV's Percolator is open but large. The recent bugs are single-node or in mode-skipping code, and a verified core may not cover them.

Gaps:
- No big-vendor 2025-26 postmortem was found for directions 3, 5 and 6.
- Arroyo, Fluvio, SurrealDB, Materialize and Neon yielded no bug evidence.
- T-Reqs authors and the KAR venue are partly from memory.
- Papers added to /hdd1/sichanghe/paper_collection (not committed): Durable Functions, KAR, both Schultz reconfiguration papers, the Jepsen etcd 3.4.3 report, PolySI, Alquraan OSDI 2018, Nifty, vMVCC, UpFuzz, Zhang SOSP 2021, HTTP Garden, T-Reqs, Chait-Roth et al. Not checked against CONVENTIONS.md naming.
