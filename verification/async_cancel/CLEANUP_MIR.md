# Checking the actual Pingora cleanup body
(authored by agents unless marked 🧑)

scope
- follow-up: [semantic translation](CLEANUP_SEMANTICS.md) derives map obligations from the instructions instead of matching these audit fingerprints
- [cleanup_mir_check.py](cleanup_mir_check.py) accepts only the complete audited MIR bodies for `CacheLockGuard::drop` and its pointer-comparison closure
  - includes declarations, types, operands, assignments, calls, branch targets and unwind edges
  - hashes the complete bodies with SHA-256 after removing indentation and empty lines
  - stores audit fingerprints rather than generated compiler artifacts
  - rejects every other body, including equivalent implementations
- matches real compiler output to a manually audited template
  - assumes SHA-256 collision resistance
  - no independent application model replaces the Rust body
  - the Python checker does not prove the template's semantics in a proof assistant
- source: [Pingora PR #1037 commit](https://github.com/cloudflare/pingora/blob/b2aeef4875823ffa75b638ba586ed491a1fc851e/pingora-memory-cache/src/read_through.rs), `CacheLockGuard`
  - upstream documentation: “Releases a [CacheLock] it owns when dropped, including when the owning future is cancelled while the lookup is still pending.”
  - compiler: Rust 1.99.1, as recorded in [the build instructions](real_pingora/README.md)
  - this checker does not authenticate build identity or recheck struct definitions

conditional claim
- assuming the field mappings and dependency semantics below, every normal return from the accepted destructor follows
  - a returned `Semaphore::add_permits` call with 10 permits on the semaphore in this guard's lock
  - removal at this guard's hashed key from this guard's lockers map iff the entry inspected under the write lock has the same allocation identity as this guard's lock
  - release of that write lock
- the identity test describes the entry while the write lock is held
  - notification precedes acquiring that lock
  - another task may change the entry before lock acquisition
  - after release, another task may insert an entry again
- makes no completion promise on panic, abort, nontermination or a blocking dependency

map effect for the abstract cleanup contract
- let M be the map immediately after write-lock acquisition, K the guard's hashed key, and L the guard's Arc allocation identity
- immediately before releasing that write lock, the map is M with K removed iff M contains K and its entry has identity L; otherwise it is M
  - every other key retains its original entry
  - an entry at K with a different identity is preserved
  - no entry with identity L remains at K
- this is the concrete effect corresponding to the abstract [cleanup contract](cleanup_contract.rs)
  - correspondence still relies on the audited template and trusted dependency meanings
  - notification adds 10 permits before the map snapshot; no final semaphore-count claim excludes concurrent consumers

audited dataflow
- `bb0–bb1`: guard field 2 → `_5` → Arc dereference `_4` → semaphore field 1 → `_3` → `add_permits(10)`
  - the sole normal successor of notification is `bb2`
- `bb2–bb4`: guard field 0 → `_18` → write guard `_6` → map `_9`
  - guard field 1 → `_11` → map lookup `_8`
- `bb5`: guard field 2 → `_13` → closure capture `_12`
  - `is_some_and(_8, _12)` produces boolean `_7`
  - closure captures the guard Arc in `_3` and returns `Arc::ptr_eq(_2, _3)`
- `bb6`: false reaches `bb10`; true reaches `bb7`
- `bb7–bb9`: mutable dereference of the same write guard → map `_15`
  - guard field 1 → `_17` → `remove(_15, _17)`
  - removed value `_14` is dropped before reaching `bb10`
- `bb10–bb11`: drop the write guard, then return
  - no path to normal return bypasses this drop
  - recognized unwind paths propagate unwinding through `bb12–bb13`

trusted boundary
- source-to-MIR compilation, input provenance, MIR parsing and the manually audited template
- struct fields: guard 0 = lockers, 1 = hashed key, 2 = lock; CacheLock 1 = semaphore
- Arc dereference preserves allocation identity; `ptr_eq` compares allocation identity; Arc destruction respects Rust ownership
- RwLock write acquisition gives exclusive map access; guard dereferences access that map; guard destruction releases the lock
  - no other task modifies the map while this guard holds its write lock
- HashMap lookup reads the supplied key; removal removes only that key and returns its previous value
  - assumes ordinary u64 key equality and hashing
- `Option::is_some_and` is false on None and otherwise returns the closure applied to the contained value
- the semaphore operation adds the specified permits when it returns
  - this is not a proof that waiters will run
- dependency implementations are not proved here
  - initialization of the correct guard and destruction of the caller's live guard remain separate correspondence obligations

reproduce
- generate the crate `--emit=mir` output with [real_pingora/README.md](real_pingora/README.md)
- run from the repository root
  - `uv run --no-project python verification/async_cancel/cleanup_mir_check.py CRATE.mir`
  - `uv run --no-project python -m verification.async_cancel.cleanup_mir_test CRATE.mir`
- executed against the actual Pingora crate MIR
  - original bodies accepted
  - nine instruction mutations rejected: wrong removal key, unconditional removal, reversed identity branch, wrong notification operand, skipped notification, wrong permit count, wrong comparison operand, skipped write-guard release, extra instruction
  - missing and duplicate destructor bodies rejected
  - mutations edit MIR text and are not compiled Rust mutants
  - test script reports failures only
