(authored by agents unless marked 🧑)

Quotes below came from WebFetch (a summarizing tool), so some are fragments; FACT = sourced, OPINION/INFERENCE = mine. Not fetched or not verified are marked.

# Direction 1: exactly-once / transactional semantics in streaming and message queues

Real failures
- Jepsen, Redpanda 21.10.1 (2022). https://jepsen.io/analyses/redpanda-21.10.1 . "with default settings in 21.10.1, any pause, crash, or network partition could cause duplicated writes" and "successfully acknowledged messages" "fail to appear in any client's polls"; one run lost "9,988 out of 11,225 successfully acknowledged messages"; "transactions routinely exhibited aborted reads and circular information flow under normal operation". FACT. Redpanda is C++.
- Jepsen, Bufstream 0.1.0 (2024). https://jepsen.io/analyses/bufstream-0.1.0 . "We found three safety and two liveness issues in Bufstream, including stuck consumers and producers, spurious zero offsets" and "the loss of acknowledged writes in healthy clusters". Also protocol-level: "There is no sequence number to order requests from the same client. There is no concept of a transaction number." A delayed commit from an earlier transaction commits part of a later one (torn transaction); "These issues affect Kafka, Bufstream, and (presumably) other Kafka-compatible systems, and remain unresolved" (KAFKA-17754; KIP-890, open since Nov 2022). FACT. Bufstream is Go.
- Jepsen, NATS 2.12.1 (2025-12-08). https://jepsen.io/analyses/nats-2.12.1 . "lost writes if data files were truncated or corrupted on a minority of nodes"; "the loss of committed writes and persistent split-brain"; cause "(at least in part) by choosing to flush writes to disk every two minutes". FACT. Go. The fsync part overlaps the already-covered durability direction; use only the corruption/split-brain part.
- Apache Iggy (Rust), issue #3635, opened 2026-07-09. https://github.com/apache/iggy/issues/3635 . "For destructive-read sources such as MySQL delete mode, it's actual data loss: the record's gone from the source DB and never landed in Iggy, and nothing gets logged about it." (search-tool paraphrase/quote; page not directly fetched). Tracking issue #4232 "establish at-least-once delivery for sink connectors": https://github.com/apache/iggy/issues/4232 . Related PR #4379 shows a Flink source skipping records 10-19 after restart. FACT that issues exist; I did not read them in full.
- ClickHouse Kafka Connect #873: with exactlyOnce, "a worker that pauses past the session timeout and then resumes writes duplicate rows (the KeeperMap state is not fenced)". https://github.com/ClickHouse/clickhouse-kafka-connect/issues/873 (title only, page not fetched). Same class: a paused zombie writer.
- Not found: any Arroyo or Fluvio exactly-once bug report (search returned none). Do not claim them.

Property to verify (OPINION: my formulation)
For every execution with crashes, pauses, reordering and duplication of network messages: (a) every acknowledged produce appears in the log exactly once, at a stable offset; (b) a consumer in read_committed mode sees all records of a committed transaction and none of an aborted one, in one atomic prefix; (c) a delayed or duplicated EndTxn from an older transaction or epoch of the same producer cannot affect a newer transaction. The Jepsen finding is that (c) fails in Kafka's protocol because requests within one epoch are unordered.

Closest prior verification
- Jack Vanlightly, "Verifying Kafka transactions" diary, TLA+ and Fizzbee, Dec 2024. https://jack-vanlightly.com/analyses/2024/12/3/verifying-kafka-transactions-diary-entry-2-writing-an-initial-tla-spec . FACT: it starts with InitPid, tiny model (2 clients, 2 brokers, 1 partition, 1 transactional id). Blog, not peer reviewed; I did not check how far the series got.
- "Model checking exactly-once", Exactly Once blog, 2020, TLA+ models. https://exactly-once.github.io/posts/model-checking-exactly-once/ . Generic, no Kafka protocol.
- arXiv 2608.00501, "Machine-Checked Dual-Write Recovery from a Commit Log" (Isabelle/HOL). Found by search only; not read.
- Open (INFERENCE): I found no peer-reviewed verification of the Kafka transaction protocol including the KIP-890 fix, nor of any Rust log or broker implementation. Absence of evidence from one search session only.

Tractability
- OPINION: the protocol-level part (KIP-890 TLA+/Apalache model, prove (c)) is a few months and not PhD-scale alone; Vanlightly is already on it, so scoop risk is high. A PhD-scale piece would be refinement of a Rust implementation (checking that the code, not the model, orders transactional requests and fences zombies). That requires an async Rust verification story, which is open.
- OPINION: Iggy's issues look like missing ack contracts between connector runtime and sources/sinks. That is a smaller, checkable "checkpoint advances only after delivery" property, but it is a bug class in connector glue, so thin for a PhD.

Rust targets
Apache Iggy (apache/iggy; broker, connectors runtime), Fluvio (infinyon/fluvio), Arroyo (ArroyoSystems/arroyo; checkpoints and two-phase-commit Kafka sink), Restate's own log (see direction 2), Materialize/RisingWave (stream processors; I did not check their delivery claims).

# Direction 2: idempotency and retries in workflows, webhooks, durable execution

