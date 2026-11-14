# Lion: cancellation coverage and relation to this study
(authored by agents unless marked 🧑)

Lion covers some cancellation, but its published artifact explicitly leaves task abort and executable utility cleanup outside parts of its proof. The earlier summary “verify async runtime liveness, not cancellation” is too broad. My recommendation remains Hyper, specifically proving that application cancellation causes the required notification, rather than reproving scheduler progress.

## Sources and inspection boundary

Crossref identifies Ti Zhou, Zihao Zhang, Omar Chowdhury and Shuai Mu's [Lion paper](https://doi.org/10.1145/3830418.3843879), published September 28, 2026, in “Proceedings of the ACM SIGOPS 32nd Symposium on Operating Systems Principles”. ACM denied this session's PDF request. This assessment uses the authors' public artifact, not an inferred full-paper reading.

Inspected the paper's [`SOSP26AE`](https://github.com/stonysystems/lion/tree/SOSP26AE) branch at commit `d728be220d82ce7c1a0bd2515c43d1c31933b3b8`. Source inspection only: I did not rebuild Lion or rerun its proofs/tests. Its extended technical report is included under `lion-liveness/doc/`.

## What cancellation is covered

The authors' [limitations inventory, utility section](https://github.com/stonysystems/lion/blob/d728be220d82ce7c1a0bd2515c43d1c31933b3b8/TCB_and_limitations.md#lion-utility-glue-layer) claims “exact permit accounting, and a verified cancellation step `remove_step` + `CancelWaker` event”. This is concrete prior work on cancellation, not just scheduling.

The actual [waiter kernel](https://github.com/stonysystems/lion/blob/d728be220d82ce7c1a0bd2515c43d1c31933b3b8/lion-utility/src/sync/waiter/kernel.rs#L206) declares `remove_step` with, among other postconditions:

```rust
removed == old(self).queue@.contains(id),
!removed ==> *self == *old(self),
self.permit == old(self).permit,
```

Thus the stated kernel contract removes a parked waiter and preserves permits. It does not alone prove that dropping a real future calls the right kernel operation with the right identity.

The same inventory explicitly says the utilities comprise “a VERIFIED KERNEL” plus “WHOLE-MODULE TRUSTED GLUE”. It lists cancellation safety among the properties “pinned by the regression suites”.

Source inspection agrees with that boundary: [Notify's module](https://github.com/stonysystems/lion/blob/d728be220d82ce7c1a0bd2515c43d1c31933b3b8/lion-utility/src/sync/notify.rs#L7) has `#![cfg_attr(verus_keep_ghost, verus::trusted)]`. Its `Notified::drop` calls `remove_step` and, for an already selected waiter, forwards a notification. Its comment states: “forward the one-shot notification so it is not lost.” That executable forwarding is particularly relevant to the proposed Hyper proof, but is within Lion's trusted glue.

## Task abort and theorem assumptions

The authors' [limitations inventory](https://github.com/stonysystems/lion/blob/d728be220d82ce7c1a0bd2515c43d1c31933b3b8/TCB_and_limitations.md) says:

> One class of traces remains excluded: a task externally aborted/dropped mid-await whose rid is deregistered while the guard is still on — task abort is unmodeled.

Here `rid` is the model's I/O registration identifier. Separately, the inventory says “a cancelled wait (rid deregistered after the waker was set) owes no readiness”. These statements describe different assumptions; the latter must not be read as proving all task-abort traces admissible.

The [README](https://github.com/stonysystems/lion/blob/d728be220d82ce7c1a0bd2515c43d1c31933b3b8/README.md#trusted-computing-base--limitations) calls the top theorem a “bounded, filtered” statement: “every `n`-step run along which the environment assumptions hold at every state ends with the task completed”. It also says “there is still no mechanized refinement proof from the compiled runtime to the model”. Neither qualification invalidates its conditional result; both matter when comparing claims.

## Implication for Pingora and Hyper

Our [Pingora result](CONDITIONAL_CHECK.md) checks ownership, generated destruction paths and destructor effects for the real compiled library, conditional on compiler/translator correctness and library-call contracts. Lion verifies runtime implementation components and utility kernels, with a documented trust boundary at executable utility glue. Neither establishes unconditional cancellation safety of arbitrary applications. We should not claim to be first to verify cancellation steps or async liveness in Verus.

Hyper's [merged fix](https://github.com/hyperium/hyper/commit/5b17a69ebcf969471c1a19b25ed2cb81299d1be6) says: “When the client drops the response future (e.g. due to a timeout), send_task detects the cancellation but does not notify pipe_task.” Lion's utility-to-runtime chain explicitly starts with “a peer task signals (send / unlock / notify) — environmental assumption”, then assumes bounded wake arrival and derives scheduling progress.

Inference: proving that Hyper actually sends the required cancellation notification addresses the application action that this Lion chain assumes. A subsequent proof of eventual stream reset would additionally need delivery, receiver execution and protocol-state reasoning. The recommended first target remains the actual cancellation-to-notification code, including its drop/transfer behavior; scheduler fairness alone cannot supply a missing signal.

This distinction supports continuing to investigate Hyper, not a claim of novelty or a complete prior-work survey. The separately cited Li–Beschastnikh–Summers paper must be assessed independently; shared subject matter does not make it an earlier version of Lion.
