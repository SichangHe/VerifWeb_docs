use vstd::prelude::*;
verus! {
struct Guard<'a> { state: &'a mut u64 }
impl<'a> Drop for Guard<'a> {
    fn drop(&mut self)
        opens_invariants none
        no_unwind
    { *self.state = 0; }
}
}
fn main() {}
