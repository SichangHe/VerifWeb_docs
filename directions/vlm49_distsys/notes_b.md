BFT consensus: Rust implementations and verification targets (agent b)

(authored by agents unless marked 🧑)
Date 2026-11-13. F = fact (source), I = inference.

CAVEATS
- Google Scholar returned a CAPTCHA (challenge_action_required); not bypassed. Used plain Google via pb-browser-page-extract instead, plus arXiv abstract pages. Papers below are NOT Scholar-ranked.
- Yale Mysticeti PDF (flint.cs.yale.edu) failed TLS verification; not downloaded; title is from a search snippet only, authors unknown.
- ACM LiDO-DAG page was Cloudflare-blocked; only title seen.
- Production-user claims are from READMEs only; not independently checked. PBFT and Narwhal/Bullshark usage not researched in depth.
- LOC = `cat *.rs | wc -l` on depth-1 clones, including tests and comments.

1. TENDERMINT / MALACHITE
Used in practice
- F Arc (Circle L1): circlefin/malachite README: "It now serves as the consensus foundation for Arc, a new purpose-built blockchain developed by Circle."
- F Starknet ecosystem funded/prompted it; Farcaster collaboration (README acknowledgements).
- F Cosmos chains use Tendermint/CometBFT, which is Go (I: not Rust).
Rust implementations
- malachite (github.com/circlefin/malachite, crates prefixed arc-malachitebft-). Last push 2026-10-19, 464 stars, not archived (F, gh api). README: "has not been externally audited" (F).
  - Total 96,256 lines Rs. Pure consensus core: core-state-machine 1,198; core-votekeeper 2,208; core-types 2,794; core-driver 9,524; core-consensus 15,173 (F, wc).
  - Rest (engine, network, sync, wal) is async actor code (ractor) and libp2p.
- tendermint-rs (informalsystems/tendermint-rs): 672 stars, pushed 2026-11-11 (F). About 23k lines in tendermint + light-client*. It is a types/RPC/light-client library, NOT a consensus engine (I, from README list: light client verifier, detector, RPC, ABCI).
- lambdaclass/tendermint_consensus appeared in search (docs.rs); not examined.
Real bugs (all in malachite engine, from circlefin/malachite issues)
- #1201 https://github.com/circlefin/malachite/issues/1201 "WAL returns early without reply when already at height, causing silent consensus failure". Body: "returns early without sending a reply when the requested height equals the current height ... Consensus gets stuck waiting for a response". Liveness bug in glue code, not in the protocol core.
- #1240 https://github.com/circlefin/malachite/issues/1240 "ProcessSyncedValue reports wrong proposer when validator set rotates per height (catch-up crash)". Body: "the proposer it derives is therefore wrong, and the application (or the core driver) detects a proposer mismatch and panics".
- #1135 https://github.com/circlefin/malachite/issues/1135 "Panic on node receiving the same proposal from different validators in same round". #1208 same panic: "BUG: Received proposals from different validators in the same round."
- #1207 "Node assumes it is in the validator set"; #1613 "engine: panics instead of erroring when a node's address is in the validator set but no signer is configured".
- I: bugs cluster at the engine/validator-set/WAL boundary, not in the vote-counting state machine. This matches where proofs of an abstract spec do not reach.
Prior formal verification
- F Malachite ships Quint specs (specs/consensus/quint: consensus.qnt, driver.qnt, votekeeper.qnt, statemachineAsync.qnt) and a CI "mbt" model-based-testing workflow (README badges) linking Rust to Quint traces. This is testing, not proof (I).
- F Tendermint TLA+ spec by Braithwaite, Buchman, Konnov, Milosevic, Stoilkovska, Widder, Zarick: "Formal Specification and Model Checking of the Tendermint Blockchain Synchronization Protocol (Fastsync)", FMBC 2020, OASIcs 10.4230/OASIcs.FMBC.2020.10 (title seen in search; author list from memory, I).
- F Ivy proofs of Tendermint safety in the Tendermint spec repo (docs.tendermint.com/master/spec/ivy-proofs).
- F tendermint-rs repo: "Tendermint in Rust with TLA+ specifications" (README), spec for light client, fastsync, fork cases.
- F SoK 2608.21935 cites Maung Maung Thin, Dong, Bai, Dong, "Formal analysis of a proof-of-stake blockchain", ICECCS 2018, and notes the censorship vulnerability found.
Proposed verification target (I)
- Verify core-votekeeper + core-state-machine (about 3.4k lines) with Verus or Aeneas/Lean against the Quint/TLA+ round state machine; prove the quorum-threshold counting and the locking rules (lockedValue/validValue) preserve agreement. Then core-driver (9.5k) as stretch.
- Why: pure, synchronous, generic over a Context trait, no I/O. Bugs found so far are outside it, so the proof would not catch them; a second target is the engine's height/validator-set/WAL handshake (#1201, #1240 class), which needs async modelling.
- Cost guess (I): core crates need ~1-2 person-months for the state machine plus votekeeper; the generic Context trait and heavy iterators/hash maps in votekeeper are the main friction. Not measured.

