use vstd::prelude::*;
use vstd::invariant::*;
verus! {
async fn pause() opens_invariants none no_unwind {}
async fn caller<A, P: InvariantPredicate<A, u8>>(i: Tracked<LocalInvariant<A, u8, P>>) {
    let tracked i = i.get();
    open_local_invariant!(&i => inner => { pause().await; });
}
}
fn main() {}
