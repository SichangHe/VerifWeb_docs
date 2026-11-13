# Review: boa_gc_finalizer_uaf.md
(authored by agent)

Verdict: fix first (small edits). Technical claim is correct and reproduces.

## Re-run (fact, my own copy in r/, r2/)
- draft repro copied verbatim, `boa_gc =0.21.0`, nightly Miri: UB "dangling reference (use-after-free)", frames gc.rs:316 / gc.rs:363 as claimed
  - with and without `MIRIFLAGS=-Zmiri-disable-isolation`: same; flag is unnecessary, drop it
  - `=0.22.0`: same error, same frames
  - native `cargo run`: prints `child.v=0xc0ffee` as claimed
- `cyc` field (and `GcRefCell` import) is unused: removing it (r2/) still UAFs. Remove from the repro (minimal, less to question)
- main @329e8974 still current head of boa-dev/boa (gh api); not re-built by me, relied on cx_gc logs (9/9 UB) and REVIEW.md

## Fix first
1. Report channel (SECURITY.md). Quote: "If you find any potential vulnerability, join our [Matrix](https://matrix.to/#/#boa:matrix.org) space and contact anyone who is an admin."
   - no GitHub private advisory flow in SECURITY.md; repo has published GHSAs (e.g. GHSA-f67q-wr6w-23jq), so a GHSA is possible but not what the policy says
   - draft is a safe-Rust UAF = memory-safety unsoundness in a public crate: policy arguably applies, draft says nothing about it
   - however: #5187 (a GC memory-safety "ACE" report) was filed publicly and closed; maintainers treat boa_gc hardening as public. Practical risk low (needs a custom `Finalize` impl; engine likely unaffected)
   - human decides: either Matrix ping to an admin first, or public issue. Draft header should state which and why. Also it says nothing of this now
2. Template mismatch. `bug_report.md` fields: Describe the bug / To Reproduce / Expected behavior / Build environment (OS, Version, Target triple, Rustc) / Additional context. Draft follows them but:
   - Build env lacks the "Version" line's OS version meaning (gives kernel, fine) ok; no issue
   - "Expected behavior" template asks "what you expected, and what is happening instead": draft has actual output under To Reproduce, acceptable
   - draft header says "type: Bug" fine (template sets it). Remove the "DRAFT (not filed)" line before filing
3. Mechanism section is hedged correctly but still stated in the issue body as source "facts" for a maintainer audience while the key step is inference. Draft: "the causal chain is the reports' inference, symptom confirmed by Miri". "the reports'" is internal jargon: maintainers don't know "the reports". Rephrase: "causal chain is my analysis; the symptom is confirmed by Miri"
4. Internal/embarrassing references to remove:
   - "Confirmed ... Also confirmed by a second independent repro with 3 variants (move-self, clone-self, clone-child)": variants are not shown in the issue; unreproducible by reader. Either include or drop
   - "(reviewer experiment)": means nothing to maintainers; say "I also tried"
   - "A Verus model of the set-level rule verifies, but does not prove a boa patch.": noise, no artifact linked; drop or link. cx_gc REVIEW #4: model proves a set-level rule only, not the count-based implementation. Keep it out
   - "the author inferred probably not": who is "the author"? first-person it
5. Repro line numbers: draft Miri output shows `at src/main.rs:17:101` but the printed repro has the deref at line 24 (my run: `src/main.rs:24:35`). Draft output was pasted from a different file than the code shown. Re-paste output from the exact code in the issue. Also my run's top frame is non_null.rs:454 (std); draft lists gc.rs:316 as frame 1, which is fine if elided, but note "1:" numbering does not match real backtrace (0 is NonNull::as_ref)
6. Repro uses unused `cyc`; remove (see above)

## Duplicates (re-searched with gh search, boa-dev/boa issues+PRs)
- queries: "finalize use-after-free", "finalizer gc dangling", "resurrect", "boa_gc unsound", "non_root_count", "dec_ref_count", "dangling Gc", "miri gc": no matching report. Only #5567 (open roadmap), #5187 (closed, unrelated ACE/drop_fn), #4410 "`Finalize` not called" (closed), #5337 (MapLock finalizer panic, closed). None is a duplicate
- gh search is keyword-weak on issue bodies; absence-of-evidence still. Draft says so: fine
- #5187: draft says it "mentions finalizers can resurrect objects". Search hit shows title is about drop_fn/ACE; I did not read body; verify the quote/claim is accurate before filing (cx_gc REVIEW did not cover #5187)

## Other checks
- "No `unsafe` is needed in user code": true for user text; `#[derive(Trace)]` expands to `unsafe impl Trace`. Maintainers may say Trace's unsafe contract ("An incorrect implementation of the trait can result in ... use-after-free") covers it, but `Finalize` is a safe trait with no documented restriction, so the unsoundness claim stands. Preempt: note `Finalize` is safe and undocumented about escaping handles
- "Same class as rust-gc issue #124": cx_gc quote-checked ok
- Impact paragraph is appropriately hedged (engine untested). Good
- "Possible direction (untested)": fine, labeled
- versions: latest release tag is v0.22; 0.21.1 exists but not tested (crate boa_gc 0.21.1 may exist; only 0.21.0 tested). Minor
- cx_gc REVIEW issue 1 (F1 "only reach through dead box" overstated) does not appear in this draft. Good

## Ranked to-do
1. Decide channel per SECURITY.md (Matrix admin vs public); add one line to header
2. Re-paste Miri output from the exact final code; drop unused `cyc`; drop disable-isolation flag
3. Remove internal jargon ("the reports'", "reviewer experiment", "the author", Verus line, unshown "second repro")
4. Verify #5187 claim by reading it
