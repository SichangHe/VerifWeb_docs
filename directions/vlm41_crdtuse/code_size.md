# CRDT Rust sync modules: code size and shape

(authored by agents unless marked 🧑)

All repos shallow-cloned (`git clone --depth 1`) under `src/<name>`; nothing built or executed. LOC = tokei `code` lines (Rust only), `tokei -t=Rust -o json <paths>`. Unsafe = `grep -rEw --include='*.rs' unsafe <dir> | wc -l` (raw, includes comment/doc mentions where noted). Async = `grep -rEw async` / `grep -rE tokio`.
Paths below are relative to /hdd1/sichangheagent/vl_meeting_work/out/vlm41_crdtuse/src.

## Commits (HEAD at clone time)
- automerge 40063d626d1601eb69e484418ac7396ff85f8534 (2026-11-09)
- loro c55cebff9bde3d01d8eaf31541765e1fe8125980 (2026-11-10)
- yrs e0b476b0ce613453c70d0bb477b955808aa79a07 (2026-11-04), yrs crate 0.28.1
- diamond-types 89ae3a0ab8d941a2885e6ec89d094bc9ce9d2922 (2026-09-02), 2.0.0

## automerge (rust/automerge)
Sync is a clearly separated module: `automerge/rust/automerge/src/sync.rs` (2495 lines, but the inline `mod tests` starts at line 854, so about 1640 lines are tests), `sync/state.rs` (214), `sync/bloom.rs` (160), `sync/message_builder.rs` (118). Sync files total 1932 code LOC (includes inline tests). Protocol is based on arXiv 2012.00472 (bloom filters + heads), per the doc comment at the top of sync.rs.
- whole crate `automerge/rust/automerge/src`: 47941 code LOC, 170 files (with tests dir etc., `automerge/rust/automerge`: 61500). Sync is about 4% of src.
- core merge logic is elsewhere (op_set2, change_graph, columnar, storage); sync builds on change/clock/change_graph.
- unsafe: 1 grep hit in the crate src, 0 non-comment; 0 in sync files.
- async: none in sync. The 1 `async` hit in src is in `transaction/owned_transaction.rs` (a comment). No tokio.
- deps (`automerge/rust/automerge/Cargo.toml`): flate2, sha2, leb128, hexane (in-repo column encoding), itertools, rustc-hash, smol_str, serde, thiserror, tracing, rand, getrandom; optional wasm-bindgen, js-sys, web-sys.
- bindings in workspace (`automerge/rust/Cargo.toml`): automerge-wasm (JS/TS, with `automerge/javascript`), automerge-c (C FFI with cbindgen), automerge-cli.

## loro (crates/loro-internal)
No single sync module. `loro-internal/src/sync.rs` (194 lines) is NOT the protocol: it only wraps std/loom Mutex/RwLock/atomics. Loro has no sync-state/handshake type; peers exchange version vectors and export/import byte blobs (`export_from(vv)`, `import`). The sync-relevant files I picked (judgment call):
- `loro/crates/loro-internal/src/encoding.rs` (709), `encoding/` (7033 lines in dir: fast_snapshot 630, shallow_snapshot 1979, json_schema 1911, outdated_encode_reordered 649, value 1535, arena 277), `version.rs` (1452) + `version/frontiers.rs`, `oplog/pending_changes.rs` (1168, buffers changes whose deps are missing). Total for these: 9221 code LOC, 11 files. Import/export entry points also live in `loro.rs`, `oplog/change_store.rs`, and the public wrapper `loro/crates/loro/src/lib.rs`.
- `loro-internal/src`: 76300 code LOC, 133 files. All crates in `loro/crates` (incl. wasm, fuzz, generic-btree, kv-store, rle): 191184 code LOC, 471 files. Public `loro` crate src: 2227.
- core CRDT logic: `container/`, `state/`, `diff_calc/`, `handler/`, `oplog/loro_dag.rs`, generic-btree.
- unsafe: 19 in loro-internal/src (all non-comment), 0 in encoding/version files, 75 non-comment across all `loro/crates`.
- async/tokio: none in loro-internal or loro.
- deps (`loro-internal/Cargo.toml`): generic-btree, serde_columnar, postcard, leb128, xxhash-rust, im, parking_lot, thread_local, bytes, smallvec, rustc-hash, rand, md5, pest (jsonpath), append-only-bytes; optional wasm-bindgen, js-sys.
- bindings: `crates/loro-wasm` (JS/TS via WASM, npm package); README says "Rust, JS (via WASM), and Swift" (Swift binding not in this repo clone as a crate; not verified).

