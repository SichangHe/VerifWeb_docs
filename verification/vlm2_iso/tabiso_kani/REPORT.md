# Kani check of the two-realm heap model (tabiso)
(authored by agents unless marked 🧑)

Labels: [F] fact observed in the logs here, [B] belief, [I] inference.
Status: runs finished except where marked INCOMPLETE. Per owner rule, no further runs were started after the stop message.

## What was done
- [F] `src/main.rs` starts with a verbatim copy of the original model (`../../vlm_runtime/tabiso/model/src/main.rs`, lines 1-49 identical; the original's trailing `run`/`main` lines were cut). The original was not modified.
- [F] Appended: (1) `mod bm`, a fixed-size port of the same model (Vec -> arrays, field/root lists -> bitmasks, M = bound); (2) `diff_test`, a cargo test comparing `bm` with the Vec model on 2x20000 random 16-step runs, passed; (3) Kani harnesses `proofs::okN` (barrier on) and `proofs::badN` (barrier off).
- [F] Each harness runs exactly N nondeterministic steps. Each step picks one of alloc / store / share / import with nondeterministic realm and in-range object operands, and asserts the invariant afterwards. N is also the object capacity.
- Tool: Kani 0.68.0, CBMC 6.11.0.

## Results [F]
Barrier on (`okN`): VERIFICATION SUCCESSFUL. Barrier off (`badN`): VERIFICATION FAILED, "assertion failed: h.inv()", line 131 (the invariant assert). Kani verification time:

    N    ok (s)     bad (s)
    3      6.0        5.7
    4     18.4       17.6
    5     38.6       37.8
    6     78.9       52.0
    8    176.3      170.0
    10   260.3      172.3
    12  1354.5      471.1

- Bound reached with the barrier: [F] all op sequences of length 12 over at most 12 objects. [I] Counterexamples exist already at N=3, so the bug needs only a short sequence.
- Runtime vs bound: [F] about 6 s at N=3 and 1354 s at N=12, so roughly 225x. It is not monotone (ok10 > bad10) and is single-run, so [I] treat it as superlinear, roughly exponential, not fitted.
- Counterexample trace: [F] Kani reports FAILED; the trace is in `logs/badN.log`. [B] I did not read the trace to name the concrete op sequence.

## Vec-model harnesses (original data structure, not the port)
- `vec_bad2`: [F] FAILED (invariant violated), 317 s.
- `vec_ok2`: INCOMPLETE. Killed by the 1500 s timeout, no verdict.
- `vec_ok3`: INCOMPLETE. "CBMC failed with status 15" after 8 s. I suspect my own cleanup `kill` hit it [B]; this is not a verdict on the model.
- `vec_bad3`: INCOMPLETE. Timed out at 1500 s.
- [I] Kani with real `Vec` is far slower than the bitmask port; only the port was pushed to larger bounds. The proofs on the port transfer to the original only through `diff_test` (random testing, not a proof of equivalence).

## Rerun
    cd /hdd1/sichangheagent/vl_meeting_work/out/vlm2_iso/tabiso_kani
    PATH=$HOME/.cargo/bin:$PATH cargo test --release        # diff test
    ./run.sh "ok3 bad3 ok4 bad4 ok5 bad5 ok6 bad6 ok8 bad8 ok10 bad10 ok12 bad12"   # T=1500 s per harness
Verbatim per-harness output: `logs/*.log`; wall times: `run.out` (wall is slightly more than Kani's "Verification Time" because of compile time).

## What this does NOT cover
- [F] Only sequences of at most N=12 steps and at most 12 objects, not all lengths. This is bounded model checking, not an unbounded proof. For small bounds it says nothing about heaps larger than 12 objects.
- Two realms only; the realm count is fixed.
- The proof is on the bitmask port (set semantics), not directly on the Vec model, except for the small unfinished Vec runs. Duplicate field entries are assumed irrelevant [I].
- It is the model, not any real engine, GC, JIT, or DOM. Only the three barrier rules are checked: no cross-realm store, share only deep-immutable objects, import only Shared or own objects.
- No side channels (Spectre), no moving GC, no object deletion, no concurrency.
- Invariant is checked after every step, so it is an inductive-in-bound check, not a stated invariant proof (no loop-invariant or Verus proof).
- Earlier attempts (Vec model with unwind 8) were abandoned: they ran minutes without a verdict, so Kani first ran with wrong harness selection and was restarted.
