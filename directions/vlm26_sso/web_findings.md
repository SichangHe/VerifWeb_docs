# Web findings: sign-in/sign-out consistency across apps sharing one SSO

(authored by agents unless marked 🧑)

Read-only research, nothing published. Date of research: 2026-11-09.

Caveat on quotes
- fetch tool returns quotes capped at ~125 chars; "..." marks truncation
- spec text was fetched via a small summarizing model, so each quote is a fragment, not a full re-read of the spec; re-check before citing in a paper
- items marked (search-summary) come from search-result text only, not read at source

## A. Standards wording

### OIDC Back-Channel Logout 1.0 (final, errata set 1) https://openid.net/specs/openid-connect-backchannel-1_0.html
- §2.5 retransmission
  - "The OP should not retransmit a Back-Channel Logout Request unless the OP suspects that previous transmissions may have failed..."
  - "In all other cases, the OP SHOULD NOT retransmit a Back-Channel Logout Request."
  - "(Note that this is the same retransmission logic as specified in Push-Based Security Event Token (SET) Delivery Using HTTP..."
- §2.7 "The mechanism by which the RP achieves this is implementation specific."
  - context: how the RP ends the session for the sid/sub in the Logout Token
- §2.7 "Refresh tokens issued with the offline_access property normally SHOULD NOT be revoked."
- §1 limits
  - "Another significant limitation of back-channel logout is that the RP's back-channel logout URI must be reachable from all the OPs used."
- inference: the OP is told not to retry in the normal case, and no RP-side state-sync is specified, so a missed logout is not repaired by the protocol

### OIDC Front-Channel Logout 1.0 https://openid.net/specs/openid-connect-frontchannel-1_0.html
- §2 "The OP renders <iframe src="frontchannel_logout_uri"> in a page with the registered logout URI as the source"
- §4.1 "some User Agents (browsers) are starting to block access to third-party content by default"
- §4.1 "the frontchannel_logout_uri might not be able to access the RP's login state when rendered by the OP in an iframe"
- §4.1 "deployments of this specification are recommended to include defensive code to detect this situation"
- §4.1 "[OpenID.BackChannel] is not known to be affected by these developments."

### OIDC RP-Initiated Logout 1.0 https://openid.net/specs/openid-connect-rpinitiated-1_0.html
- §2 "At the Logout Endpoint, the OP SHOULD ask the End-User whether to log out of the OP as well."
- §2 "If the End-User says "yes", then the OP MUST log out the End-User."
- §2 "some logout notification methods from the OP to the RP are unreliable and therefore the notification might not be received."
- §2 "Also, the End-User might not approve the OP logging out, in which case the RP would not receive a logout notification."
- §2 notification is via "the logout mechanism(s) registered by the RPs" and "depending upon which of these mechanisms the OP and RPs mutually support."

### OIDC Session Management 1.0 (final, 2022-09-12) https://openid.net/specs/openid-connect-session-1_0.html
- §3.1 "The RP iframe polls the OP iframe with postMessage at an interval suitable for the RP application."
- §5.1 "In particular, cookies and web storage APIs may not be available in the OP frame loaded in the RP context."
- §5.1 "Cookie based implementations might then return changed for every single call, resulting in infinite loops of re-authentications."

### RFC 7009 token revocation (2013) https://www.rfc-editor.org/rfc/rfc7009.html
- §2.1 "The invalidation takes place immediately, and the token cannot be used again after the revocation."
- §2.1 "In practice, there could be a propagation delay."
- §2.1 example: "some servers know about the invalidation while others do not."
- §2.1 "Implementations should minimize that window."
- §2.2.1 on 503 "the client must assume the token still exists and may retry after a reasonable delay."
- §5 if access-token revocation is unsupported, "access tokens will not be immediately invalidated when the corresponding refresh token is revoked."

### RFC 9700 OAuth 2.0 Security BCP (2025) https://www.rfc-editor.org/rfc/rfc9700.html
- §2.2.2 "Refresh tokens for public clients MUST be sender-constrained or use refresh token rotation as described in Section 4.14."
- §4.14.2 "The previous refresh token is invalidated, but information about the relationship is retained by the authorization server."
- §4.14.2 stale token presented: "one of them will present an invalidated refresh token, which will inform the authorization server of the breach."
- §4.14.2 server cannot tell who, "but it will revoke the active refresh token."
- fetch tool only paraphrased the rest; the legit client must get a new grant
- note: RFC does not mention a grace or overlap window (not found in what was read; I did not read all 142k chars verbatim). Concurrent legit refreshes (tabs) look identical to theft.