Real failures
- Restate (Rust server), docs issue #410, opened Sep 24, 2026. https://github.com/restatedev/docs-restate/issues/410 . Disputed doc claim: "Tool side effects are not duplicated (no double bookings, no duplicate emails)" and "Side effects are executed exactly once. On recovery, the result is replayed." Result: "The receiver applied the request twice in 30 of 30 trials." (worker SIGKILLed after the action, before the result was journaled). With an idempotency key from ctx.uuid(): "applied once in 30 of 30". The reporter thinks the engine is correct and the docs wrong. FACT (reported by a third party, not confirmed by Restate maintainers as far as I saw).
- Temporal, blog by Remdore, Oct (year not shown by the tool; likely 2026). https://dev.to/remdore/temporal-finished-my-workflow-exactly-once-and-ran-its-first-step-four-times-59dh . "I ran a ten-step workflow and killed the worker running it eight times, with kill -9, at random moments." "The workflow finished exactly once, as promised, and its first step ran four times". Temporal behaved as documented: activities are at-least-once. FACT it is documented, which is the point: the guarantee is conditional on user idempotency.
- Temporal forum, "Duplicate sleep TimerFired corrupting workflow history". https://community.temporal.io/t/duplicate-sleep-timerfired-corrupting-workflow-history/8431 . Reply (via tool): "We have seen these duplicate timer firing under certain failure modes when running Temporal Server using Cassandra persistence." That is an engine bug, not user code. Temporal server is Go.
- Payment double charges (blogs; may be illustrative, authenticity unverified): Medium by Naveen Metta, "We Shipped a Bug That Charged Customers Twice" https://naveen-metta.medium.com/we-shipped-a-bug-that-charged-customers-twice-heres-the-postmortem-f7847b2cb68f : 2,214 customers charged twice, about $186,000, cause "a Resilience4j @Retry on payment capture that sent no idempotency key". Weak evidence; no named vendor postmortem found.
- Failure modes of idempotency-key schemes, from https://www.infoworld.com/article/4191741/why-an-idempotency-key-isnt-an-idempotency-guarantee.html (via search summary, not fetched): new key per retry, check-then-save race, crash between charge and saving the key, key expiry, same key with different payload. These are checkable protocol properties.

Property to verify (OPINION: my formulation)
Let a workflow be a program whose steps are journaled. For any crash, restart, timeout, or concurrent duplicate-execution schedule, if every external effect carries a key derived deterministically from (workflow id, step id) and the receiver deduplicates by that key, then each effect is applied at most once and, if the workflow completes, at least once. Also, a step with no key has no such guarantee, so the verifier must identify exactly the crash windows (between effect and journal write) where duplication is possible and show it is the only one.

Closest prior verification
- Burckhardt, Gillum, Justo, Kallas, McMahon, Meiklejohn, "Durable Functions: Semantics for Stateful Serverless", OOPSLA 2021. https://www.microsoft.com/en-us/research/wp-content/uploads/2021/10/DF-Semantics-Final.pdf . FACT (via a citing paper): proves observably exactly-once under the assumption that "all observable application state (entity state, message queues, and orchestration progress) is persisted in a single durable store that the runtime manages and can update atomically." Leaves open (INFERENCE): external calls (the effect-before-journal window) and any real implementation.
- Tardieu et al., "Reliable Actors with Retry Orchestration" (KAR, IBM), arXiv 2111.11562 (PLDI 2023 per my memory, not verified). https://arxiv.org/pdf/2111.11562 . I did not read its proof content beyond the abstract text; it formalizes retry semantics for actors.
- Netherite, Burckhardt et al., PVLDB 2022: refers to the OOPSLA proof for exactly-once. Not downloaded (not checked open access).
- arXiv 2412.13314 "Distributed Speculative Execution for Resilient Cloud Applications": says durable execution gives exactly-once only if tasks are idempotent. Not read.
- Open (INFERENCE): no verified implementation of a durable execution engine found in my searches; no work I found checks idempotency-key discipline in user workflows against the engine's crash windows.

Tractability
- OPINION: tractable and PhD-scale if scoped as "verify Restate's journal/replay/retry protocol in its Rust implementation, and give a type- or effect-system for SDK code that statically flags effects not wrapped with a derived key". Restate is small, Rust, open, with a documented deterministic-replay design. Real bug evidence is currently thin for the engine itself (Restate #410 is a doc-vs-behavior dispute, not an engine bug); Temporal's Cassandra duplicate-timer report is the engine-bug evidence but is Go. Under the human's filter (Rust, distributed) it fits; the risk is that the guarantee is trivially at-least-once so the interesting theorem is only the conditional one.
- OPINION: the check-then-save and crash-between races in idempotency receivers are well-understood; a verified idempotency-key store (Rust, atomic claim, in-flight state) is a smaller, concrete artifact.

Rust targets
restatedev/restate (journal, invocation state machine, retry), restatedev SDKs (sdk-rust, sdk-shared-core), Iggy dedup, Iggy and Arroyo sinks; Temporal's Rust core SDK (temporalio/sdk-core) for replay/non-determinism checks, though the server is Go.

# Papers placed in /hdd1/sichanghe/paper_collection
- "Durable Functions - Semantics for Stateful Serverless, Burckhardt et al, OOPSLA, 2021"
- "Reliable Actors with Retry Orchestration, Tardieu et al, PLDI, 2023" (venue from memory)
Not added: Netherite, Vanlightly blog (not papers).
