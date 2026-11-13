# FV-shaped web targets (privacy, caches, cookies, plus broader web)
(authored by agents unless marked 🧑)

Scope: human said "look at things that we should formally verify that are related to the web", so section C is not privacy-specific. Excluded: C2PA, WARC, measurement studies, and the four IDEAS/pitch files.
Shape tested [inference]: small decision procedure, precise spec, costly error, input space too big to test.
Quote hygiene: WebFetch returns quotes cut to about 125 characters, so quotes are short. "[search-summary]" marks text I saw only in a search-engine summary because the page was unreadable (Chromium tracker needs login); re-check before relying on it.
Scholar: `scholar/q1..q9.json` (all read; snippets only; "none seen" means none in the first page snippets, not proof of absence).
Nothing published.

## A. Cookies and privacy

### A1. Cookie Domain vs Public Suffix List acceptance
- thing: when a site sets `Domain=x`, the browser must decide if `x` is a public suffix (e.g. `co.uk`) and reject; a wrong answer lets one site set cookies for unrelated sites
- failure: crawlberg #762, "In HTTP mode, crawlberg stores a cookie whose `Domain` is a public suffix when that suffix is not in a short fixed list." and "It then sends that cookie to every other site under the same suffix. Chrome rejects the same cookie." https://github.com/xberg-io/crawlberg/issues/762
- failure: browsers disagree (Zhong Yu, http-state, 2015): "Firefox is the only browser that implements it" (RFC 6265 5.3 same-host case); "IE apparently misunderstands wildcard rules" https://mailarchive.ietf.org/arch/msg/http-state/TPAIg769WRpZsQVkKOCFpQNqFmE/
- property: for every host and PSL (including wildcard `*.x` and exception `!y` rules), `accept(domain attr, request host)` equals the RFC 6265bis algorithm, and a cookie accepted never matches a host outside its registrable domain
- why FV: PSL has about 10k rules with wildcards and exceptions and changes weekly; tests cover listed examples only
- prior: Scholar q1 snippet: "how formal shim verification enabled us to formally verify the ... current domain suffixes build on the notion of a public suffix" (Jang, Tatlock, Lerner, USENIX Sec 2012, Quark kernel). So cookie-domain logic was verified once, 2012, against a fixed abstract suffix predicate, not the real PSL algorithm
- step: Lean/Verus the PSL matcher (longest match, wildcard, exception) from the publicsuffix.org algorithm and prove it equals a naive spec over all labels sequences

### A2. CHIPS partition key and the ancestor-chain bit
- thing: Partitioned cookies are keyed by (cookie, top-level site, bit "has cross-site ancestor")
- failure: Chromium 337206302, "Ancestor Chain Bit for CHIPS breaks sending partitioned cookies in cross-site redirects" [search-summary of title] https://issues.chromium.org/issues/337206302
- failure: launch delayed by "a partitioned cookies privacy bug" [search-summary, unverified: fetch of the blink-dev thread did not show it] https://groups.google.com/a/chromium.org/g/blink-dev/c/JNOQvsTxecI/m/V-OewM3lAwAJ
- property: a cookie stored under partition (T, b) is readable only in a context whose computed (T, b) equals it, across redirects, nested A->B->A frames, and workers
- why FV: key is recomputed in many code paths (redirects, frames, workers, WebView); each fix changed the key
- prior: Scholar q2 snippet: "Computer-aided formal security analysis of the Web platform" (Veronese, TU Wien 2024) covers same-site and cookies; I did not see partitioning
- step: model frame tree + redirect chain, prove key equality is path-independent

