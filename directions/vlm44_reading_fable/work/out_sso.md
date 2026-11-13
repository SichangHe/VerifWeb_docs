# SSO session and logout reading guide (group_sso)
(authored by agents unless marked 🧑)

Overall: only 26, 27, 84 measure logout or token invalidation on real sites. 83, 68, 69 are formal login proofs of models (hand proofs); 83 and 68 say they leave out logout and expiry. 81 is the only one that specifies revocation as state-machine logic, and it says it has no machine proof. 28, 70, 71 do not cover logout.

---
26 Measuring Improper Token Invalidation in Real-World Web Logins, Kazi Farhat Lamisa, Concordia University MASc thesis, 2024
- SHOWS: An automated black-box tool (LoginPlus) registered and logged into accounts on top-1M websites (Chrome UX Report list) and tested whether tokens and cookies still work after logout or after a password reset (measurement on real sites, no proof).
- QUOTE: "446 out of 520 websites (85%) tested for JWT invalidation do not invalidate JWTs included in requests after user logout." (Section 1.4, Contributions)
- WHY: Gives the best numbers on logout/token invalidation: 85% of 520 sites keep JWTs valid after logout; 9% of 5,642 sites (513) keep session cookies valid after logout, 203 still after 7 days; 54% (674/1,248) keep old sessions after password reset. It does not study SSO logout (Facebook/Google only appear in related work), so SSO-specific logout is still open.
- PRIORITY: high. Direct numbers on logout invalidation.
- READ: abstract, 1.4 contributions, RQ4 section (cookie logout results), conclusion, limitations. Chapter 3 (tool design) skimmed only. Note: only 520 of 1,616 JWT sites could be tested because automatic logout worked on few (limitation section).

---
27 Measuring Web Session Security at Scale, Stefano Calzavara, Hugo Jonker, Benjamin Krumnow, Alvise Rabitti, Computers & Security, 2021
- SHOWS: An automated crawler (Shepherd, extended to click logout) logged into 6,124 top sites (accounts from a public password database) and checked login, cookie and logout security (measurement on real sites, no proof).
- QUOTE: "469 (8%) sites do not terminate sessions at the server upon logout, while 230 (4%) sites do not remove security-sensitive information from the client after logout." (Section 1, Introduction)
- WHY: The earlier logout measurement that 26 repeats. On the 3,302 sites where logout worked, 18% (604) did not invalidate cookies within 5 minutes and 14% (471) still accepted them 10 days later. SSO is mentioned only as a way to log in, not tested, so SSO logout is a gap.
- PRIORITY: high. Baseline logout-failure rates, plain cookie sessions.
- READ: abstract, introduction, section 6 (logout security) results, conclusion. Other sections not read. Not clear to me from the text why the 8% (of all 6,124) and 14% (of 3,302) differ; check the paper before quoting one number.

---
28 Only as Strong as the Weakest Link- On the Security of Brokered Single Sign-On on the Web, Tommaso Innocenti, Louis Jannett, Christian Mainka, Maximilian Westers, Tobias Wich, IEEE S&P, 2025
- SHOWS: Black-box testing of "brokers" (services such as Keycloak, Cognito, Firebase that sit between a website and Google/Facebook login); found 25% of SSO websites use a broker, and vulnerabilities in over 50 brokers affecting over 2k websites (measurement and attacks on real services, no proof).
- QUOTE: "We expose vulnerabilities in over 50 brokers, compromising the security of more than 2k websites." (Abstract)
- WHY: Login flow only: redirect injection, account takeover, best-practice violations. My search of the text found no logout or revocation analysis, so it settles nothing for us except that Keycloak and Cognito are widely used and may be worth targeting as software.
- PRIORITY: low. Login-only, no logout.
- READ: abstract, introduction, keyword search for logout/revocation (none found). Evaluation details not read.

---
81 NEBULA- A Language-Independent Specification for Opaque Rotating Refresh Tokens, Matteo Teodori, arXiv, 2026
- SHOWS: A written specification of OAuth refresh-token rotation, reuse detection and revocation (by token, family, user), with ten reference implementations in ten languages that all run the same 38 test scenarios (a spec plus tests, not a machine-checked proof).
- QUOTE: "NEBULA's guarantees are argued, not machine-verified. Formal modelling of the rotation state machine and of its compare-and-set transitions—in Tamarin or ProVerif—...would, we believe, be prerequisites" (Section 7)
- WHY: The only paper here that spells out revocation and session lifetime logic (idle and absolute deadlines, family revocation, race under concurrent refresh that bypassed reuse detection). It also notes an attacker's own refreshes slide the idle clock, so only the absolute deadline bounds an abandoned session. Gives a ready state machine to verify; no proof exists yet. Single author, new, not a study of real deployments.
- PRIORITY: high. Revocation state machine, unverified.
- READ: abstract, introduction, sections 4 (state machine, revocation), 5 (security discussion, part), 7 limitations. Section 6 (conformance) skimmed.

