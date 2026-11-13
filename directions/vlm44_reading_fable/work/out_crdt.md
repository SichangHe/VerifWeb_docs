(authored by agents unless marked 🧑)

Overall (from the 16 texts below; facts are from the papers, the last two lines are my inference).
Fact: the only mechanized (machine-checked) proofs about sequence/text merge are about algorithm models, not shipped code: RGA in Isabelle (88), WOOT in Isabelle (30). The only proof about real executable code (80, Coq/Iris) covers counters, sets, registers, maps; no list/text CRDT. VeriFx (32) could not verify RGA automatically (timeout). The code-level work on Automerge itself (19) is bounded model checking, not proof.
Inference: no paper here verifies Automerge, Loro or Yrs/Yjs code. Consensus comparison: none of these papers compares directly; 20 shows convergence needs no agreement for invariants that are I-confluent (safe under merge), and 18 measures that a leader-ordered (consensus-like) scheme is faster than its CRDT, so the cost of CRDTs is in merge logic and metadata, not in coordination.

---
ID 18. A highly-available move operation for replicated trees, Martin Kleppmann, Dominic P. Mulligan, Victor B. F. Gomes, Alastair R. Beresford, IEEE TPDS, 2021
SHOWS: A CRDT algorithm for moving subtrees (no cycles, replicas converge), proved in Isabelle/HOL for the algorithm model (59 lines of definitions, 2,495 lines of proof, no sorry); code in Scala is extracted from the Isabelle definitions, so the extracted code matches the proved model; it ran 9.5x slower than hand-written code.
QUOTE: "We formally prove the correctness of our algorithm using the Isabelle/HOL proof assistant, and evaluate the performance of our formally verified implementation in a geo-replicated setting." (Abstract)
WHY: Shows proof plus code extraction works for one tricky merge rule (move), with proof size numbers; also gives a consensus baseline (leader-ordered version reached 14,000 ops/s vs 600 for the CRDT, same code), and shows move is hard (Dropbox/Google Drive bugs); Automerge/Loro lack or recently added tree move.
PRIORITY: high. Closest proof-to-code example.
READ: abstract, intro, 5.3 proof evaluation, evaluation (throughput part), related work (skimmed).

ID 19. AMC- Towards Trustworthy and Explorable CRDT Applications with the Automerge Model Checker, Andrew Jeffery, Richard Mortier, PaPoC, 2023
SHOWS: A model checker (Stateright, Rust) that explores all orderings of operations and syncs on the real Rust Automerge library plus small apps; it checks convergence, save/load round trip, no errors, historical views; this is bounded search, not a proof, and keeps state small (one key/index per run).
QUOTE: "can check the Automerge library implementation, rather than just a high level description of the CRDT" (Introduction, contribution 3)
WHY: Only paper here that touches real Automerge code; shows what bounded checking gives (finds list-move duplication, ID clashes in apps) and what is missing: unbounded proof of the merge code.
PRIORITY: high. Direct prior work on Automerge.
READ: abstract, intro, sections 2-7 (about all of it; Table 1 results not read in detail).

ID 20. Byzantine Eventual Consistency and the Fundamental Limits of Peer-to-Peer Databases, Martin Kleppmann, Heidi Howard, arXiv, 2020
SHOWS: Proves (paper proof, no tool) that a replicated database can tolerate any number of Byzantine (arbitrarily misbehaving) nodes iff its transactions are I-confluent (merge never breaks the invariant); gives a Byzantine causal broadcast algorithm and a prototype.
QUOTE: "there exists a fault-tolerant algorithm that ensures BEC if and only if the set of all transactions executed by correct replicas is I-confluent with respect to each of the invariants." (Theorem 3.1, section 3)
WHY: States exactly when merge-without-consensus is possible, the theory side of the "CRDT vs consensus" question; not about verifying code.
PRIORITY: low. Theory, not verification.
READ: abstract, intro, section 3 theorem, conclusions, appendix headings.

ID 21. Certified Program Models for Eventual Consistency, Edgar Pek, Pranav Garg, Muntasir Raihan Rahman, Indranil Gupta, P. Madhusudan, preprint, 2015
SHOWS: Models the read-repair and hinted-handoff repair protocols of Dynamo-style stores (Cassandra, Riak) as C programs, tests them against real systems, and proves eventual consistency with the VCC verifier (about 1500 lines of code and annotations, about 6 person-months); the conflict-resolution CRDT is left as an abstract stub that is assumed idempotent.
QUOTE: "We model the read-repair and hinted-handoff table based recovery protocols as concurrent C programs, test them for conformance with real systems, and then verify that they guarantee eventual consistency" (Abstract)
WHY: A proof about a model of a real protocol, not the real code; and it assumes the merge function is correct, so it leaves exactly our target (the merge code) unproved.
PRIORITY: low. Proves delivery, not merge.
READ: abstract, intro, sections 2-3, verification methodology, lessons/conclusion (parts).

