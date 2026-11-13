# Raft membership changes in openraft: first Verus proof
(authored by agents unless marked 🧑)

Result: I proved one ingredient of the first target property, on a hand transliteration of openraft's real quorum code. Neither target property is proven end to end, and I found no new bug.

Target properties (from the task): (P1) at most one leader per term, even during a membership change; (P2) `change_membership` returns Ok only if the committed membership equals the requested one.

## What is proven (FACT: Verus 0.2026.11.02, "17 verified, 0 errors", no assume/admit/external_body)

openraft decides whether a membership change may skip the joint phase in `RaftMembershipExt::allows_direct_transition_to` (openraft main 7628ad40, `openraft/src/membership/raft_membership_ext.rs`), which calls `supports_direct_transition_to`, which requires `configs.intersects_with(&other.configs) == Some(true)`. `intersects_with` and `is_quorum` live in the external crate `quorum-set` 0.6.0 (`src/quorum/quorum_intersection_impl.rs`, `src/quorum/quorum_set_impl.rs`). Candidates count votes with the same `Vec<BTreeSet>` quorum set (`openraft/src/proposer/candidate.rs`, `membership.read_quorum_set()`).

`quorum.rs` proves, for the transliterated functions:
- `BTreeSet::is_quorum` returns true exactly when the ids are a strict majority of the config (the code counts by 2 and compares with `len`).
- `Vec<BTreeSet>::is_quorum` returns true exactly when the joint config is nonempty and the ids are a majority of every part.
- `BTreeSet::intersects_with` and `Vec<BTreeSet>::intersects_with`: if they return `Some(true)`, then every quorum of the old config shares a node with every quorum of the new config. This covers the `saturating_sub` arithmetic, the empty-config early return (vacuous, since an empty joint config has no quorum) and the "any pair of parts intersects" shortcut for joint configs.

Mutant check (FACT): changing `>` to `>=` in `BTreeSet::intersects_with` (`quorum_mut.rs`) makes verification fail ("16 verified, 1 errors").

Why it matters (INFERENCE): with joint consensus, P1 rests on old and new quorums overlapping. In openraft, a direct (non-joint) transition is safe only if this check is sound. The proof shows it is sound for every input, not only for the unit-test cases.

## Gap to "the code conforms to the spec"

- The proof is about a transliteration, not the compiled crate. `BTreeSet<u64>` is replaced by a duplicate-free `Vec<u64>` with a linear `contains`; the loop structure and arithmetic follow the source line for line. Closing this gap needs Verus specs for `BTreeSet` (vstd has none for its iterators, as far as I know) or running Verus on the crate itself. I did not do either.
- P1 end to end also needs: vote persistence, the rule that a node votes once per term, log-up-to-date checks, and which membership a candidate uses (effective vs committed). None of that is verified. That code is spread over the async `RaftCore`/`Engine` (thousands of lines); I judge it not feasible in one session.
- P2 is not verified. Fact from `openraft/src/raft/api/management.rs`: the second step now appends `uniform_payload` "with its already bound target", computed once in the first step, and keeps only the `CommittedLeaderId` precondition across steps. This is the shape of the fix for #1395 (the removed-node restore). Proving P2 needs a model of the two `call_core` round trips and leader changes between them.

## Not checked
- Completeness (whether `intersects_with` returns `None` for configs that do always intersect). It only costs an extra joint phase, not safety.
- The other quorum kinds in `openraft/membership/` (threshold, weighted, grid, hierarchical, explicit). `ThresholdQuorumSet::intersects_with` has the same arithmetic shape and is the obvious next target.

## Rerun
`/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus quorum.rs` (seconds). Sources: openraft cloned at `/hdd1/sichangheagent/vl_meeting_work/tools/vlm49_raft/openraft`, quorum-set 0.6.0 at `/hdd1/sichangheagent/vl_meeting_work/tools/vlm49_raft/dl/`. No fork was needed, since no upstream code was changed.
