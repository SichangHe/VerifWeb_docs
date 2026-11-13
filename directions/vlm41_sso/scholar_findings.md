# Scholar findings: inconsistent SSO sign-in/sign-out across tabs/apps

(authored by agents unless marked 🧑)

Scope note. No paper found studies the professor's exact symptom (one tab logged out, another not, in the same browser). The closest literature measures (a) logout not ending sessions at relying parties (RPs), (b) IdP revocation not reaching RPs, (c) third-party-cookie blocking breaking silent SSO. Fact = quote from paper. Inference = mine.

## Facts

F1 (how often, IdP revocation does not reach RPs; RP fault). Ghasemisharif, Kanich, Polakis, IEEE S&P 2022, https://par.nsf.gov/servlets/purl/10339713 (Facebook as IdP, many RPs):
"Our study also shows that less than 2% of RPs correctly react to SSO revocation and 67% continue to allow account access even 10 days after revocation."
Body: "After the revocation process, only 68 RPs showed a logout behavior. By comparing these RPs with our extended group, we found that in 60 RPs the logout behavior was caused by cookie expiration and only 8 RPs actually exhibited the logged out behavior due to access revocation. We also note that 318 RPs continued accepting cookies 10 days after revocation."
Abstract also: "17.6% of the tested RPs exhibit non-functional SSO implementations" and "These flaws are not baked into the actual SSO protocols, but manifest due to the complexity of supporting separate but intermingling authentication paths."

F2 (how often, RP logout does not end server session; RP fault). Calzavara, Jonker, Krumnow, Rabitti, Computers & Security 2021 (6,124 Tranco sites; not SSO-specific), https://iris.unive.it/bitstream/10278/5004094/1/compsec21.pdf:
"we identify a number of sites which implement the logout functionality insecurely: specifically, 469 (8%) sites do not terminate sessions at the server upon logout, while 230 (4%) sites do not remove security-sensitive information from the client after logout."
Also: logout automation succeeded on 3,302 sites, "54% of the sites where we successfully logged in".

F3 (how often, token not invalidated at logout; RP fault). Lamisa, Concordia MASc thesis 2024 (conference version: Lamisa, Mannan, Youssef, 2025, Springer; not read), https://spectrum.library.concordia.ca/id/eprint/994931/1/Lamisa_MASc_F2024.pdf:
"446 out of 520 websites (85%) tested for JWT invalidation do not invalidate JWTs included in requests after user logout."
Cookies: "after seven days, 203 websites continued to exhibit the same issue of not invalidating the session cookies. In comparison, Calzavara et al. reported a higher rate of 18% for websites that did not invalidate cookies post-user logout."

F4 (why, third-party cookies; provider/browser/app interaction). Innocenti, Jannett, Mainka, Westers, Wich, IEEE S&P 2025, "Only as Strong as the Weakest Link", https://innotommy.com/Identity_Brokers.pdf:
"Blocking third-party cookies will cause certain SSO flows on third-party brokers to break [18]. For instance, the Auth0 broker can be integrated as a first party or third party. If used as a first party, it supports a "silent authentication flow" without user interaction in which the SP can fetch renewed tokens from the broker that is embedded in an iframe [10]. If used as a third party, the iframe has no access to third-party cookies and the token refresh will fail [11]."
(Statement about Auth0 documented behavior, not a measurement of how many users are logged out.)

F5 (why, refresh-token rotation race). Teodori, arXiv 2608.04115, Aug 2026 (single independent author, preprint, not peer-reviewed), https://arxiv.org/abs/2608.04115:
"We additionally consider (T5) an adversary or an ordinary client whose requests interleave, so that two refreshes of one token execute concurrently; this is not an exotic capability but the default behaviour of retrying mobile clients and multi-tab browsers."
"the BCP specifies policy, not mechanism: it prescribes no wire format, no storage schema, no ordering of verification steps, no concurrency contract ... production implementations ... may diverge in precisely the corner cases that determine security outcomes."
Also: "Exactly one of two racing refreshes can therefore win" (Scholar snippet); the loser's reuse detection revokes the token family (this spec's compare-and-set design), which is the mechanism that logs out a tab that lost the race (inference, see I3). No measurement of how often this happens in deployed systems.

F6 (why, Shibboleth/SAML SLO; seen only as Scholar snippets, papers not read). Sommer, Univ. Stuttgart thesis 2020, https://elib.uni-stuttgart.de: "Single Logout protocols has not been formally analysed previously." Wilson & Hingnikar, Springer 2022 (book chapter): "In the absence of such single logout capabilities, an application can poll an OpenID Provider periodically".

## Inferences (mine, not from papers)

I1. Cause of "some tabs logged out, others not": logout is per-RP local state (cookie/token) plus an optional IdP session; no protocol forces them to agree. F1 and F2 show RPs often keep their own session after IdP-side revocation or even RP-side logout. A tab at RP A may be dead while a tab at RP B (or a tab with a still-valid cookie/token) is alive.
I2. Provider vs app: the measured evidence in F1-F3 blames RPs (apps), not IdPs. The only provider-side evidence is F4 (broker/IdP embedded as third party breaks under cookie blocking) and F5 (rotation design).
I3. Refresh-token rotation with reuse detection can sign out the losing tab when two tabs refresh concurrently; F5 says concurrency in multi-tab browsers is default behavior, but gives no frequency.
I4. Size of the problem: for security (sessions surviving logout/revocation) it is large (F1-F3: 8% to 85% depending on definition and sample). For user-visible unexpected logout (the professor's symptom), I found no prevalence study.

## Gaps
- No measurement of cross-tab inconsistency, of Google/Microsoft/Okta SLO coverage, or of user-visible unexpected-logout rates.
- Usability query returned only an unrelated clinical EMR study and generic SSO usability; Okta/Shibboleth SLO appear only in thesis/book/industry-style sources.
- Ardi & Calder IMC 2023 and Fett et al. 2017 not re-read.

## Exact Google Scholar queries (as_ylo=2020 on all; outputs in out/vlm41_sso/scholar/q1..q7.txt)
1. single+logout+measurement+SSO
2. SSO+session+management+relying+party+logout+flaws
3. OAuth+logout+token+revocation+relying+parties+study
4. third-party+cookie+blocking+single+sign-on+breakage
5. "single logout" SAML study
6. usability+unexpected+logout+users+single+sign-on+sessions
7. refresh+token+rotation+race+concurrent+requests
No CAPTCHA encountered. Queries 8+ not run.

## paper_collection files added (PDFs only, nothing git-added)
- Measuring Web Session Security at Scale, Stefano Calzavara, Hugo Jonker, Benjamin Krumnow, Alvise Rabitti, Computers & Security, 2021.pdf
- Only as Strong as the Weakest Link- On the Security of Brokered Single Sign-On on the Web, Tommaso Innocenti, Louis Jannett, Christian Mainka, Maximilian Westers, Tobias Wich, IEEE S&P, 2025.pdf
- Measuring Improper Token Invalidation in Real-World Web Logins, Kazi Farhat Lamisa, Concordia University MASc thesis, 2024.pdf
Already present (not re-added): Ghasemisharif et al. S&P 2022 PDF; NEBULA (Teodori, arXiv 2026) PDF.
Note: files sit at top level of /hdd1/sichanghe/paper_collection, not in per-paper folders with extracted .md (that step belongs to the literature collector).
