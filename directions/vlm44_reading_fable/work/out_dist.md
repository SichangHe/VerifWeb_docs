(authored by agents unless marked 🧑)

Reading guide, group dist (17 papers). Quotes are copied from the pdftotext output; ligature glitches (fi, ff) are normalized. All papers were read in part (abstract, intro, evaluation or results, conclusion or limits), not in full.

35 | Applying Formal Verification to Microkernel IPC at Meta, Quentin Carbonneaux, Noam Zilberstein, Christoph Klee, Peter W. O'Hearn, Francesco Zappa Nardelli, CPP, 2022
SHOWS: Two engineers proved two lock-free queues (used for inter-process messages in a new Meta microkernel OS) correct in Coq with Iris (a concurrent separation logic), on a pseudocode model of the C code; it found four simplifications (two memory barriers, one atomic load, one check removed) and bugs in client drivers, not in the queue itself.
QUOTE: "The proof work was completed in person months, not years, by engineers with no prior familiarity with Iris." (Abstract)
WHY: Gives a cost data point (about 1 month to learn Iris, 2 months generic queue, 1 part-time month ports queue), but it is a single-machine, safety-only, sequentially consistent model, so it settles little for distributed systems.
PRIORITY: low. Single-machine, small, not distributed.
READ: abstract, intro, 1.5 limitations, section 9 conclusion, grep of bug/effort lines.

39 | AutoMan- Facilitating Verified Distributed Systems Development Through Automatic Code Generation and Manual Optimizations, Zihao Zhang, Ti Zhou, Christa Jenkins, Omar Chowdhury, Shuai Mu, SOSP, 2025
SHOWS: A workflow that generates implementation code plus refinement-proof obligations (Dafny-style) from a TLA specification, with hand-written optimizations for hot paths; applied to Multi-Paxos, PBFT, a sharded key-value store, and CausalMesh; real code, verified by refinement; reports less manual effort than IronFleet/IronKV and similar speed.
QUOTE: "AutoManKV-I0 reduced manual effort by 97%, while the optimized AutoManKV-I1 achieved a 56% reduction." (Section 6.1)
WHY: Directly attacks the main cost problem of verified distributed systems (proof-to-code ratios of 7.79 for Verdi and 11.5 for Grove, as the paper cites); still needs a hand-written TLA spec and glue code, and the paper says it does not cover verified concurrent shared-state code.
PRIORITY: high. Newest verified-distributed-code cost reduction.
READ: abstract, intro, evaluation start (6.1), discussion (7), related work excerpt, conclusion.

41 | Continuous Formal Verification of Amazon s2n, Andrey Chudnov, Nathan Collins, Byron Cook, Joey Dodds, Brian Huffman, Colm MacCárthaigh, Stephen Magill, Eric Mertens, Eric Mullen, Serdar Tasiran, Aaron Tomb, Eddy Westbrook, CAV, 2018
SHOWS: Automatic proofs (symbolic execution, with specs in Cryptol) of the real C code of AWS's TLS library (HMAC, DRBG random generator, TLS handshake) run in CI on every commit; they ran 956 times in about a year and needed 3 manual updates; the handshake proof found one bug.
QUOTE: "In one year of code changes only three manual updates to the proof were required." (Section 1)
WHY: Shows the proof-must-survive-code-change problem can be solved when the proof is automated and the spec is stable; effort was about 3 months each for HMAC and DRBG and 8 months for the handshake; but it is a TLS library, not a distributed system.
PRIORITY: low. Crypto library, old, not distributed.
READ: abstract, intro, CI/metrics section (effort numbers), conclusion.

53 | Kani- A Model Checker for Rust, Remi Delmas et al., arXiv, 2026
SHOWS: Kani is a bounded model checker for real Rust code (it compiles Rust MIR into the CBMC engine), extended with function and loop contracts to reach unbounded proofs; used in CI on Firecracker (the VM monitor behind AWS Lambda), s2n-quic and the Rust standard library, finding six previously unknown bugs.
QUOTE: "Kani operates at scale in production CI, with over 16,000 harnesses verified per code change in the Rust standard library verification campaign." (Abstract)
WHY: Shows a low-annotation way to check real Rust code at scale; it checks local properties (panics, unsafe code, functional contracts), not distributed protocols.
PRIORITY: medium. Real-code tool, not distributed.
READ: abstract, intro, evaluation section (case studies, table of projects), contributions on contracts.

