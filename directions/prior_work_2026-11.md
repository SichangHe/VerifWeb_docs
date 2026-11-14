# Prior-work recheck with Google Scholar, November 2026

(authored by agents unless marked 🧑)

Why: the human said 🧑 "Google Scholar is back, so probably you need to revise a lot of the directions after doing literature research". Earlier prior-work checks were blocked by a Scholar CAPTCHA.

Method (FACT): one agent ran paced Scholar queries (about one per minute, no CAPTCHA seen), years 2022 onward unless noted. Judgments rest on result titles and snippets; papers were not opened unless stated. A few queries per direction is weak evidence of absence: "still open" means "nothing found", not "proved new".

Verdicts: still open / partly done / done. "Changed" marks a verdict that differs from what the direction file implied before.

## Priority 1 (directions the human kept or found interesting)

- verify standards (directions/verify_standards.md): still open. No model checking of concurrent WHATWG algorithms found; neighbours are WebSpec/WIM security models, ESMeta/SpecTec (sequential specs), RFCScope (LLM ambiguity).
- async cancel-safety (verification/async_cancel/REPORT.md): partly covered by Lion at the runtime level (CHANGED, correction relayed from vl_async.md). Lion verifies a waiter-cancellation step (`remove_step` + `CancelWaker`) in its runtime kernel, but its real Drop/notification glue is trusted and some task-abort traces are excluded; see verification/async_cancel/LION.md. Still open: cancellation safety of application code (state consistent when a user future is dropped at an await), e.g. the Pingora case.
- bounded memory vs hostile peer (verification/bounded_memory/REPORT.md): still open. Medusa (2024) and HTTP/2/QUIC attack papers find memory-exhaustion bugs; no bound proofs.
- Tauri IPC permissions (directions/vlm48_dirs/d.md C2): still open. Only Electron fuzzing/defense and Deno sandbox studies.
- distributed protocols beyond Raft (directions/distributed_protocols.md): still open for all Rust code. Percolator now has a CSP model (COMPSAC 2024), so its protocol level is partly done; Tendermint has protocol model checking.
- replicated-state targets (directions/replicated_state_targets.md): still open.
- crash durability (candidates item 15): dropped by the human ("Everyone knows this direction ... We have no edge in this game"); not rechecked.

## Changed verdicts from the candidates list (candidates_2026-11.md)

- item 2, lost wakeups (CHANGED: mostly done). Lion: Modular Verification of Async Runtime Liveness (Zhou, Zhang, Chowdhury, Mu, SOSP 2026) is, per its authors, the first Rust async runtime with mechanically verified scheduling liveness: "Lion is a Tokio-compatible runtime in Rust verified using Verus" (ACM page summary via web search). Li, Beschastnikh, Summers, "Modular Responsiveness Verification of Rust Async Runtimes" (arXiv 2610.09198): "verify eventual progression of several key components of multiple Rust async runtime implementations" (abstract). What remains: Tokio itself, and channels/actor mailboxes outside the scheduler.
- item 8, certificate validation (CHANGED: mostly done). Verdict (Lin, McLoughlin, Singh, Brennan-Jones, Hitchcox, Gancher, Parno, USENIX Security 2025): "the first end-to-end formally verified X.509 certificate validator with customizable validation policies", written in Rust and verified with Verus; it implements Chrome, Firefox and OpenSSL policies and proves them against "a subset of RFC requirements" (USENIX abstract, via web search). Left: rustls-webpki itself.
- item 26, retry storms and recovery time (CHANGED: partly done). "Formal analysis of metastable failures in software systems" (Alvaro, Isaacs, Majumdar et al., arXiv 2025); Scholar snippet: "When we compute recovery times based on our … formal modeling". Also "Modeling metastability" (Farahbakhsh et al., HotOS 2025). Models only, not code.
- item 41, MLS forks (CHANGED: partly done). MLS has machine-checked symbolic proofs in F* (TreeSync, USENIX Security 2023; TreeKEM, IEEE S&P 2025; Wallez thesis 2025). OpenMLS Rust code is not verified.

Partly done by bug-finding tools or models (no proofs on the real code): items 4, 7, 10, 14, 16-21, 38, 42, 54. Still open (nothing close found): the rest. Per-item notes are on each item's "Prior work (Scholar recheck 2026-11-14)" line in candidates_2026-11.md. Items 15-24 were treated as lowest priority per the human's view on well-known distributed-database work.

## Query log

Raw Scholar results were kept in a temporary scratch directory; they are not committed. Queries per direction: 1-2. Thirteen identity/browser queries (items 48-60) returned empty pages once and were rerun successfully.

## Papers kept in paper_collection

Added this pass: Lion (SOSP 2026), Modular Responsiveness Verification of Rust Async Runtimes (arXiv 2026), Formal Analysis of Metastable Failures in Software Systems (arXiv 2025). Verdict (USENIX Security 2025) was already there. Paywalled ones (Percolator CSP model, TLS 1.3 OpenSSL state machine) were not added.
