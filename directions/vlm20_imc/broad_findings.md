# broad findings (web, excluding tracking/cookies/consent, caches/CDNs/URL parsing)
(authored by agents unless marked 🧑)

Method: web search, then full text of each paper read via pdftotext (extracts in txt/).
Quotes are verbatim from the PDFs. "Prior formal work" entries come from my own
memory unless a URL is given; treat them as unverified leads.
Search coverage was thin: no hits for HSTS preload, IDN, web push, ACME, or time
papers from 2023-26, so none are included.

## 1. QUIC servers echo ECT(1) when sent ECT(0)
- venue: IMC 2023, "ECN with QUIC: Challenges in the Wild" (Sander, Kunze, Blöcher, Kosek, Wehrle)
- url: https://arxiv.org/abs/2309.14273
- quote: "The remaining 301.72 k / 17.15 k domains (∼31 % / ∼35 %) failed ECN validation due to mirroring ECT(1) instead of the originally sent ECT(0) codepoints."
- also: "We observe that less than 2% of QUIC hosts, providing less than 0.3% of HTTP/3 websites, pass this validation." (abstract)
- explanation: QUIC peers report in ACKs how many packets arrived with each ECN codepoint. A sender checks those counts to decide whether the path is safe for ECN. Many servers report wrong counts, either fewer than were sent (undercount, ~65% of failures) or ECT(1) in place of ECT(0). The authors guess an ECT(0)/ECT(1) bit mix-up in the QUIC implementations (2 = 0b10 vs 1 = 0b01).
- rule violated: RFC 9000 s13.4.2 (ECN validation): the ACK-reported ECT(0)/ECT(1)/CE counts must match the codepoints actually sent and may not decrease. The failing servers are the ones breaking the reporting side.
- CVE: none.
- prior formal work: Ivy-based formal spec and testing of QUIC (McMillan and Zuck, SIGCOMM 2019; from memory). I do not know whether it covers ECN counts. Gap: checking the validation state machine against real implementations' ACK_ECN output.

## 2. ECH and HTTPS-record breakage: stale hints, key rotation, a global ECH shutoff
- venue: IMC 2024, "Exploring the Ecosystem of DNS HTTPS Resource Records" (Dong, Zhang, Lee, Huque, Sun)
- url: https://arxiv.org/abs/2403.15672
- quote 1: "For example, the frequent ECH key rotation every 1 to 2 hours requires the server to properly implement retry mechanisms [39] to avoid breaking the connection due to expired keys."
- quote 2: "Furthermore, the lack of support for ECH Split Mode leads to such failures across all major browsers, prohibiting clients from establishing connections to the server even when ECH is correctly configured by the server."
- quote 3: "We identify a total of 1,022 occurrences of domains exhibiting IP mismatches (a domain is counted multiple times if it displays mismatched IP addresses on different days), of which 317 are distinct domain names."
- explanation: An HTTPS record carries IP hints and the ECH public key. Domains must keep these in sync with their A/AAAA records and with DNS cache lifetimes, or browsers fail to connect. Cloudflare turned ECH off for all its domains on 2023-10-05 "due to a number of issues" (the paper's reading of Cloudflare's announcement). Browsers have no failover for several misconfigurations.
- rule violated: ECH retry/key-rotation rule: the server must still accept the previous ECHConfig while resolvers may serve cached HTTPS records. RFC 9460 expects hints to be consistent with address records, and clients should fall back to A/AAAA when the service endpoint fails.
- CVE: none.
- prior formal work: ProVerif analysis of TLS 1.3 + ECH privacy (Bhargavan, Cheval, Wood, CCS 2022; from memory). It models the cryptographic handshake, not the DNS-cache/rotation/failover state machine. That part looks unmodeled.