55 | Lessons from Building an Auto-Active Verifier in Lean, George Pîrlea, Vladimir Gladshtein, Qiyuan Zhao, Ilya Sergey, Dafny Workshop, 2026
SHOWS: A short talk paper about Veil, a framework (built entirely inside the Lean proof assistant) for verifying distributed-protocol transition systems with bounded model checking, SMT and interactive proofs; it lists lessons from 18 months of building it. It reports no outages or bugs found.
QUOTE: "When it comes to SMT-based proof automation, Veil is more than 10x slower than Ivy, the most closely related tool" (Section 3.5)
WHY: Shows a tool for protocol-level proofs that avoids trusting SMT solvers; it gives no evidence of a big problem solved, and performance is its main open issue.
PRIORITY: medium. Tool for us, but no results.
READ: whole paper (about 5 pages): abstract, sections 1-4.

56 | Lessons from the evolution of the Batfish configuration analysis tool, Matt Brown, Ari Fogel, Daniel Halperin, Victor Heorhiadi, Ratul Mahajan, Todd Millstein, SIGCOMM, 2023
SHOWS: Experience report on Batfish, a tool that simulates router configurations to compute the data plane and checks network policies; it dropped Datalog for an imperative simulator and BDDs (binary decision diagrams), and found that model fidelity problems come mostly from the many language features and undocumented interactions among them, not from software bugs. The check is on a model of router behavior, not on real router code.
QUOTE: "Replacing Datalog with an imperative routing simulation engine and a BDD-based data plane verification engine improved performance by three orders of magnitude" (Section 9)
WHY: A network-configuration verification success with real users; the paper states its added value for new designs is speed, "not outage prevention", and gives no outage counts; the unsolved items are debug-friendly source-level feedback and incremental computation.
PRIORITY: medium. Network outage class, practical lessons.
READ: abstract, intro (five lessons), usability section 5, conclusion and future work.

60 | Semantic-based Automated Reasoning for AWS Access Policies using SMT, John Backes, Pauline Bolignano, Byron Cook, Catherine Dodge, Andrew Gacek, Kasper Luckow, Neha Rungta, Oksana Tkachuk, Carsten Varming, FMCAD, 2018
SHOWS: Zelkova turns AWS access-control policies (JSON) into SMT formulas (strings, regexes, bit vectors) to decide who can access a resource; it is a decision procedure for a formal semantics of the policy language, deployed in S3, Config, Macie, Trusted Advisor, GuardDuty.
QUOTE: "Zelkova solves a PSPACE-complete problem and is invoked many millions of times daily." (Abstract)
WHY: A rare case of SMT-based verification used at huge scale on cloud configuration (99% of queries under 160 ms); the check is on policies, not on service code; it can answer "unknown" on unsupported constructs.
PRIORITY: medium. Strong deployment evidence, not distributed.
READ: abstract, intro, industrial experience (section VI), performance and conclusion parts.

61 | Smart Casual Verification of the Confidential Consortium Framework, Heidi Howard, Markus A. Kuppe, Edward Ashton, Amaury Chamayou, Natacha Crooks, NSDI, 2025
SHOWS: For CCF (the base of Azure Confidential Ledger), TLA+ specs of its modified Raft consensus (with reconfiguration) and its client consistency model were model checked and then tied to the C++ code by trace validation (replaying implementation logs against the spec) and simulation; six subtle bugs found before they hit production.
QUOTE: "find six subtle bugs in the design and implementation before they could impact production." (Abstract)
WHY: The most complete recent example of linking a TLA+ model to real distributed code in CI; cost: about 2 engineer-months (over 4 months) for consensus trace validation, 48 hours of exhaustive checking on 128 cores; open issues: state-space limits and spec-versus-code gaps.
PRIORITY: high. Real distributed system, model plus code.
READ: abstract, intro, trace validation section (6.2), bugs (section 7), lessons (section 8), conclusion.

