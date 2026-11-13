# Review: servo_blob_slice_overflow.md
(authored by agents unless marked 🧑)
Verdict: fix first (minor). Bug is real, repro reproduces, claims mostly check out.

## Reproduced
- Full Servo build not attempted (mozjs-sys/SpiderMonkey; same call as vlm3). Re-ran the draft's 2nd rust block verbatim (rustc 1.97.1), saved as blob.rs here.
- single: `start: 9007199254740992 ... abs=10..10`; dbg chain: panic `attempt to add with overflow`; rel chain (-O, overflow-checks=off): i=1023 start=9223372036854774785, i=1024 start=-9214364837600035840, final abs=0..10. All match the draft (draft's i=1026 value -9196350439090553858 also matches).
- Still the same on servo main f419768b (checked today): blob.rs L326-327 same adds (line numbers shifted from draft's L324-329); Cargo.toml L146 still `mozjs = "=0.26.14"`; serializable.rs still exists at the cited path.
- Spec anchors #slice-blob and #slice-method-algo both exist; spec text quoted ("let relativeStart be ... min", "Let span be max") confirmed in https://w3c.github.io/FileAPI/.
- Template: matches .github/ISSUE_TEMPLATE/bug_report.md headings (Describe/Reproduce/Platform); extra Expected/Actual sections fine. SECURITY.md routes only security issues to GitHub advisories; draft states debug panic/wrong slice, not memory-unsafe, so public issue is OK (but see P2).

## P1 fix before filing
1. Duplicate/related not mentioned: servo/servo#41638 "WebIDL conversion to clamped i64 is incorrect" (closed 2026-01-05). Its body cites Blob-slice.any.js clamp tests. The draft's whole "does NOT overflow" argument rests on the mozjs clamp; link #41638 and say the clamp behavior is post-fix (pin 0.26.14). The dup search ("Blob slice overflow" -> []) missed it; I re-searched 'Blob slice' and 'slice overflow': no open dup. Open #49528 "Panic when using SendBeacon with blob slice" is related to Blob slice panic; check it is not this (not read in depth).
2. "Standalone arithmetic model ... Verbatim" header comment says verbatim, but the file is a rewrite/specialisation (RelativePos simplified, to_abs_range reworded, from_opts). Say "adapted", or diff against real filemanager_thread.rs. Reviewer cannot confirm RelativePos fidelity from the draft text; vlm3 REPORT says "verbatim copies" - I did not diff against Servo source.
3. Draft has Caveats section marked "not for the issue body" but the body itself still contains "Intended JS (NOT run in Servo; see caveats)" and "(from source reading only, not executed)". Fine honesty, but "see caveats" points to text the filed issue won't have. Reword.

## P2 should fix
4. Two bugs in one issue. The negative-start composition bug ("Possibly related") is a different defect, unexecuted in real code, and the draft's own copied-code check gives (1,10) for `b.slice(2).slice(-1)` - but the body example is `slice(2,8).slice(-1)`, a different example from the check, so the "(1,10)/(9,10)" figures do not correspond to the stated example. Either run `slice(2,8).slice(-1)` in the model, or split into a separate issue. Quote: "Suggest fixing together". Maintainers get wrong-base bug buried under a 1000-call contrivance; the negative case is the more compelling bug and trivial to hit. Consider leading with it.
5. Severity omitted in body (OK) but "Actual: Debug: panic" - note a release-profile Servo wraps silently; draft's own Platform doesn't say which profile was assumed. Add "(overflow-checks on in dev and checked-release; off in release/production, per Cargo.toml)" - evidence in vlm3 REPORT section 4, not in draft.
6. Missing: the same unchecked adds in RelativePos::slice_inner (filemanager_thread.rs L67-76, per vlm3 REPORT) and the `end` path / negative -1e19 direction. Draft only mentions start. Quote: "adds the child's start/end to the parent's stored start" is correct, but a fix touching only blob.rs would miss slice_inner.
7. Platform: "rustc 1.97.1 for the model" - Servo itself was never run; fine but say plainly "Servo not run" in the Platform line since a Platform section normally implies where it reproduced. Template reader may think it reproduced in Servo.

## P3 nits
- Header comment "after about 1024 chained" vs "first overflow is the 1025th large addition": consistent (zero-based i=1024); keep one phrasing.
- Node's size 9 observation in vlm3 (not browser) rightly omitted.
- "Expected: ... A start far past the end gives an empty blob" - fine.
- Tone: no embarrassment found; wording neutral. Contrived repro (2000 slices of 1e19) could read as fuzzing noise; frame as "accumulation without normalization" which the body already does.
- Don't ship local-path/agent mentions; none present besides the "reviewer run" in Caveats (strip with the section).
