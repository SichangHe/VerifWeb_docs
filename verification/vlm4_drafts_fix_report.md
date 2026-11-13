# fix_drafts2 report
(authored by agents unless marked 🧑)

Applied out/cx_maint review to all 5 drafts in out/vlm4_drafts/ in place (pre-edit copies: /tmp/{boa,gc,bs,sv,lp}_orig.md). Nothing filed, posted, or sent; nothing written in /ssd1/sichangheagent/email.

Lightpanda: the draft now inlines a self-contained repro.sh (srv.py copied from the cloud bundle, probe.html, nightly download + sha256, control and --block-urls runs, readiness checks, server logs). Re-ran it once from the draft text in a fresh dir: nightly sha256 e7ed89bd... (same build as the draft); control: fetch+ws succeed; --block-urls: fetch gets err=UrlBlocked and the server sees no GET /f, but the WS upgrade reaches the server and the page receives hello. Ports moved to 18101/18103 because a stale srv.py from another agent's run (rv_drafts/lightpanda, pid 1531654) holds 127.0.0.2:18003; I left it running. Title narrowed to --block-urls; CDP/adblock kept as earlier observations without a repro.

boa_gc: added the cx_boagcfix result framed as "possible approach (prototype, not a ready patch)": Miri passes, gc/engine tests pass, 3.54x GC slowdown, ephemeron-convergence risk. Also added the main-branch Miri repro and a grep of engine Finalize impls.

Not applied, or applied differently:
- boa 3: no corpus generator found; removed the 9,430-program claim (and the boa_cli note, item 8) instead of attaching it
- boa_gc 3: no recorded 0.22.0 Miri run found; removed that claim ("not tested")
- boa_gc 2: kept the hedge, added "not instrumented"; no instrumentation was run
- bitset 2: script not found; labeled "local check; script not included"
- bitset 3: did not add "happy to send a PR" (author intent unknown); added a test snippet (not compiled)
- servo 3: added the observable JS check; no HTML wrapper or Servo command, since Servo was not built
- servo 6: added a "neg" mode to the model; re-ran the model: neg/single/chain outputs match the draft