### A3. Storage Access API grant logic
- thing: iframes ask to get unpartitioned cookies; browsers decide grant by user activation, prior first-party interaction, sandbox flags
- failure: WebKit 193277 "Storage Access API doesn't appear to work": "despite hasStorageAccess() returning true, and the promise requestStorageAccess() resolving." and "An iframe (siteB) is still unable to set and get cookies." Closed INVALID because the third party needed prior first-party interaction https://bugs.webkit.org/show_bug.cgi?id=193277
- failure: Firefox 1664779 logged a sandbox error even with the token present (title: "document.requestStorageAccess() may not be called in a sandboxed iframe without allow-storage-access-by-user-activation..." ) https://bugzilla.mozilla.org/show_bug.cgi?id=1664779
- property: `hasStorageAccess()==true` iff cookie jar access for that frame is actually unpartitioned; grant preserved only across spec-listed navigations
- why FV: hasStorageAccess, the promise and the cookie jar are three separate answers to one state; engines drift
- prior: Scholar q7 snippets only: "Exploiting the Shared Storage API" (Nisenoff, Stefan, Christin, CCS 2025) and "Least privilege access for persistent storage mechanisms in web browsers" (Kancherla et al., 2025); empirical, no formal grant model seen
- step: a 6-state model (grant, activation, sandbox, navigation kinds) and prove the three views agree

### A4. Attribution Reporting / Private Aggregation budget
- thing: ad measurement reports with noise; a per-source contribution budget (L1 = 65536) caps what one source leaks
- failure: Chrome's own authors: "neither ARA nor PAA has been backed by a rigorous DP proof" (arXiv 2412.16916, as quoted by fetch); earlier work found "the sensitivity of the output aggregate can increase with the number of publishers and advertisers" https://arxiv.org/html/2412.16916v1
- property: for any sequence of triggers, sum of contributions per source never exceeds budget, and clamping happens before noise (the discrete-Laplace scale uses the cap)
- why FV: budget filter state machine across multiple sources/triggers/destinations; the DP theorem is conditional on that filter being right
- prior: the paper above proves DP on paper only ("The text describes mathematical proofs only" per fetch); Scholar q3 snippet only a survey remark "machine-checked formal model" . No machine-checked proof seen
- step: verify the budget-filter code (Chromium `AttributionStorage` rules) against the invariant, leave DP theorem as hypothesis

### A5. Topics API epoch/ noise selection
- thing: browser picks top-5 topics per week, returns one per epoch with 5% random topic
- failure: researchers' own simulation had "simulation bug fixed and new Topics classifier (v5)" (arXiv 2403.19577 comments); measured re-identification "of 2%, 3%, and 4% after 1, 2, and 3 observations" https://arxiv.org/abs/2403.19577
- property: per (caller, site, epoch) the returned topic is deterministic and the set a caller can see is the intersection spec requires (caller had observed topic)
- why FV: small selection rule; cross-caller filtering is easy to get subtly wrong. Note: the privacy claim itself is empirical, so only the filtering rule is a proof target [inference]
- prior: none formal seen
- step: prove the "caller observed" filter on a 3-epoch model

### A6. Protected Audience k-anonymity enforcement
- thing: an ad may win/report only if its set has at least k users
- failure: Chrome PSA: "Recently, we became aware that Chrome was mistakenly applying k-anonymity enforcement on reporting to a portion of Mode A..." (rest cut) https://www.mail-archive.com/blink-dev@chromium.org/msg09890.html
- limit: "the design of the kk-anonymity check in PrAu is ineffective" (arXiv 2405.08102 sec 5) https://arxiv.org/html/2405.08102v1 . So proving the check is correct does not give privacy [inference]; weak target
- property: enforcement applied exactly where spec says (auction decision vs reporting), threshold monotone
- prior: none seen. Rating: low, because spec is acknowledged weak.

### A7. Bounce-tracking storage deletion
- thing: delete storage of sites seen as redirect hops with no user activation in the last 45 days
- spec admits holes: "TODO: Consider if we should do anything when the clock is moved forward or backward." and "TODO: Verify that using domain-match catches all cookies for the registrable domain." and "it may be necessary to weigh the cost of this 1 bit information leak" https://privacycg.github.io/nav-tracking-mitigations/
- property: a host is purged iff bounced, grace period elapsed, no activation within lifetime, for any interleaving of clock, activations, navigations; and the deletion set equals all state of the registrable domain
- why FV: timers x events x clock jumps is a temporal state space tests hit poorly; and the TODOs name real gaps
- prior: Scholar q9 returned only unrelated hits (aviation tracking); none seen
- step: timed-automaton model; check clock-skew TODO

