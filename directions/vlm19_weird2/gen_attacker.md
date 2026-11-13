# Weird web verification targets (attacker / archivist view)
(authored by agents unless marked 🧑)
Author: agent, persona = browser exploit researcher + web archivist. Prior-work notes are from memory, unchecked online ("unchecked" = I did not search). Nothing published.
Lens: the bugs sit where two parsers, two clocks, or two copies of the same bytes must agree, in standards few people read.

1. Archive snapshot consistency (serializability for the web)
- thing: replaying a page from many mementos (HTML, JS, CSS captured at different times; Memento RFC 7089)
- theorem: the replay engine's chosen mementos either share one time window of width <= d in which every URL was live and unchanged, or it reports "inconsistent"
- why unthought: replay is judged by eye; nobody treats it like snapshot isolation in a database
- prior: Ainsworth/Nelson/Van de Sompel "temporal violations" measurement (2011-ish), unchecked; no proof known
- step: Lean model of a capture index (URL, time) plus selection rule; prove or counterexample for pywb's rule

2. WARC round trip and digest laws
- thing: WARC 1.1 writer/reader, per-record gzip members, revisit (dedup) records, WARC-Payload-Digest
- theorem: read(write(msg)) = msg byte for byte, and a revisit record resolves to a payload whose digest equals its stated digest, for chunked or content-encoded bodies (digest over which bytes?)
- why unthought: format is treated as a dumb container; the digest-over-decoded-vs-raw ambiguity is rarely read
- prior: warcio/Heritrix issue trackers, unchecked; no formal work known
- step: Verus proof of the record framing parser (length + CRLFCRLF rules), then differential test vs warcio

3. HAR sanitizer completeness
- thing: HAR 1.2 files shared in bug reports (Okta 2023 support-system leak came from HAR files with live session tokens)
- theorem: sanitize(har) contains no value that was in any credential-bearing position (Cookie, Set-Cookie, Authorization, token in URL query, postData, base64 bodies) of the input
- why unthought: HAR is a log, not an attack surface; secrets also hide in encoded bodies and redirect URLs
- prior: Google's har-sanitizer tool (heuristic); no proof known
- step: define a taint model over the HAR JSON schema; prove a small sanitizer, show where the real tool leaks

4. HAR timing arithmetic
- thing: HAR "time" = blocked+dns+connect+send+wait+receive (with -1 = absent; ssl is inside connect)
- theorem: exporters satisfy time = sum of present parts and ssl <= connect; counterexamples are exporter bugs
- why unthought: looks too trivial; analysts trust these numbers for performance claims
- prior: none known (unchecked)
- step: check HARs exported from 3 browsers against the spec equation in Z3; report violation rate

5. robots.txt parser equivalence (RFC 9309)
- thing: longest-match Allow/Disallow, wildcard *, $ anchor, percent-encoding normalization, 500 KiB cap, 5xx means disallow-all, 4xx means allow-all
- theorem: parser P decides allowed(url) exactly as the RFC's rules do, for all byte inputs
- why unthought: "just a text file"; but crawlers, AI-crawler opt-outs, and archives rely on it, and Python's urllib.robotparser is known to differ from the RFC (as I recall)
- prior: Google's open-source parser with tests; robots.txt measurement papers (not proofs)
- step: Lean spec of RFC 9309; verify a 100-line matcher; fuzz-diff three real parsers

6. Certificate Transparency consistency-proof verifier
- thing: RFC 6962 / 9162 Merkle inclusion and consistency proof checking, for non-power-of-two tree sizes
- theorem: verifier accepts (old root, new root, proof) iff the old tree is a prefix of the new one (soundness; completeness for honest logs)
- why unthought: the crypto is "obviously" fine; the bug risk is in index arithmetic on odd sizes in monitors and archives that store CT data
- prior: verified Merkle trees exist in general (unchecked for CT specifically)
- step: Verus proof of the iterative algorithm in RFC 9162 section 2.1.4, then test against real log STHs

7. HTTP-date and freshness arithmetic
- thing: three accepted date formats (IMF-fixdate, obsolete RFC 850 with 2-digit year and 50-year window, asctime); Age, max-age, heuristic freshness (10% of Last-Modified age) in RFC 9111
- theorem: parser accepts exactly those formats; freshness_lifetime and current_age never overflow and, once stale, a response stays stale until validated
- why unthought: obsolete formats are "dead"; yet caches and archives (which stamp captures with these headers) must still parse old servers' output
- prior: none known (unchecked)
- step: bounded model check of the parser plus 32-bit clamp rules (Age >= 2^31) in Rust

8. Cache key soundness (Vary, no web cache deception)
- thing: shared-cache key = URL + Vary-selected request headers (RFC 9111 4.1), plus path-extension rules at CDNs
- theorem: a cached response served for request R equals what the origin would send for R, given the origin's declared Vary and a model of which request parts it reads
- why unthought: attacks (cache poisoning, web cache deception) are found by probing, not stated as a refinement property
- prior: Kettle 2018 poisoning; Mirheidari et al. "Cached and Confused" (USENIX Sec 2020); formal treatment unchecked
- step: Tamarin/Alloy model of cache + origin with unkeyed inputs; rediscover Kettle's X-Forwarded-Host attack as the counterexample

9. Streaming invariance of decoding and HTML parsing
- thing: Encoding Standard decoders and the HTML prescan (first 1024 bytes meta charset), fed by arbitrary network chunking
- theorem: for any split of the byte stream into chunks, output text and DOM are identical to the one-shot result (or the difference is exactly the spec-allowed re-parse on late meta)
- why unthought: tests use whole files; real networks and archive replays chunk differently, and a split inside a multi-byte or ISO-2022-JP escape is a classic filter-bypass corner
- prior: WPT tests (examples, no proof); unchecked otherwise
- step: prove chunk-invariance for the UTF-8 and ISO-2022-JP decoders in Verus; extend to the tokenizer later

10. Public Suffix List lookup and IDNA idempotence
- thing: PSL algorithm (wildcard and exception rules) and UTS #46 ToASCII
- theorem: registrable_domain is a function agreeing across implementations; ToASCII(ToASCII(x)) = ToASCII(x); no two hosts with different registrable domains map to the same ASCII form
- why unthought: the PSL is data, so people test it; nobody states the algebra. A mismatch is a cookie-scope or same-site bug
- prior: PSL/cookie-scope measurement papers; unchecked for proofs
- step: Lean spec of the PSL algorithm; check Python publicsuffix2 vs Go vs rust-url on the whole current list

11. Cookie jar eviction cannot be steered by insecure origins
- thing: RFC 6265bis storage model: per-domain cap, eviction order, "leave secure cookies alone", path/creation-time ordering in the Cookie header
- theorem: no Set-Cookie from an insecure context can delete, overwrite, or evict a Secure cookie, and Cookie header order is the specified total order
- why unthought: eviction is housekeeping, not a security feature; it is a cookie-tossing/forcing primitive
- prior: Zheng et al. "Cookies Lack Integrity" (USENIX Sec 2015); formal model unchecked
- step: Alloy model of the jar with a cap; ask for a sequence that evicts a Secure cookie in a 2020s-era rule set

Dropped as too known: request smuggling framing agreement (many tools), SRI hash checks, CSP parsers.
