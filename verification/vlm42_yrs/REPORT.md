# vlm42_yrs: can Verus prove things about Yrs sync code, and does it find bugs?
(authored by agents unless marked 🧑)

Short answer: yes for the wire-format leaves, and the attempt surfaced a likely remote crash. One malformed update can make a Yrs peer hit `unreachable!()` in update.rs. Verus showed the function involved, `find_index`, is correct only if a client's blocks have no gaps, and nothing in `Update::decode` enforces that. A faithful standalone copy of the logic panics on the trigger (fact). I did not run the real crate (task rules), so "real Yrs crashes" is an inference. Nothing was reported upstream.

Target: y-crdt, yrs/src, commit e0b476b (2026-11-04), shallow clone in src/y-crdt. Effort: about 2 hours of agent time, plus one read-only bug-hunting subagent (hunt.md).

## 1. Likely remote crash: duplicate client entries in one update (C1)
- Why it happens (fact, from code): `Update::decode` (update.rs:837-860) puts every client entry into `clients.entry(client)`. So one update can list the same client twice with clocks that leave a gap. Each entry is contiguous on its own, but nothing checks the two against each other. `apply_update` (transaction.rs:879-880) calls `exclude(known_state)`, then `split_at`, then `find_index` (update.rs:131-155). On a gap, the binary search empties its range and hits `unreachable!()`.
- Trigger (inference from the code, with a model run): the receiver already has client C up to clock 30. A peer sends a V1 update with clients_len=2, both entries for client C. Entry 1 is one GC block at clock 0, length 1. Entry 2 is one GC block at clock 50, length 1. `find_index(30)` finds no block covering clock 30, so it reaches `unreachable!()`.
- Evidence:
  - verus/findidx.rs: "7 verified, 0 errors", no assume. Verus proves `find_index` returns a block containing `clock` and never reaches `unreachable!()`, given this precondition: blocks are non-empty, each start <= end, consecutive blocks touch (next start = previous end + 1), and clock is between the first start and the last end.
  - verus/findidx_raw.rs: the same code with only "non-empty, start <= end" fails. Verus reports u32 overflow and possible division by zero in `(clock / end) * right`, overflow in `mid - 1`, and overflow in `(left + right) / 2`.
  - repro/exclude.rs copies the decode grouping, `known_state`, `exclude`, `split_at` and `find_index`, keeping their control flow, with a simplified block type. Run on the trigger, it prints "panicked at exclude.rs:21:9", which is the `unreachable!()`.
- Impact: I don't know for each product.
  - Fact: the workspace release profile sets `panic = 'abort'` (Cargo.toml), so the yffi and ywasm builds abort the process.
  - Inference: pycrdt (Jupyter) builds through pyo3, which turns a Rust panic into a Python exception. There it is likely a failed update rather than a dead server. Whether the document is left in a consistent state afterward, I don't know.
  - Whether Yjs (JavaScript) accepts or emits such updates: I don't know.
- Possible fix (opinion): reject a duplicate client entry in `Update::decode`, or merge entries and check contiguity.

## 2. Smaller findings
- `read_var_i64` and `i64::read_signed` (encoding/varint.rs) panic in debug builds on peer bytes. Fact: Verus flagged both (verus/i64_raw.rs), and repro/i64.rs confirms them with overflow checks on.
  - Input `80 FF FF FF FF FF FF FF FF FF 00` gives "attempt to shift left with overflow".
  - Input `C0 80 80 80 80 80 80 80 80 02` gives "attempt to negate with overflow".
  - Release builds don't panic. They silently return wrong values, e.g. Ok(-64) for the first input.
  - These decoders are reached through V2 update decoding (inference, per hunt.md).
