# vlm29_crdt: verifying CRDT sync protocols
(authored by agents unless marked 🧑)

## Findings
- the gap looks real (belief; based on Scholar snippets only, no papers read in full)
  - mechanized proofs cover the merge function (Gomes et al. 2017 Isabelle, VeriFx, Katara, Propel, Liquid Haskell, Certified MRDTs) or abstract delivery (Blau 2020 δ-CRDT Isabelle model, Nieto et al. 2022 Coq, Redmond et al. 2022 verified causal broadcast in Liquid Haskell)
  - sync/anti-entropy protocols have only pen-and-paper proofs (Almeida δ-CRDT; Kleppmann–Howard 2020 Byzantine eventual consistency) or bounded TLA+ models (Zhang et al. 2024; AIMP preprint)
  - nothing found proves, on real library code, "both say in-sync ⇒ identical" or the liveness property
- closest prior work: Blau 2020, Nieto 2022, Zhang 2024; read these before claiming novelty
- method precedent: IronFleet and Verdi verified protocol code (Paxos/Raft), not CRDT sync
- what would be new (opinion): code-level safety + liveness of a real sync handshake (Automerge Bloom-filter/heads exchange, Yjs state vectors)
- real bugs exist in exactly this layer: details in bugs.md; strongest:
  - automerge #870 (2024, https://github.com/automerge/automerge/issues/870): "they both claim to be in sync because their generated sync messages will be `null`"; no root cause stated; repro is concurrent puts on one key, so it may be merge-level; fixed in 3.0.0-beta.0
  - automerge #772 (2023), #1284 (2026), #337 (2022): sync loops forever after a lost message; #772, #1284 open
  - loro #1215, #1040 (2026, open): silent state/oplog divergence; snapshot import stuck pending
  - y-websocket #94 (2022), #204, #203 (2026): never reaches "synced", or a stale socket flips it
  - yjs #374, #550: state vectors ignore deletes, so they cannot prove equality (by design)
- caveat: GitHub search quota ran out; diamond-types showed no sync bugs; repros not run

## TeamTypeV link (fact, from code)
TeamTypeV uses Automerge 0.10's sync protocol directly (crates/teamtype/src/peer/sync.rs, daemon.rs:425 `generate_sync_message`). Existing probes listed "Automerge CRDT sync and iroh networking" as assumed, so this direction fills that assumed part.

## TeamTypeV verification in 5 sentences (for the human)
1. TeamTypeV is a collaborative editor: each editor talks to a local daemon via operational transform (OT), and daemons sync with each other via Automerge.
2. Agents wrote Verus (a verifier for Rust) proofs over the real Rust code for three pieces: OT convergence, line/character position conversion, and the editor-protocol revision state machine.
3. OT: both orders of applying two concurrent edits give the same text, including through the daemon's queue ("65 verified, 0 errors"), trusting string primitives.
4. Positions and protocol: round-trip conversion is proved except for a "\r" line-ending case, and the revision code was shown to panic on malformed editor input; small fixes were proved.
5. Not verified: end-to-end editor/daemon convergence, the TypeScript UTF-16 code, and Automerge sync plus networking, which were assumed.
Sources: /ssd1/sichangheagent/teamtype--teamtype-evidence/walk_drafts.md; /hdd1/sichangheagent/vl_codex_saturate/teamtype_probe/ot/REPORT.md

## Evidence
- scholar.md: per-paper quotes, years, URLs, coverage
- bugs.md: per-bug quotes, causes, fix status