### A8. IAB TCF consent string codec
- thing: the base64 consent string carrying user consent per vendor, passed between CMP and ad tech
- failure: iabtcf-es #142: "according to spec, we need to have 733 bits that indicate if vendors have consent or not. but we only have 28 bits." Maintainer: "That string is either invalidly encoded or truncated in some way." https://github.com/InteractiveAdvertisingBureau/iabtcf-es/issues/142
- property: decode(encode(x))=x for all well-formed x, and decode rejects every malformed string (range vs bitfield, MaxVendorId, segment order); a vendor is shown consent only if its bit is set
- why FV: bit-level format, run-length ranges, optional segments; legal cost of a wrong "consent=1"
- prior: none seen (Scholar q5 returned only compliance measurement, e.g. "Johnny can't revoke consent either")
- step: Verus/Lean the core segment decoder, prove round trip; fuzz official libraries against it

### A9. Privacy Pass (low novelty)
- thing: anonymous tokens
- "we perform the first analysis of Privacy Pass using formal verification tools" and "we also explore a stronger attack model, where key leakage uncovers a potential token forgery" https://eprint.iacr.org/2025/2022
- already done symbolically (Tamarin); remaining gap is the implementation/wire format. Rating: low.

## B. Caches

### B1. Vary vs actual cache key
- thing: `Vary` lists request headers that must be part of the cache key
- failure: "2512 websites include some header names in the Vary response header but do not configure their web cache(s) to include them in the cache key." and "only 3128 websites included the Vary header" https://arxiv.org/html/2407.16303 . (This is a measurement, used only as evidence of failure.)
- property: a stored response is served for request R iff for every header in Vary the stored and R values match under the RFC 9111 normalization (incl. `Vary: *`, absent vs empty)
- why FV: key construction is a pure function with many normalizations (case, order, whitespace, multiple fields)
- prior: Scholar q6 snippet: "Formal models for web navigations with session control and browser cache" (Chen, Zhao 2004), and RFC 9111 conformance work "Who's breaking the rules?" is testing. No verified key function seen
- step: Lean spec of "match" and a verified implementation; diff against nginx/Varnish/Squid on generated headers

### B2. Double-keyed cache: popular-resource exemption
- thing: Chrome keys cache by (top-level site, frame site, URL) to stop history sniffing
- failure: Chromium 520186620 "Cache partitioning bypass via over-broad URLPattern wildcard in SharedResourceChecker" [search-summary; page needs login]: popular resources skip partitioning; on multi-tenant CDNs the pattern also matches unpopular tenants https://issues.chromium.org/issues/520186620
- property: any entry stored without the partition prefix matches a URL that the allowlist semantics intend, i.e. the pattern language's match set is a subset of the intended resource set
- why FV: URL-pattern wildcards x multi-tenant hostnames; small matcher, large input space
- prior: Scholar q8 snippets: "Xsinator.com: From a formal model to the automatic evaluation of cross-site leaks in web browsers" (Knittel et al., 2021) and "SoK: ... xs-leaks through an extended formal model" (Van Goethem et al., 2022): formal models of leak techniques, tested not proved; no verified cache-key code seen
- step: verify URLPattern subset check for the allowlist format

### B3. Surrogate-Control vs Cache-Control precedence
- thing: CDN must follow Surrogate-Control over Cache-Control
- failure: Varnish #109 "Surrogate-Control: max-age=0 is ignored when Cache-Control specifies downstream freshness or is omitted"; "pages intended to be fetched dynamically per edge visitor are cached and served stale to all subsequent visitors." https://github.com/jonbaldie/varnish/issues/109
- property: `shared_cacheable(resp)` equals the precedence table for all header combinations incl. `max-age=0+0`, `00`
- why FV: header-combination space is infinite (extensions, number formats)
- prior: none seen
- step: small pure-function spec and proof, then differential test with seven combos from the issue

