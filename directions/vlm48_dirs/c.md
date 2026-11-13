# vlm48 directions c: practitioner failures 2023-2026
(authored by agents unless marked 🧑)

Source: postmortems, Jepsen analyses, engineering blogs. Quotes were fetched by subagents through WebFetch, which summarizes pages; a quote may differ slightly from the page, so re-check before citing. Mass global outages were excluded (AWS DynamoDB Oct 2025, Cloudflare 1.1.1.1 Jul 2025, Google Service Control Jun 2025). Each direction is a bug class seen in 2+ systems where possible, not a single bug. Scholar prior-work check: done only for direction 1 (open); Scholar CAPTCHA blocked the rest (queries in /tmp/q/queries.txt, resume at line 3).

## 1. client retries that lie about failure
broken: database client libraries retry non-idempotent requests and report "maybe committed" as "failed"; jetcd (https://jepsen.io/analyses/jetcd-0.8.2): "jetcd incorrectly retries non-idempotent requests which may have actually succeeded"
prove: for real client code, every reported failure is definite, and no request is executed twice (exactly-once-or-unknown)
- prior work: Automated Verification of Idempotence for Stateful Serverless Applications (OSDI 2023) verifies idempotence of serverless apps, not database client libraries; APIdemic: Verifying Idempotency of REST API Clients (title only seen, venue/year not seen) is nearby, not checked on real DB clients; If at first you don't succeed, try, try again...? (OOPSLA 2024) finds retry bugs by testing, no proof (Scholar query: formal verification client retry idempotency timeout definite failure)
- jetcd also: "Jetcd returned that failure to the caller—unsafely representing an indefinite failure as if it were definite." Effects: lost update, G1c, aborted reads
- TigerBeetle 0.16.11 (https://jepsen.io/analyses/tigerbeetle-0.16.11): "Requests do not time out. Clients will continuously retry requests until they receive a reply from the cluster."; client close "immediately segfaulted the entire JVM"
- Bufstream/Kafka (https://jepsen.io/analyses/bufstream-0.1.0), KAFKA-17754: a delayed EndTxn "simply commits (or aborts) whatever transaction happens to be in progress."
- why proof: the bug needs a timeout plus a lost reply plus a retry; client libraries are small and many share the pattern

## 2. acknowledged before durable
broken: NATS acks writes before fsync and loses them on crash; NATS 2.12.1 (https://jepsen.io/analyses/nats-2.12.1): "By default, NATS calls `fsync` to flush data to disk only once every two minutes, but acknowledges messages immediately."
prove: Raft/replication safety under a disk model that separates written from fsynced data, on real recovery code (snapshot install, orphan detection)
- NATS also: "nodes would sometimes decide that a stream had been orphaned, and delete all its data files."; split-brain "continued after all nodes were restarted"
- MariaDB Galera 12.1.2 (https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2): "When all nodes crashed at approximately the same time, MariaDB with Galera Cluster regularly lost committed transactions."; a second loss (MDEV-38976) has no known root cause
- note: most consensus proofs (Verdi, IronFleet) assume a perfect disk; crash-consistency work (FSCQ, Perennial) is single-node

## 3. replicas see commits in a different order than the primary
broken: AWS RDS Postgres multi-AZ violates Snapshot Isolation; (https://jepsen.io/analyses/amazon-rds-for-postgresql-17.4): "the order in which a PostgreSQL primary makes transactions visible is determined by an in-memory lock."
prove: visibility order on primary equals log apply order on replicas, or state exactly which weaker isolation the replicated system gives
- same page: "Each fork updates a different row, but neither fork observes the other's effects."
- RDS MySQL (https://jepsen.io/analyses/mysql-8.0.34): "AWS RDS MySQL routinely violated Serializability at Serializable isolation, even in healthy clusters."; cause replica_preserve_commit_order=OFF

## 4. app invariants under the database's real transaction semantics
broken: application logic correct under serial reading breaks under the database's actual semantics; Datomic (https://jepsen.io/analyses/datomic-pro-1.0.7075): "This grant is both approved and denied at the same time. Our invariant has been violated!"
prove: a checker that, given app transaction code and a formal model of the DB's semantics (Datomic, RavenDB, MySQL RR), proves app invariants hold
- Datomic: "In a serial model, the result of two increments would be `2`. In Datomic, it's `1`"; Datomic's own claims held
- RavenDB 6.0.2 (https://jepsen.io/analyses/ravendb-6.0.2): "the default settings caused RavenDB to lose updates constantly, even in single-node clusters without faults."
- MySQL: "MySQL Repeatable Read transactions cannot safely read a value and then write it."
- relevant to web apps: most web backends are such app code over such DBs

## 5. gossiped config that crashes or deadlocks every receiver
broken: one config update spread by gossip deadlocked Fly.io's whole proxy fleet (https://fly.io/infra-log/2024-09-07/): "a poisonous configuration update was rapidly gossiped across our fleet, deadlocking every `fly-proxy` that saw it."
prove: every handler of replicated config terminates, is deadlock-free and rejects malformed input, for all inputs (Rust, lock-order discipline)
- Fly: "The deadlock code path occurs when a specific configuration of virtual service is received in a Corrosion update." Cause: read lock held in `if let` into `else` that takes write lock
- same shape, global so evidence only: Google Service Control Jun 2025 (https://status.cloud.google.com/incidents/ow5i3PPK96RduMcb1SsW): "this metadata was replicated globally within seconds"; "did not have appropriate error handling"
- why proof: input space is all possible configs; fleet-wide blast radius means one bad input is enough

## 6. schema change on a replicated CRDT store
broken: Fly.io schema change made the CRDT layer rewrite every row (https://fly.io/infra-log/2024-11-30/): "the CRDT semantics on the impacted table meant that Corrosion backfilled every row in the table with the default null value"
prove: replicas running mixed schema versions converge, and a migration's sync traffic is bounded
- extends the human's "interesting" CRDT direction (rough12) from documents to databases (Corrosion is Rust, cr-sqlite)

## 7. mixed-version clusters during upgrades
broken: TigerBeetle replicas panic during upgrade (https://jepsen.io/analyses/tigerbeetle-0.16.11): "we observed repeated TigerBeetle crashes with log messages like `panic: checkpoint diverged`."
prove: protocol safety and liveness hold for any mix of version N and N+1 nodes
- same report: "TigerBeetle, surprisingly, has no story for replacing a failed node."
- Fly schema change (direction 6) is another instance

## 8. credential rotation that revokes before the new key is live
broken: Cloudflare R2 rotation deleted old credentials while new ones went to the wrong place (https://blog.cloudflare.com/cloudflare-incident-march-21-2025/): "We later discovered the --env parameter was inadvertently omitted for both Wrangler commands."
prove: "revoke old" is reachable only after every consumer uses the new key, under delayed propagation
- same post: "Old credentials were removed from our storage infrastructure to complete the credential rotation process."

## 9. revocation that never arrives
broken: Tailscale expired node keys stayed usable up to 19 days (https://tailscale.com/security-bulletins, TS-2023-002): "There was a flaw in Tailscale's logic for expiring node keys."
prove: every expired/revoked key leaves every peer's view within a bound (liveness), including when the control server is unreachable
- same: "The longest delay in removal was 19 days, from 2022-12-20 to 2023-01-09." Cause: removal only happened when the netmap changed for other reasons
- caution: human dropped TLS revocation as "sidestepped by expiry"; here expiry itself was the broken part

## 10. overload mistaken for node death in membership
broken: Discord voice hosts all fell out of the hash ring because heartbeats queued behind work (https://discord.com/blog/behind-the-scenes-of-the-3-25-26-voice-outage): "all of the hosts “dropped out” of the consistent hash ring, stopped taking on new syncers"
prove: the liveness/heartbeat path never waits on the data path, so a live node is never removed under bounded load
- same: "refreshing the service registration can also be blocked by the supervisor mailbox growth"

## 11. retry storms that amplify a small failure
broken: Fly.io updates retried during a Consul outage flooded state sync (https://fly.io/infra-log/2024-10-26/): "They pile up, rapidly and dramatically."
prove: load amplification under failure is bounded by a constant independent of fleet size (quantitative/metastability proof)
- weak: Fly Oct 2024 was fleet-wide; Slack 2022 (https://slack.engineering/slacks-incident-on-2-22-22/) is outside the window: "read load increased superlinearly in relation to the percentage of cache misses."
- prior: metastable failures (HotOS'21, OSDI'22) are empirical, not proofs

## 12. progressive rollout that does not contain a bad version
broken: Workers KV bad config spread instead of stopping at canary (https://blog.cloudflare.com/workers-kv-restoring-reliability/): "We found a bug in the deployment logic that led to a broader outage due to an incorrectly defined configuration."
prove: the rollout controller halts before a failing version passes the canary set
- same: Worker left "“frozen” with the previous, invalid configuration"
- Cloudflare Oct 2023 (https://blog.cloudflare.com/cloudflare-incident-on-october-30-2023/): "The deployment tool had a latent bug with how it returns releases and their respective versions."

## 13. recovery that depends on the thing being recovered
broken: Cloudflare's HA control plane depended on one data center (https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/): "dependencies on services exclusively running in PDX-04."
prove: a static check over the service dependency graph: every dependency of an HA service is HA, and rollback tooling has no cycle through the system it repairs
- same: "Our only safe process to recover was to follow a complete bootstrap of the entire facility."
- Oct 2023 KV incident: Access needed KV for JWT checks, so rollback tools failed too (agent summary, no quote)
- caution: may be config analysis, not FV of code

## 14. cross-tenant reuse of cache pages in LLM serving
broken: Workers AI let a request read another request's attention cache (https://blog.cloudflare.com/kv-cache-exposure-remediation/): "attending over stale cache pages that still held data from earlier requests."
prove: a cache page is readable only by the request that owns its current lease; configured capacity ≤ physical capacity
- same: "the KV cache pool on our prefill GPUs only had room for 681,280 tokens" vs 1,048,576 configured
- note: web-serving infra, not classic distributed protocol; isolation proofs over paged allocators (vLLM-style) are plausible

## 15. per-request state leaking across requests in edge runtimes
broken: Workers KV mutated global state as if request-scoped (agent summary of https://blog.cloudflare.com/workers-kv-restoring-reliability/, not verified verbatim)
prove: in a serverless isolate, state written while serving request A is invisible to request B unless declared shared
- weak evidence; needs re-check of the post

## 16. clock and timezone discontinuities in replication scheduling
broken: Slack replication/routing failed on a time config change on DST-end day (https://slack-status.com/2024-11/81f9bbf150e0daac): "had unexpected failures due to a time-logic configuration change."
prove: replication routing and notification dispatch are unaffected by clock jumps, and dispatch is idempotent
- weak: Slack does not say DST was the cause

## not found
- no 2023-2026 first-party correctness postmortems located for Figma, Linear, Shopify, Vercel, Notion, Stripe; lobste.rs/HN only searched, few fetched
