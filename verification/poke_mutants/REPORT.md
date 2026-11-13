# Real-bug mutation poke
(authored by agents unless marked 🧑)

Four selected bug/fix differences with identifiable source changes were represented by existing models; all four buggy model variants were rejected and their fixed controls passed: **4/4, 100% model kill rate**. This is a small, bug-aware selection, not a source-level mutation score. The useful new finding is a surviving Blob composition defect: an existing verified overflow repair still computes the wrong slice. Boa GC also exposes a missing connection between concrete reference counts and abstract roots.

## What was measured

A kill means the unchanged contract rejects the buggy modeled behavior while its fixed control passes. Syntax errors, solver timeouts, and merely proving a theorem that describes a bug do not count. Existing contracts and implementations were reused; the new Blob witness only calls existing functions, and the GC experiment changes one abstract marking expression. No engine was built. Available memory at checks was above 110 GiB, exceeding the required 60 GiB guard.

The four selected pairs, one count per bug rather than per failing obligation:

- **Cranelift bitset capacity endpoint: killed.** Existing `cx_bugs/bitset/bitset_from_range.rs` accepts the guarded-mask repair; `bitset_original_fails.rs` rejects `(one << lo) - one`. Fresh logs say “verification results:: 13 verified, 0 errors” and “error: possible bit shift underflow/overflow”. The draft [source evidence](../vlm4_drafts/cranelift_bitset_from_range.md) quotes the upstream contract: “Panics if `lo > hi` or if `hi > Self::capacity()`”. Thus `(64,64)` is permitted. This is a u64 specialization; the rejection itself comes from built-in arithmetic safety, not evidence that the functional postcondition is strong.
- **Boa timer/microtask ordering: killed.** The [actual proposed patch](../vlm4_drafts/boa_event_loop_ordering.patch) inserts `self.drain_promise_jobs(context)` before timers and after each timer. Existing `vlm3_boaloop/bundle/verus/event_loop{,_original}.rs` represents that scheduling difference. Fixed: “verification results:: 10 verified, 0 errors”. Original: “error: precondition not satisfied”, specifically `old(self).micro_empty()` at `q.run_timer()`. The abstraction omits cancellation, errors, async jobs, and interval-clock details; it does not validate every hunk of the patch.
- **V8 CVE-2020-6418: killed, bounded.** Exact upstream fix retrieved; its production addition is `result = kUnreliableReceiverMaps;  // JSCreate can have side-effect.` Existing Z3 model checks 7,380 operation sequences per variant, lengths 1–4. Output: “BUGGY (8.0, no JSCreate marking): maxlen=4 violations=396” and “FIXED (main): maxlen=4 violations=0”. That is one killed variant, not 396 mutants. [Provenance, original patch, logs, and rerun](cve/FINDINGS.md).
- **Wasmtime CVE-2023-26489: killed.** Exact upstream fix retrieved. Author Alex Crichton's explanation says: “the 32-bit computation should be truncated to 32-bits but when folded into the address mode computation it happens with 64-bit operands, meaning truncation doesn't happen.” Existing `vlm2_iso/sandbox_verus/wasm_mem.rs`, with and without `--cfg buggy`, represents that arithmetic difference. Fixed: “verification results:: 6 verified, 0 errors”. Buggy: “error: postcondition not satisfied” for both `m as int == wasm_ea(a, k, off)` and `m + n <= RESERVED`. Two deleted upstream lowering rules are represented by one model pair, not independently tested. The model reserves 10 GiB; the advisory describes default 6G protection. [Exact patch and caveat](cve/FINDINGS.md).

All Verus outputs above are in [logs](logs). No actual C++/Rust engine patch was mechanically applied to a verifier input. Therefore an upstream source-level kill rate is **unmeasured**, not 100%.

## The weak contracts

**Blob: arithmetic repair passes while slice composition remains wrong.** Existing [p7.rs](../vlm3_servo/servo_misc/p7.rs) states an exact saturated-sum contract for `flatten_start_fixed`, but no contract connects that sum to the intermediate slice's length. Its `to_abs_range` contract bounds both endpoints and fixes the start; it does not specify the exact end. `to_abs_blob_range` specifies only bounds. These are insufficient for full File API slicing semantics.

