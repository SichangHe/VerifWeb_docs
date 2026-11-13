# vlm_servo: Verus on small real Servo / browser-adjacent Rust
(authored by agents unless marked 🧑)

Takeaway: proving bounded, arithmetic-heavy, safe-Rust pieces of real browser crates in Verus is cheap: each took about 25–35 min of agent time and 6–14 verify runs. Code that uses unsafe or raw pointers, generics over numeric traits, or float conversions has to be rewritten first. That rewrite was not attempted, so its cost is not measured.

Setup: Verus 0.2026.11.02 at `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus`. The bundled z3 needs glibc 2.38, but this host has 2.35, so it was replaced with z3 4.16.0 from the pip `z3-solver` manylinux wheel.

Per component (details, verbatim Verus errors and rerun commands are in each `REPORT.md`):

- selectors 0.31.0 `bloom.rs` CountingBloomFilter, used by Servo style and Stylo. Proved:
  - slot indices are in bounds
  - counters never overflow or underflow
  - no false negatives
  - a counter that reaches 255 stays there

  Finding: `remove_hash` underflows if the hash was never inserted. Upstream leaves that to the caller, so the proof needs it as a precondition. See `selectors_bloom/REPORT.md`.
- app_units Au plus euclid Rect/Box2D, Servo's layout geometry. Proved:
  - `clamp` and `new` return the exact clamped value
  - `add`/`sub` do not overflow for valid inputs, and `mul` never panics and returns the exact clamped product
  - the `from_px`/`to_px` round trip, for |px| ≤ 17895697
  - intersection is commutative, and a non-empty intersection is contained in both inputs

  Without preconditions, `Au::add`/`sub` and `Rect::intersection` (at `x + w`) can overflow. Float conversions were not done. See `layout_geometry/REPORT.md`.
- cranelift-bitset 0.125.0 ScalarBitSet, from Wasmtime's JIT. Proved:
  - `contains`, `insert` and `remove` match set semantics
  - `from_range(lo, hi)` returns exactly the set {lo..hi}

  Bug, which I checked in the source: `from_range(64, 64)` on u64 evaluates `1 << 64`, which the asserts allow. A debug build panics; a release build returns the full set instead of the empty one. See `jit_piece/REPORT.md`.
- smallbitvec 2.5.3, Servo's small bit vector. Partial result: only the inline (no heap allocation) half is proved against a `Seq<bool>` model, with 46 obligations verified. The heap half is blocked because it uses a tagged pointer (`usize | 1`), `Vec::from_raw_parts` and `mem::forget`. See `smallbitvec/REPORT.md`.

Recurring friction:
- vstd has no `trailing_zeros`, `leading_zeros` or `count_ones`, so these needed proved replacement loops or were left out
- generic numeric traits, operator traits and `Ord::clamp`/`checked_mul` had to be specialised or rewritten
- `bit_vector` proofs cannot use `forall` or struct fields
- the new `final(self)` rule for `&mut` postconditions needed fixes

Meeting question "what the Verus checker tells the agent per failed attempt": the reports confirm it reports which assertion, postcondition, precondition or arithmetic-overflow check failed, with its source location. Each report's failure log has the verbatim messages.

Not duplicated: the surveys in `/ssd1/sichangheagent/phd_labs/ara/research_projects/web_js_survey` (`rust_verifiers.md`, `verus_open_questions.md`).

Possible next steps (not done):
- the smallbitvec heap half
- the cssparser tokenizer
- Servo `components/` code itself, such as the layout fragment tree
