// appended to tokio/src/sync/tests/loom_mpsc.rs by semaphore.sh

/// A bounded sender's queued `reserve` is polled again while the receiver
/// frees two slots and then closes. With a `Sender` still alive, once the
/// channel is closed and drained, `recv()` must return `None`
/// (documented pattern of `Receiver::close`).
#[test]
fn close_after_repoll_recv_returns_none() {
    use std::future::Future;
    use std::task::{Context, Poll};
    loom::model(|| {
        let (tx, mut rx) = mpsc::channel::<i32>(2);
        tx.try_send(1).unwrap();
        tx.try_send(2).unwrap();
        let tx2 = tx.clone();
        let t = thread::spawn(move || {
            block_on(async move {
                let mut reserve = Box::pin(tx2.reserve());
                // first poll queues the waiter; the second races the receiver
                poll_fn(|cx| {
                    if reserve.as_mut().poll(cx).is_pending() {
                        let _ = reserve.as_mut().poll(cx);
                    }
                    Poll::Ready(())
                })
                .await;
                // dropping the future (or the permit it returned) gives slots back
            });
        });
        assert_eq!(rx.try_recv().unwrap(), 1);
        assert_eq!(rx.try_recv().unwrap(), 2);
        rx.close();
        t.join().unwrap();
        // `tx` is still alive; the channel is closed and empty
        let waker = futures::task::noop_waker();
        let mut cx = Context::from_waker(&waker);
        let mut recv = Box::pin(rx.recv());
        assert!(
            matches!(recv.as_mut().poll(&mut cx), Poll::Ready(None)),
            "recv() did not return None after close: slot permit leaked (capacity {} of {})",
            tx.capacity(),
            tx.max_capacity()
        );
        drop(tx);
    });
}
