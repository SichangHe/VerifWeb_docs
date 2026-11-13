# Web cache / HTTP plumbing findings (reading only; nothing published)
(authored by agents unless marked 🧑)

Caveats
- WebFetch limits quotes to short fragments, so some quotes are fragments but each is verbatim from the page or from pdftotext of the paper PDF. Items marked (secondary) came from a search summary, not the page; verify before relying on them.
- Venues for arXiv-only items are not confirmed. I did not use Google Scholar.
- Item 4 predates 2023; included as the baseline for item 3.

## 1. HTTP Garden: bare CR as chunk-line terminator (Node.js vs. CDNs)
- Venue: arXiv 2405.17737 (May 2024); venue not stated in PDF
- URL: https://arxiv.org/pdf/2405.17737
- Quote: "However, using the HTTP Garden, we discovered that Node.js allows chunk lines to be terminated by bare CR."
- Explanation: The RFCs say chunk lines end in CRLF, but Node.js also accepts a lone CR. Apache Traffic Server, Google Cloud Classic ALB and Akamai GHost forward CR bytes in the whitespace before the ";" that starts a chunk extension. A proxy and Node.js therefore see different request boundaries, which allows smuggling and access-control bypass. Mitigations by Google (strip extensions) and Akamai (reject CR) were themselves incomplete.
- Rule violated: RFC 9112 chunk-size line = chunk-size [BWS ";" ...] CRLF, and a transducer must not forward bytes that the next hop parses differently. Roughly: for every byte stream s, framing_proxy(s) = framing_origin(s).
- CVE: none read in the PDF; Node.js fixed in 21.2.0. Also (same paper): "We found 122 unique parsing discrepancies" (partial quote).

## 2. HDHunter: number-parsing and trailer-section desync, including response-side
- Venue: USENIX Security 2025 (Mu, Chen, Zhuge, Li, Duan, Feamster)
- URL: https://www.usenix.org/system/files/usenixsecurity25-mu.pdf
- Quote: "We identified 17 HTTP Desync vulnerabilities in those implementations, affecting famous implementations like Apache, Tomcat, Squid, etc."
- Explanation: Gray-box differential testing across 19 implementations found five discrepancy classes: non-standard numbers, inconsistent trailer-section acceptance, non-standard line separator, different TE.CL handling and incomplete response sanitization. It covers HTTP responses and CGI responses, which earlier tools ignored. Table 1 lists Squid (number parsing, Critical), ATS (trailer section, Critical), Tomcat (trailer section, $4660 bounty).
- Rule violated: numeric fields must match 1*DIGIT or 1*HEXDIG (no sign, "0200", "0x" prefixes). Trailer fields must be consistently accepted or rejected by every hop.
- CVE: "A total of 9 CVE IDs have been assigned." The IDs are only checkmarks in Table 1; I did not extract them.

## 3. Path confusion: delimiter and %-decoding disagreement between CDN and origin
- Venue: PortSwigger Research whitepaper, Martin Doyhenard, Aug 2024 (PDF metadata date; conference not stated, possibly Black Hat USA 2024)
- URL: https://portswigger.net/kb/papers/kapvrid/gotta-cache-em-all.pdf
- Quote: "Many HTTP servers and proxies including Nginx, Node, CloudFlare, CloudFront and Google Cloud decode certain delimiter characters before interpreting the pathname."
- Quote: "This means that the same URL will have a different meaning in the most popular CDNs and origin servers even without any custom configuration."
- Explanation: Origins treat extra characters as path delimiters: ";" in Spring, "." in Rails, %00 in OpenLiteSpeed, %0A in Nginx rewrites. A cache that does not treat them as delimiters sees a static-looking path like /myAccount$x.css and stores the private response. Decoding is also inconsistent: "/hello/..%2fworld" resolves to /world on some servers and stays as is on others.
- Rule violated: the cache-key path and the origin-routed path must be the same function of the raw URL: normalize_cache(u) = normalize_origin(u), including delimiter set, %-decoding set, and dot-segment handling after decoding. This is a good formal target: a small relational spec over URL-to-path functions.
- CVE: none given.

## 4. Baseline (2022): WCD Escalates, path-confusion variants measured at scale
- Venue: USENIX Security 2022 (Mirheidari, Golinelli, Onarlioglu, Kirda, Crispo)
- URL: https://www.usenix.org/system/files/sec22-mirheidari.pdf
- Quote: "We identify 1188 vulnerable websites."
- Explanation: Using 12 attack URLs per page on the Alexa Top 10K, the paper finds encoded semicolon (%3B) works on 863 sites (72.64%), encoded newline (%0A) on 528, and encoded "#" (%23) on 526. The original technique (invalid path extension) found only 18 in the comparison set.
- Rule violated: same as item 3: cache and origin disagree on which prefix of the path identifies the resource.
- CVE: none ("no CVE to ..." in the Discussion).

## 5. Browsers disagree on RFC 9460 HTTPS record semantics
- Venue: IMC 2024 (Dong, Zhang, Lee, Huque, Sun); the arXiv page itself does not name the venue
- URL: https://arxiv.org/html/2403.15672v2
- Quote: "However, Chrome and Edge fail to utilize TargetName, resulting in failure of obtaining the right service."
- Quote: "Chrome and Edge experience a hard failure if unable to connect using the IP addresses in the A record."
- Explanation: Chrome and Edge ignore the port parameter and prefer A records over IP hints. Safari and Firefox honor port and use hints directly, and only Safari follows AliasMode targets. The paper also found domains where ipv4hint disagreed with A/AAAA for days, and, with malformed ECH config, "Chrome and Edge fail hard, while Firefox ignores it".
- Rule violated: RFC 9460 ServiceMode and AliasMode client procedure (TargetName, port, hint precedence, ECH fallback). Formalizable as a client state machine, with the invariant "reachable set from hints is a subset of the reachable set from A/AAAA".
- CVE: none.

