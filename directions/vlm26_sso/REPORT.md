# SSO sign-in/sign-out consistency: literature check
(authored by agents unless marked 🧑)

Details, full quotes and the exact Scholar queries: scholar_findings.md (Google Scholar, 10 fetches, no CAPTCHA) and web_findings.md (standards, vendor docs, CVEs, Rust).

## Findings first

1. The harm is now measured, and the measurement is recent: 2022, not 2018.
   - Ghasemisharif and Kanich, IEEE S&P 2022 (https://par.nsf.gov/servlets/purl/10339713), read in full. After the identity provider revoked access, "only 8 RPs actually exhibited the logged out behavior due to access revocation" and "318 RPs continued accepting cookies 10 days after revocation." (RP means relying party, an app that accepts the SSO login.)
   - Vendors admit the delay. Microsoft Entra CAE (continuous access evaluation, updated 2026): "latency of up to 15 minutes might be observed". Auth0's back-channel logout docs admit "eventual consistency".
   - Bugs in open-source identity providers: Keycloak #34234 (2024): if the refresh token is revoked first, the back-channel logout is never sent. A stale bot closed it as "not planned". There are also logout/session CVEs in Keycloak, authentik and Zitadel (2023-2026), but I saw those only in search summaries.
2. Random sign-outs: yes, this direction covers them. The cause is documented but has never been measured.
   - How it happens: with refresh-token rotation, each refresh issues a new token and invalidates the old one. When two tabs or apps refresh at the same time, one of them sends a token that was just invalidated. The server reads that as token theft and revokes the whole session.
   - NEBULA (arXiv 2608.04115, 2026, read) says concurrent refresh is "the default behaviour of retrying mobile clients and multi-tab browsers".
   - Vendors patch around it with timing windows. Okta allows a 30 s grace period. Auth0's overlap window is off by default (auth0-spa-js #1684, 2026). The Auth.js docs admit the race.
   - Browsers make it worse. Safari: "ITP by default blocks all third-party cookies". That breaks silent SSO renewal and front-channel logout, and the Session Management spec itself warns of "infinite loops of re-authentications".
   - Not found: any study counting how often users get signed out this way.
3. The standards guarantee only best effort, and that is the gap a formal model would expose.
   - Back-Channel Logout: "the OP SHOULD NOT retransmit a Back-Channel Logout Request". How the app ends its session is "implementation specific".
   - RFC 7009: "The invalidation takes place immediately", and also "In practice, there could be a propagation delay".
   - RFC 8935, the delivery layer under Shared Signals/CAEP (the newer standard for pushing revocation events): the sender "may be unaware of whether or not a SET has been delivered". (A SET is a security event message.)
   - Caveat: these spec quotes came through a summarizing fetch tool. Re-check them against the spec text before using them externally.
4. Novelty: Scholar confirms that no formal work covers logout or revocation propagation.
   - Fett et al. 2017 (OIDC): "We do not model less used features, in particular OIDC logout". The model also has no notion of time, so tokens never expire. Their 2016 OAuth model also leaves out logout.
   - Found nothing covering OIDC back- or front-channel logout, SAML single logout, revocation reaching many apps, or rotation under concurrent refresh.
   - Not yet read, so they could change this: a 2020 thesis on Shibboleth (Sommer), a 2026 Tamarin model of CAS (Cai et al.) and a 2023 thesis on OAuth (Vasudevan).
   - NEBULA is the closest. It specifies a compare-and-set rotation rule (a refresh succeeds only if the token is still the current one), but it has no proof, no multiple apps and no logout.

## "Would we just do all the parts in Rust and formally verify all of them?"

Opinion: no, only the server side and the client library. The browser and third-party apps are out of our control.
- Identity provider:
  - Kanidm (Rust, 5555 stars) has no back-channel logout. Its maintainer, on RP-initiated logout (#4240): "This is why so far we don't implement it". This could be our contribution.
  - Rauthy (Rust, 1439 stars) advertises back-channel logout.
- App-side library: openidconnect-rs (651 stars) supports RP-initiated logout only, as far as we found. A verified multi-tab-safe refresh client would be new.
- Browser: Servo still lacks Web Locks (#44777) and Service Workers (#11091), the pieces tabs use to coordinate. Verifying them alone does not fix SSO (see msg_sso).
- Verus: we found no prior verified-Rust work on auth or sessions.
- Realistic split (opinion): first a TLA+ model of the protocol, covering what the standards allow. Then Verus proofs of the provider's logout/revocation path in Kanidm or Rauthy, and of a client refresh library.

## Where the idea came from

This came out of our own direction brainstorm: section 3 (logout/revocation) and section 4 (tabs racing refresh) of the vlm25_dist report. The human raised random SSO sign-outs after we proposed SSO; that sharpened the focus on sign-outs that happen without asking. The literature above shows outside evidence for the problem. We found no paper or person proposing to verify it.

## Gaps

- Not found: a measurement of CAEP deployment, Google's revocation latency, logout CVEs for Okta, Auth0 or Kanidm, or oauth2-rs logout support.
- Search-summary only, not read at the source: the CVEs, the oidc-client-ts multi-tab issue, FedCM.
