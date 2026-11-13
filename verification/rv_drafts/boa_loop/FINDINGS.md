# Review: boa_event_loop_ordering (draft .md + .patch)
(authored by agents unless marked 🧑)
Reviewer: independent agent, 2026-11-04. Work dir: this dir. Drafts not edited.

Verdict: fix first (small text edits only; technically sound).

## What I re-ran (own copies, pinned commit 329e8974, rustc 1.97.1, release build)
- patch applies cleanly (`patch -p1`) to a fresh `git archive` of the commit; built from draft text only
- repro (code block copied verbatim from the .md): unpatched `T0 P1 | P0 T1 P2 | T0 T2 P1 | T0 M1`, patched `P1 T0 | P0 P2 T1 | T0 P1 T2 | M1 T0`. Matches the draft's table exactly.
- 9,430-program corpus (`conf/run.py 4 4 boa-simple boa-simple-fixed node22`, paths repointed to my builds, results in `conf/results/`):
  - boa-simple (unpatched) fail(es2019) 4171
  - boa-simple-fixed (NEW patch) fail(es2019) 0
  - node22 fail(es2019) 0 (es2017 counts 2934 for both patched and node, i.e. identical)
  - so the new patch also passes the whole corpus; draft says it was not run.
- cancel_stop (`cancel.rs`, token set after 20 ms, release build): patched prints `cancelled`, exit 0. UNPATCHED also prints `cancelled`, exit 0. This closes the draft's "Not verified on the unpatched commit" gap (the build did complete for me, 2m51s).
- not run: cargo test (engine job / wintertc), test262, Verus/TLA. I did not re-verify the draft's "2 passed / 54 passed" figures.

## Claims checked against evidence
- source quotes and line refs OK: `timers/mod.rs` L1-3 cites the HTML timers spec; `job.rs` L863-866 "mostly pretty limited"; `mem::take(&mut *self.promise_jobs...)` snapshot is real.
- commit is current upstream HEAD of boa-dev/boa (checked via API 2026-11-04); `job.rs` last changed 2026-05-01. No staleness.
- Node v22.21.1 confirmed locally.
- Template: `.github/ISSUE_TEMPLATE/bug_report.md` sections (Describe the bug / To Reproduce / Expected behavior / Build environment / Additional context) all present, in order. Template is `type: "Bug"`; fine. SECURITY.md covers vulnerabilities only; this is not one, so a public issue is right.
- CONTRIBUTING.md and PR template: no AI-disclosure rule found by grep (AI/LLM/generated/copilot/claude).

## Findings, prioritized

1. Medium, stale/now-wrong caveats (fix by updating, they undersell the patch):
   - "The corpus was not re-run against the final patch." -> it was (0/9430 fail). Update with my result (and say who ran it).
   - "Not verified on the unpatched commit that `cancel_stop` returns (the original-library build timed out in review)" -> verified, returns. Update.

2. Medium, placeholder left in body: "`cancel_stop` source: (attach `examples/src/bin/cancel_stop.rs`: ...)". Either inline the 12-line source (`../cancel.rs`) or delete the parenthetical; as written the reader gets neither.

3. Medium, maintainers will ask for a regression test and the patch has none. Add a unit test in `job.rs` (promise-then vs setTimeout ordering, plus the cancel case) or say plainly that tests are omitted. Also say test262 not run (it does) but note `boa_tester` uses SimpleJobExecutor, so test262 is the relevant gate for this patch.

4. Low, prior-art omission. Search again (GitHub API, repo boa-dev/boa, microtask / setTimeout / event loop / SimpleJobExecutor / checkpoint): no duplicate of this ordering report. But the draft's cited "#4782" was closed `not_planned` (maintainers declined a SimpleJobExecutor timer fix); also relevant and uncited: #4730 (due-now timeout dropped, PR, not merged), #4785 (merged, "Fix due-now timeout jobs in executor and CLI"), #4926. Cite #4782's not_planned status and #4785 so the maintainers do not think you missed them; helps judge "may consider it intended".

5. Low, wording that could mislead:
   - "In HTML (and Node >= 11, Chromium)": Chromium was never run in this round (earlier review: "Unverifiable here: ... Chromium was not rerun"). Drop Chromium or cite the spec only.
   - "(confirmed by independent rerun)" and "It was identical over 5 earlier runs": the 5 earlier runs are not reproducible from artifacts; keep only the same-day runs.
   - Corpus uses a `queueMicrotask` polyfill (`to_js(p, polyfill_qm=True)`), not the native one; the draft implies native. Mention it, or note program 4 covers native.
   - "<= 4 grammar nodes" is right; avoid anyone reading it as "4 callbacks" (the cx_loop review flagged that error in the cloud report; not repeated here, good).
   - Title says it "differs from HTML event-loop ordering"; body hedges well ("I do not know" on intent). Keep.

6. Low, scope/embarrassment risk:
   - CLI note "9 of 9,430 ... nondeterministic; I did not analyze" invites "then why mention it". Either drop it or put a ready repro. Currently harmless but unactionable.
   - Draft is long for the template; the Additional-context bullet on the patch is one very dense paragraph. Split "Limits" and "Test results" lines.
   - Header "# DRAFT, NOT FILED. Template: ..." must be removed before filing; the "Final-patch results" paragraph is test-log style, trim.

7. Patch review (diff small, logic OK):
   - cancel path correct: drain returns Ok on stop, timer loop `break`s, `continue` returns to top where `stop` is cleared and queues cleared. Timers already popped from `clock_jobs` into `jobs_to_run` are dropped on cancel (acceptable, since `clear()` runs anyway).
   - Interval arm reorders reschedule before the drain; fine, and untested (draft says so).
   - Unrelated reformatting of the Interval arm inflates the diff; minor.
   - `Ordering::Relaxed` read per job is consistent with existing code.
   - Doc comment calls it "like the HTML 'perform a microtask checkpoint'" while the limits list says it is not complete; soften to "similar to".

## Not found wrong
No fabricated numbers: 4,171 / 9,430 / traces / env block / line refs all reproduced or verified.
