Scope: gossip membership/failure detection (SWIM, Lifeguard), Scuttlebutt anti-entropy, leases/distributed locks.

(authored by agents unless marked 🧑)
Tags: [F] fact with source, [I] inference.
Limitation: Google Scholar via pb-browser-page-extract returned "challenge_action_required" (CAPTCHA) twice (one retry after 20s). Not bypassed. Literature below came from WebSearch/WebFetch instead; it is NOT a Scholar sweep, so "no prior verification found" is weak evidence. Needs human to clear the CAPTCHA if a Scholar pass is wanted.

== 1. SWIM / Lifeguard ==
Used in practice
- [F] HashiCorp memberlist (Go) implements SWIM + Lifeguard; Consul uses it (Lifeguard paper arXiv 1707.00788: "Consul uses Raft to present a strongly consistent view of the group membership it obtains from memberlist" - via search summary). Serf, Nomad likewise (HashiCorp products; from my knowledge, not re-checked).
- [F] Fly.io Corrosion uses foca. README quote: "Uses Foca to manage cluster membership using a SWIM protocol" (https://github.com/superfly/corrosion). QCon 2025 talk: "we use Foca, which uses a SWIM protocol to manage cluster membership." (https://www.infoq.com/presentations/corrosion/)
- [F] Apple swift-cluster-membership implements SWIM+Lifeguard (https://github.com/apple/swift-cluster-membership).

Rust implementations
- foca: https://github.com/caio/foca ; v1.0.0 on crates.io; no_std+alloc; 240 stars; last commit 2026-08-02; 2 open issues. [F] LOC (my count of clone): src 7.8k Rust lines (incl. inline tests), repo 8.7k. Only known user: Corrosion (Fly.io). Transport- and identity-agnostic, I/O-free state machine: Input -> runtime Output.
- memberlist-rs (al8n): https://github.com/al8n/memberlist ; 144 stars; last commit 2026-09-15 (clone), pushed 2026-11-02; 18 open issues; 205k lines in workspace (many drivers: compio, reactor, embassy, smoltcp, embedded; proto separate). [F] It ports HashiCorp memberlist (and has serf). Large, fast-moving, many "[Adversarial review]" issues (looks LLM-assisted; [I]). Users: none found.
- chitchat (Quickwit): https://github.com/quickwit-oss/chitchat ; 383 stars; last commit 2026-11-09; MIT; 8.5k lines src, 10k total. Not SWIM: Cassandra/Scuttlebutt style with phi-accrual failure detector (see 2).
- Reference Go: hashicorp/memberlist 6.8k non-test lines + 8.3k test lines.

Real bugs (verbatim)
- foca #26 (closed): "BUG! Probe cycle finished without running its full course" - logged in Corrosion: "foca: error handling timer: BUG! Probe cycle finished without running its full course" https://github.com/caio/foca/issues/26 (also #2)
- foca #29 (closed): "I noticed that if the last saved state was `Suspect`, and it was applied on start, those members would never go back to a non-suspect state." https://github.com/caio/foca/issues/29
- foca #15 (closed): "If there's a network event causing a node to lose all connectivity, all members will appear down from its point of view. It doesn't appear to recover from this condition when the network goes back up." https://github.com/caio/foca/issues/15
- foca #34 (closed): "node1 has only receives `Notification::Rename`. However, there should be `Notification::Rename` and `Notification::Up`, as described in comments." (fast restart) https://github.com/caio/foca/issues/34
- memberlist-rs #150 (closed): "can fire an overdue SWIM timer (`handle_timeout`) **while gossip datagrams are still buffered behind the per-poll receive cap** ... can produce **premature suspicion/failure of a live node**" https://github.com/al8n/memberlist/issues/150
- memberlist-rs #131: "if a node issues a query and does **not** fully drain its response channel..." a later query from another node is dropped from the broadcast queue (serf layer). https://github.com/al8n/memberlist/issues/131
- [I] Pattern: bugs are state-machine/liveness (stuck suspect, no re-join, timer ordering), not memory safety; this is what a protocol-level proof targets, not what Rust's types give.

Prior formal verification
- [F] Vanlightly & Kuppe, TLA+ Conf 2022 talk "Obtaining statistical properties by simulating specs with TLC" models SWIM (+Inf, +Susp) in TLC simulation mode for message load/detection time, not safety proofs. https://conf.tlapl.us/2022/JackMarkusTLA+Statistics.pdf
- [F] Tran, Konnov, Widder, "A case study on parametric verification of failure detectors" (arXiv 2112.08826): Chandra-Toueg-style failure detectors in TLA+/Apalache, FAST, Ivy. Related, not SWIM. https://arxiv.org/pdf/2112.08826
- [F] No verification of SWIM, Lifeguard, memberlist, or foca found in my searches. [I] weak (Scholar blocked).

Proposed target
- foca core state machine (single crate, I/O-free, no_std: the best verification fit of everything here). Verus/Creusot proof that the implementation refines a SWIM spec. Properties: (a) incarnation numbers monotone; (b) a Down member is never resurrected without a higher incarnation/new identity; (c) probe cycle always reaches final state (the #26 BUG! path is an unproved invariant); (d) suspect timer always resolves (#29, #15 are liveness violations). Needs timing assumptions as explicit hypotheses: SWIM completeness is probabilistic [I], so prove safety + deterministic "eventual state transition" lemmas, not detection probability.
- Effort [I]: ~8k lines, but the logic file set (runtime.rs, members.rs, probe.rs, broadcast.rs) is a fraction; wire codec and tests separable. Rough: person-months, not weeks, mostly spec work.

== 2. Scuttlebutt anti-entropy ==
Used in practice
- [F] Cassandra gossip is based on Scuttlebutt (SYN/ACK/ACK2 digest exchange). Quickwit chitchat README: "A anti-entropy gossip algorithm called scuttlebutt is in charge of spreading a common state to all nodes." "borrowed from Cassandra, itself borrowing it from DynamoDB." https://github.com/quickwit-oss/chitchat
- [F] Quickwit uses chitchat "at the core" for membership and metadata, and "We also abuse `chitchat` in Quickwit and use it like a reliable broadcast, with different caveats."
Rust implementation
- chitchat (above). Only Quickwit named as user ("Used by" section empty). Healthy maintenance (commit 2026-11-09, 25 open issues).
Real bugs
- chitchat #121 (closed): "The current key GC logic is broken. It relies on heartbeat, assuming that all keys that were updated before the last heartbeat have been received. This is however incorrect." Scenario: "node2 receives partial update not contain key K but updating Node 1 heartbeat ... node1 GC key K" -> deleted key reappears. https://github.com/quickwit-oss/chitchat/issues/121
- chitchat #178 (closed): "Chitchat monotonicity assert failing. This causes a panic as reported in https://github.com/quickwit-oss/quickwit/pull/6196" https://github.com/quickwit-oss/chitchat/issues/178
- [I] #121 is exactly a convergence-safety bug (tombstone GC vs partial deltas): a model-level property that a proof would have caught. Same GC issue is noted in the literature: original Scuttlebutt cannot delete keys; Enes et al. add "Scuttlebutt-GC".
Prior formal verification
- [F] None of Scuttlebutt/chitchat/Cassandra gossip found. Related: Enes et al., "Efficient Synchronization of State-based CRDTs" (arXiv 1803.02750) gives the Scuttlebutt-GC variant (paper argument, no mechanization found). TLA+ GossipProtocol.tla in redis-rust is a different protocol. [I] CRDT convergence proofs exist in Isabelle (Gomes, Kleppmann et al., 2017; not re-checked here).
Proposed target
- chitchat's core delta/digest logic (state.rs, delta, digest, ~2-3k lines of the 8.5k [I], rest is transport/failure detector/tests). Properties: eventual convergence of per-node KV maps under any delivery order/duplication/loss; per-node version monotonicity (#178); GC never causes resurrection (#121; this requires a spec of the fixed rule). Very good fit: pure data-structure + merge logic, CRDT-like proof shape, Rust BTreeMap-heavy. Verus may be hard with std maps [I]. Best candidate in this report for a "real bug found by spec" story.

== 3. Leases / distributed locks ==
Used in practice
- [F] etcd leases and etcd concurrency.Mutex (Go); Chubby (Google, closed-source); ZooKeeper ephemeral nodes. Kubernetes leader election uses leases (my knowledge; not re-checked).
Rust implementations
- No canonical Rust lease/lock server. Rust clients: etcd-client (tonic client to etcd; not re-checked), ash-lock (https://github.com/ashforge-rs/ash-lock; small, fencing tokens over etcd; tiny and unknown adoption [F from search]). The lease logic that matters lives inside etcd's Go server (server/lease + client/v3/concurrency = 2.8k non-test Go lines in my clone).
Real bugs
- Jepsen etcd 3.4.3: "Unfortunately, this is unsafe, because multiple clients may hold the same etcd lock simultaneously." and "If a client waited for another client to release a lock, lost its lease, and then the lock was released, the server ... would not re-check to make sure the lease was still valid" https://jepsen.io/analyses/etcd-3.4.3 (excerpts as returned by the fetch tool, partly trimmed).
- Also from Jepsen: "mutex violations cannot be eliminated altogether, because distributed locks are a fundamentally unsafe concept in asynchronous systems." [F]
Prior formal verification
- [F] Search summary of arXiv 2605.17076 (S-Bus) says TiDB, CockroachDB, and etcd publish TLA+ specs without implementation refinement proofs (secondhand; not verified).
- [I] Lease safety depends on bounded clock drift, which is an assumption not a protocol property; proofs must state it.
Proposed target / port cost
- No usable Rust implementation to verify. Options: (a) verify a client-side lease holder + fencing-token check (small, new Rust, ~500 lines [I]) against a model of etcd revisions; verifies the part Jepsen says users get wrong. (b) port etcd lease manager: 2.8k Go lines [F, count] but it sits on raft/mvcc/bbolt; [I] a faithful port needs the KV store and txn layer too, so >> 10k lines; poor value. Recommendation [I]: (a), or skip leases since it is the weakest fit (Raft is already in scope elsewhere and leases are mostly built on it).

== Ranking [I] ==
1. chitchat Scuttlebutt delta/GC core (real convergence bug, pure logic, active).
2. foca (SWIM state machine; I/O-free; real liveness bugs).
3. lease client with fencing (small, new code).
memberlist-rs: too big/fast-moving (205k lines) to be a stable target.

== Papers worth keeping (PDF URLs I could confirm exist from searches; authors/venues from my memory unless noted) ==
- Lifeguard: Local Health Awareness for More Accurate Failure Detection. Dadgar, Phillips, Currey. DSN 2018 (arXiv 2017). https://arxiv.org/pdf/1707.00788
- SWIM: Scalable Weakly-consistent Infection-style Process Group Membership Protocol. Das, Gupta, Motivala. DSN 2002. https://www.cs.cornell.edu/projects/Quicksilver/public_pdfs/SWIM.pdf (URL from memory, not fetched)
- Efficient Reconciliation and Flow Control for Anti-Entropy Protocols. van Renesse, Dumitriu, Gough, Thomas. LADIS 2008. (PDF URL not confirmed.) Original Scuttlebutt.
- Efficient Synchronization of State-based CRDTs. Enes, Almeida, Baquero, Leitao. ICDE 2019 (arXiv 2018). https://arxiv.org/pdf/1803.02750
- A case study on parametric verification of failure detectors. Tran, Konnov, Widder. arXiv 2021 (venue not confirmed). https://arxiv.org/pdf/2112.08826
- Jepsen: etcd 3.4.3. Kingsbury. 2020. https://jepsen.io/analyses/etcd-3.4.3 (web report, not PDF)
- Formal Model-Driven Analysis of Resilience of GossipSub to Attacks from Misbehaving Peers. arXiv 2022. https://arxiv.org/pdf/2212.05197 (adjacent gossip verification; authors not confirmed)
Paper-collection note: per memory, kept papers go into /hdd1/sichanghe/paper_collection per its CONVENTIONS.md; I did not add them (needs confirmation of the keep list).
