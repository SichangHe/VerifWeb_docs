# vlm48 candidate directions, set a
(authored by agents unless marked 🧑)

24 candidates mined from Rust project trackers and RustSec (2026-11-13). Each one is a class of recurring bugs, not a single bug. For each, "broken:" gives one real failure with a link and a verbatim quote, "prove:" gives the theorem, and the evidence follows. Opinions are marked OPINION.
Literature check: NOT DONE. Google Scholar showed a CAPTCHA on the first query and it was not bypassed (raw/prior.md).
net = tokio/hyper/h2/rustls/quinn/tonic/Pingora/s2n-quic; storage = TiKV/openraft/raft-rs/Garage/Neon/Restate/Fluvio etc.; client = Deno/Servo/Wasmtime/Kanidm/Automerge/Yrs/Loro/Iroh/Matrix.


# part: net

Candidate research directions mined from RustSec advisories (advisory-db clone, fetched 2026-11-13) and GitHub issues (gh issue list/view) for tokio, hyper, h2, rustls, quinn, tonic, Pingora, s2n-quic. linkerd2-proxy has GitHub issues disabled, and none of its advisories are in RustSec, so it is not represented. Each candidate is a class. Quotes are verbatim from fetched text. Text marked OPINION is my judgment. Nothing was posted anywhere.

Caveat (OPINION): several 2026 issues (pingora 931-933, 1024, 1028, 1031; s2n-quic 3210, 3257, 3259) read like AI-generated audit reports, and s2n-quic 3210 even cites quiche source paths. They are open and unconfirmed, so I use them only as supporting evidence, and the RustSec advisories as the anchor wherever possible.

=====================================================================
1. Cancellation safety: dropping an async future at any await point must leave shared state consistent
broken: https://github.com/cloudflare/pingora/issues/931 (open) "later same-key callers wait forever on the leaked zero-permit semaphore" (a dropped RTCache::get() future skips cleanup of a coalescing lock).
prove: for every await point p in an async fn, dropping the future at p preserves the shared-state invariant (no published-but-uncompleted state, no lost completion event). Tool: Verus or Creusot on the async state machine with a generated "drop at each yield" obligation; Kani for bounded checks of the lowered state machine. Alternative: Iris-style invariants with an explicit drop-transition.
evidence:
- https://github.com/cloudflare/pingora/issues/932 "This can make a cache-served response appear complete after only a prefix of the upstream body."
- https://github.com/cloudflare/pingora/issues/933 "the durable in-memory state says the response stream is complete, while the external completion event that the subrequest pipe consumes was not published"
- https://github.com/hyperium/hyper/issues/4040 (closed) "it does **not** signal `pipe_task` in any way" (dropping the h2 response future leaves the request body pump and SendStream alive, so no RST_STREAM is sent)
- https://github.com/hyperium/hyper/issues/3906 (closed) h2 panic after future cancellation: "panicked at 'state=State { inner: Closed(ScheduledLibraryReset(CANCEL)) }'"
- https://github.com/tokio-rs/tokio/issues/8551 (closed) "Traditional-timer cancellation drops the stored waker under the timer-driver mutex."
- Nobody knows the contract: https://github.com/quinn-rs/quinn/issues/1763 "Presumably RecvStream::read` can be cancelled and retried without missing reads, but I'm not sure just from the docs." and https://github.com/hyperium/hyper/issues/4054 "I think Hyper is largely cancel safe:"
impact: every service built on these crates that uses timeout/select!/task abort (all of them); effects range from leaked locks and hung same-key requests to truncated cached responses being served as complete (data integrity), plus leaked connections.
why tests/fuzzing miss: the bug needs the drop to land at one specific await among many, in a specific state (e.g. channel full). Test and fuzz harnesses rarely cancel at every await; the library docs themselves do not state the contract (quinn 1763, hyper 4054). A proof quantifies over all drop points.
OPINION: strongest candidate for a paper; the novelty is a tool and proof method that makes cancellation a first-class transition for Rust async code, applied to a real proxy cache and h2 client.

=====================================================================
2. Peer-driven resource accounting: every queue and counter reachable by a peer is bounded, and counters equal the true contents
broken: https://rustsec.org/advisories/RUSTSEC-2026-0523.html (quinn-proto) "a peer can send one small MAX_STREAM_DATA frame naming a very large stream index, and `accept` then yields every stream up to that index."
prove: for all sequences of peer frames, memory held by the connection <= f(TransportConfig), and each counter (buffered bytes, queue length, stream count) equals the sum over the structure it summarizes. quinn-proto is sans-IO, so it is a pure state machine; tool: Verus (invariant + bounded-resource refinement), Kani for the arithmetic lemmas.
evidence:
- https://rustsec.org/advisories/RUSTSEC-2026-0342.html "A DATAGRAM frame with an empty payload was charged zero bytes, so it never triggered eviction and was appended to the queue, which has no other bound."
- https://rustsec.org/advisories/RUSTSEC-2026-0341.html (the fix for 0185 was bypassed) "However, the cap was only checked inside"
- https://rustsec.org/advisories/RUSTSEC-2026-0343.html "subtracted an evicted datagram's size from the buffered byte counter twice"
- https://rustsec.org/advisories/RUSTSEC-2026-0339.html (quinn: unbounded RETIRE_CONNECTION_ID queue) "The normal path bounds this queue and closes the connection with a CONNECTION_ID_LIMIT_ERROR if the bound would be exceeded."
- https://rustsec.org/advisories/RUSTSEC-2026-0258.html (h2) "accept and queue empty DATA frames without limit"; https://rustsec.org/advisories/RUSTSEC-2023-0034.html (h2) "the pending accept queue can grow in memory usage"; https://rustsec.org/advisories/RUSTSEC-2024-0003.html (h2) "force these resets to be queued in an unbounded fashion"
- https://rustsec.org/advisories/RUSTSEC-2026-0389.html (Pingora) "used the h2 crate's default HTTP/2 server limits, a 16 MiB decoded header-list size and no limit on concurrent streams"
impact: any QUIC or HTTP/2 server or client (all quinn, h2, hyper, tonic, Pingora users); remote unauthenticated OOM or CPU DoS. At least 10 advisories in these crates alone, several recurring in the same code (0185 -> 0341; 0339 and 0342 are normal-path-bounded, odd-path-unbounded).
why tests/fuzzing miss: the bound holds on the main path and fails on a rare path (already-retired CID, zero-length frame, gap-heavy fragments); fuzzers see memory growth only if they run long enough and measure it. "Every enqueue site is covered by a bound" is a whole-program property, which a proof checks and a test samples.
note: overlaps in spirit with the excluded "HTTP/2 flow-control credit deadlock" only through h2; this class is memory bounds and counter conservation, not deadlock.
OPINION: second strongest; the recurrence of "fix then bypass" (0185/0341) shows local fixes do not suffice.

