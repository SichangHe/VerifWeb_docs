# Shibboleth/InCommon as a verification target (cardi's comment)
(authored by agents unless marked 🧑)

Follows up cardi's comment on the VerifWeb memo: "What about looking at USC's SSO, Shibboleth? There's also the InCommon Federation ... how they delegate authentication for the eduroam WiFi ... I looked at campus/enterprise SSOs a while ago: there weren't too many papers around that".
Evidence, with verbatim quotes and URLs: web_findings.md and scholar_findings.md in this folder. Quotes marked [S] there come from search snippets, not checked against the page.

## Verdict (opinion)

Campus SAML is a narrower and less crowded target than OIDC. It is a better target only if we pick the parts nobody has formalized: single logout (SLO) and federation metadata trust. SAML login itself has already been modeled several times. My recommendation is SLO plus metadata/MDQ trust, framed as "federated session and trust state". I don't know whether that has enough systems content for the advisor; that is a judgment call for the human.

## How USC's setup works (facts, public docs only)

- USC runs Shibboleth and joined InCommon. From USC's SP install guide (https://shibboleth.usc.edu/docs/sp/install/): "USC is a member of the InCommon Federation".
- The same guide says: "The current version of Shibboleth does not support single logout." The page looks old, so this may be stale.
- Duo MFA is required for all NetID owners (https://itservices.usc.edu/duo/).
- USC switches to a new Microsoft Entra sign-in page on Nov 19, 2026 (https://itservices.usc.edu/2026/10/26/entra-login-page-rolls-out-nov-19/). That page does not say whether Shibboleth stays behind Entra.
- Not found: USC's IdP entityID, its IdP version, or any USC statement on logout for the current IdP.

## Where it breaks

1. SLO is fragile by design (fact). Shibboleth concepts page: "If the SP is not responsive the process breaks down and the remaining SPs will not receive logout requests." SLO is best-effort in IdP v3. In IdP v5, back-channel (SOAP) logout needs server-side sessions. ("SP" means service provider: the app that accepts the login.)
2. Federation metadata is heavy and its signing key is critical (fact). InCommon, 2020: the metadata aggregate was "almost 70MB in size, and requires several gigabytes of memory to parse". The fix was MDQ, a per-entity metadata query service signed with a separate key. I found no named MDQ outage or incident write-up.
3. Shibboleth security advisories concern signatures and storage, not logout (fact). 2025 SP advisories: forged signed SAML messages (March) and CVE-2025-9943, an SQL injection in the ODBC replay store (September). I found no logout CVE.
4. eduroam fails mostly through configuration (fact, but summaries only). The GEANT CAT list shows repeated certificate failures: CA swaps, cross-signed chains on Windows 11, stale certificates, TLS 1.3. Jisc says BlastRADIUS (CVE-2024-3596) does not affect eduroam because eduroam uses EAP. That is a search summary; the pages returned 403.

## Literature: is cardi right? (inference from 10 Scholar queries, not exhaustive)

- Wrong for SAML login in general. At least five formal models exist: Armando et al. 2008 (AVISPA, attack on Google's SAML SSO), a 2020 ProVerif paper, Sommer 2020, Anić 2025 (Tamarin thesis), and Hartl & Derek, IEEE Access 2025 (Tamarin). Hartl & Derek: "We suggest a simple fix, and formally verify that it does indeed mitigate the discovered attack."
- Right for campus-specific topics.
  - Shibboleth SLO has one formal item, Sommer's Stuttgart master's thesis (2020). Its snippet reads: "the security of Single Logout protocols has not … to formalize Single Logout protocols".
  - I found no security analysis of InCommon or eduGAIN metadata trust.
  - CAS has one 2026 paper, seen by title only.
- eduroam/RADIUS is the exception: it is active. Goldberg et al., "RADIUS/UDP Considered Harmful", USENIX Security 2024 (BlastRADIUS), plus several credential-theft papers.

## What could be formally verified (opinion, ranked)

1. SLO propagation as a distributed protocol: IdP, N SPs, browser, with unresponsive SPs and message loss.
   - Property: after logout, no SP still accepts the old session, or the user is told which SPs failed.
   - Tools: TLA+/TLC for the protocol; Verus for an SP session-store core.
   - Why it fits: it is distributed state, it is best-effort today, and it matches the earlier tab-inconsistency finding (../vlm41_sso/REPORT.md).
   - Gap: only one thesis covers it.
2. Metadata/MDQ trust pipeline: signature check, validUntil/expiry, caching, key rollover, fallback when MDQ is down.
   - Property: an SP never trusts an entity whose metadata is unsigned, expired or revoked, and keeps serving through MDQ outages within a bounded staleness.
   - Gap: no prior analysis found. Small, crisp state machine.
3. SAML assertion validation in an SP (signature wrapping, replay cache, audience/time checks).
   - Real bugs exist (the 2025 forged-message advisory). Crowded: XML signature wrapping is a well-studied attack class.
4. eduroam: RADIUS is already broken and being replaced by RadSec, and its failures are configuration. Low verification payoff.

## Versus OIDC (opinion)

OIDC has the Fett/Küsters/Schmitz web-model proofs and much more attention. Its logout specs have the same best-effort weakness. SAML/Shibboleth is less studied, local to USC (we have a real deployment to describe, though we must not probe it), and its SLO and metadata gaps are unclaimed. Against it: SAML is legacy, and USC is moving its front end to Entra, which may reduce relevance. I don't know whether Shibboleth will stay behind Entra.

## Gaps

- Paywalls or bot blocks stopped us from reading Sommer 2020, Hartl & Derek 2025 (open access; a human can fetch it), Armando 2008, the 2020 ProVerif paper and the Anić thesis. Quotes from those come from snippets.
- Shibboleth Jira SLO issues and IdP4 docs were not searched.
- Saved to paper_collection (not committed): Goldberg 2024, Fett OAuth 2016, Fett BrowserID 2015, Müller & Oupický 2024.
