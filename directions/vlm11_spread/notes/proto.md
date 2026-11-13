(authored by agents unless marked 🧑)

# formal-verification targets: servers/CDNs, protocols, web standards

tags: [F] fact with quote+URL, [I] inference, [O] opinion.
limits: search tool gave summaries, so quotes below are verbatim from fetched pages or from search-tool text as marked "(search summary)". Candidates 6-12 lack a fetched bug source; their "why" is [I]. Two bug-search queries were blocked by a safeguard error (see raw_proto/search_log.txt). Scholar not used.

## 1. HTTP/1.1 message framing agreement (request smuggling)
- why: [F] HTTP Garden, https://arxiv.org/pdf/2405.17737 : "substantial parsing discrepancies exist between nearly all pairs of HTTP/1.1 implementations."
- why: [F] same paper: "when the cache server and origin server differ in their interpretation of an incoming request's URI, the cache might store data that the origin server didn't expect"
- verified already: none found for proofs that two HTTP parsers agree. [F] (search summary, query 3): "no paper that formally proves two HTTP/1.1 implementations agree on message framing". Only differential fuzzing (T-Reqs, HTTP Garden). Related: EverParse/3D verified parsers (arXiv 2609.12488, not fetched).
- new: [I] a machine-checked framing function (CL/TE/chunked/obs-fold) with a non-malleability proof, plus a theorem "proxy and origin parse equal or one rejects" for a compliant-strict profile. Verifying one strict parser shows no desync for that parser only; [I] pairwise agreement needs a shared spec.

## 2. HTTP/2 to HTTP/1 downgrade translation
- why: [F] https://portswigger.net/research/http2 : "HTTP/2 downgrading is when a front-end server speaks HTTP/2 with clients, but rewrites requests into HTTP/1.1"; "Amazon Web Services' (AWS) Application Load Balancer failed to obey this line, and accepted requests containing Transfer-Encoding."; "I could take full control over every page on every site on the Netlify CDN." Netflix: CVE-2021-21295 (Netty).
- verified: none found (query 1, 3). 
- new: [I] verify a translator H2 frame/pseudo-header/header-set -> H1 bytes satisfies "output parses under H1 framing to exactly one request equal to the H2 request". Small, bounded, well-specified; [O] best-scoped item here.

## 3. HTTP/2 stream/flow-control state machine and resource bounds (Rapid Reset)
- why: [F] https://cloud.google.com/blog/products/identity-security/how-it-works-the-novel-http2-rapid-reset-ddos-attack : "rather than waiting for a response to each request stream from the server or proxy, the client cancels each request immediately." CVE-2023-44487.
- verified: none found for HTTP/2 or HTTP/3 (query 1: "None of the results covered formal verification of HTTP/2 or HTTP/3 themselves", search summary).
- new: [I] model RFC 9113 stream state machine and prove safety/liveness plus a bound "server work <= f(client-paid cost)". The resource-accounting property is non-standard; [O] hard to state, high value.

## 4. QUIC (and HTTP/3 over it) implementation conformance
- verified: [F] McMillan/Zuck, Ivy specs and testers; "Verifying QUIC implementations using Ivy" https://arxiv.org/pdf/2503.01374 (search summary: "implement[s] a significant part of draft-29 requirements in Ivy"; "contradictions and ambiguities in the QUIC specification"). Saved raw_proto/ivy_quic_2503.01374.pdf (text extraction did not print abstract).
- gap: [I] those are draft-29, testing-based (specification-based testing, not proof of an implementation). Not HTTP/3, QPACK, or WebTransport; none found by query 1.
- new: [I] QPACK dynamic table sync and HTTP/3 stream mapping; WebTransport session/stream semantics over HTTP/3. Verified-code option (Ivy to extracted code) is [O] costly.

## 5. TLS 1.3 + ECH in browsers
- verified: [F] Bhargavan, Cheval, Wood, CCS 2022 https://dl.acm.org/doi/abs/10.1145/3548606.3559360 (search summary): "first mechanized formal analysis of privacy properties for the TLS 1.3 handshake", ProVerif, draft-ietf-tls-esni-13, "attacks on ECH, some found during the course of this study".
- gap: [I] analysis covers the protocol only ("omitting outside factors that nevertheless are important for privacy"). Not covered: browser fallback/retry-config logic, DNS HTTPS-RR interaction (cleartext DNS leak), GREASE behavior, final RFC vs draft-13. No Tamarin ECH model found.
- new: [I] model the browser ECH client state machine + DNS (HTTPS RR, DoH) as one system and prove the SNI-privacy property under fallback.

## 6. DNS-over-HTTPS / DoH fallback and resolver selection in browsers
- why: [I] fallback to system resolver breaks the privacy and policy invariants; no bug source fetched.
- verified: none found (no query hit DoH specifically; query 1 and 7 returned nothing). Weak "none found": only 2 queries touched it.
- new: [I] small state machine (opportunistic vs strict, canary domains, enterprise policy) with a proved invariant "no query leaves in clear in strict mode".

## 7. WebAuthn / FIDO2 / passkeys
- verified: [F] Barbosa et al. CRYPTO 2021 (search summary): "It confirms that WebAuthn's authentication is secure, but shows CTAP2 can only be proved secure in a weak sense". [F] Bindel, Cremers, Zhao, IEEE S&P 2023: "proves FIDO2 with WebAuthn 2 and CTAP 2.1 secure against classical adversaries". [F] Barbosa et al. PoPETs 2025 https://eprint.iacr.org/2025/459.pdf. [F] "A Formal Analysis of the FIDO2 Protocols" ESORICS (symbolic).
- gap: [F] (search summary) "None of these papers gives a passkey-specific proof for credentials synced across devices."
- new: [I] synced-passkey model: cloud sync + account recovery + cross-device (hybrid/CTAP over BLE+tunnel) flows, relying-party origin/rpId checks in the browser (related-origin requests). Browser-side origin binding checks are not in the crypto proofs. [O] strong candidate.

