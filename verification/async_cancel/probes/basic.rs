use vstd::prelude::*;
verus! {
async fn one() -> (r: u64) ensures r == 1 { 1 }
async fn caller() { let r = one().await; assert(r == 1); }
}
fn main() {}