62 | Systematization of Knowledge- Formal Verification of Consensus Protocols, Nikita Bondarev, Kirill Ziborov, Yury Yanovich, arXiv, 2026
SHOWS: A survey of over 20 verified consensus protocols (Raft, HotStuff, Tendermint, Algorand and others) with a maturity scale, a protocol/property/method table, and four named gaps.
QUOTE: "liveness verification remains underdeveloped, scalability constraints limit analysis to toy configurations, and verified models frequently diverge from production code." (Section 7)
WHY: Cheap list of unsolved problems to pick from: only about 30% of works treat liveness, explicit checkers run out beyond 4-10 nodes, models drift from Go/Rust code; blockchain-focused and a secondary source.
PRIORITY: medium. Gap list, survey not primary.
READ: abstract, intro, section 5 (open problems), conclusion; taxonomy tables skimmed only.

63 | Uncovering Bugs in Distributed Storage Systems during Testing (Not in Production!), Pantazis Deligiannis, Matt McCutchen, Paul Thomson, et al., Shaz Qadeer, Wolfram Schulte, FAST, 2016
SHOWS: P# (C# extension) lets engineers model the environment of real Azure components (Storage vNext, Live Table Migration, Service Fabric) and systematically explore thread and failure interleavings of the real code, checking safety and liveness specs; 8 serious bugs found, including ones that stress testing missed for months.
QUOTE: "Using P# we managed to uncover 8 serious bugs in our case studies." (Section 6)
WHY: Testing, not proof, but on real code with small harnesses (vNext harness about 2 person-weeks per text; modeling Fabric took about 5 person-months); a baseline any verification proposal should beat.
PRIORITY: medium. Real-code baseline, testing only.
READ: abstract, intro, vNext section skim, cost section 6, conclusion.

64 | Understanding Inconsistency in Azure Cosmos DB with TLA+, A. Finn Hackett, Joshua Rowe, Markus Alexander Kuppe, ICSE-SEIP, 2023
SHOWS: A small TLA+ model of what clients can observe from Cosmos DB across its 5 consistency levels, model checked and reviewed with a Cosmos DB developer; it exposed two documentation problems and explained the root cause of a past high-priority Azure outage in a dependent service. Model only, no code link.
QUOTE: "We document the 2 person-month development process of our specification" (Section I)
WHY: Shows that a spec of a service's user-visible behavior (not its implementation) can prevent outages in dependents; the paper itself says trace validation against the implementation is impractical for them.
PRIORITY: high. Outage-driven, cheap, relevant to cloud.
READ: abstract, intro, outage section V.C, related work, conclusion.

65 | Use of Formal Methods at Amazon Web Services, Chris Newcombe, Tim Rath, Fan Zhang, Bogdan Munteanu, Marc Brooker, Michael Deardeuff, technical report, 2014
SHOWS: Experience since 2011 using TLA+ and PlusCal model checking on the designs of S3, DynamoDB, EBS and an internal lock manager: bugs found in each, in specs of 100 to 940 lines; engineers learn it in 2-3 weeks; 7 teams use it. The check is on design models, not code.
QUOTE: "the shortest error trace exhibiting the bug contained 35 high level steps." (DynamoDB case study)
WHY: The canonical case for design-level model checking; the paper also states a limit: it knows of no feasible way to model "sustained emergent performance degradation" (retry storms and similar), and a missed liveness bug where liveness was not checked.
PRIORITY: high. Classic baseline, states unsolved class.
READ: whole paper skimmed: intro, results table, limits, DynamoDB section.

67 | VeriSMo- A Verified Security Module for Confidential VMs, Ziqiao Zhou, Anjali, Weiteng Chen, Sishuai Gong, Chris Hawblitzel, Weidong Cui, OSDI, 2024
SHOWS: A Rust security module for AMD SEV-SNP confidential VMs, proved in Verus (Rust verifier using SMT) against an adversarial hypervisor that can interrupt it and change hardware state at any time; real code with trusted hardware specs; near-zero guest overhead; the work found a confidentiality requirement overlooked by AMD SVSM.
QUOTE: "VeriSMo is fully verified for functional correctness, secure information flow, and memory safety." (Section 1)
WHY: Shows Verus can prove security of real systems Rust code at about thousands of lines (Table 2: for example the allocator has 386 exec lines and 1003 proof lines); one machine, not distributed.
PRIORITY: low. Single-node, cloud-security, Verus.
READ: abstract, intro, evaluation 8.2-8.4 incl. Table 2, conclusion; verification design only skimmed.

