# vlm6_atfix: fix + proof for Boa `at()` overflow
(authored by agents unless marked 🧑)

## result
- fix: guard `i >= -len` in String.prototype.at and Array.prototype.at (`at_fix.patch`, against boa main 329e8974; worktree `boa/`, branch vlm6-atfix)
- Verus (`at_proof.rs`, spec = ecma262 main ToAbsoluteIndex + at steps): fixed string/array guards 4 verified, 0 errors (`verus_fixed.log`); original guards (`--cfg 'feature="orig"'`) 2 overflow errors (`verus_orig.log`)
  - assumptions: 0 ≤ len ≤ 2^53-1; ToIntegerOrInfinity saturates to i64 as Boa does; port of match arms, not Boa source
  - original array guard uses `i.abs()`; modeled as `-i` (equal for i<0) since vstd lacks a spec for i64::abs
- repro (`repro.js`): fixed build 10/10 ok (`repro_fixed.log`); unfixed build panics `Unexpected get()` (`repro_unfixed.log`)
- test262 main 831359a4, fixed release build (`t262_fixed.log`):
  - built-ins/String 1221 pass / 2 ignored / 0 fail; built-ins/Array 3083 pass / 0 fail; TypedArray/prototype/at 15 pass
  - staging/sm/{String,Array,TypedArray}/at.js pass; staging/sm overall 85 fail, none under String/ or Array/; no unfixed baseline run
- not done: debug build, `cargo test`
- draft: `../vlm4_drafts/boa_at_overflow.md` (+ `.patch`)
- boa_gc_finalizer_uaf.md: 0.22.0 restored as affected (Miri log cx_gc/0.22.0_clone-child.log shows UAF at boa_gc-0.22.0 gc.rs:316/363; vlm2_boagc/report.md: "triggers a Miri use-after-free on boa_gc 0.21.0, 0.22.0")
- nothing filed upstream
