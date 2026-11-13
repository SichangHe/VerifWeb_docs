# vlm43_ctlrace: stale control-plane overwrites beyond AWS Oct 2025
(authored by agents unless marked 🧑)

Why: vlm42 showed TLC reproduces the AWS DynamoDB DNS race and that compare-and-set on plan generation fixes it. The question here is whether that is a class (several public outages, one shared fix, one reusable verified component) or a one-off.

Answer, short. FACT: in 2022-2026 public postmortems I found only one more clear case of a stale writer overwriting newer control-plane state (GitHub, 7 Oct 2026), one real but undescribed race (Google Cloud Load Balancing, Sep 2023), and one weak human-level case (Cloudflare, Jun 2022). FACT (TLC): the GitHub case reproduces in 3 states and is fixed by either compare-and-set on config version or an "only up-to-date nodes may lead" election rule. FACT (TLC): a look-alike, Cloudflare Jan 2023, where a whole-record write wiped a token secret, is NOT fixed by compare-and-set, because nothing ran concurrently. OPINION: one reusable "versioned register with compare-and-set" component would prevent the stale-writer subclass (AWS, GitHub, probably Google Cloud), but not the read-modify-write data-loss subclass. Public evidence is thin: 3 clear cases in 5 years.

## Cases (FACT: verbatim quotes, texts saved in dl/)
1. AWS DynamoDB, 19-20 Oct 2025 (baseline, https://aws.amazon.com/message/101925/, dl/aws_dynamodb_dns_2025-10.txt): "Before it begins to apply a new plan, the DNS Enactor makes a one-time check that its plan is newer than the previously applied plan." "the first Enactor (which had been unusually delayed) applied its much older plan to the regional DDB endpoint, overwriting the newer plan." Modelled in vlm42.
2. GitHub, 7 Oct 2026 (https://www.githubstatus.com/incidents/djlmxz2zd0j7, dl/github_stale_routing_node_2026-10.txt): "one of the new machines started with an outdated copy of its records, which still listed database servers we had already retired. When this node came online, it incorrectly modified routing configuration with the outdated records, routing write requests to non-existent database servers." "Each outage ended when one of our established machines with correct configuration became the leader of the quorum and sent the correct configuration." "At 16:52 UTC, an automated maintenance task that did not honor the pause put it back in charge, and the outage happened again." Impact: "two outages of write operations with the same cause, totaling about 19 minutes". Fix: "we are keeping new machines from being elected leader until their records have been checked. We are also changing our systems to reject configuration that point to servers that don't exist and to keep using the last known-good settings instead."
3. Google Cloud Load Balancing, 21-22 Sep 2023 (https://status.cloud.google.com/incidents/skbvoobU4btcxyAthEmu, dl/gcp_gclb_2023.txt): "a change in the leader election process of a component of Google Cloud Load Balancer's configuration management pipeline. This change triggered a race condition in a downstream component in the pipeline, resulting in overwriting some customer configurations with empty configurations." "which were being affected due to natural leader election flips." Impact: "up to 20% of customers' queries failed due to missing configuration". Not modelled: Google does not say who wrote what, so any model would be invented.
4. Cloudflare, 21 Jun 2022 (https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/): root cause was a bad policy order, but recovery was slowed because "network engineers walked over each other's changes, reverting the previous reverts, causing the problem to re-appear sporadically." Concurrent human writers, same pattern, too little detail to model.
5. Contrast, Cloudflare, 24 Jan 2023 (dl/cloudflare_2023-01-24.txt): "Service token read requests redact the “client secret” value by default for security reasons. The “last seen at” update to the service token then used that information from the read did not include the “client secret” and updated the service token with an empty “client secret” on the write." This is an overwrite from a read-modify-write, but it involves no concurrency. The research agent rejected it as "a buggy release, not a race". I kept it as a contrast case.
Rejected after reading (from the research agent): Azure Front Door Oct 2025, both incidents (version-skew metadata, bypassed safeguard), Railway Sep 2026 (rollout ran before the migration, nothing overwritten), Fly.io GRU Sep 2026 (replication bug plus a stale cached peer address), Cloudflare Jul and Nov 2025 (bad configuration). The search found nothing for Slack, Fastly, Meta, Tailscale, Datadog or Heroku. The search was wide but not exhaustive. I don't know whether the Azure PIR texts say more; only summaries were read.

## Models (tla/, TLC from tools/tla2tools.jar, run with -deadlock; outputs in tla/*.out)
- GhRouting.tla, GitHub. Each node holds a record version, and the elected leader pushes its records to the routing config. The model's actions:
  - Retire: a new truth; the leader learns it and pushes it.
  - Sync: followers catch up.
  - Replace: a node restarts from an older snapshot.
  - Elect: the new leader pushes its records.
  - Invariant NoRetiredTargets: config = truth.
  Results, with 3 nodes and MaxVer 3:
  - Buggy: violated in 3 states. A server is retired, n2 (not yet synced) is elected, and it pushes version 1.
  - Fix "cas" (the config store rejects older versions): holds, 108 distinct states, exhaustive.
  - Fix "elect" (a node may lead only if its records are newest): holds, 42 states.
  - INFERENCE: the shortest bug needs only a lagging follower, not a replaced machine. Raft-style "up-to-date candidate" voting covers both cases.
  - ASSUMPTION: the "elect" guard checks every node's records, an all-knowing check. A real implementation would compare against a majority.
- CfToken.tla, Cloudflare 2023 contrast. An updater reads the token record (secret redacted) and writes the whole record back; the owner may rotate the secret. Invariant SecretIntact.
  - Buggy: violated in 3 states.
  - "cas": still violated, because the version has not changed between the read and the write.
  - "patch" (write only the last-seen field): holds.
  - FACT: compare-and-set does not address this subclass.
- VersionedRegister.tla, the generic class: N writers each read the newest version, may be delayed, then write. Invariant Monotone: the register never drops below the newest version written.
  - Blind writes: violated.
  - Check at read time only (the AWS pattern): violated.
  - Compare-and-set at write time: holds (2 writers, MaxVer 3, exhaustive).

## Pattern and fix
- Common pattern (INFERENCE from cases 1-3): an automated writer decides on state S at time t1 (reads a plan, boots from a snapshot, gets elected) and writes S at a later t2 with a blind replace. Newer state written between t1 and t2 is lost. The decision is checked once and the write is unconditional.
- Common fix (FACT for the models): make the write itself conditional. Options:
  - Compare-and-set on a monotone version or generation (AWS, GitHub).
  - Fencing tokens or epochs: the store rejects writes from an older leader epoch. This is the same idea with the leader's term as the version.
  - Leader eligibility tied to up-to-date state (GitHub's own fix).
  GitHub's "reject configuration that point to servers that don't exist" is a separate validity check, not a fix for staleness.
- One reusable verified component? OPINION: yes for the stale-writer subclass. A small library or store API, "a versioned register whose writes require version > current, with an epoch for the writer", has a 25-line TLA+ spec (VersionedRegister) that TLC already checks. A Verus-verified Rust implementation is plausible and small; I did not build it. Limits:
  1. It must be the only path to the store. AWS's clean-up and GitHub's maintenance automation were second writers.
  2. Versions must come from one monotone source.
  3. It does nothing for a whole-record read-modify-write (Cloudflare 2023), which needs field-level patches, or for a bad but newest config (most rejected cases).
  Unknown: how much of real outage volume this class covers. Public evidence shows about 3 clear cases in 2022-2026.

## Not done
- No Google Scholar search and no papers added to the collection. Fencing tokens and compare-and-set are standard; I cited no paper.
- No Verus component was built.
- The Google Cloud case is not modelled because its mechanism is unspecified.
