# Candidate PhD directions: formal verification of web and distributed systems (vlm48)

(authored by agents unless marked 🧑)

Note: Scholar CAPTCHA'd every searcher after 2-7 queries, so prior-work checks are partly web search and agent memory. Read every "none found" as weak, not as proof of absence. Nothing was published; nothing was added to paper_collection.

Terms used below. Safety: nothing bad ever happens. Liveness: something good eventually happens. To prove "refines": to prove the code can only do what a simpler model allows. Raft: a protocol where servers agree on one ordered log of commands. Linearizable read: a read that sees the latest completed write.

## Part 1. The 20 directions (2 lines each: what is broken, what we would prove)

1. Stale-check-then-write race in AWS's DNS automation
   - Broken: AWS DynamoDB outage, Oct 2025, https://aws.amazon.com/message/101925/ : "The check that was made at the start of the plan application process, which ensures that the plan is newer than the previously applied plan, was stale by this time due to the unusually high delays in Enactor processing."
   - Prove: with N independent workers ("enactors") applying versioned plans and a cleaner that deletes old plans, the applied plan never goes back to an older one, the DNS record is never empty, and the system never gets stuck, for any delay of any worker.

2. Crash in the middle of "apply" leaves replicas different (etcd)
   - Broken: etcd v3.5 postmortem, https://github.com/etcd-io/etcd/blob/main/Documentation/postmortems/v3.5-data-inconsistency.md : "If etcd crashed after consistency index is saved, but before to apply workflow finished it would lead to data inconsistency."
   - Prove: for a Raft-backed key-value store, after any crash and restart at any instruction, each replica's data equals the committed log applied up to its saved index.

3. Linearizable reads in a Raft system (CCF)
   - Broken: microsoft/CCF PR #6167, https://github.com/microsoft/CCF/pull/6167 : "Document non-linearizability of read-only transactions in rare system conditions"; issue #5636 : "Without this, the read might be stale, even if forwarding is set to always and the client waits until the read txn ID is committed."
   - Prove: for each read path (lease, read-index, etc.) reads are linearizable given a clock-drift bound and message-delay assumptions, and state exactly which assumption breaks when they are not.

4. Does the Kubernetes API server give the guarantees verified controllers assume?
   - Broken: kubernetes/kubernetes #59848, https://github.com/kubernetes/kubernetes/issues/59848 : "Because a read serviced by the watch cache can be arbitrarily delayed, a client that connects to that api server can read an arbitrarily old history."
   - Prove: a model of the API server's list/watch reads meets the read guarantees that verified controllers (Anvil) assume, or we list the exact conditions under which it does not.

5. Retry storms: provable recovery time after a correlated crash
   - Broken: Google Cloud incident, 2025-06-12, https://status.cloud.google.com/incidents/ow5i3PPK96RduMcb1SsW : "Service Control did not have the appropriate randomized exponential backoff implemented to avoid this."
   - Prove: for clients with retry policy P against a server of capacity C, after a mass restart the system returns to normal within time T for all loads below a stated bound, and a stuck overloaded state ("metastable") exists otherwise.

6. Deductive proof of Raft membership changes against the real implementation (CCF)
   - Broken: CCF NSDI'25 Sec. 7, bug "Incorrect election quorum tally": "CCF was tallying election quorums against the union of active configurations (the current configuration plus any pending reconfigurations), rather than against each indi[vidual configuration]". Latent: found by the authors, no production incident. Tracker: https://github.com/microsoft/CCF/issues/5220
   - Prove: the consensus code refines a spec that includes membership changes, so one leader per term and no lost committed entries hold for arbitrary change sequences, not only one node at a time.

7. Load balancer keeps sending requests to a dead backend (Envoy)
   - Broken: Envoy issue #39737 (open, 2025-06-04), https://github.com/envoyproxy/envoy/issues/39737 : "When one of the backend endpoint is rebooted (not process-killed), the total TPS observed by the proxy drops to almost zero in several seconds, then recover to normal in several seconds."
   - Prove: from the config knobs (timeouts, check interval, thresholds, number of choices), if a backend stops answering then within a computed time the share of requests sent to it is below epsilon and total throughput stays above a floor; usable as a config checker.

8. Config file that one component produces and another crashes on (Cloudflare)
   - Broken: Cloudflare, 18 Nov 2025, https://blog.cloudflare.com/18-november-2025-outage/ : "The software had a limit on the size of the feature file that was below its doubled size. That caused the software to fail."
   - Prove: the config loader never crashes and never replaces the last-good config with an invalid one; stronger, every file the generator can output (any old or new version during rollout) passes the loader's checks.

9. What a set of service-mesh resources means (Istio/Envoy)
   - Broken: Istio issue #49550, https://github.com/istio/istio/issues/49550 : "there are two SEs defined on the same host but different ports. I expect both port 8080 and 9080 can be accessed. However, only one of them can be accessed in practice, sometimes 8080 while sometimes 9080."
   - Prove: a written meaning for mesh resources (ServiceEntry, VirtualService, ...), and that the Envoy config Istio generates implements it for all resource sets, including independence from the order resources are merged.

10. Microservice cache correctness when the store is weaker than assumed (no incident yet)
   - Broken: NOT found. No public incident was verified for this direction; by the brief's rule it does not qualify yet.
   - Prove: MuCache's consistency guarantee degrades in a stated way (e.g. bounded staleness) when the datastore is not linearizable or requests are not pinned to one shard.

11. Async Rust runtime (Tokio): every submitted task eventually runs, even when dropped or cancelled
   - Broken: tokio issue #8772 (Nov 2026), https://github.com/tokio-rs/tokio/issues/8772 : "a task that drives a `FuturesUnordered` whose futures lock a `tokio::sync::Mutex`, and that also locks the same mutex itself between polls of the set, deadlocks permanently."
   - Prove: for Tokio's Mutex, Semaphore, Notify and timers, under a fair scheduler every task waiting to be woken is eventually woken, even if futures are dropped at any await point.

12. WebAssembly compiler is the trusted base of the sandbox (Cranelift/Wasmtime)
   - Broken: Wasmtime advisory GHSA-897f-g5gm-fmxm, https://github.com/advisories/GHSA-897f-g5gm-fmxm : "A very large Wasm function body, or one that is specially crafted to use many SSA values, can use this to force type-confusion or other arbitrary side-effects and escape the sandbox."
   - Prove: for any size of valid Wasm module, the compiled machine code means the same as the Wasm semantics (or compilation fails cleanly), including that index and branch-offset arithmetic never overflows.

13. Actor/choreography runtimes: an enqueued message must eventually run (Pekko)
   - Broken: Apache Pekko issue #3613 (open, 2026-10-10), https://github.com/apache/pekko/issues/3613 : "The message that was already enqueued stays in a mailbox that is **no longer marked as scheduled**, and nothing ever re-schedules it."
   - Prove: the runtime's mailbox state machine keeps "enqueued implies scheduled or running" even when the thread pool rejects work; a protocol compiled to actors ("choreography") then still follows its global script despite crashes.

