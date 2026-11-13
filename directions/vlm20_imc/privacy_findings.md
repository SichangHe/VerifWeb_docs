# Web tracking / privacy plumbing: 8 niche findings (read-only survey, 2026-11-09)
(authored by agents unless marked 🧑)

Method: web search, then downloaded PDFs (kept in ./dl/) and grepped them. Quotes are copied from the PDF text (pdftotext), not from search snippets.
Nothing published. CVE/bug-tracker search found no CVE for any item below.
Caveat: the scope asked for 2023-2026. Items 1 and 7 are arXiv-only for the stated venue (see notes). Venue of item 4 is by template/search, not a proceedings page.

## 1. Consent revoked, but the stored consent string stays positive; third parties never told
- Venue: PoPETs 2025 (arXiv 2411.15414v3; the PoPETs template is in the PDF, I did not see a proceedings page).
- URL: https://arxiv.org/abs/2411.15414
- Quote: "Further, we analyzed 281 websites implementing the IAB Europe Transparency & Consent Framework, and found 22 websites that store a positive consent despite user's revocation."
- Quote: "Surprisingly, we found that on 101 websites, third parties that have received consent upon user's acceptance, are not informed of revocation, leading to the illegal processing of users' data by such third parties according to EU laws."
- Explanation: A CMP writes a TCString (consent bitfield) and hands it to vendors via an API or in request parameters. On revocation, the site UI changes but the stored string is not updated on 22 sites, or the update is never sent to vendors that already got "accept" on 101 sites. So a vendor's last-seen state is "consent".
- Rule violated: GDPR Art. 7(3) plus EDPB guidance: after revocation, the receiver must stop processing. As an invariant: for every vendor v, if the user's latest choice is "revoke", then the last consent state v saw is "no consent".
- Spec gap (good for formal modeling): "TCF v2.2 does not specify any URL parameters to be used for this", and "the specific storage mechanism is not specified in TCF v2.2". The protocol has no revoke-propagation obligation.
- CVE/tracker: none.

## 2. Banner says "reject", string says "legitimate interest", Purpose 1 claimed anyway
- Venue: WWW 2024 (Smith, Sen, Torres-Agüero, Chen), "A Study of GDPR Compliance under the Transparency and Consent Framework".
- URL: https://dl.acm.org/doi/10.1145/3589334.3645618 (PDF https://web.njit.edu/~borcea/papers/acm-www24.pdf)
- Quote: "However, we found that 72.8% of the websites that were TCF compliant claimed legitimate interest as a rationale for overriding the consent choice."
- Quote: "Any visit to a website where legitimate interest is claimed for Purpose 1 means that data is stored on, or accessed from the user's machine for the purpose of identifying the user without their consent."
- Explanation: The TC string has separate consent and legitimate-interest (LI) bit sets per purpose. After a user rejects, many sites still set LI bits, so vendors see a legal basis that needs no consent. Purpose 1 (store/access on device) may not use LI at all, yet 33 crawls on 16 Didomi domains claimed it.
- Rule violated: TCF policy "Purpose 1 requires consent" (LI bit for purpose 1 must be 0). Also a well-formedness rule: some strings were "clearly not TC strings such as the text 'cookie_banner_accepted'".
- Total: 117 crawls to 48 domains violate TCF policy (1.3% of crawls). Odd: all Purpose-1 cases are one CMP (Didomi), i.e. a single code path bug or config.
- CVE/tracker: none.

