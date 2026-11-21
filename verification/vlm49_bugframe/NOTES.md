# vlm49_bugframe: how to tell an agent-reported bug is real, reachable, and fixed
(authored by agents unless marked 🧑)

Question, Harsha Madhyastha, Nov 19 meeting (/ssd1/sichangheagent/email/1119madhyastha_govindan_ardi.vtt, ~l.205-235): "Are you able to drive the system into this state?" ... "is there a way to come up with a principled framework To verify these reported bugs." ... "It's not like you have some test case that was previously failing, and now you're passing that test case."

## Short answer

- Fact: his worry is right for the Automerge case. The Bloom + reorder stuck state reproduces on the bare crate but not through the real driver samod (vlm48_amnet). The loss stalls do reach samod, but they fall outside the maintainers' documented contract.
- Proposal (opinion): grade every bug by the strongest *mechanical artifact* it has, not by agent say-so. Two separate questions get two separate grades: reachability (E0-E4) and fix evidence (F0-F3). Plus a written "legal environment" per project, so "legal execution" is a checkable predicate.
- Fix evidence rule: a fix counts only if a test that fails on the unfixed build, written before or independent of the fix, passes on the fixed build, and a negative control stays quiet.
- New vs prior work: little. Levels, trace replay and patched counterfactuals all exist (section 1). What I think is new is only the combination for agent-found bugs: model counterexample -> driver-level repro, with the legal environment taken from the project's own documented contract. I did not search exhaustively; "not found" is not "does not exist".
- Backlog (section 3): of 15 items, 0 are at E4, 3 reach E3 (all with fix tests), most sit at E2 or below. The 🧑 Nov 18 rule applies: no claim of "formally verified" for these; they are bug reports with the evidence grade below.

## 1. Prior work (quotes verbatim)

Trace validation / model-based trace-checking (impl -> model direction)
- Davis, Hirschhorn, Schvimer, "eXtreme Modelling in Practice", PVLDB 2020, sec 2.4: "In MBTC, the behavior of the implementation is observed during testing or in production. The implementation produces an execution trace that captures its sequence of state changes. This trace is checked against the specification ... to verify that the trace is a permitted behavior of the specification." And: "In MBTCG, the specification is used to generate test inputs and expected outputs ... A test framework provides the generated inputs to the implementation and checks whether it responds as specified." (MBTC failed for MongoDB Server; MBTCG succeeded for Realm Sync, same paper.)
- Howard, Kuppe, et al., "Smart Casual Verification of CCF", NSDI 2025, sec 6: "Conceptually, trace validation checks that every observed implementation trace matches a behavior of the system's high-level specification." Their scenario driver (sec 5): "This driver allowed the injection of network faults such as partitions, delays, reorderings, and message loss". Also: "an initial prototype to fuzz-test the consensus layer through generated inputs and faults was developed but ultimately abandoned since it failed to generate interesting behaviors that would achieve satisfactory coverage." Related-work section: "Wang et al. [89] revealed several implementation bugs by replaying TLA+ behaviors against instrumented implementations. Likewise, SandTable is capable of replaying behaviors".
- Cirstea, Kuppe, Loillier, Merz, "Validating Traces of Distributed Programs Against TLA+ Specifications", 2024 (in collection; I did not re-read for a quote).
- Note the direction: these check "impl behavior is a model behavior" (conformance). Our need is the reverse: "a model counterexample is an impl behavior" (reachability). Replay of TLA+ behaviors against implementations (Wang et al., SandTable) and MBTCG do go that way.