Fresh results:

- Original unchecked addition in `p7_fail_flatten.rs`: “error: possible arithmetic underflow/overflow”, at `parent_start + start`.
- Saturating candidate `p7.rs`: “verification results:: 5 verified, 0 errors”. This is only an overflow repair, not a correct slice repair.
- [blob_survivor.rs](blob_survivor.rs), a copy of `p7.rs` with one added caller, proves `flatten_start_fixed(2,-1)` followed by `to_abs_range(start,Some(8),10)` returns start **1**: “verification results:: 6 verified, 0 errors”. All existing function contracts and bodies are unchanged.

For a 10-byte root blob, `slice(2,8).slice(-1)` should start at **7**: the intermediate blob has length 6, so `-1` selects its final byte. The existing [confirmed draft](../vlm4_drafts/servo_blob_slice_overflow.md) explicitly records “range 1..8. The spec gives 7..8 (originalSize is the 6-byte intermediate slice).” This new witness demonstrates an accepted wrong composition; it is not a new defect discovery. The draft also cautions: “Saturating addition prevents these integer overflows but does not implement the required slice normalization.” Count this as a separate survivor check, not a complete buggy/fixed pair in the 4/4 score.

**Boa GC: the full fix is outside the proof connection.** Existing root-count proof verifies while explicitly proving `live_after_finalize(clones, moved) && !boa_pass2_rooted(indeg, clones, moved)`. Its 13 passing obligations characterize the bug; they do not assert collection safety. The marking proof accepts a supplied root set. The later resurrection safety proof assumes the correct post-finalizer roots rather than deriving them from the patched counts. Its report admits: “I did not model `ref_count`, `non_root_count`, `Gc::finalize` decrementing, or `DropGuard`.”

The later abstract safety contract does reject replacing post-finalizer roots by empty roots for the clone-child scenario: one additional abstract mutant killed, with fixed control passing. But concrete count maintenance, repeated finalization, and dead-handle accounting remain unmapped. This is a coverage gap, not a measured full-fix survivor or kill. [Exact edit, quotations, and logs](gc/README.md).

## Other attempted or excluded cases

The existing cross-phase JIT toy pair also rejects the unguarded fold: fixed “2 verified, 0 errors”; buggy “2 verified, 1 errors”. Its own [report](../vlm2_jit/t3_cross_phase/REPORT.md) says: “No upstream code was read; the model is my abstraction.” Its CVE-2021-4102 motivation does not establish an actual patch mapping, so it is excluded from the four source-grounded model pairs.

Lightpanda WebSocket blocking has a confirmed reproduction but its [draft](../vlm4_drafts/lightpanda_blockurls_websocket.md) offers only a “Suggested fix direction (opinion)”. No matching executable Verus/Z3 blocking contract was identified in the inspected artifacts. It is unscored. The remaining CVEs in TARGETS.md were not evaluated in this bite-sized poke. Typer scripts do not supply another confirmed historical fix pair here.

## Reproduce and interpret

From the workspace root, run `bash out/poke_mutants/run.sh`. It checks available memory before each Verus invocation, uses 90-second timeouts, saves full logs, and prints process statuses. Expected buggy cases exit 1. The nonfatal GLIBC weak-version warning occurs on passing runs too. Z3 and GC reruns are in their linked evidence notes.

The script runs existing pairs sequentially; `blob_survivor.rs` adds only a caller proving the concrete wrong start. This report is the design record for those two small additions. No upstream issue or external message was sent; no email directory was written.

My recommendation: pursue a small **held-out bug/fix corpus** and report both model coverage and kill rate. Freeze contracts before choosing the held-out bugs. The present 4/4 mostly confirms contracts written with those bugs already in mind. Blob shows why semantic survivor checks matter; GC shows why the source-to-model connection must be measured separately. A next experiment should target those two concrete gaps rather than enlarge the count with more toy mutations.
