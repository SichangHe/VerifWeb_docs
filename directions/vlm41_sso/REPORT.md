# How big is the SSO sign-out / tab-inconsistency problem?
(authored by agents unless marked 🧑)

Answers Harsha (Nov 10 meeting): "So why does this happen at all? Have people studied why some tabs get logged out and others don't?" and "I'm trying to understand how big of a problem this is".
Evidence with full quotes: web_findings.md and scholar_findings.md in this folder. Earlier work: ../vlm26_sso/REPORT.md.

## Verdict

Most of the inconsistency is by design, not caused by bugs in Google, Microsoft or Facebook. Each app keeps its own session or token, and that copy outlives the provider's session. The standards make logout propagation best-effort only. Browser third-party-cookie blocking has since broken the iframe mechanisms that apps relied on to stay in sync. Real bugs sit on top of that, mostly in apps and client libraries (concurrent refresh in multiple tabs), rarely in the providers.

How big: I don't know how often users experience it. No study counts unexpected sign-outs or cross-tab disagreement. What has been measured is the opposite failure: sign-outs and revocations that fail to reach apps. That failure is large and well documented. Inference: as a user annoyance, "random sign-outs" is anecdotal and low-volume in public trackers. As a correctness/security problem ("I logged out, but app B didn't"), it is big and standard behavior.

## Where it breaks (why tabs disagree)

1. Tokens outlive sessions (by design). Microsoft Learn, on third-party cookie blocking: "A user could log out of application A in tab A, but application B in tab B will still appear as logged in for the access token's remaining valid time", which it calls "a known limitation of the OpenID Front-Channel Logout 1.0 specification" (learn.microsoft.com, current page). Okta Universal Logout, for Microsoft apps: "Universal Logout only revokes their refresh tokens. User sessions aren't terminated until the user's existing access tokens expire", and "The token expiration timeout is different for each app."
2. University SAML barely does logout. Shibboleth wiki: "The Shibboleth 2 IdP does not support single logout in any meaningful sense." Several university logout pages tell users to close the browser (UC Irvine, UW-Madison, Minnesota; seen in search snippets only). I found no USC page.
3. Browsers broke the sync channel. Innocenti et al., IEEE S&P 2025: silent token refresh fails under third-party-cookie blocking when the SSO broker is embedded as a third party (this is documented Auth0 behavior; they did not measure how many users it affects). oidc-client-ts #1032 (2023): "The problem isn't the Iframe but rather the third-party cookies." Duende blog (Apr 2026) says front-channel logout "is equally dead"; its Chrome claim is doubtful, so verify before citing it.
4. Tabs race each other (app/library bugs). This is the likely source of the random sign-outs. With refresh-token rotation, two tabs refreshing at once look like token theft, and the provider kills the session. NEBULA (arXiv 2608.04115, 2026) calls concurrent refresh "the default behaviour of retrying mobile clients and multi-tab browsers". MSAL.js #7402 (2024): logging out from several tabs at once throws `interaction_in_progress`. These are mechanisms with small issue threads; there are no frequency data.

## Measured scale (all show apps not reacting to logout/revocation)

- Ghasemisharif, Kanich, Polakis, IEEE S&P 2022 (IdP: Facebook): "less than 2% of RPs correctly react to SSO revocation and 67% continue to allow account access even 10 days after revocation." (RP = relying party, the app using the SSO.)
- Calzavara et al., Computers & Security 2021: on logout, 469 of 6,124 sites (8%) do not end the session at the server. This study is not SSO-specific.
- Lamisa, Concordia MASc thesis 2024: 446 of 520 sites (85%) do not invalidate JWTs after logout.

## Provider-side incidents (few, and not the main cause)

- Google Colab #4232 (open since Dec 2023): a "Your Google Account was signed out on a different tab" loop.
- Microsoft Q&A, Sept 2025: about 8 accounts in one tenant randomly signed out of M365. The answer points to a Conditional Access session-lifetime policy, which is a configuration issue.
- The Meta outage of Mar 5, 2024 logged users out at scale (over 500k Downdetector reports). Meta published no root cause.
- CVEs: none found where logout fails to propagate. Forced-logout bugs exist (Keycloak, pac4j-saml), seen in search snippets only.

## Gaps

Not found: any user-frequency study, Apple evidence, Okta/Entra status-page sign-out incidents, Google's "sign out of all sessions" scope documentation, or high-volume Google/Facebook forum threads. A single-logout thesis (Sommer) was not read.
