# Servo GC rooting contract: bite-sized Kani model

(authored by agents unless marked 🧑)

## Takeaways
- [F] A mock of Servo's `Dom<T>`/`Root`/`JSTraceable` plus a final-GC sweep is checkable with Kani in seconds. 4 harnesses, all as expected.
- [F] Kani separates the #24621 pattern (Drop derefs another GC object: fails in one sweep order) from a compliant Drop (passes in all orders).
- [F] A trace that omits a `Dom` field is caught; a derive-style trace generated from the field list marks every `Dom` field.
- [B] This checks the contract on a model, not on Servo. The gap is large (see the end).

## Sources (upstream cloned shallow, commit 6d3581dc86f1120c187b63b416a010fae43f811a, at `src_upstream/`; read only, not built)
- [F] `components/script_bindings/root.rs:153`: `pub struct Dom<T> { ptr: ptr::NonNull<T> }`, with doc "if garbage collection happens with a `Dom<T>` on the stack, the `Dom<T>` can point to freed memory." and "This should only be used as a field in other DOM objects." Marked `#[cfg_attr(crown, crown::unrooted_must_root_lint::must_root)]`.
- [F] `components/script_bindings/trace.rs`: traits `JSTraceable`/`CustomTraceable`, `unsafe fn trace(&self, trc: *mut JSTracer)`. Safety doc: "implementors of this method must ensure that all active objects are properly traced or else the garbage collector may end up collecting objects that are still reachable."
- [F] `components/script/docs/JS-Servos-only-GC.md:125`: "We will implement this method with a custom `derive` target `#[derive(JSTraceable)]`, or a custom attribute `#[dom_struct]` which implies it."
- [F] crown is at `support/crown/src/` (`unrooted_must_root.rs`, `trace_in_no_trace.rs`, ...). `unrooted_must_root.rs` says: "This lint ... ensures that `#[crown::unrooted_must_root_lint::must_root]` values are used correctly." It checks must-root values are not used in a non-`must_root` struct field. So crown enforces "no unrooted Dom on stack/in non-DOM fields". [I] It has no lint on what `Drop` touches (I found none among its 4 lint files; not exhaustively audited).
- Issues (via `gh issue view`):
  - https://github.com/servo/servo/issues/24621, "Crash during final GC with webgl content": "This is another instance of the problem with doing things in DOM object destructors that requires interacting with other DOM objects (#26488). There are absolutely no guarantees that pointers are valid any more, since the JS objects could have been finalized and destroyed the corresponding Rust object. In this case, the webgl texture finalizer tries to check the current bound framebuffer for the webgl contex, but the framebuffer object has already been GCed." (stack: `WebGLTexture::drop` -> `delete` -> `WebGLRenderingContext::bound_framebuffer` -> `MutNullableDom<WebGLFramebuffer>::get`, under `JSRuntime::destroyRuntime` -> `gc`).
  - https://github.com/servo/servo/issues/15318, "Shutting down Servo with a native Promise object alive crashes during GC": "When we do the final GC when shutting down a JS runtime, if there's a native `Rc<Promise>` alive then its destructor will run and cause problems." Stack: `Promise::drop` -> `DomObject::global` -> `GlobalScope::from_reflector`. Later comment by jdm: "the stack trace shows the crash is slightly different than I thought - it's not crashing during a GC, it's crashing when dropping the native Promise object as part of dropping the ScriptThread (via the JobQueue that holds on to Job objects that contain Promises), presumably after the GC has happened."
  - [F] So #15318 is Drop-after-runtime-gone, not Drop-during-sweep. My model covers only the #24621 shape (sweep order).