---
83 The Web SSO Standard OpenID Connect- In-Depth Formal Security Analysis and Security Guidelines, Daniel Fett, Ralf Küsters, Guido Schmitz, arXiv, 2017
- SHOWS: A hand-written formal model of OpenID Connect in the authors' web model (FKS) and a manual proof of authentication, authorization and session-integrity properties (a model of the standard, not real code, no tool).
- QUOTE: "We do not model less used features, in particular OIDC logout, self-issued OIDC providers" (model scope section, near "Since the FKS model has no notion of time")
- WHY: Shows that the standard formal result for OIDC leaves out logout, and has no notion of time so no token expiry. "Session integrity" here means a login is not forced onto the wrong user, not logout. This is the gap for us.
- PRIORITY: medium. Gap evidence, login only.
- READ: abstract, introduction, model scope paragraph. Proof sections not read.

---
84 Towards Automated Auditing for Account and Session Management Flaws in Single Sign-On Deployments, Mohammad Ghasemisharif, Chris Kanich, Jason Polakis, IEEE S&P, 2022
- SHOWS: SAAT, an automated tool that logs into websites ("relying parties", RPs) using Facebook login and tests account merging, re-authentication, cookie lifetime, logout and what happens when the user revokes the app at Facebook (measurement on real sites; models the revocation as a small state machine used to drive tests, no proof).
- QUOTE: "less than 2% of RPs correctly react to SSO revocation and 67% continue to allow account access even 10 days after revocation." (Abstract)
- WHY: The closest match to our question: SSO sites keep users logged in after access is revoked at the identity provider. In the results section, of 470 RPs with detectable state only 8 actually logged out because of revocation; 318 still accepted cookies 10 days later; 48% accepted cookies 40 days after login. Google and Apple login behaved the same as Facebook in 99% of cases on a 50-site subset. Not about logging out of one tab or app and seeing others stay on, and not about the IdP's own logout.
- PRIORITY: high. Direct SSO revocation numbers.
- READ: abstract, introduction, revocation test design, results and takeaways, comparison with Google/Apple, parts of discussion. Account-merging sections skimmed.

---
68 A Comprehensive Formal Security Analysis of OAuth 2.0, Daniel Fett, Ralf Küsters, Guido Schmitz, CCS, 2016
- SHOWS: A hand-written formal model of OAuth 2.0 (all four grant types) and a manual proof of authorization, authentication and session-integrity properties after fixes for four attacks found while proving (model, not real code).
- QUOTE: "We do not model expiration of access tokens and session ids... We also do not model revocation of access tokens and user log out." (Limitations of Our OAuth Model)
- WHY: Explicit statement that the best-known OAuth formal proof assumes tokens never expire and are never revoked, and no logout. Verifying these is new ground.
- PRIORITY: medium. Explicit gap statement, login only.
- READ: abstract, intro, limitations paragraph, conclusion heading. Proofs not read.

---
69 Analyzing the BrowserID SSO System with Primary Identity Providers Using an Expressive Model of the Web, Daniel Fett, Ralf Küsters, Guido Schmitz, ESORICS, 2015
- SHOWS: A hand-written formal model of Mozilla BrowserID (primary IdP mode) with a manual proof of authentication properties after a fix; found an identity injection attack and privacy attacks (model of a real system, confirmed attack on the real implementation, no tool).
- QUOTE: "An authenticated session can (non-deterministically) expire, i.e. the authenticated session can get unauthenticated or it is removed completely. Such an expiration is used to model a user logout or a session expiration caused by a timeout." (appendix, model of the IdP)
- WHY: The only formal model here that includes logout, but only as a random event in the model; the proven properties (authentication, privacy) are about login. I did not find a property about sessions ending correctly. BrowserID is discontinued.
- PRIORITY: low. Logout modelled, not proven about.
- READ: abstract, conclusion, the model passages on logout and expiry (found by keyword search). Not checked whether any stated property constrains logout beyond that.

---
70 Post-quantum XML and SAML Single Sign-On, Johannes Müller, Jan Oupický, PoPETs, 2024
- SHOWS: Post-quantum signature and encryption schemes plugged into XML and SAML SSO, implemented in OpenSAML, Apache Santuario and BouncyCastle, with performance measurements (implementation and benchmarks, no proof of session behaviour).
- QUOTE: "We have designed post-quantum solutions for the cryptographic building blocks in XML and integrated them into the SAML SSO protocol." (Abstract)
- WHY: About future cryptography, not sessions. Search found no logout or session lifetime content. Useful only as a pointer that OpenSAML is real SAML software.
- PRIORITY: low. Cryptography only.
- READ: abstract, contributions, conclusion; keyword search for logout/session (nothing relevant).

---
71 RADIUS:UDP Considered Harmful, Sharon Goldberg, Miro Haller, Nadia Heninger, Mike Milano, Dan Shumow, Marc Stevens, Adam Suhl, USENIX Security, 2024
- SHOWS: A man-in-the-middle attack on the RADIUS network login protocol using an MD5 collision computed in under 5 minutes, with working proof-of-concept attacks against real RADIUS software (attack on real code, no formal proof).
- QUOTE: "Our attack allows a man-in-the-middle attacker to authenticate itself to a device using RADIUS for user authentication, or to assign itself arbitrary network privileges." (Abstract)
- WHY: Not web SSO and not about sessions or logout; it concerns network access authentication. Off-topic for our direction.
- PRIORITY: low. Network protocol, no logout.
- READ: abstract, introduction, keyword search for session/logout (nothing relevant). Rest not read.