14. Two readers of one file format disagree (Rust zip crate)
   - Broken: GHSA-m665-v7pm-7grj, https://github.com/advisories/GHSA-m665-v7pm-7grj : "This discrepancy enables ZIP archives to appear to have different file paths and contents according to which tool is reading them."
   - Prove: from one format spec, the streaming reader and the random-access reader accept exactly the same archives and return the same (name, content) pairs, or reject on mismatch.

15. Verified WebAuthn (passkey) server-side verification library
   - Broken: SimpleWebAuthn advisory GHSA-6hxq-p678-4hr2, https://github.com/advisories/GHSA-6hxq-p678-4hr2 : "The success condition is therefore \"the certs form an internally-consistent chain ending in some self-signed cert\" Rather than \"the chain terminates at one of the configured trust anchors.\""
   - Prove: the server accepts a registration or login response only if every step of the W3C WebAuthn checklist holds (chain ends at a trusted anchor, origin, challenge, counter, cross-origin check).

16. OAuth account linking through connector/integration vendors
   - Broken: Salesloft Drift token theft, Aug 2025, https://cloud.google.com/blog/topics/threat-intelligence/data-theft-salesforce-instances-via-salesloft-drift : "the actor targeted Salesforce customer instances through compromised OAuth tokens associated with the Salesloft Drift third-party application." (This is token theft, not the linking flaw in the source paper.)
   - Prove: in a web-protocol model with malicious connectors and many tenants, a token linked by one user's session cannot be obtained or used by another user or tenant, and which proposed defenses are necessary.

17. Memory bounds for QUIC implementations
   - Broken: quinn-proto GHSA-4w2j-m93h-cj5j, https://github.com/advisories/GHSA-4w2j-m93h-cj5j : "fragments with many gaps (because these cannot be defragmented). In such a scenario, the receiving connection suffers from high buffer overhead, enabling memory exhaustion."
   - Prove: given the advertised flow-control limits L, memory held for peer-controlled state is at most f(L) for every peer behaviour (gaps, duplicate connection IDs, overlapping ACKs).

18. Guard and router read the same URL path differently
   - Broken: @hono/node-server GHSA-jpvv-r467-5p4w, https://github.com/advisories/GHSA-jpvv-r467-5p4w : "A request for `/admin\secret` or `/public\..\admin/secret` reaches the application as `/admin/secret`." Nuxt GHSA-r99w-jh2x-3mg9 needed a second fix for a variant.
   - Prove: for a verified path normalizer, the string the access check sees is the string the router dispatches on, for all request targets; this closes the whole family instead of one variant at a time.

19. Wallet UI shows one transaction, signs another (web3)
   - Broken: Bybit, Feb 2025, https://www.sygnia.co/blog/sygnia-investigation-bybit-hack/ : "JavaScript resources hosted on the AWS S3 bucket serving Safe{Wallet}'s web interface, were modified and injected with malicious code manipulating transactions."
   - Prove: the wallet's display of a transaction is injective on security-relevant fields (chain, contract, recipient, amount, call meaning), and a compromised page can only get signed what the user confirmed in an isolated trusted UI.

20. CSRF middleware vs. what browsers can send cross-origin (source paper missing)
   - Broken: Hono GHSA-46wx-v44x-9hh2 (2026-11-12): "Chromium's hyperlink auditing (`<a ping>`) sends a cross-origin POST with the user's cookies and the content type `text/ping`, which is not in that list." (advisory URL not recorded in the notes; the ID is the pointer)
   - Prove: from a model of which requests a browser can send cross-origin with cookies, the CSRF middleware blocks every one that should be blocked.

## Part 2. Evidence per direction

Key: "Broken" quotes are in Part 1 unless added here. "Unchecked" means prior work was not checked on Scholar.

### 1. DNS planner/enactor stale-write race (merged: dist D1, atc D1, pl 3)

Further broken evidence:
- Same AWS summary, https://aws.amazon.com/message/101925/ : "The root cause of this issue was a latent race condition in the DynamoDB DNS management system that resulted in an incorrect empty DNS record for the service's regional endpoint (dynamodb.us-east-1.amazonaws.com) that the automation failed to repair."
- "Therefore, this did not prevent the older plan from overwriting the newer plan."
- "This situation ultimately required manual operator intervention to correct."
- "The race condition involves an unlikely interaction between two of the DNS Enactors."
- Recency: Oct 2025, one year old.

Theorem details (three notes, kept together):
- safety plus "no stuck state" invariant; liveness (automation eventually repairs any bad state) under fairness.
- Why proof beats testing: trigger needs one enactor delayed across many plan generations plus the cleaner running at the same instant; unbounded delay, so bounded model checking misses it and fault injection rarely hits it.
- Tools proposed: Verus for enactor/planner with a trusted Route53 transaction model; TLA+ (TLAPS, TLC), Apalache or Ivy for the protocol; fix to verify is compare-and-set on generation in the same Route53 transaction, or fencing tokens. Fencing-token correctness is a known pattern, so new content is the proof for the plan/apply/cleanup pipeline, not a new theory. Pl note: Prusti-based refinement plus a liveness layer.

Source papers (three, none names this incident):
- Sun et al., Anvil, OSDI'24, Sec. 9 "Discussion and Future Work": "If the unverified controllers are custom controllers not modeled in Anvil (§4.3.1), Anvil cannot reason about their interactions with verified controllers, and hence cannot rule out bugs caused by conflicting interactions." and "We plan to extend Anvil to admit multiple verified controllers and verify the interactions among them in a modular way." https://www.usenix.org/system/files/osdi24-sun-xudong.pdf
- Lu et al., "One-Size-Fits-None: Understanding and Enhancing Slow-Fault Tolerance in Modern Distributed Systems", NSDI '25, https://www.usenix.org/system/files/nsdi25-lu.pdf , "Limitations" of their detector ADR (paragraph after Fig. 10): "Limitations. ADR cannot detect slow faults that appear during start-up. ... Finally, ADR assumes developers already know where to check for slow faults." Also Finding 10: "All studied systems use static timeouts." Fit is indirect (empirical, detection-based, no correctness guarantee). Section number not verified.
- Bily, Pereira, Muller, "A Refinement Methodology for Distributed Programs in Rust", PACMPL 2025 (ACM DOI 10.1145/3763119; conference not confirmed), Sec. 7 Conclusion: "As future work, we plan to more thoroughly address initialisation in distributed systems and liveness properties." Abstract: "existing refinement techniques have limitations that impede their practical usefulness." Case studies include Memcached.