72 | 3DGen- AI-Assisted Generation of Provably Correct Binary Format Parsers, Sarah Fakhoury, Markus Kuppe, Shuvendu K. Lahiri, Tahina Ramananandro, Nikhil Swamy, arXiv, 2024
SHOWS: LLM agents turn RFC text into specs in EverParse's 3D language, checked with symbolic test generation, then EverParse produces verified C parsers; tested on 20 Internet formats; it found errors in 3 handwritten specs (UDP, ICMP, VXLAN), merged upstream.
QUOTE: "We have evaluated 3DGen on 20 Internet standard formats, demonstrating the potential for AI-agents to produce formally verified C code at a non-trivial scale." (Abstract)
WHY: Shows the spec-writing bottleneck can be eased with AI plus tests; for TCP and IPv4 the generated spec was underconstrained when tests were weak, so it is only as good as the test oracle. Parsers only.
PRIORITY: low. Parsers, not distributed.
READ: abstract, intro, problem formulation, results (section on handwritten spec comparison), related work excerpt.

73 | Configuration Validation with Large Language Models, Xinyu Lian, Yinfang Chen, Runxiang Cheng, Jie Huang, Parth Thakkar, Minjia Zhang, Tianyin Xu, arXiv, 2023
SHOWS: Ciri prompts LLMs (8 models) to check config files of 10 open-source systems; average F1 0.72 at file level and 0.56 at parameter level on synthetic data; on 51 real misconfigurations it caught 33-45. Not formal.
QUOTE: "among which Ciri can detect 33-45 misconfigurations" (Section V, real-world dataset of 51)
WHY: Shows LLM checking is fast (10-70 seconds versus 20-230 minutes for config tests) but weak on parameter dependencies and environment issues; gives no guarantee, so it is only a screening step.
PRIORITY: low. No formal guarantee.
READ: abstract, intro, evaluation findings (V), comparison with Ctest, conclusion paragraph.

74 | Making Deployments Safe at Meta- Health Checks for Continuous Change-Safety, Prakash KL, Anton Korenkov, Uttam Thakore, Christopher Hegre, arXiv, 2026
SHOWS: Experience report on Meta's Service Health Checker, a mandatory gate on every code and config change that watches metrics during phased rollouts and triggers rollback; false positive rate cut from 12.1% to 2.7% in a year. No formal method; no counts of prevented outages are given.
QUOTE: "Every code and configuration change entering Meta production passes through SHC as a mandatory gate." (Section I)
WHY: Describes the outage class (bad changes) that formal checks aim at, and shows the real operating cost is false alarms; leaves open what could be proven before rollout rather than detected during it.
PRIORITY: low. Monitoring, not verification.
READ: abstract, intro, quantitative-impact paragraph, lessons learned, related work, future work.

75 | Testing Configuration Changes in Context to Prevent Production Failures, Xudong Sun, Runxiang Cheng, Jianyan Chen, Elaine Ang, Owolabi Legunsen, Tianyin Xu, OSDI, 2020
SHOWS: Ctests turn existing unit and integration tests of five cloud systems into tests parameterized by configuration values, so a config change is tested against the code it affects; on 64 real failures, 1,055 injected misconfigurations and 92 Docker config files; real code, testing.
QUOTE: "Ctests detected the failure-inducing configurations in 96.9% of the real-world failures." (Section 1.1)
WHY: Quantifies the outage class (the paper cites configuration changes as 16% of Facebook service incidents and the second largest cause of disruptions in a main Google service) and shows testing catches most known cases, which sets the bar for a formal approach; it also found 14 new bugs (12 confirmed).
PRIORITY: medium. Outage evidence and strong testing baseline.
READ: abstract, intro, discussion and limitations (7), conclusion; evaluation tables only skimmed.
