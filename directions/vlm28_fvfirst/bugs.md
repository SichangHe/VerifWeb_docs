# Real documented bugs per web-system candidate
(authored by agents unless marked 🧑)

Quotes verbatim from the cited page (fetched 2026-11-09). "Year" is the publication/report year.
Search-engine summaries were not used as quotes; each quote was re-read from the primary source (NVD, RustSec, GitHub API, paper PDF).

## 1. HTTP request smuggling (boundary disagreement)
- hyper, CVE-2021-21299 (2021). https://rustsec.org/advisories/RUSTSEC-2021-0020.html
  "hyper's HTTP server code had a flaw that incorrectly understands some requests with multiple transfer-encoding headers to have a chunked payload, when it should have been rejected as illegal. This combined with an upstream HTTP proxy that understands the request payload boundary differently can result in "request smuggling" or "desync attacks"."
- Pingora, CVE-2026-2833 (2026). https://nvd.nist.gov/vuln/detail/CVE-2026-2833
  "An HTTP request smuggling vulnerability (CWE-444) was found in Pingora's handling of HTTP/1.1 connection upgrades. The issue occurs when a Pingora proxy reads a request containing an Upgrade header, causing the proxy to pass through the rest of the bytes on the connection to a backend before the backend has accepted the upgrade."
- Also Pingora CVE-2025-4366 (2025). https://rustsec.org/advisories/RUSTSEC-2025-0037.html
  "Pingora versions prior to 0.5.0 which used the caching functionality in pingora-proxy did not properly drain the downstream request body on cache hits. This allows an attacker to craft malicious HTTP/1.1 requests which could lead to request smuggling or cache poisoning."
- h2 crate: none found (no smuggling CVE located).

## 2. URL parser differentials
- Orange Tsai, Black Hat USA 2017 (2017). https://blackhat.com/docs/us-17/thursday/us-17-Tsai-A-New-Era-Of-SSRF-Exploiting-URL-Parser-In-Trending-Programming-Languages.pdf
  Slide text: "It's all about the inconsistency between URL parser and requester". Example on slide: `$url = 'http://127.0.0.1:11211#@google.com:80/';` marked "Fixed in PHP 7.0.13". (Slides are bullet fragments; no full sentence available beyond the first.)
- Rust idna (used by rust-url), CVE-2024-12224 (2024). https://rustsec.org/advisories/RUSTSEC-2024-0421.html
  "idna 0.5.0 and earlier accepts Punycode labels that do not produce any non-ASCII output, which means that either ASCII labels or the empty root label can be masked such that they appear unequal without IDNA processing or when processed with a different implementation and equal when processed with idna 0.5.0 or earlier."
- rust-url / Servo url crate vs WHATWG parser differential advisory itself: none found.

## 3. Cookie jar rules
- Cookie Crumbles, USENIX Security 2023. https://www.usenix.org/system/files/usenixsecurity23-squarcina.pdf (Sec. 4.2.1)
  "We found that this design introduces a novel attack vector that can bypass even the __Host- prefix."
  Also: "...jointly disclosed the __Host- cookie bypass to the Chrome [29] and Firefox [34] security teams who issued CVE-2022-2860 and CVE-2022-40958, respectively."
- Chrome CVE-2022-2860 (2022). https://nvd.nist.gov/vuln/detail/CVE-2022-2860
  "Insufficient policy enforcement in Cookies in Google Chrome prior to 104.0.5112.101 allowed a remote attacker to bypass cookie prefix restrictions via a crafted HTML page."
- Server side: Werkzeug CVE-2023-23934 (2023). https://github.com/advisories/GHSA-px8h-6qxv-m22q
  "Werkzeug <= 2.2.2 will parse the cookie `=__Host-test=bad` as `__Host-test=bad`."

## 4. CRDT convergence (real libraries)
No confirmed "replicas permanently diverge" bug in a released Automerge/Yjs/Loro found with a clean quote of a fixed CVE; these are open/closed issue reports:
- Loro #1215 (2026, open). https://github.com/loro-dev/loro/issues/1215
  "If a document first imports updates whose dependencies it doesn't have yet (they are kept as pending), and the missing dependencies then arrive inside a **snapshot** (`export(mode: .snapshot)`) rather than as updates, the pending changes enter the oplog but are never applied to the document state."
  (Same issue: "a fresh document built from this one's oplog shows different text.")
- Yjs #824 (2026, open at fetch time). https://github.com/yjs/yjs/issues/824
  "A struct integrated past a gap is pending again in a doc loaded from `encodeStateAsUpdate`, or built from `mergeUpdates` of the same updates. So the doc and its own reload show different content."
- Automerge #595 (2023, closed). https://github.com/automerge/automerge/issues/595
  Title: "Automerge.save does not persist orphan changes, potentially leading to a loss of convergence"
- Diamond Types: none found.

