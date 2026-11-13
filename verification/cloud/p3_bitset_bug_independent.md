# p3_bitset_bug_independent — independent check of the cranelift-bitset `from_range(64, 64)` claim

(authored by agents; date 2026-11-04)

## Verdict

The claim is confirmed (fact, reproduced locally). `ScalarBitSet::<u64>::from_range(64, 64)` panics in debug with `attempt to shift left with overflow` and returns the full set (64 elements) in release. The correct answer is the empty set, because `64..64` is empty. The same bug exists for every width `N` at `from_range(N, N)` (confirmed for `u32` at `(32, 32)`). Wasmtime `main` has the identical code. I found no open issue or PR that reports this exact case. A maintainer did say in 2023 that `N..N` should be legal.

## 1. Source lines

- Fact: crates.io `cranelift-bitset` 0.137.1, `src/scalar.rs` lines 127–143. Wasmtime `main` at commit `9959c2c6e2d9a5c42be8b5adaea88b072089502f` has byte-identical `scalar.rs` (`diff` printed nothing).
- URL (pinned): https://github.com/bytecodealliance/wasmtime/blob/9959c2c6e2d9a5c42be8b5adaea88b072089502f/cranelift/bitset/src/scalar.rs#L127-L143

```rust
127    pub fn from_range(lo: u8, hi: u8) -> Self {
128        assert!(lo <= hi);
129        assert!(hi <= Self::capacity());
130
131        let one = T::from(1);
132
133        // We can't just do (one << hi) - one here as the shift may overflow
134        let hi_rng = if hi >= 1 {
135            (one << (hi - 1)) + ((one << (hi - 1)) - one)
136        } else {
137            T::from(0)
138        };
139
140        let lo_rng = (one << lo) - one;
141
142        Self(hi_rng - lo_rng)
143    }
```

- Fact: the documented contract (same file, lines 110–111) is `/// Panics if `lo > hi` or if `hi > Self::capacity()`.` So `(64, 64)` is documented as a valid input. It passes both asserts.
- Fact: line 133's comment shows the author guarded the `hi` shift against overflow. Line 140's `lo` shift has no guard. `lo <= hi <= capacity`, so `lo == capacity` happens only when `lo == hi == capacity`.
- Inference: in release, `one << 64` is computed with the shift amount masked to 6 bits, so it equals `1 << 0 = 1`. Then `lo_rng = 1 - 1 = 0`, and `hi_rng - lo_rng` equals all-ones. This matches the observed output `0xffffffffffffffff`.

## 2. Reproduction (fact: run here with rustc 1.97.0 on x86_64 Linux)

`Cargo.toml`:
```toml
[package]
name = "bitset-repro"
version = "0.1.0"
edition = "2021"

[dependencies]
cranelift-bitset = "=0.137.1"
```

`src/main.rs`:
```rust
use cranelift_bitset::ScalarBitSet;
fn main() {
    let s = ScalarBitSet::<u64>::from_range(64, 64);
    println!("from_range(64,64) len={} is_empty={} bits={:#x}", s.len(), s.is_empty(), s.0);
    let t = ScalarBitSet::<u32>::from_range(32, 32);
    println!("u32 from_range(32,32) len={} bits={:#x}", t.len(), t.0);
    let u = ScalarBitSet::<u64>::from_range(3, 3);
    println!("control from_range(3,3) len={} bits={:#x}", u.len(), u.0);
}
```

Debug (`cargo run`), exit 101:
```
thread 'main' (509) panicked at /root/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/cranelift-bitset-0.137.1/src/scalar.rs:140:22:
attempt to shift left with overflow
```

Release (`cargo run --release`), exit 0:
```
from_range(64,64) len=64 is_empty=false bits=0xffffffffffffffff
u32 from_range(32,32) len=32 bits=0xffffffff
control from_range(3,3) len=0 bits=0x0
```

- Fact: the panic points at line 140, column 22, which is `one << lo`.
- Fact: the control case `(3, 3)` correctly returns the empty set. So the bug is specific to `lo == hi == capacity`.

## 3. Existing reports upstream

Search method: the GitHub REST API was unavailable in this session ("No linked GitHub account"), so I fetched github.com issue-search pages and ran one web search. Result counts come from the WebFetch summarizer. They are not raw API output.

- `is:issue/pr from_range` returned 2 items, both merged PRs: #6020 and #6013 (unrelated DSL work).
- `ScalarBitSet` returned 4 items: #12381, #10404, #10118, #9099. None of them is this bug. #10118 is an x64 `assert_eq` on `I32` vs `I64` address types at `cranelift/codegen/src/isa/x64/lower.rs:233:9`.
- `bitset overflow` returned 1 item: #6020.
- Fact (from `git log` of the cloned repo): `from_range` has had no commit message mentioning it. `scalar.rs` history on `main` has 4 commits (`b3636ff6e` 2024-06-18 crate introduction, `ff92e7afd`, `e4c27aea0`, `703871a29` 2025-05-27). None of them fixes this.

The closest prior work is PR #6020, "cranelift: Fix shift overflow when constructing BitSet" (merged 2023-03-14, https://github.com/bytecodealliance/wasmtime/pull/6020). Quotes below came back through the WebFetch summarizer and may not be exact:
- PR body: "`BitSet8::from_range` will panic if the lower bound is `>= 8`"
- PR body: "When constructing the `Wider` constraint for `I128`, avoid initializing the `ints` field of `ValueTypeSet` at all."
- reviewer cfallin: "LGTM. Arguably, a bitset with N bits should be legal to construct from range N..N, since N..N is empty, so if you want to put the conditional in `BitSet{,8}::from_range()` that would be fine too; but I don't mind too much either way."

Inference: the bug was known in 2023 for the old `BitSet8` type. It was worked around at the caller instead of fixed in `from_range`. The code carried over into `ScalarBitSet` when the crate was introduced (#8826).

## 4. Impact on wasmtime itself (fact: `grep` of `main`)

- The workaround from #6020 is still in place at `cranelift/codegen/src/ir/instructions.rs:1024` (`if lower_bound < BitSet8::capacity() {`), with the comment "Adding one to exclude I128 from the lower bound would overflow as 2^8 doesn't fit in a u8, but this would already describe the empty set so instead we leave `ints` in its default empty state."
- None of the other in-tree call sites (`instructions.rs` lines 993, 998, 1002, 1015, 1034, 1285–1288) can pass `lo == capacity` as written. That is inference from reading the constant or bounded arguments.
- The unit test `cranelift/bitset/tests/bitset.rs` `fn from_range` (lines 57–77) covers `(5,5)`, `(0,8)`, `(0,16)` and others, but not `(N, N)` at capacity.
- Belief: there is no wasmtime-internal exposure today. Exposure is limited to external users of the public `cranelift-bitset` API.

## 5. Assessment

- Severity (opinion): low. This is a logic bug in a public API, not memory-unsafe, and in-tree callers avoid it. The release-mode behavior is worse than the debug panic: it silently returns the complement of the right answer.
- Fix sketch (opinion): compute `lo_rng` with the same split trick as `hi_rng` (`if lo >= 1 { (one << (lo - 1)) + ((one << (lo - 1)) - one) } else { 0 }`), or special-case `lo == hi` to return the empty set. Then add a `from_range(N, N)` test for each width.
- Verification angle: this is a good small target for Verus/Kani-style checking. The spec "`from_range(lo, hi)` contains exactly `lo..hi` for all `lo <= hi <= capacity`" would catch it immediately.
- Upstream: not filed, per the instruction.
