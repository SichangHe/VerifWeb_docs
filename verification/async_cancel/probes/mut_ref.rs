use vstd::prelude::*;
verus! {
async fn pause() {}
async fn set(x: &mut u64) ensures *final(x) == 2 {
    *x = 1;
    pause().await;
    *x = 2;
}
async fn caller() { let mut x = 0; set(&mut x).await; assert(x == 2); }
}
fn main() {}