ID 22. Collaborative Text Editing with Eg-walker- Better, Faster, Smaller, Joseph Gentle, Martin Kleppmann, arXiv, 2024
SHOWS: A new text merge algorithm (Eg-walker) that keeps the edit history and replays it, with no stored CRDT state at rest; measured against Automerge (Rust) and Yjs; correctness is a paper proof (Appendix C, no proof tool named) against the strong list specification, plus randomized tests.
QUOTE: "To evaluate the correctness of Eg-walker we proved that the algorithm complies with Attiya et al.'s strong list specification [8] (see Appendix C)." (Section 3, correctness paragraph)
WHY: Shows that merge algorithms keep changing and the rich ones are proved only on paper; any verification of the real libraries is aimed at a moving target (Eg-walker is the newer approach).
PRIORITY: medium. Newest algorithm, paper proof only.
READ: abstract, intro, contributions, evaluation memory/speed parts, correctness paragraph, appendix C start, conclusion.

ID 23. Delta State Replicated Data Types, Paulo Sérgio Almeida, Ali Shoker, Carlos Baquero, arXiv, 2016
SHOWS: Defines delta-CRDTs (send small state deltas, not full state) with paper proofs that they keep eventual and causal consistency, plus an anti-entropy algorithm; no machine proof, no code verification.
QUOTE: "We prove that eventual consistency is guaranteed in δ-CRDT as long as all deltas produced by δ-mutators are delivered and joined at other replicas" (Introduction)
WHY: The sync side of Automerge/Yrs (sending only what changed) rests on this kind of argument; it is only paper-proved, which is a gap for verifying sync code.
PRIORITY: low. Background theory.
READ: abstract, intro, proof statements, conclusion.

ID 24. Keep CALM and CRDT On, Shadaj Laddad, Conor Power, Mae Milano, Alvin Cheung, Natacha Crooks, Joseph M. Hellerstein, VLDB, 2022
SHOWS: Vision paper: add a query model to CRDTs so reads that are safe without coordination are identified using the CALM theorem (monotone programs need no coordination); no proofs, no implementation measured.
QUOTE: "formal verification and fuzzing, which can assist developers designing CRDTs by automatically checking the core correctness properties." (Section 4, end)
WHY: Only a pointer that verification is a wanted direction; it says CRDT guarantees cover updates but not reads, which is a spec gap to be aware of when choosing what to verify.
PRIORITY: low. Vision, no verification content.
READ: abstract, intro, section 4 end, conclusion.

ID 25. Making CRDTs Byzantine Fault Tolerant, Martin Kleppmann, PaPoC, 2022
SHOWS: Sketches how to make op-based CRDTs tolerate Byzantine nodes (hash-linked updates, validity checks); a short position paper with no complete proof and no evaluation.
QUOTE: "I leave a detailed proof of this conjecture in the context of particular CRDT algorithms for future work." (Section 3)
WHY: Marks that the Byzantine case is an open claim, so out of scope for a first verification effort.
PRIORITY: low. Short, unproved sketch.
READ: abstract, intro, section 3 end, conclusions.

ID 29. Peritext- A CRDT for Collaborative Rich Text Editing, Geoffrey Litt, Sarah Lim, Martin Kleppmann, Peter van Hardenberg, CSCW, 2022
SHOWS: A rich-text (bold, links) merge algorithm built on an Automerge-like list CRDT; prototype in TypeScript, randomized property tests (found coding bugs in earlier versions; 5,000-operation traces), and a paper convergence proof in Appendix A that leans on earlier RGA proofs.
QUOTE: "We also prove that our algorithm ensures convergence, and demonstrate its causality preservation and intention preservation properties." (Abstract)
WHY: Intent preservation (what users expect) is only argued by examples, not formally; Automerge and Loro now ship rich-text, so the spec for it is the harder open part.
PRIORITY: medium. Shows rich-text spec gap.
READ: abstract, intro, implementation/testing section, appendix A start, conclusion.

ID 30. Strong eventual consistency of the collaborative editing framework WOOT, Emin Karayel, Edgar Gonzàlez, Distributed Computing, 2022
SHOWS: First proof that the WOOT text CRDT converges (the question was open 14 years; earlier checks were only bounded), machine-checked in Isabelle/HOL, about an abstract model of the protocol with a sort-key simulation.
QUOTE: "Its eventual consistency property was verified only for a bounded model to date. ... the property for WOOT remained open for 14 years." (Abstract)
WHY: Evidence that text-merge convergence can be subtle enough to need years and a new proof idea; it is a model proof, not code.
PRIORITY: high. Shows difficulty of text-merge proofs.
READ: abstract, intro, conclusion, formalization section (skimmed).

ID 31. The Art of the Fugue- Minimizing Interleaving in Collaborative Text Editing, Matthew Weidner, Martin Kleppmann, arXiv, 2023
SHOWS: Defines a property "maximal non-interleaving" (concurrent inserts at the same spot do not get mixed letter by letter), gives Fugue/FugueMax, and proves them on paper (no tool); also finds that many older algorithms interleave and that Yjs's non-interleaving proof is in progress; Fugue speed is similar to Yjs.
QUOTE: "We introduce two related CRDT algorithms, Fugue and FugueMax, and prove that FugueMax satisfies maximal non-interleaving." (Abstract)
WHY: A concrete property worth specifying for real libraries, and the table shows even the proofs of Yjs behavior are incomplete.
PRIORITY: high. Gives text-merge specs to verify.
READ: abstract, intro, related work table, section 4-5 (proof outline skimmed), implementation/evaluation headings.

