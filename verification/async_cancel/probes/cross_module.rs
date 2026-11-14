use vstd::prelude::*;
verus! {
mod producer {
    use vstd::prelude::*;
    pub async fn one() -> (r: u64) ensures r == 1 { 1 }
}
mod consumer {
    use vstd::prelude::*;
    async fn caller() { let r = crate::producer::one().await; assert(r == 1); }
}
}
fn main() {}
