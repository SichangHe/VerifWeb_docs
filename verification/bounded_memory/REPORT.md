# Bounded memory against a hostile peer: study
(authored by agents unless marked 🧑)

As of 2026-11-13, we have a Verus proof that the actual code of one quinn-proto buffer, the incoming DATAGRAM queue, keeps its accounted memory within the configured `datagram_receive_buffer_size` for every sequence of peer frames. The same proof fails on the pre-fix code of RUSTSEC-2026-0342, at exactly the memory-bound postcondition. This is one buffer out of several per connection, not a whole-connection theorem, and the accounted memory is not yet the true heap footprint (see "Gaps").

## Why this class matters

Peer-driven memory bugs recur in the most used Rust network crates, and their fixes are local patches that keep missing paths. quinn-proto's 2026 chain is the clearest:

- RUSTSEC-2026-0185 capped buffered stream fragments; RUSTSEC-2026-0341 says “the cap was only checked inside the branch that triggers defragmentation ... Frames handled entirely by the unordered-read deduplication loop returned before the check ran at all”, and “With the default `TransportConfig` ... a remote, unauthenticated peer can pin roughly 3 GB of receiver memory”.
- RUSTSEC-2026-0339: “The normal path bounds this queue ... However, the path handling a connection ID that had already been retired pushed onto the queue without applying the limit”.
- RUSTSEC-2026-0342: “A DATAGRAM frame with an empty payload was charged zero bytes, so it never triggered eviction and was appended to the queue, which has no other bound.”
- RUSTSEC-2026-0343, a bug in a release carrying the new limit: it “subtracted an evicted datagram's size from the buffered byte counter twice”.
- RUSTSEC-2026-0523: “`received_max_stream_data` treated the stream, and every lower-numbered stream, as opened without checking the stream ID against the limit advertised to the peer.”

h2 has the same shape in four advisories on different queues and counters (RUSTSEC-2023-0034, 2024-0003, 2024-0332, 2026-0258), and its counter-based fixes then cut off legitimate traffic: h2 issue #944 says “Streams with high-volume undersized `DATA` frames were cut off with `GOAWAY ENHANCE_YOUR_CHILL` in `v0.4.16`”. Pingora RUSTSEC-2026-0389 shows h2's default limits let “a single connection ... get a Pingora process with a 2 GiB memory limit OOM-killed”. Outside RustSec, s2n-quic (GHSA-9q54-f358-3fqf: “a single 1200-byte packet can cause approximately 9.4 MB of allocation”) and quiche (unbounded connection-ID retirement storage, path events, and per-flow maps, 2023–2026) have the same failures. We found no peer-driven memory advisory for tokio, hyper, tonic, or the quinn wrapper crate; that is absence of reports, not evidence of a bound.

Inference: the common cause is a limit that is charged incorrectly or checked on some paths only. A single invariant “retained memory ≤ f(config)”, proved over every mutation site, would have rejected 0339, 0341, 0342, 0343, and 0523 by construction; tests and fuzzers see these only if they take the rare path and measure memory.

Reach (crates.io, fetched 2026-11-14): quinn-proto 430 M all-time downloads (158 M in about 90 days); quinn 420 M with 682 reverse dependencies; h2 977 M; hyper 1.13 B with 6,090 reverse dependencies; rustls 1.12 B; tonic 474 M; s2n-quic 0.86 M; quiche 3.1 M.

## What the proof establishes