## 8. OAuth 2.0 / OIDC in browsers
- verified: [F] Fett, Küsters, Schmitz, CCS 2016 https://arxiv.org/abs/1601.01229 (search summary): "Our in-depth analysis revealed four attacks on OAuth"; OIDC at CSF 2017 https://arxiv.org/abs/1704.08539. Pen-and-paper in the FKS web model; (search summary, second-hand) "The analysis is not machine-verified". 
- gap: [I] no mechanized proof found; FKS predates OAuth 2.1/BCP, FedCM, DPoP, browser changes (third-party-cookie removal, SameSite=Lax default).
- new: [I] mechanize FKS-style model (Tamarin/Coq) for OAuth 2.1 + FedCM, with browser rules as assumptions. Mechanization = new; model fidelity to real browsers = hard ([O]).

## 9. Browser web model: Origin/site, SameSite, cookies, storage partitioning, CHIPS
- verified: [F] ETH thesis, https://ethz.ch/content/dam/ethz/special-interest/infk/inst-infsec/information-security-group-dam/research/software/ma-19-duenki-webmodel.pdf (search summary): Tamarin web model with cookie storage per browser and domain; SameSite and partitioning not shown. FKS model exists (candidate 8). Akhawe et al. "Towards a Formal Foundation of Web Security" (Alloy) suggested by search tool, not fetched.
- spec drift evidence: [F] https://github.com/WICG/CHIPS/issues/40 (search summary): "The ancestor chain bit was added to the partitioned storage key to enforce SameSite semantics in service workers and to prevent click jacking." [F] W3C slides (search summary): "Cookies, Storage, Network all have different partition keys".
- none found: query 6 for SameSite+partitioning+Alloy/Tamarin/Coq.
- new: [I] one model of all partition keys (cookies, storage, network, cache, HSTS?, service workers) and prove cross-site non-interference unless explicit opt-in. [O] high value; spec is moving.

## 10. WHATWG URL / Fetch / HTML spec algorithms
- verified (partial): [F] Lean 4 proof (search summary of https://github.com/danbri/factoidal/issues/1188): path rule "gives the same path as RFC 3986 §5.2.4 removeDotSegments"; whole-parser claim "is measured, not proved" ("403407 agree, 0 disagree"). Not peer-reviewed; single author. [F] "A Model of Navigation History" https://arxiv.org/pdf/1608.05444: model "found that the specified model does not satisfy this property, but we have shown that a patched model does."
- none found: Fetch standard mechanized model (query 10).
- why: [F] HTTP Garden quote above: URI interpretation differences between cache and origin.
- new: [I] full URL parser equivalence to a relational spec; Fetch CORS/redirect/credentials algorithm as a model with a proved CSRF/leak-freedom property. [O] Fetch is the highest-impact unexplored standard.

## 11. Cache keys: web cache poisoning/deception, RFC 9111, Vary
- why: [F] https://portswigger.net/web-security/web-cache-poisoning (search summary): "Caches identify equivalent requests by comparing a predefined subset of the request's components, known collectively as the 'cache key'. Components of the request that are not included in the cache key are said to be 'unkeyed'."
- verified: none found (query 4: only DNS cache poisoning models, Son & Shmatikov, and CTMC for Kaminsky).
- new: [I] formal cache-semantics (RFC 9111 + Vary + CDN key rewrites) with theorem "response served to request r equals what origin would return for r" under declared key-function assumptions. Detects unkeyed-input dependence statically if origin is modeled as input-dependency set. Needs origin abstraction; [O] feasible for CDN config only.

## 12. Edge compute isolation (Workers/V8 isolates) and edge config languages
- verified: [F] vWasm (USENIX Sec 2022) https://www.usenix.org/system/files/sec22-bosamiya.pdf : "formally-verified provably-safe sandboxing Wasm-to-native compiler"; WaVe (S&P 2023) https://cseweb.ucsd.edu/~dstefan/pubs/johnson:2023:wave.pdf verifies hostcalls keep isolation; the paper says Wasm isolates code on edge clouds (search summary). None found for V8-isolate-based Workers (query 9: "None of the results show formal verification of Cloudflare Workers or of V8 isolates").
- edge config languages (VCL, Cloudflare rules, Envoy/nginx config, CloudFront functions): none found (no dedicated query beyond 4, 9; weak). [I] semantics-and-equivalence checking of rule languages is open here.
- new: [I] verified edge-rule engine (ordering, rewrite, cache-key transformation) with Cloudflare-style rules as a small DSL; verify "rule change cannot alter cache key unless declared". [O] cheaper than isolate proofs, which are engine internals.

## 13. Permissions Policy / Feature Policy, CSP inheritance
- why: [I] delegation across iframes (allow attributes, header inheritance, default allowlists) is a small algorithm that is easy to specify. No bug source fetched.
- verified: none found by name (no query run; Scholar unused). Treat as untested.
- new: [I] mechanize inheritance algorithm and prove "a frame cannot gain a feature its parent denied", plus equivalence with CSP/Sandbox flags.

## ranking [O]
1 candidate 2 (H2 downgrade translator), 9 (partition keys), 7 (synced passkeys + browser origin checks), 10 (Fetch), 8 (mechanized OAuth 2.1/FedCM), 11, 3, 5, then 4, 12, 6, 13.
