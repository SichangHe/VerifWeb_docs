// appended to tokio/src/sync/tests/loom_semaphore_batch.rs by semaphore.sh

/// A queued waiter is polled again while its permit is assigned, a second
/// permit is released and the semaphore is closed. Every permit must be back
/// in the semaphore once the future is dropped.
#[test]
fn repoll_assign_close_conserves_permits() {
    loom::model(|| {
        let semaphore = Arc::new(Semaphore::new(0));
        let s2 = semaphore.clone();
        let t = thread::spawn(move || {
            block_on(async move {
                let mut acquire = Box::pin(s2.acquire(1));
                // first poll usually queues the waiter; a second poll races the releases and close
                let got = poll_fn(|cx| {
                    let r = match acquire.as_mut().poll(cx) {
                        Poll::Pending => acquire.as_mut().poll(cx),
                        r => r,
                    };
                    Poll::Ready(matches!(r, Poll::Ready(Ok(()))))
                })
                .await;
                drop(acquire);
                if got {
                    s2.release(1); // the caller owned the permit: give it back
                }
            })
        });
        semaphore.release(1);
        semaphore.release(1);
        semaphore.close();
        t.join().unwrap();
        assert_eq!(semaphore.available_permits(), 2, "permit leaked");
    });
}
