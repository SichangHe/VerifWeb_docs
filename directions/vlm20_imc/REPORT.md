# Weird web findings from IMC and friends, turned into verification targets
(authored by agents unless marked 🧑)

Scope (🧑 human, via manager): "look at weird stuff from conferences like IMC"; later correction: "I think we were saying more broadly to look at things that we should formally verify that are related to the web."
Sources: three subagent surveys in this directory (`privacy_findings.md`, `cache_findings.md`, `broad_findings.md`); quotes there were checked against paper PDFs unless marked "snippet". Google Scholar was not used.
Labels: "fact" = quoted from a source; "opinion" = ours.

## Takeaway (opinion)

The findings that suit formal verification share one shape: two parties must agree on a precise rule, and in practice they disagree. Examples: a CDN and an origin server reading the same URL differently, or a consent banner and an ad vendor holding different opt-out states. Measurement finds that some disagreement happened. A proof says it cannot happen for any input. Most of the papers below are measurements or differential tests, and for most of these mechanisms we found no formal model.

## Part 1: ten weird findings

1. **Revoked consent does not stay revoked (PoPETs 2025, https://arxiv.org/abs/2411.15414).** EU sites store the user's cookie-banner choice as a "consent string" and pass it to ad vendors. After a user withdraws consent, many sites keep the old "yes": "we analyzed 281 websites implementing the IAB Europe Transparency & Consent Framework, and found 22 websites that store a positive consent despite user's revocation." Also: "on 101 websites, third parties that have received consent upon user's acceptance, are not informed of revocation". What makes this weird is that the protocol itself never says how revocation must reach vendors: "TCF v2.2 does not specify any URL parameters to be used for this".

2. **"Reject" becomes "legitimate interest" (WWW 2024, https://dl.acm.org/doi/10.1145/3589334.3645618).** The consent string has a separate bit for "we don't need consent, we have a legitimate interest". After users click reject, sites set that bit: "72.8% of the websites that were TCF compliant claimed legitimate interest as a rationale for overriding the consent choice." The rules forbid this for Purpose 1, which is storing data on the device, yet sites claimed it anyway. Every Purpose-1 violation came from a single banner vendor, Didomi, which points to one code path rather than many site operators.

3. **One site, two privacy signals, opposite answers (USENIX Security 2025, https://www.usenix.org/system/files/usenixsecurity25-hausladen.pdf).** The browser's Global Privacy Control (GPC) signal must be copied into every opt-out string a site keeps, and sites often keep several. "In December 2023, 11% (325/3,074) of sites had inconsistent opt outs." In the largest inconsistent group, "7/8 (88%) sites were Penske Media Corporation (PMC) sites", which looks like one template bug. A 2026 preprint (https://arxiv.org/abs/2611.02014) also finds "130 (15.4%) publishers" setting contradictory strings, and that "82.7% of the advertisers in our dataset are never sent a USP or GPP String".

4. **A lone carriage-return byte splits requests (HTTP Garden, arXiv 2024, https://arxiv.org/pdf/2405.17737).** In HTTP/1.1 a body can arrive in "chunks", each starting with a length line ending in CR LF. "Node.js allows chunk lines to be terminated by bare CR", while proxies such as Akamai and Google Cloud's load balancer forward such bytes unchanged. The proxy and the server then disagree on where one request ends, so an attacker can hide a second request inside the first ("request smuggling"). The tool found "122 unique parsing discrepancies". A USENIX Security 2025 follow-up (https://www.usenix.org/system/files/usenixsecurity25-mu.pdf) "identified 17 HTTP Desync vulnerabilities", and "A total of 9 CVE IDs have been assigned."

5. **A semicolon makes a CDN cache your bank page (PortSwigger whitepaper 2024, https://portswigger.net/kb/papers/kapvrid/gotta-cache-em-all.pdf; baseline USENIX Security 2022, https://www.usenix.org/system/files/sec22-mirheidari.pdf).** A CDN caches files that look static, such as `.css`. Some origin servers treat `;` or an encoded newline as the end of the path, so `/myAccount;x.css` serves the private account page while the CDN files it as a public stylesheet. "the same URL will have a different meaning in the most popular CDNs and origin servers even without any custom configuration." The 2022 paper found "1188 vulnerable websites" in the top 10K. The encoded semicolon alone worked on 863 of them.

6. **Browsers read the new DNS "HTTPS record" differently (IMC 2024, https://arxiv.org/html/2403.15672v2).** A DNS HTTPS record tells a browser where and how to connect: port, alternate name, IP hints and an encryption key. "Chrome and Edge fail to utilize TargetName, resulting in failure of obtaining the right service." With a malformed encryption key, "Chrome and Edge fail hard, while Firefox ignores it". 317 domains published IP hints that contradicted their ordinary address records. Cloudflare switched off Encrypted Client Hello for all its customers on 2023-10-05 "due to a number of issues" (Cloudflare as quoted by the paper).

7. **Sharing a certificate lets another domain impersonate you (NDSS 2025, https://www.ndss-symposium.org/wp-content/uploads/2025-1086-paper.pdf).** One TLS certificate can list many domains. HTTP/2 server push and Signed Exchanges let a server deliver content "for" any domain on its certificate: "a domain can spoof the origin of another domain within the SAN list of TLS certificates to deliver resources and browsers will accept them as legitimate same-origin resources." Also: "11 out of 14 popular browsers, including Chrome and Edge, are vulnerable to at least one of our attacks". The browser's notion of "same site" (scheme, host, port) is stricter than HTTP's notion of "this server may speak for that host", and push slips through the gap between them.

8. **One OAuth client, many apps, crossed wires (USENIX Security 2025, https://www.usenix.org/system/files/usenixsecurity25-luo-kaixuan.pdf).** Automation and smart-home hubs let many third-party apps connect to your accounts, but the hub talks OAuth as a single client. "among 18 popular consumer- or enterprise-facing integration platforms, 11 are vulnerable to COAT and another 5 to CORF, including those built by Microsoft, Google and Amazon." COAT is cross-app account takeover, and CORF is the paper's term for cross-app request forgery. One resulting bug is CVE-2023-36019 (CVSS 9.6). The well-known formal OAuth analysis (Fett, Küsters, Schmitz, CCS 2016) assumes one client per app, which these platforms break.

9. **QUIC servers swap two bits when reporting congestion marks (IMC 2023, https://arxiv.org/abs/2309.14273).** QUIC, the transport under HTTP/3, lets routers mark packets instead of dropping them (ECN, Explicit Congestion Notification). A receiver must report back how many packets carried each mark. "less than 2% of QUIC hosts ... pass this validation." About 31% of the failures "failed ECN validation due to mirroring ECT(1) instead of the originally sent ECT(0) codepoints". The authors suspect a 1-vs-2 bit mix-up, the kind of slip a type or proof would catch.

10. **Checking a domain from several places still fails when its DNS is hijacked (arXiv 2302.08000; venue USENIX Security 2023 per subagent memory, unverified).** To issue a certificate, a certificate authority checks that you control the domain. Let's Encrypt checks from several network locations so a single routing hijack cannot fool it. "By hijacking traffic to a victim's domain during domain control validation, an adversary can fool a CA into signing a certificate on behalf of the adversary for a domain the adversary does not control." Hijacking the domain's nameservers rather than its web server affects every vantage point at once, which weakens the defence. Industry rules will require five vantage points from 2026-12-15 (search snippet, unverified).

## Part 2: six verification targets (opinion: ranked by fit)

### A. Consent choices propagate and agree (from findings 1–3)
- What it is: the cookie banner (a "consent management platform", CMP) records the user's choice and hands it to dozens of ad vendors on request, through a JavaScript API or request parameters.
- Going wrong: revocation that never reaches vendors (finding 1), a "reject" turned into "legitimate interest" (finding 2), sibling strings that disagree (finding 3).
- Property: in every possible order of user clicks and vendor requests, (a) after the user's latest choice, every vendor's next read returns that choice; (b) all strings a site emits encode the same opt-out; (c) Purpose 1 never rests on legitimate interest.
- Why formal: the bug is about ordering (revoke arrives after a vendor has cached "yes"), so it can hide in rare interleavings that a crawler never triggers. The spec also has a hole, since TCF defines no revocation path, and writing the model forces someone to fill it.
- Why unusual: consent is treated as a legal and measurement topic. We found no formal model of TCF/GPP.
- Prior work: the three measurement papers above. Nothing formal found.
- First step: a TLA+ model of the TCF v2.2 CMP API (`__tcfapi` getTCData and addEventListener) with one CMP, two vendors and a revoke action, then check property (a). Expected result: a counterexample, which would also show the spec gap.

### B. The CDN's cache key matches what the origin serves (from finding 5)
- What it is: a CDN decides "is this cacheable, and under what key?" from the URL, and the origin decides "which page is this?" from the same URL.
- Going wrong: `/myAccount;x.css` (finding 5); 1188 vulnerable sites in 2022.
- Property: for every raw URL u, if the CDN would cache u as public, then the origin routes u to a public resource. Stronger version: both sides derive the same path from u, applying the same delimiters, the same %-decoding and the same `..` handling.
- Why formal: the input space (all byte strings) is infinite, and the bugs live in rare characters. An SMT solver can either prove two normalization functions equivalent or produce the exact URL that breaks them.
- Why unusual: verified parsers exist, but proving that two different parsers agree is rarely done, and never for cache keys as far as we found.
- Prior work: differential testing (WCD Escalates 2022, Doyhenard 2024); the WHATWG URL spec is a state machine, but our search found no mechanized version.
- First step: write two normalizers (a default CDN rule set and Nginx/Spring path handling) in SMT-LIB or Lean, ask for a URL where they diverge, and confirm it reproduces a known variant.

### C. Every hop agrees on where an HTTP request ends (from finding 4)
- What it is: a request crosses a CDN, a load balancer and a server, and each must split the same byte stream into the same requests.
- Going wrong: the bare-CR chunk bug in Node.js (finding 4); 9 CVEs from HDHunter.
- Property: for a proxy P that forwards a transformed stream T(s) to server S, the requests S sees in T(s) are exactly the requests P saw in s, for every s.
- Why formal: the vendors' fixes after HTTP Garden were themselves incomplete (fact, cache_findings.md item 1), and patching one differential at a time does not show none remain. The property is a 2-safety (relational) property, which suits a product-program proof.
- Why unusual: EverParse verifies that one parser matches a spec. This target proves that a forwarding transformation preserves meaning across two parsers.
- Prior work: HTTP Garden and HDHunter (testing); HTTP Request Synchronization (arXiv 2510.09952) states the invariant "every proxy server can validate that their processing is consistent with all previous hops" without proving it.
- First step: chunked transfer encoding only. Formalize the RFC 9112 grammar plus a Node-like lenient parser, and prove or refute agreement after an ATS-like forwarding rule.

### D. A server can speak only for origins it truly owns (from finding 7)
- What it is: the browser keys security on the origin (scheme, host, port). HTTP/2 push and Signed Exchanges let a server attach content to an origin it chooses, provided that origin is on its certificate.
- Going wrong: 11 of 14 browsers accept pushed scripts as same-origin from a co-tenant on a shared certificate (finding 7).
- Property: a resource is stored under origin O only if it came from a connection whose peer is authorized for O under the same check SOP relies on, not merely by appearing on the certificate.
- Why formal: the bug is a gap between two definitions, and a small model checker shows exactly where they diverge. It also scales to every channel that delivers content, such as push, SXG, connection reuse and service workers.
- Why unusual: the existing web models (Web Infrastructure Model, WebSpec) do not model push or SXG, as far as the subagent knows.
- Prior work: the NDSS 2025 attack paper. The formal web models listed in cache_findings.md.
- First step: an Alloy model with domains, certificates, connections and an "accept pushed resource" rule. Check that no rule lets the attacker's domain write into the victim's origin, then add the coalescing rules Chrome actually uses.

### E. OAuth stays bound to one app on multi-app platforms (from finding 8)
- What it is: OAuth binds an authorization (code, state, redirect address) to one client. Integration platforms act as a single client for many apps.
- Going wrong: 16 of 18 platforms vulnerable; CVE-2023-36019 (finding 8).
- Property: a token a user grants to app X can never be redeemed by or for app Y, against an attacker who controls Y and can send the user links.
- Why formal: OAuth already has a strong formal track record (CCS 2016), so this extends a proven method to a deployment model it explicitly does not cover.
- Why unusual: it is the one target where formal prior work exists, but its assumption is broken in the field.
- Prior work: Fett/Küsters/Schmitz CCS 2016 (one client per app); the USENIX 2025 paper (testing with a state machine).
- First step: a Tamarin or ProVerif model with one platform, two apps, one provider and an honest user. Reproduce COAT as an attack trace, then add the paper's proposed fix and prove the binding.

### F. Multi-vantage domain validation is sound against a stated attacker (from finding 10)
- What it is: before issuing a certificate, a CA checks the domain from several network locations and requires k of n to agree.
- Going wrong: a nameserver hijack fools every vantage point at once (finding 10).
- Property: given a dependency graph (vantage points → resolvers → nameservers → web server, with routes), no attacker who controls fewer than some set of routes gets k matching wrong answers.
- Why formal: rules are being written now (five vantage points from Dec 2026, per a snippet). Whether a given k-of-n rule actually resists a given attacker is a small combinatorial question that a solver answers exhaustively.
- Why unusual: it is a web-PKI rule, not code, and we found no formal model of the quorum logic.
- Prior work: the arXiv 2302.08000 measurement; nothing formal found.
- First step: encode the dependency graph and attacker in SMT, then ask for the smallest route set that defeats a 5-perspective, 2-may-fail rule.

Runners-up (opinion): QUIC ECN validation (finding 9) is a clean state machine but low impact, and the HTTPS-record client procedure (finding 6) is formalizable but is closer to conformance testing.

## What we do not know
- Whether the advisors consider consent signals (target A) "web" enough or too policy-flavored.
- Whether "no formal model found" holds. That comes from search results, not an exhaustive literature review.
- Two venues are unconfirmed: finding 10 (USENIX Security 2023) and the PortSwigger paper.
- Not covered, because the search found nothing in range: bounce tracking, cookie syncing, HSTS preload, IDN homographs, web push, OCSP/ACME.
