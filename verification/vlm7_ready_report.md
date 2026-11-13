# vlm4 drafts: ready-to-file report
(authored by agents unless marked 🧑)

All 9 drafts in out/vlm4_drafts/ edited in place; nothing filed or contacted. Each repro was re-run once from the final text; none is fixed upstream.

- boa_arraybuffer_slice_resize: ready. Boa Matrix (SECURITY.md) or https://github.com/boa-dev/boa/issues. main 329e897 still panics
- boa_atomics_store_resize: ready. Same destinations. 329e897 still panics
- boa_at_overflow (+ 2 patches next to it): ready. Same destinations. 329e897 (rebuilt) still panics / wrong key. Left: "I can contribute a test262 test" sentence has no PR link; filer may keep or drop
- boa_event_loop_ordering (+ patch next to it): ready. Same destinations. 329e897 still reproduces. Patch tests not re-run
- boa_gc_finalizer_uaf: ready. Same destinations. 329e897 Miri still reports use-after-free. Left: "I can share the prototype" sentence; filer may keep or drop
- boa_typedarray_int_conversion: ready. Same destinations. 329e897 still prints -1 255 -1 65535
- cranelift_bitset_from_range: ready. https://github.com/bytecodealliance/wasmtime/security (SECURITY.md) or /issues. main 33b89be has a byte-identical scalar.rs; repro ran against crate 0.137.1, not a main build
- lightpanda_blockurls_websocket: ready. security@lightpanda.io (SECURITY.md says no public issue). Main 61378ec not built (no zig on this machine); repro ran on the latest nightly b8e234a; source of main still lacks the block check
- servo_blob_slice_overflow: ready. https://github.com/servo/servo/security/advisories/new (SECURITY.md) or /issues. Main moved to fde5631, buggy code unchanged; pins updated; repro is a standalone Rust model (Servo not built)
