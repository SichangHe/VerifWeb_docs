# Distributed-systems problems on the web worth verifying: privacy and identity candidates

(authored by agents unless marked 🧑)

Scope: reading and search only. Nothing published. Tags: [FACT] quoted from a source; [OPINION] agent judgment; [GAP] searched, nothing found (absence in my searches only, not proof).
Quotes of arXiv PDFs were read via pdftotext locally; other quotes come from WebFetch/WebSearch summaries of the page, so a few are partial (marked "tool-relayed").

## Takeaway

[OPINION] Ranking: (1) consent revocation propagation (TCF/GPP) is strongest; (3) OIDC/CAEP logout and revocation is second and is the most tractable to model; (2) cookie syncing is weakest as a verification target, because it is an adversarial-by-design information leak, not a protocol that is supposed to meet a spec.

Common shape of 1 and 3: an event ("user revoked", "session ended") must reach N independent parties that do not trust or even know each other. The specs give only "SHOULD retry"-style, best-effort delivery and leave enforcement at the receiver unspecified. That is a liveness property ("eventually every party stops") plus a safety property ("no processing after revocation is acknowledged, beyond a bound"). Black-box measurement can observe violations but cannot prove their absence, because the receiving end is server-side.

---

## Candidate 1: consent/revocation propagation (IAB TCF, GPP/GPC, CMPs, OpenRTB)

### Who is hurt, with sources

Users who revoke consent keep being tracked.
- [FACT] Kancherla, Bielova, Santos, Bichhawat, "Johnny Can't Revoke Consent Either" (arXiv 2411.15414, PoPETs 2025), abstract: "we analyzed 281 websites implementing the IAB Europe Transparency & Consent Framework, and found 22 websites that store a positive consent despite user's revocation. Surprisingly, we found that on 101 websites, third parties that have received consent upon user's acceptance, are not informed of revocation, leading to the illegal processing of users' data by such third parties". URL: https://arxiv.org/abs/2411.15414
- [FACT] same paper, limitation (§4.3): "As the third-party notification happens server-side, this may result in some false-positives on our end."
- [FACT] same paper: "57.5% websites do not delete the cookies after consent revocation enabling continuous illegal processing of users' data."

Vendors do not check the signal they are sent (this is about the initial signal, but it is the same receiver-side gap).
- [FACT] Adalytics (Dec 2021), quoted in TechCrunch: "The TCF strings that were designed by IAB Europe do not appear to be honored or parsed correctly by many ad tech vendors". And: "it appears that many take this 'gdpr=0' parameter at face value, without performing any additional server-side checks". URL: https://techcrunch.com/2021/12/17/adalytics-tcf-research/ . Caveats stated there (tool-relayed): not peer reviewed; cannot see processing on vendors' servers.
- [FACT] Belgian DPA ruling, via TechCrunch: under the TCF "adtech vendors receive a consent signal without any technical or organisational measure to ensure that this consent signal is valid or that a vendor has actually received it (rather than generated it)". URL: https://techcrunch.com/2022/02/02/iab-tcf-gdpr-breaches/ (tool-relayed search snippet, not fetched in full; verify before citing).

US opt-out (GPC, USP/GPP strings) does not reach advertisers.
- [FACT] "One String to Rule Them All: Measuring Consent Under the IAB Global Privacy Platform" (arXiv 2611.02014): "Alarmingly, 82.7% of the advertisers in our dataset are never sent a USP or GPP String". Limitation: "we cannot identify third parties who are legally allowed to collect data—even if a user opts-out". URL: https://arxiv.org/html/2611.02014v1 . Note: the paper does not mention OpenRTB (tool-relayed).
- [FACT] Hausladen et al., USENIX Security 2025 (tool-relayed): among sites implementing a privacy string, 44% (1,411/3,226) opted users out via all implemented strings in Dec 2023. URL: https://www.usenix.org/system/files/usenixsecurity25-hausladen.pdf
- [FACT] Enforcement (tool-relayed from a vendor blog, Ketch; unverified, treat as claim): Disney (Feb 2026, CA AG, $2.75M) "GPC honored on one device only". URL: https://www.ketch.com/blog/posts/gpc-compliance-gap . I did not verify this at a primary source.

### Why it is a distributed-systems property
- Safety: after revocation is acknowledged to the user at time t, no vendor in the supply chain processes the user's data for the revoked purpose after t+Δ (Δ = bounded propagation delay). Legal text asks "without undue delay".
- Liveness: every vendor that was told "yes" is eventually told "no" (or the "yes" expires).
- Fan-out is dynamic: header bidding and OpenRTB auctions forward the string to parties the publisher never listed. TCF 2.3 added a Disclosed Vendors segment to address vendors that got signals without being shown (tool-relayed from a search summary; weak source).
- Three stores can disagree: browser cookie, CMP API, and the string embedded in each request (Kancherla et al. RQ3 asks exactly this).
- [OPINION] Core difficulty is an unreliable, asynchronous, mostly pull-less system: the signal rides on whatever request the browser happens to send next. If no further request is sent to vendor V, V never learns of the revocation, so liveness depends on user behavior, not just the network.