## 3. HTTP/2 push and Signed Exchanges let any domain in a shared certificate act as same-origin
- venue: NDSS 2025, "Cross-Origin Web Attacks via HTTP/2 Server Push and Signed HTTP Exchange" (Chen et al., Tsinghua)
- url: https://www.ndss-symposium.org/wp-content/uploads/2025-1086-paper.pdf
- quote: "Combining these two characteristics, a domain can spoof the origin of another domain within the SAN list of TLS certificates to deliver resources and browsers will accept them as legitimate same-origin resources."
- also: "Our client-side measurement results show that: (1) 11 out of 14 popular browsers, including Chrome and Edge, are vulnerable to at least one of our attacks"
- explanation: The same-origin policy uses scheme, host and port. HTTP/2 and HTTP/3 "authority" is looser: any name in the server certificate's SAN counts. So a server that shares a certificate with a victim domain can push a script that the browser files under the victim's origin. This bypasses CSP and enables XSS and cookie writes. The paper shows shared certificates are easy to get via domain reselling or takeover, and are hard to revoke.
- rule violated: SOP origin (scheme, host, port) versus RFC 9110 authority (SAN match). The authority check is weaker than the origin check, and push and SXG let the pusher choose the origin.
- CVE: none found in the text; Huawei, Baidu, Microsoft acknowledged, Google "still in" discussion.
- prior formal work: Web Infrastructure Model (Fett, Küsters, Schmitz) models browsers and OAuth. I know of no model of server push or SXG, nor of authority versus origin. This is a good fit for a small model checker: two relations (authority, origin) and one acceptance rule.

## 4. OAuth integration platforms do not tell apps apart (cross-app account takeover)
- venue: USENIX Security 2025, "Universal Cross-app Attacks: Exploiting and Securing OAuth 2.0 in Integration Platforms" (Luo et al., CUHK and Samsung)
- url: https://www.usenix.org/system/files/usenixsecurity25-luo-kaixuan.pdf
- quote: "Our measurement study reveals that among 18 popular consumer- or enterprise-facing integration platforms, 11 are vulnerable to COAT and another 5 to CORF, including those built by Microsoft, Google and Amazon."
- explanation: Platforms such as workflow automation and smart-home hubs let third-party apps link a user's account via OAuth. The platform's OAuth architecture does not separate the apps. A malicious app, or a crafted link, can therefore make the platform issue or accept authorizations meant for another app. One case compromised a major ecosystem in a single click.
- rule violated: OAuth's binding of authorization (code/state/redirect) to one specific client. The platform acts as one client for many apps, so the binding is lost. The paper's testing tool tracks the flow with a state machine.
- CVE: CVE-2023-36019 (CVSS 9.6, Microsoft).
- prior formal work: Fett, Küsters, Schmitz, "A comprehensive formal security analysis of OAuth 2.0" (CCS 2016, cited in this paper). It assumes one client identity per app. The multi-app platform-as-client case seems not modeled.

## 5. Passkeys cannot be revoked at some sites
- venue: USENIX Security 2025, "The Case of Passkeys in Interpersonal Threat Models" (Daffalla et al.)
- url: https://www.usenix.org/system/files/usenixsecurity25-daffalla.pdf
- quote: "Neither CVS nor Porkbun provides service ASIs supporting revocation, meaning there is no way for users to revoke passkeys."
- also: "For example, one is an adversary using local access to add their biometrics to a victim device in order to retain illicit access to an account."
- explanation: With a passkey, whoever can unlock the device can log in. Services differ on whether a user can list and delete passkeys. Some give no way at all, so a person with brief physical access keeps durable access. The paper reports this across 12 services.
- rule violated: no hard spec rule; WebAuthn leaves credential management to the relying party. Candidate invariant: every registered credential is listable and deletable, and registration/removal notifies the user.
- CVE: none.
- prior formal work: FIDO2 provable security (Bindel et al., S&P 2023, from memory). It covers authentication, not credential lifecycle or recovery invariants. Weakest fit for formal verification of the eight.