### OpenID Shared Signals Framework 1.0 https://openid.net/specs/openid-sharedsignals-framework-1_0.html and RFC 8935 https://www.rfc-editor.org/rfc/rfc8935.html
- SSF §8.1.2.1 "The Transmitter MAY drop zero or more events that are held when the stream is paused."
- SSF §8.1.4.2 "Event Receivers MUST NOT depend on the Verification Event being transmitted synchronously..."
- SSF: no wording on retries or at-least-once in the portion read (last ~14k chars unread). Defers to RFC 8935/8936.
- RFC 8935 §2 "MAY transmit the same SET to the SET Recipient multiple times, regardless of the response"
- RFC 8935 §2 "MUST NOT expect or depend on a SET Transmitter to retransmit a SET"
- RFC 8935 §2 "In all other cases, the SET Transmitter SHOULD NOT retransmit a SET."
- RFC 8935 §4 "The SET Transmitter may be unaware of whether or not a SET has been delivered to a SET Recipient."
- RFC 8935 §4 "SET Transmitters with high reliability requirements may be tempted to always retry failed transmissions."
- answer to "at-least-once?": no. Delivery is best effort; retry is discouraged; loss is possible. (inference from quotes)
- CAEP spec itself (openid-caep) not read.

## B. Harm evidence 2022-2026

### Logout / revocation not taking effect
- Keycloak issue #34234 (2024-10-23, closed "not planned" 2024-11-11 by stale bot) https://github.com/keycloak/keycloak/issues/34234
  - "Backchannel logout is not called if the revoke endpoint was previously called with the refresh_token"
  - maintainer: "It is expected to not run logout at the `end_session_endpoint` if the session is no longer valid."
  - cause: revoking the refresh token removes the user session, so later logout finds nothing and notifies no RP
- Keycloak CVE-2025-11429 (2025-10) (search-summary) https://advisories.gitlab.com/maven/org.keycloak/keycloak-services/CVE-2025-11429/
  - "Keycloak does not immediately enforce the disabling of the "Remember Me" realm setting on existing user sessions."
  - CWE-613, CVSS 5.4, fixed 26.2.11 / 26.4.1
- Keycloak CVE-2025-12390 (search-summary) https://access.redhat.com/security/cve/cve-2025-12390
  - logout cleanup fails when cookies are missing; one user can get another's tokens (CVSS 6.0)
- Keycloak CVE-2026-18569 (2026-08) (search-summary) https://github.com/keycloak/keycloak/issues/51381
  - opposite direction: forged back-channel logout tokens accepted when validateSignature=false (Low)
- authentik CVE-2025-29928 (2025) (search-summary) https://docs.goauthentik.io/security/cves/CVE-2025-29928/
  - "deleting sessions via the Web Interface or the API would not revoke the session and the session holder would continue to have access"
  - non-default DB session storage; fixed 2025.2.3 / 2024.12.4
- Zitadel CVE-2023-22492 (2023) (search-summary) https://nvd.nist.gov/vuln/detail/CVE-2023-22492
  - refresh tokens not invalidated for locked/deactivated users, CWE-613
- Zitadel issue #12637 (open) (search-summary) https://github.com/zitadel/zitadel/issues/12637
  - refresh tokens still mint access tokens after the session is terminated
  - Zitadel blog (as quoted by search): "ZITADEL, however, keeps refresh tokens active post-logout, a decision driven by usability considerations."
- Authelia, Okta, Auth0, Kanidm CVEs on logout: not found. Authelia search returned nothing relevant (one search only).

### Vendor docs admitting delay
- Microsoft Entra CAE (page updated 2026) https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-continuous-access-evaluation
  - "By default, access tokens are valid for one hour"
  - "The goal for critical event evaluation is for response to be near real time, but latency of up to 15 minutes might be observed because of event propagation time"
  - "Changes made to Conditional Access policies and group membership made by administrators could take up to one day to be effective."
  - "CAE doesn't support Guest user accounts. CAE revocation events and IP based Conditional Access policies aren't enforced instantaneously."
  - CAE web Office apps "Not Supported" for Exchange; initial scope "Exchange, Teams, and SharePoint Online" only
  - "Token lifetime increases to long-lived, up to 28 hours, in CAE sessions."
