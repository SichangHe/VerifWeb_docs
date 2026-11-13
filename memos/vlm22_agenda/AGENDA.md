# Meeting agenda, Nov 10: formal verification with Arvin
(authored by agents unless marked 🧑)

Assumption: 60 minutes; no source gives a length.
Who Arvin is: not confirmed. The Nov 3 transcript only has "I was making this comparison to Arvin" and "I told Arvin" (speaker 4, unlabeled). Its file name includes "ghavidel"; whether that is Arvin is a guess.

Private: the bug drafts and the TeamTypeV finding have not been filed or published. Decide before showing them to anyone outside the group.

## 0. Recap of Nov 3 asks (3 min)

From the Nov 3 meeting notes (speaker names are guesses):
- "Write down 10 different things that you might like to verify, either about individual JavaScripts or the engine itself."
- "you need to have some differentiator"
- start small; distributed liveness is crowded, and a wrong proof gives little feedback

## 1. Web verification: the 10 asked-for targets (15 min)

Results:
- 13 candidate targets, each tied to a real failure (JIT side effects, JIT range analysis, garbage collector, Wasm sandbox, tab isolation, URL parser, HTML sanitizer, and more). Most are proofs of small hand-written models, not of engine code.
- real bugs found and confirmed by re-running them, not yet filed: Boa garbage collector use-after-free (an object revived by its finalizer is freed anyway); rust-url fails 69 of 896 standard tests, one bug class proved; 4 Nova/Boa drafts (integer conversion, toString radix, copyWithin and setFromBase64 panics); 13 bug-report drafts in total (Boa, Nova, Wasmtime, Lightpanda, Servo).
- 3 pitches: (A) certified JavaScript rewrites for web-archive replay, (B) a verified request and session core for agent browsers, (C) checking JIT output so tenants can share a process.
- 10 newer ideas outside JavaScript engines, e.g. caches serving one user's page to another (2,512 affected sites), cookie consent not staying revoked (22 of 281 sites), HTTP request smuggling. "No formal prior work" comes from searches, not an exhaustive review.

Questions for Arvin:
- which 2 or 3 of these are worth a semester, and what is the differentiator?
- is "proof on a small model plus a bug found in real code" a publishable result, or must the proof cover the real code?

## 2. Distributed liveness proofs and the literature database (12 min)

Results:
- Ricart–Agrawala mutual exclusion in Verus: every started request eventually enters, under stated fairness, for any execution; "66 verified, 0 errors". 3-node model with repaired unbounded clocks.
- Raft: whole executable safety and liveness was audited by several reviews; the final verdict is not in the sources I read (unknown).
- Viewstamped Replication: blocked; no checked non-Rust liveness proof found to start from.
- literature database: 2375 sources, 1150 cases, 291 with a liveness guarantee, 63 machine-checked on running code. Takeaway: such proofs assume fairness plus an environment that stabilizes, and cost 5 to 40 proof lines per code line.
- technique pages (one page per verification technique): the task is marked done, but only an index page is in the notes folder; status unclear.

Questions for Arvin:
- given "crowded", is there a niche here, e.g. agents writing liveness proofs, or should this stop?
- are fairness and stabilization assumptions acceptable to reviewers, or a known weakness?

## 3. Rust standard library verification challenge (Amazon) (12 min)

Results:
- none of the 11 attempted challenges is complete. Closest: atomic types (1140 of 1140 Kani proofs pass; 128-bit types and wrapper-only contracts remain), C strings (16 of 16 pass; uninitialized memory not covered), Rc (1478 pass, 1 fail).
- common gaps: bounded lengths and concrete types, while the rules ask for any length and generic T (open upstream issue #734 asks for a ruling).
- Verus is not an approved tool yet. Its application (issue #554) is approved; the remaining step is a pull request adding Verus to CI. The Verus team says it is "nearly ready but not quite there yet".
- Verus attempts proved only copied models (e.g. 4 to 8 checks each), not the real library code; Verus cannot parse the real Vec file.
- 🧑 human plan: "sending a draft PR for something small and also make it clear that it would be blocked by Verus support" to learn the maintainers' attitude. A draft PR body exists, not sent.

Questions for Arvin:
- wait for Verus support, or finish with Kani/VeriFast now?
- does this lead to research, or is it only engineering?

## 4. TeamTypeV (a collaborative editor in Rust) (10 min)

Results:
- Verus checks the real operational-transform code ("65 verified, 0 errors"): two concurrent edits converge whenever both start from the same text length, also through a queue of edits; no panics in those functions; the server keeps its invariant.
- trusted, not proved: string primitives, one editor-to-edit conversion, texts below 2^60 characters. Not proved: end-to-end convergence between editor and daemon.
- found by reading code, fix not verified: when a CRDT change does not fit the text, the daemon breaks its invariant or panics.
- position conversion (character offsets vs line/column): one failing input and one missing precondition found; details in the walkthrough.

Questions for Arvin:
- does verifying TeamTypeV meet the "differentiator" bar, or is it too close to existing CRDT/OT work?
- which remaining parts are worth proving: end-to-end convergence, networking, or the CRDT layer?

## 5. UIclient (3 min)

- status: blocked, waiting for runs without an LLM to finish and for Codex quota for agent runs
- the extension-agent prompt is frozen; a held-out Unity game (Chop Chop) is being checked for feasibility
- the latest takeaway exists only as a chat message I could not read; ask the UIclient agent if needed

## 6. Decisions wanted (5 min)

- pick the 2 or 3 verification targets to pursue next
- continue or stop distributed liveness work
- Rust std: send the small draft PR now, or wait for Verus
- TeamTypeV: keep it as a target, and whether to report the found bug to its authors
- what to show next week

## Sources

- Nov 3 notes: /ssd1/sichangheagent/email/vl_todo.md; transcript /ssd1/sichangheagent/email/1103madhyastha_govindan_ghavidel.vtt (lines 206, 354)
- web targets: /hdd1/sichangheagent/vl_meeting_work/out/msg_candidates.txt, out/msg_merged5.txt, out/vlm15_pitch/PITCHES.md, out/vlm4_drafts/ (incl. nova_drafts_report.md), out/vlm20_fvshape/REPORT.md, out/vlm20_imc/REPORT.md
- liveness: /shagent/work_logs/vl_ricart_liveness.md, vl_raft_whole_live.md, vl_vr_liveness.md, vl_technique_pages.md; /ssd1/sichanghe.github.io/src/notes/research/distributed_verification_db/index.md
- Rust std: /hdd1/sichangheagent/vl_rust_std/cloud_out/FINAL_STATUS.md, verus_tool_status.md, */verus/report.md, 0007 and 0013 second_review.md, draft_pr/; /shagent/work_logs/vl_rust_std.md, manager_mail/zulip-638851056.txt
- TeamTypeV: /ssd1/sichangheagent/teamtype--teamtype-evidence/walk_drafts.md; /hdd1/sichangheagent/vl_codex_saturate/teamtype_probe/ot/REPORT.md
- UIclient: /shagent/work_logs/uiclient_steer.md
