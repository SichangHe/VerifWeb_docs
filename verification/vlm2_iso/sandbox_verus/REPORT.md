# Verus model of the V8 sandbox external-pointer table and a Wasm linear-memory bounds check
(authored by agents unless marked 🧑)

Labels: [F] fact (checked or quoted), [B] belief, [I] inference.

## Takeaways
- [F] Both models verify: `ept.rs` 16 verified, 0 errors; `wasm_mem.rs` correct version 6 verified, 0 errors.
- [F] The buggy 35-bit lowering is rejected: `5 verified, 1 errors` (two failed postconditions).
- [F] Search found no prior formal verification of V8's ExternalPointerTable (see below).
- [I] The model proves the V8 sandbox's claimed table property under assumptions the real system must also satisfy (tag antichain, table-only-trusted-writes). It does not touch V8's code.

## Prior work (searched online)
- [F] Search "formal verification V8 sandbox external pointer table verified" returned no proof of the V8 sandbox or EPT. Closest hits are about other systems: "Automated Formal Verification of a Software Fault Isolation System" (https://arxiv.org/pdf/2508.15898, LFI) and "Compiling sandboxes: Formally verified software fault isolation" (ESOP 2019, cited from https://arxiv.org/pdf/2401.16277). These are SFI, not pointer-table sandboxes. [B] absence of evidence from one search engine, not proof none exists.
- [F] V8's own trusted-pointer-table header states the design goal only as a comment, https://raw.githubusercontent.com/v8/v8/main/src/sandbox/trusted-pointer-table.h line 130: "trusted pointer (an index into the table) either results in an invalid pointer or a valid pointer to a valid (live) object of the expected type."
- [F] A recent bypass shows tags do not tie an entry to its owner: Chromium issue 531459121 (https://issues.chromium.org/issues/531459121), summarized by the search tool (I did not open the issue): overwrite one ArrayBuffer's `extension_` handle with another same-tag handle. Not covered by my model (see below).

## V8 design quoted (what the model follows)
Threat model, https://github.com/v8/v8/blob/main/src/sandbox/README.md:
- "The sandbox assumes that an attacker can arbitrarily and concurrently modify any memory inside the sandbox address space"
- "converting raw pointers either into offsets from the base of the sandbox or into indices into out-of-sandbox pointer tables"

Entry design, https://raw.githubusercontent.com/v8/v8/main/src/sandbox/external-pointer-table.h:
- "a single pointer-sized word containing the external pointer, the marking bit, and a type tag" (class comment, line ~29)
- `GetExternalPointer`: "If the specified tag doesn't match the actual tag of this entry, the resulting pointer will be invalid and cannot be dereferenced." (lines 47-48)
- Zapped entry: "Any access to a zapped entry will result in an invalid pointer that will crash upon dereference." (lines 72-73)
- The header's tag mechanism (tags "ORed into the unused top bits", "ANDed away" on load) comes from a WebFetch summarizer's rendering of the file's design comment, not a line I read verbatim; I did grep the header and confirmed the lines above. [B] on the OR/AND wording.

CVE-2023-26489 (a Wasmtime/Cranelift bug, not V8), https://github.com/advisories/GHSA-ff4p-7xrq-q5r8, via search summary: "address-mode computation mistakenly would calculate a 35-bit effective address instead of WebAssembly's defined 33-bit effective address"; trigger: "a WebAssembly address which is left-shifted by a constant amount from 1 to 3". I did not open the advisory page itself.

## Model 1: `ept.rs` (cage + one external-pointer table)
State = `cage: Map<u64,u8>` (attacker bytes) and `table: Seq<u64>` (entries outside the cage).
- Entry = `payload | (tag << 48)`; payload < 2^47. Load with expected tag x: `entry & !(x << 48)`; trap (None) if the top 16 bits of the result are non-zero (models "non-canonical, faults on dereference"), or the handle index is past the table end.
- Operations: `AttackerWrite{addr,val}` (any address, any byte, including handle words in the cage), plus trusted `TrustedSet`/`TrustedAlloc` which require a valid tag and payload.
- Invariant `inv`: every entry is `mk_entry(p,t)` with p < 2^47 and valid tag t. Proved preserved by every op (`step_preserves`), hence by any op sequence (`run_preserves`). `attacker_cannot_touch_table` is the frame fact.
- `main_theorem`: for any initial good state, any op sequence, any 32-bit handle (fully attacker-chosen), any valid expected tag x, a non-trapping `deref` returns r with `table[i] == mk_entry(r, x)` for some i and r < 2^47. That is: a valid payload of an entry whose tag is exactly x.
- Key assumption, stated as a definition: valid tags are 16 bits `i | ((255-i)<<8)` so no tag's bit set is a subset of another's (`tag_antichain`, proved with `by(bit_vector)`). Without it the no-explicit-compare AND trick is unsound: negative control `ept_badtags.rs` (tags = any u16) fails (`error: assertion failed` in `tag_antichain`, output in `badtags_out.txt`). [I] This is the property V8's real tag constants must have; I did not check V8's constants against it.

## Model 2: `wasm_mem.rs` (linear memory, guard-region scheme)
- Wasm semantics: `i32.shl a s` wraps to 32 bits, then effective address = x + static offset < 2^33. Instance owns RESERVED = 2^33 + 2^31 bytes (bytes past `mem_len` are guard pages: trap). Safety = machine offset m satisfies m + n <= RESERVED.
- `lower` (correct): truncates the product mod 2^32 before adding the offset. Ensures `m == wasm_ea` and `m + n <= RESERVED`. Verifies.
- `lower` under `--cfg buggy`: `(a as u64) * k + off` (zero-extend looked through, 64-bit shift inside the address mode, max about 2^35 + 2^32). Verbatim errors (`buggy_out.txt`):
```
error: postcondition not satisfied
  --> wasm_mem.rs:28:13
28 |     ensures m as int == wasm_ea(a, k, off), m + n <= RESERVED,
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ failed this postcondition
32 |     (prod + off as u64)                  // up to 2^35 + 2^32
error: postcondition not satisfied
28 |     ensures ... m + n <= RESERVED,
   |                                             ^^^^^^^^^^^^^^^^^ failed this postcondition
verification results:: 5 verified, 1 errors
```
- `checked`: explicit check `m + n <= mem_len` implies in-bounds of current memory.

## Rerun
```
V=/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus
cd /hdd1/sichangheagent/vl_meeting_work/out/vlm2_iso/sandbox_verus
$V ept.rs                       # 16 verified, 0 errors
$V wasm_mem.rs                  # 6 verified, 0 errors
$V wasm_mem.rs -- --cfg buggy   # 5 verified, 1 errors
$V ept_badtags.rs               # fails (negative control)
```
Each takes a few seconds (the first ept run was 5.4 s wall). A harmless `GLIBC_2.39 not found` line is printed by the verus launcher; verification still runs. Total Verus runs while developing: about 8 for ept (type errors with `<<` on `int`, trigger inference, `forall` not allowed inside `by(bit_vector)` so lemmas became `requires/ensures` fns), 3 for wasm_mem.

## NOT covered
- [F] Real V8 code. Everything is a hand-written abstract model; nothing is extracted from or linked to C++.
- Handle-to-index decoding is `handle >> 8`; the real shift, segmented/multi-segment table, freelist, evacuation entries, marking bit, GC and table compaction are not modeled. Free/zapped entries are only covered by "all entries are good".
- Same-tag confusion (the Chromium 531459121 class): the theorem says the result is some entry with tag x, not the entry that belongs to this object. The property "right object" is not stated.
- Concurrency: README says the attacker modifies memory "concurrently"; model is sequential, with handle read as one atomic value.
- Table bounds: real table is reserved virtual memory, not bounds-checked per access as in the model.
- Not modeled: code pointer table, trusted pointer table, sandboxed pointers (offset form), the sandbox-base + 32-bit-offset load, out-of-cage reads by the attacker, the final dereference of the returned pointer by trusted code (the model stops at "pointer is valid-by-construction").
- Wasm: only the shift+offset addressing path with constant k in {1,2,4,8}; no memory.grow, no 64-bit memories, no multiple memories, no SIMD alignment, no real x86 encoding. The reserve size 2^33 + 2^31 is my choice (the real guard size is a config option, [B]).
- The cage as `Map<u64,u8>` plays no role in the proof except as the thing the attacker writes; the model proves independence of table from it by construction (separate fields), which is the assumption, not a theorem about memory layout.

## Distance from real V8
- [I] Large. This states the invariant and shows the tag-AND scheme is sound if tags form an antichain and only trusted code writes the table. The hard part (that all V8 code obeys "table only written by trusted ops", that no raw pointer leaves the cage, and C++ semantics) is untouched. Next steps: check V8's real tag constants for the antichain property (finite, cheap with Verus or a script); add freelist/segments; state the same-tag object-ownership property and see what extra invariant it needs.
