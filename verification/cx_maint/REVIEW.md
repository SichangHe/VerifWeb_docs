# Maintainer triage of vlm4 drafts
(authored by agents unless marked 🧑)

These are triage assessments, not maintainer decisions. Nothing was filed upstream, and no maintainer was contacted. Each linked file gives the reproduction evidence, the current-main evidence with verbatim quotes, and the concrete text changes in priority order.

- [boa_event_loop_ordering](boa.md): likely accepted. The ordering reproduces exactly on main 329e8974. Risk: maintainers may close it as won't-fix because the default executor is intentionally limited, so the draft should ask whether HTML parity is in scope. Not done: applying the patch (it passes `git apply --check`), re-running the 9,430-program corpus (the draft gives no generator), running `cancel_stop`.
- [boa_gc_finalizer_uaf](gc.md): likely accepted as a soundness bug. It reproduces under Miri on boa_gc 0.21.0 and on main 329e8974. Upstream's own doc says finalizers "can potentially resurrect dead nodes". Not done: 0.21.1, 0.22.0, duplicate search.
- [cranelift_bitset_from_range](bitset.md): likely accepted as a real, low-severity bug. The debug panic and the release full-set result reproduce on 0.137.1. `scalar.rs` on wasmtime main 9959c2c6 is identical to that release. Not re-run: the draft's claims about other widths and its fix.
- [servo_blob_slice_overflow](servo.md): likely accepted, pending a browser reproduction. The Rust model reproduces, and the current source (c69de3c5) has the same additions. The draft overstates model output as Servo behavior. Servo was not built.
- [lightpanda_blockurls_websocket](lightpanda.md): needs more info. The draft references `srv.py` but does not include it, so it cannot be reproduced. Current main (d4ad6b07) source supports the bypass: `WebSocket.connect` skips `isUrlBlocked`.
