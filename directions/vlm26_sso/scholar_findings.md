# Scholar findings: SSO logout/revocation consistency and refresh-token rotation races

(authored by agents unless marked 🧑)

Legend: [READ] = text read in the PDF/abstract page. [SNIPPET] = only seen in a Google Scholar result snippet (not verified in the paper).
Scholar budget: 10 fetches used. No CAPTCHA seen (challenge_action_required=false every time). Raw outputs: q1.txt .. q10_noyear.txt, q8_cites_ghasemisharif2022.txt in this directory.

## Queries run (all via pb-browser-page-extract; as_ylo=2022 unless noted)
1. single logout OpenID Connect back-channel logout session revocation
2. refresh token rotation reuse detection race condition concurrent tabs
3. formal analysis single sign-on logout session management ProVerif OR Tamarin
4. Shared Signals CAEP continuous access evaluation session revocation
5. "Single Sign-On" "Single Sign-Off" account takeover logout session not terminated measurement
6. third party cookies blocking silent authentication SSO iframe prompt=none Safari ITP breaks (0 results)
7. formal verification OAuth OpenID Connect logout token revocation model refresh token
8. cites=8840205349185279755 (Cited by, Ghasemisharif et al. S&P 2022), as_ylo=2022
9. third-party cookie blocking breaks single sign-on silent login iframe
10. formal model single sign-on "logout" session management OAuth OpenID Connect web infrastructure model security analysis (no year filter)
Plus curl of arXiv 1704.08539, arXiv 2608.04115 and par.nsf.gov/servlets/purl/10339713 (no Scholar budget).

## Part 1: evidence of harm, 2022-2026

### 1.1 Ghasemisharif and Kanich, "Towards automated auditing for account and session management flaws in single sign-on deployments", IEEE S&P 2022. [READ]
URL: https://par.nsf.gov/servlets/purl/10339713 (Scholar: Cited by 50)
Quote: "After the revocation process, only 68 RPs showed a logout behavior. By comparing these RPs with our extended group, we found that in 60 RPs the logout behavior was caused by cookie expiration and only 8 RPs actually exhibited the logged out behavior due to access revocation."
Quote: "We also note that 318 RPs continued accepting cookies 10 days after revocation."
Quote (method): "If the logout is successful, we use the (invalidated) cookies in a fresh browser and visit the RP"
Shows: after IdP-side revocation, only 8 RPs actually cut access (zombie sessions at RPs). Direct follow-up to the 2018 paper.
Does not cover: no fix or protocol/formal model; measures RP behaviour on a fixed sample, not propagation timing; no refresh tokens or tab races.

### 1.2 Ghasemisharif, "Exploring the Security Implications of Single Sign-On Deployments in the Wild", PhD thesis, UIC, 2023. [SNIPPET]
URL: https://indigo.uic.edu/articles/thesis/Exploring_the_Security_Implications_of_Single_Sign-On_Deployments_in_the_Wild/25392838/1/files/44992162.pdf
Snippet: "a universal revocation method, Single Sign-Off, to revoke access … extension to OpenID Connect to support single sign-off by … The back-channel logout proposal is also more flexible than …"
Not covered: thesis not opened; likely repeats 2018/2022 work.

### 1.3 Ghasemisharif et al., "O Single Sign-Off, where art thou?", USENIX Security 2018 (baseline, not new). [SNIPPET]
URL: https://www.usenix.org/system/files/conference/usenixsecurity18/sec18-ghasemisharif_0.pdf
Snippet: "propose Single Sign-Off, an extension to OpenID Connect for … The back-channel logout proposal is also more flexible than …"

### 1.4 Lee, Choi, Yoon, Kim, "An empirical analysis of incorrect account remediation in the case of broken authentication", IEEE Access 2023 (Cited by 10). [SNIPPET]
URL: https://ieeexplore.ieee.org/ (title search; no direct URL captured)
Snippet: "Single Sign-On (SSO) allows users to access multiple ser… a session lasts before users log out or how the server issues … need for robust account takeover prevention and remediation."
Not covered: unverified; relevance to SSO remediation unclear from snippet.

### 1.4b Bhattacharya, Bellini, Ristenpart, Dell, "Evaluating Ongoing Access Attacks on the Web", 2026 (nixdell.com). [SNIPPET]
Snippet: "of access routes, including single-sign on, passkeys, recovery … to sign out of the mobile app using session sign-out functionality (…"
Not covered: unread; looks like remediation/ongoing-access study; check if it finds sign-out not revoking SSO-derived sessions.

