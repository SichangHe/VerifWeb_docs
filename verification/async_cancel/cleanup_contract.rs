use vstd::prelude::*;

verus! {

/// Abstract effect of the identity-guarded removal checked in the real MIR.
pub open spec fn cleanup(before: Map<u64, int>, key: u64, owner: int) -> Map<u64, int> {
    if before.dom().contains(key) && before[key] == owner {
        before.remove(key)
    } else {
        before
    }
}

// 🧑 "the human requires proving the real code conforms to the spec, not only a model"
pub proof fn cleanup_contract(before: Map<u64, int>, key: u64, owner: int)
    ensures
        !cleanup(before, key, owner).dom().contains(key)
            || cleanup(before, key, owner)[key] != owner,
        before.dom().contains(key) && before[key] != owner
            ==> cleanup(before, key, owner) == before,
        forall|other: u64| #![auto] other != key ==>
            (cleanup(before, key, owner).dom().contains(other) == before.dom().contains(other)),
        forall|other: u64| #![auto] other != key && before.dom().contains(other) ==>
            cleanup(before, key, owner)[other] == before[other],
{
}
}

fn main() {}