### Why testing/measurement cannot settle it
- Processing happens on vendor servers; crawlers see only request headers/cookies (stated limits above in Adalytics and Kancherla et al.).
- Absence of a violation in a crawl is not absence in the protocol: race windows, old strings cached, server-to-server OpenRTB hops are unobservable from the browser.
- Legal exceptions (service-provider contracts) are private (2611.02014 limitation).

### What one would prove, and with what
- [OPINION] Tool: TLA+ (TLC for small configs, Apalache for symbolic) for the protocol model; no need for ProVerif since the threat is non-compliance and loss, not a network attacker.
- Model: actors = user/browser, CMP, publisher, SSP, k vendors; events = grant, revoke, page-load request, bid-request forwarding, string update; channels lossy/delayed.
- Properties: (a) Safety: `Revoked(u,p) at t` implies no `Process(v,u,p)` after t+Δ for any v that was ever sent a positive string. (b) Liveness under fairness: if the user keeps loading pages, every vendor eventually holds a negative string. (c) Counterexample search: show the spec as written (TCF string with no revocation push) admits a trace with permanent violation when the vendor is never contacted again. Expected result [OPINION]: (c) is true, so the contribution is a precise statement of which extra mechanism (server-side revocation push, expiry TTL on consent, or mandatory re-signal on every request) makes (a) and (b) hold.
- Then check that a proposed fix (e.g., a revocation list or short TTL) satisfies (a) and (b) with bounds.