### 1.5 Giacomello, Lassak, Hielscher, Golla, "Exploring the Complexities of Passkey Revocation (Extended Version)", 2026. [SNIPPET]
Snippet: "changing passwords and expiring sessions remains … to log out of a public computer (Public Computer), sharing an …"
Not covered: passkeys, not SSO/OIDC.

### 1.6 Zhou, Guo, Grishchenko, Lie, "PORTA: Systematic Discovery of Vulnerabilities in Identity Brokers", 2026 (Toronto). [SNIPPET]
Snippet cites: "single sign-off, where art thou? an empirical analysis of single sign-on account hijacking and session …". Impact stated: "account takeover for any local Logto account whose email is registrable on …"
Not covered: broker bugs; no logout propagation seen.

### 1.7 Jannett, Westers, Wich, Mainka et al., "SoK: SSO-Monitor", IEEE EuroS&PW 2024 (Cited by 37); Innocenti et al., "Only as Strong as the Weakest Link: On the Security of Brokered SSO on the Web", IEEE S&P 2025; Westers et al., "SSO privacy: we still know what you did last summer", 2024. [SNIPPET]
URLs: sso-monitor.me; innotommy.com; sso-privacy.me (from Scholar)
Snippets: "in 2024 due to Chrome's third-party cookie phaseout [32]" (SoK); "the ongoing deprecation of third-party cookies on SSO (§6.4)" (privacy).
Not covered: none of the snippets mention logout or revocation; third-party-cookie effect appears only as a measurement caveat.

### 1.8 Bahrami, Fass, Shafiq, "Characterizing and Isolating the First-Party Cookie Jar", ACM CCS 2025 / arXiv 2406.05310. [SNIPPET]
URL: https://arxiv.org/abs/2406.05310
Snippet: "overhead of 0.3 seconds and breaks Single Sign-On on 11% of …"
Relevance: a cookie-isolation defence breaking SSO on 11% of sites, i.e. cookie policy can silently break SSO. Not about third-party cookie blocking per se, nor sign-out.

### 1.9 Refresh-token rotation races (harm = random sign-outs)
a) Teodori, "NEBULA: A Language-Independent Specification for Opaque Rotating Refresh Tokens", arXiv 2608.04115, 2026. [READ]
URL: https://arxiv.org/abs/2608.04115
Quote: "two refreshes of one token execute concurrently; this is not an exotic capability but the default behaviour of retrying mobile clients and multi-tab browsers."
Quote: "a compare-and-set rotation contract that closes a reproducible bypass of reuse detection under concurrent refresh"
Shows: concurrent rotation is a recognised spec-level issue (here the bypass direction, i.e. security). It also has a lost-response retry "grace" path and lineage revocation on reuse.
Does not cover: single token store only; no multiple relying parties, no logout propagation, no formal proof (conformance tests only: 38 scenarios); does not measure user-visible random sign-outs from the reuse-detection false positive.
b) Arella, Malaraju, "Secure Session Management in MERN Stack Applications Using Token Rotation and Refresh Strategies", IEEE conf 2025 (Cited by 1). [SNIPPET]
Snippet: "expose race conditions in scenarios where multiple tabs of … rotating refresh tokens and reuse detection … due to token invalidation during concurrent refresh attempts,"
c) Andrushchak, Kupyra, "Authentication and session management in modern web applications using JWT with rotating refresh tokens", 2026. [SNIPPET]
Snippet: "refresh-in-progress promise to coalesce concurrent refresh"
Not covered (b, c): low-tier venues; unread; no measurement of real-world frequency.
Nothing found: no peer-reviewed measurement of how often refresh-token-rotation races log users out in production.

### 1.10 Third-party-cookie blocking breaking silent SSO
Query 6 returned zero results; query 9 found only the items in 1.7/1.8 plus Clarke 2024 "Tracking Third-Party Cookies" (York St John, thesis, [SNIPPET]: "known as the third-party domain"). Nothing found that measures silent-auth/prompt=none breakage under 3PC blocking. Gap.