## 5. Wasm compiler / runtime (Rust)
- Wasmtime/Cranelift CVE-2023-26489 (2023). https://nvd.nist.gov/vuln/detail/CVE-2023-26489
  "wasmtime's code generator, Cranelift, has a bug on x86_64 targets where address-mode computation mistakenly would calculate a 35-bit effective address instead of WebAssembly's defined 33-bit effective address."
- Cranelift CVE-2023-27477 (2023), pure miscompilation. https://nvd.nist.gov/vuln/detail/CVE-2023-27477
  "Wasmtime's code generation backend, Cranelift, has a bug on x86_64 platforms for the WebAssembly `i8x16.select` instruction which will produce the wrong results when the same operand is provided to the instruction and some of the selected indices are greater than 16."

## 6. QUIC state-machine / liveness
- OpenSSL QUIC (not Rust), issue #33373 (2026). https://github.com/openssl/openssl/issues/33373
  "If the packet that carried the last such update is lost, OpenSSL declares the packet lost but does not send the update again. The peer stays at the old limit, the receiver has read everything up to that limit, and the stream makes no further progress."
- quiche (Rust, flow-control accounting, closes rather than hangs), issue #2696 (2026). https://github.com/cloudflare/quiche/issues/2696
  "The receiver occasionally closed the QUIC connection with `FLOW_CONTROL_ERROR`, typically within 60 minutes under this workload."
- quinn / s2n-quic liveness (hang/migration) bug with a quotable primary source: none found. (quinn RUSTSEC-2026-0037 etc. are panic/DoS, not liveness.)

## 7. CDN purge failures
- Cloudflare status incident, Fedramp purge bug (2026-11-06). https://www.cloudflarestatus.com/incidents/wp49bp8bqo6c
  "Cloudflare has identified a bug with our purge pipeline impacting fedramp customers. Stale content may be served until expired."
- Cloudflare status incident, Qingdao (2026-10-31). https://www.cloudflarestatus.com/incidents/5tlm9r9j9rpo
  "Cloudflare is observing cache purge delay in Qingdao in Shandong, China."
- Fastly / Akamai purge incident: none found.

## 8. CSP / policy evaluator bugs in browsers
- Chrome CVE-2022-3056 (2022). https://nvd.nist.gov/vuln/detail/CVE-2022-3056
  "Insufficient policy enforcement in Content Security Policy in Google Chrome prior to 105.0.5195.52 allowed a remote attacker to bypass content security policy via a crafted HTML page."
- Chrome CVE-2021-30532 (2021). https://nvd.nist.gov/vuln/detail/CVE-2021-30532
  Same wording, "prior to 91.0.4472.77".
- Permissions-Policy / CORS evaluator: none found (not searched deeply). NVD gives no spec-deviation detail; "deviation from spec" is my inference.

## 9. X.509 / TLS in Rust
- rustls-webpki, RUSTSEC-2026-0099 / CVE-2026-93601 (2026). https://rustsec.org/advisories/RUSTSEC-2026-0099.html
  "Permitted subtree name constraints for DNS names were accepted for certificates asserting a wildcard name. This was incorrect because, given a name constraint of accept.example.com , *.example.com could feasibly allow a name of reject.example.com which is outside the constraint."
- rustls-webpki RUSTSEC-2026-0098 (2026), URI name constraints ignored (seen via search summary only, quote not verified): not quoted.

## 10. OAuth/OIDC refresh-token rotation
- Keycloak CVE-2026-1035 (2026), token reuse accepted. https://nvd.nist.gov/vuln/detail/CVE-2026-1035
  "When strict refresh token rotation is enabled, the validation and update of refresh token usage are not performed atomically. This allows concurrent refresh requests to bypass single-use enforcement and issue multiple access tokens from the same refresh token."
- Random-logout race: client-side reports only (camunda-security-library #739, simple_module_python #738); not verified by me, not quoted. IdP-side logout-race bug in Kanidm/Auth0/Okta: none found.

## 11. Site isolation / process model
- Chrome CVE-2026-11693 (2026). https://nvd.nist.gov/vuln/detail/CVE-2026-11693
  "Inappropriate implementation in Plugins in Google Chrome prior to 149.0.7827.103 allowed a remote attacker who had compromised the renderer process to bypass site isolation via a crafted HTML page."
  Caveat: requires an already-compromised renderer. Servo-specific bug: none found.

## 12. HTTP/2 flow-control deadlock/liveness
- hyperium/h2 #975 (2026). https://github.com/hyperium/h2/issues/975
  "Under bulk data in both directions on one connection, two h2 peers can deadlock permanently."
- hyperium/h2 #853 (2025). https://github.com/hyperium/h2/issues/853
  Title: "Logical connection deadlock occurs under high concurrency - outgoing data transmission stops"
- hyper #2899 (2022). https://github.com/hyperium/hyper/issues/2899
  "Some part of response body is transferred (several megabytes) and then both server and client are stuck with zero bytes being transferred."
