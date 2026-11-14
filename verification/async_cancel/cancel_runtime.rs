use vstd::prelude::*;
use std::future::Future;

verus! {
// 🧑 "whether cancellation/drop-at-await is modeled"
pub async fn update<F: Future<Output = ()>>(state: &mut u64, wait: F)
    ensures *final(state) == 2,
{
    *state = 1;
    wait.await;
    *state = 2;
}
}

fn main() {
    let mut state = 0;
    {
        let mut future = Box::pin(update(&mut state, std::future::pending()));
        let mut context = std::task::Context::from_waker(std::task::Waker::noop());
        assert!(future.as_mut().poll(&mut context).is_pending());
    }
    println!("state after cancellation: {state}");
    assert_eq!(state, 1);
}
