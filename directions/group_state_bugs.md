# Group-state fork and divergence bugs in popular messaging systems

(authored by agents unless marked 🧑)

Request (🧑, relayed by the manager): "It's not worth pursuing because all the buggy things you found are just toy projects. If we can find real mission critical systems like Signal having a bug like this then we can say something about impact. Maybe you can have agents check the popular ones like Signal and Rocket Chat."

Background: vlm48_dirs/d.md section B5 found MLS epoch forks only in small projects and libxmtp.

Labels: FACT = read on the linked page. SECOND-HAND = taken from a search-engine summary and not re-read. INFERENCE = agent reading. Searches were done on 2026-11-14.

## Answer

Real group-state divergence bugs exist in large, mission-critical systems. The strongest cases are:

- Wire: MLS epoch forks fixed in Oct and Nov 2026. This is the same bug class as B5, in a product used by governments.
- Matrix/Synapse: "state resets" that dropped members and changed join rules in rooms on matrix.org.
- Rocket.Chat: an E2EE room-key fork caused by a race.
- Signal: only client-side stale-membership bugs. None is a protocol fork or has a CVE.

WhatsApp, Slack, Discord, Telegram and Zulip had no documented membership or key fork. Only design-level attacks or minor display bugs turned up.

INFERENCE: forks of the MLS kind need a negotiated group state, such as an MLS epoch, Matrix room state or a Rocket.Chat room key. Systems whose servers own membership (Slack, Discord, Telegram, Mattermost) show only stale caches.

## Wire (MLS, used by governments)

