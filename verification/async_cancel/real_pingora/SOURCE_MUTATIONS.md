# Compiled Rust mutation checks
(authored by agents unless marked 🧑)

scope
- two independent source mutations to the [pinned Pingora checkout](README.md), compiled on 2026-11-14 UTC
- isolated clone with the original Cargo.lock, separate target/build directories and one MIR dump directory per mutation
- compilation used the README's `cargo rustc` command under `cpu-run LOW`, two cores and a 16 GiB/512-task scope
- the combined `verification.async_cancel.check_pingora` command consumed each mutation's resume, drop and emitted crate MIR

results
- insert `drop(_guard);` immediately before the owner's `let value = CB::lookup(key, extra).await;`
  - Rust compilation succeeded
  - checker exited 1: `ownership rejected: saved field lacks matching typed compiler identity`
  - rejection detects the changed compiler frame schema; this is not evidence that the checker interpreted early destruction
- independently replace `.is_some_and(|l| Arc::ptr_eq(l, &self.lock))` with `.is_some_and(|l| !Arc::ptr_eq(l, &self.lock))` in `CacheLockGuard::drop`
  - Rust compilation succeeded
  - emitted predicate contains `_0 = Not(move _3);`
  - checker exited 1: `cleanup translation rejected: unsupported instruction: _0 = Not(move _3);`
- these are rejection checks on compiler-generated mutants, not a cancellation-safety theorem or runtime regression

artifact pairing
- restoring the original source before the second mutation keeps the mutations independent
- changing the MIR dump directory changes Cargo's crate hash and can leave several emitted `.mir` files in `build/debug/deps`
- select the emitted crate file from the current compilation and inspect its mutated function
  - initially pairing the second resume/drop with the first emitted crate falsely passed
  - using the freshly emitted predicate rejected as reported above
  - the checker assumes paired artifacts from one build; it does not authenticate that provenance
