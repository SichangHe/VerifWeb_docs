# VLM42 Shibboleth/SSO web findings

(authored by agents unless marked 🧑)

Method: public web only, no USC system probed. Quotes came through WebFetch/WebSearch, which summarize pages with a small model; quotes marked [S] are search-summary text, not page-verified. Tags: FACT = quoted source says it; INFER = my inference. Not fetched/blocked: eduroam.org BlastRADIUS statement (403), Jisc advisory (403), Internet2 MDQ wiki (empty), IdP5 LogoutConfiguration page (only search snippets).

## 1. USC SSO

- FACT USC is an InCommon member. "USC is a member of the InCommon Federation." https://shibboleth.usc.edu/docs/sp/install/
- FACT Logout guidance from USC: "The current version of Shibboleth does not support single logout"; "The only way for a user to completely log out of all Shibboleth services is to close their browser." Same URL. (INFER: page is old; may be stale vs IdP 3.2+ SLO.)
- FACT Test IdP does not check SP certs: "the Test Identity Provider does not actually authenticate Service Providers with the SSL certificate they present." Same URL.
- FACT Attribute release differs test vs prod: "the attributes your application receives will likely differ from those you received from the Test IdP." Entitlements "will begin with urn:mace:usc.edu:gds:entitlement". Same URL.
- FACT SP entityID convention: "https://www.usc.edu/department-name/application-name/shibboleth-sp". Same URL.
- FACT Duo: "Duo is free and required for all current USC NetID owners, whether faculty, staff, students, or affiliates." https://itservices.usc.edu/duo/ . Also "USC is retiring Duo Voice authentication for students, faculty, and staff".
- FACT Login is changing: USC will launch "an updated login experience for users accessing USC systems starting Nov. 19." "you will be prompted to sign in via two steps instead of one." https://itservices.usc.edu/2026/10/26/entra-login-page-rolls-out-nov-19/ . Page links an "Entra SSO FAQs [PDF]"; page says nothing on Shibboleth, Duo or logout. Earlier: login ID format becomes NetID@usc.edu on July 30 [S] https://itservices.usc.edu/2026/07/01/your-usc-netid-login-format-is-changing/
- INFER Entra login page on Nov 19, 2026 (9 days from today) suggests the front end/IdP is changing or being fronted by Microsoft Entra; whether Shibboleth IdP stays behind it is NOT FOUND.
- NOT FOUND: USC IdP entityID value, IdP software version, whether USC IdP does SLO, attribute list for production, in any public page I reached. (Check InCommon metadata/MDQ for the entityID; not done.)

## 2. SAML SLO in Shibboleth