- Auth0 back-channel logout https://auth0.com/docs/authenticate/login/logout/back-channel-logout
  - "Back-channel logout requests are placed into an asynchronous queue and processed as quickly as possible."
  - "During high load situations, there may be a slight delay before the logout request is executed"
  - page says nothing on retries, timeouts, or delivery failure (not found)
- Google token revocation latency: not searched, nothing found.

### Refresh-token-rotation races -> random sign-outs
- Auth0 docs https://auth0.com/docs/secure/tokens/refresh-tokens/configure-refresh-token-rotation
  - "helps to avoid concurrency issues when exchanging the rotating refresh token multiple times"
  - "During the leeway window the breach detection features don't apply and a new rotating refresh token is issued."
  - "Only the previous token can be reused; if the second-to-last one is exchanged, breach detection will be triggered."
  - "By default leeway is disabled."
  - on reuse: "the entire set of refresh tokens issued since that invalidated token was issued" is revoked
- auth0-spa-js issue #1684 (2026-07) https://github.com/auth0/auth0-spa-js/issues/1684
  - reporter: SPA sends "the same refresh token for all POST requests to /oauth/token"; later calls "return 'invalid_grant'"
  - maintainer: MRRT and rotation are "fundamentally incompatible"; "each call gets back a different new RT so the family does get forked."
  - closing: "the first concurrent burst can still race on the same RT but that is expected." Advice: overlap "not set to 0"
- Okta https://developer.okta.com/docs/guides/refresh-tokens/main/
  - grace default 30 s: "You can change the value to any number from 0 through 60 seconds."
  - on reuse Okta "immediately invalidates the most recently issued refresh token and all access tokens issued since the user authenticated."
- Auth.js guide https://github.com/nextauthjs/next-auth/blob/main/docs/pages/guides/refresh-token-rotation.mdx
  - "Therefore, in some cases, a race-condition might occur if multiple requests will try to refresh the token at the same time."
  - "The Auth.js team is aware of this and would like to provide a solution in the future."
  - discussions #11317 (2024), #3940 (search-summary): second refresh fails with invalid_grant
- oidc-client-ts multi-tab (search-summary, third-party PR text, not primary) https://github.com/mattbutlerengineering/mattbutlerengineering/pull/8372
  - tabs share a stored refresh token and renew on own timers; leeway 0 revokes the family; fix was 30 s leeway
  - primary oidc-client-ts / MSAL issues: not searched, not found
- Other projects hitting same race (search-summary): better-auth #8512, cloudflare/workers-oauth-provider #214, nextcloud/user_oidc PR #1450, spring-security #20018
- opinion: all vendor fixes are time-window heuristics (overlap 30 s), not a coordination protocol; the window trades theft detection for liveness

### Third-party cookies, FedCM
- Safari ITP https://webkit.org/tracking-prevention/
  - "ITP by default blocks all third-party cookies."
  - "There are no exceptions to this blocking."
  - "Third-party cookie access can only be granted through the Storage Access API and the temporary compatibility fix for popups."
  - page does not mention SSO explicitly; effect on iframes is inference
- Chrome: Google abandoned third-party cookie deprecation (2024-07-22) and confirmed no prompt (2025-04-22); Privacy Sandbox APIs retired 2025-10-17 but CHIPS, FedCM, Private State Tokens kept (search-summary of news sites, not Google primary). Chrome still allows third-party cookies by default; Incognito blocks.
  - so iframe-based logout/silent renew is broken on Safari and Firefox, mostly works on Chrome (inference)
- FedCM (search-summary) https://privacysandbox.google.com/blog/fedcm-chrome-122-updates
  - disconnect API since Chrome 122; "Disconnect is not a logout"
  - IdP logout API (logoutRPs) was experimental, never shipped by default; spec editor: no API for IdP logout
  - FedCM Chromium-only as of 2026-10 per vendor article; Edge 136+; Firefox 138 added Login Status API only

## C. Rust feasibility (GitHub numbers via gh api on 2026-11-09)