Prior work:
- Scholar snippet: "Welder: Compositional Liveness Verification of Cluster Control Planes" (SOSP 2026, seen only as a snippet; ACM PDF not fetchable, not read): "verify a composition of four practical Kubernetes controllers". Covers composition and liveness on Kubernetes.
- Believed gap (unchecked beyond that): safety of check-then-act with versioned plans and cleanup under unbounded delay, outside Kubernetes. Need to read Welder.
- Must (OOPSLA 2024): "While Must's API does not have an explicit notion of time, one could model timeouts by using the nondeterministic choice operator." Checks bounded configurations only.
- Scholar also listed "Validating traces of distributed programs against TLA+ specifications" and "Compiling distributed system models with PGo" (titles only).
- No formal model of the AWS case found; TLA+ reproductions of the incident not checked.

Caveats: AWS code is not public, so we would verify a reconstruction of the published protocol. Liveness for real code is hard; the refinement-paper authors hold the tool and state this as their own next step. Notes' own verdict: strongest real failure; paper tie weak. Kivi (ATC'24, "We do not model when controllers themselves encounter issues. Hence we omit error handling.") could pair with this: retry in the enactor is the omitted part.

### 2. etcd crash atomicity (dist D2)

- Broken: etcd v3.5 data inconsistency postmortem (2022-04-20; bug in v3.5.0, 2021). Summary: "Code refactor in v3.5.0 resulted in consistent index not being saved atomically. Independent crash could lead to committed transactions are not reflected on all the members."
- Caveat: 2022 report, 2021 release; real but not 2025. Keep if the human accepts 2022.
- Why proof beats testing: reporters needed "frequent crashes" under load; the crash point is any instruction inside apply; a crash-Hoare-style proof covers all of them. Tool: Perennial/Grove (Coq/Iris, Go) or Verus with a crash model of the storage backend.
- Source: CCF, Howard et al., NSDI'25, Sec. 8: "Despite modern hardware and advances in tooling, we found that exhaustive model checking, at our level of abstraction, took significant time to complete. This led us to limit the state space more than we would have liked. We could have used a proof system, such as the TLA+ Proof System, instead of a model checker." https://www.usenix.org/system/files/nsdi25-howard.pdf
- Source: Grove, SOSP'23, Sec. 1: "One limitation is that Grove is only able to verify safety properties, ensuring that a system never returns the wrong results." (Not the crash point itself; Grove does model crashes.)
- Weak link: the papers do not name the etcd apply/index split as future work; this direction is the note author's inference from the incident plus the proof-vs-model-check remark.
- Prior: Grove/Perennial prove crash recovery for a Go key-value store (vKV) with a log; no verified Raft-backed store matching a real engine's apply/index split found (unchecked on Scholar).
- Note author's ranking: middle.

### 3. CCF linearizable reads (dist D3)

- Broken details: PR text: "[Click here to interactively explore the 12-step counterexample documenting non-linearizability of read-only transactions in rare system conditions.]" Issue #5636 "More efficient support for linearizable reads": "This is because the primary who served the read may no longer be the current primary." https://github.com/microsoft/CCF/issues/5636 . PR opened 2024-05-05. Found by spec, not a production incident; the documented behavior is real in shipped CCF.
- Theorem: read path R (lease/PreVote/leader-stickiness/read-index variant) gives linearizable reads given clock-drift bound epsilon and delay assumptions; show the counterexample class exactly when assumptions fail. Why proof beats testing: 12-step counterexample with a deposed primary and delayed commit; Jepsen-style tests see it only on rare timing. Tools: TLA+/TLAPS for protocol; Verus for implementation; Grove's ghost-time lease method.
- Source: CCF NSDI'25, Sec. 5: "Following our success with the consensus spec and a discussion regarding the linearizability of read-only transactions [60], we decided to formalize the possible externally visible behaviors of a CCF service in TLA+" and "By design this spec does not model the internal details of the service itself". Grove Sec. 3.1: "This assumes that node clocks are synchronized to within known bounds (on the order of less than a second, for the purposes of vKV's use of leases)."
- Prior: Grove proves lease-based reads for vKV; no proof for CCF-style signature/commit-index reads found (unchecked). Overlap with Grove is real: novelty would be the multi-read-path comparison and the failure condition, not leases themselves.
- Note author's ranking: strongest (with 1).

### 4. Kubernetes API server contract (dist D4)

- Broken details: same issue, "`node-1` starts `pod-0` (uid 1) and `node-2` is already running `pod-0` (uid 2)." Caveat: opened 2018-02-14, still open, last updated 2025-04-30 (90 comments). Real and unresolved but not new; no recent post-2024 instance found in a quick search.
- Theorem: a TLA+/Verus model of apiserver list/watch (resourceVersion semantics, watch cache, HA apiservers) satisfies the read guarantees Anvil's trusted environment model assumes, or lists exact failing conditions. Why proof beats testing: needs partition plus arbitrary cache delay plus kubelet restart. Tool: TLA+ model checking to find conditions, then a Verus-checked shim.
- Source: Anvil Sec. 9: "We also plan to ensure the quality of the trusted model of the environment, the shim layer, and external APIs using lightweight formal methods." https://www.usenix.org/system/files/osdi24-sun-xudong.pdf
- Prior: not checked on Scholar (blocked). Anvil/Sieve/Acto-style tools test or trust the model; no formal API-server consistency model recalled, not verified.
- Note author's ranking: weakest (old issue).

### 5. Retry storms and bounded recovery (dist D5)

- Broken details: "Within some of our larger regions, such as us-central-1, as Service Control tasks restarted, it created a herd effect on the underlying infrastructure it depends on (i.e. that Spanner table), overloading the infrastructure. Service Control did not have the appropriate randomized exponential backoff implemented to avoid this. It took up to ~2h 40 mins to fully resolve in us-central-1"
- Why proof beats testing: herd needs fleet scale and a correlated restart. Tool: timed model (TLA+ with real time, or Verus plus a timed-systems library) tied to client library code.
- Source: Grove, SOSP'23, Sec. 4.2: "This is because Grove is limited to safety properties—ensuring that vRSM never returns the wrong result—as opposed to liveness, such as guaranteeing that a client will receive a response." Anvil Sec. 10 context: liveness proved only for the controller's own eventual reconcile, not time bounds.
- Prior (Scholar snippets): "Analyzing metastable failures" (Isaacs, Alvaro, Majumdar, HotOS/ACM 2025) "restrict ourselves to the setting of retry storms"; "Performal" (OOPSLA'23) proves latency properties in Dafny; "Lion" (SOSP'26) proves async-runtime liveness in Verus. Retry-storm models and latency proofs exist. Remaining gap (unchecked): connecting them to real client-library/server code.
- Note author's ranking: weakest on novelty.

### 6. Raft reconfiguration proof (dist D6)

