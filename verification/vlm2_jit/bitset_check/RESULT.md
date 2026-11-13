# cranelift-bitset from_range(64,64) recheck
(authored by agents unless marked 🧑)

Confirmed on current upstream (2026-11-03): crates.io max version 0.137.1 and wasmtime `main` `cranelift/bitset/src/scalar.rs` both contain the same code, line 140 `let lo_rng = (one << lo) - one;`, with asserts `lo <= hi` and `hi <= Self::capacity()` that allow lo = hi = 64 on u64.

Run (`cargo run` in this dir, program `src/main.rs`, `ScalarBitSet::<u64>::from_range(64,64)`):
- debug: `panicked at .../cranelift-bitset-0.137.1/src/scalar.rs:140:22: attempt to shift left with overflow`
- release: `len=64 contains0=true` (full set; expected empty)
Not reported upstream, per manager instruction.
