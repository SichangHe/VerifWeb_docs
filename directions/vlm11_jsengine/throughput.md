# Verus proof throughput of our AI agents
(authored by agents unless marked 🧑)

Takeaway: the proof volume is measurable (fact); the agent-hours are not (no authoring timestamps survive), so every rate is a bracket. 41% of passing proofs carry a soundness caveat, and none is shown to be on upstream source.

## Facts (computed from local files)
- source: out/cx_proofs/REVIEW.md "Per-file inventory" (97 distinct entries parsed; the audit says 83 distinct contents, 150 paths; the 97 vs 83 gap is unexplained, probably my parse counting probe entries).
- verdict counts parsed: sound within model 30, overstated 15, unsound trusted contract 6 (= 51 "passing"); rejected 32; probes 14. REVIEW.md itself says 48 pass, so 51 vs 48 is a 3-file discrepancy.
- lines: non-blank, non-`//` lines of each .rs (script /tmp/cnt.py, regex heuristic). "Spec/proof" = lines starting with proof/spec fn, requires, ensures, invariant, decreases, assert, reveal, ghost, etc. "Exec" = everything else (incl. struct/use/global lines and hand-written models).
- all 51: 10132 lines = 6621 exec + 3511 spec/proof (exec:spec = 1.9:1).
- clean 30 only: 4852 lines = 3158 exec + 1694 spec/proof.
- by dir (total/exec/spec, files): cx_servo 5916/4043/1873 (31); cx_gc 1018/606/412 (5); vlm4_sbvfix 895/564/331 (1); vlm_servo 753/488/265 (7); vlm2_url 729/358/371 (1); vlm2_iso 527/355/172 (3); cx_loop 119/95/24 (1); cx_bugs 95/58/37 (1); vlm2_jit 80/54/26 (1).
- cx_builtins, vlm6_builtins hold JS conformance scripts (0 .rs files); vfy_at has 1527 .rs under src but 1 verus file, not in the audit. None contributes passing Verus lines here.
- caveat rate (fact, from audit verdicts): (15 overstated + 6 unsound) / 51 = 41%; unsound alone 6/51 = 12% (all six are old smallbitvec `ptr::add` variants, one root cause). Clean = 30/51 = 59%.

## Real code vs model (mostly fact, sample-based)
- I read headers of 5 files: boa_mark.rs "Verus model of boa_gc's stop-the-world mark phase"; path_spec.rs "hand-transcribed spec ... segment-level port"; sbv_full.rs "spec: inline encoding"; au.rs, p3.rs are re-written functions. Inference: all passing proofs are hand-written models/ports, not verification of upstream source. REVIEW.md agrees: "not a proof of ... correspondence to upstream execution".
- Upstream Rust lines modeled: not measured (no mapping in files). "Exec" lines above are model lines, not upstream lines. Treat "verified executable code" as an upper bound.
- Double counting: sbv has several near-identical versions (sbv_work, vlm4_sbvfix, heap, sbv_full), inflating cx_servo/vlm4 counts. Not deduplicated.

## Agent time (estimate)
- file mtimes are copy times: cx_gc proofs span 23:43-23:50 on 2026-11-03, cx_servo 23:44-23:46, vlm2_iso 22:03-22:08. Audited proofs land in one burst, 2026-11-03 21:59 to 2026-11-04 00:16 (about 2.3 h). This is a floor, not authoring time.
- ~/amh_work_logs (1.9 KB, two stub sessions) and ~/work_logs (one digest file) hold no timing. Only evidence: 42 Claude session logs for this directory; first-to-last timestamp spans sum to 31.5 h, of which one session (e61ccdf3, 2026-11-06 to 11-07) is 25.3 h of wall-clock with idle gaps; the other 41 sum to about 6.2 h. The cx_* proofs were likely written by codex agents (cx_ prefix, inference) whose time is not in these logs.
- per-directory hours: not recoverable. Only bounded: every audited dir was written inside the 2.3 h burst window.

## Rates (estimate = fact lines / assumed hours)
Divide by H. Three assumed H: 2.3 (floor), 6.2 (sessions except the long one), 31.5 (all session spans).
- all 51, exec 6621: 2879 / 1068 / 210 lines per agent-hour.
- all 51, proof+spec 3511: 1527 / 566 / 111.
- clean 30, exec 3158: 1373 / 509 / 100.
- clean 30, proof+spec 1694: 737 / 273 / 54.
- Best single guess: none defensible. If forced, the 6.2 h row is the middle: about 500 clean exec and 270 clean proof lines per agent-hour, on hand-written models, with ~41% of items later found overstated/unsound.
- Not counted: rejected/negative files (32+14), which cost time too, so rates overstate real throughput.
