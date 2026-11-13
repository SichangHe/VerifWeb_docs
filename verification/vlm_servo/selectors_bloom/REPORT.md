# selectors_bloom: Verus on Servo `selectors` CountingBloomFilter
(authored by agents unless marked 🧑)

Upstream: selectors 0.31.0 (crates.io), `src_upstream/selectors-0.31.0/bloom.rs`.
Result: PROVED (BloomStorageU8 / BloomFilter only). cssparser: not attempted.

Rerun: `timeout 300 /hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus /hdd1/sichangheagent/vl_meeting_work/out/vlm_servo/selectors_bloom/v2.rs`
-> `verification results:: 19 verified, 0 errors`. (`v1.rs` = first bounds-only step, 11 verified.)

## Properties proved (v2.rs)
1. No panic/overflow: `hash1`/`hash2` < 4096 (index in bounds); `adjust_slot` never overflows (0xff is skipped) and `-= 1` never underflows, given the remove precondition.
2. Functional: no false negatives. Ghost `items: Seq<u32>` = inserted-not-removed hashes. `wf`: for every slot i, `counters[i] == 255 || counters[i] == occ(items, i)`, where occ counts how many slot references (first and second) in items hit i. Proved `insert_hash` and `remove_hash` preserve `wf`, and `might_contain_hash` returns true for every member of `items`.
3. Saturation: a saturated counter stays 255 forever, so it can only cause false positives, never false negatives (covered by the `255 ||` disjunct).

Finding (fact, from proof): `remove_hash` has no check, so removing a hash that is not currently in the filter can hit `*slot -= 1` on 0 (panic in debug, wrap in release). Safety needs the caller's precondition `items.contains(hash)`. Negative check (`neg.rs`, precondition dropped) fails as expected: "precondition not satisfied ... requires s.contains(h)" (and the remove-index lemma).
Also handled: hash with both slots equal (a == b) - needs occ >= 2, from the strengthened `occ_member` lemma (`occ >= contrib`).

## Failed attempts (verbatim, trimmed)
v1 attempt 1, original constants `const KEY_MASK: u32 = (1 << KEY_SIZE) - 1;`:
```
error: possible arithmetic underflow/overflow
 --> v1.rs:6:23
6 | const KEY_MASK: u32 = (1 << KEY_SIZE) - 1;
error: postcondition not satisfied
10 | fn hash1(hash: u32) -> (r: u32) ensures r < 4096 {
12 |     hash & KEY_MASK   -- at the end of the function body
```
Told me: the const body is checked as exec code and Verus does not know the const's value (opaque), so the mask bound is not provable. Typed literals `(1u32 << 12u32) - 1u32` did not help (same two errors). Fix: `const KEY_MASK: u32 = 4095;` plus a proof fn showing `(1u32<<12u32)-1u32 == 4095u32` by bit_vector. Same for `ARRAY_SIZE = 4096`.

v2 attempt 1: 
```
error: to dereference a mutable reference parameter in a postcondition, disambiguate by wrapping it in either `old` or `final`
error: disallowed: field expression for an opaque datatype ... ensures self.items@.contains(hash) ==> r
```
Fixes: use `final(self)` in ensures (new mut-ref semantics in this Verus version); drop `pub` (private fields cannot appear in public specs); route through a spec helper.
After those and strengthening `occ_member`, v2 verified on the next run (19 verified).

## Changes to original code
- consts inlined as literals (above); `[u8; ARRAY_SIZE]` kept.
- Merged `CountingBloomFilter<S: BloomStorage>` + trait into the concrete `BloomStorageU8` case (trait with default methods and generic S not attempted; `BloomStorageBool` not ported).
- Dropped: `Debug`, `Default`/`Clone`, `clear`, `is_zeroed`, `#[cfg]`, tests, `#[inline]`.
- `first_slot_is_empty` etc. inlined into `insert_hash`/`remove_hash`/`might_contain_hash` (calls to `hash1`, `hash2`, `adjust_slot`, `slot_is_empty`). Bodies of `adjust_slot` (including `&mut self.counters[index]`) and `slot_is_empty` are verbatim.
- Added: ghost field `items`, `wf` spec, requires/ensures, proof blocks.

## Unsupported / friction
- `&mut self.counters[index]` on an array: supported, no change.
- Constants with shifts: need literal workaround.
- New `final(self)`/`old(self)` rules in postconditions.
- Not hit: trait/generic port was not tried, so unknown.

## Effort
About 25 min wall-clock, 6 verify runs (including 1 negative). Code ported ~45 lines; spec+proof ~100 lines (occ, 3 lemmas, wf, ghost updates).
Not done: cssparser tokenizer; the probabilistic false-positive claims in the doc comment (not verifiable in Verus as stated); `u32` hash assumed arbitrary (high 8 bits ignored, as upstream).
