# Web/browser things worth formally verifying: a wide list
(authored by agents unless marked 🧑)

Labels: [F] fact, with a source; [I] inference; [O] opinion. Each item's verbatim quotes and URLs are in `notes/engine.md` (browser engine) and `notes/proto.md` (servers, protocols, standards). Caveat [F]: many quotes come from search-tool summaries, not fetched pages, and the notes mark those. No Scholar fetches were made. Searches on Wasm-engine CVEs, cookie parsing, cache deception and OAuth CVEs were blocked by a tool safeguard.

## Takeaway [O]
The most web-specific gap is "two programs must agree on how to read the same bytes". Today that is checked only by fuzzing, and the disagreements are real attacks: request smuggling, cache poisoning, URL confusion, HTTP/2 downgrade. One proof framework, "this translator or this pair of parsers preserves meaning", covers several of the top 5.

## Candidates (22; bug evidence / prior verification / what is new)
Browser engine
1. JIT range analysis: CVE-2019-9793 / done: VeRA (PLDI 2020), V8 translation validation (ICSE 2024) / new: little; crowded
2. WHATWG URL parser vs RFC 3986: CVE-2021-32786 / done: only a partial, unreviewed Lean proof of one path rule / new: full parser proof plus a differential theorem
3. browser security mechanisms (CORS, CSP, cookies, service workers): WebSpec found flaws / done: WebSpec (Coq model of the spec, not the code) / new: link the model to engine code
4. site isolation and the browser kernel: none gathered / done: QUARK (2012, toy browser) / new: Chrome-scale isolation invariants
5. WebAssembly semantics: CertiCoq-Wasm found a WasmCert modeling bug / done: WasmCert, WasmRef, vWasm / new: little; crowded
6. WGSL/WebGPU shader translation: DarthShader found 39 faults, 15 got Chrome CVEs / done: none found / new: WGSL semantics plus a verified or validated translator to HLSL/MSL/SPIR-V
7. IndexedDB: repeated use-after-free CVEs, e.g. CVE-2026-15107 / done: none found / new: lifetime and transaction model
8. extensions: none gathered / done: IBEX (pre-Manifest V3) / new: MV3 permission model
9. HTML/CSS parsing and cookie parsing: not searched (gap)

Servers, CDNs, edge
10. HTTP/1.1 framing agreement (smuggling): HTTP Garden "substantial parsing discrepancies exist between nearly all pairs" / done: fuzzing only; EverParse verifies single parsers / new: agreement proof between pairs
11. HTTP/2-to-HTTP/1 downgrade translator: PortSwigger, AWS ALB accepted Transfer-Encoding / done: none found / new: meaning-preserving translator
12. cache keys (poisoning, deception): PortSwigger / done: none found / new: a cache-key soundness property, "same key implies the origin gives the same response"
13. edge isolation and edge config languages: Cloudflare Spectre (vlm10) / done: vWasm, WaVe for Wasm; none for V8 isolates or rule languages / new: verified edge rule compiler
14. HTTP/2 stream state and resource bounds: Rapid Reset, CVE-2023-44487 / done: none found / new: resource-bound proofs

Protocols
15. QUIC/HTTP/3: Ivy found spec ambiguities / done: Ivy testers (draft-29) / new: QPACK, WebTransport, RFC 9000
16. TLS ECH in browsers: done: ProVerif (CCS 2022) / new: browser fallback and DNS interaction
17. DoH fallback: weakly searched

Standards
18. WebAuthn/passkeys: done: several proofs / new: synced passkeys, browser-side origin checks
19. OAuth/OIDC in browsers: done: pen-and-paper (Fett, Küsters, Schmitz, CCS 2016) / new: a mechanized proof
20. SameSite and storage partitioning: CHIPS spec patch for service workers / done: none found; a 2019 Tamarin model lacks them / new: model of the partition key
21. Fetch spec algorithms: done: none found / new: mechanize Fetch, as WasmCert did for Wasm
22. Permissions Policy: not searched

## Top 5 (special and web-specific) [O], each with a first small step
1. HTTP/2-to-HTTP/1 downgrade (11)
   - step: write a reference meaning for requests in Lean or Dafny, then prove a small downgrader keeps it; run it against HTTP Garden's inputs
2. parser agreement for HTTP framing and URLs (2, 10)
   - step: prove the WHATWG URL host/path rules equal RFC 3986 where both are defined, and list the exact inputs where they differ
3. cache-key soundness at CDNs (12)
   - step: state the property formally; check it on one open cache (e.g. Varnish's default key) against an origin model
4. WGSL shader translation (6)
   - step: per-shader translation validation for a small WGSL subset to SPIR-V in Tint or Naga; replay the DarthShader bugs
5. cookie/storage partition model (20)
   - step: extend WebSpec's Coq model with the CHIPS partition key and check the service-worker invariant

## Is a verified JS engine doable now? [O]
I don't know. Evidence: Wasm took years of spec mechanization (WasmCert). JS is much larger, and only spec-level work (e.g. JSCert, older) exists. Agents may cut the cost, but no result shows it. The top 5 are each far smaller.
