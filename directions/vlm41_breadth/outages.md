# Outage failure classes 2023-2026, for picking a big verification problem
(authored by agents unless marked 🧑)

Date written: 2026-11-10. Nothing was published or contacted.

Conventions. FACT = quoted from the cited page. INFERENCE = mine. Quotes were returned by the WebFetch tool (a small model reading the page), so treat them as near-verbatim and re-check before citing in a paper. Sources are primary (the company's own page) unless marked SECONDARY. I did not find or read: any Meta, Fastly or Zookeeper postmortem from 2023-2026, any 2023-2026 Jepsen report on TiKV, CockroachDB or Kafka itself, or the full text of the CrowdStrike RCA PDF and the OSDI'22 metastable paper (both returned as unreadable PDFs). For those I say "I don't know".

Rust summary (FACT where quoted). The only incident here with a Rust component in the failure path that the vendor confirms is Cloudflare 18 Nov 2025 (FL2). Everything else I could check is not stated to be Rust. Language claims marked "my knowledge" are not from the sources.

## Class 1. Global config / data push with no staged rollout

Takeaway: the single most repeated pattern. A config or data file reaches the whole fleet in seconds, and the consumer cannot survive it.

- Cloudflare, 18 Nov 2025. FACT, https://blog.cloudflare.com/18-november-2025-outage/ (2025): "On 18 November 2025 at 11:20 UTC (all times in this blog are UTC), Cloudflare's network began experiencing significant failures". Core traffic mostly normal "by 14:30"; all normal "As of 17:06". Cloudflare calls it "Cloudflare's worst outage since 2019." Cause: "it was triggered by a change to one of our database systems' permissions"; "That feature file, in turn, doubled in size." "The software had a limit on the size of the feature file that was below its doubled size." Limit "is set to 200, well above our current use of ~60 features."
- Cloudflare, 5 Dec 2025. FACT, https://blog.cloudflare.com/5-december-2025-outage/ (2025; I could not fetch this URL at first, the quotes came from a fetch of the same title, so verify the URL): "approximately 28% of all HTTP traffic served by Cloudflare"; "The incident was resolved at 09:12 (~25 minutes total impact)"; "triggered by changes being made to our body parsing logic" while mitigating CVE-2025-55182.
- Cloudflare's own summary, https://blog.cloudflare.com/fail-small-resilience-plan/ (2025): "we instantaneously deployed a configuration change in our data centers in hundreds of cities"; "a wrong configuration took down our network in seconds."; "Require controlled rollouts for any configuration change that is propagated to the network", called "the most important workstream of our Code Orange plan."
- Google Cloud, 12 Jun 2025. FACT, https://status.cloud.google.com/incidents/ow5i3PPK96RduMcb1SsW (2025): "a policy change was inserted into the regional Spanner tables"; "This policy data contained unintended blank fields."; scope "Global"; "This occurred globally given each regional deployment."; "Incident began at 2025-06-12 10:51 and ended at 2025-06-12 18:18 (all times are US/Pacific)."; "If this had been flag protected, the issue would have been caught in staging."
- Azure Front Door, 29 Oct 2025. FACT, https://azure.status.microsoft/en-us/status/history/?trackingId=YKYN-BWZ (2025): trigger "a specific sequence of customer configuration changes, performed across two different control plane build versions"; "exposed a latent bug in the data plane"; ran "between 15:41 UTC on 29 October and 00:05 UTC on 30 October 2025." Fixes: "an additional 'pre-canary' stage"; "extending the bake time during each stage of the configuration propagation."
- CrowdStrike, 19 Jul 2024. FACT, https://www.crowdstrike.com/en-us/blog/falcon-content-update-preliminary-post-incident-report/ (2024): "On Friday, July 19, 2024 at 04:09 UTC, as part of regular operations, CrowdStrike released a content configuration update"; reverted "at 05:27 UTC". Microsoft, https://blogs.microsoft.com/blog/2024/07/20/helping-our-customers-through-the-crowdstrike-outage/ (2024): "CrowdStrike's update affected 8.5 million Windows devices, or less than one percent of all Windows machines." Fix: "Implement a staggered deployment strategy for Rapid Response Content… starting with a canary deployment."
- Cloudflare 1.1.1.1, 14 Jul 2025. FACT, https://blog.cloudflare.com/cloudflare-1-1-1-1-incident-on-july-14-2025/ (2025): "a misconfiguration of legacy systems used to maintain the infrastructure that advertises Cloudflare's IP addresses"; "The service topology for the 1.1.1.1 Resolver's prefixes was reduced from all locations down to a single, offline location."; "resulting in downtime for 62 minutes".
- Rust: only the Nov 2025 Cloudflare consumer is Rust (see Class 2). Others: not stated. INFERENCE: the push mechanism (what rolls out, to whom, when to stop) is language-independent, so a verified rollout protocol could matter more than a verified language.

## Class 2. Consumer crashes on input it assumed valid (panic, null, out-of-bounds, nil)

Takeaway: the data was bad, but the outage came from the reader crashing instead of degrading. This is where types and proofs of totality bite.

- Cloudflare 18 Nov 2025 (same URL as Class 1). FACT: error text "thread fl2_worker_thread panicked: called Result::unwrap() on an Err value". "Customers deployed on the new FL2 proxy engine, observed HTTP 5xx errors." On old FL: "bot scores were not generated correctly, resulting in all traffic receiving a bot score of zero." The failing code appears only as an image, so I could not read the source. Cloudflare's fix: "Instead of panicking, there should have been a sane set of validated defaults" and "we should not have dropped traffic by default." (fail-small-resilience-plan page.) FACT that the failing proxy is Rust: the 5 Dec post says "our new FL2 proxy, which is written in Rust". This is the strongest Rust hook found.
- Cloudflare 5 Dec 2025 (FL1, Lua). FACT: "attempt to index field 'execute' (a nil value)"; "In our replacement for this code in our new FL2 proxy, which is written in Rust, the error did not occur." So Rust prevented this one, a data point for "Rust semantics help".
- Google Cloud 12 Jun 2025. FACT: "Without the appropriate error handling, the null pointer caused the binary to crash." Language of Service Control: I don't know (the page does not say).
- CrowdStrike 2024. FACT (preliminary PIR): "problematic content in Channel File 291 resulted in an out-of-bounds memory read triggering an exception." It "could not be gracefully handled, resulting in a Windows operating system crash (BSOD)." RCA outline items (https://www.crowdstrike.com/wp-content/uploads/2024/08/Channel-File-291-Incident-Root-Cause-Analysis-08.06.2024.pdf, 2024): "The number of fields in the IPC Template Type was not validated at sensor compile time"; "A runtime array bounds check was missing for Content Interpreter input fields on Channel File 291". SECONDARY (search summary, not read in the PDF): 21 input fields defined vs 20 supplied. The sensor is a Windows kernel driver; language not stated. INFERENCE: C/C++, unverified.
- Azure Front Door 29 Oct 2025: "This incompatibility triggered a crash during asynchronous processing within the data plane service." Language: I don't know.

## Class 3. The validation gate itself is wrong or tests the wrong thing

Takeaway: the checker passed what the runtime could not run.

- CrowdStrike FACT (preliminary PIR): "Due to a bug in the Content Validator, one of the two Template Instances passed validation despite containing problematic content data." RCA outline: "The Content Validator contained a logic error"; "Template Instance validation should expand to include testing within the Content Interpreter".
- Azure 29 Oct 2025 FACT: crash showed up late, so "the bad configuration passed the health checks"; the PIR says it was saved into the 'Last Known Good' snapshot. (My wording of the PIR's content: the fetch tool paraphrased this, verify.) Fix quote: "We are now enforcing complete synchronous processing of each customer configuration, before advancing to production stages."
- INFERENCE: the property "if the validator accepts x, the consumer will not crash on x" is a stated, checkable spec in two of the biggest incidents.

## Class 4. Automation race on shared state (DNS plan overwrite)

- AWS us-east-1, 19-20 Oct 2025. FACT, https://aws.amazon.com/message/101925/ (2025): "a latent race condition in the DynamoDB DNS management system that resulted in an incorrect empty DNS record"; the delayed Enactor "applied its much older plan to the regional DDB endpoint, overwriting the newer plan."; "As this plan was deleted, all IP addresses for the regional endpoint were immediately removed."; "This situation ultimately required manual operator intervention to correct."; "the event started at 11:48 PM PDT on October 19 and ended at 2:20 PM PDT on October 20". Fix: "We have already disabled the DynamoDB DNS Planner and the DNS Enactor automation worldwide." and "we will fix the race condition scenario and add additional protections to prevent the application of incorrect DNS plans".
- Language of Planner/Enactor: I don't know. INFERENCE: this is a textbook model-checking target (TLA+-style: two writers, versioned plans, delete of old plans); small state space, very high impact.

## Class 5. Metastable failure / retry storms / thundering herd

- AWS Oct 2025 (same page). FACT: "DWFM had entered a state of congestive collapse and was unable to make forward progress in recovering droplet leases"; NLB: "This resulted in health checks alternating between failing and healthy." Fix: "we are adding a velocity control mechanism to limit the capacity a single NLB can remove".
- Google 12 Jun 2025. FACT: "Service Control did not have the appropriate randomized exponential backoff implemented to avoid this." "It took up to ~2h 40 mins to fully resolve" in us-central1.
- Cloudflare Dashboard, 12 Sep 2025. FACT, https://blog.cloudflare.com/deep-dive-into-cloudflares-sept-12-dashboard-and-api-outage/ (2025): "The API calls were managed by a React useEffect hook, but we mistakenly included a problematic object in its dependency array."; "the API call executed many times during a single dashboard render instead of just once."; "overwhelming the service, which then failed to recover." Control plane only: "the outage did not affect services on Cloudflare's network."
- GitHub, 17 Aug 2026. SECONDARY only (https://www.pagerly.io/blog/github-outage-postmortem-retry-storm-2026-08-20, 2026): "Impact ran from 13:28 to 21:15 UTC on August 17"; "a total of 7 hours and 47 minutes"; "overly optimistic retry logic overloaded internal load balancers and made everything worse". I did not find GitHub's own page.
- Research context. SECONDARY (search-result summary of OSDI'22 Huang et al., https://www.usenix.org/system/files/osdi22-huang-lexiang.pdf): retry amplification is the most common sustaining effect. I could not read the PDF; I don't know the exact numbers. Verify before use.
- INFERENCE: dynamics (feedback loops) are not what classic verification handles well; this is a research-heavy, less crisp target.

## Class 6. Hidden or circular dependency (control plane and recovery tools depend on the thing that failed)

- Cloudflare Workers KV, 12 Jun 2025. FACT, https://blog.cloudflare.com/cloudflare-service-outage-june-12-2025/ (2025): "a failure in the underlying storage infrastructure used by our Workers KV service"; "Part of this infrastructure is backed by a third-party cloud provider, which experienced an outage today"; "This outage lasted 2 hours and 28 minutes"; "Workers KV saw 90.22% of requests failing"; "Access failed 100% of identity based logins for all application types". The post never names the provider.
- Cloudflare R2, 6 Feb 2025. FACT, https://blog.cloudflare.com/cloudflare-incident-on-february-6-2025/ (2025): "R2 and other services were unavailable for 59 minutes" (08:14-09:13 UTC); "100% of operations against R2 buckets and objects"; recovery slowed because admin tooling "was unavailable because it relies on R2".
- Cloudflare PDX-04, 2 Nov 2023. FACT, https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/ (2023): "a subset of services that were supposed to be on the high availability cluster had dependencies on services exclusively running in PDX-04"; Cloudflare "had never tested fully taking the entire PDX-04 facility offline."; "The incident lasted from November 2 at 11:44 UTC until November 4 at 04:25 UTC."
- Cloudflare Code Orange: "Turnstile went down, so dashboard users without sessions 'were not able to log in to Cloudflare in the moment of most need'" (as returned by the fetch tool; part of this is the tool's paraphrase).
- INFERENCE: a dependency-graph check ("no failover target depends on the failed domain") is mechanical. Lower research novelty, high practical value, but it needs the real graph, which is not public.

## Class 7. Unintended or over-broad automated action

- Heroku, 10-11 Jun 2025. FACT, https://www.heroku.com/blog/summary-of-june-10-outage/ (2025): "An automated operating system update ran on our production infrastructure when it should have been disabled."; "creating up to 24 hours of downtime for many customers"; "it relied on a legacy script that only applied correct routing rules on initial boot."; "No system changes will occur outside our controlled deployment process going forward."
- Cloudflare 6 Feb 2025 (above). FACT: the abuse action "inadvertently disabled the R2 Gateway service instead of the specific endpoint/bucket associated with the report"; "human error and insufficient validation safeguards".
- INFERENCE: spec = "an action's blast radius is within its declared scope"; fits capability/policy checking more than protocol verification.

## Class 8. Expired credentials / certificates

- GitHub, 18 Nov 2025. FACT, https://github.blog/news-insights/company-news/github-availability-report-november-2025/ (2025): "from 20:30 to 21:34 UTC"; "failures on all Git operations, including both SSH and HTTP Git client interactions"; "an expired TLS certificate used for internal service-to-service communication."; "accelerating efforts to eliminate our remaining manually managed certificates."
- INFERENCE: real and repeated, but a monitoring/lifecycle issue; weak fit for formal verification.

## Class 9. Latent defect triggered by maintenance, cache warm-up, or restart

- Slack, 26 Feb 2025. FACT, https://slack-status.com/2025-02-26 (2025): "From 6:45 AM PST to 4:13 PM PST on February 26, 2025, a large percentage of Slack users experienced issues"; "a maintenance action in one of our database systems, which, combined with a latent defect in our caching system"; "approximately 50% of instances relying on this database became unavailable."; Events API backlog until "8:30 AM PST on February 27, 2025" because mitigation "paused the Events API job queue".
- GitHub, 30 Jan 2025. FACT, https://github.blog/news-insights/company-news/github-availability-report-january-2025/ (2025): "between 14:22 UTC and 14:48 UTC"; "at peak the error rate was 44%"; "prolonged due to a lack of automated failover for the caching layer".
- GitHub, 9 Jan 2025: "a deployment which introduced a query that saturated a primary database server" (31 minutes, error rate peaked at "6.85% of update requests").
- GitHub, 13 Jan 2025: "a configuration change related to traffic routing and testing" that "caused our internal load balancer to drop requests between services that Git relies upon"; "all Git operations were unavailable" for 49 minutes.
- Language and exact defect: I don't know.

## Class 10. Replication / consensus durability and safety bugs

- NATS JetStream, Jepsen, 2025. FACT, https://jepsen.io/analyses/nats-2.12.1 (2025): "uses the Raft consensus algorithm to replicate data among nodes"; "By default, NATS calls fsync to flush data to disk only once every two minutes, but acknowledges messages immediately."; one run: "caused NATS to lose 679,153 acknowledged writes out of 1,367,069 total."; "coordinated power failures, or an OS crash on a single node combined with network delays or process pauses" can cause "persistent split-brain." Older versions: "process crashes alone could cause the total loss of a JetStream stream". The page does not state NATS's language (my knowledge: Go).
- etcd v3.5 inconsistency, 2022 (outside 2023-2026, kept as the reference case). FACT, https://github.com/etcd-io/etcd/blob/main/Documentation/postmortems/v3.5-data-inconsistency.md: "when etcd was applying data, it would update the consistent-index first, followed by committing the data. However, these operations were not atomic. If etcd crashed in between, it could lead to data inconsistency"; "fixing the data inconsistency took almost 2 weeks and multiple tries". Later etcd issues: #20059 (May 2025, v3.5.11 inconsistency); resolution I don't know. My knowledge: etcd is Go.
- Other Jepsen 2024-25 reports I found only via search summary (SECONDARY, https://jepsen.io/blog): MariaDB Galera, Bufstream 0.1.0 (2024), Capela (2025), Orkes Conductor. I did not read them.
- Rust: TiKV is Rust (my knowledge); I found no 2023-2026 TiKV safety incident. CockroachDB/Kafka 2023-2026: I don't know.
- INFERENCE: here formal verification has the best track record (Raft proofs, TLA+). The failures above are crash-consistency (fsync, atomic apply), which refinement proofs usually omit. This is a gap, not a solved area.

## Class 11. Failover assumed but untested / no automatic failover

- Cloudflare PDX-04 2023 (Class 6): "had never tested fully taking the entire PDX-04 facility offline."
- GitHub 30 Jan 2025 (Class 9): "lack of automated failover for the caching layer".
- GitHub, 28 May 2025. SECONDARY (search summary of the GitHub May 2025 report, not read): Actions delay from "a misconfiguration in backend caching behavior after a failover". Verify.
- Coinbase, 7 May 2026. SECONDARY (search summary; the Coinbase page returned 403 to me): "three of five matching-engine nodes went down and we lost quorum." I don't know the AWS-side root cause primary source; a tracker claims a cooling failure in one data-center hall, unverified.

## Class 12. Overload from the success path of recovery (herd after restart) and unsafe mitigation

- Google 2025 and AWS 2025 (Class 5): recovery itself created the second outage (Spanner herd; DWFM congestive collapse).
- Slack 2025: the mitigation caused events to be dropped ("Events that piled up while it was paused were never delivered." is the fetch tool's paraphrase).
- Azure Sep 2026. FACT as returned by fetch of https://azure.status.microsoft/en-us/status/history/ (2026): "Paused gateway updates resumed all at once, adding load" (paraphrase by the tool; Tracking ID 7Q30-010), and "Existing request-throttling and load-protection mechanisms did not sufficiently protect critical processing". Verify at the PIR.

## Class 13. Browser and memory-safety exploitation

- GTIG, 2025 zero-days. FACT, https://cloud.google.com/blog/topics/threat-intelligence/2025-zero-day-review (2026): "Google Threat Intelligence Group (GTIG) tracked 90 zero-day vulnerabilities exploited in-the-wild in 2025."; "Browsers accounted for less than 10% of 2025 zero-day exploitation, a marked decrease from the browser-heavy years of 2021-2022. This suggests that browser hardening measures are working."; "memory safety issues (particularly use-after-free [UAF] and out-of-bounds write) accounting for roughly 35% of the vulnerabilities."; "Both the raw number (43) and proportion (48%) of vulnerabilities impacting enterprise technologies reached all-time highs".
- Chrome count 2025. SECONDARY (search results; sources disagree on how many were V8): about eight exploited Chrome zero-days in 2025, including V8 type confusion bugs. I don't know the exact V8 count.
- Chromium (2020, older): about 70% of serious bugs are memory-unsafety, per search summary of https://www.chromium.org/Home/chromium-security/memory-safety/ (not read directly).
- INFERENCE: browser exploitation is shrinking in share, so this is a weaker "outage" story; the engine (V8 JIT) bugs are the residue. Rust relevance: a Rust rewrite does not touch JIT-generated code.

## Class 14. Overlay: physical/regional infrastructure

- Cloudflare PDX-04 2023 (power): "the batteries started to fail after only 4 minutes." Not a verification problem.
- 2026 provider outages (AWS May, Azure Jan/Feb/Jul, Google Aug/Sep/Oct): only SECONDARY trackers (shattered.io, servnetuk, Medium) found; I did not verify against provider pages. I don't know their root causes.

## Cross-cutting reading (INFERENCE, mine)

- Four of the five biggest software-caused events (Cloudflare Nov and Dec 2025, Google Jun 2025, Azure Oct 2025, CrowdStrike 2024) combine Class 1 (global push) with Class 2/3 (crashing consumer, weak validator). The common missing spec is "a bad update must be rejected or degraded, never crash the fleet".
- The AWS Oct 2025 case is the cleanest small protocol bug (Class 4).
- Class 10 has the strongest verification literature but the recent bugs are in durability assumptions that proofs often assume away.
- Rust angle: Cloudflare's own text gives one failure in Rust (unwrap on config parse), one where Rust avoided a Lua nil error. That combination (a panic is a chosen failure policy, not a memory bug) is the cleanest Rust-specific claim I can source.
