# Scholar prior-work search: verified CRDT sync layer (vlm29)
(authored by agents unless marked 🧑)

Method: 10 Google Scholar queries via pb-browser-page-extract (raw in scholar/q*.txt), 25s apart, no CAPTCHA hit. Quotes are Scholar snippets only (not full abstracts); I did not open the papers. "On" = code or model. Sync layer: yes/no/partial.

1. Verifying strong eventual consistency in distributed systems. Gomes, Kleppmann, Mulligan, Beresford. 2017, OOPSLA. https://dl.acm.org/ (Scholar q1)
   - "the Isabelle/HOL interactive proof assistant for verifying the correctness of CRDT algorithms"
   - on: model (Isabelle algorithm model, abstract network of causal delivery). sync layer: partial (network model yes, sync/anti-entropy protocol no)
2. Verifying Strong Eventual Consistency in δ-CRDTs. T. Blau. 2020, arXiv:2006.09823. (q110)
   - "We present a relaxed network model in Isabelle and show that …" (snippet truncated; mentions UDP networks)
   - on: model. sync layer: partial (delta delivery assumptions; verify whether anti-entropy is modeled)
3. Formal specification and verification of CRDTs. Zeller, Bieniusa, Poetzsch-Heffter. 2014, FORTE. (q1)
   - "in using Isabelle/HOL for the verification of CRDTs"
   - on: model. sync: no
4. Strong eventual consistency of the collaborative editing framework WOOT. Karayel, Gonzalez. 2022, Distributed Computing. (q1)
   - "We formalize the proof using the Isabelle/HOL proof … machine-checked"
   - on: model. sync: no
5. VeriFx: Correct replicated data types for the masses. De Porre, Ferreira, Boix. 2022, arXiv:2207.02502. (q2)
   - "we build two libraries for implementing and automatically verifying RDTs"
   - on: code in own language (transpiled). sync: no
6. Certified mergeable replicated data types. Soundarapandian et al. 2022, PLDI. (q2)
   - "just verifying convergence, and provide a methodology to verify arbitrarily complex specifications. We develop a replication-…"
   - on: code (F*). sync: partial (replication-aware simulation of merge; not transport)
7. Modular verification of op-based CRDTs in separation logic. Nieto, Gondelman, Reynaud, Timany et al. 2022, OOPSLA. (q110)
   - "All our proofs are mechanized in Coq."
   - on: code (Aneris/OCaml-like, with network semantics). sync: partial (op-based causal broadcast layer, not state/doc sync handshake)
8. Verified causal broadcast with Liquid Haskell. Redmond, Shen, Vazou, Kuper. 2022, IFL. (q4)
   - "CRDT implementations to get an end-to-end correctness guarantee. … our library enables modular verification of higher-level properties for applications built on top of the"
   - on: code. sync: partial (broadcast layer, closest on transport)
9. Verifying replicated data types with typeclass refinements in Liquid Haskell. Liu, Parker, Redmond, Kuper, Hicks, Vazou. 2020, OOPSLA. (q4)
   - "Given a CRDT specification, their framework will determine which consistency policy is required" (this is a citing description, not own abstract)
   - on: code. sync: no
10. Type-checking CRDT convergence (Propel). Zakhour, Weisenburger, Salvaneschi. 2023, PACMPL. (q4)
   - "to verify such properties on concrete CRDT implementations. In this paper, we present Propel"
   - on: code. sync: no
11. Katara: Synthesizing CRDTs with verified lifting. Laddad, Power, Milano, Cheung et al. 2022, OOPSLA. (q3)
   - "Crucially, our synthesized CRDTs are fully, automatically verified"
   - on: code (merge). sync: no
12. Delta state replicated data types. Almeida, Shoker, Baquero. 2018, JPDC. (q5)
   - "CRDT as long as all deltas produced by δ-mutators are delivered and joined at other replicas, and we present a corresponding simple anti-entropy algorithm"
   - on: paper proof (not mechanized). sync: yes but pen-and-paper
13. Efficient synchronization of state-based CRDTs. Enes, Almeida, Baquero, Leitao. 2019, ICDE. (q5)
   - snippet: "When a δ-group is received (line 14), then it is checked …" (no verification claim)
   - on: protocol + experiments. sync: yes, unverified