## 6. Bytespider reads robots.txt and ignores it; AI search crawlers rarely check it
- venue: IMC 2025, "Somesite I Used To Crawl: Awareness, Agency and Efficacy in Protecting Content Creators From AI Crawlers" (Liu, Luo, Shan, Voelker, Zhao, Savage)
- url: https://arxiv.org/abs/2411.15091
- quote: "Perhaps surprisingly, though, only one major AI data crawler (Bytespider) does not respect it."
- companion: IMC 2025, "Scrapers Selectively Respect robots.txt Directives" (Kim et al.), https://arxiv.org/abs/2505.21733. From its abstract (via search snippet, not the full text): bots are less likely to comply with stricter directives, and some categories, including AI search crawlers, rarely check robots.txt at all.
- explanation: Controlled test sites served distinct robots.txt files and logged who obeyed. The many sites that block AI crawlers rely entirely on voluntary compliance. Hosting platforms often do not let users edit robots.txt at all (the paper's table, e.g. Squarespace, Artstation).
- rule violated: RFC 9309 (Robots Exclusion Protocol) crawler obligation to honor disallow rules.
- CVE: none.
- prior formal work: none known to me. Compliance is a trace property over server logs. It is checkable from logs, but is not a protocol state machine.

## 7. Third-party CT monitors return incomplete certificate sets
- venue: NDSS 2024, "Certificate Transparency Revisited: The Public Inspections on Third-party Monitors" (Sun et al.)
- url: https://www.ndss-symposium.org/wp-content/uploads/2024-834-paper.pdf
- quote: "For example, recent studies [32], [33] reported that 5 popular third-party CT monitors cannot always return the complete set of certificates inquired by users, which fundamentally impairs the protection that CT aims to offer."
- also: "the prototype detected 14 potential design or implementation issues of these monitors" (6 monitors, 52 days, 8.26M certificates)
- explanation: CT only protects a domain owner if monitors reliably show every logged certificate. Monitors are not specified or checked by anything. The authors cross-compare monitors' search answers and find disagreements caused by misconfiguration and implementation flaws.
- rule violated: the monitor completeness property that CT relies on (every certificate in a log appears in a search answer). RFC 6962 does not define monitor behavior, so this is a missing spec as much as a violated one.
- CVE: none.
- prior formal work: search found an arXiv accountability model of CT with merge delay (arXiv 2609.11552, "Accountability in Certificate Transparency and Variants"; I did not read it, and the ID looks odd, so verify it exists). Monitor completeness seems less covered.

## 8. Multi-vantage-point domain validation is weakened by nameserver hijacks
- venue: USENIX Security 2023 per my memory (arXiv 2302.08000; PDF has no venue), "How Effective is Multiple-Vantage-Point Domain Control Validation?" (Cimaszewski, Birge-Lee, Wang, Rexford, Mittal)
- url: https://arxiv.org/abs/2302.08000
- quote: "By hijacking traffic to a victim's domain during domain control validation, an adversary can fool a CA into signing a certificate on behalf of the adversary for a domain the adversary does not control [11]."
- also (search snippet, unverified in text): multiVA gives 88% median resilience against BGP hijacks versus 76% for single-vantage validation. I did not read the "novel technique to force all of ..." attack (the sentence is cut in the extract).
- explanation: Let's Encrypt validates domain control from several network locations so one BGP hijack cannot fool it. The paper models hijacks of the domain's DNS nameservers too, and RPKI, not just of the web server. That shrinks the protection. From 2026-12-15 CA/B Forum rules require five remote perspectives (search snippet).
- rule violated: CA/B Forum BR 3.2.2.4 domain validation. The defence's assumption that hijacks affect only some vantage points fails when the shared nameserver path is hijacked.
- CVE: none.
- prior formal work: none known for MPIC quorum/corroboration logic. It is a small, checkable quorum protocol (k-of-n agreement under an attacker controlling a subset of routes). Good fit.

## Ranking for formal verification (my opinion)
Best: 3 (authority vs origin), 4 (OAuth multi-app binding), 8 (MPIC quorum), 1 (ECN validation), 2 (ECH rotation/failover).
Less suitable: 7 (missing monitor spec), 5 (policy, not a rule), 6 (log-trace compliance).

## Not found / caveats
- No in-range paper found on HSTS preload, IDN homographs, web push, OCSP stapling, ACME, or clock errors. The only clock item was a Chromium issue tracker bug (an on-path delay of a Variations Seed response skews NetworkTimeTracker into the past, so expired certificates pass); not academic, not verified, so excluded.
- Google Scholar and pb-browser-page-extract were not used.
