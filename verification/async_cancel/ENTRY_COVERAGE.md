# Pingora entry coverage
(authored by agents unless marked 🧑)

run
- `uv run --no-project python -m verification.async_cancel.entry_coverage RESUME.mir`
- `uv run --no-project python -m verification.async_cancel.entry_coverage_test RESUME.mir`
- use the resume artifact from [the pinned build](real_pingora/README.md)

checked structure
- exactly one direct `HashMap::<...>::insert(...)` occurs in the parsed function
  - the actual artifact places it in `bb47`
  - registration's write-lock acquisition at `bb14` dominates it from coroutine dispatch `bb0`
    - removing `bb14` makes insertion unreachable from `bb0`
    - insertion is reachable from both entries before removal
- there is one normal-control-flow block sequence from `bb0` to this insertion
  - reverse reachability isolates blocks that can reach insertion
  - reject multiple insertion-reaching successors and cycles
  - [the combined command](CONDITIONAL_CHECK.md) compares this prefix with the interpreter's actual executed trace
- each boxed dynamic callback poll's normal successor dispatches on its result discriminant
  - permits only unrelated storage cleanup and a result place mention before an adjacent discriminant assignment and switch
  - rejects intervening selector writes or mutable borrows
  - rejects unrecognized accesses to the return place instead of overlooking alternate Pending writes
  - includes terminating-unwind callback calls in the poll inventory
  - every block reachable from the Ready edge is free of Pending returns and direct insertion
  - covers all three callback polls, including the owner's callback
- normal control flow overapproximates switch choices and assertion success
  - ignores unwind edges, follows normal call and drop returns
  - rejects unknown terminators, missing targets and additional direct insert sites
  - examines direct insert sites even in unreachable blocks

source connection
- [pinned `read_through.rs`](https://github.com/cloudflare/pingora/blob/b2aeef4875823ffa75b638ba586ed491a1fc851e/pingora-memory-cache/src/read_through.rs), `RTCache::get`, map-miss branch
  - `let new_lock = CacheLock::new_arc();`
  - `let new_lock2 = new_lock.clone();`
  - `lockers.insert(hashed_key, new_lock2);`
  - `(Some(new_lock), None)`
- the corresponding MIR call is `HashMap::<u64, Arc<CacheLock>>::insert(move _73, move _76, move _77) -> [return: bb48, unwind: bb350]`
- the owner's callback switch is `switchInt(move _271) -> [0: bb191, 1: bb190, otherwise: bb13]`

remaining proof obligations
- block-prefix coverage does not establish coverage of all possible values
  - the publication interpreter now derives saved frame values and key derivation from initial dispatch
  - its cache/map misses remain conditional call outcomes; different values may follow the same block sequence
  - the checker does not establish that every state reaching insertion follows the interpreted map-miss semantics
  - no whole-function ownership theorem follows from this check
- direct call names delimit the insertion inventory
  - callees, generic callbacks, destructors and indirect calls may modify shared state under their separate contracts
  - does not prove absence of map mutation through other APIs or raw writes
- Ready exclusion concerns caller suspension points only
  - a synchronous call may block, panic, diverge or have side effects
  - no Ready-path cleanup, successful return or termination theorem
- inherits the pinned MIR parser and compiler trust boundary
  - assumes Poll discriminants 0 for Ready and 1 for Pending
  - validates the pinned callback dispatch shape, not arbitrary equivalent MIR
  - `bb14` remains the pinned registration entry

mutation evidence
- real artifact accepted
- rejected entry bypass, additional insertion, callback Ready redirected to Pending, overwritten selector and mutable result borrow
- rejected a second path to insertion, terminating-unwind poll bypass and alternate Pending discriminant write
- accepted inserted neutral block and systematic non-return-local renaming
