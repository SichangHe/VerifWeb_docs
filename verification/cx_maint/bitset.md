# Wasmtime/Cranelift maintainer triage
(authored by agents unless marked 🧑)

Judgment: likely accepted as a small real bug (valid input per the documented contract panics or returns the wrong set); a one-line fix plus a test would be welcomed. Low severity, no in-tree caller affected. Minor wording fixes needed. This is my triage assessment, not a maintainer decision.

Reviewed [the draft](../vlm4_drafts/cranelift_bitset_from_range.md) without changing it. Fresh work directory: [bitset/](bitset/). Upstream `main` resolved to `9959c2c6e2d9a5c42be8b5adaea88b072089502f` on 2026-11-04 (same as the draft); sparse clone retained in `bitset/up/wasmtime`.

## Execution evidence

Ran the draft's `Cargo.toml` (`cranelift-bitset = "=0.137.1"`) and `main.rs` unchanged with rustc `1.97.1 (8bab26f4f 2026-07-14)`. Results match the draft:

- [Debug log](bitset/debug.log): `panicked at .../cranelift-bitset-0.137.1/src/scalar.rs:140:22: attempt to shift left with overflow`.
- [Release log](bitset/release.log): `from_range(64,64) len=64 is_empty=false bits=0xffffffffffffffff`.

The draft's other-widths and fix claims (u8..u128, usize, two fixes, existing tests) were not re-run; the draft shows no script for them. Reproduction of the headline case needs no extra information.

## Current upstream source evidence

- [`scalar.rs` on main](https://github.com/bytecodealliance/wasmtime/blob/9959c2c6e2d9a5c42be8b5adaea88b072089502f/cranelift/bitset/src/scalar.rs#L127-L139) is byte-identical to the 0.137.1 crate file ([upstream-scalar.rs](bitset/upstream-scalar.rs)): `let lo_rng = (one << lo) - one;` at line 140 after `// We can't just do (one << hi) - one here as the shift may overflow`. The guarded `hi_rng` is at lines 134-138, not 133-139.
- Doc contract, same file: "Panics if `lo > hi` or if `hi > Self::capacity()`." Asserts `lo <= hi` and `hi <= Self::capacity()` pass for `(N, N)`.
- [Existing test](https://github.com/bytecodealliance/wasmtime/blob/9959c2c6e2d9a5c42be8b5adaea88b072089502f/cranelift/bitset/tests/bitset.rs#L57-L58) covers `from_range(5, 5)` for u8 only, not `(N, N)`; the missing-test claim holds.
- Callers: [instructions.rs L1024](https://github.com/bytecodealliance/wasmtime/blob/9959c2c6e2d9a5c42be8b5adaea88b072089502f/cranelift/codegen/src/ir/instructions.rs#L1024-L1034) still has `if lower_bound < BitSet8::capacity() {` guarding `BitSet8::from_range(lower_bound, 8)`. Other calls use literal bounds below capacity or `lo = 0`. My grep of `cranelift/` found no unguarded `(N, N)` caller; this confirms the draft's hedged claim for the sparse checkout only.
- Channel: [SECURITY.md](https://github.com/bytecodealliance/wasmtime/blob/9959c2c6e2d9a5c42be8b5adaea88b072089502f/SECURITY.md) line 15 contains `Report a Vulnerability`; the draft's quote is correct. `.github/ISSUE_TEMPLATE/` has `clif-bug-report.md`, as claimed. A non-security API bug belongs in a normal issue.
- #6020 history and the cfallin quote were not re-fetched.

## Concrete draft changes, in priority order

1. Original: "`scalar.rs` is byte-identical to wasmtime `main` ... #L110-L143". Link range covers doc text; use `#L127-L139` and name the function. Also the original "The `hi` shift on lines 133-139" should read "lines 134-138".
2. Original: "I ran u8, u16, u32, u64, u128 and usize ... and compared every other valid `(lo, hi)` pair". Attach the script (or say it is a local check not in the report), since a maintainer cannot reproduce it from the text. The Steps only cover u64.
3. Original: "Possible fix. Either of these ... passes the crate's existing tests". Offer a PR explicitly or give the test snippet; maintainers prefer a patch plus test. Add: "Happy to send a PR" (only if the author intends to).
4. Original: "If this is fixed, that workaround could possibly be removed." Make concrete: the guards at `instructions.rs` L1024 and L1033 would become unnecessary; or drop the sentence to keep the report focused.
5. Original: "(inference from reading call sites; not established repo-wide)". Replace with the scope actually checked: "grep of `cranelift/` on 9959c2c: no `(N, N)` caller."
6. Original: "Cranelift version or commit: crates.io ... `cargo search` on 2026-11-04 showed 0.137.1". Drop the `cargo search` detail; the pinned version and commit suffice.
