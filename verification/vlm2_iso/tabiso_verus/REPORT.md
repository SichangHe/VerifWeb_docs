# tabiso_verus: Verus proof of the two-realm heap isolation invariant
(authored by agents unless marked 🧑)

Labels: [F] fact observed here, [B] belief, [I] inference.

## Result
- [F] `heap.rs` verifies: `verification results:: 24 verified, 0 errors` (wall 2.9 s).
- [F] Ops proved to preserve the inductive invariant `inv()` for any heap size and any op sequence: `alloc`, `store` (write barrier), `share` (deep-immutable check), `import` (Shared-or-own check), and stretch `free` (per-realm GC of one object). `Heap::new()` establishes `inv()`. Because every op `requires inv()` and `ensures inv()`, any sequence of calls is covered by induction.
- [F] `proof fn isolation(h, r)` (requires `inv()`) proves both: every object reachable from realm r's roots is r-owned or Shared; every reachable Shared object's fields are Shared. Reachability is an explicit path from a root (`is_path`/`reaches`), so the theorem is not hidden inside the invariant.
- [F] `inv()` is local (no reachability): (a) all field/root indices in bounds; (b) a root of realm r points to an r-owned or Shared object; (c) a Realm(x) object's fields are x-owned or Shared, a Shared object's fields are Shared. `path_ok` proves by induction on path length that this implies the theorem.

## Model differences from `model/src/main.rs`
- [F] Heap is `Vec<Obj>`, roots a `Vec<(realm, idx)>` (not two fixed vectors); realm id is any `u8`, so it covers 2 realms and more.
- [F] Added `Own::Free` for the GC stretch. `store`/`share` also reject Free objects (the Rust model has no Free).
- [F] Rust `store` allowed `dst` Shared from Realm(a) src; so does this one. Same barrier otherwise.
- [F] `free(r, o)`: allowed only if o is Realm(r)-owned and no root and no non-Free object has a field equal to o (two loops scan the heap); then o becomes Free. Invariant (b)/(c) force reachable objects to be non-Free, so freeing an unreferenced object cannot break isolation.

## Rejecting the no-barrier version
Both files are `heap.rs` with the barrier checks deleted from `store`, `share`, `import` (and `free` dropped).
- `nobarrier.rs` keeps the lemma calls; Verus rejects at the barrier preconditions (3 errors; full log `nobarrier_error.txt`). Verbatim (store):
```
error: precondition not satisfied
   --> nobarrier.rs:287:17
135 |         h.own_of(src as int) != Own::Shared, h.own_of(src as int) != Own::Free, h.own_of(dst as int) != Own::Free,
    |         ----------------------------------- failed precondition
287 |         proof { lemma_store(h0, *self, src, dst); }
```
(share fails on `h.own_of(o as int) != Own::Free` at line 300, i.e. the deep-immutable check is gone; import fails on `owner_ok(h.own_of(o as int), r)` at line 311.)
- `nobarrier_direct.rs` also drops the lemma calls, so the plain contract fails (3 errors, `verification results:: 16 verified, 3 errors`; log `nobarrier_direct_error.txt`). Verbatim (each of store/share/import has this):
```
error: postcondition not satisfied
   --> nobarrier_direct.rs:279:17
279 |         ensures final(self).inv(),
    |                 ^^^^^^^^^^^^^^^^^ failed this postcondition
288 |         true
    |         ---- at the end of the function body
```
- [I] The first file shows which missing check each op needs; the second is the clean "this op can break `inv`" signal. Neither gives a counterexample heap (Verus does not print one). [F] The Rust model's runtime test found violations (19975/20000), which is independent evidence the unchecked ops are actually unsound; this proof's rejection alone shows only "not provable".

## Rerun
```
V=/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus
cd /hdd1/sichangheagent/vl_meeting_work/out/vlm2_iso/tabiso_verus
$V heap.rs; $V nobarrier.rs; $V nobarrier_direct.rs
```
Plain invocation works (z3 already swapped, per `vlm_servo/SUMMARY.md`). A harmless `GLIBC_2.39 not found` line is printed by the shell/Verus wrapper in this environment on every run [F]; verification still proceeds.

## Effort
- [F] Verify runs: about 14 on `heap.rs` while developing, plus 1 timing run, 1 each for the two no-barrier files (about 17 total; count from memory of this session, not logged).
- [B] About 25-30 min agent time. Not timed.
- Friction [F]: derived `==` on enums is not understood in exec code (used `match` helpers `is_shared`, `is_free`, `owner_ok_exec`); `Vec::new()` cannot appear in spec; quantifiers needed explicit instantiation helpers (`inv_a`, `inv_r`) and `c_ok` as a trigger; `(n-1)+1` had to be written out to fire the path trigger; updating a nested Vec used clone-then-`set`.

## What the proof does NOT cover
- [F] It proves the model, not any real engine. Nothing links `Heap` to V8/SpiderMonkey/QuickJS. The barrier being sufficient says nothing about whether a real JIT/runtime enforces it.
- [F] "Shared" immutability is only enforced by `store` rejecting Shared sources; there is no value/primitive model, and fields are append-only (no overwrite or delete of a field).
- [F] `free` is a single-object, conservative free (it also refuses self-referencing objects and ignores fields of Free objects). There is no mark-sweep over reachability, no slot reuse/moving GC, no proof that garbage is eventually reclaimed (liveness), and no check that Free objects are never accessed by ops other than through `own` tests. Realm-level GC (collect all unreachable) is not done.
- [F] `import` models only root insertion, not a message-passing protocol. No concurrency, threads, or weak references. Index arithmetic overflow past `usize` is not an issue because indices are `usize` into a `Vec`.
- [F] Spectre/timing side channels are outside the model (as in `tabiso/REPORT.md`).
- [I] The non-vacuity check is informal: `new` produces an `inv()` heap and the ops are executable, but I did not prove a concrete non-empty reachable example (no `assert(h.reaches(...))` witness).
- [B] `main` is an empty stub; the exec ops were not run (Verus-checked only).
