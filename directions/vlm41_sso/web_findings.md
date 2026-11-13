# VLM41 SSO: web evidence on unexpected sign-outs and cross-tab/app inconsistency
(authored by agents unless marked 🧑)

Labels: PB provider bug, AB app/integration bug, BP browser-policy-caused, BD by-design. "Quote" = verbatim from a page fetched by WebFetch (fetch tool returns excerpts via a small model, so quotes are as returned, not independently re-checked). "Summary-only" = seen only in WebSearch snippets, not verified on the page. Fact = stated by source; Inference = mine.

## A. By-design / vendor admits logout does not reach all apps (ii)

A1. Microsoft Learn, "How to handle third-party cookie blocking in browsers" (page updated 2026-06-15; ms.date 2022). Label: BP + BD. Fact.
URL: https://learn.microsoft.com/en-us/entra/identity-platform/reference-third-party-cookies-spas
Quote: "there's a risk that without access to third-party cookies, not all federated applications will see a sign-out at the same time. This is a known limitation of the OpenID Front-Channel Logout 1.0 specification. ... A user could log out of application A in tab A, but application B in tab B will still appear as logged in for the access token's remaining valid time."
Also: "Silent token acquisition no longer works when third-party cookies are blocked" and "Developers can continue to use `prompt=none` with the expectation that they see a higher rate of interacion_required errors when third-party cookies are blocked." SPA refresh tokens: "24-hour lifetime rather than a 90-day lifetime."
This is the most direct vendor answer to Harsha's "why some tabs and not others". It is a tab-level statement.