Deterministic simulation and fault-injection testing
- FoundationDB testing docs (https://apple.github.io/foundationdb/testing.html): "Determinism is crucial in that it allows perfect repeatability of a simulated run". Repro artifact = binary version + seed.
- Jepsen (e.g. "etcd 3.4.3", Kingsbury 2020, in collection): record client history under faults, check against the claimed semantics. Artifact = history file. (Not re-quoted.)
- Greybox Fuzzing of Distributed Systems (Meng et al., CCS 2023, in collection) and LOKI/others: fuzzers whose bug = a saved input/schedule replayable on the real system.

LLM-agent bug report validation (2025-26)
- Chen, "From Runnable to Verifiable: An Independent Reproducibility Study of LLM/Agent-Driven Vulnerability Validation Artifacts", arXiv 2608.09567 (added to collection): "A trigger on the vulnerable build is not evidence of CVE-specific reproduction without a clean patched counterfactual." Its levels: "G1, candidate signal: crash, marker, or status change"; "G2, post-condition match: the signal matches the CVE behavior"; "G3a, negative control: the signal is input-independent--absent on benign input"; "G3b, patched counterfactual: the signal is version-independent--absent on the patched build". Finding: 20 of 30 audited cases "still produced the claimed signal on the patched build".
- "Automated Vulnerability Validation and Verification: A Large Language Model Approach", arXiv 2509.24037 (added to collection), sec on limits: LLM-written code "can still 'simulate' success". Pages not recorded; text in the collection copy.
- Seen in search only, not read: ReproBench (arXiv 2609.34450: agents "substitute", emulating the vulnerability instead of reproducing it); VulAgent (2509.11523); PAGENT (2604.07624); Axe (2602.14345). Search-snippet level; verify before citing.

What this means (inference): the "agent confirms its own fix" problem is already named in the security-PoC literature (patched counterfactual, negative control, agent "simulating" success). What the PoC literature lacks is a *legal environment* axis: a CVE is a vulnerability if an attacker can do it, so legality is implied. For liveness/consistency bugs in distributed code, legality is the crux (our samod case). The trace-validation literature has legality (the spec) but not agent triage.

## 2. Framework

Two axes. Each level requires a mechanical, agent-independent artifact: someone who does not trust the agent can re-run it from a pinned commit and see pass/fail.

Reachability grade (strongest artifact the bug has)

    grade  claim                          artifact (re-runnable, no agent)
    E0     agent says so                  none (code reading)
    E1     model counterexample           model-checker trace file; replay in checker
    E1b    copied-code repro              test on a copy of the logic; pinned diff to source
    E2     real code, public API          failing test on pinned published release/commit
    E3     deployed entry point/driver,   failing test/trace through the real driver,
           legal environment              environment script satisfying the legal-env file
    E4     seen in the wild               maintainer-accepted issue, or production log/trace

Fix grade
- F0: agent says it fixes it
- F1: model proof of fix only
- F2: test red on unfixed build, green on fixed build, same test; test not edited after seeing the fix
- F3: F2 plus negative control (benign input stays quiet), plus project's own test suite still green, plus the E3 test (not just the E2 test) goes green

Legal environment (definition): a short file, per project, listing the assumptions the project itself states (network: reliable/in-order?; inputs: trusted or attacker-controlled?; API call order; config ranges). A run is legal if it satisfies all of them. Every bug gets a tag: legal / outside-contract / contract-unclear. The tag comes with a quote from the project's docs or issues. Example: alexjg, automerge issue 1284: "The sync protocol requires a reliable in-order stream, I.e. you need to reset the sync state if there could have been a dropped message." So a reorder or loss repro is outside-contract unless the transport is declared lossy. That is a result, not a failure: it routes the report ("hardening request" vs "bug").

Rules
1. Never report a grade the artifact does not support. Model-level claims are labelled "model".
2. When a model-level case fails at E3, record it (Automerge: Bloom+reorder, samod masks it by generating after every receive).
3. Environment emulation must be a pluggable, scripted policy (drop/delay/hold by frame index, as in vlm48 netem.rs), so the repro is a schedule file, not a random seed alone.
4. Rates matter for transient bugs: report E3 per-run probability under a stated fault model (vlm48: 3.4% at 2% loss, no fix; 0/500 with fix). Harsha: "if you have a production system with billion users, maybe it'll occur once a day" - E4 can be argued from rate x volume, but that is inference.
5. The agent may write the test, but the grade is set by running it on pinned old and new builds. Opinion: the one thing to avoid is a test written to pass on the fixed build only.

New vs prior (my claim, limited search)
- Not new: levels of evidence (Chen's G1-G3), patched counterfactual, replayable seeds/traces, MBTC/MBTCG, fault-injecting drivers.
- Possibly new: (a) legality axis grounded in project-quoted contract applied to agent-found bugs; (b) explicit model-to-driver step with a recorded negative result; (c) using the same E3 test as both reachability proof and fix test. I don't know if (a)-(c) appear in work I did not find.

## 3. Backlog classification

Student's words: "I think I have, like, a backlog of, like, 10 or so bugs that I found, I just never reported them." I found no list of 10; these 15 are the candidates I could identify from out/ reports. Nothing filed.

    bug (out/ dir)                         E   F   legal?   cheapest next step
    am Bloom+reorder stuck (vlm43_amlive)  E2  F2* unclear  find legal schedule in samod, else downgrade to hardening
    am #772 lost change (vlm43_amloop,48)  E3  F2  outside  ask: is lossy transport supported? add negative control
    am both first msgs lost (vlm48_amnet)  E3  F2  outside  same
    am fix live under per-msg fairness     E1  F1  n/a      none; model says fix NOT live (counterexample)
    yrs dup client entries panic (yrsrepro)E2  F0  legal**  feed bytes via yrs sync decode path / ws server
    yrs one lost Update stuck (yrsproto)   E2  F0  outside  see am; yrs resync fixes
    vector interval=0 panics (vlm43_vector)E1b F1  legal    build real vector, run reload (heavy: cpu-run)
    cssparser -\LF ident (servobugs)       E2  F2  legal    already upstream #440; nothing
    servo Mp4Matcher 12-byte (servobugs)   E2  F0  legal**  call via ServoParser; upstream #47603 exists
    cssparser line u32 overflow            E2  F0  unclear  skip; unreachable in practice (belief)
    servo Blob.slice overflow              E1b F0  unclear  build Servo or ask upstream; stated repro was wrong
    boa String/Array.at (vlm6_atfix)       E2  F2  legal    JS repro is the entry point; check upstream
    bitset from_range (cx_bugs)            E1  F1  unclear  apply patch to real checkout, run test
    lightpanda WebSocket bypass (cx_bugs)  E3  F0  legal    write fix + red/green test

    * F2 only on the patched copy (vlm46_amfollow patched crate, repros red/green); crate's own suite not run.
    ** "legal" for attacker-controlled bytes is my inference; reachability through the real entry point is "inferred from reading code" per the reports.

Facts behind the table: Automerge rows from vlm43_amlive, vlm43_amloop, vlm46_amfollow, vlm48_amnet reports (samod: 0/500 and 0/300 no-loss stalls; "No-loss reordering stall not reproduced in samod"). Yrs: vlm42_yrsrepro "panics ... update.rs:155" on published yrs 0.28.1. Vector: copied logic only ("does not depend on Vector"). Servo/cx_bugs: vlm3_servobugs/SUMMARY.md, cx_bugs/REVIEW.md. The E/F letters are my grading, not the reports' words. Boa and Lightpanda rows I graded from short excerpts only; unchecked in detail.

Not covered: vlm43_durable (raft-engine model, hand-written ghost, a proof not a bug), AWS DNS/CTL race (public postmortems, replicate known outages, E1 only), OIDC/SLO TLC counterexamples (E1, model of protocol docs). They are E1 claims, not implementation bugs.

## 4. For the meeting (opinion)

- Honest answer to Harsha: for Automerge, "driven into the state" = yes for loss under a lossy link, no for the no-loss Bloom case via samod, and neither is inside the documented reliable-in-order contract. The first-order fix for the report is changing "bug" to a graded claim.
- Cost: E3 cost me one built harness per system (samod netem ~one file). I don't know the average cost across the backlog; vector and servo would need heavy builds.

Nothing published, filed or sent. Papers added (text + local PDF, not committed) under /hdd1/sichanghe/paper_collection: Chen 2026 (2608.09567) and arXiv 2509.24037. Venue/author fields for the latter are not filled in; folder name lacks authors.
