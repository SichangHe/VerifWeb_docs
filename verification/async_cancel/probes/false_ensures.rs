use vstd::prelude::*;
verus! {
async fn one() -> (r: u64) ensures r == 2 { 1 }
}
fn main() {}
