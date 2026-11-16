# VerifWeb reading walkthrough
(authored by agents unless marked 🧑)

Notes of the papers walked through with the human, in order, and the human's takeaways.

## 1. Verifying Strong Eventual Consistency in Distributed Systems (Gomes et al., OOPSLA 2017)

- status: presented Nov 13; agent read the full paper
- human's takeaways: (pending)
- human asked (Nov 16): is this the state of the art; do real systems (editors, databases) reach agreement without consensus?
  - answered: Gomes 2017 is the foundation, not the latest; pointed to Nieto 2022, Peepul 2022, Propel 2023, Sal 2026; real systems: Automerge/Yjs/Loro, Riak, Cassandra (no consensus) vs Google Docs (central server)

## Priority for Nov 17 advisor meeting
Order from vl_meeting_work's out/reading_priority_1117.md: Nieto 2022, AMC 2023, Lion (SOSP 2026), Vest (USENIX Sec 2026); if time: ESMeta, WebSpec, Verdict.

## 2. Modular Verification of Op-Based CRDTs in Separation Logic (Nieto et al., OOPSLA 2022)
- status: presented Nov 16; agent read the full paper
- points for advisors: safety only, no eventual delivery (liveness) proved; no text CRDT, no Rust, no deployed library; ~30 Coq lines per OCaml line (Table 2)
- human's takeaways: (pending)

## 3. AMC: Automerge Model Checker (Jeffery, Mortier, PaPoC 2023)
- status: presented Nov 16; agent read the full paper
- points for advisors: authors say mechanized CRDT proofs "cannot aid more optimized implementations"; checking is bounded (1 key/index, 3 servers, depth 19) on a reliable ordered network; bugs found were app-level (list move duplicates, ID clashes)
- human's takeaways: (pending)