- FACT Design-level fragility (Shibboleth concepts page): "If the SP is not responsive the process breaks down and the remaining SPs will not receive logout requests." "In the event that a SP is not responsive the user will be presented with an HTTP error." "In almost all failure cases the sensible thing would be to tell the user to close their browser." "only SAML 2 supports single logout." https://shibboleth.atlassian.net/wiki/spaces/CONCEPT/pages/928645229/SLOIssues
- FACT IdP v3: "Single Logout (SLO) support is new in 3.2.0." "SLO is a best-effort attempt to end relying party sessions without clearing the browser's cookie and storage state." https://shibboleth.atlassian.net/wiki/spaces/IDP30/pages/2499805694/LogoutConfiguration (IdP3 is EOL per page banner.)
- FACT [S] IdP v3 interop warning: "SLO is in general vastly less interoperable than SSO in SAML" (same URL, from search snippet only).
- FACT [S] IdP5: "The IdP supports reception of either type of request, but use of SOAP obviously requires server-side session state." https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199510118 . Back-channel needs server-side session store, "which is not the default, and greatly complicates clustering" (search summary of https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199500736/SecurityAndNetworking).
- FACT [S] Propagation needs idp.session.trackSPSessions, default false (IdP5 LogoutConfiguration).
- FACT No SP logout CVE found. SP advisories 2025: 13 Mar (forged signed SAML messages via non-XML-signature bindings, fix OpenSAML C++ 3.3.1) https://shibboleth.net/community/advisories/secadv_20250313.txt ; 3 Sep CVE-2025-9943 SQLi in ODBC replay store, SP <=3.5.0, fix 3.5.1 [S] https://shibboleth.net/community/advisories/secadv_20250903.txt
- FACT Mar 2025 advisory touches logout config: "You can keep logout working by removing HTTP-Redirect from the SP metadata so IdPs use HTTP-POST instead." (workaround side effect of removing SimpleSigning rule).
- FACT [S] IdP5 advisories (https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199512795/SecurityAdvisories): 2024-03-20 CAS SSRF CVE-2024-22259/22262 (<5.1.2); 2025-03-26 forged SAML messages (<5.1.4); 2025-08-26 CAS XSS (fix 5.1.6); 2026-05-13 DoS via memory/CPU exhaustion decoding SAML/SOAP messages (https://shibboleth.net/community/advisories/secadv_20260513.txt, not fetched).
- NOT FOUND: specific Jira issues on SLO failures (not searched deeply); IdP4 page. INFER: SLO failure modes most relevant to a "log out of USC but still signed in elsewhere" bug are non-responsive SP, missing SingleLogoutService in metadata, unsigned logout messages, SP sessions not tracked.

## 3. InCommon metadata/MDQ

- FACT Aggregate size: "The InCommon “main” metadata aggregate is now almost 70MB in size, and requires several gigabytes of memory to parse." "This results in enormous memory footprints and lengthy start-up times for your SAML software." https://lists.incommon.org/sympa/arc/inc-ops-notifications/2020-02/msg00001.html
- FACT MDQ purpose: "MDQ prevents your software from using these resources by allowing it to only fetch the metadata it needs, when it needs it." Same URL. Adopting needs "a new public key."
- FACT [S] 2018 thread "InCommon metadata aggregate exceeds 50MB" http://shibboleth.net/pipermail/users/2018-March/039773.html
- FACT [S] MDQ key differs from legacy: "not the same certificate that was used for the legacy aggregates from md.incommon.org" https://spaces.at.internet2.edu/display/MDQ/production-mdq-signing-key (not page-verified).
- FACT [S] Legacy md.incommon.org retirement date moved from 2025-01-20 to 2025-02-25; search summary says legacy aggregate "expired on March 31, 2025, and some organizations had SSO problems." Source URLs not identified; treat as unverified.
- NOT FOUND: any MDQ signing-key rollover after 2020; any named InCommon outage incident page; current MDQ aggregate size.
- INFER: a SP/IdP still pinned to the legacy key/aggregate after March 2025 would fail to refresh federation metadata; unverified for USC.

## 4. eduroam/RADIUS

- FACT [S] Jisc advisory 2024-07-09 says BlastRADIUS (CVE-2024-3596) does not affect eduroam traffic because eduroam uses EAP; Message-Authenticator enforcement partly mitigates. https://community.jisc.ac.uk/library/network-and-technology-service-docs/2024-07-advisory-mitigating-blastradius-enforcing-use (403 on fetch; eduroam statement https://eduroam.org/eduroam-response-to-the-blastradius-vulnerability/ also 403). Paper: https://www.blastradius.fail/
- FACT [S] RadSec/TLS is not affected; fix is RADIUS/TLS or DTLS plus Message-Authenticator.
- FACT Cert-validation incidents are common, from the GEANT cat-users list: cross-signed chain broke Windows 11 clients after CA swap (Oct 2025) https://lists.geant.org/sympa/arc/cat-users/2025-10/msg00034.html ; stale cert in CAT profile after renewal (2024) https://lists.geant.org/sympa/arc/cat-users/2024-03/msg00022.html ; TLS 1.3 EAP failures on Windows 11 22H2 (2022) https://lists.geant.org/sympa/arc/cat-users/2022-10/msg00040.html ; UW eduroam drop from RADIUS issue (June 2022) https://mailman22.u.washington.edu/pipermail/eoutage/2022-June/000004.html . Quotes not verbatim (summaries only).
- INFER: eduroam weakness is client-side CA pinning; clients that accept any cert prompt are open to rogue-AP credential theft. Source summary states the click-through risk; no USC-specific eduroam fact found.
- NOT FOUND: USC eduroam incident or config.