## 3. GPC honored in one privacy string, not in the sibling string, on the same site
- Venue: USENIX Security 2025 (Hausladen et al.), "Websites' Global Privacy Control Compliance at Scale and over Time".
- URL: https://www.usenix.org/system/files/usenixsecurity25-hausladen.pdf
- Quote: "In December 2023, 44% (1,411/3,226) of such sites opted users out via all implemented privacy strings."
- Quote: "In December 2023, 11% (325/3,074) of sites had inconsistent opt outs."
- Quote (sec 4.3.2): "The biggest inconsistency was 8 sites in the OAC + USPS Opt Out Only category in December 2023. 7/8 (88%) sites were Penske Media Corporation (PMC) [63] sites."
- Explanation: A GPC signal must be copied into each privacy string (USP string, GPP string, OneTrust OptanonConsent cookie). On about one in ten multi-string sites, some strings say opt-out and others say opt-in. One publisher's template rollout (Penske Media) fixed itself in the next crawl, which suggests a config bug, not intent.
- Rule violated: CCPA regs require GPC be treated as a valid opt-out; mechanical invariant: GPC=1 implies every implemented string encodes opt-out, and strings agree with each other.
- Note: a search snippet claimed "110 sites claim to honor GPC but set targeting cookies"; I could not find that number in the PDF. Do not cite it.
- CVE/tracker: none.

## 4. GPP and USP strings contradict each other; opt-out sets almost nothing off
- Venue: arXiv 2611.02014v1 (dated 1 Nov 2026), "One String to Rule Them All: Measuring Consent Under the IAB Global Privacy Platform". No venue stated. Outside the requested venue list; treat as a preprint.
- URL: https://arxiv.org/abs/2611.02014
- Quote: "However, 130 (15.4%) publishers exhibit inconsistencies: 85 (10.1%) publishers set the USP String to opt-out while the GPP String was set to opt-in, whereas 45 (5.3%) publishers did the opposite."
- Quote: "Alarmingly, 82.7% of the advertisers in our dataset are never sent a USP or GPP String, meaning that users' opt-out choices are unlikely to be honored by these parties."
- Quote: "Didomi does not appear to restrict or delete advertiser cookies when users opt-out."
- Explanation: GPP replaced USP in 2024, so sites emit both and the two can disagree. Inside one GPP section, 16 national and 4 California strings had SaleOptOut=1 but other fields contradicted it (e.g. Gpc=0, TargetedAdvertisingOptOut=2; from the tool read, I did not grep these). Opt-out strings exist but most ad requests never carry them.
- Rule violated: internal consistency of the GPP spec (SaleOptOut=1 should imply the other opt-out fields), and propagation: every ad request after opt-out carries a string saying opt-out.
- CVE/tracker: none.