2. HOTSTUFF FAMILY (Aptos / Diem / Jolteon)
Used in practice
- F Aptos mainnet consensus: aptos-core/consensus is Rust. Directory contains consensus-types, safety-rules, dag, quorum_store (Jolteon-style 2-chain per round_manager/2chain names; I). Diem/LibraBFT (HotStuff variant) is the ancestor (I, from memory; Diem repo archived).
- F aptos-labs/aptos-core: 6,440 stars, pushed 2026-11-13.
Rust implementations
- aptos-core/consensus: 96,580 lines Rs; safety-rules: 3,997 lines (F, wc). The safety-rules crate is the small, security-critical part (vote/proposal/timeout signing guard) and is isolated from the rest.
- Other: Diem archived codebase (not checked).
Real bug
- F aptos-core #20801 https://github.com/aptos-labs/aptos-core/issues/20801 "[Bug][consensus] Liveness deadlock after BlockStore::rebuild due to HQC regression below SafetyRules preferred_round and one_chain_round". Body: "the validator is deadlocked: it cannot sign a proposal as leader because SafetyRules::guarded_sign_proposal ... fails with IncorrectPreferredRound, and it cannot sign a timeout because SafetyRules::safe_to_timeout ... fails with NotSafeToTimeout." Open; includes a repro test. Interaction bug between BlockStore and SafetyRules persisted state: exactly the cross-component invariant that a spec refinement would state.
Prior formal verification
- F Carr, Jenkins, Moir, Miraldo, Silva, "Towards formal verification of HotStuff-based Byzantine fault tolerant consensus in Agda", NFM 2022, pp. 616-635 (citation from SoK ref [9]). Models LibraBFT, which is the Diem/Aptos ancestor.
- F Jehl, safety proof of simplified HotStuff in Ivy and TLAPS (per Google result summary; I have not opened it; the summary also cites it as in the arXiv 2026 survey).
- F SoK 2608.21935: "many works focus solely on safety"; "Tree-based models used in protocols like HotStuff make proving liveness more difficult".
Proposed target (I)
- safety-rules (4k lines): prove the monotone-watermark invariants (preferred_round, one_chain_round, last_voted_round never decrease; never sign two conflicting votes per round) in Verus, and state the BlockStore-side precondition that #20801 violates. Small, isolated, and has a real open bug at its interface.
- Cost guess (I): 4k lines but depends on aptos crypto and serialization types; abstract those as opaque; 1-2 person-months. The full round_manager (async, tokio) is far harder.

