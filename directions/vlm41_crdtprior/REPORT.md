# Collaborative-editor sync: prior work and hardness
(authored by agents unless marked 🧑)

Labels: [fact] = quoted from source; [inference] = agent reasoning; [opinion] = agent take. Nothing was published.

## Short answer

(a) Harsha: "is there any prior work in, formally verified... Conflict resolution." Yes, much of it, but almost all proves that the merge function converges assuming a network that delivers messages (causal, at least once). I found no proof that the sync protocol of Automerge, Loro or Yjs gets replicas in sync. That gap is where our idea would sit.

(b) Ramesh: "I wonder if it's at least as challenging as consensus." For convergence, no: CRDTs need no agreement, and proofs are far smaller. The hard parts are elsewhere: liveness of delivery/sync, what a good merge is (intention), and Byzantine nodes. Consensus returns only for goals beyond convergence (non-I-confluent invariants, metadata cleanup).

## (a) What is proved, by whom

### Merge functions, network assumed

Gomes, Kleppmann, Mulligan, Beresford, OOPSLA 2017 (https://arxiv.org/abs/1707.01747). Read in full. Isabelle/HOL; first machine-checked proofs for RGA (text list), OR-set, counter.
- [fact] "We avoid correctness issues that have dogged previous mechanised proofs in this area by including a network model in our formalisation, and proving that our theorems hold in all possible network behaviours."
- [fact] causal delivery is an axiom; "It is still possible for some message never to be delivered"; causal broadcast mechanisms "(such as vector timestamps for causal delivery, or sequence numbers for message uniqueness) ... we leave it for future work."
- [fact] on OT: "For IMOR and SOCT2, there had even been machine-checked 'proofs' [Imine et al. 2003], but Oster et al. [2005] showed that they were also invalid because they had made incorrect assumptions."
- left out [inference]: executable code, sync protocol, intention, membership change.

Karayel, Gonzàlez, Distributed Computing 2022 (doi 10.1007/s00446-021-00414-6). Read in full. Isabelle proof for WOOT.
- [fact] "Its eventual consistency property was verified only for a bounded model to date ... the property for WOOT remained open for 14 years."
- [fact] "The conditions ensure intention preservation, i.e., that the character appears at the place it was inserted. But for concurrent insertion at the same place, the order is unspecified."
- [fact] assumes "semantic causal delivery and eventual delivery."

Kleppmann, Mulligan, Gomes, Beresford, IEEE TPDS 2021 (https://ieeexplore.ieee.org/document/9563274). Abstract/intro only. Isabelle proof of tree move.
- [fact] "we demonstrate bugs in Google Drive and Dropbox that arise with concurrent moves."

De Porre, Ferreira, Gonzalez Boix, VeriFx, arXiv 2022 (https://arxiv.org/abs/2207.02502). Intro, results, related work. SMT proofs for 35 CRDTs and OT functions.
- [fact] "VeriFx was able to verify all CRDTs except the Replicated Growable Array (RGA) ... due to the recursive nature of the insertion algorithm."
- [fact] OT: "Suleiman et al. [1997]'s functions satisfy TP1 but the proof for TP2 times out"; Imine's functions "guarantee TP1 but not TP2".
- [fact] "the overall model assumes reliable causal broadcast."

### Network / sync layers

Nieto, Gondelman, Reynaud, Timany, Birkedal, OOPSLA 2022 (doi 10.1145/3563351). Read in full. Coq/Aneris; verifies a real (OCaml subset, UDP) reliable causal broadcast library plus 12 op-based CRDTs. Closest to "sync on real code".
- [fact] "messages can be dropped, re-ordered, and duplicated by the network. The library deploys ... sequence ids, acknowledgments, retransmissions, and a delay queue."
- [fact] safety only: "We proved specifications of our implementation that satisfy the three safety properties above." Timany et al. 2021 is "the only related work that proves eventual delivery" (one state-based G-Counter).
- [fact] the 12 CRDTs are counters, sets, registers, combinators; no list/text CRDT seen.

Blau, UW senior thesis, arXiv 2020 (https://arxiv.org/abs/2006.09823). Read in full. Isabelle; state-based and δ-CRDTs (G-Counter, G-Set), network may duplicate.
- [fact] "we consider I to be fixed during execution; that is, we do not support addition or deletion of replicas."
- [fact] "While our main result is still predicated on a set of nice delivery semantics P"; future work: "mechanizing well-known anti-entropy algorithms and causality constraints ... would be sufficient to remove the precondition."

Pek, Garg, Rahman, Gupta, Madhusudan, preprint marked "Submission to SoCC '15", publication unconfirmed (http://pranav-garg.com/papers/eventual_consistency.pdf). VCC proofs of C models of Dynamo-style anti-entropy.
- [fact] "Eventual delivery is a liveness property, and is established by finding a ranking function."
- [fact] "The result that a single read-repair does ensure eventual consistency of the stable live nodes was a result we wrongly believed in before the verification."
- models, not real Riak/Cassandra code.

Almeida, Shoker, Baquero, JPDC 2018 (arXiv 2016 read, https://arxiv.org/abs/1603.01529). Paper proofs. [fact] "we present an anti-entropy algorithm for eventual convergence, and another one that ensures causal consistency."

### Model checking / testing

Zhang, Huang, Wei, Ma, Met, JSEP 2024 (arXiv 2022 text read, https://arxiv.org/abs/2204.14129). TLA+/TLC on their CRDT designs, then trace-driven tests of CRDT-Redis.
- [fact] "the checking cost is exponential to the scale of the model. We have to limit the scale."
- [fact] bug class merge proofs miss: "The RemoveWin CRDT protocols assume that the underlying network provides causal delivery of messages. The CRDT-Redis platform does not provide such semantics."
- [fact] "bugs corresponding to the unmodeled part of the system cannot be detected."

Jeffery, Mortier, AMC, PaPoC 2023 (doi 10.1145/3578358.3591326). Rust (Stateright) model checker for Automerge apps; bounded, assumes "ordered reliable network".
- [fact] "Whilst mechanized verification of CRDTs [11] is available it operates on constrained DSLs and cannot aid more optimized implementations, or applications built on them."

### Mainstream text algorithms: paper proofs only

- Eg-walker, Gentle, Kleppmann, arXiv 2024 (https://arxiv.org/abs/2409.14252). [fact] "we proved that the algorithm complies with Attiya et al.'s strong list specification ... We also performed randomised property testing." Not machine-checked as far as seen.
- Fugue, Weidner, Kleppmann, arXiv 2023 (https://arxiv.org/abs/2305.00583). [fact] "a formal specification of the required behavior only appeared as recently as 2016 [Attiya et al.]. We argue that this specification is incomplete"; "almost all algorithms that we surveyed interleave text in some cases." Hand proof. (Unsourced belief: Loro uses Fugue.)
- Peritext, Litt, Lim, Kleppmann, van Hardenberg, CSCW 2022 (doi 10.1145/3555644). [fact] intent given as scenarios ("This provides a test suite"), checked by "randomized property-based testing".

Not read (known only via citations above): Zeller 2014, Liu OOPSLA 2020, Liang & Feng PLDI 2021, Nagar & Jagannathan CAV 2019, Timany 2021, Attiya PODC 2016 (bot check, not bypassed), Zakhour OOPSLA 2023, Sinchuk 2016, Randolph 2015, Shapiro RR-7506 2011 (HAL bot check; only a provenance folder in the collection, no PDF).

### Implication for the posted memo

- [inference] memo's "none on real code" is slightly too strong: Nieto 2022 (real causal broadcast, safety only) and Pek 2015 (anti-entropy models, with liveness) are partial exceptions.
- [inference] safer: no proof of Automerge/Loro/Yjs sync, and no liveness proof on real code for any editor. Scholar search found none; cannot rule out misses.
- [inference] open slots: (1) sync liveness + "in sync ⇒ identical documents" on real Rust; (2) machine-checked intention/non-interleaving for a text CRDT; (3) membership change and tombstone cleanup.
- I don't know whether Automerge/Loro sync-loop bugs are protocol or code bugs; not checked.

## (b) Convergence vs consensus

Consensus makes everyone pick one value forever. A CRDT lets each replica act alone and merge later, so there is no agreement step to prove.

- [fact] Gomes 2017: "Unlike strong consistency models, it is possible to implement SEC in decentralised settings without any central server or leader, and it allows local execution at each node to proceed without waiting for communication with other nodes."
- [fact] Blau 2020: "we posit that it is the safety requirement in traditional Distributed Consensus Algorithms which make them difficult"; Raft verification took "on the order of 45,000 lines of proof scripts" (Woos et al. 2016, quoted). Gomes's network model + convergence + RGA ≈ 620 + 380 + 775 Isabelle lines. [opinion] different properties, so not a clean comparison, but the gap is large.
- [fact] Nieto 2022: SEC = "Eventual Delivery: An update delivered to a correct replica is eventually delivered to all replicas" (liveness) + "Convergence: Replicas that have delivered the same updates eventually reach equivalent states" (safety).
- [fact] CALM, Laddad et al., VLDB 2022 (https://arxiv.org/abs/2210.12605): "programs are convergent without coordination iff they are monotone."

Ramesh's "it depends on what the merging algorithm is supposed to be" is right. By spec:
1. Convergence only: proved many times; useless merges satisfy it (last-writer-wins converges "at the cost of losing user input", Gomes 2017).
2. Intention preservation: no agreed formal statement (Fugue finds the 2016 spec incomplete; Peritext uses scenarios); never machine-checked as far as found. [opinion] hardest, and a spec problem, not a consensus-like protocol problem.
3. Sync liveness: only Timany 2021 (one counter) and Pek 2015 (models). [inference] memo's sync-loop bugs are this class; needs fairness assumptions and ranking functions.
4. Byzantine: Kleppmann & Howard, arXiv 2020 (https://arxiv.org/abs/2012.00472): [fact] "it is possible for a peer-to-peer database to be immune to Sybil attacks if and only if all of the possible transactions are I-confluent", vs Byzantine agreement that "typically require[s] at least 3f + 1 nodes"; delivery needs "any two correct nodes can communicate either directly, or indirectly via other correct nodes." Paper proofs; for CRDTs: "I leave a detailed proof of this conjecture in the context of particular CRDT algorithms for future work" (Kleppmann, PaPoC 2022).
5. Consensus returns: [fact] "a Byzantine consensus algorithm need only be used for those transactions that are not I-confluent" (Kleppmann & Howard); tombstone cleanup "can only be done using a consensus-based mechanism, which is only possible when the number of participating peers is small" (Karayel 2022).

[opinion] Plain convergence is easier than consensus; the effort would go into sync/delivery on real Rust and into choosing a spec stronger than convergence.

## Notes

- Long proof sections: definitions and theorem statements read, not every step.
- Collection's Met file labeled "JSEP, 2024" contains the arXiv 2022 text.
- 10 Scholar queries, ~25 s apart, no CAPTCHA.