### 1.11 CAEP / Shared Signals and revocation propagation
a) Hilbig, Serzantov, Schreck, "Protect the Gate - Not Only Once: Continuous Access Evaluation in Practice", 2023 7th Cyber Security in Networking Conf (Cited by 3). [SNIPPET]
Snippet: "CAEP defines five Event types that relate to sessions and devices: The Session Revoked Event signals the revocation …"
b) Liu, Yu, Zhang, "Revocation Is Not Complete at Receipt: An Executable Outcome Contract for Distributed Agent-Tool Gateways", arXiv 2610.15991, 2026. [SNIPPET]
URL: https://arxiv.org/abs/2610.15991
Snippet: "Evaluating only the earlier stages can hide a stale gateway; … transmitter provides signed CAEP session-revoked SETs over RFC …"
Relevance: same concept (receipt of revoke event is not enforcement) but for agent-tool gateways, not user SSO.
c) Stöcker, "Runtime Revocation in Multi-Agent Systems: Protocol Verification and Evaluation of Privacy and Containment", 2026 (spherity.github.io). [SNIPPET] Verification claimed in title; domain is agents.
Not covered (a-c): no measurement of real CAEP deployment or receiver lag; none is OIDC logout. Little academic evidence of CAEP deployment harm was found.

### 1.12 Non-paper
Wilson, Hingnikar, "Logout" chapter, Springer 2022 (book on OAuth 2, OIDC, SAML 2). [SNIPPET] "back-channel logout may not be implemented in all SAML 2 …". Practitioner statement that SLO support is uneven.

## Part 2: prior formal work

### 2.1 Fett, Küsters, Schmitz, "The Web SSO Standard OpenID Connect: In-depth Formal Security Analysis and Security Guidelines", IEEE CSF 2017. [READ] https://arxiv.org/abs/1704.08539
Quote: "We do not model less used features, in particular OIDC logout, self-issued OIDC providers"
Quote: "Since the FKS model has no notion of time, we overapprox-" (sic, cut at line end; rest of sentence not captured). Meaning: no expiry/time modelling.
Not covered: logout, time/expiry, revocation, propagation across several RPs, refresh tokens.

### 2.2 Fett, Küsters, Schmitz, "A Comprehensive Formal Security Analysis of OAuth 2.0", ACM CCS 2016. [SNIPPET] https://arxiv.org/abs/1601.01229
Snippet: "registration, signing and encryption of messages, and logout. In … Dolev-Yao style model of the web infrastructure" (listed among things not modelled, per context).
Not covered: logout (as above); refresh-token rotation (not in 2016 OAuth 2.0 core).

### 2.3 Sommer, "Formal security analysis of the Shibboleth Web Single Sign On System using a comprehensive model of the web", Univ. Stuttgart thesis, 2020. [SNIPPET]
URL: https://elib.uni-stuttgart.de (Scholar-listed)
Snippet: "to formalize Single Logout protocols, defines some security …" (context unclear; could be the thesis stating SLO is out of scope or future work).
Not covered: unread; SAML SLO status unverified.

### 2.4 Cai et al., "Formal analysis of CAS under malicious service providers: Implications for trust-aware deployments", Computers & Security 2026 (and SSRN 6465622). [SNIPPET]
Snippet: "We develop a Tamarin model of the CAS authentication … ’s global session and optionally send logout notifications to all …"
Interpretation (inference): CAS single logout is described in the background; it is unclear whether the Tamarin model checks logout properties. Needs reading.

### 2.5 Vasudevan, "Formal analysis and verification of OAuth 2.0 in SSO", Aalto thesis 2023 (Cited by 1). [SNIPPET]
Snippet: "OAuth provides the flexibility for users to easily revoke … The tools used for conducting the formal verification in this investigation …". Unread; revocation coverage unknown.

### 2.6 Others seen, probably not relevant
"Integrating single sign-on within the WebAuthn framework" (BRAC thesis 2026, Tamarin; snippet "of the session is safely deleted on logging out"); Modesti et al., "Cyber Security and Applications" (Newcastle, ProVerif; "if session tokens are not invalidated after logout"); Hermenius and Olofsson, "Formalizing and Evaluating mAuth" (Chalmers; "A mismatch aborts the session and triggers a revocation call"). All [SNIPPET], unread, small scope.

### 2.7 Survey
Schäberle, "Overview on web authentication and authorization protocol security evaluations", Univ. Stuttgart thesis 2025. [SNIPPET] Surveys formal models of OAuth/OIDC; not read.

## Not found (explicit)
- No formal model (ProVerif/Tamarin/TLA+/WIM/Verus etc.) found that covers OIDC back-/front-channel logout, SAML SLO, token revocation propagation to multiple RPs, or refresh-token rotation with concurrency. Candidates 2.3-2.5 need reading to rule out.
- No measurement paper found on random sign-outs from refresh-token rotation races, nor on 3PC blocking breaking silent SSO.
- No paper found measuring CAEP/SSF receiver deployment lag.
- Scholar coverage is limited to 10 fetches; arXiv/IEEE/ACM full-text search was not used.