3. NARWHAL / BULLSHARK / MYSTICETI (SUI)
Used in practice
- F Sui mainnet. Mysticeti paper (arXiv 2310.14821, "Mysticeti: Reaching the Limits of Latency with Uncertified DAGs") describes the protocol Sui deployed (I: stated from knowledge, only the title was seen in search). A Yale paper's snippet says Mysticeti is used by Sui and IOTA.
Rust implementations
- MystenLabs/sui consensus/core (Mysticeti): 52,049 lines Rs, of which about 7,866 in files whose path contains "test" (F, wc). Repo 7,787 stars, pushed 2026-11-13. Narwhal/Bullshark was the older Sui consensus, in the same repo earlier (I: Sui issue #13091 mentions a "narwhal docker example"; current status unchecked).
- Dependencies (I): tokio, Sui crypto crates, consensus-config/types.
Real bugs
- Not found. gh search on MystenLabs/sui for "mysticeti" returned only upgrade/protocol-version issues, not consensus safety bugs. Absence of evidence only; Sui's consensus bugs may be handled via private security reports (I).
Prior formal verification
- F Bertrand, Ghorpade, Rubin, Scholz, Subotic, "Reusable Formal Verification of DAG-based Consensus Protocols", arXiv 2407.02167 (2 Jul 2024; v2 18 Mar 2025). Abstract: "safety-verified specifications for five DAG-based consensus protocols ... DAG-Rider, Cordial Miners, Hashgraph, and Eventual Synchronous BullShark ... We employ TLA+ ... and the TLAPS proof system".
- F Coglio, McCarthy, "Formal Verification of Blockchain Nonforking in DAG-Based BFT Consensus with Dynamic Stake", arXiv 2504.16853 (23 Apr 2025). ACL2, "verified in 1 minute by ACL2"; models Aleo-style DAG BFT.
- F "Mechanized Safety and Liveness Proofs for Mysticeti" (Yale FLINT, sp26.pdf; title and venue guess "IEEE S&P 2026" from the filename only, I). Not read.
- F "LiDO-DAG: A Framework for Verifying Safety and Liveness ..." ACM DL 10.1145/3729306 (title only).
Proposed target (I)
- consensus/core: the committer / commit-rule logic (decision for leader slots: direct and indirect rules) and the DAG block-acceptance checks (ancestors, round, timestamps) as pure functions. Prove: two honest validators never decide different leaders for the same slot, linked to the Yale mechanized model.
- Cost guess (I): without reading the commit code in detail, assume the commit logic is a few thousand lines, tightly coupled to DagState (in-memory store with Arc/RwLock). A Verus proof needs a functional extraction of the decision rule, 2-4 person-months. Mysticeti has an existing mechanized protocol proof, so the implementation refinement is the open gap.

4. PBFT
Used in practice
- F Hyperledger Sawtooth PBFT engine in Rust: hyperledger/sawtooth-pbft, archived, last push 2024-02-01 (gh api). Others: Hyperledger Fabric 0.6 and Tendermint-style systems moved off it (I, from memory, unverified).
Rust implementations
- 0xjeffro/pbft-rust: 55 stars, pushed 2024-09-16; Szymongib/pbft-rust: 5 stars, pushed 2024-03-08. Both look like hobby/educational projects (I, not read). LOC not measured.
- sawtooth-pbft: archived, so no maintenance.
Real bugs: not researched.
Prior formal verification: not researched here. Many TLA+/Coq PBFT models exist (I, from memory, unverified).
Proposed target (I): low priority; no maintained production Rust PBFT. If PBFT is wanted, port nothing: verify a small PBFT replica core from scratch only if a customer exists. Porting cost: sawtooth-pbft is the best candidate in Rust but archived, so verification would be of a dead codebase.

RANKING FOR VERIFICATION (I)
1. Malachite core-votekeeper + core-state-machine: small, pure, maintained, in production (Arc), existing Quint spec to refine, ongoing bugs show the real risk is at engine boundaries.
2. Aptos safety-rules: 4k lines, one open bug at the BlockStore interface.
3. Sui Mysticeti commit rule: protocol-level proof exists (Yale), but code coupling is heavy.
4. PBFT: skip.

PAPERS WORTH KEEPING
1. Reusable Formal Verification of DAG-based Consensus Protocols. Bertrand, Ghorpade, Rubin, Scholz, Subotic. arXiv cs.LO, 2024 (v2 2025). https://arxiv.org/pdf/2407.02167
2. Formal Verification of Blockchain Nonforking in DAG-Based BFT Consensus with Dynamic Stake. Coglio, McCarthy. arXiv, 2025. https://arxiv.org/pdf/2504.16853
3. Systematization of Knowledge: Formal Verification of Consensus Protocols. Bondarev, Ziborov, Yanovich. arXiv, Aug 2026. https://arxiv.org/pdf/2608.21935
4. Towards Formal Verification of HotStuff-based Byzantine Fault Tolerant Consensus in Agda. Carr, Jenkins, Moir, Miraldo, Silva. NFM 2022. PDF URL not found (cited by SoK ref [9]).
5. Mechanized Safety and Liveness Proofs for Mysticeti. Yale FLINT Group (authors not seen). 2026. https://flint.cs.yale.edu/certikos/publications/sp26.pdf (not read; TLS failed).
6. Formal Specification and Model Checking of the Tendermint Blockchain Synchronization Protocol. FMBC 2020. https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.FMBC.2020.10
7. Mysticeti: Reaching the Limits of Latency with Uncertified DAGs. arXiv 2310.14821, 2023 (protocol, not verification). https://arxiv.org/abs/2310.14821
(LiDO-DAG, ACM 10.1145/3729306, 2025: seen by title only; not recommended until read.)
