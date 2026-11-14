use vstd::prelude::*;
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};
verus! {
struct Ready;
impl Future for Ready {
    type Output = u64;
    fn poll(self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<u64> { Poll::Ready(7) }
}
impl vstd::future::FutureSpecImpl for Ready {
    open spec fn obeys_future_laws(&self) -> bool { true }
    #[verifier::prophetic]
    open spec fn view(&self) -> u64 { 7 }
}
async fn caller() { let r = Ready.await; assert(r == 7); }
}
fn main() {}
