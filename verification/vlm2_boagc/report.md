# vlm2_boagc: independent check of the boa_gc finalizer-resurrection use-after-free claim
(authored by agents unless marked 🧑)

claim checked: /hdd1/sichangheagent/vl_meeting_work/out/cloud/p1_gc_marking.md §4

## verdict
- CONFIRMED (fact): my own safe-Rust repro triggers a Miri use-after-free on boa_gc 0.21.0, 0.22.0 (crates.io) and git main @ 329e89748ed34e218fe593b4209b1dbe1d6eb64d
- no existing boa report of this bug found (fact, from searches below); nothing filed upstream
- the final Verus files verify with tools/verus-x86-linux (fact); all 7 mutants fail (fact)

## my repro (written independently; 0 `unsafe` tokens): repro/src/main.rs
- parent box holds Gc<Child>; Parent::finalize clones `self.c` into a thread_local; parent dropped; force_collect(); then read child
- no cycle needed: dropping the only external handle makes parent dead
- variants: r_0.22.0/, r_main/ (same source, different dependency)
- command: `MIRIFLAGS=-Zmiri-disable-isolation cargo +nightly miri run` (miri 0.1.0 (8d1a764304 2026-10-06))
- native run prints `child.v=0xc0ffee` (reads freed memory silently)

Miri output (0.21.0, verbatim excerpt):
```
error: Undefined Behavior: constructing invalid value of type &boa_gc::GcBox<Child>: encountered a dangling reference (use-after-free)
   --> .../library/core/src/ptr/non_null.rs:454:18
            1: boa_gc::Gc::<Child>::inner
                at .../boa_gc-0.21.0/src/pointers/gc.rs:316:18: 316:43
            2: <boa_gc::Gc<Child> as std::ops::Deref>::deref
                at .../boa_gc-0.21.0/src/pointers/gc.rs:363:9: 363:21
            3: main::{closure#0}
                at src/main.rs:17:101: 17:104
```
- 0.22.0: same error, frames at `boa_gc-0.22.0/src/pointers/gc.rs:316:18` and `:363:9`
- main: same error, frames at `checkouts/boa-.../329e897/core/gc/src/pointers/gc.rs:316:18` and `:363:9`
  - https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/gc/src/pointers/gc.rs#L316
- not independently verified: the report's root-cause explanation (stale non_root_count, Gc::finalize dec_ref_count); I only confirmed the symptom

## upstream search (gh search, boa-dev/boa)
- "resurrect": #5187 (closed, vtable-corruption/ACE report) and #5567 (open GC roadmap); neither reports this UAF
  - #5187 only says: "finalizers heavily mutate state and can resurrect objects"
  - #5567 comment (mansiverma897993): "an object without a finalizer can become reachable through another object's finalizer. Excluding such objects from the second mark needs a separate justification" — design caveat, not a bug report
- "finalize use-after-free": no hits; "finalizer": #5337, #4410, #3940 — unrelated
- PRs "resurrect": none
- not checked: rust-gc #124 cited by report

## Verus spot-check (final_artifacts copied to final/; verus 0.2026.11.02.8bf68ee; log verus_mine.txt)
- boa_ephemeron 15, boa_mark 11, boa_roots 13, incremental 9 verified, 0 errors (= report's 48)
- m1–m7: each has ≥1 verification error
- no assume/admit/external_body in the 4 proofs
- caveat: earlier extracted/ boa_mark.rs fails to parse on this Verus (mut-ref `old`/`final` syntax); final version is fine
- not checked: whether the models faithfully match boa source
