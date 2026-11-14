# Candidate directions, November 2026: merged list for judging

(authored by agents unless marked 🧑)

Why this exists: the human said 🧑 "I think you have failed to provide lots of directions for me to judge on". This file merges every direction not yet shown to the human into one list. Each direction gets two lines. "Broken" is one real failure with a link. "Prove" is the theorem we would prove and why that matters. Both lines are agent inference built on the cited failure.

Sources (full evidence, quotes and prior-work notes are in these files only):
- [a] [vlm48_dirs/a.md](vlm48_dirs/a.md): Rust project trackers and RustSec advisories
- [b] [vlm48_dirs/b.md](vlm48_dirs/b.md): distributed-systems, systems-venue and security papers, plus their incidents
- [c] [vlm48_dirs/c.md](vlm48_dirs/c.md): practitioner postmortems, Jepsen analyses and engineering blogs, 2023-2026
- [d] [vlm48_dirs/d.md](vlm48_dirs/d.md): web platform, sync engines, identity and desktop web apps
- [v41] [vlm41_breadth/REPORT.md](vlm41_breadth/REPORT.md) items 3-10, and [v46] [breadth2/REPORT.md](breadth2/REPORT.md) items 2-8 (both written earlier)

Markers: the tag after each title lists which sources found the direction. ★ means it fits STORY.md (keeping copies of state in agreement across tabs, devices, collaborators or identity providers, and proving the real Rust code converges and finishes). "top" means a source agent named it among its strongest picks. There is no other ranking.

Caveats (FACT, stated in the source files; partly superseded 2026-11-14, see prior_work_2026-11.md and the "Prior work" lines): Google Scholar blocked every agent with a CAPTCHA after a few queries, so most "no prior work" claims are weak. Many quotes came through a summarizing fetch tool and must be re-checked before citing.

Left out because the human already judged them: config pushes that crash the fleet (includes [b] 8, [c] 5 gossiped config, [c] 12 staged rollout); stale control-plane overwrites (AWS DNS race, [b] 1); Raft membership changes ([a] storage 1, [b] 6, [v46] 1); HTTP/1.1 framing across proxies ([v46] 2, judged with the vlm28 ideas as "too small"); refresh-token rotation races ([d] C4, part of the SSO direction); browser JIT exploits ([v41] 9, judged "too PL").

## How many directions exist (capture-recapture estimate)

Method: Chao2 incidence estimator over the 4 agents a-d, S = S_obs + ((m-1)/m) · Q1² / (2·Q2), where m = 4 agents, Q1 = directions found by exactly one agent, Q2 = found by exactly two.

Counts, including the excluded directions above: S_obs = 62, Q1 = 53, Q2 = 8, one direction found by three agents. Estimate: 62 + 0.75 · 53² / 16 ≈ 194.

What this means (INFERENCE): the agents searched different sources on purpose, so they rarely overlap. That breaks the estimator's assumption that every agent could find every direction equally, and the true number is probably higher. Treat the estimate as "well over 100 directions of this kind exist; we have seen about a third".

## Async Rust runtimes and concurrency

1. Cancellation safety of async code [a] top
   - Broken: in Pingora's cache, dropping a lookup mid-way leaks a lock, so "later same-key callers wait forever on the leaked zero-permit semaphore" (https://github.com/cloudflare/pingora/issues/931).
   - Prove: dropping an async task at any pause point leaves shared state consistent. This is a failure mode that every Rust async server has and no tool checks today.
   - Prior work (Scholar recheck 2026-11-14): partly covered by Lion at the runtime level (SOSP 2026; trusted Drop glue); application-level cancellation safety still open. See prior_work_2026-11.md.