=====================================================================
3. Panic- and overflow-freedom of sans-IO protocol cores on arbitrary wire bytes
broken: https://rustsec.org/advisories/RUSTSEC-2026-0037.html (quinn-proto) "Unfortunately the maintainers did not properly assess usage of `unwrap()` calls in the transport parameters parsing code"
prove: for all byte strings and all connection states, quinn-proto's receive path (parse + frame handlers + transmit builder) never panics and never overflows (checked arithmetic is total, Durations/Instants ordered). Tool: Kani/Verus on parsers and frame handlers; this needs invariants for state (e.g. min_ack_delay <= max).
evidence:
- https://rustsec.org/advisories/RUSTSEC-2023-0063.html "Unfortunately this is issue was not found by our fuzzing infrastructure."
- https://rustsec.org/advisories/RUSTSEC-2026-0340.html "the peer's transport parameters could cause `AckFrequencyState::candidate_max_ack_delay` to call `Duration::clamp` with a minimum greater"
- https://rustsec.org/advisories/RUSTSEC-2026-0524.html "which only a debug assertion checked" (client panics or exhausts memory on a long Retry token)
- https://rustsec.org/advisories/RUSTSEC-2024-0399.html (rustls) "A bug introduced in rustls 0.23.13 leads to a panic if the received TLS ClientHello is fragmented."
- https://rustsec.org/advisories/RUSTSEC-2026-0104.html (rustls-webpki) "This panic is reachable prior to a CRL's signature being verified."
- https://github.com/quinn-rs/quinn/issues/1818 "attempt to subtract with overflow" (flow-control credit growth); https://github.com/quinn-rs/quinn/issues/2885 "bytes_read overshoots, RecvState::stop underflows"
- https://github.com/aws/s2n-quic/issues/3107 "this will kill at least the entire s2n-quic endpoint" (one connection's panic takes down the whole endpoint)
impact: one malicious UDP packet or one handshake takes down a whole endpoint (all connections of all users), because panics in a shared endpoint task are not contained.
why tests/fuzzing miss: the advisories say so themselves (0063, 0037: "we did not have sufficient fuzzing coverage"). Panics depend on relational state (two peer-controlled values compared) and on debug-only assertions that behave differently in release builds.
OPINION: weakest of the set alone ("no panic" is arguably an engineering result); s2n-quic already runs Kani harnesses (https://github.com/aws/s2n-quic/blob/main/docs/dev-guide/kani.md "s2n-quic uses the [Kani Rust Verifier]"). It becomes paper-sized only if combined with 2 (one state-machine invariant proof giving both bounds and totality), or if framed as a proof of whole-receive-path totality at scale.

=====================================================================
4. Missed-wakeup and stuck-future liveness: every pending future is eventually woken or resolved
broken: https://github.com/aws/s2n-quic/issues/3382 (open) "Client::wait_idle() never returns when the client has zero connections." (shutdown signals are sent "in a way that registers no wake")
prove: wake obligation: whenever a task returns Pending, some enabled event will call its waker, or the state is terminal. Includes channel send/close races and reentrant wake under locks. Tool: TLA+/P model of the wake protocol for the channel+dispatcher; for Rust code, Iris/Trillium-style liveness or at least exhaustive model checking (loom/Shuttle) of the extracted protocol. Honest limit: full liveness proofs of Rust async code are research-hard.
evidence:
- https://github.com/hyperium/hyper/issues/4202 (closed) "No error is returned and the request is not retried." (hyper-util legacy client: a send racing a close between `inc_num_messages()` and `chan.send()` leaves the request pending forever)
- https://github.com/tokio-rs/tokio/issues/8555 (closed) "A callback that creates a child token from such an ancestor recursively takes its mutex and deadlocks."
- https://github.com/hyperium/h2/issues/975 (open) "Both stop reading, so neither can ever write." (control-frame write gates reads; close to the excluded flow-control class, so treat as borderline)
- https://github.com/cloudflare/pingora/issues/1028 (open) "a silent peer parks the connection forever"; https://github.com/cloudflare/pingora/issues/1031 "a never-reading client parks the stream forever" (waits with no deadline)
- https://github.com/hyperium/h2/issues/546 (closed) "there is a deadlock when tokio runtime is shutting down."
impact: hung requests that only the caller's own timeout ends; leaked sockets and tasks per failed connection (s2n-quic 3382); no error to alert on.
why tests/fuzzing miss: needs a specific interleaving (a preemption between two steps of a send) and absence of an event (hangs do not crash); test harnesses time out rather than diagnose.
OPINION: high impact, but proof effort is the highest here; likely best scoped to one mechanism (the tokio mpsc/oneshot + waker protocol used by hyper's dispatcher) with a TLA+ model validated against the code.

=====================================================================
5. Soundness of the safe API of async-runtime primitives under concurrency (data-race and lifetime freedom)
broken: https://rustsec.org/advisories/RUSTSEC-2026-0384.html (tokio 1.54.0 Interval) "can drop an internal timer entry without synchronizing with the driver thread that is firing it." (introduced by https://github.com/tokio-rs/tokio/pull/8458, a change to the timer; "the v1.54.0 release of Tokio has been yanked")
prove: tokio's sync/time/io primitives (oneshot, broadcast, timer wheel, AsyncFd registration) are data-race-free, memory-safe and linearizable under the C11/Rust memory model for every safe client. Tool: RustBelt/Iris-style semantic typing proof (as for std Arc/Mutex), supported by Loom and Miri on the same harness; extend to weak-memory.
evidence:
- https://rustsec.org/advisories/RUSTSEC-2021-0124.html "the two halves of the channel can concurrently access a shared memory location, resulting in a data race."
- https://rustsec.org/advisories/RUSTSEC-2025-0023.html "values that are `Send` but not `Sync` can trigger unsoundness"
- https://rustsec.org/advisories/RUSTSEC-2023-0005.html "`tokio::io::ReadHalf<T>::unsplit` can violate the `Pin` contract"
- https://rustsec.org/advisories/RUSTSEC-2026-0386.html "This violates I/O safety in two ways" (AsyncFd; https://github.com/tokio-rs/tokio/issues/8538)
- https://rustsec.org/advisories/RUSTSEC-2022-0022.html (hyper) "This is unsound, since `Header` contains references and thus must be non-null."
impact: every Rust async server; unsoundness in safe code means memory corruption without any `unsafe` in the user's code.
why tests/fuzzing miss: Miri/Loom check single or bounded schedules and need a test that exercises the exact racing pair; 0124 and 0384 are regressions that passed the existing suite. Type-system arguments (Send/Sync bounds) are the missed part, and only a semantic proof covers them.
OPINION: prior art is heavy (RustBelt, Loom); a paper needs a concrete new angle, such as proof-carrying performance changes (0384 came from an optimization). Risk of "not novel" is higher than for 1 and 2.

=====================================================================
6. TLS handshake state machine: nothing derived from unauthenticated or wrong-epoch input may affect security-relevant output
broken: https://rustsec.org/advisories/RUSTSEC-2026-0349.html (rustls) "The client recorded the server-selected key exchange group for each server name when processing the ServerHello, before the server was authenticated." (a network attacker downgrades later connections to classical key exchange)
prove: a noninterference/typestate theorem: (a) every message is accepted only in the epoch RFC 8446 allows, (b) persistent client state (session store, kx hints) is written only after authentication, (c) application data is released only in states where the peer is authorized for it. Tool: Verus or Kani-checked typestate encoding of rustls's state machine with refinement to a TLS 1.3 spec (e.g. mechanized in Tamarin/ProVerif for the protocol side); information-flow labels for secrets.
evidence:
- https://rustsec.org/advisories/RUSTSEC-2026-0285.html "a plaintext `EncryptedExtensions` message packed into the same record as the `ServerHello` was accepted." Also "This is functionally the same bug as Go's [GO-2026-4340]" (same bug in another implementation)
- https://rustsec.org/advisories/RUSTSEC-2026-0347.html "Plaintext meant for the inner server therefore goes to the client-facing server named by `public_name`."
- https://rustsec.org/advisories/RUSTSEC-2026-0346.html "The `Debug` implementations of `Tls12ClientSessionValue` and `Tls13ClientSessionValue` were derived, and so included the TLS 1.2 master secret or TLS 1.3 resumption PSK in their output."
- https://rustsec.org/advisories/RUSTSEC-2024-0336.html "If a `close_notify` alert is received during a handshake, `complete_io` does not terminate."
- https://rustsec.org/advisories/RUSTSEC-2026-0524.html (quinn) "A client kept the token from a Retry packet without any length limit" (unauthenticated peer data persisted into later packets)
impact: all rustls/tokio-rustls/quinn/Pingora TLS users; confidentiality loss (post-quantum downgrade, plaintext to the wrong server, secrets in logs). Handshake bugs are low-severity individually (attacker needs a network position), which is why they get missed.
why tests/fuzzing miss: these are spec-conformance violations that produce no crash and no wrong output on honest peers; interop tests only exercise honest peers, and fuzzers have no oracle for "should have rejected".
OPINION: good fit for proofs because the oracle is the RFC; risk is overlap with miTLS/HACL-style work. The new part would be doing it for idiomatic Rust (rustls) and covering ECH and PQ hybrids, which are exactly where 2026 bugs sit.

=====================================================================
7. X.509 path validation: the verifier accepts exactly what RFC 5280 allows (name constraints, CRL distribution points, revocation)
broken: https://rustsec.org/advisories/RUSTSEC-2026-0049.html (rustls-webpki) "If a certificate had more than one `distributionPoint`, then only the first `distributionPoint` would be considered against each CRL's `IssuingDistributionPoint` `distributionPoint`" (with UnknownStatusPolicy::Allow, revoked certificates are accepted)
prove: refinement: webpki's accept/reject decision equals a declarative RFC 5280 path-validation predicate (including name constraints incl. wildcards, CRL/IDP matching, distrust lists), for all DER inputs; parser totality included. Tool: Verus against a Lean/Dafny-style spec (recent Rust-verified-parser work as prior art to check, OPINION: needs a literature check before claiming novelty).
evidence:
- https://rustsec.org/advisories/RUSTSEC-2026-0098.html "Name constraints for URI names were ignored and therefore accepted."
- https://rustsec.org/advisories/RUSTSEC-2026-0099.html "Permitted subtree name constraints for DNS names were accepted for certificates asserting a wildcard name." and "This is very similar to [CVE-2025-61727]" (Go)
- https://rustsec.org/advisories/RUSTSEC-2026-0382.html "may accept certificate paths containing distrusted emSign intermediate public keys"
- https://rustsec.org/advisories/RUSTSEC-2026-0104.html "A panic was reachable when parsing certificate revocation lists" (before signature check)
impact: anyone relying on rustls for server or client authentication (mTLS meshes, Pingora upstream TLS, tonic TLS). Each bug needs CA misissuance, so the severity is limited, but name constraints and revocation exist precisely for that case.
why tests/fuzzing miss: differential fuzzers need a reference implementation with the same bug-compatible behavior (Go had the same wildcard bug); the combinatorics of extensions across a chain exceed handwritten vectors.
OPINION: four advisories in one crate within 2026 make this a class, but it is the most "crypto-library-shaped" of the set and may sit outside the network/distributed-systems focus the human prefers.

=====================================================================
8. Server lifecycle: accept loops never exit on recoverable errors, and graceful shutdown terminates without dropping accepted work
broken: https://rustsec.org/advisories/RUSTSEC-2024-0376.html (tonic) "there is a remote DoS attack that can cause the server to exit cleanly on accepting a tcp/tls stream." (a client with a wrong TLS config makes the accept error, and the accept loop exits; https://github.com/hyperium/tonic/issues/1897)
prove: TLA+/P model of the server lifecycle (accept loop, connection tasks, shutdown signal, GOAWAY/draining), with properties: (safety) every request accepted before shutdown completes or gets a retryable error; (liveness) shutdown terminates within a bound; accept errors are classified and never terminate the loop unless fatal. Then conformance-check the Rust (hyper graceful_shutdown, Pingora server) against the model, or prove it in Verus for the state machine.
evidence:
- https://github.com/tokio-rs/tokio/issues/3529 (closed) "Then once the `too  many open files` error  occur, it will never  stop." (the other half of accept handling: EMFILE spins)
- https://github.com/hyperium/hyper/issues/1422 (closed) "Once such an error occurs the Hyper client is "tainted" and cannot make a successful request anymore."
- https://github.com/cloudflare/pingora/issues/865 (closed) "after sending GOAWAY, Pingora stops reading from the H2 connection" (so queued in-flight streams are dropped)
- https://github.com/hyperium/hyper/issues/4170 (closed) "would never return and block for an hour or more after the shutdown_grpc_token CancellationToken was canceled." (a hyper graceful_shutdown behavior change broke tonic)
- https://github.com/cloudflare/pingora/issues/813 (closed) "Graceful shutdowns take roughly double the expected time per runtime."
- s2n-quic closing/draining (unconfirmed, see caveat): https://github.com/aws/s2n-quic/issues/3259 "enters `Draining` on a remote close or stateless reset, then immediately finalizes the connection with no close/drain timeout."
impact: every deployment doing rolling restarts or exposed to hostile or misconfigured clients: dropped in-flight requests (clients see 520s), hours-long hangs on deploy, a whole server silently exiting.
why tests/fuzzing miss: needs a fault in the environment (fd exhaustion, bad TLS peer) and a precise shutdown-time interleaving; each library tests its own part, while the property spans tokio listener, hyper, h2 and tonic (the 4170 regression was a cross-crate interaction).
OPINION: fits the "distributed" filter best and is the least checked by existing tools; the proof target (a model plus conformance of the code) is more modest than 1, 2 and 5.

=====================================================================
Ranking (OPINION): 1, 2, 8, 6, 4, 5, 7, 3 by fit with "class of recurring failures, proof matters, tool-feasible".

# part: storage

Storage/consensus candidates (read-only mining, 2026-11-13). Quotes are verbatim from fetched issue text. OPINION marks are mine.
Coverage gaps: Garage issue search returned nothing (deuxfleurs-org/garage); Materialize, Fluvio, foyer not mined in depth; RustSec listing showed no Raft/KV-store advisories (only h2/HTTP-type ones, already covered), so evidence is GitHub issues.

1. Raft membership change: leader/quorum invariants break at reconfiguration edges
broken: https://github.com/databendlabs/openraft/issues/2169 "A leader in neither its effective nor its committed membership still appends membership entries, and `change_membership` from a joint config can put it there itself (debug builds panic)"
prove: the Rust Engine (membership + leader handlers) refines an abstract Raft-with-joint-consensus spec, including the invariant "a node that acts as leader is in the effective config", plus safety under interrupted/re-targeted changes. Tool: Verus (openraft maintainers already started this, see #2245).
evidence:
- https://github.com/databendlabs/openraft/issues/2091 "A cluster can remain leaderless after all nodes and network connections recover if the old leader loses leadership before committing the final membership entry that removes it as a voter."
- https://github.com/databendlabs/openraft/issues/2178 "While `transfer_to` is set, the leader sends no heartbeats." (removed leader "stays Leader forever")
- https://github.com/tikv/raft-rs/issues/192 "Joint consensus may get stuck if either C<old> or C<new> could not reach a quorum after entering the begin-conf-change stage"
- https://github.com/restatedev/restate/issues/4463 "sealed loglet segments that reference the lost node in their nodeset cause continuous, unrecoverable repair attempts"
impact: anyone operating TiKV, Restate, Databend, other openraft users; stuck or leaderless clusters during node replacement, the exact moment operators are already under failure.
why tests/fuzzing miss it: bad states need an interrupted change plus a specific next leader plus a further change; #2091 says "A deterministic reproduction test has not been run" (found by inspection); #2178 needed a 130000-step deterministic fuzz run. Liveness has no assertion oracle other than a timeout.
OPINION: strongest candidate; reconfiguration is the part of Raft with the least settled proofs, and safety plus liveness-after-heal is a paper-sized claim.

2. Async command reordering: purge/snapshot/apply preconditions invalidated by interleaving
broken: https://github.com/databendlabs/openraft/issues/2116 "`get_log_id` returns `None` for a purged index and the `unwrap()` panics the RaftCore task. ... When this hits a quorum of nodes, the cluster loses quorum **permanently**"
prove: for the engine-to-runtime command queue, every deferred command's precondition (log id still present, responder still registered, snapshot flushed) holds when it runs under every legal reordering of snapshot, purge, apply and install. Tool: Verus on the Rust code with a command-queue model, or TLA+/P of the queue then refinement.
evidence:
- https://github.com/databendlabs/openraft/issues/2247 "RaftCore panics on stale client responders when apply runs before snapshot purge"
- https://github.com/databendlabs/openraft/issues/2248 "`RaftCore::apply_to_state_machine` panics when it applies the log above a snapshot while `PurgeLog` for that snapshot is still waiting for `snapshot.flushed()`."
- https://github.com/databendlabs/openraft/issues/1761 "During a `cluster_netem_delay` fault on node 3, two Raft groups on that node permanently stopped making progress."
- https://github.com/databendlabs/openraft/issues/2183 "a late local snapshot upload can overwrite `current_snapshot` after a newer snapshot has been installed from the leader."
impact: openraft users; one panic is permanent loss of that replica, a quorum of them is permanent unavailability. Four fixes in a row (#2116, #1761, #2247, #2248) hit the same shape, which is the class evidence.
why tests/fuzzing miss it: needs a specific interleaving of async workers; #2247 had to "pause the state-machine worker to control the ordering".
OPINION: class is real but tied to one codebase; the paper is a reusable method for verifying async deferred-command designs, not openraft alone.

3. Message-construction invariants in Raft implementations (what is acknowledged/committed vs what was sent)
broken: https://github.com/tikv/raft-rs/issues/599 "The follower acknowledges an index it never stored, the leader records a phantom `Progress::matched`, and that value is later used to compute the committed index."
prove: the code that builds AppendEntries (entries, prev index, leader_commit) satisfies the preconditions of the abstract Raft follower rule, so no follower can accept a commit or ack beyond what it holds. Tool: Verus refinement of request builder and follower handler against abstract Raft spec.
evidence:
- https://github.com/databendlabs/openraft/issues/2245 "A follower that has not seen the intermediate terms accepts the request, commits the old term's entry and applies it, although the cluster has overwritten that entry. Two different entries are applied at one index." (found by Verus, per the issue)
- https://github.com/databendlabs/openraft/issues/2117 "the receiver rejects the vote but never adopts the candidate's higher term and never steps down."
- https://github.com/tikv/raft-rs/issues/570 "Historical entries (existing before learner joined) are persisted via `take_entries()` but skipped in `take_committed_entries()`"
- https://github.com/tikv/raft-rs/issues/349 "Unexpected FinalizeMembershipChange entries in commited entries after finalize" (title only)
impact: a safety violation (two entries applied at one index) in the consensus core under TiKV/TiDB-class deployments; learners silently missing state.
why tests/fuzzing miss it: #2245 needs "two elections" to occur while a worker is descheduled between two reads; #599 needs batching on plus a pending empty append.
OPINION: overlaps candidate 1 in tool; keep separate only if the story is "optimisations (batching, pipelining) break Raft refinement". Weaker alone.

4. MVCC transactions with GC, async commit, CDC and stale reads: timestamp-ordering invariants
broken: https://github.com/tikv/tikv/issues/20228 "A commits. Prewrite finds no write on k with a commit ts above S, so it reports no write conflict, and A recreates k with its stale value."
prove: snapshot-isolation (no lost update, no resurrection) of the Percolator-style prewrite/commit/GC/resolved-ts protocol, with GC safe point, async commit min_commit_ts, stale reads and CDC as concurrent actors. Tool: TLA+ model (TiKV #10319 already scoped a GSoC async-commit spec) plus Verus/Kani on the key checks in the Rust MVCC layer.
evidence:
- https://github.com/tikv/tikv/issues/11187 "After a pessimistic transaction is committed, a non-pessimistic lock of the same transaction can be also prewritten successfully." (breaks CDC assumption, TiKV panics)
- https://github.com/tikv/tikv/issues/15420 Jepsen run on dynamic regions: ":workload {:cycle {:valid? false" (monotonic pessimistic test found transaction cycles)
- https://github.com/tikv/tikv/issues/18706 "support async commit with stale reads" (title; shows feature-pair not yet covered)
- https://github.com/tikv/tikv/issues/10319 "GSoC: TLA+ Specification for Async Commit" (title; prior spec exists, scope limited to async commit)
impact: TiDB/TiKV users get silent data corruption (resurrected rows, cycles) or CDC panics.
why tests/fuzzing miss it: bug needs a transaction open longer than the GC wait time (#20228) or a feature combination; Jepsen finds only what its workload touches.
OPINION: highest impact, but TiKV is a large target and the spec exists partially; the novelty claim must be "features composed", not "TiKV protocol".

5. Async-Rust locks and queues held across awaits: liveness deadlocks
broken: https://github.com/neondatabase/neon/issues/12875 "Because Tokio's RwLock enforces a strict writer-priority (fair) queue, holding a read lock during slow WAL transmission creates a trap: ... all subsequent read requests (metrics collection, other WAL senders, state queries) will be permanently queued behind the pending writer."
prove: a deadlock-freedom (more precisely: bounded-wait) theorem for a Rust async program's lock discipline, i.e. no guard of lock L is live across an await that can transitively wait on a writer of L. Tool: a static checker with a proof of soundness (OPINION: Iris-style or Verus model of Tokio RwLock fairness plus a MIR-level lint), not testing.
evidence:
- https://github.com/neondatabase/neon/issues/12876 "holds the `RwLockReadGuard<SharedState>` across **unbounded disk I/O operations**"
- https://github.com/risingwavelabs/risingwave/issues/27921 "Schema replacement holds the reschedule write lock across catalog and barrier" (title)
- https://github.com/risingwavelabs/risingwave/issues/27916 "Reschedule write lock blocks DDL readers across meta and barrier waits" (title)
- https://github.com/risingwavelabs/risingwave/issues/27373 "A decoupled sink shares one pause state between its KV log-store writer and its KV log-store reader, and the two halves run in the same actor task."
impact: Neon safekeepers (WAL path, so every Postgres compute), RisingWave meta; whole-service stalls with no crash or log.
why tests/fuzzing miss it: only slow I/O plus a pending writer triggers it; fair-RwLock behaviour is invisible in tests with fast disks. Loom-style checking does not model real I/O latency.
OPINION: weakest on "needs proof" (a lint may suffice) and the Neon issues read like automated reports; maybe fold into 8.

6. Error-path and lifecycle leaks of protocol state (holds, timers, reused ids)
broken: https://github.com/restatedev/restate/issues/5425 "When the old timer fires, Restate appends a `Notification: Sleep` with the old run's completion id to the **new** run's journal."
prove: for a durable-execution runtime, every piece of derived state (timers, holds, journal entries) is scoped to an invocation incarnation, and purge/kill/failure removes it, so stale effects cannot reach a later incarnation with the same id. Tool: Verus or TLA+ refinement of the state machine with incarnation ids; Kani for the early-return release pattern.
evidence:
- https://github.com/neondatabase/neon/issues/12957 "If the guard acquisition fails ... `start_snapshot` returns through `?` before any `SnapshotContext` exists. The hold stays set on the live timeline." (WAL removal disabled forever)
- https://github.com/restatedev/restate/issues/5462 "verify the expected state survives, without lost mutations or stale changes applied later" (test plan for failover; the release notes it cites mention an inconsistent-state-mutation cleanup)
- https://github.com/restatedev/restate/issues/5239 "Harden orphaned journal completion-index cleanup" (title)
- https://github.com/restatedev/restate/issues/5374 "Invoker inactivity timeout fires during a ProposeRunCompletion round-trip, causing spurious suspend/replay"
impact: Restate users: wrong sleep wake times or permanently failing retries (RT0007); Neon: unbounded local WAL growth then disk-limit outages.
why tests/fuzzing miss it: requires purge/kill followed by re-run of the same key (id derived from key) or a timeout at the exact await; the happy path is clean.
OPINION: the class (stale effect crosses identity reuse) is general, but proofs here are mostly "ordinary invariant", so the theorem must be about exactly-once semantics of durable execution to be paper-sized.

7. Crash recovery of embedded storage engines under write reordering
broken: https://github.com/spacejam/sled/issues/1533 "A Sled database (version `0.34`) enters a corrupt state and cannot be opened after the Docker container using it was abruptly stopped."
prove: recovery after any crash point, with any reordering of writes between fsyncs, yields a state equal to some prefix of acknowledged operations (or opens successfully). Tool: Verus or Iris-style crash-refinement over a file-system model (as in Perennial/GoJournal), applied to a Rust storage engine's recovery path.
evidence:
- https://github.com/spacejam/sled/issues/1527 "corrupt snapshot file found, crc does not match expected" (deleting `snap.YYY.generating` opens the DB, reporter asks if that "breaks some invariant")
- https://github.com/spacejam/sled/issues/1077 "alice ... found bugs in every system it targeted." (maintainer proposes an ALICE-like write permuter)
- https://github.com/databendlabs/openraft/issues/2290 "Add a persistent archive-backed rkyv log store example with restart/recovery tests" (title; shows Raft log stores are rebuilt by each user and need recovery proofs)
- https://github.com/tikv/raft-rs/issues/314 "re-joining after simulated node crash panics on trying to re-add an already existing node."
impact: any app embedding sled; any Raft user writing their own log store, where a lost fsync order breaks Raft's persistence assumption.
why tests/fuzzing miss it: crash states are exponential in write reorderings; a handful of kill -9 tests cover almost none.
OPINION: weaker evidence than 1-4 (sled is largely unmaintained, issues are old); not cross-project in the strict sense. Would improve if a Raft-storage-trait contract proof is the target.

8. Failure isolation in barrier/epoch-based streaming: one stuck component blocks unrelated progress
broken: https://github.com/risingwavelabs/risingwave/issues/27837 "why does a decoupled sink's inability to make external progress become a prerequisite for unrelated tables to checkpoint"
prove: in the barrier protocol, the set of jobs whose checkpoint can be blocked by a failure is bounded by the failed job's dependency closure; plus eventual checkpoint for all unaffected jobs. Tool: TLA+/P model of barrier injection, collection and DDL-triggered mutations, then model checking of the Rust meta barrier manager.
evidence:
- https://github.com/risingwavelabs/risingwave/issues/27373 "a paused decoupled sink deadlocks its schema-change barrier" (title)
- https://github.com/risingwavelabs/risingwave/issues/27949 "sink: whole-epoch buffering with O(n²) ChangeBuffer compaction blocks barriers for hours, and recovery cannot abort the actor" (title)
- https://github.com/risingwavelabs/risingwave/issues/27891 "mass actor rebuild trips h2 reset limit on exchange connection, unrelated actors fail with too_many_internal_resets" (title)
- https://github.com/restatedev/restate/issues/4463 "continuous, unrecoverable repair attempts" (permanent failure of one node leaks into whole-cluster load)
impact: RisingWave production users (the 27837 reporter cites "A production incident"); outage scope grows beyond the failed component.
why tests/fuzzing miss it: needs a failing external system plus a concurrent DDL barrier; chaos tests rarely combine them.
OPINION: good fit for P/TLA+ but the property (isolation) is underspecified in the system today; part of the work would be stating it. Risk that it reads as one system's design bug.

# part: client

# VL candidate directions mined from client-side Rust projects (read-only; nothing posted)

Quotes are verbatim from issue or advisory text fetched with gh on 2026-11-13. Statements marked OPINION are mine. Impact and "why tests miss it" are OPINION unless a quote supports them.

## 1. Complete mediation of capability checks in a permissioned runtime

broken: Deno `node:sqlite` reaches files without the file permission check, https://github.com/denoland/deno/security/advisories/GHSA-8vxj-4cph-c596 : "It is possible to bypass Deno's read/write permission checks by using `ATTACH DATABASE` statement."
prove: every code path from a JS-visible API to an OS resource (file, network, env, subprocess) is dominated by a permission check whose argument equals the resource actually touched (complete mediation). Tool: encode each host op as a Rust function with a typestate/ghost "permission token" and verify in Verus that no resource-touching call is reachable without the token; the sink set is an explicit allowlist of syscall wrappers.
evidence:
- https://github.com/denoland/deno/security/advisories/GHSA-4c8g-jvcx-v4hv : "`process.loadEnvFile()` (the Node-compatible API for loading variables from a `.env` file) does **not** honor this. It only checks that the program has **read** permission for the dotenv file"
- https://github.com/denoland/deno/security/advisories/GHSA-qq26-84mh-26j9 : "`Deno.FsFile.prototype.stat` and `Deno.FsFile.prototype.statSync` are not limited by the permission model check `--deny-read=./`."
- https://github.com/denoland/deno/security/advisories/GHSA-vc52-gwm3-8v2f : "Outbound HTTP requests made using the built-in "node:http" or "node:https" modules are incorrectly not checked against the network permission allow list (`--allow-net`)."
- https://github.com/denoland/deno/security/advisories/GHSA-xpwj-7v8q-mcgj : "Modules that are dynamically imported through `import()` or `new Worker` might have been able to bypass network and file system permission checks when statically importing other modules."
- Also in the same project: GHSA-7w8p-chxq-2789 "Deno.env.toObject() ignores the variables listed in --deny-env and returns all environment variables".
impact: anyone running untrusted dependencies under `--allow-*`/`--deny-*` flags; the flags are the only security promise of the runtime. About 40 published Deno advisories (gh api repos/denoland/deno/security-advisories); by title, roughly half are permission or sandbox bypasses (OPINION on the count).
why tests/fuzzing miss it: a missing check is the absence of code; fuzzers need an oracle for "this call should have been denied", and each new Node-compat API (hundreds) is a new unchecked path. Tests only cover APIs someone thought to test. OPINION: a proof over the call graph catches the next new API at compile time, which is the research value.

## 2. Path and address confinement: the name checked equals the resource used

broken: Wasmtime filesystem sandbox escape via trailing slashes, https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-m9f7-9w4p-gv38 : "Guests provided write-access to any directory within their sandbox could move any directory on the filesystem the host process could access into their sandbox, and then read and write its contents. This bug is a full filesystem sandbox escape for guests."
prove: for the path-resolution function `resolve(root, p)` (including normalization, symlink, trailing-slash, case and Unicode folding rules of the OS), the resulting handle is beneath `root` for every input `p`, and the string compared by the policy is the same one resolved by the OS. Tool: Verus or Kani on a Rust model of the resolver, with an abstract filesystem (directories, symlinks, name-equivalence relation) as the specification; or Iris-style refinement for the cap-std layer.
evidence:
- https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-vqjp-4c8c-hfgg : "Wasmtime's filesystem sandboxing is primarily provided by the cap-std family of crates. This dependency had a vulnerability, [GHSA-hp8f-xmx4-4qrg] ... which meant that when dealing with symlinks a trailing slash could be used in specific circumstances to escape the filesystem sandbox."
- https://github.com/denoland/deno/security/advisories/GHSA-8xpq-cjcf-3wh9 (Unicode): "On macOS, that comparison was done at the raw-byte level while the APFS filesystem treats different Unicode spellings of the same name as the same file."
- https://github.com/denoland/deno/security/advisories/GHSA-968w-xfqw-vp9q : "the module resolver did not validate that a package's resolved entrypoint stayed within its `node_modules/<pkg>/` directory."
- https://github.com/denoland/deno/security/advisories/GHSA-hrqr-jv8w-v9jh : "The permission check would prompt for the base directory of the API, but the final file that was created would be outside of this directory"
- Network analogue, https://github.com/denoland/deno/security/advisories/GHSA-v8fw-85r8-5m23 : "the Node.js compatibility TCP path checked the permission against the **original hostname string** before resolution and then did not re-check after resolution."
impact: hosts of untrusted guests/plugins (Wasmtime embedders, Deno users); full read/write of host filesystem in the worst case.
why tests/fuzzing miss it: bugs need a specific interaction of path spelling, symlink layout and OS semantics (the cap-std bug is avoided on Linux >= 5.6 by `openat2`, so Linux CI does not see it). The equivalence relation of names is OS-specific, so a differential test needs the exact OS and filesystem. A model with an explicit name-equivalence relation makes the OS dependence part of the theorem.

## 3. Resource accounting completeness: every guest-triggered host cost is charged to a limit

broken: Wasmtime fuel dropped on some call paths, https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-m63x-6p34-q65x : "can drop any accumulated fuel usage within the callee, resetting to the fuel-remaining before the call. This can lead to exponential fuel amplification, that is, a guest that can run for exponential time using linear fuel"
prove: define cost(guest step) = host work + host memory; prove that for every host/compiled path, total cost <= a function of (fuel consumed + bytes charged to ResourceLimiter), i.e. no uncharged work or allocation. Tool: Verus specification of the metering counter as a ghost monotone resource ("fuel is a linear resource, never reset"); for the allocation side, a Kani/Verus proof that each allocation site takes a limiter token.
evidence:
- https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-j366-h8gg-77pm : "causes the host to do perform work which is `O(n)` in the number of subscriptions passed without consuming fuel or checking if fuel has run out."
- https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-q554-3cjc-rx7p : "Allocation is bounded only by a per-table cap and is charged to no `ResourceLimiter` or `StoreLimits`"
- https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-6fr9-xmw9-5352 : "Wasmtime still allocated host memory to track this borrow. This memory allocation wasn't accounted for anywhere and guests could make this memory grow arbitrarily large."
- https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-x84v-gj2h-g759 : "the host would unconditionally copy all of the bytes that a guest offered to the host and then buffer them up for processing."
- https://github.com/bytecodealliance/wasmtime/issues/14047 : "bulk operations (e.g. `memory.copy`) were updated to chunk the operation internally when fuel/epochs were enabled with preemption checks in the middle ... This was later discovered to be the source of a number of possible security vulnerabilities with epoch callbacks"
impact: multi-tenant hosts of Wasm (edge/serverless, plugin systems) rely on fuel/limits for isolation of CPU and memory.
why tests/fuzzing miss it: the property is a global inequality over all executions; a fuzzer sees only one run and a timeout is the only signal (issue 11427 "Huge array allocations are timing out during fuzzing" shows timeouts are noise). Each new component-model feature adds a new unmetered path, as the repeated advisory titles show.

## 4. Bounded stack depth for recursive processing of untrusted input

broken: Kanidm SCIM filter parser, https://github.com/kanidm/kanidm/security/advisories/GHSA-2pm5-6m23-h692 : "A depth limit (`SCIM_FILTER_MAX_DEPTH = 128`) was added on 2026-04-30, but it is applied only after each nested rule has already been entered, so it bounds the accepted tree depth, not the recursion depth ... a Rust stack overflow is an uncatchable abort, so the whole `kanidmd` process dies."
prove: for every function reachable from a network entry point, native stack use <= S for all inputs of length n, with S independent of nesting (or a static bound with an explicit depth check before descent). Tool: Verus with a ghost "stack budget" decreasing at each call, plus a call-graph analysis (cargo-call-stack style) for recursion through dependencies; the depth guard is proven to precede the recursive call.
evidence:
- https://github.com/kanidm/kanidm/security/advisories/GHSA-qcrp-p3rq-pffr : "`LdapCodec` from `ldap3_proto` 0.7.1 delegates structural parsing to `lber` 0.4.2, whose recursive-descent decoder has no nesting-depth bound."
- https://github.com/kanidm/kanidm/security/advisories/GHSA-r5fr-9gmv-jggh : title "Unauthenticated process abort via SCIM filter stack exhaustion"
- https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-wjc8-633q-pwxr : "The dropping logic was originally protected against this guest-controlled recursion by converting it into an iterative loop, but recursion was accidentally introduced in Wasmtime 42.0.0."
- the first kanidm fix was incomplete, per the advisory text above ("The BER wire path stays unbounded on 0.7.1, so the fix does not cover LDAP-protocol input.") in GHSA-qcrp-p3rq-pffr.
impact: unauthenticated remote crash of an identity server (Kanidm) or a Wasm host; Rust stack overflow aborts the process so no catch_unwind recovery.
why tests/fuzzing miss it: stack limit depends on frame size, optimization level and thread stack size (the advisory notes the "default 2 MiB tokio worker stack"); fuzzers rarely generate thousands of nested parentheses, and a regression (Wasmtime 42.0.0) reintroduces recursion silently. OPINION: a depth-before-descent proof is what the incomplete fixes lacked.

## 5. Totality and failure-atomicity of applying untrusted updates (not convergence)

broken: Yrs applies a decodable but malformed update and panics, https://github.com/y-crdt/y-crdt/issues/733 : "`Update::decode_v1` accepts a crafted update without error, but applying that update with `TransactionMut::apply_update` panics with `mid > len` inside `ItemContent::splice`."
prove: (a) totality: `apply(doc, bytes)` never panics or aborts; (b) failure atomicity: if it returns Err, the document is observationally unchanged (equal state, no poisoned lock, no observer fired). Convergence is assumed and out of scope. Tool: Verus/Kani with the document invariant (well-formed block store) as a loop/data-structure invariant; Kani harnesses on decode+integrate with bounded sizes for the bug-finding stage, Verus for the unbounded proof.
evidence:
- https://github.com/loro-dev/loro/issues/1254 : "After the panic, the document's internal mutex is still held, so every later write or import on that document throws `RuntimeError: unreachable`."
- https://github.com/loro-dev/loro/issues/1118 : "If the doc is dropped while that first panic is unwinding ... the second panic happens during cleanup and the process aborts."
- https://github.com/loro-dev/loro/issues/1068 : "Importing a remote update whose dependencies were folded into a shallow snapshot panics inside `OpLog` instead of returning `Err`. The panic then poisons the document's internal mutex"
- https://github.com/y-crdt/y-crdt/issues/764 : "`impl Drop for TransactionMut` calls `self.commit()` unconditionally. When a panic unwinds through a transaction ... the store may hold a change half made."
- https://github.com/y-crdt/y-crdt/issues/688 : "A Rust panic cannot unwind across an `extern "C"` boundary, so any panic reached from a yffi entry point terminates the host process"
- https://github.com/y-crdt/y-crdt/issues/758 : "v2 encoding of a doc with a same-client clock gap is undecodable"
- Cross-project: Wasmtime has the same pattern, e.g. GHSA-hmwq-g22x-qjw5 "Panic when pending calls are run after a trap" and GHSA-3r89-v5mq-j5xf "Host panic when component `call_async` is cancelled under some conditions"; Iroh GHSA-jx4g-cg2x-jc35 "Deserializing a crafted CustomAddr can set an out-of-bounds inline length, causing a panic".
impact: any collaborative-editing server or app (Yrs/Loro embedders, Swift/JS bindings) where one peer can crash or brick a shared document for everyone; persisted half-applied updates can reach other peers (Yrs 764).
why tests/fuzzing miss it: fuzzers do find the first panic, but the issues show the class keeps reappearing in new code paths (Loro 1068 "still reproduces on `main` ... the panic just moved"); the atomicity property after an Err needs a state-equality oracle and an invariant over the whole store, which fuzzers lack.

## 6. Deadlock freedom of lock / channel / actor wait graphs with callbacks

broken: Matrix Rust SDK holds a lock while calling user code that needs the same lock, https://github.com/matrix-org/matrix-rust-sdk/issues/5091 : "`process_and_take_response()` calls all the `sync_response_handlers` while the `sync_lock` is still in scope. I've registered an AccountDataEvent Handler, which calls room.members(), if members are not synced, we end up in `receive_all_members()` which also takes the `sync_lock`, ending up in a deadlock"
prove: the wait-for graph over locks, bounded channels and actor inboxes (including user callbacks, modeled as arbitrary code that may call any public API) is acyclic, hence no deadlock; plus no blocking send inside an actor loop without a bounded-wait. Tool: extract a lock/channel model from the Rust code (await points, guard scopes, channel capacities) and model check in TLA+ or P with the callback as a nondeterministic environment; stronger variant, a Verus/Iris lock-ordering ghost-state proof ("callbacks run with no locks held").
evidence:
- https://github.com/matrix-org/matrix-rust-sdk/issues/6669 : "every callback is dispatched while the read guard is still held ... The only way to detach a delegate is to call `set_delegate(None)`, which also requires the write guard"
- https://github.com/matrix-org/matrix-rust-sdk/issues/6524 : "something leaks a `LockedRoomEventCacheState` write lock, making it impossible for other parts of the SDK to read this data, and blocking the whole timeline-related logic for a particular room"
- https://github.com/n0-computer/iroh/issues/2345 : "If there are more items than the RPC layer will buffer a call to any `iroh.docs` RPC method *while consuming the stream* will deadlock."
- https://github.com/n0-computer/iroh/issues/4511 : "`RemoteStateActor::handle_message` awaits `State::handle_msg_send_datagram` inside its inbox loop. When the Relay queue is full, `RelaySender` waits for capacity ... There is no timeout around this wait."
- https://github.com/servo/servo/issues/41017 : "One principle of IPC communication is that a send can block if the buffer is full, and so to avoid deadlock the receiver should always be ready to receive"
- https://github.com/servo/servo/issues/22921 : "WebGL channels dynamically switch between using ipc and using mpsc. Unfortunately, these have different behaviour: `send` is blocking in ipc, but not in mpsc, which can result in deadlock"
- https://github.com/denoland/deno/issues/36417 : "`deno bundle` silently deadlocks with its esbuild service under CPU starvation (both at 0% CPU forever)"
impact: users see frozen chat timelines (Element X), hung browsers or IDB (Servo), stalled P2P endpoints (Iroh), hung CLI (Deno). These are in 5 of the 9 target projects.
why tests/fuzzing miss it: deadlocks need a specific interleaving plus buffer-full state; Matrix says of one "usually quite hard to reproduce" (issue 6524), and a Matrix issue is titled "Tests randomly get stuck" (issue 436). Callbacks are written by third parties, so the environment cannot be tested exhaustively. Note: this is scoped to a single process and its channels; it does not repeat the already-covered HTTP/2 credit deadlock.

## 7. Authenticity binding in an end-to-end encrypted client: every identity field is checked at every layer

broken: Matrix Rust SDK does not bind the sender in a to-device message, https://github.com/matrix-org/matrix-rust-sdk/security/advisories/GHSA-wfq4-36m3-9g42 : "The `matrix-sdk-crypto` crate before 0.16.1 is missing a check for the sender's user ID when decrypting an Olm-encrypted to-device message containing the `sender_device_keys` property. This could be exploited to spoof the sender of an encrypted to-device message, but only if the attacker colludes with (or is) the homeserver operator."
prove: a refinement from the Rust decrypt/validate pipeline to a protocol model: any event displayed with sender U and room R was encrypted by a device belonging to U in session bound to R, assuming a malicious homeserver (Dolev-Yao on the server channel). Tool: Tamarin or ProVerif for the protocol model, plus a Verus/Kani proof that each validation function checks exactly the fields the model requires (sender, room_id, session_id, device, encryption flag).
evidence:
- https://github.com/matrix-org/matrix-rust-sdk/security/advisories/GHSA-x958-rvg6-956w : "does not correctly validate the sender of an encrypted event. Accordingly, a malicious homeserver operator can modify events served to clients, making those events appear to the recipient as if they were sent by another user."
- https://github.com/matrix-org/matrix-rust-sdk/security/advisories/GHSA-h97m-27fx-42rx : "when replacing an encrypted event, the replacement event itself is not required to be encrypted."
- https://github.com/matrix-org/matrix-rust-sdk/security/advisories/GHSA-vp68-2wrm-69qm : "it doesn't check that the device that responded matches the device the key was requested from."
- https://github.com/matrix-org/matrix-rust-sdk/security/advisories/GHSA-4qg4-cvh2-crgg : title "`UserIdentity::is_verified` not checking verification status of own user identity while performing the check"
- Outside E2EE, same shape in Kanidm: https://github.com/kanidm/kanidm/security/advisories/GHSA-x8cg-3c8h-gw55 title "Oauth2 trust login provider subject not validated".
- Race variant that threatens the key-sharing invariant: https://github.com/matrix-org/matrix-rust-sdk/issues/3529 : "The SDK is _supposed_ to hit `/members` prior to sending encrypted events to ensure they have an up-to-date member list."
impact: users who rely on E2EE against an untrusted homeserver (the stated threat model; the advisories name "malicious homeserver operator" as the attacker). The Matrix advisory rates "CVSS score is 4.9 ... but we consider this a High Severity security issue".
why tests/fuzzing miss it: each bug is a missing equality check on one field; the code works for all honest inputs, so only an adversarial-server oracle reveals it. Protocol tools verify the spec but not the Rust; the gap between spec and code is the contribution. OPINION: the spec-to-code gap is the most paper-worthy part, since all three SDK advisories are "spec says check X, code did not".

## 8. Cross-process lease/lock safety for shared local state (distributed protocol on one machine)

broken: Matrix Rust SDK's cross-process lock, https://github.com/matrix-org/matrix-rust-sdk/issues/3313 : "We have a lock whose job it is to prevent both the main process and the NSE (notifications) process on Element X from using the OlmAccount at the same time ... However, we have evidence that it doesn't actually work."
prove: mutual exclusion plus staleness detection for a lease-based lock with a generation counter over a shared store (SQLite/files) with process suspension and clock jumps: no process acts on cached state after another process's generation increased; state-machine refinement of the Rust lock implementation. Tool: TLA+ (or P) model with process pause and lease expiry as environment actions, then model check or Verus proof of the lock's Rust code against it. Fencing tokens are the standard fix, so the theorem is that every store write carries and checks the generation.
evidence:
- https://github.com/matrix-org/matrix-rust-sdk/issues/6681 : "The `CrossProcessLock` has been introduced to deal with the following problem: a process $P_1$ uses the SDK, starts syncing, starts updating data here and there; process $P_1$ is suspended; a process $P_2$ starts and does similar things ... then later, process $P_1$ is resumed, and keeps going. there is a problem now: $P_1$ is not aware that the data has changed: it can be dramatic!" (the issue is titled "[meta] Adopt a new cross-process state invalidation strategy")
- https://github.com/matrix-org/matrix-rust-sdk/issues/6366 : title "iOS: `0xdead10cc` crashes — SQLite WAL locks held by tokio blocking threads during background suspension"
- https://github.com/matrix-org/matrix-rust-sdk/issues/2667 : "Race condition when sharing secrets to a new session" (title)
- https://github.com/denoland/deno/issues/36943 : title "Cross-process locking for DENO_DIR and build outputs (Cargo-style cache locks)"
- https://github.com/matrix-org/matrix-rust-sdk/issues/1041 : title "Joining and leaving room might be racy with data loss"
impact: mobile Matrix users lose messages (UTDs, unreadable encrypted events) or crash when the OS suspends one process; Deno users on shared caches.
why tests/fuzzing miss it: the failure needs an OS-controlled suspension between two instructions; the 3313 reporter had to find it in a rageshake log from production. Model checking explores suspension at every point. OPINION: this is the one candidate where the existing implementation had no spec at all, so the spec itself is a contribution; risk is that it overlaps with prior lease/fencing-token verification (Paxos-lease style) and novelty must be checked.