## 6. Chromium: shared-resource exemption defeats double-keyed HTTP cache
- Venue: Chromium bug tracker 520186620 (not a paper; page needs JS/login, so the content was NOT read)
- URL: https://issues.chromium.org/issues/520186620
- Quote (title, as returned by search): "Cache partitioning bypass via over-broad URLPattern wildcard in SharedResourceChecker"
- Explanation (secondary, search summary, unverified): popular-resource patterns skip partitioning (the NetworkIsolationKey prefix is dropped), so a pattern matching multi-tenant paths such as cdn.shopify.com lets a site probe the shared entry by timing and learn a user's history.
- Rule violated: cache key must include top-frame site unless the resource is provably non-user-specific. The exemption predicate (URLPattern match) must imply "same bytes for all users", which an over-broad wildcard breaks.
- CVE: none seen.

## 7. URL parsing differentials at scale
- Venue: IEEE S&P 2027, "Parsers of Babel" (Blunt, Datta, Modval, Enck, Kapravelos); acceptance posted Sep 14, 2026
- URL: https://wspr.csc.ncsu.edu/news.html ; code https://github.com/wspr-ncsu/TURLMOIL
- Quote: "Our paper, Parsers of Babel: A Large Scale Study of URL Parsing Differentials, has been accepted for publication" (fragment; page then names S&P 2027)
- Explanation: Systematic comparison of URL parsers, following Equivocal URLs (ESORICS 2022). I did not find the paper text, so the findings are unknown. Related (secondary): the LangSec 2023 survey (https://langsec.org/spw23/papers/Ali_LangSec23.pdf) cites CVE-2020-5902 (F5 TMUI RCE), where Apache httpd and Tomcat normalize a URL differently.
- Rule violated: WHATWG URL algorithm vs RFC 3986 vs library-specific parsing. Exact violations unknown until the paper is read.
- CVE: CVE-2020-5902 (secondary, from the survey).

## 8. Defense with an explicit invariant: HTTP Request Synchronization
- Venue: arXiv 2510.09952 (Oct 2025; Topcuoglu, Onarlioglu, Sprecher, Kirda); venue not stated
- URL: https://arxiv.org/abs/2510.09952
- Quote: "every proxy server can validate that their processing is consistent with all previous hops" (fragment)
- Explanation: Each hop appends its processing history using standard HTTP extension points, and later hops check agreement. It was implemented for Apache, NGINX, HAProxy, Varnish and Cloudflare. It states the invariant but has no mechanized proof, so the invariant is a candidate target for a formal check.
- Rule: for hops h1..hn, interp(h_i, req) = interp(h_j, req) for all i, j. Formal methods: none mentioned on the page.
- CVE: none.

## Related, not a distinct finding
- Web Cache Overflow (arXiv 2608.04744, Aug 2026): "precise cache-key design is the most direct mitigation against this abuse vector" (fragment). Unnecessary request elements in cache keys create duplicate entries that degrade caches. https://arxiv.org/abs/2608.04744
- CCS 2024, Liang et al., "Internet's Invisible Enemy" (WCP measurement, tool HCache). The abstract says WCP stems from cache-key problems (secondary); the PDF returned 403. https://dl.acm.org/doi/pdf/10.1145/3658644.3690361
- bfcache and service-worker caches: no academic paper found. A Chrome/Edge BFCache information-disclosure CVE-2026-79059 appears in the FSTEC database (secondary, https://vulners.com/bdu_fstec/BDU:2026-16495). Not read.

## Prior formal-methods work (search results; none read in depth)
- Result of searches: I found nothing formalizing RFC 9111 caching, HTTP request smuggling, web cache deception or WHATWG URL parsing in Coq/Lean/TLA+/Alloy/ProVerif. "Nothing found" is a search result, not proof of absence.
- WebSpi (ProVerif library for web apps/browsers/HTTP): Bansal, Bhargavan et al. Search summary: "Because of how ProVerif does its analysis, the WebSpi model is monotonic." Survey: https://iris.unive.it/bitstream/10278/3685125/1/jlamp16.pdf
- Akhawe et al.: Alloy model of the web infrastructure. Fett/Kuesters/Schmitz: expressive web infrastructure model (manual proofs), https://d-nb.info/1175951277/34
- WebSpec: Coq framework for browser security mechanisms, https://arxiv.org/abs/2201.01649
- Bulwark: ProVerif-based monitoring, https://arxiv.org/abs/2101.06043
- An Alloy "security model with cache" paper exists (title only seen: "Towards Further Formal Foundation of Web Security: Expression of Temporal Logic in Alloy and Its Application to a Security Model With Cache"). Not read.
- EverParse / F*: "Access Control as Verified Parse Constraints" (arXiv 2609.12488) verifies an HTTP request preprocessor. Closest to a verified HTTP parser; I did not check scope.
- Ada URL parser (arXiv 2311.10533): WHATWG-compliant by testing, not verified. The WHATWG URL spec is a state machine, which suits formalization.
- T-Reqs (CCS 2021) has formal definitions of its mutation operators, per a search summary.
