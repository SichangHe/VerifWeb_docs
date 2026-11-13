# Yrs e0b476b: remote-bytes crash/divergence hunt

(authored by agents unless marked 🧑)

Paths are under yrs/src. Read-only review; nothing was built or run. "Fact" = read from code; "inference" = my reasoning about behaviour, untested.

## C1. Update::exclude -> find_index `unreachable!()` (panic, debug and release). Confidence: fact for code path, inference that no earlier check rejects it.
update.rs:135-155 (BlockSet::find_index, private copy used by split_at):
    while left <= right { ... mid = (left + right) / 2; }
    unreachable!()
Cause: Update::decode (update.rs:837-860) does `.entry(client).or_insert_with(VecDeque::new)` and then `clock` is read fresh per chunk, so one update may list the same client twice with clocks that are non-monotonic or have a gap. Nothing checks contiguity. exclude() (update.rs:~80-112) assumes the deque is sorted and gap-free.
Trigger (two messages, V1): (1) update giving client C one block at clock 0..30 so the store has C at clock 30. (2) update with clients_len=2, both entries client C: chunk1 clock 0, one GC len 1; chunk2 clock 50, one GC len 1. apply_update -> known_state = C[0,30) -> exclude: clock_start=0, clock_end=51, range [0,30): start>clock_start so split_at(30). find_index: last block 50..50, start!=30; mid=0; block0 0..0 -> left=1; mid=1; block1 start 50>30 -> right=0; loop exits -> unreachable!() -> abort under panic=abort.
Same function also has `right = mid - 1` (update.rs:150, mid=0 and start>clock): underflow, same class as the known block_store one; reachable with the same duplicate-client trick (first block clock > range.start is not needed to be 0).

## C2. Release-mode u32 wraparound in integrate, divergence/corruption. Confidence: inference.
update.rs:344,361: `let offset = (*local_clock as i32) - (id.clock as i32);` then `if offset < 0 { ... offset.abs() as u32 ...}`; and `*local_clock = (*local_clock).max(id.clock + len);`
`as i32` wraps for clocks >= 2^31. Example: client unseen (local 0), first block is an Item with named parent and no origins at clock 0x80000001: offset = 0x7FFFFFFF > 0, so no Skip is inserted for the hole, the block is integrated at a clock far past the store clock (store invariant "contiguous from 0" broken); store clock becomes huge, later state vectors/encode_diff/find_index misbehave. Clock 0x80000000 gives offset i32::MIN: `.abs()` overflows (debug panic; release ok). `id.clock + len` also overflows with clock near u32::MAX (debug panic; release wraps so local clock is not advanced: divergence).

## C3. Unchecked u32 additions on wire values (debug panic; release wrap = divergence). Confidence: fact for code, inference for release effects.
- update.rs:862: `clock += block.len();` (clock and len both attacker u32).
- id_set.rs:27-31 `Ok(clock..(clock + len))` (V1 and V2). Release: start>end ranges are kept (`IdRanges::from_raw` does no normalisation or sorting); apply_delete then silently ignores them (wire delete differs from what Yjs applies). Not a crash that I could find.
- updates/decoder.rs:307 `self.ds_curr_val += self.cursor.read_var::<u32>()?;` and :312-313 `read_var::<u32>()? + 1`, `ds_curr_val += diff` (V2 delete set).
- decoder.rs IntDiffOptRleDecoder: `read_var::<u32>()? + 2`, `((self.last as i32) + self.diff) as u32`; UIntOptRleDecoder: `read_var::<u32>()? + 2` and `self.last = (-s.value()) as u64` (negate of i64::MIN; likely the same root cause as the known varint negate, separate site); RleDecoder: `(self.cursor.read_var::<u32>()? as i32) + 1` (0x7FFFFFFF overflows; 0x80000000.. gives negative count that decrements until `count -= 1` overflows at i32::MIN, debug panic).
All V2-only except the first two. Release: wraps silently.

## C4. V2 StringDecoder::read_str underflow. Confidence: fact.
updates/decoder.rs:495-503 (read_str): `remaining -= c.len_utf16(); // but yjs provides them as utf-16`
Trigger: V2 string-length RLE value 1 (or any odd cut) where the next char is outside the BMP (len_utf16 = 2): usize 1-2 underflows. Debug: panic. Release: wraps to huge, loop never hits `remaining == 0`, so the entire rest of the string buffer is consumed into one string (wrong parent/key/content, shifted later reads: divergence, no crash). Used for parent names, parent_sub, keys, text content.

## C5. ItemContent::decode memory amplification (same class as the known try_reserve one, new sites). Confidence: fact.
block.rs:2033+: JSON `buf.try_reserve(remaining as usize)` with len up to 2^31-1 (negative i32 gives huge usize -> Err, fine); Any `values.try_reserve(len)` with len up to u32::MAX (len * size_of::<Any>). Under overcommit these succeed and may OOM; also BLOCK_ITEM_JSON loop `while remaining >= 0` reads len+1 strings (off-by-one: honest Yjs JSON content with len strings errors out at the extra read; not a crash).
Also Update::decode `blocks.try_reserve(blocks_len)` per chunk, repeated across duplicate client entries.

## Looked at, seems unreachable or benign
- block_store.rs find_index division `clock / end`: end==0 only if last block is (clock 0,len 1), then clock<=end forces clock==0==start and the fast path returns first. Update::find_index likewise (clock < clock_end of last block).
- write_blocks_from (store.rs:217-250) with peer state vector: clock in diff is always < local clock, and `.max(first block start)` guards the known underflow; `find_index(...).unwrap()` is safe for contiguous stores. Peer SV with larger clocks is skipped (`local_clock > remote_clock`). encode_diff in update.rs: `(remote_clock as i64 - ...).max(0)` is safe.
- sync/protocol.rs and awareness decode: only read_buf/read_var plus the known try_reserve; no new arithmetic. AwarenessUpdate json is not validated as JSON here (not a crash).
- apply_delete `unwrap_unchecked` after find_index: index comes from find_index so valid, except the known clock < first block start case.
- Update::decode `Block::Skip` len and GC len `read_len() as u32` truncation: len 0 is rejected, so no empty block.
