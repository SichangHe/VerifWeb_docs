# Group-chat bug probe: matrix-rust-sdk cross-process lock

(authored by agents unless marked 🧑)

Scope: a small probe (about 1 hour of work), matrix-rust-sdk only, at commit b93751e (2026-11-16). Wire core-crypto was not examined.

## Answer

- The probe found a concrete, model-checked way for two processes to both act under the crypto-store lock. It is not clearly new: a maintainer already says the guard "can be corrupted and we don't know about it".
- New relative to that comment (INFERENCE): the two exact code paths and a minimal trace. Nothing was reported upstream.
- Estimate (OPINION): a fuller hunt on this lock gives a sharper write-up, not a new headline bug. Better odds are in components with no maintainer awareness (Wire core-crypto commit/welcome handling, Matrix Olm session recovery).

## Component and why

`crates/matrix-sdk-common/src/cross_process_lock.rs`, the lease lock that keeps the Element X app and its notification process (NSE) from using the Olm account at the same time.

- It is candidate 46 and issue #3313. #3313 was closed as fixed on 2026-04-02 after PR #6326 made the generation counter atomic.
- It is small (about 500 lines of logic) and has a clear property: at most one process acts on crypto state, and a process whose cached state is stale is told so ("dirty").

## What was checked

- Read the lock, the SQLite lease query (`crates/matrix-sdk-sqlite/src/crypto_store.rs`, `try_take_leased_lock`), and the crypto caller (`crates/matrix-sdk/src/encryption/mod.rs`, `lock_store` / `on_lock_newly_acquired`).
- Wrote `lease_model.py`, a breadth-first explicit-state model: two processes, store row (holder, expiration, generation), 50 ms ticks, 500 ms lease, any process may be suspended for any number of ticks. Property: a process holding a guard that is not dirty has a view equal to the store generation.

## Suspected bug (FACT for code quotes, INFERENCE for the consequence)

Two code paths let a process keep a "Clean" guard after losing the lease.

1. The renewal task ignores the generation it gets back. Code:
   `Ok(Some(_generation)) => { // It's impossible that the generation can be different from the previous generation.`
   If the process was suspended past the lease, another holder took and released the lock, and renewal then succeeds with a new generation. `is_dirty` is never set.
2. A failed renewal only stops the task: `Ok(None) => { error!("Failed to renew the lock lease: the lock could not be obtained"); break; }`. Existing guards stay valid, and later `try_lock_once` calls return Clean without touching the store because `count_holders(&self.inner) > 0`.

Model output (A = main app, B = NSE):

    A:acquire -> 11 ticks (A suspended 550 ms) -> B:acquire -> A:STALE_WRITE

Concrete scenario (INFERENCE, not reproduced): A holds the guard during an encryption sync; iOS suspends A; the lease expires; B runs a sync, advances Olm sessions or uploads one-time keys, and saves; A resumes and saves its stale Olm state. Consequences match the #3313 symptoms: duplicate one-time-key upload (HTTP 400) or a wedged Olm session (#3354), seen by users as unable-to-decrypt.

Known-status evidence, Hywan in #3313 (FACT): "#6326 solves the “atomicity” problem of the generation, but it doesn't solve the next part: the lock guard can be corrupted and we don't know about it. The problem is mitigated by the fact the lock is acquired for a very short lifetime every time, but it's not ideal."

Caveats:
- The model is coarse: it treats any write by A after B acquired as a violation, and does not model how long real crypto guards are held.
- Not run against the real code; a reproduction would need a test that pauses one process past 500 ms while holding a guard.
- The real fix is a fencing check (compare the store generation at each write), a known pattern for leases.

## Would a fuller hunt find more? (OPINION)

- On this lock: unlikely to yield more than a stronger write-up and a reproduction of a maintainer-acknowledged issue.
- Mapping across group chats: the lease-without-fencing pattern is generic, so other multi-process clients (e.g. Wire's iOS notification extension with core-crypto) may have it; unchecked.
- The bigger bug class in group_state_bugs.md (Wire MLS forks, Matrix state resets) lives in protocol-state handling, which needs more than a 3-hour probe.
