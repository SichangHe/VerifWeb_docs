# Scoping: a verified merging protocol as a Rust library
(authored by agents unless marked 🧑)

The request, from the Nov 19 advisor meeting (transcript `1119madhyastha_govindan_ardi.vtt`, lines 291-292):
- 🧑 Ramesh: "one maybe small project is to develop a verified, merging… protocol, or whatever, right? And as a Rust library. And this may… this may not satisfy the… you know, impact test, but it may be somewhat interesting."
- 🧑 It answers Harsha's question just before it: "if I publish the proof and whatever invariants it satisfies, can somebody else who uses my library build on part properties I've already proven."

Short answer:
- The project would be a Rust crate, verified in Verus, that does two things:
  - merging, i.e. a CRDT
  - the sync protocol that exchanges changes between peers
- It would export its specs, so that users' own Verus proofs can build on them.
- What is new would be a Verus-checked proof covering both the merge and the sync liveness of the executable Rust that ships.
- Effort, my guess with low confidence: about 2-4 weeks for a small CRDT plus sync, much of it reusing proofs from vlm47_amcode. A text CRDT like Automerge's would take months.

## 1. What it would be (proposal; scope is a judgment call for the human)

- Merge: one or more CRDTs.
  - Theorem: replicas that have received the same set of changes have equal state (convergence).
  - Smallest useful choice: an OR-map or a text CRDT such as RGA or Fugue. Counters and sets alone are already well covered by prior work.
- Sync: the Automerge-style protocol. Peers exchange heads and a Bloom filter of their changes, then send the changes the other side is missing.
  - With the timeout fix, our vlm47_amcode proofs already cover its safety and liveness at the code level.
  - So this half is mostly repackaging.
- Library form: specs exposed as Verus `pub open spec` and `ensures` clauses.
  - A user's own Verus code can then rely on statements such as "after sync, the documents are equal".
  - This is Harsha's composability question.
  - Inference: Verus supports this today, because a crate's `ensures` clauses are visible to dependent crates. I have not tested it across crates.

## 2. What prior work covers

Fact, from `directions/vlm41_crdtprior/REPORT.md` and `vl_meeting_work/out/vlm47_amcode/prior_work.md`, where each item is quoted with pointers:
- Merge correctness is well studied, but almost always for models or for code written for the verifier, and almost always safety only:
  - Gomes et al. 2017 (Isabelle): RGA, OR-Set, counter
  - Karayel and Gonzàlez 2022: WOOT
  - Nieto et al. 2022: Coq, executable OCaml subset
  - VeriFx, Peepul, Propel, Sal
  - Each assumes the network eventually delivers messages.
- Sync liveness: no machine-checked proof found, except ours (vlm47_amcode, Verus, on copies of Automerge's code, with a fix).
- Automerge: only bounded model checking (AMC, PaPoC 2023).

Web search today: Verus plus CRDT gave no hit. Projects linking a proof to Rust exist, but none proves the Rust code itself:
- SafeMesh (https://github.com/velvetmonkey/safemesh): Lean proofs of 5 CRDTs, including RGA/Text. Its Rust is checked by "differential tests against a Lean-generated oracle corpus", which it calls "evidence, not a universal theorem". These are search-snippet words; I did not read the repo.
- Axiom (https://github.com/roshworldwide/axiom): TLA+ plus Rust "linked by explicit refinement mappings", model-checked, "not proved" (repo description, via search).
- crdtlib (https://github.com/prg-grp/crdtlib): Lean 4 only, tied to an OOPSLA 2026 paper "Composing CRDTs Convergent by Construction". Not read.
- nickel-crdt (https://github.com/carbon-study/nickel-crdt): plans hax-based proofs of Rust, but has "no CRDT implementation or public API yet".

## 3. What would be new

These are inferences, to be re-checked against crdtlib and SafeMesh before any claim.

New:
- Proof of the deployed Rust itself, not a model, an oracle test or a separate OCaml or Lean program
- Liveness of sync in the same library as merge convergence
- Specs that client proofs can use

Not new:
- Convergence proofs of these CRDT algorithms
- Liveness of real distributed code in general (IronFleet, Anvil)

Impact risk:
- Ramesh already flagged it: "this may not satisfy the… impact test".
- My opinion: a fresh crate has no users. Verifying a copy of Automerge's own code, as vlm47_amcode does, ties the result to a library people use.

## 4. Effort (my guess, low confidence)

- Sync half: 1-2 weeks. The model, the code-conformance proof and liveness exist in `SichangHe/automerge--automerge` branch `vl-verus`. Work left:
  - port the proofs into a standalone crate
  - prove the 34 trusted specs we currently assume, at least the change graph and the Bloom filter
- Merge half, small CRDT (OR-map): about 1 week.
- Merge half, text CRDT (RGA or Fugue): weeks to months. Gomes et al.'s Isabelle RGA proof is the reference size.
- Cross-crate spec export demo: days.

## Open questions for the human

1. Is the deliverable a fresh crate, or verified parts of an existing one (Automerge, or yrs, the Rust port of Yjs)?
2. Which CRDT: an OR-map is quick, while text is what editors need?
3. Does "verified" have to cover the Bloom filter and the change graph, which we currently trust?