ID 32. VeriFx- Correct Replicated Data Types for the Masses, Kevin De Porre, Carla Ferreira, Elisa Gonzalez Boix, arXiv, 2022
SHOWS: A small functional language where CRDT/OT code is verified automatically by the Z3 SMT solver (a fully automatic checker) and then translated to Scala or JavaScript; 35 CRDTs verified in seconds, found real bugs (a Kleppmann map CRDT diverges, the 2P-Set is not functionally correct), but the list CRDT RGA timed out.
QUOTE: "VeriFx was able to verify all CRDTs except the Replicated Growable Array (RGA) [Shapiro et al. 2011a] due to the recursive nature of the insertion algorithm." (Section 6.1)
WHY: Shows that automatic proofs work for sets/maps/counters but fail on the list merge that Automerge/Yrs depend on; the proof is about code in the VeriFx language, not Rust.
PRIORITY: high. Shows where automation stops.
READ: abstract, intro, tool design, section 6.1 and Table 1; later sections not read.

ID 79. Met- Model Checking-Driven Explorative Testing of CRDT Designs and Implementations, Yuqi Zhang, Yu Huang, Hengfeng Wei, Xiaoxing Ma, JSEP, 2024
SHOWS: Specify CRDT design in TLA+ and model check it, then replay the model-checker traces on the real implementation (CRDT-Redis, Java) to test it; found deep bugs in both designs and code; testing, not proof, and the developer must write the spec.
QUOTE: "Then test cases are automatically generated from the model checking traces to achieve explorative and exhaustive testing at the code level." (Section 7, conclusion)
WHY: A practical middle route between model proof and full code proof that could apply to Rust libraries; does not cover Automerge/Loro/Yrs.
PRIORITY: medium. Practical code-level method.
READ: abstract, intro, section 5.2 bug discussion, conclusion.

ID 80. Modular Verification of Op-Based CRDTs in Separation Logic, Abel Nieto, Léon Gondelman, Alban Reynaud, Amin Timany, Lars Birkedal, OOPSLA, 2022
SHOWS: Proofs in Coq with Iris/Aneris (separation logic, a logic for reasoning about programs with shared state) about real OCaml code: a causal broadcast library (196 OCaml lines, 4,854 proof+spec lines) and a CRDT library (86 OCaml lines, 3,576 spec+proof lines), used to verify 12 CRDTs (counters, sets, registers, product and map); no list/text CRDT; liveness (eventual delivery) not proved for the whole stack.
QUOTE: "Our technique is the first work on verification of op-based CRDTs that satisfies both of the following properties: it is modular and targets executable implementations, as opposed to high-level protocols." (Abstract)
WHY: Best answer to "model vs real code": the proof is on real (small OCaml) code, and shows proof size is about 10-20 lines of proof per line of code; it does not reach sequence CRDTs or Rust.
PRIORITY: high. Real-code proof with size numbers.
READ: abstract, intro, overview, library metrics tables, related work (part), conclusions.

ID 86. Verifying Strong Eventual Consistency in δ-CRDTs, Taylor Blau, arXiv, 2020
SHOWS: A bachelor's thesis extending the Gomes et al. Isabelle framework to state-based and delta-state CRDTs with a weaker network model; proves convergence for G-Counter and G-Set style examples; models only, not code; the 2P-Set is left to future work.
QUOTE: "We formalize this intuition in the Isabelle interactive theorem prover and show that state-based CRDTs achieve SEC." (Abstract)
WHY: Shows the Isabelle framework (88) can be extended to the sync style used by delta-based libraries, only for simple types.
PRIORITY: low. Student thesis, simple types.
READ: abstract, table of contents, intro, chapter 3-5 headings, parts of the future work.

ID 88. Verifying Strong Eventual Consistency in Distributed Systems, Victor B. F. Gomes, Martin Kleppmann, Dominic P. Mulligan, Alastair R. Beresford, OOPSLA, 2017
SHOWS: An Isabelle/HOL framework with an explicit network model (messages may be delayed, dropped, reordered) and an abstract convergence theorem; the first machine-checked proofs for RGA (list), OR-Set, and counter; about 620 lines network model, 380 abstract proof, 775 RGA proof, under 800 for all three; OCaml/Scala/Haskell code extractable from the definitions.
QUOTE: "We then obtain the first machine-checked correctness theorems for three concrete CRDTs: the Replicated Growable Array, the Observed-Remove Set, and an Increment-Decrement Counter." (Abstract)
WHY: Direct prior work on verified list-merge convergence, and the cost: RGA about 775 proof lines; but it proves a model of the algorithm, with extracted code only as a side use, and RGA is simpler than what Yrs/Loro/Automerge do (formatting, moves, GC, compression).
PRIORITY: high. Core prior work, RGA proof.
READ: abstract, intro, conclusion, proof-size section, section 7 RGA overview (skimmed).
