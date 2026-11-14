use vstd::prelude::*;
verus! {
struct Guard;
impl Drop for Guard {
    fn drop(&mut self)
        no_unwind
    { }
}
}
fn main() {}