### B4. Web cache deception / CPDoS as path-and-status rules
- failure: "Web cache deception (WCD) is an attack ... where an attacker tricks a caching proxy into erroneously storing private information" https://www.usenix.org/system/files/sec20-mirheidari.pdf ; CPDoS: "One of the main reasons for HHO and HMC CPDoS attacks lies in the fact that a vulnerable cache illicitly stores responses containing error codes such as 400 Bad Request by default." [search-summary] https://cpdos.org/
- property: a cache never stores a response whose cacheability depends on a request component outside the key (path suffix rules, error status)
- why FV: configuration is a small rule list; but needs origin model [inference], so heavier
- prior: HDiff/HTTP Garden are testing tools (DSN 2022)
- step: verify a CDN rule set (e.g. static-extension caching rule) against an origin routing model

## C. Broader web

### C1. HTTP Range handling in proxies
- failure: Squid SQUID-2021:4: "Due to an integer overflow bug Squid is vulnerable to a Denial of Service attack"; trigger "can be expected to exist in HTTP traffic without any malicious intent" https://github.com/squid-cache/squid/security/advisories/GHSA-pxwq-f3qr-w2xf
- property: Range parsing/merging never overflows and returns exactly RFC 9110 satisfiable ranges
- why FV: integer ranges over 64-bit; tiny spec (RFC 9110 14)
- prior: none seen
- step: Verus a Range parser + coalescer

### C2. Hostname normalization (IDNA/UTS46) before access checks
- failure: Go x/net/idna "incorrectly accepts Punycode-encoded labels that decode to ASCII-only strings, violating UTS 46 revision 33" and "`xn--example-.com` is accepted and normalized to `example.com` instead of being rejected." https://www.krakend.io/security-advisories/cve-2026-39821/
- property: to_ascii(h) equals the UTS46 table-driven result for all inputs; validators on ASCII form and on Unicode form agree
- why FV: Unicode table x punycode arithmetic; testing needs the full table
- prior: none seen (Scholar not run for this one)
- step: prove the punycode decode/encode round trip and the "decodes to ASCII" rejection

### C3. HTTP/1.1 message framing (smuggling)
- thing: where a message ends (Content-Length vs Transfer-Encoding)
- "an attack that exploits a semantic gap in parsing more than one Content-Length or Transfer-Encoding header field" and "we discovered 14 vulnerabilities" (HDiff, DSN 2022; text from search-summary) https://www.jianjunchen.com/p/hdiff.dsn22.pdf
- property: parser's framing equals RFC 9112 or the message is rejected; two verified parsers agree on every byte stream
- prior: only differential fuzzing (HDiff, HTTP Garden https://arxiv.org/pdf/2405.17737), no proof seen
- step: verified framing function, compare with one proxy

### C4. Tracking-filter `$removeparam` matching
- failure: AdGuard #3615: "A valid named `$removeparam` rule fails before the request when the target is the first query item." and "the final address bar looks sanitized in both cases even though the first-position value has already left the browser." https://github.com/AdguardTeam/AdguardBrowserExtension/issues/3615
- failure: adblock-rust #245 "Support removeparam exceptions" (exceptions silently unsupported since 2023) https://github.com/brave/adblock-rust/issues/245
- property: compiled rule (Chrome DNR) matches a URL iff the source rule's `^`, `*`, `|` semantics match it; exceptions and `$badfilter` cancel exactly their targets
- why FV: translation from filter syntax to DNR with separator semantics; privacy-significant silent failure
- prior: Scholar q4 shows empirical filter-list work (Chen, Snyder et al.), no verification
- step: prove separator-aware translation correct on a 3-operator pattern language

## Ranking [opinion]
1. B3/B1 (smallest, clearest spec), 2. C4, 3. A8, 4. A1, 5. A7, 6. C1, 7. B2, 8. A3. A6 and A9 weakest.
Not done: C1-C3 had no own Scholar query; Chromium tracker quotes unverified; SameSite Lax+POST 2-minute rule seen only in blogs, dropped.
