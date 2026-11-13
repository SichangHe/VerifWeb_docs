# Breadth survey: big problems where formal verification could matter

(authored by agents unless marked 🧑)

Why: the advisors asked for "a big problem that's likely to have significant impact". The biggest software outages of 2024-2025 mostly share one failure: a global config push reaches a consumer that crashes. Formal verification at scale so far covers protocol designs and policy engines, not the code that applies config or replicates data. Evidence (verbatim quotes, URLs, years) is in outages.md (incidents) and fv_side.md (verification work). This file only summarizes. FACT means sourced there, INFERENCE and OPINION mean mine. The ranking is by impact, my opinion.

1. Config pushes that crash the fleet (consumer totality plus staged rollout).
FACT: Cloudflare 18 Nov 2025 (Rust FL2 "called Result::unwrap() on an Err value", "worst outage since 2019"), Cloudflare 5 Dec 2025 (28% of HTTP traffic), Google Cloud 12 Jun 2025 (blank policy fields, null pointer, global), Azure Front Door 29 Oct 2025, CrowdStrike 2024 (8.5M Windows machines).
Broken: a validated update can still crash its reader. The CrowdStrike validator "passed validation despite containing problematic content", and the Azure bad config "passed the health checks".
Theorem (INFERENCE): if the validator accepts x, the consumer does not crash on x and degrades instead. Rollout halts before the fleet fails. Fit: Verus on the Rust consumer (Cloudflare FL2 is Rust), and TLA+/P for the rollout.
Prior FV: I don't know any specific to this. Not solved because current fixes are process fixes like canaries and bake time (FACT, the vendor fix lists), and nobody proves validator/consumer agreement (INFERENCE).

2. Automation races on shared control-plane state.
FACT: AWS us-east-1, 19-20 Oct 2025, about 14.5 h. A delayed DNS Enactor "applied its much older plan … overwriting the newer plan", which deleted all IPs of the DynamoDB endpoint.
Broken: concurrent automation writers had no versioning invariant.
Fit: TLA+/P model checking. The state space is small. The language is unknown.
Prior FV: AWS's own TLA+/P program (Newcombe 2014, PObserve), which did not cover this system (INFERENCE). Not solved because small automation tools rarely get models; they are not "core protocols" (OPINION).

3. Crash-consistency and durability in replicated stores.
FACT: Jepsen on NATS 2.12.1 (2025) lost 679,153 of 1,367,069 acknowledged writes because of fsync every 2 minutes. etcd 3.5 (2022) did a non-atomic apply plus index update, and the fix took "almost 2 weeks".
Broken: the code acknowledges before the data is durable, or the apply is not atomic. Raft proofs usually assume away the disk.
Fit: Verus over Rust stores (TiKV is Rust). Perennial/Grove cover crash safety, in Go.
Not solved because Grove is safety-only at about 12x proof overhead, and ShardStore calls full verification "currently impractical" (FACT, fv_side.md).

4. Implementation conforms to its checked design (design-to-code gap).
FACT: CCF calls its consensus "an unproven algorithm" and uses trace validation. AWS 2014 was "not aware of any such tools". Industry checks code against specs only through logs and tests.
Impact (INFERENCE): this gap underlies problems 2 and 3, since model-checked designs still ship buggy code.
Fit: Verus refinement, or upgrading trace validation toward proof.
Prior FV: IronFleet, Verdi, Grove, Anvil, AutoMan (SOSP 2025). All are research systems. Not solved because of proof cost and spec drift under evolving code (FACT, Woodcock and Larsen 2026).

5. Metastable failures and retry storms.
FACT: AWS Oct 2025 DWFM "congestive collapse", Google Jun 2025 had no "randomized exponential backoff", GitHub Aug 2026 had 7 h 47 m of retry overload (SECONDARY source).
Broken: recovery itself overloads the system.
Fit: weak. FACT: Brooker 2025 says metastability fits neither safety nor liveness. Possibly quantitative or probabilistic models.
Not solved because there is no accepted spec (OPINION: research-heavy, high impact, risky).

6. Liveness of multi-controller cloud control planes (Kubernetes-style).
Impact (INFERENCE): controllers that fight or stall cause hidden partial outages. I found no headline 2023-2026 postmortem, so impact evidence is weak.
Fit: Verus. Anvil proves liveness for one controller in Rust.
Not solved because Anvil assumes the other controllers behave (FACT, fv_side.md). Composing several controllers is open.

7. Hidden or circular dependencies in failover.
FACT: Cloudflare 2 Nov 2023 (the HA cluster depended on PDX-04, about 41 h). R2 6 Feb 2025 ("admin tooling … relies on R2"). Workers KV 12 Jun 2025 (90.22% of requests failed, from a third-party cloud).
Theorem (INFERENCE): no failover path depends on the failed domain. This is a graph check.
Not solved because the real dependency graph is undocumented. OPINION: high value, low verification novelty, Batfish-like.

8. Blast radius of automated actions.
FACT: Heroku Jun 2025 had up to 24 h of downtime from an OS update that ran when it "should have been disabled". A Cloudflare abuse action disabled the whole R2 gateway.
Theorem (INFERENCE): an action only touches its declared scope. Fit: policy/capability checking like Zelkova/Cedar (both FACT at AWS scale).
Not solved: I don't know of work on ops actions specifically.

9. Browser engine exploits (JIT/V8).
FACT: GTIG 2025 found browsers under 10% of 90 zero-days, "a marked decrease", with memory safety at about 35% overall.
Fit: Rust/Servo does not cover JIT-generated code (INFERENCE). The human already rated JS-engine work "too PL" (human_views.txt).
OPINION: shrinking impact, so it ranks low.

10. Spec correctness (is the trusted spec right).
FACT: Cosmos DB says a spec error could have "escaped the notice of those reviewing it". Fonseca 2017 found 16 bugs at the boundary between verified and unverified code.
Cross-cutting: it limits every item above. OPINION: important but hard to make concrete as a project.

Dropped by the human's filters: expired certificates (monitoring, no FV), physical and power failures (not software), CDN purge (the human already said timing makes it unsolvable).

Gaps: no Meta, Fastly or Zookeeper postmortems found for 2023-2026. 2026 incidents come only from secondary sources. Scholar hit a CAPTCHA after 16 queries (not bypassed), so five prior-work queries did not run, including trace validation and liveness. Quotes came through a fetch summarizer, so re-check them before quoting in a paper.