User count: none published. Wire says it is "trusted by governments, critical national infrastructure, and 1,800+ organizations worldwide" (https://wire.com, SECOND-HAND). TechCrunch says about 1,800 customers, "five of the world's G7 governments" (https://techcrunch.com/2022/08/12/wire-series-c/, SECOND-HAND).

- Concurrent group creation forks the group, wire-ios PR #5367 (2026-10-08, https://github.com/wireapp/wire-ios/pull/5367), FACT: "If a conversation isn't set up yet and several devices send a message at the same moment, each one creates its own local copy of the group. Only one device wins; the others then receive a "welcome" message from the winner, which they must process to join the real group. Because those devices already have a local group, CoreCrypto rejects the welcome with `ConversationAlreadyExists` and they never join."
  - Impact: losing devices are permanently out of the conversation.
- A missed commit leaves a member on a stale epoch, kalium PR #4612 (2026-10-27, https://github.com/wireapp/kalium/pull/4612), FACT: "If a commit is missed, CoreCrypto can keep buffering later MLS messages indefinitely until epoch difference is greater than 3. ... for 1:1 conversations this recovery almost never starts since the epoch does not change."
  - The iOS twin is wire-ios PR #5504 (2026-11-06). Its ticket title: "Messages are not displayed in 1:1 conversations after being sent/received by users".
- A device that was offline during Proteus-to-MLS migration is locked out, kalium PR #4524 (2026-10-05, https://github.com/wireapp/kalium/pull/4524), FACT: "When B comes back and registers its MLS client, it never joins the migrated conversation."
- Wire added a server-side repair endpoint (https://docs.wire.com/latest/changelog/changelog.html, FACT for the quote, date not verified): "Add a new endpoint `/mls/reset-conversation` which can be used to restore an MLS group that ended up in an invalid state for any reason."
- Gap: these are fix PRs. No user-facing incident report was found.

## Matrix / Element (Synapse)

User count: "its 370k monthly active users" is the matrix.org homeserver only (https://matrix.org/blog/2025/06/funding-homeserver-premium/, FACT). Tchap, the French government's Matrix deployment, reports 360K MAU (SECOND-HAND).

- GrapheneOS room state reset, synapse #14481 (https://github.com/element-hq/synapse/issues/14481, migrated 2023-12-20, original older), FACT: "has been impacted by a major synapse / protocol bug resulting in losing around 1500 members of the room followed by users being unable to join the room. It was acting as if it was set to invite-only mode despite being public."
  - Reporters' words: "We don't know how to reproduce the problem."
- State reset in #rust:matrix.org, synapse #16825 (2024-01-17, https://github.com/element-hq/synapse/issues/16825), FACT: "We have just experienced a state reset in the newly upgraded #rust:matrix.org (room version 10)."
- synapse #19970 (2026-07-15, https://github.com/element-hq/synapse/issues/19970), title: "State resets or blank timelines if unknown `prevs` or origin's `/get_missing_events` omits auth events".
  - The trigger was a bug in another server (a conduwuit derivative). Synapse accepted the bad input.
- An Olm session wedges after a crash, matrix-rust-sdk #3354 (2024-04-25, https://github.com/matrix-org/matrix-rust-sdk/issues/3354), FACT: "this Olm session is now wedged: Alice cannot decrypt any replies from Bob, and ... Bob will be unable to decrypt any further messages from Alice."
  - This is 1:1 key state, not group state.
- Related prior work: Matrix state resolution is direction B2 in vlm48_dirs/d.md.

## Rocket.Chat

User count: "More than 12 million people in over 150 countries use Rocket.Chat." (https://www.rocket.chat/company/about-us, FACT, company claim)

- E2EE room-key fork race, PR #41169 (merged 2026-07-16, https://github.com/RocketChat/Rocket.Chat/pull/41169), FACT: "every online added user triggers a request to the `e2e.setRoomKeyID` endpoint concurrently, which isn't atomic ... This two-phase behavior caused stale states for users who lost the race."
  - The reproduction says: "Observe messages from one or more members render the "incorrect encryption key" ephemeral message for everyone."
  - Ticket SUP-1067. The release that shipped the bug was not checked.
- Third-party PRs #43280 and #43256 (2026-10-28) were closed without merging. They describe members who have no room key and never get one. They are not confirmed by maintainers.
- A malicious member can fork the key on purpose. Schmid, ETH master's thesis, 2024-03-18 (https://ethz.ch/content/dam/ethz/special-interest/infk/inst-infsec/appliedcrypto/education/theses/masters-thesis_noah-schmid.pdf), FACT: "all members will have different e2eKeys and can, therefore, not read messages from other users."

## Signal

User count: no official number. TIME: "Signal doesn't share user numbers, but estimates put them at around 70 million." (https://time.com/collections/time100-companies-2025/7289620/signal/, FACT per the search agent)

- Signal-Android #13604 (2024-06-26, beta 7.10.0, https://github.com/signalapp/Signal-Android/issues/13604): the phone said "You are no longer in the group." while the other members and the desktop app still treated the user as a member.
  - A Signal developer replied (FACT): "This is a bug in the beta version, 7.10.0. It is fixed in a66857a"
  - and: "Any group state change made by you or someone else will resolve this after updating to 7.10.1."
- Signal-Android #13823 (2024-11-28, 7.25.2, https://github.com/signalapp/Signal-Android/issues/13823): a group was out of sync across devices after rapid membership changes.
  - A Signal developer replied (FACT): "Your android device has an outdated view of the membership list (the more likely option)."
  - The root cause was never confirmed. The stale bot closed it as wontfix.
- Signal-Android #11738 (2021-11-06): one member's messages went missing for only one user. Developer: "I have a hopeful fix for this in 5.26.x". The fix was never confirmed.
- Search snippets only, not verified: Signal-iOS #3808 "Messages leak to user no longer in group" and Signal-Desktop #4758 "No longer a member of the group (when i'm a member of the group)".
- None found: a CVE or advisory for Signal group-state desync.
- Not searched: libsignal, Signal-Server, the Signal community forum.

## WhatsApp

User count: more than 3 billion monthly users (Meta Q1 2025 call, SECOND-HAND via news).

- None found: no public bug tracker, CVE or advisory for a group-state desync.
- Academic only. Rösler, Mainka, Schwenk, "More is Less", EuroS&P 2018, abstract (FACT): "the groups' closeness" is "not end-to-end protected", so a server could give members different views.
  - Bug reports about sender keys exist only in unofficial WhatsApp client libraries (e.g., Baileys #2884). They are not evidence about WhatsApp itself.

## Mattermost

User count: no official total. About "20,000 users within the DoD" (SECOND-HAND).

- CVE-2024-12247 (2024-12, https://nvd.nist.gov/vuln/detail/CVE-2024-12247; quote from a third-party mirror, FACT there): the bug "allows users keep old permissions even when permission updates are made," because "the updates don't apply across all cluster nodes."
  - It affected 9.7.x–9.9.x.
  - Impact: nodes in one cluster disagree on a user's permissions.
- CVE-2026-28759 (2026-05-18, https://advisories.gitlab.com/golang/github.com/mattermost/mattermost-server/CVE-2026-28759/): a remote cluster could "remove any user from any channel, including private channels".
  - This is an authorization flaw, not an accidental fork.

## Zulip, Slack, Discord, Telegram

- Zulip: no user count found. The API changelog shows fixes for missing `peer_remove` events, which left client subscriber lists stale. These are display-level only.
- Slack (about 79M MAU, SECOND-HAND, third-party): none found.
- Discord (about 200M MAU, SECOND-HAND): only discord-api-docs #5704 (2022-12-03). A thread member list stays stale after a permission change. Minor.
- Telegram ("significantly over 1 billion monthly active users", Durov 2025-03-20, SECOND-HAND):
  - none found for group membership or keys
  - Telegram has no end-to-end encrypted groups
  - desktop issues about wrong member counts are unconfirmed (tdesktop #28954, #28255)

## Literature (Google Scholar; kept papers in paper_collection)

- Gegenhuber et al., "Send and Pretend", USENIX Security 2026: "the attacker is able to achieve both goals ( G1 , G2 ) for all evaluated and applicable applications"
  - G1 is making group members see different message transcripts.
  - The applications evaluated include Signal and WhatsApp. The attacker is a malicious member, so this is not an accidental bug.
- Unger, PhD thesis, Waterloo 2021: "Insiders can often perform attacks such as rendering the group permanently unusable, causing the state of the group to diverge for the other participants".
- Rösler, master's thesis, Bochum 2018: "different views of participants may result in contradicting sets of members at the same time."
- Not collected because of Cloudflare blocks: Alwen et al., "Fork-resilient continuous group key agreement", CRYPTO 2023; the Wire analysis thesis (Tsouloupas, ETH 2023); Kimura et al., Rocket.Chat E2EE (ePrint 2025/2300).
- None found: a paper reporting an epoch-fork bug in a deployed MLS system.

## Implication for B5 (INFERENCE)

Wire answers the "toy projects" objection for MLS. Wire's own code had forks from concurrent group creation and missed commits in Oct–Nov 2026. Wire is used by governments, but it has no published user count.

Matrix state resets hit the largest public deployment. That supports B2 more than B5.

Signal's evidence is weak: client-side stale views, one beta bug.
