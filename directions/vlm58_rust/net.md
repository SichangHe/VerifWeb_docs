# Rust networking infrastructure: candidates
(authored by agents unless marked 🧑)

Scope: tokio, hyper/h2, rustls, quinn, Pingora, hickory-dns. Reused (not redone): vlm48_dirs/a.md (bug quotes, marked [a.md]). Newly fetched by me: crates.io numbers, Lion paper text, hickory advisories, Cloudflare/ntpd-rs deployment.
Not picked: boringtun (crates.io total 2,183,180; small user base, no recurring class found), ntpd-rs (deployment real but I found no bug class; skip), linkerd2-proxy (GitHub issues disabled [a.md]).

## Shared numbers (FACT, crates.io API, fetched 2026-11-19, field `downloads` / `recent_downloads`)
- tokio 1,217,868,688 total / 319,428,763 recent
- hyper 1,152,572,752 / 296,669,060
- rustls 1,146,097,535 / 295,390,268
- h2 996,640,567 / 236,301,059
- quinn-proto 443,700,501 / 165,042,606; quinn 433,555,445 / 161,768,981
- hickory-proto 108,647,463 / 36,921,545
- Cloudflare (https://x.com/cloudflare/status/1570034885590654977): "a new HTTP proxy we've built in-house using Rust that serves over 1 trillion requests a day". FL2 is a separate Rust proxy (Oxy-based), blog "Cloudflare just got faster and more secure, powered by Rust": "We built FL2 in Rust, on Oxy".
- Let's Encrypt runs ntpd-rs (https://letsencrypt.org/2024/06/24/ntpd-rs-deployment); Ubuntu plans it as default (secondary: lobste.rs, Mar 2026).

## Ranking (OPINION): 1 > 2 > 3 > 4

## 1. Verified multi-threaded (work-stealing) async runtime core
What the advisors mentioned is real future work, and the single-thread part is already taken.
Closest prior work (FACT): Lion, SOSP'26, Zhou, Zhang, Chowdhury, Mu (Stony Brook), https://coladog.github.io/assets/lion-sosp26.pdf. Abstract: "We demonstrate this framework via Lion, a Tokio-compatible runtime in Rust verified using Verus." Limit, verbatim: "Lion's verified core is single-threaded: one executor, one reactor, and one event loop per thread." and "Extending the verification to cover cross-thread work-stealing, where tasks migrate between cores and shared queues require concurrent reasoning, is a challenging direction for future work." Also a follow-up arXiv 2610.09198 "Modular Responsiveness Verification of Rust Async Runtimes" (contents not read; must check).
New vs Lion (INFERENCE): work-stealing queues, cross-thread wakeups, shared timer wheel/reactor.
Users: tokio numbers above. Every Rust server (hyper, Pingora, tonic) sits on it.
Failure class: lost wakeup / timer never fires / unsound sync primitive.
- Lion paper on Tokio #5020: "the notification was suppressed when the task's timer later woke it, and the task remained queued indefinitely with no executor aware of it." Fix "required 18 commits and 38 review comments over 26 days".
- Tokio #3069: "registration succeeds with no error indication, yet the callback is never delivered." Same paper also says "Tokio has 9 more confirmed liveness bugs similar to these two."
- https://rustsec.org/advisories/RUSTSEC-2026-0384.html [a.md] "can drop an internal timer entry without synchronizing with the driver thread that is firing it." (tokio 1.54.0 yanked)
- https://rustsec.org/advisories/RUSTSEC-2021-0124.html [a.md] "the two halves of the channel can concurrently access a shared memory location, resulting in a data race."
Caution (FACT, Lion): "the majority of the confirmed liveness bugs in Tokio occur in single-threaded scheduling logic, not in multi-threaded synchronization." So the multi-threaded extension covers the minority class of observed bugs, and the 0124/0384 safety bugs. OPINION: the real risk is that the extension is "just" weak-memory concurrency proof work with a small bug payoff; the pitch must lean on tokio being the default production runtime.
Theorem (proposed): under assumption that the reactor delivers each registered event, for all schedules of N workers with stealing, every task whose waker is invoked is polled within bounded steps; plus data-race freedom for the queue/timer/waker structures.
Why proof beats testing: Loom/Miri explore bounded schedules; 0124 and 0384 passed the test suite [a.md].
Tool: Verus (Lion's method) plus a concurrent-separation extension (Verus has tracked ghost state / atomics invariants; feasibility of weak-memory atomics in Verus is ASSUMPTION, check).
Change for users: drop-in runtime with no lost wakeups under load; honest claim is "liveness under stated environment assumptions".
Scholar queries: "verified async runtime Rust"; "work-stealing scheduler verification"; "Verus concurrent data structure atomics"; "Iris RustBelt tokio"; "Chase-Lev deque formal verification weak memory"; "liveness verification Rust async lost wakeup".

## 2. Memory-bound and counter-conservation proof for QUIC/HTTP2 state machines (quinn-proto, h2)
Users: quinn-proto 443.7M, h2 996.6M downloads; all hyper/tonic/Pingora/reqwest users.
Class: peer-triggered unbounded memory/CPU (remote unauthenticated DoS). Quotes [a.md]:
- https://rustsec.org/advisories/RUSTSEC-2026-0523.html (quinn-proto) "a peer can send one small MAX_STREAM_DATA frame naming a very large stream index, and `accept` then yields every stream up to that index."
- https://rustsec.org/advisories/RUSTSEC-2026-0339.html (quinn) unbounded RETIRE_CONNECTION_ID queue: "The normal path bounds this queue and closes the connection with a CONNECTION_ID_LIMIT_ERROR if the bound would be exceeded."
- https://rustsec.org/advisories/RUSTSEC-2026-0258.html (h2) "accept and queue empty DATA frames without limit"
- https://rustsec.org/advisories/RUSTSEC-2023-0034.html (h2) "the pending accept queue can grow in memory usage"
- https://rustsec.org/advisories/RUSTSEC-2026-0389.html (Pingora) "used the h2 crate's default HTTP/2 server limits, a 16 MiB decoded header-list size and no limit on concurrent streams"
Theorem: for all peer frame sequences, bytes held by the connection <= f(config); each counter equals the sum over the structure it summarizes. quinn-proto is sans-IO, so it is a pure state machine, which suits Verus.
Why proof beats testing: bug pattern is "normal path bounded, odd path not" (0339); fuzzers must hit the odd path; a proof forces every path.
Prior work (known): s2n-quic runs Kani harnesses (https://github.com/aws/s2n-quic/blob/main/docs/dev-guide/kani.md); verified QUIC parsing in EverParse/Project Everest (QUIC-LowParse). Need to confirm nobody proved resource bounds. Scholar queries: "QUIC formal verification resource exhaustion"; "verified QUIC implementation"; "IVy QUIC formal specification"; "EverParse QUIC"; "HTTP/2 denial of service formal verification"; "Kani s2n-quic".
OPINION: a clear class and recurring (>=10 advisories), but may read as engineering; the paper angle is a reusable "bounded queue" invariant library in Verus.
Change for users: DoS-resistance guarantee instead of patch-per-advisory.

## 3. Hickory DNS: parser/decoder totality and DNSSEC validation correctness
Users: hickory-proto 108.6M downloads; Prossimo funds it (ISRG blog above: "Rustls TLS library, Hickory DNS, River reverse proxy, sudo-rs..."). Smaller than 1-2; I have no sourced deployment count for resolvers (gap).
Class (FACT, advisories fetched via search summary; verify on rustsec.org before quoting):
- https://rustsec.org/advisories/RUSTSEC-2026-0118.html NSEC3 closest-encloser proof validation "enters unbounded loop on cross-zone responses"; release builds compile the assertion out.
- https://rustsec.org/advisories/RUSTSEC-2026-0119.html "CPU exhaustion during message encoding due to O(n²) name compression"
- RUSTSEC-2026-0491 "Memory amplification from record counts in the DNS message header"
- RUSTSEC-2026-0487 / 0490 parser panics (SVCB alpn, 4096+ char zone token)
- RUSTSEC-2026-0549 / 0556 DNSSEC bypass: NSEC3 NODATA at zone apex accepted without a matching NSEC3 record (secondary summary)
Theorem: decode(encode(m)) = m and decode is total with allocation <= c*|input|; DNSSEC validator accepts only if the denial/answer proof follows RFC 5155/4035.
Prior work: verified DNS in Coq/Lean "Formal verification of DNS (GRoot, SCALE)" mostly zone-config analysis; EverParse for parsers. Queries: "verified DNS resolver"; "formal verification DNSSEC validation"; "SCALE DNS symbolic execution"; "EverParse DNS".
OPINION: security-relevant (cache poisoning/DNSSEC bypass), but the parser half is incremental over EverParse; the DNSSEC proof-chain half is the novel part. Smaller user base, but DNS is infrastructure.

## 4. Cancellation safety of async Rust (Pingora cache, hyper/h2 client)
Class (all [a.md]): a future dropped at one await leaves shared state inconsistent.
- https://github.com/cloudflare/pingora/issues/931 (open, possibly AI-generated report per a.md caveat) "later same-key callers wait forever on the leaked zero-permit semaphore"
- https://github.com/hyperium/hyper/issues/4040 (closed) "it does **not** signal `pipe_task` in any way"
- https://github.com/hyperium/hyper/issues/3906 (closed) "panicked at 'state=State { inner: Closed(ScheduledLibraryReset(CANCEL)) }'"
- https://github.com/quinn-rs/quinn/issues/1763 "Presumably RecvStream::read` can be cancelled and retried without missing reads, but I'm not sure just from the docs."
Theorem: for each async fn, dropping at any await point preserves the module invariant (or the API documents non-cancel-safety).
Tool: Verus plus a model of drop-at-await (a.md calls it the strongest paper candidate; I agree on novelty (INFERENCE) but have not searched prior work). Queries: "cancellation safety async Rust"; "cancel safe futures verification"; "drop at await point formal"; "Rust async verification Verus futures".
Impact: Pingora (1T+ requests/day) cache coalescing; hyper clients.

## Open items for the Scholar agent
- Read arXiv 2610.09198 and check whether it already covers multi-threading.
- Check whether Verus supports the atomics/weak-memory reasoning needed for 1.