## Model (`model/src/lib.rs`, `model/src/proofs.rs`)
- `GcBox<T>` = header (`alive`, `marked`) + value. `Dom<T>` = raw pointer (as Servo's `NonNull`). `Dom::get` asserts the pointee is alive (Servo has no check).
- `JSTraceable::trace(&self,&Tracer)`; impls for `Dom`, `Option<Dom>`, `[Option<Dom>;N]`, `u32`. `Root::mark` marks and traces. `finalize` runs the value's Drop then sets `alive=false`; memory is never freed, so a stale deref is a deterministic assertion.
- `derive_traceable!` macro generates `trace` from the field list, standing in for `#[derive(JSTraceable)]`.
- Harnesses:
  - `derived_trace_visits_all`: `Holder{a: Dom, b: Option<Dom>, v: [Option<Dom>;2], n: u32}`, all optionality symbolic. Asserts each present `Dom` is marked and visit count equals the number of present `Dom`s.
  - `bad_trace_misses_field` (`should_panic`): hand-written trace omits `b`.
  - `final_gc_bad_drop` (`should_panic`): `BadTexture{fb: Dom<Fb>}` whose Drop reads `fb.id`; sweep order symbolic.
  - `final_gc_good_drop`: `GoodTexture` whose Drop touches only its own `u32`; both orders.

## Rerun
```
cd /hdd1/sichangheagent/vl_meeting_work/out/vlm2_iso/servo_rooting/model && ~/.cargo/bin/cargo-kani kani   # or: cargo kani
```
Verbatim (filtered; full log in `kani_run.txt`):
```
Checking harness proofs::h::final_gc_good_drop...
VERIFICATION:- SUCCESSFUL
Checking harness proofs::h::final_gc_bad_drop...
Failed Checks: "UAF: Dom<T> deref of finalized GC object"
VERIFICATION:- SUCCESSFUL (encountered one or more panics as expected)
Checking harness proofs::h::bad_trace_misses_field...
Failed Checks: "reachable via h.b but not marked"
VERIFICATION:- SUCCESSFUL (encountered one or more panics as expected)
Checking harness proofs::h::derived_trace_visits_all...
VERIFICATION:- SUCCESSFUL
Complete - 4 successfully verified harnesses, 0 failures, 4 total.
```
Kani 0.68.0, CBMC 6.11.0.

## Debugging notes (honest record)
- [F] First run of `final_gc_bad_drop` reported "no panics": `drop_in_place` on a `ManuallyDrop<T>` is a no-op, so Drop never ran. That also made the first "good" pass vacuous. Fixed to drop the inner `T`; this is why the bad/good pair matters (a should_panic harness guards against vacuous passes).
- [F] `Vec<Dom>` hit unsupported alloc-error paths in Kani, so the Vec field became `[Option<Dom>;2]`.

## NOT covered
- Miri: not run. [F] `cargo miri` is "not available for the '1.99.1-x86_64-unknown-linux-gnu' toolchain" here. Also, `finalize` casts `*const T` to `*mut T` from a shared reference, which Miri would flag as UB; the model needs `UnsafeCell` before Miri use.
- Verus: not used.
- crown: not run (needs Servo's pinned nightly with `rustc_private`; not built).
- No real GC: no incremental marking, no JS-side reachability, no `Rc<Promise>`/ScriptThread teardown (#15318 shape), no `MutNullableDom`, no `Heap<T>`/barriers, no threads.
- Sweep order is only the two orders of two objects; no cycles; no "Drop touches only non-GC data" check beyond the one example. The property is encoded by the `alive` assert at deref, not as a static spec on `Drop` (that would need a lint, e.g. a crown rule, or a ghost "in_final_gc" flag on every `Dom::get`).
- The derive check is weak: the macro generates trace and the field list from one source, so it tests my macro, not Servo's `#[derive(JSTraceable)]` (a proc macro in `components/`; not read in depth).

## Gap to checking real Servo code
1. Servo's real derive is a proc macro over `script` types; checking it needs expansion of real DOM structs (rustc-driven, e.g. a crown lint "every `Dom`/`MutDom`/`DomRefCell` field is reached by trace"). Kani cannot build `script` (SpiderMonkey FFI, huge crate).
2. The Drop rule is a global property over call graphs: every `impl Drop` of a `dom_struct` must not reach `Dom::deref`/`MutNullableDom::get`/`DomObject::global`. This is a reachability analysis (MIR call graph, as crown works on MIR/HIR), not a bounded proof. A natural next bite: a crown-style lint, validated on a mock that replays #24621 and #15318.
3. Needs a real list of `Drop` impls on DOM types (e.g. `git grep "impl Drop for" components/script/dom` gives `DroppableWebGLFramebuffer`, `DroppableWebGLBuffer`, `VertexArrayObject` at the clone commit) and manual triage of what each touches.