- Broken details: Sec. 8: "the operators added and removed nodes one at time. This meant that the bug did not lead to a safety violation and thus remained undiscovered, but could have surfaced if the operators had changed their reconfiguration strategy." Also "the incorrect fix for the commit advance for previous term bug (§7) did not lead to a production incident can be attributed to chance." Quote in Part 1 was cut by a page break in extraction. Issue #5220 (2023-04-26): spec/impl mismatch on initial configuration.
- Theorem: the C++/Rust consensus code (or its trace-validated spec) refines the TLA+ spec with reconfiguration; election safety and leader completeness hold for arbitrary reconfiguration sequences. Why proof beats testing: CCF's own model checking hit the state-space limit; the bug matters only under non-default operator behavior. Tools: TLAPS for the spec, Verus/Dafny for implementation refinement.
- Source: CCF Sec. 8 (quote in direction 2) continues: "By opting for model checking, we chose to prioritize developer time and accessibility over compute time. As interactive theorem provers continue to advance [13, 75], along with AI-assisted verification [44], this trade-off may no longer be necessary." Also "manually aligning a formal spec with its implementation is possible, we found that trace validation is a more systematic and efficient approach". Sec. 7 detail: "48 hours of exhaustive model checking of the consensus spec on a 128 core machine revealed that CCF was tallying election quorums against the union of active configurations".
- Prior (Scholar snippets): "TraceLink: Linking Implementations with Their Verified Designs" (Hackett, Beschastnikh, 2025); "Validating traces of distributed programs against TLA+ specifications" (Cirstea, Kuppe et al., SoSyM 2026); etcd-io/raft issue #111 (TLA+ spec and trace validation, 2023). These cover trace validation, not deductive proof of the implementation. Verified Raft work (Verdi, Ivy, Grove) predates 2023; whether any proves a production reconfiguring Raft is unchecked.
- Note author's ranking: middle.

### 7. Load balancer health checks (atc D2)

- Broken details: also "Requests are stucked by the rebooted endpoint, leading to near-complete TPS drop across the service." The proxy keeps picking the dead host because its active-request count is lowest or tied (Envoy 1.34.1). Second instance, AWS NLB, same postmortem as direction 1: "The alternating health check results increased the load on the health check subsystem, causing it to degrade, resulting in delays in health checks and triggering automatic AZ DNS failover to occur."
- Theorem: model picker (power-of-N-choices on in-flight counts), health checker, outlier detector and client timeouts as a timed system; bound B(timeouts, check interval, thresholds, choice_count) on traffic to a frozen backend, goodput floor, and no oscillation-driven positive feedback in the health-check subsystem. Why proof beats testing: safe region depends on the product of 6+ knobs; the issue config has consecutive_5xx 700 and consecutive_local_origin_failure 20 against a 3 s timeout. Tools: UPPAAL or TLA+ real-time for bounds; Rust model with Kani/Verus for the picker.
- Source: Wydrowski et al. (Google), "Load is not what you should balance: Introducing Prequal", NSDI '24, https://www.usenix.org/system/files/nsdi24-wydrowski.pdf , Sec. 4, "Error aversion to avoid sinkholing": "Prequal includes some heuristics to avoid sinkholing, but since they are not central to our contribution, we have chosen to simplify our exposition by omitting details." Fit: an omission, not a stated future-work sentence.
- Prior: not checked on Scholar. No formal model of Envoy least-request plus outlier detection known. Related: "Analyzing Metastable Failures", HotOS '25, https://sigops.org/s/conferences/hotos/2025/papers/hotos25-106.pdf (retry models, not LB-specific as far as the snippet showed).
- Caveat: the Envoy issue is one user's report with no maintainer diagnosis yet (only "cc" comments); reproduce before claiming.

### 8. Edge config producer/consumer contract (atc D3)

- Broken details: "A change in our underlying ClickHouse query behaviour (explained below) that generates this file caused it to have a large number of duplicate "feature" rows. This changed the size of the previously fixed-size feature configuration file, causing the bots module to trigger an error." Related, not quoted (final report text not fetched): Azure Front Door 29 Oct 2025; secondary reports say a tenant config change bypassed deployment safety due to a software defect.
- Theorem: (a) for all database states and permission schemas in a declared class, the generator output meets the consumer's precondition (size, uniqueness, schema); (b) during staged rollout with versions v and v+1, every consumer accepts every file either producer makes, and a rejected file never replaces the last-good one. Why proof beats testing: the trigger was a permissions change in another system that changed query result multiplicity; tests of either side alone pass. Tools: Verus/Kani on the Rust loader; SMT-checked query-result bounds (Lean/Dafny model of the SQL fragment). Cheap core: "load_config never panics and never replaces last-good state with an invalid state".
- Source: Guo et al. (Meta), "MobileConfig: Remote Configuration Management for Mobile Apps at Hyperscale", NSDI '24, https://www.usenix.org/system/files/nsdi24-guo.pdf , Sec. 3.3: "Although we have a design for MobileConfig to support cross-config consistency by maintaining metadata about matching versions of interdependent configs, it remains unimplemented due to the absence of a genuine need for such complexity." Sec. 8.1 lists production incidents (e.g. a parameter changed from 25 to 0 with no emergency push).
- Prior: not checked on Scholar. Memory, unverified: network-device config verification (Batfish-style) is mature; no proofs about application-config loaders with last-good fallback known.
- Caveats: generator-side bound is hard; consumer-side theorem is the tractable core. Overlaps the "decision propagation" pattern in vlm25_dist; manager should check it is different enough.

### 9. Service-mesh semantics (atc D4)

- Broken details: filed 2024-02-26 (closed). Full quote: "there are two SEs defined on the same host but different ports. I expect both port 8080 and 9080 can be accessed. However, only one of them can be accessed in practice, sometimes 8080 while sometimes 9080. Which port can be accessed seems to be random". Caveat: 2024, not 2025. MeshTest reports 23 new bugs overall (19 confirmed, 10 fixed). Lower impact (a bug, not an outage).
- Theorem: declarative semantics of ServiceEntry/VirtualService/DestinationRule/Gateway (the "service flow CFG") and translation validation: check each generated xDS config against it with SMT, including merge-order independence for same-host resources. Why proof beats testing: MeshTest "covers all pairwise interactions" only; 3-way interactions and ordering nondeterminism are outside. Tools: Lean/Rocq semantics plus an SMT checker in Rust over istiod output; first lemma is merge determinism (bug is a merge that depends on map iteration order).
- Source: Zheng et al., "MeshTest: End-to-End Testing for Service Mesh Traffic Management", NSDI '25, https://www.usenix.org/system/files/nsdi25-zheng-naiqian.pdf , Sec. 6 "Limitations and future work": "MeshTest does not cover all possible input configuration space. Both the input generator and the testing oracle rely on the domain specific service flow model, which can not cover implementation specific details." and "The soundness of test results rely on the correctness of the service flow CFG model." and "MeshTest does not aim to test the state reconciliation of the service mesh system."
- Prior: not checked on Scholar beyond MeshTest. Batfish/Minesweeper are for routers, not meshes; unknown for Istio.

### 10. Microservice cache under weak stores (atc D5)

