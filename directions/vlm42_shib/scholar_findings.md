# Campus/enterprise SSO literature search

(authored by agents unless marked 🧑)

Method: Google Scholar via pb-browser-page-extract, 10 queries, as_ylo=2018 (2008 for Armando, 2015 for Fett), no CAPTCHA hit. Raw outputs: /hdd1/sichangheagent/vl_meeting_work/out/vlm42_shib/scholar/*.txt. "Saved" = PDF plus extracted text placed in /hdd1/sichanghe/paper_collection (not git-added). Where the PDF was not retrievable (paywall or bot block, not bypassed), the quote is only the Scholar snippet or the IEEE abstract page, and it is marked "not saved".

## Formal verification of SAML / SSO

1. Zvonimir Hartl, Ante Derek. "Toward Automated Formal Security Analysis of SAML V2.0 Web Browser SSO Standard: The POST/Artifact Use Case." IEEE Access 13, 2025. Not saved (IEEE PDF blocked by bot check; open access, so a human can fetch it).
   Quote (IEEE abstract page, truncated by extraction): "One of the most common SSO protocol frameworks — the Security Assertion Markup Language V2.0 (SAML) Web SSO Profile —". Scholar snippet: "We suggest a simple fix, and formally verify that it does indeed mitigate the discovered attack. • We include the Tamarin code and".
   Relevance: the most recent Tamarin model of SAML Web SSO (found an attack, verified a fix); the direct modern successor to Armando et al.

2. Alessandro Armando, Roberto Carbone, Luca Compagna, Jorge Cuellar, Llanos Tobarra. "Formal analysis of SAML 2.0 web browser single sign-on: breaking the SAML-based single sign-on for Google Apps." ACM FMSE 2008. Not saved (ACM paywall/bot block). Pre-2018, seminal.
   Quote (Scholar snippet of Armando, Carbone, Compagna, SATMC, STTT 2016): "identified in the SAML-based SSO for Google Apps. We reported … the formal specification of the SAML-based SSO for Google … the extended versions of the AVISPA tools."
   Relevance: the AVISPA/SATMC result showing the Google Apps SAML SSO let a malicious service provider impersonate users.

3. Daniel Sommer. "Formal security analysis of the Shibboleth Web Single Sign On System using a comprehensive model of the web." Master's thesis, University of Stuttgart, 2020. Not saved (university repository returned an anti-bot page; not bypassed).
   Quote (Scholar snippet): "Nevertheless, the security of Single Logout protocols has not … to formalize Single Logout protocols, defines some security … all security properties still hold for Shibboleth, if all SAML".
   Relevance: the only item found that formalizes Shibboleth and Single Logout (Fett/Küsters/Schmitz web model, Stuttgart); a thesis, not peer reviewed.

4. Daniel Fett, Ralf Küsters, Guido Schmitz. "A Comprehensive Formal Security Analysis of OAuth 2.0." ACM CCS 2016 (arXiv:1601.01229). Saved.
   Quote: "When proving the security of OAuth in our model, we discovered four attacks which break the security of OAuth. The vulnerabilities can be exploited in practice and are present also in OpenID Connect."
   Relevance: the web-model method (WIM) that the Shibboleth thesis reuses; shows the method finds standard-level bugs.

5. Daniel Fett, Ralf Küsters, Guido Schmitz. "The Web SSO Standard OpenID Connect: In-Depth Formal Security Analysis and Security Guidelines." IEEE CSF 2017 (arXiv:1704.08539). Already in collection.
   Quote: "Despite its importance, it has not received much attention from security researchers so far, and in particular, has not undergone any rigorous security analysis."
   Relevance: same authors' OIDC result; for contrast, SAML has no equivalent published analysis in this web model beyond item 3.

6. Daniel Fett, Ralf Küsters, Guido Schmitz. "Analyzing the BrowserID SSO System with Primary Identity Providers Using an Expressive Model of the Web." ESORICS 2015 (arXiv:1411.7210). Saved. Pre-2018, seminal.
   Quote: "During our analysis we discovered new and practical attacks that do not apply to the secondary mode: an identity injection attack, which violates a central authentication property of SSO systems".
   Relevance: shows the web model on an assertion-based SSO with browser-mediated flow, structurally close to SAML.

7. Johannes Müller, Jan Oupický. "Post-quantum XML and SAML Single Sign-On." PoPETs 2024. Saved.
   Quote: "SAML. This standard is one of the most widely used options for implementing Single Sign-On (SSO), which allows users to authenticate to different service providers using the credentials from a single identity provider."
   Relevance: recent (2024) SAML security paper, cryptographic rather than protocol-logic; shows SAML is still studied but through crypto-migration.

8. "Formal analysis of CAS under malicious service providers: Implications for trust-aware deployments." Computers & Security, 2026 (also listed as "When Single Sign-On Meets Zero Trust: Formal Analysis of CAS under Malicious Service Providers"). Not saved (ScienceDirect paywall/bot page); authors not captured.
   Quote: only the title (no abstract captured).
   Relevance: CAS is the campus SSO protocol (Apereo); a 2026 formal analysis, the closest hit to "campus SSO formal verification".

9. Anonymous-in-extraction: "Automatic verification of security of identity federation security protocol based on SAML2.0 with ProVerif in the symbolic model." Journal paper (Airiti), 2020. Not saved.
   Quote: title only.
   Relevance: a ProVerif model of SAML 2.0 federation; low-visibility venue.

10. Vedran Anić. "Formalno modeliranje protokola za digitalni identitet." Thesis, University of Zagreb FER, 2025. Not saved.
   Quote (Scholar snippet): "we formally analyse the security of the SAML 2.0 Web-SSO profile with the Tamarin Prover."
   Relevance: another independent Tamarin SAML model (thesis, Croatian).

## Deployment and measurement

11. Tommaso Innocenti, Louis Jannett, Christian Mainka, Vladislav Mladenov, Engin Kirda. "Only as Strong as the Weakest Link: On the Security of Brokered Single Sign-On on the Web." IEEE S&P 2025. Already in collection.
   Quote: "Our study reveals that 25% of the websites with SSO integrate brokers for authentication, an area that has not been covered by any previous research."
   Relevance: brokers (proxy IdPs) are the structure of federations like eduGAIN hubs; this is OIDC/OAuth-centered, not SAML.

12. Mohammad Ghasemisharif, Chris Kanich, Jason Polakis. "Towards Automated Auditing for Account and Session Management Flaws in Single Sign-On Deployments." IEEE S&P 2022. Already in collection (not re-read this session).
   Relevance: session management and logout flaws in SSO deployments, adjacent to SLO.

13. Calvin Ardi, Matt Calder. "The Prevalence of Single Sign-On on the Web." IMC 2023. Already in collection (not re-read).
   Relevance: measurement of public-web SSO; says nothing about campus federations.

14. Eduardo Ribeiro de Mello, Michelle Silva Wangham et al. "Multi-factor authentication for Shibboleth identity providers." Journal of Internet Services and Applications, 2020. Not saved (PDF link returned a web page).
   Quote (Scholar snippet): "federation, where it was evaluated using functional and integration testing, as well as security … This section presents a discussion about some security considerations on MFaP."
   Relevance: Shibboleth IdP hardening in a campus federation (Brazil's CAFe); engineering, not protocol analysis.

## eduroam / RADIUS

15. Sharon Goldberg, Miro Haller, Nadia Heninger, Mike Milano, Dan Shumow, Marc Stevens, Adam Suhl. "RADIUS/UDP Considered Harmful." USENIX Security 2024. Saved.
   Quote: "Our attack allows a man-in-the-middle attacker to authenticate itself to a device using RADIUS for user authentication, or to assign itself arbitrary network privileges." Also: "It is used to support remote access for diverse use cases including ... enterprise Wi-Fi including the Eduroam network".
   Relevance: the strongest recent eduroam-relevant security result (Blast-RADIUS, MD5 chosen-prefix collision on the Response Authenticator).

16. Palamà, Amici, Bellicini, Gringoli et al. "Attacks and vulnerabilities of Wi-Fi Enterprise networks: User security awareness assessment through credential stealing attack experiments." Computer Networks, 2023. Not saved.
   Quote (Scholar snippet): "of 802.1x in general, and more specifically that of Eduroam, we … x authentication through a RADIUS server also running on …".
   Relevance: experimental credential stealing (evil twin) against eduroam users.

17. "Careful with that Roam, Edu": experimental analysis of Eduroam credential stealing attacks. IEEE, 2022 (IEEE Xplore 9764586). Not saved (IEEE blocked); authors not captured.
   Quote: title only.
   Relevance: same threat, earlier measurement.

Other eduroam hits, not read: AUDIT@eduroam (SBSeg), a Radboud 2025 bachelor's thesis "Trusting Eduroam", Bremen bachelor's thesis on EAP-TLS in eduroam, "Challenges and Solutions for Eduroam Network Security" (Procedia CS 2025), "Specifying SSI over EAP" (2024).

## Federation metadata trust (InCommon / eduGAIN)

No security-analysis paper found. Hits were uses of federations, not analyses of their metadata trust: Basney et al., "CILogon: Enabling federated identity and access management for scientific collaborations" (PoS 2019; snippet: "for scalable trust management via SAML metadata exch..."); "Matching federation identities, the eduGAIN and STORK approach"; Italy's OpenID Federation longitudinal study ("All You Need is Trust", recent); "The Many Faces of Authentication and Authorisation at CERN". None saved or relied on.

## How thin is the campus-SSO literature?

Claim under test (a commenter): "there weren't too many papers around that."

Finding (inference from 10 Scholar queries, not an exhaustive survey): partly true, and the answer depends on the topic.
- False for "formal verification of SAML SSO in general": at least 5 independent models exist (Armando 2008 AVISPA, Hartl-Derek 2025 Tamarin, Anić 2025 Tamarin thesis, a 2020 ProVerif paper, Sommer 2020 for Shibboleth) plus the Stuttgart web-model line for OAuth/OIDC/BrowserID/FAPI. The SAML ones are few per decade and cluster in 2008 and 2020-2025.
- True for campus-specific topics: Shibboleth/SLO has one formal item (a master's thesis); I found no peer-reviewed security analysis of InCommon or eduGAIN metadata trust; CAS has one 2026 formal paper. Most campus hits are deployment or engineering papers (MFA add-ons, "case study of University X", CAS high availability), with little adversarial analysis.
- eduroam/RADIUS is the exception: active, with top-venue work (USENIX Security 2024) and several experimental attack papers.
- Caveat: Scholar's top-10 per query and the 2018+ filter bias toward recent items; non-English and grey literature (REFEDS, GEANT, TERENA reports) are not covered. The search did not look in those places.
