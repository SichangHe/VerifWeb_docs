# Boa maintainer triage
(authored by agents unless marked 🧑)

Judgment: likely accepted as a real bug/spec-conformance issue, with some risk of "won't-fix / limited default executor" or a request to redirect to a PR. The ordering reproduces exactly as stated; the draft's own hedge about `SimpleJobExecutor` being "pretty limited" is the main uncertainty. This is my triage assessment, not a maintainer decision.

Reviewed [the draft](../vlm4_drafts/boa_event_loop_ordering.md) and its patch without changing them. Fresh work directory: [boa/](boa/). Upstream `main` resolved (`git ls-remote`) to `329e89748ed34e218fe593b4209b1dbe1d6eb64d` on 2026-11-04, equal to the draft's commit; clone retained in `boa/upstream`.

## Execution evidence

- Copied the draft's `order_repro.rs` unchanged (diff against the draft's code block: identical) into `examples/src/bin/` and ran `cargo run --release -p boa_examples --bin order_repro` with rustc 1.97.1. Build needs no extra steps ([log](boa/ordering.log)). Output: `T0 P1 | P0 T1 P2 | T0 T2 P1 | T0 M1`, i.e. exactly the draft's "Boa actual" column.
- The draft's patch passes `git apply --check` on this commit. I did not apply it, re-run the 9,430-program corpus (generator not provided), or run `cancel_stop`.
- Not verified against Node here; the expected column rests on the HTML spec and the draft's Node claim.

## Current upstream evidence

- [Timers header](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/wintertc/src/timers/mod.rs#L3): "Spec: <https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html#timers>". The draft says L1-3; correct.
- [`SimpleJobExecutor` docs](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/job.rs#L863-L866): "This is the default job executor for the [`Context`], but it is mostly pretty limited for a custom event loop." The phrase is at L865 (draft says L863-866; the sentence spans L864-865). This supports a "by design" reply but does not claim spec conformance either way.
- [`run_jobs_async` loop](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/job.rs#L955-L985): "Dispatch all past-due timeout jobs before the termination check." Past-due jobs are collected and run back to back with no promise drain; confirms the draft's cause.
- Related items (GitHub API, 2026-11-04): #4782 "timeout jobs scheduled for `now` can be skipped" closed `not_planned`; #4785 "Fix due-now timeout jobs in executor and CLI" closed (completed); #4730 closed, `merged: false` (the draft's "PR, not merged" is correct). Those are about dropped timers, not ordering; the draft's reading is right.
- [Bug template](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/.github/ISSUE_TEMPLATE/bug_report.md): sections "Describe the bug", "To Reproduce", then expected behavior/environment; the draft follows it. `SECURITY.md` L14 quote matches.

## Concrete draft changes, in priority order

1. Original: "so maintainers may consider it intended; I do not know." Make this an explicit question to maintainers: "Is ordering parity with HTML in scope for the default `SimpleJobExecutor`, or only for custom executors? If the latter, I'd suggest documenting the difference." This turns the main won't-fix risk into a decision request.
2. Original: the opening paragraph's "all microtasks run to completion after each task, before the next timer task" is stated as the whole story. Add the exact spec step link ("perform a microtask checkpoint") with URL; currently only the timers URL is cited.
3. Original: "The generator is not included; it can be shared." A maintainer cannot verify 4,171/9,430. Attach the generator or reduce the claim to the four programs. The corpus sentence is the weakest-sourced claim.
4. Original: "(`job.rs` L863-866)". Quote the sentence and point to L865 with a permalink; add permalinks for `run_jobs_async` (L955-L985).
5. Original: "#4730 (...; PR, not merged)". Correct as written; add "closed" for precision.
6. Original: "Proposed patch (attached ...)". Maintainers usually want a PR, not an attachment; say "I can open a PR with the test if the direction is acceptable" (the draft already says this about the test; move it before the patch-limits bullet and shorten the bullet list).
7. Original: the `cancel_stop` section. It shows no difference between patched and unpatched; say once that it is a regression guard, not a bug, to avoid reading as a second problem.
8. Original: `boa_cli` note "9 of 9,430, timing dependent; not analyzed". Drop or file separately; it is unreproducible from the text.
