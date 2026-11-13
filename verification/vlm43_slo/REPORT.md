# vlm43_slo: TLA+ model of Shibboleth SAML single logout (SLO)
(authored by agents)

## Takeaway
The model shows that push-only logout (the IdP sends logout messages and the SPs act on them) cannot meet the guarantee "every SP session ends within D, or the user is told which did not". TLC finds a counterexample for each of the three Shibboleth-style schemes. The documented failure is one of them. One fix passes TLC under every fault in the model: make each SP session a lease of length L that the SP must renew with the IdP over the back channel. Logout then ends every session within D = L, even if an SP crashes, the browser tab closes, or the IdP has forgotten the SP. With D = L-1, TLC finds a counterexample, so L is the tightest bound. The cost (opinion): every SP must change, because the SP has to renew the lease and the app's session has to be tied to the SP session. That is the step the Shibboleth page says many app developers refuse.

## Sources (facts, verbatim)
- Shibboleth Concepts, SLOIssues (https://shibboleth.atlassian.net/wiki/spaces/CONCEPT/pages/928645229/SLOIssues, fetched today, saved as src/SLOIssues.txt):
  "When the IdP is using a front-channel binding to send messages it is tossing complete control to the SP (which it hopes will be there to catch it). If the SP is not responsive the process breaks down and the remaining SPs will not receive logout requests. So, in addition to not being able to tell the user what has happened there are also SPs, with active sessions, that are unaware that a failed logout attempt has occurred."
  "The use of the back-channel binding can mitigate almost all the issues presented so far (except the lack of failure information in the SLO response during SP-initiated logout). However, ... the user's session cookie is not available to the application and so the same issues are present; inability to look up the user's session and destroy it."
- Shibboleth IdP 5, LogoutConfiguration (https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199510118/LogoutConfiguration, via the Confluence REST API, saved as src/IdP5_LogoutConfiguration.txt):
  "SLO is a best-effort attempt to end relying party sessions without clearing the browser's cookie and storage state. ... It is deeply imperfect, minimally supported, and should not be viewed as a security feature or treated as reliable. ... It has no future."
  "the browser mediates (i.e. front-channel) a series of logout messages coordinated via iframes, javascript, and in some cases HTML5 storage."
  "a red X for failure or a green checkbox for success. This is typically quite limited in accuracy, and many false positives or negatives should be expected."
  "Propagation to SPs via SOAP when possible is supported more or less automatically"
  "The idp.session.defaultSPlifetime and idp.session.slop properties control how long the IdP will \"remember\" an SP's session. Once elapsed, it's likely that a request for logout will fail from any SP that has expired from the cache."
- SAML 2.0 Profiles, section 4.4 (src/saml-profiles-2.0-os.pdf), lines 1152-1154: "session participants should if possible use a \"front-channel\" binding when initiating this profile to maximize the likelihood that the session authority can propagate the logout successfully to all participants."
- SAML 2.0 Core, section 3.7.3.2 (src/saml-core-2.0-os.pdf), lines 2641-2645: "In the event that not all session participants successfully respond ... the session authority MUST include in its <LogoutResponse> message a second-level status code of urn:oasis:names:tc:SAML:2.0:status:PartialLogout". (Inference: this code says only that some SP failed, not which one.)

## Model (tla/SLO.tla; matrix in tla/matrix.txt; traces in tla/runs/*.out)
- The model has one user, an IdP and 3 SPs, with a discrete clock (MaxTime=6, Timeout=1, Lease=2).
- Assumption: the IdP, the browser and every SP that is up finish their protocol steps before the clock ticks.
- Faults: an SP crashes or recovers; the browser tab closes; the IdP evicts an SP from its session cache (defaultSPlifetime); an app session is not tied to the SP session (the set "Unindexed").
- Two properties:
  - Guarantee: D ticks after logout starts, every SP session has ended or the user was shown a summary that names that SP as failed.
  - NoFalseOk: an SP reported as logged out really is.
- Schemes: chain (sequential redirects), iframe (Shibboleth IdP 5 propagation), soap (the IdP calls each SP over SOAP and then shows a list of failed SPs), lease (the proposal).

## Results (TLC facts)
Each result gives the fault TLC was allowed and what happened.
- chain, crash: the documented failure. s1 is down, so the browser gets an HTTP error and the chain stops. s2 and s3 stay live and the user is told nothing.
- chain, tab closed: violated. Remaining SPs stay live.
- chain, no faults: passes.
- iframe, crash: passes. The dead SP gets a red X after the timeout.
- iframe, tab closed: violated.
- iframe, eviction: violated, and silently. The IdP forgot s1 and s2, so the user sees a "done" page with only s3 green, while s1 and s2 stay live.
- iframe, app session not tied (s2 in Unindexed): NoFalseOk violated. s2 is shown green but still live.
- soap, crash: passes, because the user sees the list of failed SPs.
- soap, crash and tab closed: violated. s2 is down and correctly marked "fail", but nobody sees the list.
- soap, eviction: violated. soap, Unindexed: NoFalseOk violated.
- lease, all faults on, D=L=2: passes (262,048 distinct states).
- lease, D=1: violated. A crashed SP keeps its session until the lease runs out.
- lease at larger bounds (MaxTime=8, Lease=3), all faults on: D=3 passes (284,256 distinct states) and D=2 is violated. The bound D = L holds at both sizes checked.
- lease, Unindexed: NoFalseOk violated. The lease only protects apps whose session is the SP session.

## Inferences and limits
- Why push fails (inference): the user is told only if the browser is still present. The IdP can report only SPs it still remembers. A green check means the SP's own session ended, not the app's. The lease fixes the first two. Only SP-side engineering fixes the third.
- What the lease needs (assumption): SPs honor the lease, SP clocks are within the skew bound (not modeled), and an SP that is up can reach the IdP. If it cannot, the session simply ends, so availability drops instead of safety.
- Possible concern (opinion): the lease is close to existing ideas such as short SessionNotOnOrAfter values and OIDC session refresh. Novelty is doubtful, so check the literature before claiming it. I did no Scholar search this run.
- Not modeled: SP-initiated logout, where the SP receives only PartialLogout; signature checks; third-party cookie blocking in iframes, which I would expect to look like the Unindexed case (not checked); lost messages, as opposed to crashes; larger N and time bounds. The model is bounded, so a pass is not a proof.
- No papers were relied on, so nothing was added to paper_collection. Nothing was published.