Target: quinn main at `c7b46a969cd315398b504792e9e9af6a15a7dcc6`, `quinn-proto/src/connection/datagrams.rs`: `DatagramState::received` (handles a peer's DATAGRAM frame), `recv`, and `DatagramBuffer::{push_back, pop_front, memory_used, is_empty}`. quinn-proto is sans-IO, so these are plain synchronous functions; no async cancellation issue arises.

Specification ([fixed.rs](fixed.rs)): `wf` says the counter `payload_bytes` equals the sum of queued payload lengths. `mem` is `payload_bytes + queue.len() * size_of::<Datagram>()` in mathematical integers. The theorem on `received` is: if the buffer is well formed and `mem ≤ window` before, then afterwards it is well formed and `mem ≤ window`. Within the crate, only `received` and `recv` touch `incoming`, the window comes from the immutable connection config, and the buffer starts empty. Inference: by induction, `mem ≤ datagram_receive_buffer_size` holds after every peer frame sequence. The proof also shows absence of arithmetic overflow and termination of the eviction loop.

Result with Verus `0.2026.11.13.6ae5f7b`: fixed code, “verification results:: 19 verified, 0 errors”. [buggy.rs](buggy.rs), the parent of fix commit `a3109c34` with the same specification: “18 verified, 1 errors”, failing the `mem ≤ window` postcondition. The old code bounds only payload bytes, so empty frames grow the queue without limit, which is RUSTSEC-2026-0342. Tying the specification to all memory, not to the counter the code happened to keep, is what exposes the bug.

Connection to real code: the executable code between the `BEGIN UPSTREAM` and `END UPSTREAM` markers is upstream code with Verus annotations added and `debug!` lines removed. [conform.py](conform.py) checks this mechanically: after stripping specification clauses, proof blocks, comments, and whitespace, every upstream item must appear verbatim; a one-character mutation (`>` to `>=`) is reported. This is a textual check, not a compiled-artifact link: the verified file is compiled by Verus, not as part of quinn-proto's build. `bash run.sh` (with `VERUS` and, if needed, `VERUS_Z3_PATH` set) clones quinn, runs both conformance checks, and both verifications.

Trusted base, stated in the file: a `Bytes` stand-in exposing only `len` (real type: `bytes::Bytes`); a `TransportError` stub; a Verus `assume_specification` that `VecDeque::is_empty` returns `len == 0`; vstd's `VecDeque` specifications; and environment preconditions that a datagram and `size_of::<Datagram>()` are at most `isize::MAX` and that old memory plus the new datagram fits in `usize`. The last holds because the buffered objects exist in memory; it is not proved from code.

## Gaps

Accounted memory is not the heap. Two differences remain unproved. First, `VecDeque` capacity can exceed its length. Second, `frame.rs` builds DATAGRAM payloads with `self.bytes.split_to(len as usize)`, a slice that shares the received packet's buffer. Hypothesis, not tested: each queued small datagram keeps its whole packet buffer alive, so true memory could be about MTU / `size_of::<Datagram>()` times the configured window. Still bounded by configuration, but by a much larger function. A measurement or a `Bytes` model with ownership of the underlying buffer would settle it.

One buffer is not a connection. The direction needs the sum over streams (assembler, RUSTSEC-2026-0341), pending connection-ID retirements (0339), stream-open state (0523), outgoing control-frame queues, and crypto buffers. Each needs its own invariant against the configured limits, and their sum gives the per-connection theorem. 0523 is the next natural target: its bound is on stream count, so the specification must relate opened streams to the advertised limit. The stream code is much larger than this file; we have not estimated the effort.

A per-connection bound does not bound a server. Number of connections is an endpoint limit; the theorem composes only if each connection's limit is proved.

## Prior work

Seven Google Scholar queries (paced, no CAPTCHA) found no paper proving per-connection memory bounds against a hostile peer for a real QUIC or HTTP/2 implementation. Seven queries is weak evidence of absence. The nearest work, judged from Scholar snippets only (papers not opened):

- Automatic amortized resource analysis: RaRust (Lian and Wang, PACMPL 2025), “automatic amortized resource analysis for Rust programs”; Liquid resource types (ICFP 2020); the survey by Hoffmann and Jost (2022). These infer cost bounds; no network application seen.
- Verified Rust systems: Verus (OOPSLA 2023, SOSP 2024); Atmosphere (SOSP 2025), whose snippet says “To reason about the system's memory usage, we ...”, the closest found to proved memory accounting in real Rust.
- Verified protocol code covers parsers and record layers, not retained state: the verified QUIC record layer (S&P 2021), EverParse (PLDI 2022), Vest (USENIX Security 2025).
- Kani runs in s2n-quic's CI; per its 2026 paper, it is bounded model checking, so it covers inputs only up to a bound.

No paper was downloaded, so none was added to the paper collection.

## Recommended next step

Extend the same method to quinn-proto's stream-open bound (RUSTSEC-2026-0523) and assembler (0185/0341), with pre-fix code required to fail, then state the per-connection sum. In parallel, measure whether shared `Bytes` makes true memory exceed accounted memory; if it does, the specification, and possibly quinn, must count retained packet buffers. The decision for the human is whether a textual conformance check is an acceptable link to real code, or whether the proof must run on quinn-proto's own build, for example in a fork with Verus annotations in place.

## Scholar update, 2026-11-14 (changed in this pass)

Four more Scholar queries, snippets only. New closest work:
- Medusa: "unveil memory exhaustion DoS vulnerabilities in protocol implementations" (Du et al., 2024, ACM): finds such bugs by analysis/testing, no bound proof.
- PRETT2: "Discovering HTTP/2 DoS Vulnerabilities via Protocol Reverse Engineering" (ESORICS 2024), MadeYouReset (IEEE S&P 2026), "Logical Vulnerabilities in QUIC Implementations" (NDSS 2026, 16 implementations): attack/bug finding.
- RaRust, "Automatic Linear Resource Bound Analysis for Rust via Prophecy Potentials" (Lian, Wang, PACMPL 2025), already listed above.

Verdict: still open (unchanged). Bug-finding for memory-exhaustion DoS is active; proving a per-connection bound on real code was not found.