## yrs (yrs/yrs)
Sync protocol module: `yrs/yrs/src/sync/` = `protocol.rs` (705), `awareness.rs` (805), `time.rs` (32), `mod.rs` (14): 1218 code LOC, 4 files. protocol.rs defines the y-sync messages (sync step 1 = state vector, step 2 = update, update) via a `Protocol` trait.
- state vector / update encoding sit outside sync/: `state_vector.rs` (299), `update.rs` (1741), `id_set.rs` (1121, delete set), `updates/{encoder,decoder}.rs`, `encoding/`. Sync dir plus these: 7090 code LOC, 17 files.
- whole crate `yrs/yrs/src`: 32051 code LOC, 58 files. Sync dir is about 4%; with encoding about 22%.
- core: block.rs, block_store.rs, branch.rs, transaction.rs, types/, store.rs, doc.rs.
- unsafe: 72 raw / 69 non-comment in yrs/src; 2 in sync/state-vector/update files.
- async: yes. 13 `async` hits in `yrs/yrs/src/sync/protocol.rs` (`async fn start/handle/handle_message/handle_sync_step1/2`, `async_trait`) and 2 in `undo.rs` (`pub async fn undo/redo`). Runtime-agnostic: no tokio; uses `async-lock`.
- deps (`yrs/yrs/Cargo.toml`): thiserror, fastrand, smallstr, smallvec, async-lock, async-trait, arc-swap, serde, serde_json, dashmap.
- bindings in workspace (`yrs/Cargo.toml`): `ywasm` (JS via WASM), `yffi` (C FFI with cbindgen; used by other-language ports).

## diamond-types
No peer-to-peer protocol or sync state in the crate. It provides a causal graph, version summaries and serialisable ops; the application transports the bytes. Files I picked: `diamond-types/src/causalgraph/summary.rs`, `causalgraph/agent_assignment/remote_ids.rs` (local vs remote version ids), `causalgraph/storage.rs`, `src/encoding/` (11 files), `src/list/encoding/` (decode_oplog, encode_oplog, etc.). Total 4866 code LOC (comments 1511), 25 files. Plus `oplog_merge.rs`, `wal.rs`, `storage/` not counted.
- `diamond-types/src`: 20678 code LOC, 98 files; with `crates/`: 23775 code LOC, 121 files. Core merge: `listmerge/`, `listmerge2/`, `list/merge.rs`, `causalgraph/graph/`.
- unsafe: 20 raw / 13 non-comment in src, 3 non-comment in crates; 12 in encoding/causalgraph dirs (grep of raw count).
- async/tokio: none.
- deps (`diamond-types/Cargo.toml`): smartstring, str_indices, smallvec 2.0.0-alpha, rle (in-repo), bumpalo, jumprope, crc, num_enum, libc; optional lz4_flex, serde, serde_json, rand.
- bindings: `crates/dt-wasm` (JS/WASM), `crates/dt-swift` (swift-bridge), `crates/dt-cli`; `diamond-types/js/` is the TS side.

## Takeaways
- Only automerge and yrs have a dedicated sync module (about 1.2k to 1.9k code LOC, about 4% of the crate). Loro and diamond-types expose version vectors/summaries plus export/import encoding instead; the "sync" boundary there is encoding code (about 5k to 9k LOC).
- Only yrs has async in its sync code, and it is runtime-agnostic (async-trait, async-lock). None uses tokio.
- unsafe is rare in automerge (0 non-comment) and absent from loro encoding code; yrs has the most (about 69).
- Caveat: the loro and diamond-types file selections are my judgment; automerge's 1932 includes about 1640 lines of inline tests, so non-test sync is roughly 1.3k lines.
