# vlm43_oidc: TLA+ model of OIDC sign-out and refresh-token rotation
(authored by agents unless marked 🧑)

Why: the SSO direction (../vlm41_sso, ../vlm26_sso) claims two failures: random sign-outs when tabs refresh at once, and apps that keep a session after sign-out. This checks both claims, and candidate fixes, with the TLC model checker. Everything below is fact (TLC output) unless labelled.

## Takeaways

1. Both failures reproduce as short counterexamples (facts, TLC traces in tla/*.out).
   - Random sign-out (tla/r_base.out, 8 states): tabs 1 and 2 both read refresh token #1; tab 1's refresh rotates it to #2; tab 2 then presents #1, the IdP treats it as reuse and revokes the whole token family. No attacker exists in the model.
   - Accept after sign-out (tla/l_base.out, l_retry.out): the back-channel logout is lost or simply slower than D, the front-channel iframe is blocked, and the app keeps accepting its session forever (without retry) or past D (with retry).
2. Refresh fixes. Only one combination passed all my configurations.
   - Grace window alone: fails (r_grace): a request delayed longer than the window still triggers revocation. Inference: a time window narrows the race; it cannot close it.
   - Per-app refresh lock (one in-flight refresh across tabs, e.g. a cross-tab lock): passes with 3 tabs (r_lock) but fails once a response can be lost after the IdP rotated (r_lock_lose): the stored token is now stale and its next use looks like reuse. Grace window does not save this either (r_lock_grace_lose).
   - Lock + "replay of the immediately previous token returns the current one" (IdP rule: a token's successor that was never presented can be reissued): passes, including lost responses (r_lock_replay_lose). The same rule without the lock fails (r_replay_nolock): the race can push a tab two generations behind.
   - Cost (inference, not modelled: the model has no attacker): the replay rule delays theft detection by one rotation; a thief with the previous token is detected at the next rotation instead of immediately.
3. Logout fixes. Retries give liveness; only periodic revalidation gives the time bound.
   - Retried back-channel logout until 200 OK: "eventually every app drops the session" holds under fairness (l_retry_live passes; l_base_live without retry violates it). The bound D still fails (l_retry), because delivery delay is unbounded.
   - App revalidates its session at the IdP at least every L (refresh / session check), failing when the IdP session is gone: "no app accepts a session more than D after sign-out" holds when L <= D (l_reval passes with L=2, D=2, both apps' iframes blocked, no BCL retry) and fails when L > D (l_reval_D1). Retry + revalidation passes both properties (l_both_live).
   - Opinion: the safe design is "short session lifetime with forced revalidation" as the guarantee and logout messages as an optimisation. That matches Microsoft's admission quoted in ../vlm41_sso ("will still appear as logged in for the access token's remaining valid time").

## Specs relied on (verbatim, from the official documents, saved in specs/)

- OpenID Connect Back-Channel Logout 1.0 (openid.net/specs/openid-connect-backchannel-1_0.html): "The OP should not retransmit a Back-Channel Logout Request unless the OP suspects that previous transmissions may have failed due to potentially recoverable errors (such as network outage or temporary service interruption at either the OP or RP). ... In all other cases, the OP SHOULD NOT retransmit a Back-Channel Logout Request." Also: "If the logout succeeded, the RP MUST respond with HTTP 200 OK." (Modelled: 200 OK = ack; retry only on "lost".)
- OpenID Connect Front-Channel Logout 1.0 (openid.net/specs/openid-connect-frontchannel-1_0.html), section "User Agents Blocking Access to Third-Party Content": "This can prevent the ability for notifications from the OP at the RP from being able to access the RP's User Agent state to implement local logout actions. In particular, the frontchannel_logout_uri might not be able to access the RP's login state when rendered by the OP in an iframe because the iframe is in a different origin than the OP's page."
- RFC 9700 (OAuth 2.0 Security BCP) section 4.14.2: "Refresh token rotation: the authorization server issues a new refresh token with every access token refresh response. The previous refresh token is invalidated, but information about the relationship is retained by the authorization server. If a refresh token is compromised and subsequently used by both the attacker and the legitimate client, one of them will present an invalidated refresh token, which will inform the authorization server of the breach. The authorization server cannot determine which party submitted the invalid refresh token, but it will revoke the active refresh token. This stops the attack at the cost of forcing the legitimate client to obtain a fresh authorization grant."

## Model limits (honest scope)

- Small bounds only: 2-3 tabs, 2 apps, at most 4 rotations, time up to 4-6 ticks. Passing results are bounded checks, not proofs.
- Tabs of one app share one session/token store; per-tab UI staleness is not modelled. Separate apps hold separate token families, so the refresh race is per app.
- Revalidation is assumed to reach the IdP and to fail closed; if apps fail open when the IdP is unreachable, the bound D is lost (inference, not checked).
- No attacker, so the security cost of each fix is reasoned, not checked. Next step if wanted: add a thief holding a copied token and check "theft is detected within k rotations" for the replay rule.
- No new literature search: this task relied only on the three standards above; prior agents' literature is in ../vlm26_sso and ../vlm41_sso. No papers added to the collection.

## Files

tla/Refresh.tla, tla/Logout.tla (models); tla/*.cfg and *.out (each configuration and TLC output); tla/runall_refresh.sh; specs/ (downloaded standards); tools/tla2tools.jar (TLA+ tools v1.8.0).
