# vlm42_awsdns: TLA+ model of the AWS DynamoDB DNS race (Oct 2025)
(authored by agents unless marked 🧑)

Why: the 19-20 Oct 2025 us-east-1 outage started with a small, model-checkable race. I wanted to know whether a tiny TLA+ model, built only from AWS's own description, reproduces the outage, and which fix is enough to prevent it. Answer (FACT, from TLC runs): yes, TLC finds the exact outage sequence in 10 states. A per-endpoint compare-and-set on plan generation is enough by itself. A clean-up that only spares the active plan is not.

## Source (FACT, verbatim quotes from https://aws.amazon.com/message/101925/, saved in dl/pm.html and dl/pm.txt)
- Components: "the DNS Planner, monitors the health and capacity of the load balancers and periodically creates a new DNS plan for each of the service's endpoints"; "the DNS Enactor ... enacts DNS plans by applying the required changes in the Amazon Route53 service. For resiliency, the DNS Enactor operates redundantly and fully independently in three different Availability Zones (AZs). Each of these independent instances of the DNS Enactor looks for new plans and attempts to update Route53 by replacing the current plan with a new plan using a Route53 transaction, assuring that each endpoint is updated with a consistent plan even when multiple DNS Enactors attempt to update it concurrently."
- The stale check: "Before it begins to apply a new plan, the DNS Enactor makes a one-time check that its plan is newer than the previously applied plan. ... it is possible to encounter delays as it attempts a transaction and is blocked by another DNS Enactor updating the same endpoint. In these cases, the DNS Enactor will retry each endpoint until the plan is successfully applied to all endpoints."
- The race: "When the second Enactor (applying the newest plan) completed its endpoint updates, it then invoked the plan clean-up process, which identifies plans that are significantly older than the one it just applied and deletes them. At the same time that this clean-up process was invoked, the first Enactor (which had been unusually delayed) applied its much older plan to the regional DDB endpoint, overwriting the newer plan. The check that was made at the start of the plan application process ... was stale by this time ... The second Enactor's clean-up process then deleted this older plan because it was many generations older than the plan it had just applied. As this plan was deleted, all IP addresses for the regional endpoint were immediately removed. Additionally, because the active plan was deleted, the system was left in an inconsistent state that prevented subsequent plan updates from being applied by any DNS Enactors. This situation ultimately required manual operator intervention to correct."
- The fix, which AWS does not describe: "we will fix the race condition scenario and add additional protections to prevent the application of incorrect DNS plans."

## Model (tla/DnsEnactor.tla, about 80 lines; a constant FIXED switches the design)
- Planner: makes generations 1..MaxGen and adds each to a plan store.
- Enactor x: Pick (reads the latest plan and runs the one-time check against the newest generation applied to any endpoint), then one atomic Apply per endpoint in any order and with any delay, then Cleanup (deletes store plans with gen + K < its plan).
- An endpoint resolves iff its current plan is still in the store.
- Safety, NewestApplied: every endpoint's current plan is the newest generation ever applied to it, and that plan still exists. Resolves is the weaker "plan still exists" part.
- Liveness, Converges: <>[] (every endpoint serves the latest plan), assuming weak fairness for enactor steps.
- Fixed design: (1) Apply is a compare-and-set: it writes only if plan gen > the endpoint's current gen and the plan still exists; (2) Cleanup never deletes a plan that any endpoint currently uses.

## Results (FACT; TLC 1.8.0, run with -deadlock; outputs in tla/*.out)
- Buggy, Resolves: violated. The 10-state trace matches the postmortem step for step: planner makes plans 2, 3, 4; enactor a picks 2; enactor b picks 4; b applies e1; a (delayed) overwrites e1 with 2; b applies e2, then cleans up and deletes plans 1 and 2; e1's plan no longer exists, so e1 has no IPs.
- Buggy, NewestApplied: violated earlier, at the overwrite itself.
- Buggy, Converges: violated. After the deletion, the run ends in permanent stuttering: no enactor can ever repair e1 (the "manual operator intervention" state).
- Fixed: both invariants and Converges hold. Small config (2 enactors, 2 endpoints, MaxGen 4, K 1): 605 states. Larger config (3 enactors, 3 endpoints, MaxGen 6): 455,757 states. Both are exhaustive.
- Ablations (tla/abl/), Resolves only:
  - compare-and-set alone: holds. Reason (INFERENCE): compare-and-set keeps every endpoint at or above the cleaner's own plan, so clean-up never reaches an active plan.
  - clean-up guard alone: violated. The old plan is deleted while still in flight; the delayed enactor then installs it after the clean-up.
- OPINION: the root bug is check-then-act. The newer-plan check must happen inside the same Route53 transaction as the write. Protecting the active plan only helps as defence in depth.

## What the postmortem leaves unspecified, and what I assumed
- What "the previously applied plan" is (global, or per endpoint) and where it is stored. Assumed: the newest generation currently in DNS across endpoints, read once at Pick. A per-endpoint read at Pick time is just as stale; I did not check that variant.
- How a deleted plan "removes all IPs". Assumed: a DNS record points to its plan, so it resolves iff the plan exists.
- Why later updates were blocked. Assumed: a transaction that "replaces the current plan" needs the current plan to exist, so it blocks otherwise. This assumption is what produces the liveness failure; another mechanism would also fit the text.
- How old "significantly older" is: K = 1 generation. Whether clean-up and Apply are atomic: each is one atomic step. Number of enactors: 2 in the reproduction, 3 in the larger fixed run. Route53 transactions: atomic per endpoint, and I assume they offer compare-and-set or an equivalent conditional write. I don't know whether Route53's ChangeResourceRecordSets supports such a condition directly; a version record checked inside the same change batch might work, but I have not checked.
- Also not modelled: per-endpoint plan contents (weights/LBs), the IPv6/regional shared plan, enactor crashes, and DNS caching or TTLs.

## Limits
- Bounded model checking only: small constants, not a proof for every size. A TLAPS or Verus proof of the fixed design would be the next step if wanted. I did not do one.
- I did no literature search, so no papers were added to the paper collection.

## Files
- dl/: postmortem (pm.html, pm.txt) and tla2tools.jar
- tla/DnsEnactor.tla, *.cfg, *.out; tla/abl/ (ablations)