### Identity providers
- Kanidm https://github.com/kanidm/kanidm : 5555 stars, MPL-2.0, pushed 2026-11-10
  - back-channel logout: not supported. Issue #2412 closed 2026-03-31 as completed; maintainer: "The reason it's not advertised is because it's not currently supported :)"
  - RP-initiated logout / global logout: issue #4240 "OAuth2 Global Logout" open (2026-03-31). Maintainer: "This is why so far we don't implement it - I think the experience kind of sucks, it's misleading..."
  - same issue: "Signing out of Kanidm expires every single related OAuth2 session immediately!!!"; "the best way for the user to logout, is to just go to Kanidm and sign out there."
  - revocation: docs list token/revoke endpoint (mislabeled RFC 7662; search-summary)
  - refresh tokens: exist; default 16h sliding expiry (third-party PR, search-summary); rotation behaviour not confirmed; offline_access issue #4034 open
  - end_session_endpoint: issue #1997 open, #3752 closed (2025)
- Rauthy https://github.com/sebadob/rauthy : 1439 stars, Apache-2.0, pushed 2026-11-09
  - README (search-summary): "OpenID Connect RP Initiated Logout" and "OpenID Connect Backchannel Logout"
  - release notes (search-summary): revocation endpoint added; config to revoke tokens on logout; maintainers warn revocation "only works when the tokens are checked against Rauthy's API"
  - refresh-token rotation / reuse interval: not found
  - companion crate rauthy-client has a backchannel-logout feature (LogoutToken validation)
- Ory Hydra https://github.com/ory/hydra : 17655 stars, but Go, not Rust. Ory "pieces" in Rust: not found.

### Client libraries
- openidconnect-rs https://github.com/ramosbugs/openidconnect-rs : 651 stars, MIT, v4.1.0 (2026-10-31)
  - README lists "OpenID Connect RP-Initiated Logout"; src/logout.rs has end_session_endpoint metadata
  - back-channel / front-channel logout token validation: not found in the repo's file listing or README
- oauth2-rs https://github.com/ramosbugs/oauth2-rs : 1213 stars, Apache-2.0, last push 2026-02-22
  - logout features not checked; RFC 7009 revocation support not verified
- no Rust client lib found that coordinates refresh across tabs (not applicable: native Rust has no tabs; relevant only for WASM/Servo)

### Servo https://github.com/servo/servo : 38448 stars, MPL-2.0, pushed 2026-11-10
- cookies: components/net/cookie.rs and cookie_storage.rs exist; "Implement SameSite cookies" #25600 open; third-party cookie blocking policy: not found
- service workers: "Implement Service Workers API" #11091 open; components/script/dom/serviceworker/ exists; #40781 "Service Worker improvements in serviceworker-next" open; #48195 "Service worker is not available" open (2026-11)
- Web Locks: "Implement Web Locks API" #44777 open (2026-08); #47893 notes "IndexedDB and Web Locks gaps"
- BroadcastChannel: no clear tracking issue found; a WPT test for it appears in bfcache issue #39521. Status unresolved (not checked in source).
- opinion: a Servo-based demo of cross-tab coordination cannot rely on Web Locks today; BroadcastChannel/localStorage events unverified

### Verus / verified Rust for auth
- https://github.com/verus-lang/verus : 3622 stars, MIT, pushed 2026-11-09
- found: "Towards System-Oriented Formal Verification of Local-First Access Control" https://arxiv.org/pdf/2604.23560 (2026) uses Verus for authorization rules on an event log (search-summary)
- found: Anvil (verified Kubernetes controllers) as largest Verus system; Vest verified parser; Atmosphere OS (VeruSAGE, arXiv 2512.18436)
- not found: Verus-verified OAuth/OIDC, session, token-revocation or logout-propagation work
- opinion: the logout-propagation / refresh-race problem is a distributed-protocol property; Verus-style verification of a Rust IdP plus RP library is plausible (Anvil is a precedent for liveness of controllers) but there is no prior art in this space found

## Gaps
- CAEP spec text, Google/Entra revocation numbers beyond the Entra page, MSAL and oidc-client-ts primary issues, Authelia/Okta/Kanidm CVEs, Servo BroadcastChannel source status, oauth2-rs logout/revocation support, Rauthy rotation