- Broken: none verified. Closest: Railway incident 2026-03-30 (cited in vlm25_dist/REPORT.md, CDN-purge area, already covered) and Meta cache-consistency work. The note author says by the brief's rule this does not qualify yet. Keep only if someone finds a real incident (e.g. stale cache after autoscaling reshard).
- Theorem sketch: MuCache's guarantee degrades gracefully (causal+ or bounded staleness) under weaker stores and resharding; TLA+ or Rocq.
- Source: Zhang et al., "MuCache: A General Framework for Caching in Microservice Graphs", NSDI '24, https://www.usenix.org/system/files/nsdi24-zhang-haoran.pdf , "Discussion and Limitations": "The correctness of MuCache depends on the datastores being linearizable" and "An interesting avenue for future research would be to lift the requirement for hard affinity, allowing for more flexible load balancing and autoscaling."
- Prior: not checked. MuCache already has a formal development (paper: "our formal development"), so this extends an existing proof.
- Note author's ranking: weakest.

### 11. Tokio liveness and cancellation (pl 1)

- Broken details: Tokio 1.54.0/1.54.1; issue closed 2026-11-09. Fuller quote: "Since 1.54.0, a task that drives a `FuturesUnordered` whose futures lock a `tokio::sync::Mutex`, and that also locks the same mutex itself between polls of the set, deadlocks permanently. Nothing in user code holds the guard across an `.await`. All runtime threads park, CPU is zero, and the program never finishes." Fact: regression introduced by a fix (#8371), found only by a user's production CLI; tests did not catch it. Also "With 50 futures it passes; from roughly 200 it hangs every time". Related: https://github.com/tokio-rs/tokio/issues/8695 "time: `Interval` drops an elapsed timer without synchronizing with the time driver" (title only read); https://github.com/tokio-rs/tokio/issues/8175 "When reviewing the cancel safety documentation across Tokio I noticed that there exists multiple versions of what should be a standardized description."
- Theorem (inference): every registered waker obligation is eventually discharged under a fair scheduler, even with drops at any await point; cancel safety in select! as a stated property, not prose. Tools: extend Jackdaw/LART with wake-one and obligation revocation; or Verus with a ghost obligation ledger; Loom-style model checking as bug-finder first.
- Source: Li, Beschastnikh, Summers, "Modular Responsiveness Verification of Rust Async Runtimes", arXiv:2610.09198 (Oct 2026, preprint, no venue stated), Sec. 7 "Limitations and Future Work":
  - "Known gaps in the existing model of LART include: a wake-one primitive (non-deterministically discharge one obligation in a repository) for single-permit synchronization idioms (e.g., tokio's Mutex, Semaphore), and cross-poll reasoning that would let invariants established in a prior poll discharge later checks."
  - "Cancellation and task drop. Async tasks can typically be cancelled at any await point, at which time any wakers the task has registered with reactors must be reclaimed. Our model currently has no notion of obligation revocation and no mechanism for a reactor to learn that a transferred obligation becomes irrelevant"
  - "Real-world async runtime implementations such as tokio use weaker atomic memory accesses for high performance; so far, we have not seen examples in which extra observable behaviors could result, but our technique is not checking this formally"
  - "Jackdaw does not check for mistakes in these annotations".
- Prior: "Lion / Modular Async Runtime Liveness" appeared in Scholar (same group, title only); check whether Lion is an earlier version. Verus OOPSLA 2023 has no async support in the text read (Sec. 9 lists only mutable borrows, unsafe, type system). Loom exists; its liveness support not checked.
- Caveats: the authors themselves are on it, and they suggest the extension is straightforward, so the cancellation part may be too small for a thesis; the memory-model part (relaxed atomics) is the thesis-sized piece. Note author's ranking: first among pl directions.

### 12. Verified Wasm compiler (merged: pl 2, sec 2)

- Broken details: GHSA-897f-g5gm-fmxm (CVE-2026-115889), published 2026-10-23. Quote: "In Wasmtime prior to v43, the Cranelift compiler backend bit-packs its SSA value indices in a way that can result in silent overflow in release builds, and result in incorrect value references in the IR resulting in arbitrary miscompilation." Impact: "A Wasmtime engine with default settings (using the Cranelift backend) on any architecture/platform could experience a sandbox escape from a specially-crafted Wasm module." Second advisory, GHSA-mghf-wjfp-p5xm (2026-10-28), https://github.com/advisories/GHSA-mghf-wjfp-p5xm : "Wasmtime can compile a Wasm module with more than ~256k targets on one `br_table` instruction in a way that results in an incorrect conditional branch target. ... All versions of Wasmtime/Cranelift that support aarch64, since the initial release of that support in 2020 (before Wasmtime v1.0), are affected." Sat about 6 years. Both need extreme sizes, which explains why fuzzers missed them. Fact: a compiler bug; proofs about source Wasm programs say nothing about it. Server-side Wasm (edge functions, plugins) is web infrastructure.
- Theorem (inference): emitted code for control flow (br_table, branch-offset encoding) and value numbering refines Wasm semantics for all sizes, or compilation fails cleanly with a size-limit check proven sufficient. Why proof beats testing: bugs sit at integer-range boundaries; fuzzers would need megabyte inputs; release-mode overflow is invisible in debug builds. Tools: Kani for packing/offset arithmetic; Verus or Creusot on Cranelift's Rust index/entity layer; refinement against WasmCert or Iris-Wasm. Narrow first target: the entity/index layer.
- Sources:
  - "Iris-Wasm: Robust and Modular Verification of WebAssembly Programs", PLDI 2023 (authors not recorded), end of Sec. 6 (Related Work): "It can be used to rigorously investigate compilers that either target Wasm or compile Wasm down to some low-level assembly language. ... Iris-Wasm sets the groundwork for similar results for realistic compilers involving Wasm." Sec. 4: "an interesting line of future work is to extend Iris-Wasm with various automation techniques, such as the proof search strategy of Mulder et al. [2022], and use it to prove specifications of large real-world programs." (About 3800 Coq lines to verify a 637-byte stack module: cost is a real barrier.)
  - Zhang, Zhao, Xu, Liu, Xie, Tian, Chen, Ji, "Waltzz: WebAssembly Runtime Fuzzing with Stack-Invariant Transformation", USENIX Security 2025, https://www.usenix.org/system/files/usenixsecurity25-zhang-lingming.pdf , Sec. 7 (digit survived extraction, title did not; discussion after RQ4): "Wasm is an evolving language, with many proposals currently under standardization. Presently, WALTZZ supports only the Wasm core specification as this standard is the most widely adopted among runtimes." "around 40% of the bugs involve proposals that are still in progress." "In summary, diversifying target settings could empower WALTZZ to find more bugs, and we leave this as a future direction." The paper's limitation is fuzzing coverage; "so prove instead" is the note author's inference.
  - Scholar titles only, not read: "TMLM: A Taxonomy of Type-Driven Lowering Bugs in WebAssembly JIT Compilers" (SSRN), "Exploring missed optimizations in WebAssembly optimizers" (ISSTA 2023), "CertiCoq-Wasm: A Verified WebAssembly Backend for CertiCoq" (CPP 2025), "WaVe: a verifiably secure WebAssembly sandboxing runtime".
- Prior (memory, not re-verified): WasmCert (Coq), Isabelle Wasm (Watt et al.), VeriWasm (NDSS 2021), Crocus (ASPLOS 2024; verifies Cranelift ISLE rules in SMT, not the Rust data structures here). CertiCoq-Wasm compiles into Wasm, not out of it; WaVe verifies the WASI boundary, not the JIT. No verified Wasm-to-native production compiler found (weak). Unchecked: that Crocus does not already cover br_table lowering.
- Caveats: whole-compiler verification is not thesis-sized; the narrow layer may be too small (a checked-arithmetic Rust lint might do), so frame as verifying the resource-limit contract end to end. Overlap: vlm11_jsengine / vlm14_engine cover JS engines; this is the Wasm/Cranelift side only; check before pitching.

### 13. Actor and choreography runtimes (merged: pl 4, pl 5)

- Broken details (one issue serves both): Pekko #3613 (open, 2026-10-10). Fuller quote: "When `ExecutorService.execute(mailbox)` throws `RejectedExecutionException` twice, `Dispatcher.registerForExecution` resets the mailbox to *idle* and rethrows; `Dispatch.sendMessage` then swallows the exception. The message that was already enqueued stays in a mailbox that is **no longer marked as scheduled**, and nothing ever re-schedules it. If that message was the last step of a request/response protocol, the actor — and everything waiting on it — stalls **permanently**". Same issue: "this recurses without bound and ends in `StackOverflowError`, which `pekko.jvm-exit-on-fatal-error` turns into a **JVM kill**." Second Pekko issue https://github.com/apache/pekko/issues/3689 (open, 2026-10-24) "Replicator.isKnownNode does not cover members first observed in Leaving/Exiting/Down status, so thei..." (title truncated, body not read): CRDT membership, overlaps covered CRDT direction; do not use.
- Honest link: this is an actor-runtime scheduling bug (lost message on a failure path), not a typed-ordering bug and not a choreography flaw. No choreography-system incident was found; the link is the note author's inference (weak). Sound reading: if protocols compile to actors, the target's failure behavior must be in the theorem.
- Theorem (inference): a choreography compiled to a runtime with crash/restart and message loss still refines the global choreography (no deadlock, no lost step); mailbox layer upholds "enqueued implies eventually run" including under executor rejection/restart. Why proof beats testing: failing path needs two executor rejections and the retry logic itself failing; fault injection rarely hits it. Tools: Rocq/Iris for semantics; Verus on a small Rust actor core (mailbox + dispatcher), compare with Pekko's Scala by stating the same invariant in TLA+.
- Sources (all preprints, no venue confirmed):
  - Kløvedal, Plyukhin, Peressotti, Montesi, "Accompanist: A Runtime for Resilient Choreographic Programming", arXiv:2603.20942, Sec. 3.3 "Limitations": "D1. CP requires services to block so they cannot participate in multiple choreographies at once;" "D3. CP does not let services join a running choreography;" "D4. CP requires rewriting the application from scratch." The paper builds a runtime addressing these; no formal correctness theorem for its recovery seen. Sec. 7 related work: "While Chorex does not come with a formal semantics and a formal correctness result for its recovery mechanism, its try-catch mechanism shares some similarities with models explored in the adjacent context of multiparty session types".
  - Plyukhin, Peressotti, Montesi, "Ozone: Fully Out-of-Order Choreographies", arXiv:2401.17403 (section not recorded): "Reasoning about nondeterminism in choreographies is an important topic for future work." Conclusion: "An important subject for future work is confluence. ... but sometimes the nondeterminism is unexpected and causes bugs."
  - Gordon, "Actor Capabilities for Message Ordering" (extended version), arXiv:2502.07958v2 (Sep 2025; Springer chapter 10.1007/978-3-032-05291-9_3 in Scholar; venue not stated in text read), acknowledgments: "Thanks also to Ivan Beschastnikh, for asking me in 2012 how I could apply reference capabilities to distributed systems. It took 13 years, but I think I've finally articulated a good answer, even if handling faults remains future work." Related work: "Establishing a formal relationship between our capabilities and behavioural effects like Caldwell et al.'s ... would be intriguing future work." and "most actor frameworks include both normal and selective receive, making integration of our ideas and theirs interesting future work."
- Prior: Chorex (Elixir) try-catch with checkpoint, unverified. Graversen et al. studied omission failures in choreographies (cited in Accompanist; not read). Scholar titles only: "Probabilistic, Resource-Aware, Asynchronous, Out-of-Order Choreographies" (arXiv 2606.13520), "Real-world choreographic programming: Full-duplex asynchrony and interoperability" (arXiv 2303.03983, believed Programming'23, unchecked). Mailbox types (contrasted in Gordon's related work). Must (OOPSLA 2024) is bounded only. No verified actor runtime found in 5 Scholar queries (weak).
- Caveats: weakest failure-to-theorem link in the pl notes; single bug; venue not PLDI/OOPSLA. Merged from pl 4 and 5 (the notes said they likely merge); may also be a sub-case of direction 11.

### 14. Parser differential between two readers (pl 6)

- Broken details: zip crate (`<= 9.0.4`), published 2026-10-28. Quote: "A critical architectural parser differential exists in the `zip` crate (`<= 9.0.4`) between random-access archive readers (`ZipArchive`) and streaming readers (`ZipStreamReader`). `ZipArchive` considers the Central Directory File Header (CDFH) authoritative and ignores the filename declared in the Local File Header (LFH). In contrast, `ZipStreamReader` relies exclusively on the Local File Header (LFH) when extracting files to the filesystem." Web relevance: upload scanners and extractors are separate readers; the classic smuggling shape, like the covered HTTP framing direction but for archives. Other 2026 Rust parser advisories (titles only): yara-x GHSA-2jx3-ff3v-j7jj "Unvalidated deserialization in safe `Rules::deserialize` allows memory corruption and UB"; vibeio-http GHSA-fx4f-mhw4-qm7j "DoS vulnerability in HTTP/1.x chunked encoding parser".
- Theorem details: why proof beats testing: differential fuzzing finds examples but cannot show none remain; two authority points (LFH vs CDFH) force a rejection rule. Tool: Vest-style verified combinators in Verus, one declarative format spec from which both reader shapes are derived and proved equivalent.
- Source: Verus, OOPSLA 2023 (Lattuada et al., arXiv 2303.05491), Sec. 9 "Limitations": "Verus relies on borrow-checking rules and hence cannot reason about traditional Rust unsafe code." Limits parsers using unsafe. Scholar surfaced "Vest: Verified, Secure, High-Performance Parsing and Serialization for Rust" (USENIX Security; not fetched, the URL returned HTML not PDF) and "Secure Parsing and Serializing with Separation Logic Applied to CBOR, CDDL, and COSE" (title only). No verbatim future-work quote for Vest: this direction lacks a verified parser-paper limitation quote. Open item: fetch Vest's limitations section.
- Prior: Vest and EverParse-family tools verify one parser against a spec and prove round-trip. None found proving equivalence of two reader shapes (not verified; "not found in 1 Scholar query").
- Caveats: depends on the unread Vest paper; ZIP is messy; single advisory.

### 15. Verified WebAuthn relying-party library (sec 1)

- Broken details: published 2026-09-04. Also: "`validateCertificatePath()` does not verify that an attestation's certificate chain actually terminates at a configured trust anchor. When walking the chain it stops at the first self-signed certificate it finds (which could be user-supplied), and exits early." Advisory rates it "low" severity: attestation trust only, not login bypass; still a real spec-step failure.
- Theorem details: accept(response) implies every step of WebAuthn L3 Sec. 7.1/7.2 holds; includes the topOrigin/cross-origin-iframe check. Why proof beats testing: single early `break` on a path needing an attacker-chosen chain; test suites use honest vectors; a proof forces every spec step to be discharged. Tools: Rust library with Verus or Creusot over a spec transcribed from W3C text; or F* with HACL*/EverCrypt; Lean/Coq executable step-list predicate then refinement.
- Source: Jannett, Mayer, Westers, Mladenov, Mainka, Schwenk, "The State of Passkeys: Studying the Adoption and Security of Passkeys on the Web", USENIX Security 2026, https://www.usenix.org/system/files/usenixsecurity26-jannett.pdf
  - Sec. 9 Concluding Remarks: "Future work may also extend its use beyond websites to test passkey libraries [78] and third-party services that promise to streamline passkey adoption [75]."
  - Sec. 6: "We found that all but one website failed to validate the built-in clickjacking protections of WebAuthn. Without additional safeguards, attackers could trick users into registering or authenticating passkeys on unintended sites."
  - Related work, "Formal Analyses": "The FIDO2 standards have been examined with formal methods to prove their security and privacy, identify potential weaknesses, and investigate post-quantum security of the underlying protocols [9, 10, 11, 12, 35, 46, 47, 48]. While these works concentrate on the standards, our study focuses on how WebAuthn is used on the Internet." (States the gap: standard analyzed, RP code not.)
- Prior: standard-level only: provable security of FIDO2 (Barbosa et al.); Tamarin models (Scholar: "Formal verification of FIDO2 with human interaction", "Formal Verification of Peer-Assisted FIDO2 Passkey Recovery Protocol with Tamarin"). No verified WebAuthn RP implementation found in 6 Scholar lists or web search; not exhaustively checked.
- Caveats: modest scope (one library); contribution would be spec-to-code method, not new crypto. Note author's ranking: sec directions ordered strongest first.

### 16. OAuth account linking in connector ecosystems (sec 3)

- Broken details: window "as early as Aug. 8, 2025 through at least Aug. 18, 2025". Caveat from notes: incident is token theft from a connector vendor, not the session-fixation flaw in the paper; it shows connector-held tokens are the real blast radius. The protocol flaw has no incident URL beyond the paper: "Responsible Disclosure. To date, we have received acknowledgments from 20 vendors, with over 15 confirmed fixes and a total of $35,850 in bug bounties." (Luo et al. S&P 2026, Sec. 1). No public bug report URL found.
- Theorem details: WIM-style model (web infrastructure model, Fett-Kuesters-Schmitz) with honest/malicious connectors, multi-tenant OAuth-as-a-Service, cross-user-agent flows; session integrity plus tenant isolation; the proof also shows which of defenses D1-D3 are necessary. Why proof beats testing: multi-party interleaving across origins and user agents; the paper's own tool is static and "a lower bound". Tools: manual WIM proofs, Lean/Isabelle mechanization of WIM, or Tamarin with browser rules (Tamarin/ProVerif alone model the web poorly).
- Sources:
  - Luo, Wang, Fung, Lau, "Demystifying the (In)Security of OAuth-based Account Linking in Connector Ecosystems", IEEE S&P 2026, https://mobitec.ie.cuhk.edu.hk/connector-oauth-security/paper.pdf , Sec. 9 Conclusion: "This work represents an initial step toward addressing these gaps; while the proposed defenses are intuitive and empirically motivated, formal security proofs remain important future work." Appendix C, Meta-Review: "Mitigations. The defenses presented are intuitive but not formally analyzed or proven to be robust."
  - Luo et al., "Exploiting and Securing OAuth 2.0 in Integration Platforms", USENIX Security 2025, https://www.usenix.org/system/files/conference/usenixsecurity25/sec24winter-prepub-332-luo.pdf ; related work lists "formal analysis [7]" as prior art; Appendix A defense titled "Limitations of issuer Defense for Integration Platform".
- Prior: WIM OAuth proofs (Fett, Kuesters, Schmitz, CCS 2016) and FAPI 2.0 (Scholar: "Formal security analysis of the OpenID FAPI 2.0 family of protocols", "The grant negotiation and authorization protocol: attacking, fixing, and verifying an emerging standard", Hauck's OID4VP thesis). None found modeling OaaS multitenancy or connector-bot linking (from titles only; unchecked in text).
- Overlap: vlm26_sso / vlm41_sso / vlm42_shib (login/logout consistency) and vlm10_agent (agent security) are adjacent; confirm with those reports.

### 17. QUIC resource bounds (sec 4)

- Broken details: published 2026-07-24, severity "high". Repeated pattern: quic-go CVE-2025-64702 "quic-go HTTP/3 QPACK Header Expansion DoS" (2025-12-11); CVE-2024-22189 "QUIC's Connection ID Mechanism vulnerable to Memory Exhaustion Attack" (2024-04-02), https://github.com/advisories/GHSA-c33x-xqrf-c478. Fuller quote: "Readers that read from a `RecvStream` in order ... will be sensitive to peers that send fragments while leaving out early parts of the stream, and in particular, fragments with many gaps".
- Theorem details: why proof beats testing: a bound over all adversarial schedules; fuzzing finds only reached instances (the NDSS 2026 paper says so). Tools: Verus/Prusti on a Rust assembler/CID table with a ghost "bytes held" counter; or Ivy for a protocol-level bound (McMillan-Zuck QUIC spec).
- Sources (venue fit weak):
  - Luo et al., "Bleem: Packet Sequence Oriented Fuzzing for Protocol Implementations", USENIX Security 2023, https://www.usenix.org/system/files/usenixsecurity23-luo-zhengxiong.pdf , Sec. 8: "Second, the current representation of the SSTG cannot always guarantee reproducibility due to its inherent nondeterministic and coarse-grained transition labeling." No formal-methods call.
  - Better fit but NDSS 2026 (outside the three venues): "Identifying Logical Vulnerabilities in QUIC Implementations" (MerCuriuzz), https://www.ndss-symposium.org/wp-content/uploads/2026-s1777-paper.pdf , Sec. VI.B: "we do not necessarily uncover all security issues in QUIC, this is an inherent limitation of fuzzing, which cannot exhaust all possibilities." Related work: "This motivates our future work to integrate automata into MerCuriuzz."
  - No S&P/CCS/USENIX 2023-26 QUIC paper found by web search ("I didn't find a USENIX Security 2024 or 2025 paper specifically about fuzzing QUIC state machines").
- Prior: Ivy QUIC (McMillan & Zuck, SIGCOMM 2019) specs wire behavior and found spec errors; "Network Simulator-centric Compositional Testing" (FORTE 2024). They test, not bound resources (from search summaries).
- Caveat: sibling of the covered HTTP/2 flow-control direction (vlm25_dist); the notes suggest folding into that one rather than a separate thesis.

### 18. Path-interpretation agreement (sec 5)

- Broken details: hono advisory published 2026-11-12. Full quote: "A request for `/admin\secret` or `/public\..\admin/secret` reaches the application as `/admin/secret`. A reverse proxy that follows RFC 3986 forwards the backslash unchanged and applies its path-based rules to the original path, so the request reaches a route the proxy is meant to block." Nuxt GHSA-r99w-jh2x-3mg9, published 2026-11-13, https://github.com/advisories/GHSA-r99w-jh2x-3mg9 : "Nuxt parses a request path that starts with `//` as a URL with a host before rendering a page ... server-side checks keyed on `/admin` do not apply. The fix for GHSA-9v7c-q64q-vv33 in `4.6.3` covered dot segments but not this form." (incomplete fix: patching by test misses variants).
- Theorem details: A(N(r)) = A(route(r)) (single normalization point), plus differential-freedom between two normalizers over RFC 3986 path + WHATWG URL. Honest limit: cannot prove agreement with a third-party proxy unless it is modeled too. Tools: EverParse/F* parser combinators, or Rust normalizer in Verus; bisimulation of two finite transducers (Lean).
- Source (flagged: quote missing): Zhang, Liu, Lin, Zhang, "Be Aware of What You Let Pass: Demystifying URL-based Authentication Bypass Vulnerability in Java Web Applications", ACM CCS 2025, DOI 10.1145/3719027.3765199. PDF not fetched (ACM returned HTML/403; Semantic Scholar openAccessPdf CLOSED). Only Scholar snippets: "performing string operations to parse and normalize the path" and "we focus on UABVuln, another subclass of broken access control". No limitation/future-work quote; do not cite one until the PDF is read. HTTP-garden and related fuzzing papers (arXiv 2405.17737) concern covered HTTP/1.1 framing, not used.
- Prior: parser-differential fuzzing is crowded (Scholar: HTTP garden, Gudifu, PathFault, ReqsMiner). Verified-normalizer angle: none found in that list; unchecked beyond one Scholar page.
- Note author's ranking: lowest priority of the sec six until the CCS 2025 PDF is read.

### 19. Wallet WYSIWYS (sec 6)

- Broken details: Sygnia, full context: "February 19 – JavaScript resources hosted on the AWS S3 bucket serving Safe{Wallet}'s web interface, were modified and injected with malicious code manipulating transactions. The malicious code included an activation condition, set to execute the transaction manipulation only on a specific Bybit's cold wallet." Not a protocol bug: a gap between what the UI shows and what the signer signs, with the browser as the only check.
- Theorem details: why proof beats testing: WalletProbe found UI-truncation and simulator problems by testing 39 extensions; injectivity of a renderer is a clean proof target, testers cannot show absence. Tools: Lean/Coq spec of EIP-712 typed data and transaction display; verified renderer in Rust; hardware-wallet firmware via existing work.
- Source (venue not S&P/CCS/USENIX): Hu, He, Wang, "WalletProbe: A Testing Framework for Browser-based Cryptocurrency Wallet Extensions", arXiv 2504.11735 (published venue not confirmed), https://arxiv.org/pdf/2504.11735 . Limitations: "Our study has three main limitations. First, we do not address attack vectors unrelated to blockchain data, such as private key leaks, as our focus is on blockchain-based technologies. Second, our analysis does not include all existing wallet extensions, given the rapid emergence of new ones." Also "Unfortunately, V1 is an inherent limitation for simulators." (a proof must state what the simulator promises). No S&P/CCS/USENIX wallet paper with a formal-methods limitation found.
- Prior: hardware-wallet and smart-contract verification plentiful (not web); wallet-UI injectivity proof: none found in the one Scholar list seen; unchecked.
- Caveat: renderer property is closer to UI correctness than web protocols; weaker fit with the VL story (confirm with STORY.md).

### 20. CSRF middleware vs browser cross-origin requests (sec, "considered and dropped")

- Broken: Hono GHSA-46wx-v44x-9hh2 (2026-11-12), real and recent (quote in Part 1). URL not recorded in the notes.
- Theorem: a model of which requests a browser can send cross-origin with credentials (Fetch standard), and middleware soundness against it. Good fit for a browser Fetch-standard model.
- Source: none. The note author found no S&P/CCS/USENIX 2023-26 source paper with a limitation sentence (web search: "no 2024-2026 USENIX Security, CCS or S&P paper that studies framework CSRF middleware"). Dropped by the author only for that reason; included here because the brief says directions need not fit a source-paper rule. Flag: source-less.

## Not kept as directions (for the record)

- ATC '24 Kivi (Liu et al., https://www.usenix.org/system/files/atc24-liu-bingzhe.pdf , Appendix C and Sec. 8): "We do not model when controllers themselves encounter issues. Hence we omit error handling. If there are failures caused by the behavior of error handling, we cannot catch them." Real direction (verify Kubernetes controllers including retries) but no recent public incident found, so not kept; pairs with direction 1.
- ATC '24 QDSR (Wei et al.), NSDI '24 Legolas partial-failure (Wu et al., "It would miss bugs triggered by multiple faults"): testing papers, no failure found.
- QUIC logical vulnerabilities (NDSS 2026) as a stand-alone: venue out of scope (used as a source in direction 17).

## Notes carried over

- Already covered in VerifWeb and not repeated: CRDT sync, SSO logout, CDN purge, HTTP framing/flow control, JS engines, Servo, cookies, cross-tab, consent.
- Not covered by the existing reports, per the dist note: cloud controllers and consensus (vlm25_dist, vlm27_queue skimmed).
- Papers the sec note says to add to paper_collection (not done): Jannett USENIX Sec 26 (passkeys), Zhang USENIX Sec 25 (Waltzz), Luo S&P 26 (OAuth connectors), Luo USENIX Sec 25 (integration platforms), Bleem USENIX Sec 23, Hu et al. arXiv 2504.11735 (WalletProbe).
- Unconfirmed venues: Lion/Jackdaw (arXiv 2610.09198), Accompanist (arXiv 2603.20942), Gordon actor capabilities (arXiv 2502.07958), WalletProbe, and the Bily et al. refinement paper (PACMPL 2025, conference unconfirmed).
- One WebSearch call in the sec notes was refused by a safety filter and not retried.
- Direction 7's Envoy issue and direction 13's Pekko issue are single user reports; Tokio, Wasmtime, Pekko, zip, hono and Nuxt advisories carry 2026 dates as recorded in the notes.