14. Byzantine eventual consistency and the fundamental limits of peer-to-peer databases. Kleppmann, Howard. 2020, arXiv:2012.00472. (q19)
   - "We introduce an algorithm that guarantees BEC based on Byzantine causal broadcast, prove its correctness, and demo…"
   - on: paper proof. sync: yes (broadcast/sync algorithm), not mechanized
15. Model-checking-driven explorative testing of CRDT designs and implementations. Zhang, Huang, Wei, Ma. 2024, JSEP. (q8)
   - "Given that the protocol design has been verified by model checking…"
   - on: TLA+ model + tests of implementation. sync: partial (models "broadcast the synchronization message to all")
16. Conflict-free Replicated Priority Queue: Design, Verification and Evaluation. Zhang, Ouyang, Huang, Ma. 2023, APSys. (q8)
   - "Given the CRPQ protocols specified in TLA+, we can now …"
   - on: model. sync: partial
17. AMC: Towards Trustworthy and Explorable CRDT Applications with the Automerge Model Checker. Jeffery, Mortier. 2023, PaPoC. (q3)
   - snippet only cites Katara; title is the claim.
   - on: model checking of Automerge-based apps (code-level exploration). sync: partial/unknown (check)
18. AIMP: AI Mesh Protocol. F. Salmi. (undated preprint, ResearchGate). (q5,q7,q8)
   - "We use bounded model checking in TLA+ to verify three safety …"; "in a single anti-entropy round confirms the CRDT property"
   - on: model (TLA+) of a Rust CRDT gossip system. sync: yes (anti-entropy), bounded, non-peer-reviewed, low confidence
19. Verified detection and prevention of concurrency anomalies in multi-agent LLM systems. (q8, truncated). Not relevant.
20. IronFleet (Hawblitzel et al., SOSP 2015) and Verdi (Wilcox et al., PLDI 2015). (q2)
   - IronFleet: "focus on verifying newly written code in a verification-friendly …"
   - Verdi: "our goal with Verdi is to verify working code."
   - on: code, but Paxos/Raft/KV, not CRDT sync. sync: methodology precedent only
21. Towards System-Oriented Formal Verification of Local-First Access Control. Jacob, Stuber, Hartenstein. 2026, arXiv:2604.23560. (q6)
   - "of Byzantine fault-tolerant eventual consistency of the underlying hash chronicle [15], our query results are eventually consistent"
   - on: model. sync: no (assumes it)
22. Lore: A programming model for verifiably safe local-first software. Haas, Mogk, Yanakieva, Bieniusa et al. 2024, TOPLAS. (q7); CONLOC, Köhler et al. 2024 (q7)
   - Lore verifies app invariants over an assumed sync. sync: no
23. Not found: verified OT (q9 returned unrelated Coq results); any Ivy/TLA+/verified analysis of Yjs or Automerge sync-message protocol (q7, q8 found none; automerge sync protocol = Bloom filter + heads exchange).
   - Caveat: Scholar snippets only, and I did not run searches for "Yjs state vector" specifically.

## Closest prior work
- Delivery/network layer proven: Gomes 2017 and Blau 2020 (Isabelle model with network assumptions), Nieto 2022 (Coq, op-based over network semantics), Redmond 2022 (causal broadcast, Liquid Haskell code).
- Sync-protocol-ish with a proof: Kleppmann-Howard 2020 (pen-and-paper BEC); Almeida delta anti-entropy (pen-and-paper); Zhang 2024 and AIMP (TLA+ model checking, bounded).
- None found that verifies a CRDT library's own sync handshake (e.g. Automerge heads/Bloom, Yjs state vectors) with "both say in-sync => docs identical" plus liveness, on code, in a mechanized prover.

## Is the gap real
Belief, from snippet-level evidence: yes, plausibly real. Proven work targets merge (convergence) or abstract delivery (causal broadcast); sync protocols appear only pen-and-paper or bounded TLA+. Risks to novelty: Blau's δ-CRDT Isabelle model, Zhang's TLA+ work, Nieto's network model might cover more than the snippet shows; read these three before claiming it. Verdi/IronFleet show the code-level method exists for other protocols.