## 5. UID smuggling: partitioned storage defeated by carrying the ID in the URL; 41% of smugglers unlisted
- Venue: IMC 2022 (Randall et al.), "Measuring UID Smuggling in the Wild". Outside 2023-2026, but it is the base paper for items below and for IMC 2023 (Understanding the Privacy Risks of Popular Search Engine Advertising Systems, arXiv 2308.15309, same navigational-tracking theme).
- URL: https://arxiv.org/abs/2203.10188
- Quote: "Indeed, when we compared the dedicated smugglers that we found to the Disconnect list of trackers [15], 41% of them (11 out of 27) were not yet present in the list."
- Quote: "This path existed because the button on instagram.com advertising the Instagram mobile app always appended instagram.com's UID cookie to the navigation request for play.google.com."
- Quote: "A sampling of data collection from one of our crawler machines indicates that 16% of the UIDs we identify have a lifetime of less than 90 days" (grep'd text: "...16% of the UIDs we identify have a lifetime of less than 90 days, and 9% have a lifetime shorter than a month.")
- Explanation: Storage partitioning gives each top-level site its own tracker cookie jar. A decorated link carries the ID in a query parameter across the site boundary, and a redirector (allowed first-party storage) can store it. Firefox's redirect defense depends on a blocklist; Chrome had no defense then.
- Rule violated: the partitioning invariant "state keyed by (top-level site, tracker) cannot link across top-level sites" holds only for storage, not for navigation parameters.
- CVE/tracker: none. This is a design gap, not an implementation bug.

## 6. Related Website Sets: an exception to partitioning users cannot predict
- Venue: IMC 2024 (McQuistin, Snyder, Haddadi, Tyson), "A First Look at Related Website Sets".
- URL: https://www.peteresnyder.com/static/papers/related-sites-imc-2024.pdf (DOI 10.1145/3646547.3689026)
- Quote: "Our findings indicate that 42 (36.8%) of the user determinations in our study are incorrect in privacy-harming ways, where users think that sites are not related, but would be treated as related (and so due less privacy protections) by the Related Website Sets feature."
- Explanation: RWS lets a set of up to six sites share third-party storage despite partitioning, assuming users can tell the sites are related. ccTLD variants need common ownership, but associated sites do not ("they are not required to have common ownership" in the PDF). The rules for set membership are enforced by GitHub review, not by the browser.
- Rule violated: the RWS premise "sites in a set are recognizably the same entity" (user-expectation invariant). Concrete spec hole: unlimited ccTLD variants per set, and associated sites need no ownership proof.
- Status note: a search result says Google retired RWS on 2025-10-17 (not verified from a primary source). Still a clean formal target for "partition exception" logic.
- CVE/tracker: none found.

## 7. Topics API: "noise" is a fixed 5%, so a user's topic history re-identifies them
- Venue: PoPETs 2023 (Jha, Trevisan, Leonardi, Mellia), "On the Robustness of Topics API to a Re-Identification Attack".
- URL: https://petsymposium.org/popets/2023/popets-2023-0098.pdf
- Quote: "Using real traffic traces and realistic population models, we find that the Topics API mitigates but cannot prevent re-identification to take place, as there is a sizeable chance that a user's profile is unique within a website's audience."
- Quote: "Among the mechanisms in place, the Topic API returns at most one topic per epoch (a week), and randomly replaces 5% of actual topics with random ones."
- Explanation: Each caller sees one topic per weekly epoch, and the browser swaps 5% of them for random ones. An attacker on two sites accumulates topics over weeks and matches the profile; success reaches 15-17% in a pool of 1,000 users with under 0.2% false positives. Follow-up (PETS 2024, Beugin and McDaniel) argues the noisy topics can be filtered out (any topic not seen on enough popular sites is probably noise); that claim came from a search snippet and I did not read it.
- Rule violated: the privacy goal (a caller learns only coarse, deniable interests; no cross-site linkage). This is a quantitative information-flow property rather than a boolean rule, which makes it harder to verify formally.
- CVE/tracker: none.

## 8. Server-side tracking: tracker moved behind a first-party name, so blocklists and Safari/Firefox defenses miss it
- Venue: PoPETs 2024(4) (Fouad, Santos, Laperdrix), "The Devil is in the Details: Detection, Measurement and Lawfulness of Server-Side Tracking on the Web".
- URL: https://hal.science/hal-04617727
- Quote: not verified from the PDF (I did not download it). From a search snippet only: "28 websites perform Server-side tracking in a first-party capacity", 389 of 7,367 sites track behind a cloaked domain.
- Explanation: Server-side Google Tag Manager and CNAME or A-record cloaking put the tracker on a subdomain of the site. Cookie lifetime caps and third-party blocking key off the domain name, so the identifier gets first-party treatment. WebKit's CNAME defense caps such cookies at 7 days (https://webkit.org/blog/11338/cname-cloaking-and-bounce-tracking-defense/).
- Rule violated: "third-party tracker identity is determined by the registrable domain in the URL". It fails when DNS makes a third party look first-party. Same class as the PETS 2021 CNAME paper (Dimova et al.).
- CVE/tracker: none. Unverified lead: a Chromium issue titled "Cache partitioning bypass via over-broad URLPattern wildcard in SharedResourceChecker" (issue 520186620) appears in search. The page needs sign-in and I could not read it, so I do not know its date, status or CVE. Treat as unconfirmed.

## Gaps
- No academic bounce-tracking measurement 2023-2026 found beyond item 5; no cookie-syncing paper found in the date range.
- Not read: the 2023 GPC paper by Zimmeck et al. (snippet: only 54/464 sites with a US Privacy String opted users out after GPC).
- Best formal-verification targets: items 1 and 3 (clear state/propagation invariants), item 2 (a precise per-purpose rule), item 6 (a rule hole).