A2. Okta, third-party apps supporting Universal Logout (2025-26 doc). Label: BD (vendor limit). Fact.
URL: https://help.okta.com/oie/en-us/content/topics/itp/universal-logout-supported-third-party-apps-list.htm
Quote (Microsoft row, "Partial Universal Logout support"): "These apps share an identity stack and only provide a partial Universal Logout. Universal Logout only revokes their refresh tokens. User sessions aren't terminated until the user's existing access tokens expire or the user signs out. The token expiration timeout is different for each app."
Summary-only (same help.okta.com family): does not work with custom SAML/OIDC apps under Federation Broker Mode; needs apps to support Global Token Revocation + Signed JWT. Okta dev forum (https://devforum.okta.com/t/universal-logout-feasibility-with-okta-as-intermediary/35264): inbound SAML SLO to Okta "not currently supported" (summary-only).

A3. Shibboleth wiki "The Difficulties of Single Logout". Label: BD. Fact. Undated, old (IdP 2/3 era).
URL: https://shibboleth.atlassian.net/wiki/spaces/CONCEPT/pages/928645229/SLOIssues
Quotes: "The Shibboleth 2 IdP does not support single logout in any meaningful sense." / "If the SP is not responsive the process breaks down and the remaining SPs will not receive logout requests." / "In almost all failure cases the sensible thing would be to tell the user to close their browser."
IdP 3 LogoutConfiguration (https://shibboleth.atlassian.net/wiki/spaces/IDP30/pages/2499805694/LogoutConfiguration), summary-only: SLO "is a best-effort attempt"; SPs participate only if metadata lists SingleLogoutService; relies on iframes and JavaScript.

A4. University IdP logout pages (various years, summary-only from search snippets, not fetched). Label: BD. Fact.
- UC Irvine: "You have logged out of your application, but you may have active sessions on other sites you have visited while signed in. To sign out of all sites, please close your browser." https://shib.service.uci.edu/logged_out.html
- UW-Madison: central logout "will not log the user out of other NetID-protected resources ... (e.g. other tabs in the same browser)". https://kb.wisc.edu/helpdesk/page.php?id=20415
- U Minnesota: "if you log out of one of those applications, you will remain signed in to the other application as long as the browser window remains open." https://it.umn.edu/services-technologies/good-practices/make-sure-you-are-fully-logged-out-keep
- Also Cornell, Colorado State, UT Dallas, UW Seattle say same.
USC: not found (no USC page surfaced). Need a targeted check of USC ITS docs.

A5. Google Workspace session length help (summary-only): "when you change the session length, users need to sign out and then sign in again for the new settings to take effect." https://support.google.com/a/answer/7576830. Same search: admins cannot set session length "for native mobile apps". Google Cloud: service-account tokens "can't be invalidated through the Admin console" and remain valid up to expiry (https://docs.cloud.google.com/docs/security/compromised-credentials). Label: BD. Google "sign out of all sessions" scope page: not found/verified.

## B. Why tabs/apps disagree (iii)

B1. Duende blog "The Cookie Apocalypse Already Happened", 2026-04-14. Label: BP. Fact (vendor opinion).
URL: https://duendesoftware.com/blog/20260414-the-cookie-apocalypse-already-happened
Quotes: "Silent token renewal via hidden iframes, the technique that oidc-client-js and its successor oidc-client-ts relied on..." is broken; "Front-channel logout, which relied on the same cross-site iframe pattern, is equally dead." Names Safari ITP, Firefox Total Cookie Protection, Chrome ("removed third-party cookies for all users" per the blog; Inference: this conflicts with my recollection that Chrome kept 3PC, so verify before citing the Chrome claim).

B2. oidc-client-ts #1032 "Does Silent Renewal Using iFrames Work with Modern Browsers?" (opened 2023-06-03, closed stale 2024-10-14). Label: BP. Fact.
URL: https://github.com/authts/oidc-client-ts/issues/1032
Quote (commenter theadell, 3 thumbs-up): "The problem isn't the Iframe but rather the third-party cookies." Maintainer: "There is still the chance that the iframe renewable process works" (SameSite=strict cookie sent because the IdP page loads in the iframe). Scale: 3 upvotes.

B3. Refresh-token rotation race across tabs. Label: AB (client) interacting with provider reuse-detection (BD). Fact for mechanism; Inference that it applies to big IdPs.
- CerberAuth blog, 2026-07-17: https://www.cerberauth.com/blog/refresh-token-rotation-integration-challenges/ Quote: "nothing stops two tabs from waking up and refreshing at the same instant." and "A lock inside one tab doesn't stop a different tab from racing it." Fix: Web Locks API + BroadcastChannel; server grace period.
- Summary-only: many small-repo issues (e.g. https://github.com/johannesjahn/chat-platform/issues/650 "two tabs refreshing together log the user out"; StellarEduPay #1529). These are hobby repos, not evidence of scale. No issue in oidc-client-ts, next-auth, auth0-spa-js on this specific race was found this round (auth0-spa-js #1684 already known).

B4. MSAL.js multi-tab issues. Label: AB (library/integration). Fact.
- #7402 (opened 2024-11-04, msal-browser 2.30.0 + msal-angular 2.4.5): idle app logs out from all tabs at once; "BrowserAuthError: interaction_in_progress: Interaction is currently in progress." Expected: "User should be logged out from all the tabs". 2 thumbs-up, 0 comments, open, unassigned. https://github.com/AzureAD/microsoft-authentication-library-for-js/issues/7402
- Also (summary-only): #7399 (logout fails with multiple tabs, msal-react), #6245 (interaction_in_progress from multiple tabs), #5565 (400 after signout on multiple tabs), #4369 (B2C multi-tab). MS Q&A 1530709 (Feb 2024): other tabs stuck on logout page.
- #7990 (summary-only): maintainer says login_required/interaction_required arises when no active account is set for acquireTokenSilent.

## C. Provider-side unexpected sign-outs (i)

C1. Meta outage, 2024-03-05. Label: PB. Fact (news).
URLs: https://variety.com/2024/digital/news/facebook-down-users-report-problems-including-getting-logged-out-1235930538/ ; https://techcrunch.com/2024/03/05/facebook-instagram-and-threads-are-all-down-in-massive-meta-outage-on-super-tuesday/amp
Summary-only: "over half a million" Downdetector complaints; ~76% of Facebook reports about login; Meta: "We are recovering from an earlier outage impacting Facebook Login". Root cause never published. Only Facebook incident found; no Facebook per-tab inconsistency evidence found.

C2. Microsoft Q&A, 2025-09-22, "Users randomly signed out due to token corruption after password change or session revoke". Label: unresolved (likely tenant CA policy). Fact.
URL: https://learn.microsoft.com/en-us/answers/questions/5563285/users-randomly-signed-out-due-to-token-corruption
Quote: "~8 accounts where users keep getting signed out from Microsoft 365 apps (Teams, Outlook, OneDrive, etc.) on all devices"; errors 50133/50173. Only reply (volunteer moderator): CA session-lifetime policy may be the cause. 0 me-too. Scale: one tenant, 8 users.

C3. Entra "MACE Credential Revocation" lockouts, ~2025-04-19. Label: PB (hypothesised). Summary-only, secondary source.
URL: https://www.helient.com/news/important-update-addressing-recent-microsoft-entra-user-blockages
Quote (as reported): "numerous organizations experienced significant disruptions as their users were unexpectedly locked out of Microsoft Entra ID accounts." The same source says it found no Microsoft status/MSRC corroboration of the refresh-token-invalidation hypothesis. Weak evidence; not verified on page.

C4. Google Colab #4232, "Your Google Account was signed out on a different tab. Sign in to continue LOOP" (opened 2023-12-17, still open, comments through 2026-09). Label: PB or AB, unknown; labelled bug+triaged. Fact.
URL: https://github.com/googlecolab/colabtools/issues/4232
Quote: "Despite me signing in 5 separate times and deleteing all the cookies / site data." Reply (2023-12-19): "We've sometimes seen this when the url includes an `authuser` param that should be removed". Another user (2024-01-06) suspects "a long-running cell" plus laptop sleep. 4 comments, no reaction counts shown. This is literally a cross-tab sign-out message from Google.

C5. Google Account Community / Apple / Okta community "me too" threads: not found this round (search did not surface support.google.com or Apple threads). Entra/Okta status-page incidents specifically about sign-outs: not found.

## D. Incidents / CVEs (iv)
No CVE found where logout fails to propagate. Found the opposite class (forced logout) and generic SSO bypass; relevance to Harsha's question is low.
- Keycloak #53116 "SAML SLO: unauthenticated arbitrary session termination via LogoutRequest (SessionIndex)" https://github.com/keycloak/keycloak/issues/53116 (summary-only, no CVE seen). Label: PB.
- CVE-2026-82465 pac4j-saml before 6.5.6, "Session Destruction via Unsigned LogoutRequest" https://app.opencve.io/cve/CVE-2026-82465 (summary-only). Label: AB.
- CVE-2025-0126 PAN-OS GlobalProtect SAML session fixation (pre-auth session id not invalidated) https://security.paloaltonetworks.com/CVE-2025-0126 (summary-only).
- Blog (summary-only): SLO leaves "orphaned session" where the app is logged out but the IdP is not. https://ashishsrivastav.com/blog/saml-single-logout-implementation

## Gaps
- No numbers on how many users are affected anywhere; all scale evidence is single-digit upvotes or one incident (Meta 2024).
- Not found: Apple Sign in; USC-specific Shibboleth doc; Google "sign out of all sessions" scope; Okta/Entra status-page sign-out incidents; Chrome 3PC current status (sources disagree; Inference: check).
- Strongest framing (Inference): the cross-tab inconsistency is mostly by-design (tokens outlive sessions; front-channel logout is best-effort) plus browser-policy breakage of iframe mechanisms, with app-level races (rotation, multi-tab MSAL) adding genuine bugs.