2. Lost wakeups: a waiting task is never woken [a, b]
   - Broken: s2n-quic "Client::wait_idle() never returns when the client has zero connections" (https://github.com/aws/s2n-quic/issues/3382). Similar: Tokio #8772 deadlock, Pekko actor mailbox never rescheduled.
   - Prove: every task that waits is eventually woken or the system is finished, for Tokio's locks, channels, timers and actor mailboxes. This is a liveness proof about the scheduler that all async code trusts.
   - Prior work (Scholar recheck 2026-11-14): CHANGED, mostly done: Lion (SOSP 2026) verifies scheduling liveness of a Tokio-compatible runtime in Verus; Li-Beschastnikh-Summers (arXiv 2610.09198) verify progress of parts of smol, futures and tokio. Left: Tokio itself, channels, actor mailboxes.

3. Memory safety of Tokio's own primitives [a]
   - Broken: Tokio 1.54.0 was yanked because a timer "can drop an internal timer entry without synchronizing with the driver thread that is firing it" (https://rustsec.org/advisories/RUSTSEC-2026-0384.html).
   - Prove: Tokio's unsafe internals (channels, timer wheel) are race-free for every safe caller. This extends RustBelt-style proofs from the standard library to the async runtime.
   - Prior work (Scholar recheck 2026-11-14): still open; no verification of Tokio's unsafe primitives found.

4. Deadlock freedom with locks held across awaits and user callbacks [a]
   - Broken: Neon's WAL sender held a Tokio read lock during slow I/O, so "all subsequent read requests ... will be permanently queued behind the pending writer" (https://github.com/neondatabase/neon/issues/12875). Matrix SDK has the same with callbacks.
   - Prove: the lock and channel wait graph of a real Rust program has no cycle, even when user callbacks call back in. This turns a common production hang into a checkable rule.
   - Prior work (Scholar recheck 2026-11-14): partly done: static and runtime deadlock detectors for Rust exist (Zhang et al., arXiv 2401.01114, ASE journal 2026; Deloxide, IST 2026), bug finding, no proof covering await and callbacks.

## Network protocol code

5. Bounded memory against a hostile peer [a top, b]
   - Broken: in quinn (QUIC), "a peer can send one small MAX_STREAM_DATA frame naming a very large stream index, and `accept` then yields every stream up to that index" (https://rustsec.org/advisories/RUSTSEC-2026-0523.html).
   - Prove: memory held per connection is at most a function of the configured limits, for every peer behavior. Advisories show fixes that were then bypassed, so local patches do not suffice.
   - Prior work (Scholar recheck 2026-11-14): still open; see verification/bounded_memory/REPORT.md.

6. Never crash on hostile input [a]
   - Broken: quinn panicked on bad transport parameters because maintainers "did not properly assess usage of `unwrap()` calls" (https://rustsec.org/advisories/RUSTSEC-2026-0037.html). Kanidm died from unbounded recursion in a filter parser.
   - Prove: the receive path never panics, overflows or exhausts the stack, for all byte strings. A single crash is a remote denial of service.
   - Prior work (Scholar recheck 2026-11-14): still open; fuzzing only ("Don't Panic! Finding Bugs Hidden Behind Rust Runtime Safety Checks", 2025).

7. TLS handshake never trusts unauthenticated data [a]
   - Broken: rustls stored the server's key-exchange choice "before the server was authenticated", allowing a downgrade of later connections (https://rustsec.org/advisories/RUSTSEC-2026-0349.html).
   - Prove: rustls's state machine writes persistent state and releases data only after authentication, matching TLS 1.3. Existing TLS proofs cover the protocol, not this code.
   - Prior work (Scholar recheck 2026-11-14): partly done: "Formally verifying the state machine of TLS 1.3 handshake in OpenSSL" (2025, C code); hax/libcrux verify Rust protocol code (Bhargavan et al. 2025); rustls itself not verified.

8. Certificate validation equals the standard [a]
   - Broken: rustls-webpki checked only the first CRL distribution point, so revoked certificates could be accepted (https://rustsec.org/advisories/RUSTSEC-2026-0049.html).
   - Prove: webpki accepts a certificate chain exactly when RFC 5280 says so. This is the trust decision under most Rust TLS.
   - Prior work (Scholar recheck 2026-11-14): CHANGED, mostly done: Verdict (USENIX Security 2025), "the first end-to-end formally verified X.509 certificate validator", Rust verified in Verus, policies proved against a subset of RFC requirements; ARMOR (S&P 2024) also. Left only: rustls-webpki itself.

9. Servers survive errors and shut down cleanly [a]
   - Broken: in tonic, "a remote DoS attack ... can cause the server to exit cleanly on accepting a tcp/tls stream" (https://rustsec.org/advisories/RUSTSEC-2024-0376.html).
   - Prove: the accept loop never exits on a recoverable error, and shutdown finishes without dropping accepted requests. This is liveness for the server lifecycle in hyper, tonic and Pingora.
   - Prior work (Scholar recheck 2026-11-14): still open; nothing found.

10. Two parsers of one format agree [b]
    - Broken: the Rust zip crate let archives "appear to have different file paths and contents according to which tool is reading them" (https://github.com/advisories/GHSA-m665-v7pm-7grj).
    - Prove: two readers derived from one spec accept the same files and return the same contents. Parser disagreement is a recurring security bug class.
    - Prior work (Scholar recheck 2026-11-14): partly done: Vest (USENIX Security 2025) gives verified Rust parsers/serializers from one format spec; Pardiff (2024) finds parser differentials statically.

11. The name checked is the resource used [a, b]
    - Broken: a Wasmtime sandbox escape via trailing slashes was "a full filesystem sandbox escape for guests" (https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-m9f7-9w4p-gv38). Hono had the same shape for URL paths: "/admin\secret" reached "/admin/secret".
    - Prove: the path or URL that the access check sees is exactly the one the file system or router uses, for every input. This closes a whole family instead of one variant at a time.
    - Prior work (Scholar recheck 2026-11-14): still open; bug studies only ("Wormholes in the file system", USENIX Security 2026; URL parser studies 2022-2024).

## Sandboxes and permissioned runtimes

12. Every privileged call is permission-checked [a, d top]
    - Broken: Deno: "It is possible to bypass Deno's read/write permission checks by using `ATTACH DATABASE` statement" (https://github.com/denoland/deno/security/advisories/GHSA-8vxj-4cph-c596). Tauri: an attacker page "can invoke backend commands" (CVE-2026-42184).
    - Prove: every path from web-page code to an OS resource passes a check on that same resource. This is the only security promise of Deno, Tauri and Electron.
    - Prior work (Scholar recheck 2026-11-14): still open (Tauri, Deno); see vlm48_dirs/d.md C2.

13. Sandboxed code pays for all the work it causes [a]
    - Broken: Wasmtime fuel accounting could be reset, so "a guest that can run for exponential time using linear fuel" (https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-m63x-6p34-q65x).
    - Prove: total host work is bounded by the fuel and memory charged. Multi-tenant edge platforms rely on this to stop one tenant from starving others.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing found.

14. Verified WebAssembly compiler [b]
    - Broken: in Cranelift, a huge Wasm function could "force type-confusion or other arbitrary side-effects and escape the sandbox" (https://github.com/advisories/GHSA-897f-g5gm-fmxm).
    - Prove: compiled code behaves like the Wasm semantics for modules of any size. The compiler is the trusted base of the whole sandbox.
    - Prior work (Scholar recheck 2026-11-14): partly done: Crocus (ASPLOS 2024) and Arrival (2025) verify Cranelift instruction selection; not the whole compiler.

## Replicated storage and consensus

15. Acknowledged data survives crashes [a, b, c; also v41 3]
    - Broken: NATS "calls `fsync` ... only once every two minutes, but acknowledges messages immediately" and lost acknowledged writes (https://jepsen.io/analyses/nats-2.12.1). Same class: etcd 3.5 non-atomic apply, sled corruption.
    - Prove: after a crash at any point, each replica holds a prefix of what it acknowledged, with a disk model that separates written from synced. Consensus proofs usually assume a perfect disk.

16. Raft code matches Raft, beyond membership [a]
    - Broken: in raft-rs, "The follower acknowledges an index it never stored, the leader records a phantom `Progress::matched`" (https://github.com/tikv/raft-rs/issues/599). In openraft, a reordered purge panics a quorum "permanently".
    - Prove: the message-building and command-ordering code refines abstract Raft. The algorithm is proven; these bugs are in the code around it.
    - Prior work (Scholar recheck 2026-11-14): partly done: Bilý-Pereira-Müller refinement methodology for distributed Rust (OOPSLA 2025); runtime refinement checking (NSDI 2025); raft-rs/openraft code not proved.

17. Databases give the isolation they advertise [a, c; also v46 8]
    - Broken: RDS Postgres multi-AZ violates snapshot isolation because "the order in which a PostgreSQL primary makes transactions visible is determined by an in-memory lock" (https://jepsen.io/analyses/amazon-rds-for-postgresql-17.4). TiKV had a lost update with garbage collection.
    - Prove: every execution meets the stated isolation level, including replicas and garbage collection. Applications assume this without checking.
    - Prior work (Scholar recheck 2026-11-14): partly done: many black-box isolation checkers (Plume, IsoVista, Viper, VerIso 2023-2025); proofs over real code not found.

18. Application invariants under the database's real semantics [c]
    - Broken: Datomic: "This grant is both approved and denied at the same time" (https://jepsen.io/analyses/datomic-pro-1.0.7075). RavenDB lost updates by default.
    - Prove: given app transaction code and a formal model of the database, the app's invariants hold. Most web backends are exactly this kind of code.
    - Prior work (Scholar recheck 2026-11-14): partly done: VerIso (2025), "Verifying Isolation Levels of Database Implementations for Free Using Separation Logic" (arXiv 2607.15877, 2026).

19. Reads are up to date [b; also v46 5]
    - Broken: CCF documented "non-linearizability of read-only transactions in rare system conditions" (https://github.com/microsoft/CCF/pull/6167). Jepsen: etcd locks "do not provide mutual exclusion".
    - Prove: lease-based and read-index reads return the latest write under stated clock-drift and pause bounds, and name the assumption that breaks otherwise.
    - Prior work (Scholar recheck 2026-11-14): partly done: Bodega (2026), LeaseGuard (2026), LAW theorem (2025) design and argue lease reads; not code proofs.

20. Clusters with mixed versions during upgrades [c; also v46 3]
    - Broken: TigerBeetle replicas crashed during upgrade with "panic: checkpoint diverged" (https://jepsen.io/analyses/tigerbeetle-0.16.11). A Fly.io schema change made its CRDT store rewrite every row.
    - Prove: safety and liveness hold for any mix of old and new nodes, and mixed schemas converge. Every upgrade passes through this state.
    - Prior work (Scholar recheck 2026-11-14): partly done: UpFuzz (NSDI 2026) tests upgrade format incompatibility; no proofs.

21. Durable execution: effects happen once per run [a; also v46 4]
    - Broken: in Restate, "When the old timer fires, Restate appends a `Notification: Sleep` with the old run's completion id to the **new** run's journal" (https://github.com/restatedev/restate/issues/5425).
    - Prove: under any crash and retry, each step takes effect once, and leftovers of a dead run never reach a new run. "Exactly once" is the product's main promise.
    - Prior work (Scholar recheck 2026-11-14): partly done: ExoFlow (OSDI 2023), Halfmoon (SOSP 2023), Boki, Burckhardt et al. 2022 give exactly-once designs with some formal semantics; Restate code not proved.

22. Streaming: one stuck job does not block others [a]
    - Broken: RisingWave: "why does a decoupled sink's inability to make external progress become a prerequisite for unrelated tables to checkpoint" (https://github.com/risingwavelabs/risingwave/issues/27837).
    - Prove: a failure blocks only jobs that depend on it, and all others keep checkpointing.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

23. Transactional streaming (Kafka protocol) [v46 7]
    - Broken: Kafka transaction issues "affect Kafka, Bufstream, and (presumably) other Kafka-compatible systems, and remain unresolved" (https://jepsen.io/analyses/bufstream-0.1.0).
    - Prove: acknowledged messages are not lost or duplicated, and transactions are atomic across failures. (Implementations are not Rust; an industry expert is already modeling it.)
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close on Scholar.

24. Database clients that report a "maybe" as "failed" [c]
    - Broken: "jetcd incorrectly retries non-idempotent requests which may have actually succeeded" (https://jepsen.io/analyses/jetcd-0.8.2).
    - Prove: every failure the client reports is definite, and no request runs twice. Client libraries are small and share this pattern.
    - Prior work (Scholar recheck 2026-11-14): partly related: "Automated verification of idempotence for stateful serverless applications" (OSDI 2023); client libraries not covered.

## Cluster operations and control planes

25. Kubernetes API server gives what verified controllers assume [b; also v41 6]
    - Broken: "a client that connects to that api server can read an arbitrarily old history" (https://github.com/kubernetes/kubernetes/issues/59848).
    - Prove: the API server's list and watch meet the assumptions of verified controllers (Anvil), or list exactly when they do not. Today those proofs rest on an unchecked assumption.
    - Prior work (Scholar recheck 2026-11-14): still open; Anvil (OSDI 2024) and "Who Watches the Watchers?" (2026) found, API-server assumption not checked.

26. Retry storms and recovery time [b, c; also v41 5]
    - Broken: Google Cloud, June 2025: "Service Control did not have the appropriate randomized exponential backoff" (https://status.cloud.google.com/incidents/ow5i3PPK96RduMcb1SsW).
    - Prove: after a mass failure, load returns to normal within a computed time, below a stated load. No accepted specification of this exists yet.
    - Prior work (Scholar recheck 2026-11-14): CHANGED, partly done: "Formal analysis of metastable failures in software systems" (Alvaro, Isaacs, Majumdar et al., arXiv 2025) computes recovery times on models; "Modeling metastability" (HotOS 2025); not on code.

27. Overloaded node mistaken for a dead node [c]
    - Broken: at Discord, "all of the hosts “dropped out” of the consistent hash ring" because heartbeats queued behind work (https://discord.com/blog/behind-the-scenes-of-the-3-25-26-voice-outage).
    - Prove: the heartbeat path never waits on the data path, so a live node is never removed under bounded load.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

28. Leader election under partial network partitions [v46 6]
    - Broken: at Cloudflare, "node 1 repeatedly initiated leader elections ... while node 2 repeatedly voted for node 3" (https://blog.cloudflare.com/a-byzantine-failure-in-the-real-world/).
    - Prove: when a quorum can still talk, a leader is eventually elected and stays. The fix is known, so this would be a proof without new bugs.
    - Prior work (Scholar recheck 2026-11-14): still open; "Partial network partitioning" (TOCS 2023) is a study.

29. Load balancer stops sending to a dead backend [b]
    - Broken: Envoy: when a backend reboots, "the total TPS observed by the proxy drops to almost zero in several seconds" (https://github.com/envoyproxy/envoy/issues/39737).
    - Prove: from the config values, traffic to a dead backend falls below a bound within a computed time. Usable as a config checker.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

30. Meaning of a service-mesh configuration [b]
    - Broken: Istio: two entries on one host, "only one of them can be accessed in practice, sometimes 8080 while sometimes 9080" (https://github.com/istio/istio/issues/49550).
    - Prove: the Envoy config Istio generates implements a written meaning of the resources, independent of merge order.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

31. Microservice cache over a weaker store [b]
    - Broken: NOT FOUND; the source agent found no public incident.
    - Prove: the cache's consistency degrades in a stated, bounded way when the store is not linearizable.
    - Prior work (Scholar recheck 2026-11-14): not searched (no incident).

32. Credential rotation never revokes too early [c]
    - Broken: Cloudflare R2: old credentials were deleted while new ones went to the wrong place; "the --env parameter was inadvertently omitted" (https://blog.cloudflare.com/cloudflare-incident-march-21-2025/).
    - Prove: the old key is revoked only after every consumer uses the new one, under delayed propagation.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

33. Revocation reaches every peer [c] ★
    - Broken: Tailscale expired node keys stayed usable for up to 19 days; "There was a flaw in Tailscale's logic for expiring node keys" (https://tailscale.com/security-bulletins, TS-2023-002).
    - Prove: every revoked key leaves every peer's view within a time bound, even when the control server is unreachable. Unlike the TLS case, here expiry itself was what broke.
    - Prior work (Scholar recheck 2026-11-14): still open; only measurement ("A First Look at Certificate Revocation Latency", 2026).

34. Recovery that depends on what it recovers [c; also v41 7]
    - Broken: Cloudflare's high-availability control plane had "dependencies on services exclusively running in PDX-04" (https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/).
    - Prove: no failover or rollback path depends on the failed component. This is a graph check; little verification novelty.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

35. Automated actions stay in their declared scope [v41 8]
    - Broken: Heroku, June 2025: an OS update ran when it "should have been disabled", causing up to 24 hours of downtime (source in vlm41_breadth/outages.md).
    - Prove: each automated action touches only its declared scope, checked like AWS's policy checkers.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

36. Clock jumps in scheduling [c]
    - Broken: Slack replication "had unexpected failures due to a time-logic configuration change" (https://slack-status.com/2024-11/81f9bbf150e0daac). Weak: Slack does not name the cause.
    - Prove: routing and dispatch are unaffected by clock jumps.
    - Prior work (Scholar recheck 2026-11-14): still open; timeout-bug fuzzing only (Chronos, S&P 2024).

## Multi-tenant serving

37. LLM serving never reads another request's cache [c]
    - Broken: Cloudflare Workers AI was "attending over stale cache pages that still held data from earlier requests" (https://blog.cloudflare.com/kv-cache-exposure-remediation/).
    - Prove: a cache page is readable only by its current owner, and configured capacity never exceeds physical capacity.
    - Prior work (Scholar recheck 2026-11-14): still open for stale-page reads; KV-cache timing side-channel defenses exist (e.g. Mirage, arXiv 2611.10756, 2026).

38. Per-request state does not leak across requests at the edge [c]
    - Broken: Workers KV treated global state as per-request (https://blog.cloudflare.com/workers-kv-restoring-reliability/; weak, quote not verified).
    - Prove: state written while serving one request is invisible to the next unless declared shared.
    - Prior work (Scholar recheck 2026-11-14): partly done: Groundhog (EuroSys 2023) enforces request isolation in FaaS; no proof.

## Sync engines and collaborative state ★

39. Offline-first sync engines apply each change once [d] ★
    - Broken: Zero 0.26: "Fix duplicate mutations when retry transaction succeeds" (https://zero.rocicorp.dev/docs/release-notes/0.26).
    - Prove: after any disconnects and retries, every acknowledged change is applied exactly once and the client equals server plus pending changes. These engines sit under many collaborative web apps.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

40. Matrix room state converges [d top] ★
    - Broken: Matrix.org: "delayed federation traffic could cause key-value state associated with a room to revert to an earlier state", observed in public rooms including #rust (https://matrix.org/blog/2025/08/project-hydra-improving-state-res/).
    - Prove: all honest servers with the same events compute the same room state, in any delivery order. Rust implementation: ruma-state-res.
    - Prior work (Scholar recheck 2026-11-14): still open; only a Matrix mapping study (2026).

41. Group key agreement does not fork (MLS) [d top] ★
    - Broken: "Two concurrent commits against the same group fork the epoch" (https://github.com/CIRISAI/CIRISEdge/issues/604, a small project).
    - Prove: members that accept a commit agree on keys and membership, with no unrecoverable fork. Rust implementation: OpenMLS.
    - Prior work (Scholar recheck 2026-11-14): partly done: MLS protocol has machine-checked proofs in F* (TreeKEM, S&P 2025; TreeSync, USENIX Security 2023; Wallez thesis 2025); OpenMLS Rust code not verified.

42. Firefox bookmark sync [d] ★
    - Broken: "[meta] Bookmarks dataloss ... caused by Sync" (https://bugzilla.mozilla.org/show_bug.cgi?id=621584; old, closed WONTFIX).
    - Prove: bookmark trees on all devices converge to a valid tree without dropping live entries. The merger is Rust (application-services).
    - Prior work (Scholar recheck 2026-11-14): partly done: move-op CRDT verification on models (Da-Kleppmann 2024; Nieto et al. 2022); dogear code not.

43. Password manager vault sync [d] ★
    - Broken: Bitwarden, 2018: "\"Sync Vault\" does not really sync. Possible data loss" (https://github.com/bitwarden/server/issues/332).
    - Prove: no acknowledged edit is lost under concurrent edits from two devices.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

44. Bluesky (AT Protocol) relays mirror accounts correctly [d] ★
    - Broken: "Relays stopped picking up PDS"; the account was wrongly "marked as 'deactivated' on a large number of independent relay instances" (https://github.com/bluesky-social/atproto/issues/4583).
    - Prove: a relay ends with the same repository as the source, or marks it out of sync instead of silently diverging.
    - Prior work (Scholar recheck 2026-11-14): still open; only the AT Protocol design paper (2024).

45. Applying a bad collaborative-editing update fails safely [a] ★
    - Broken: Yrs: "applying that update with `TransactionMut::apply_update` panics" (https://github.com/y-crdt/y-crdt/issues/733).
    - Prove: applying any update never crashes, and a rejected update leaves the document unchanged. This complements convergence proofs, which assume well-formed updates.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

46. Cross-process lock for shared local state [a] ★
    - Broken: Matrix SDK's lock between the app and its notification process: "we have evidence that it doesn't actually work" (https://github.com/matrix-org/matrix-rust-sdk/issues/3313).
    - Prove: no process acts on stale cached state after another took over, with OS suspension at any point. The implementation has no spec, so the spec is part of the contribution.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

## End-to-end encryption and identity

47. Encrypted messenger checks every identity field [a]
    - Broken: matrix-sdk-crypto "is missing a check for the sender's user ID ... could be exploited to spoof the sender" (https://github.com/matrix-org/matrix-rust-sdk/security/advisories/GHSA-wfq4-36m3-9g42).
    - Prove: any message shown as from user U was encrypted by U's device, against a malicious server. Protocol proofs exist; this proves the Rust code does what they assume.
    - Prior work (Scholar recheck 2026-11-14): still open; Matrix attacks (Albrecht et al., S&P 2023) and protocol proofs, no code proof.

48. Passkey (WebAuthn) server verification [b]
    - Broken: SimpleWebAuthn accepted a chain ending at "some self-signed cert" rather than "one of the configured trust anchors" (https://github.com/advisories/GHSA-6hxq-p678-4hr2).
    - Prove: the server accepts a login only if every step of the W3C checklist holds.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

49. Passkey lists stay in sync between site and password manager [d] ★
    - Broken: Zitadel: a removed passkey stays, "The manager keeps offering it, and the sign-in fails" (https://github.com/zitadel/zitadel/issues/12987). On iOS, deleting one account's passkey can delete another's.
    - Prove: the offered passkeys eventually equal the site's accepted set, and a signal never deletes another account's passkey.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

50. OAuth tokens through third-party connectors [b]
    - Broken: Salesloft Drift, 2025: attackers used "compromised OAuth tokens associated with the Salesloft Drift third-party application" (https://cloud.google.com/blog/topics/threat-intelligence/data-theft-salesforce-instances-via-salesloft-drift).
    - Prove: a token linked by one user cannot be used by another user or tenant, even with malicious connectors.
    - Prior work (Scholar recheck 2026-11-14): still open; OAuch (2022) compliance testing only.

51. Crypto wallet signs what it shows [b]
    - Broken: Bybit, 2025: Safe{Wallet}'s web scripts were "injected with malicious code manipulating transactions" (https://www.sygnia.co/blog/sygnia-investigation-bybit-hack/).
    - Prove: a compromised page can only get signed what the user confirmed in a trusted display.
    - Prior work (Scholar recheck 2026-11-14): still open; "What I Sign Is Not What I See" (arXiv 2026) is a usability study.

52. CSRF protection covers every cross-site request a browser can send [b]
    - Broken: Hono: Chromium's `<a ping>` "sends a cross-origin POST with the user's cookies" with a content type the filter missed (advisory GHSA-46wx-v44x-9hh2).
    - Prove: from a model of what browsers can send cross-site with cookies, the middleware blocks every such request.
    - Prior work (Scholar recheck 2026-11-14): still open; CSRF in OIDC formal analysis (2026) is protocol-level.

## Browser platform

53. Navigation and session history always finish [d top]
    - Broken: in the HTML spec, "the iframe never fires its load event, and waitForLoad waits forever"; Ladybird, following the spec, crashed (https://github.com/whatwg/html/issues/12861).
    - Prove: every navigation finishes or is visibly aborted, in a model of the spec, then in Servo or Ladybird. Several open 2026 spec bugs sit in this one algorithm.
    - Prior work (Scholar recheck 2026-11-14): still open; see verify_standards.md.

54. IndexedDB transactions are not silently lost [d top]
    - Broken: Firefox: "active transactions will be silently aborted" when a page enters the back-forward cache (https://bugzilla.mozilla.org/show_bug.cgi?id=1458342, open 8 years).
    - Prove: committed transactions are serializable and survive as promised; page lifecycle never aborts one silently. Servo has a Rust implementation under active change.
    - Prior work (Scholar recheck 2026-11-14): partly done (testing): IDBFuzz (ASE 2025) fuzzes web storage databases; no proof.

55. Servo enforces CORS [d]
    - Broken: Servo delivered "all 19 body bytes" of a response that failed the CORS check (https://github.com/openharmony-rs/servo-ohos/pull/42, a downstream fork).
    - Prove: Servo's fetch code refines the Fetch spec: a script reads a cross-origin response only if CORS passed.
    - Prior work (Scholar recheck 2026-11-14): still open for Servo; WebSpec (S&P 2023) models browser security mechanisms.

56. HTTP cache never serves one user's response to another [d]
    - Broken: Servo's cache served a response stored without an Origin header to a request with one (https://github.com/L-K-M/servo/pull/41).
    - Prove: the cache returns a stored response only when the request matches per RFC 9111, so user A's response never reaches user B. (Possibly close to the cache direction the human called "remote".)
    - Prior work (Scholar recheck 2026-11-14): still open; cache deception/poisoning attack studies only.

57. Storage partitioning keeps sites apart [d] ★
    - Broken: on Chrome, "shared partitioned storage, different storage access"; wordpress.com reverted a rollout after logged-in state leaked between frames (https://github.com/privacycg/CHIPS/issues/88).
    - Prove: state written under one partition key is never readable under another, across cookies, IndexedDB, service workers and BroadcastChannel.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing close.

58. Web Locks are always released [d] ★
    - Broken: Safari: "Web Locks held in a Worker are not released on page refresh or exit", risking deadlock (https://bugs.webkit.org/show_bug.cgi?id=239614, fixed 2022).
    - Prove: every lock is eventually released or its holder destroyed, even with frozen pages.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing found.

59. Service worker updates never mix versions [d] ★
    - Broken: "Old page + new module = an API-contract lottery after every deploy" (https://github.com/mentria-ai/website/issues/1163; app-level, small repos).
    - Prove: every tab eventually runs one consistent app version and never mixes old code with new cached files.
    - Prior work (Scholar recheck 2026-11-14): still open; nearest: "Consistent Updates for Scalable Microservices" (2026).

60. Browser extensions survive service-worker restarts [d]
    - Broken: MetaMask's move to Manifest V3 flooded errors and dropped messages, "Even 100+ times from a single service worker restart" (https://github.com/MetaMask/metamask-extension/issues/15970).
    - Prove: each message is delivered once or the sender learns it failed, and state is recovered after any restart.
    - Prior work (Scholar recheck 2026-11-14): still open; MV3 studies only.

61. Push subscriptions stay in sync [d] ★
    - Broken: the browser's subscription-change event "doesn't have oldSubscription", so servers keep dead subscriptions (https://github.com/w3c/push-api/issues/325).
    - Prove: the server's set of live subscriptions eventually equals the browser's, even when events are lost.
    - Prior work (Scholar recheck 2026-11-14): still open; nothing found.

## Cross-cutting (not projects on their own)

62. Code matches its checked design [v41 4]: industry checks code against specs only through logs and tests; this gap underlies many items above.

63. The trusted spec is right [v41 10]: Cosmos DB says a spec error could have "escaped the notice of those reviewing it"; it limits every proof above.
