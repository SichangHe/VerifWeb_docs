use vstd::prelude::*;
verus! {
mod m1 {
    use vstd::prelude::*;
    pub async fn foo() -> (ret: usize) ensures ret == 1 { 1 }
}
mod m2 {
    fn bar() { let future = crate::m1::foo(); }
}
}
fn main() {}