- Memory amplification despite `try_reserve`. The code comments say `try_reserve` "turns an allocation bomb into a recoverable decode error". That holds only if the allocation fails.
  - Fact: this host uses Linux overcommit mode 0, and repro/reserve.rs shows `HashMap<u64,u32>::try_reserve(2^30)` succeeds with 2050 MiB resident (2^28: 513 MiB).
  - Inference: SyncStep1 is about 8 bytes on the wire. It can declare a state vector of 2^32-1 entries, which would make about 8 GiB resident and about 136 GiB virtual before decoding fails. Under a container memory limit that is an OOM kill, not an error.
  - The same pattern appears in awareness decode, `Update::decode` and `ItemContent` decode (hunt.md C5).
  - Possible fix (opinion): cap the count by the remaining bytes.
- From the subagent's read-only hunt (hunt.md, not checked by me beyond C1):
  - C2: `as i32` clock casts wrap for clocks >= 2^31. This can skip filling a gap and corrupt the store (inference).
  - C3: unchecked u32 additions on wire values. Debug builds panic; release builds wrap silently, so peers can end up with different documents.
  - C4: V2 `read_str` does `remaining -= len_utf16`, which underflows on odd UTF-16 cuts. Release swallows the rest of the string buffer, so peers can end up with different documents.

## 3. What was proved (verus/varint.rs: "31 verified, 0 errors", 0 assume, 0 external_body)
- No panic on any byte input for `Cursor::read_exact`, `read_u8`, `read_buf`, `read_var_u32` and `read_var_u64`, from any valid cursor position.
- `write_var_u64` appends exactly enc(v), the canonical LEB128 spec.
- `read_var_u64` returns v and consumes exactly enc(v) whenever the bytes start with enc(v).
- Together: decode(encode(v)) == v, checked through the exec code (`roundtrip_u64`).
- `find_index` correctness under the gap-free precondition (section 1).

Changes to the copied code, and why
1. Read/Write traits replaced by a concrete Cursor and Vec<u8>, and the generic `T: VarInt` dispatch removed: Verus handles trait-generic code poorly.
2. `wrapping_shl(x, n)` replaced by `x << (n & 63)` (`& 31` for u32): Verus doesn't support it; same semantics.
3. `loop` restructured with invariants. In `read_var_u64`, the non-canonical 11th-byte case moved into a helper with the same behavior.
4. `read_exact`'s `next + len > buf.len()` rewritten as `len > buf.len() - next`: Verus flags possible usize overflow in the original. Not reachable today: callers pass at most u32::MAX on 64-bit.
5. Error payloads dropped. `VecDeque<Block>` replaced by `Vec<(start, end)>` in findidx.rs.

## 4. What I did not do, and blockers
- Not done:
  - u32 varint round trip.
  - StateVector encode/decode round trip: it should compose from the varint lemmas. Note the writer encodes the length as a usize and the reader reads it as u32, which is fine below 2^32 clients.
  - "diff(sv) contains exactly the missing updates" (`write_blocks_from`, store.rs:217).
- Blockers seen:
  - Trait generics (Encoder/Decoder, VarInt) had to be replaced by concrete types.
  - The diff property needs a spec of the block store: per-client gap-free block lists, skips, pending updates. The code never states it, and Block is a large enum with unsafe pointer-based integration (block_store.rs uses `unsafe { &*... .get() }`).
  - No async in this code path. The sync protocol module is plain decode/encode.
- Estimate (my guess, low confidence):
  - StateVector round trip and no-panic for all of sync/protocol.rs decode: about half an agent-day.
  - "Decoded updates satisfy the store invariant" (the property whose absence causes C1), over V1 decode: 1-3 agent-days.
  - diff correctness against an abstract block-store model: about 1 person-week.
  - Convergence of the integration algorithm (YATA ordering) on the real code: months. The unsafe pointer graph in block.rs/block_store.rs is the main obstacle.

## Rerun
- Verus:
  - V=/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus
  - timeout 900 $V verus/varint.rs
  - $V verus/findidx.rs
  - $V verus/findidx_raw.rs (expected to fail)
  - $V verus/i64_raw.rs (expected to fail)
  - z3 per out/vlm_servo/SUMMARY.md
- Repro (own files only):
  - rustc -O repro/exclude.rs -o /tmp/ex && /tmp/ex
  - rustc -O -C overflow-checks=on repro/i64.rs -o /tmp/i && /tmp/i shift
