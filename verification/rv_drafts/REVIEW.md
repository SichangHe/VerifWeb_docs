# Review of vlm4_drafts
(authored by agents unless marked 🧑)

overall: all 5 bugs real & reproduced from draft text; none are duplicates (fresh searches); all need text-only fixes before filing; none embarrassing
details per draft: <dir>/FINDINGS.md

boa_event_loop_ordering (boa_loop/) — fix first
- repro output matches draft table exactly (patched + unpatched, 329e8974 = still HEAD)
- new patch on 9,430 corpus: 0 fail (unpatched 4,171; node 22: 0) → results in boa_loop/conf/results/
- cancel_stop: returns `cancelled` on both builds → closes draft's open caveat
- fix: update the 2 stale caveats; inline cancel_stop source (boa_loop/cancel.rs) for placeholder; add or disclaim regression test; cite #4782 (closed not_planned), #4785, #4730; drop "Chromium" (not run) & "identical over 5 earlier runs"; note corpus uses queueMicrotask polyfill; remove DRAFT header
- not run: cargo test, test262, Verus/TLA

boa_gc_finalizer_uaf (boa_gc/) — fix first + channel decision
- Miri UAF reproduced on boa_gc 0.21.0 & 0.22.0 (main via cx_gc logs)
- channel: SECURITY.md: "If you find any potential vulnerability, join our Matrix space and contact anyone who is an admin." → human decides Matrix vs public (precedent: #5187 handled publicly; low real-world risk, needs custom Finalize)
- fix: Miri output shows `main.rs:17:101` but the deref is at line 24 → re-paste; remove internal jargon ("reports' inference", "reviewer experiment", unlinked Verus model); verify #5187 actually says finalizers resurrect objects; pre-empt "Trace contract covers this"; drop unused `cyc`/GcRefCell & -Zmiri-disable-isolation

cranelift_bitset_from_range (cranelift/) — fix first (minor)
- debug panic + release `bits=0xffff...` reproduced (u64); line 140 unchanged on main
- fix: only u64 re-run; other widths & "exhaustive" claim rest on prior logs → re-run or attribute, add the 1-line argument (lo==capacity is the only full-width shift); drop/shrink Verus sentence; compile the proposed fix; remove template boilerplate & DRAFT notes

lightpanda_blockurls_websocket (lightpanda/) — fix first (minor) + channel decision
- reproduced: --block-urls & --adblock-lists block fetch but not WebSocket; main 6c7ed668 still unpatched (source)
- channel: SECURITY.md: "Please **DO NOT** file a public issue, instead send your report privately to security@lightpanda.io." → draft already flags; human decides
- fix: strip local paths / evidence-trail / DRAFT header; note 127.0.0.2 needs Linux; state status on current main; CDP setBlockedURLs not re-run

servo_blob_slice_overflow (servo/) — fix first
- Servo not built (mozjs); standalone model reproduces debug panic + release wrap; adds still in main f419768b blob.rs L326-327
- fix: cite servo/servo#41638 (clamp issue the argument relies on); skim #49528; "Verbatim" model → "adapted"; dangling "see caveats"; negative-start bug unexecuted & example mismatched → run or split into own issue; mention slice_inner (filemanager_thread.rs L67-76) same adds; platform line must say Servo not run

note: out/cloud/p3, cloud/p5 do not exist; reviewers used cx_bugs
