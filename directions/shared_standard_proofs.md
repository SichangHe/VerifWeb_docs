# Sharing proofs across Rust implementations of one web standard

(authored by agents unless marked 🧑)

Request (🧑, relayed by manager): "It might be interesting to formally verify a bunch of Rust libraries based on web standards, and see if we can extract any proofs or something like that, to be shared among them. And in that way, we know how to do formal verification for these things in scale."

Evidence files: [vlm55_shared/survey.md](vlm55_shared/survey.md) (libraries, users, bugs, prior work; quotes from fetch/search tools, check before citing externally), [the pilot](../verification/shared_varint/REPORT.md). Related: [verify_standards.md](verify_standards.md), [bounded_memory](../verification/bounded_memory/REPORT.md).

## Answer in short

What transfers between implementations is the specification and the statement of the theorem, not the proof. In our pilot, one Verus spec of the RFC 9000 varint was proved against the real decoders of quinn-proto and quiche. The spec was reused unchanged. The decode lemmas were not, because the two decoders compute the value by different arithmetic routes. Most per-implementation effort went into Verus plumbing (buffer traits, std conversion specs), which is shared only by implementations that use the same libraries (INFERENCE from one pilot, n=2).

## Which standards have several popular Rust implementations (facts, survey.md)

Few do. QUIC has three independent popular ones: quinn-proto (430 M downloads), quiche/octets (5.1 M), s2n-quic (0.86 M). WebSocket has two: tungstenite (402 M), fastwebsockets (6.5 M). URL (url, 1.07 B, 17,887 reverse deps), HTTP/1 (httparse, used by hyper), HTTP/2 (h2), and TLS (rustls) each have one popular Rust implementation. Download counts from crates.io, fetched 2026-11-14.

INFERENCE: for URL and HTTP, "share proofs among libraries" mostly means one verified component used by many crates, not one spec checked against many. Many implementations of those standards exist across languages (the SecWeb 2022 study tested "8 URL parsers ... detected 4,262 inconsistencies"), but not in Rust.

Bugs in these crates are dominated by peer-driven panics and unbounded memory (12 quinn-proto advisories; h2 RUSTSEC-2023-0034, 2026-0258) and by spec conformance gaps in proxies (Pingora RUSTSEC-2026-0390: "RFC 9110 Section 7.6.1 requires intermediaries to remove them"). Our earlier work found rust-url fails 69 of 896 WPT URL tests (verification/vlm2_url).

## Prior work: what others reused (facts, survey.md)

- Vest (Verus, USENIX Security 2025) and EverParse/LowParse (F*): reuse a verified combinator library across formats (TLS, QUIC, Bitcoin, Wasm). They reuse proofs across formats in one implementation style, and generate the implementation.
- Verdict (Verus, USENIX Security 2025): one proof framework for X.509 policies of Chrome, Firefox and OpenSSL, "formally prove that they conform to a subset of RFC requirements"; integrated into rustls. Closest to "one spec, many behaviors", but the code is Verdict's, not the browsers'.
- SpecTec (Wasm) and ESMeta (ECMAScript): one machine-readable spec generates prose, interpreters and tests used by many engines. They reuse the spec, not proofs about implementations.
- s2n-quic has a Kani round-trip harness for its varint (bounded, round-trip only, not conformance to the RFC).
- Not found: any proof that two existing, independently written implementations conform to one shared spec. Searched with 5 Scholar queries plus web search; weak evidence of absence.

## Pilot result (facts, verification/shared_varint)

One spec (`decode`: big-endian value of the first `len` bytes modulo 2^(8·len−2)) proved against real code: quinn-proto `VarInt::decode` and `encode`, and quiche `Octets::get_varint`. Verus reports "27 verified, 0 errors" and "25 verified, 0 errors". A one-bit change to quiche's 4-byte mask is rejected. Upstream code is checked verbatim against pinned commits; the proof files are in public fork branches SichangHe/quinn and SichangHe/quiche `verus-varint`.

Reuse, in non-blank lines: the shared file has 132 lines (spec ~25, trusted std specs ~30, lemmas ~75). quinn needed 110 more proof and stand-in lines; quiche needed 96, about 45 of them assumed contracts for its byte readers. The encoding lemma is implementation-neutral; quiche's encoder was not proved, because it writes through a returned `&mut [u8]` we did not model.

Gaps: quiche's byte readers are trusted, not verified (Verus rejects their `static_assert!` const blocks); the link to real code is textual, not the crates' own build; two implementations of a 4-case codec is a small sample.

## What would make this scale (OPINION)

1. Share the spec and the theorem statement per standard, written over an abstract "unread bytes / written bytes" view. Each implementation adds only an adapter from its buffer type to that view. This part reused cleanly.
2. Share adapters per library, not per standard: `bytes::Buf`/`BufMut` specs would serve quinn, h2, hyper, tungstenite and others at once. Plumbing dominated our effort, so this is likely the largest saving.
3. Fix Verus's std gaps once: slice→array `try_into`, `from_be_bytes`, `unreachable!`, `mem::size_of` in const. We hit each in a 30-line function.
4. Expect lemmas to transfer only between implementations with the same arithmetic route. A library of "route" lemmas (mask-then-assemble vs assemble-then-mask) may cover most variants of a field codec.
5. Pick standards with at least two popular Rust implementations: QUIC frames and transport parameters (where quinn-proto's panic and memory advisories cluster), then WebSocket framing (tungstenite vs fastwebsockets).

## Open questions for the human

- Is textual conformance an acceptable link to real code, or must the proofs build inside the forked crates?
- Should "shared" target one spec checked against many Rust crates (QUIC, WebSocket), or one verified crate used by many (url, httparse), given most web standards have only one popular Rust implementation?

## Side observation (not checked)

quiche writes stream, crypto and datagram frame lengths with `put_varint_with_len(length, 2)`. A length ≥ 16384 would be truncated and its tag corrupted. Whether any configuration allows that was not checked.
