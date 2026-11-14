# Prior-work recheck with Google Scholar, November 2026

(authored by agents unless marked 🧑)

Why: the human said 🧑 "Google Scholar is back, so probably you need to revise a lot of the directions after doing literature research". Earlier prior-work checks were blocked by a Scholar CAPTCHA.

Method (FACT): one agent ran paced Scholar queries (about one per minute, no CAPTCHA seen), years 2022 onward unless noted. Judgments rest on result titles and snippets; papers were not opened unless stated. A few queries per direction is weak evidence of absence: "still open" means "nothing found", not "proved new".

Verdicts: still open / partly done / done. "Changed" marks a verdict that differs from what the direction file implied before.

## Priority 1 (directions the human kept or found interesting)

- verify standards (directions/verify_standards.md): still open. No model checking of concurrent WHATWG algorithms found; neighbours are WebSpec/WIM security models, ESMeta/SpecTec (sequential specs), RFCScope (LLM ambiguity).
- async cancel-safety (verification/async_cancel/REPORT.md): still open. New must-cite neighbours: Lion (SOSP 2026) and Li-Beschastnikh-Summers (arXiv 2026) verify async runtime liveness, not cancellation.
- bounded memory vs hostile peer (verification/bounded_memory/REPORT.md): still open. Medusa (2024) and HTTP/2/QUIC attack papers find memory-exhaustion bugs; no bound proofs.
- Tauri IPC permissions (directions/vlm48_dirs/d.md C2): still open. Only Electron fuzzing/defense and Deno sandbox studies.
- distributed protocols beyond Raft (directions/distributed_protocols.md): still open for all Rust code. Percolator now has a CSP model (COMPSAC 2024), so its protocol level is partly done; Tendermint has protocol model checking.
- replicated-state targets (directions/replicated_state_targets.md): still open.
- crash durability (candidates item 15): dropped by the human ("Everyone knows this direction ... We have no edge in this game"); not rechecked.

## Changed verdicts from the candidates list (candidates_2026-11.md)

- item 2, lost wakeups (CHANGED: mostly done). Lion: Modular Verification of Async Runtime Liveness (Zhou, Zhang, Chowdhury, Mu, SOSP 2026) is, per its authors, the first Rust async runtime with mechanically verified scheduling liveness: "Lion is a Tokio-compatible runtime in Rust verified using Verus" (ACM page summary via web search). Li, Beschastnikh, Summers, "Modular Responsiveness Verification of Rust Async Runtimes" (arXiv 2610.09198): "verify eventual progression of several key components of multiple Rust async runtime implementations" (abstract). What remains: Tokio itself, and channels/actor mailboxes outside the scheduler.
