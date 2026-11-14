vlm55 survey: Rust web-standard libraries and reusable formal specs
(authored by agents unless marked 🧑)

- scope and conventions
  - fact = quoted or measured; inference = marked "inference"
  - crates.io numbers fetched 2026-11-14 18:25 UTC via https://crates.io/api/v1/crates/NAME and .../reverse_dependencies
  - format: all-time downloads / recent downloads (crates.io "recent" = last 90 days) / direct reverse deps
  - RustSec ids link to https://rustsec.org/advisories/ID.html; db cloned 2026-11-14 from https://github.com/rustsec/advisory-db
  - "independent" = different codebase and maintainers, same standard
  - Scholar: 5 queries (as_ylo=2022), no CAPTCHA seen

part 1: libraries per standard

- URL (WHATWG URL; RFC 3986 older)
  - >=2 independent popular Rust impls: no. only url is popular; ada-url is a binding to C++ Ada, tiny usage
  - url 2.5.8: 1,066,210,635 / 264,072,846 / 17,887 (https://crates.io/crates/url)
  - ada-url 4.0.0: 395,810 / 246,525 / 7 (https://crates.io/crates/ada-url)
  - idna 1.1.0 (used by url): 1,153,751,212 / 272,646,675 / 265
  - bugs, advisories
    - RUSTSEC-2024-0421 (idna): "`idna` accepts Punycode labels that do not produce any non-ASCII when decoded ... Concretely, `example.org` and `xn--example-.org` become equal after processing by `idna` 0.5.0 or earlier."
    - no RustSec entry for the url crate itself in the clone
  - bugs, spec conformance (open GitHub issues, fetched 2026-11-14)
    - https://github.com/servo/rust-url/issues/742 "Specification alignment tracking issue": "updating wpt testdata makes following nonalignment evident:" followed by an unchecked list of WHATWG/WPT PRs
    - https://github.com/servo/rust-url/issues/504 "Joining relative path onto a file:// url with a hostname is non spec compliant" (open)
    - https://github.com/servo/rust-url/issues/1135 "Implement URL Standard change to pass through bogus xn-- labels if the whole domain is ASCII" (open)
    - https://github.com/servo/rust-url/issues/612 "Url::parse does not encode backslash as %5C" (open; reporter: "Maybe this is as per spec, i'm not sure")
  - cross-implementation evidence: Ajmani et al., "yoU aRe a Liar://", SecWeb 2022 (in paper_collection): "We tested 8 URL parsers from different languages, browsers, and tools written in 5 programming languages. In total, we detected 4,262 inconsistencies with how each of the tools parse the same URL to its basic components."
    - also: "WHATWG specification while other libraries and commandline tools follow RFC 3968 to implement their URL parsers."
  - inference: one popular Rust impl, so "many impls" must come from other languages/engines (Ada, Chromium, Firefox) or from non-Rust Rust users (reqwest, hyper via http crate, below)

- HTTP/1.1 (RFC 9110/9112)
  - >=2 independent: weak. httparse is the shared parser (hyper, others); Pingora has its own HTTP/1 stack, unverified here (inference: it may also use httparse)
  - httparse 1.10.1: 894,639,264 / 238,544,424 / 652
  - hyper 1.12.0: 1,128,512,221 / 286,936,586 / 6,101
  - http 1.5.0 (types): 1,255,673,023 / 333,727,902 / 9,078
  - pingora 0.9.1: 10,034,780 / 1,150,457 / 61 (sub-crates pingora-core etc. carry the advisories)
  - advisories
    - RUSTSEC-2021-0078 (hyper), CVE-2021-32715: "`hyper`'s HTTP header parser accepted, according to RFC 7230, illegal contents inside `Content-Length` headers. Due to this, upstream HTTP proxies that ignore the header may still forward them along if it chooses to ignore the error."
    - RUSTSEC-2022-0022 (hyper): "Affected versions of this crate called `mem::uninitialized()` in the HTTP1 parser to create values of type `httparse::Header` ... This is unsound"
    - RUSTSEC-2026-0033 (pingora-core): "Pingora versions prior to 0.8.0 would immediately forward bytes following a request with an Upgrade header to the backend, without waiting for a 101 Switching Protocols response. This allows an attacker to smuggle requests to the backend and bypass proxy-level security controls."
    - RUSTSEC-2026-0390 (pingora-proxy): "...without removing the client's Connection header, other hop-by-hop headers, or the headers Connection nominated, although RFC 9110 Section 7.6.1 requires intermediaries to remove them."
    - RUSTSEC-2026-0035 (pingora-cache): "Pingora versions prior to 0.8.0 generated cache keys using only the URI path, excluding critical factors such as the host header."
    - RUSTSEC-2023-0065 (tungstenite, HTTP handshake parse): "...denial of service (minutes of CPU consumption) via an excessive length of an HTTP header in a client handshake."
  - httparse spec conformance (open issues)
    - https://github.com/seanmonstar/httparse/issues/161 "`is_token` implementation is more permissive than standard"; body cites RFC 9110 tchar and says "in practice it seems that this specific grammar is relaxed to a larger set of allowed characters"
    - https://github.com/seanmonstar/httparse/issues/196 "`Request::parse()` accepts invalid methods."
    - no RustSec entry for httparse in the clone

- HTTP/2 (RFC 9113)
  - >=2 independent: weak. h2 is the only widely used Rust impl; Pingora uses h2; others are small. Inference: no second popular impl
  - h2 0.4.20: 978,056,594 / 229,773,233 / 346
  - advisories
    - RUSTSEC-2023-0034, CVE-2023-26964: "If an attacker is able to flood the network with pairs of `HEADERS`/`RST_STREAM` frames, such that the `h2` application is not able to accept them faster than the bytes are received, the pending accept queue can grow in memory usage."
    - RUSTSEC-2026-0258: "The h2 crate, used internally by hyper, had a flaw that would accept and queue empty DATA frames without limit."
    - RUSTSEC-2026-0388 (pingora-core): "Pingora also accepted `:authority` values containing userinfo ... This violates RFC 9113 Section 8.3.1, which requires an intermediary to use the `:authority` value for Host and replace any existing Host field."
    - also in db: RUSTSEC-2024-0003, RUSTSEC-2024-0332 (h2; not read)

- QUIC (RFC 9000, incl. 62-bit varint, RFC 9001, RFC 9002)
  - >=2 independent: yes, 3 popular. quinn-proto, s2n-quic, quiche. Each has its own varint
  - quinn-proto 0.11.19: 430,615,611 / 159,436,309 / 118 (quinn: 420,730,759 / 156,050,835 / 682)
  - s2n-quic 1.92.0: 860,201 / 204,649 / 29 (s2n-quic-core: 1,366,038 / 307,971 / 15)
  - quiche 0.30.1: 3,066,357 / 642,888 / 34; octets 0.3.7 (holds `get_varint`): 5,143,392 / 1,699,001 / 18
  - h3 (HTTP/3, over quinn): 5,794,294 / 1,899,165 / 206
  - quinn-proto advisories
    - RUSTSEC-2026-0037, CVE-2026-31812: "Receiving QUIC transport parameters containing invalid values could lead to a panic. Unfortunately the maintainers did not properly assess usage of `unwrap()` calls in the transport parameters parsing code, and we did not have sufficient fuzzing coverage to find this"
    - RUSTSEC-2026-0338: "Remote peer can panic quinn-proto with zero-length STREAM frames during unordered reads"
    - RUSTSEC-2026-0341: "The fix for RUSTSEC-2026-0185 in 0.11.15 added a cap on the number of chunks buffered by the `Assembler` ... However, the cap was only checked inside the branch that triggers defragmentation"
    - 12 quinn-proto advisories total in the clone (2023-0063, 2024-0373, 2026-0037/0185/0338-0343/0523/0524)
  - quiche (GitHub security advisories, https://github.com/cloudflare/quiche/security/advisories)
    - GHSA-m3hh-f9gh-74c2: "Cloudflare quiche was discovered to be vulnerable to an infinite loop when sending packets containing RETIRE_CONNECTION_ID frames." (cites RFC 9000 s5.1)
    - GHSA-2v9p-3p3h-w56j: "Cloudflare quiche was discovered to be vulnerable to incorrect congestion window growth, which could cause it to send data at a rate faster than the path might actually support."
    - GHSA-mh64-ph39-mrc9 "Use-after-free in connection ID iterator FFI functions"
  - s2n-quic (https://github.com/aws/s2n-quic/security/advisories)
    - GHSA-475v-pq2g-fp9g: "An issue in s2n-quic could result in unnecessary resource utilization when peers open streams beyond advertised limits."
    - 6 listed; also GHSA-rfhg-rjfp-9q8q "Potential denial of service after connection migration"
  - pattern (inference): the advisories are mostly panics/DoS/resource bounds in frame and transport-parameter handling, i.e. exactly what a verified frame parser plus bounded-state invariants would address

- TLS (RFC 8446, RFC 5280 for certs)
  - >=2 independent: no popular Rust second impl (native-tls wraps OS/OpenSSL; not Rust). rustls is the one. webpki is shared
  - rustls 0.24.0-dev.3 (max version): 1,122,383,622 / 285,916,368 / 6,007
  - rustls-webpki: 979,213,580 / 274,570,381 / 319 (old webpki 0.22.4: 140,085,522 / 9,628,579 / 161)
  - advisories
    - RUSTSEC-2024-0399, CVE-2024-11738: "A bug introduced in rustls 0.23.13 leads to a panic if the received TLS ClientHello is fragmented."
    - RUSTSEC-2026-0349: "Unauthenticated ServerHello can downgrade later connections to classical key exchange"
    - RUSTSEC-2026-0098 (rustls-webpki): "Name constraints for URI names were incorrectly accepted"
    - RUSTSEC-2026-0099: "Permitted subtree name constraints for DNS names were accepted for certificates asserting a wildcard name."
    - 7 rustls and 6 rustls-webpki advisories in the clone
  - formal tooling in rustls repo: a grep for kani/verus/creusot/prusti/hax over .rs/.toml/.md in a 2026-11-14 shallow clone found no hits (fact about that grep only)

- cookies (RFC 6265)
  - >=2 independent: yes. cookie (parse/jar) and cookie_store (RFC 6265 matching, builds on cookie)
  - cookie 0.18.2: 284,304,642 / 73,268,761 / 502
  - cookie_store 0.22.1: 100,693,475 / 30,204,954 / 142
  - advisory: RUSTSEC-2017-0005 (cookie, old); not read
  - inference: cookie_store depends on cookie, so not independent; no spec-conformance issues found in a short GitHub search

- MIME sniffing (WHATWG MIME Sniffing)
  - infer 0.22.0: 147,050,372 / 37,253,239 / 376 (magic-number sniffing, not the WHATWG algorithm; inference from its README)
  - mime 0.3.18 (parse/types): 758,128,888 / 199,269,481 / 1,992
  - mime_guess 2.0.5 (extension map): 347,631,182 / 95,371,150 / 1,594
  - no Rust implementation of the full WHATWG sniffing algorithm found as a popular crate; Servo has one internally (not checked here)
  - no advisories found

- CSS tokenizing (CSS Syntax Level 3)
  - >=2 independent: yes. cssparser (Servo/Firefox) and lightningcss (own parser built on cssparser; inference: depends on it)
  - cssparser 0.38.0: 121,318,689 / 46,656,372 / 256
  - lightningcss 1.0.0-alpha.72: 5,009,883 / 1,536,637 / 166
  - no RustSec entries in clone for either
  - issues: https://github.com/parcel-bundler/lightningcss/issues/289 "`u + a` selector is minified to `u+a`" (open); https://github.com/servo/rust-cssparser/issues/460 "cssparser-color: debug assertion in hsl_to_rgb for a hue that overflows f32" (open)

- WebSocket (RFC 6455)
  - >=2 independent: yes. tungstenite and fastwebsockets are separate codebases
  - tungstenite 0.30.0: 402,300,129 / 129,310,690 / 765 (tokio-tungstenite: 361,115,579 / 116,698,637 / 3,882)
  - fastwebsockets 0.10.0 (Deno): 6,496,921 / 2,262,956 / 62
  - advisory: RUSTSEC-2023-0065 (above)
  - conformance: https://github.com/denoland/fastwebsockets/issues/122 "Fragmented text frame treated as invalid if it contains partial utf-8" (closed)

- Servo crates (reference point)
  - url, idna, cssparser are Servo-origin: https://github.com/servo/rust-url, https://github.com/servo/rust-cssparser
  - Servo's "html5ever", "selectors" not queried

- summary of >=2 independent popular Rust impls
  - yes: QUIC (3), WebSocket (2), CSS (2, weakly: lightningcss builds on cssparser)
  - weak/shared dependency: HTTP/1 (httparse reused by hyper, Pingora), cookies, TLS (single impl, shared webpki)
  - no: URL, HTTP/2, MIME sniffing, TLS (single popular Rust impl each)
  - consequence (inference): the best "one spec, many Rust impls" targets are QUIC frames/varint and WebSocket framing; URL/HTTP1 are best served by one verified component reused by many consumers

part 2: prior reusable specs and proofs

- Vest (Verus), Cai et al., USENIX Security 2025 (in collection)
  - source: https://github.com/secure-foundations/vest ; https://www.usenix.org/system/files/usenixsecurity25-cai-yi.pdf
  - what is reused: a combinator library `vest_lib` ("∼6K lines of Verus code (with ∼1:1:1 ratio of spec, proof, and exec code)") plus DSL compiler: "the VestDSL compiler can cleanly combine VestLib combinators to build up a specification, a proof, and a corresponding implementation from the existing combinator definitions in the library"
  - reused by: 3 formats in the paper ("the Bitcoin block format, TLS 1.3 handshake messages, and the WebAssembly binary format"); README adds WireGuard, CMS (ASN.1), CBOR
  - one spec, many impls? no: one generated implementation per format; reuse is of the proof library across formats, not across third-party implementations
  - Round Trip theorems "for all Vest formats"

- EverParse / 3D / QuackyDucky / EverCBOR (F*, Low*, Pulse)
  - sources: https://github.com/project-everest/everparse ; PLDI 2022 "Hardening attack surfaces with formally proven binary format parsers" (in collection); EverCBOR CCS 2025 (in collection)
  - README: "QuackyDucky: A frontend for EverParse that accepts data formats in a style common to many RFCs. We have used it to generate message processing code for several networking protocols, including TLS and QUIC."
  - README: "EverCBOR, a standalone verified C/Rust implementation of CBOR"; "EverCDDL ... generates verified C or Rust data types, parsers and serializers"
  - PLDI 2022 text: "EverParse3D has been in use in the Windows kernel for the past year. Applied primarily to the Hyper-V network vir-" (pdftotext line break)
  - what is reused: LowParse combinator library and its proofs, generated C (and some Rust) per format spec
  - not done: no Rust crate in the survey above uses EverParse output (fact about my search only: I checked rustls and s2n-quic for kani/verus only)

- HACL* / EverCrypt / libcrux / hax
  - HACL*: "a formally verified cryptographic library written in F*" (https://github.com/hacl-star/hacl-star)
  - libcrux README: "libcrux is a cryptographic library written in Rust. It uses formally verified code generated from the HACL* project and includes Rust code that is directly verified for runtime safety and functional correctness using the" hax toolchain
  - reused: F*-verified algorithm code extracted to C and Rust, consumed by libcrux and (per other sources, not checked here) Firefox, Linux; one verified spec per algorithm, many consumers
  - Bhargavan et al., "Formal security and functional verification of cryptographic protocol implementations in rust", CCS 2025 (found via Scholar; PDF not obtainable openly in this session, not added to collection)
    - snippet: "outlines our multi-prover methodology for verifying Rust code ... the protocol implementation against a formal specification"

- Verdict (Verus), Lin et al., USENIX Security 2025 (added to collection)
  - source: https://www.usenix.org/system/files/usenixsecurity25-lin-zhengyao.pdf
  - "we use Verdict's policy framework to implement the X.509 validation policies found in Google Chrome, Mozilla Firefox, and OpenSSL, and formally prove that they conform to a subset of RFC requirements"
  - "We also integrate Verdict into an existing TLS library, Rustls [54], and show that using Verdict in a practical setting incurs negligible overhead."
  - reused: one generic correctness proof parameterized by a user-supplied policy; 3 policies; integrated into 1 Rust TLS library
  - closest existing "one spec skeleton, many implementations' behavior" result; quote on why: "there is effectively no one true spec"

- Wasm SpecTec / ESMeta / P4-SpecTec (OCaml/Scala frameworks)
  - SpecTec, PLDI 2024 (in collection): "SpecTec serves as a single source of truth — from a SpecTec definition of the Wasm semantics, we can generate a typeset specification, including formal definitions and prose pseudocode descriptions, and a meta-level interpreter."
  - "the generated meta-level interpreter passes 100% of the applicable official test suite"
  - reused: one spec source -> LaTeX/prose, interpreter, (planned) test generation and theorem-prover backends. Not reused across third-party implementations directly; consumers are the standard and test suite
  - P4-SpecTec (in collection): "ESMeta has been officially integrated" (pdftotext truncation; ES: JavaScript) and "ESMeta reconstructs, whereas Wasm-SpecTec rewrites the existing normative specification"
  - WEST, ICSE 2025 (Scholar snippet only): "Wasm test cases from mechanized specifications written in SpecTec" -> test generation from one spec for many engines; not added to collection (only abstract seen)
  - relevance: prose-to-machine-spec is the method for WHATWG/IETF text; closest analog is ESMeta parsing the ECMA-262 prose

- Kani in s2n-quic
  - https://github.com/aws/s2n-quic/blob/main/docs/dev-guide/kani.md: "`s2n-quic` uses the [Kani Rust Verifier] tool for verifying properties throughout various places in the codebase. The Kani test harnesses are written using [bolero], which is also capable of running them as concrete tests."
  - 31 .rs files contain `kani::proof` (shallow clone, 2026-11-14)
  - RFC 9000 varint: quic/s2n-quic-core/src/varint/tests.rs has `#[cfg_attr(kani, kani::proof, kani::unwind(10), kani::solver(cadical))] fn round_trip_values_test()` asserting `assert_codec_round_trip_value!(VarInt, v)`
  - bounded model checking (unwind bounds) of a codec round trip, reused only inside s2n-quic; harness is not extractable to quinn or quiche
  - quiche's varint is `Octets::get_varint` in octets/src/lib.rs; grep found no kani or verus in quiche (2026-11-14)

- URL/HTTP formal specs
  - searched GitHub repos for WHATWG URL formal models (Coq/Lean/Isabelle/Verus): none found
  - Scholar found only testing work: Ajmani et al. (cross-testing of 8 URL parsers; added to collection)
  - Murphy 2022, "Parsing the QUIC Packet Description Language" (https://ry4n.org/s/Parsing_The_QUIC_Packet_Description_Language__Murphy_2022.pdf; Scholar snippet only): a grammar from the QUIC RFC with "a generic parser", not verified; not added
  - not found: any "one spec, many implementations" proof for URL, HTTP, or QUIC in Rust. Inference: this is a gap, not proof of absence

- other Scholar hits not pursued
  - Singh et al., "VUPER: Verified ASN.1 UPER Parser" (title only)
  - "Access Control as Verified Parse Constraints" (title only)
  - MiniPoly, ICSE 2026 (ESMeta -> polyfills; snippet only)

collection additions (not committed; /hdd1/sichanghe/paper_collection)
  - Towards Practical, End-to-End Formally Verified X.509 Certificate Validators with Verdict, Zhengyao Lin et al., USENIX Security, 2025
  - yoU aRe a Liar-- A Unified Framework for Cross-Testing URL Parsers, Dashmeet Kaur Ajmani et al., SecWeb, 2022
  - already present: Vest, EverParse PLDI 2022, EverCBOR, SpecTec PLDI 2024, P4-SpecTec, HACL*, 3DGen
