use vstd::prelude::*;
verus! {
async fn caller() { let r = async { 1u64 }.await; assert(r == 1); }
}
fn main() {}
