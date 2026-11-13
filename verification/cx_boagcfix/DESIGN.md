# Finalizer collection
(authored by agents unless marked 🧑)

fresh reachability after callbacks
- preserve handle reference counts until handles are destroyed
  - `Gc::finalize` and `Ephemeron::finalize` do nothing
  - ordinary `Drop` decrements immediately
- clear marks and internal-handle counts, recount heap handles, then mark from roots
  - roots have more total handles than heap handles
  - revisit previously marked objects because callbacks can change their edges
- repeat callbacks and marking when newly unreachable objects need cleanup
  - remember strong objects already finalized this collection
  - clear pending ephemeron contents even when only their key dies
  - repeat after clearing because dropping values can change roots
- before sweep, count handles inside dead allocations and subtract them from target counts
  - all target allocations still exist
  - `DropGuard` suppresses decrements during deallocation
  - surviving allocations therefore retain accurate counts for later collections

assumptions and limits
- `Trace` implementations enumerate heap handles correctly
- callbacks complete and eventually stop refilling pending ephemerons
- fresh marking does not prove callback termination or arbitrary custom destructor safety
- tests and the benchmark are described in `REPORT.md`