### Closest prior formal work
- [FACT] Pardo and Le Métayer, "Model-Checking the Implementation of Consent" (arXiv 2409.11803, SEFM'24): "TLA+" models checked to show low-level models satisfy GDPR consent requirements; case studies "an implementation of cookie banners and a IoT system communicating via Bluetooth low energy" (tool-relayed; abstract paraphrased by the fetch tool, and the quoted phrases are short fragments). URL: https://arxiv.org/abs/2409.11803 . Closest. [OPINION] It models the controller side of consent, and from the summary does not model multi-vendor propagation; confirm by reading the paper.
- [FACT, tool-relayed] Robol et al., "Consent Verification Monitoring" (TOSEM, arXiv 2206.06406): consent framework formalized in Description Logic with consent and withdrawal events. Monitoring, not distributed propagation.
- [FACT, tool-relayed] Arfelt, Basin, Debois, "Monitoring the GDPR" (MFOTL, MonPoly). Log monitoring.
- [FACT, tool-relayed] Bigraphs + PRISM paper (SoSyM 2025): CTL property "no data remains after consent is withdrawn". Abstract, single controller.
- [FACT, tool-relayed] "Breaking the Illusion" (arXiv 2512.22789, Cosmic): authors note it cannot verify "whether consent choices are actually honored in backend processing, trace data flows to third parties" (paraphrase by search tool; the exact wording not verified).
- [GAP] I found no TLA+/Ivy/Verus model of TCF/GPP string propagation across vendors. Google Scholar not queried (searched with WebSearch only).

### First bite-sized step
Write a ~100-line TLA+ spec: 1 user, 1 CMP, 3 vendors, a string version number per vendor, a "next request" action chosen nondeterministically per vendor, plus a revoke action. Ask TLC for the liveness violation without fairness on requests to each vendor. That reproduces Kancherla et al.'s "101 websites" finding as a 10-line counterexample, then add the TTL/push fix.

---

## Candidate 2: cookie syncing between trackers

### Who is hurt, with sources
- [FACT] Papadopoulos, Kourtellis, Markatos, WWW'19 (arXiv 1805.10505), abstract: CSync lets trackers "merge user data they own, but also reconstruct a user's browsing history, bypassing the same origin policy"; "97% of the regular web users are exposed to CSync"; "CSync increases the number of domains that track the user by a factor of 6.75." URL: https://arxiv.org/abs/1805.10505 (tool-relayed fragments).
- [FACT, tool-relayed] Urban et al., arXiv 1811.08660: GDPR did not change the overall structure of syncing but the number of connections fell by about 40% (search-summary paraphrase).
- [FACT, tool-relayed] Smith, "Review of Cookie Synchronization Detection Methods" (arXiv 2301.02619): studies "define things like party relations and identifier values inconsistently, or not at all" (paraphrase of the search summary, not a verified quote). URL: https://arxiv.org/abs/2301.02619

### Why it is (weakly) a distributed-systems property
- Safety-like: an identifier mapping learned by party A about party B must respect user opt-out/revocation; a revoked or cleared ID must stop being joinable.
- Liveness-like: deletion of a user's cookie at A should eventually delete the mapping at B ("forget" propagation). Syncing creates replicated identity tables with no delete protocol.
- [OPINION] But the primary issue is information flow (what is learned), not agreement or delivery. That is a privacy/noninterference problem, better served by information-flow or differential-privacy reasoning than by TLA+. Browser changes (third-party cookie restrictions) also make the protocol a moving target.

### Why testing/measurement cannot settle it
- Same server-side opacity: CONRAD-type work detects syncing events in request logs ("detect CSync events at real time", even "when the synced IDs are obfuscated"), but cannot see the server-side joins or deletions.
- Detection definitions are inconsistent across studies (Smith survey).

### What one would prove
- [OPINION] A "forget" property: if user clears ID at A, no future join at B can link the old and new IDs. Needs a model of server-side match tables; the interesting part is not provable from outside. ProVerif/Tamarin could model unlinkability as an equivalence property, but the real system violates it by design, so a proof would only say "yes, syncing links users", which is known.

### Closest prior formal work
- [GAP] I found no formal model of cookie syncing; the search tool itself reported "None of the results cover formal modeling or verification of cookie syncing protocols."

### First bite-sized step
Define cookie syncing as a protocol in 2 pages (redirect with ID parameter, match-table insert), then state the "forget" property. Cheap, but [OPINION] likely low payoff.

---

## Candidate 3: OAuth/OIDC across parties, logout and revocation propagation (back-channel/front-channel logout, RFC 7009, CAEP/SSF)

### Who is hurt, with sources
Compromised or ended sessions persist at relying parties.
- [FACT] Ghasemisharif, Ramesh, Checkoway, Kanich, Polakis, "O Single Sign-Off, Where Art Thou?", USENIX Security 2018, abstract (read locally via pdftotext): "Our findings highlight the inherent limitations of prevalent SSO schemes as most services lack the functionality that would allow users to remediate an account takeover. This is exacerbated by the scale of SSO coverage, rendering manual remediation attempts a futile endeavor." They evaluate "95 major web and mobile services". URL: https://www.usenix.org/system/files/conference/usenixsecurity18/sec18-ghasemisharif_0.pdf
- [FACT] same paper, on why no IdP kill-switch exists: "As long as the cookie remains valid, the browser remains logged in to the RP without the need for any further communication with the IdP".
- [GAP] No recent (post-2018) measurement of back-channel logout adoption or failure rate found. Practitioner posts only (e.g., ashishsrivastav.com, dev.to), which I did not treat as evidence.

The specs themselves make weak guarantees (this is the strongest evidence for the property gap).
- [FACT] OIDC Back-Channel Logout 1.0 §2.5 (tool-relayed): the OP "SHOULD NOT retransmit a Back-Channel Logout Request" except on suspected recoverable errors; §1: "the RP's back-channel logout URI must be reachable from all the OPs used"; §2.7: "The mechanism by which the RP achieves this is implementation specific." URL: https://openid.net/specs/openid-connect-backchannel-1_0.html
- [FACT] RFC 7009: "The invalidation takes place immediately, and the token cannot be used again after the revocation." But also: "a propagation delay, for example, in which some servers know about the invalidation while others do not." Servers "SHOULD support the revocation of access tokens". For self-contained tokens: "some (currently non-standardized) backend interaction". URL: https://www.rfc-editor.org/rfc/rfc7009 (tool-relayed). [OPINION] The word "immediately" and the admitted propagation delay are in tension: that is a ready-made specification bug to formalize.
- [FACT] SSF 1.0 (tool-relayed): "The Transmitter MAY drop zero or more events that are held when the stream is paused."; "Event Receivers MUST NOT depend on the Verification Event being transmitted synchronously or in any particular order"; ordering: "the Transmitter MUST make sure that those events are transmitted in the order of time that they were generated" unless later events cancel earlier ones. Acknowledgement semantics deferred to RFC 8935/8936. URL: https://openid.net/specs/openid-sharedsignals-framework-1_0.html
- [FACT] CAEP 1.0 (tool-relayed): "Session Revoked signals that the session identified by the subject has been revoked." and "The spec never requires a specific enforcement action" (the second is the fetch tool's summary, not a verified quote). URL: https://openid.net/specs/openid-caep-1_0-final.html

### Why it is a distributed-systems property
- Safety: once the IdP acknowledges logout/revocation at t, no RP or resource server accepts the session/token after t+Δ. With self-contained JWTs and no introspection, the bound is the token lifetime, not Δ.
- Liveness: every RP that holds a session derived from the IdP session eventually terminates it (back-channel with retries or polling).
- Failure modes are classic: lost message (no retry rule beyond SHOULD), partition (RP unreachable), reordering (login event after logout event for same `sid`), duplicate events, and stream pause/drop in SSF.
- Subtle interleaving [OPINION, to be checked by model]: a new login at an RP racing with an in-flight logout token for the same `sub` with no `sid`: "all sessions at the RP for the End-User" semantics could kill or miss the new session depending on arrival order.

### Why testing/measurement cannot settle it
- Interop testing shows each implementation passes a scripted scenario; the bug class is interleavings of N parties plus failures, which tests sample poorly.
- RP session termination is "implementation specific", so black-box conformance suites cannot check the property the spec cares about.
- [OPINION] Deployed IdPs rarely track which RPs hold sessions (the 2018 paper's finding on lacking functionality), so measurement from outside sees only "logout button works at one site".

### What one would prove, and with what
- [OPINION] Tool: TLA+ again. Model: IdP, k RPs, one resource server, user agent; actions login, logout-at-IdP, send logout token (lossy/dup/reorder), RP receive, token revoke, introspection or JWT expiry; SSF stream with push and poll, pause/drop.
- Properties: (a) bounded staleness safety (Δ = f(retry policy, token TTL, clock skew)); (b) liveness under weak fairness of retry; (c) check "immediately" in RFC 7009 against a model with a propagation delay; expect a counterexample unless access tokens are introspected; (d) cascading refresh/access revocation ("SHOULD also invalidate all access tokens based on the same authorization grant") yields a stale access token window.
- Ivy would be a fit if one wants to prove inductively for unbounded RPs; Verus is a fit only if verifying a real implementation (e.g., a Rust OIDC RP's logout handler) against the spec model, which is a later step.

### Closest prior formal work
- [FACT] Fett, Küsters, Schmitz, "The Web SSO Standard OpenID Connect: In-Depth Formal Security Analysis and Security Guidelines" (CSF 2017, arXiv 1704.08539), read locally: "We do not model less used features, in particular OIDC logout". And: "Since the FKS model has no notion of time, we overapprox-imate by never letting tokens, e.g., id tokens, expire." So the best OIDC formal model explicitly omits logout and time. URL: https://arxiv.org/abs/1704.08539
- [FACT, tool-relayed] Hofmeier, ETH bachelor thesis 2019, Tamarin model of OIDC. URL: https://ethz.ch/content/dam/ethz/special-interest/infk/inst-infsec/information-security-group-dam/research/software/ba-19-hofmeier-oidc.pdf . Not checked for logout.
- [FACT, tool-relayed] OpenID Foundation lists "Formal Security Analysis of the Transmitter Configuration Discovery of the OpenID Shared Signals Framework" (Univ. of Stuttgart, 2024); fixes in draft 03 were issuer mix-up, stream audience mix-up, attacker stream subject insertion. URL: https://openid.net/new-shared-signals-drafts/ and https://openid.net/developers/security-analysis/ . This analyzes discovery and authentication (security), not delivery/liveness of events.
- [FACT, tool-relayed] Fett et al. FAPI analysis, arXiv 1901.11520 (security properties, not logout).
- [GAP] No formal work found on logout, revocation propagation, or CAEP event delivery. Single Sign-Off paper (above) proposes a fix but no formal model.

### First bite-sized step
TLA+ spec of back-channel logout with 1 OP, 2 RPs, lossy channel, one-shot send (as the spec's SHOULD NOT retransmit implies), and a login/logout race on `sub` without `sid`. Check: "after OP logout completes, eventually no RP has a live session". TLC should give a 6-step lossy-message counterexample immediately; the real work is then stating which fix (retry, poll, TTL) restores it.

---

## Summary comparison
- Evidence of real harm: 1 strongest (peer-reviewed measurements plus regulators); 3 solid but dated (2018); 2 solid on prevalence, thin on harm from a failure.
- Formal-gap: all three have no direct prior work; 3 has the closest neighbors (OIDC web-model with logout and time explicitly omitted).
- Tractability: 3 > 1 > 2. Specs for 3 are crisp text with MUST/SHOULD; 1 depends on legal and private vendor behavior.
- Risk: for 1, "correct behavior" is a legal notion (Δ is "undue delay"), so the theorem statement needs an argued parameter. [OPINION] State it with Δ as a parameter and report what Δ each mechanism can guarantee.

## Notes on method
- Searches were WebSearch/WebFetch only; Google Scholar via pb-browser-page-extract was not used, so the "closest prior work" lists may miss papers.
- Anything marked tool-relayed came through a summarizing fetch tool and could contain paraphrase; verify against the primary page before external use.
