# Upstream report drafts
(authored by agents unless marked 🧑)

Drafts for human review, 2026-11-19. Nothing here has been posted or sent. Each draft is the text to paste; the test code is copied from files in this directory.

## 1. Tokio issue: batch semaphore leaks a permit when `close` races a re-poll

Title: `Semaphore`: permit leaked when `close()` races a re-poll of a queued `acquire`; bounded `mpsc` `recv()` then never returns `None`

Version: master `fc0d151` (tokio 1.54.1).

In `Semaphore::poll_acquire` (`tokio/src/sync/batch_semaphore.rs`), a queued waiter that is polled again can take permits from the counter with the CAS, and only then lock the wait list (`else if lock.is_none() { break self.waiters.lock(); }`). If `close()` runs between the CAS and the lock, the function returns at

```rust
if waiters.closed {
    return Poll::Ready(Err(AcquireError::closed()));
}
```

The permits held in the local `acquired` are neither assigned to the waiter nor returned. `Acquire::drop` returns only `num_permits - state`, so they are lost.

Sequence (one waiter needing 1 permit, semaphore starts at 0): the waiter is polled and queued; it is polled again and reads `needed = 1`; `release(1)` assigns 1 permit to it; `release(1)` adds 1 to the counter; the re-poll's CAS takes that permit; `close()` runs; the re-poll returns `Err(closed)`; dropping the future returns 1 permit. Final available: 1, expected 2.

Effect on bounded `mpsc`: `Rx::recv` returns `None` only if `rx_closed && semaphore.is_idle()`. After the leak, `is_idle()` stays false, so `rx.close(); while let Some(_) = rx.recv().await {}` (the pattern documented on `Receiver::close`) does not end while a `Sender` is alive.

Reproduction: append to `tokio/src/sync/tests/loom_semaphore_batch.rs` and `tokio/src/sync/tests/loom_mpsc.rs`, then run

```
RUSTFLAGS="--cfg loom -C debug-assertions" LOOM_MAX_PREEMPTIONS=3 \
  cargo test --lib --release --features full -- \
  sync::tests::loom_semaphore_batch::repoll_assign_close_conserves_permits \
  sync::tests::loom_mpsc::close_after_repoll_recv_returns_none
```

Observed on master: both fail, with `permit leaked` and `recv() did not return None after close: slot permit leaked (capacity 1 of 2)`.

```rust

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
```

```rust

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
```

Possible fix (only checked with these loom tests and the existing `loom_semaphore_batch` and `loom_mpsc` tests, which pass with it): return the locally acquired permits before the early return.

```diff
diff --git a/tokio/src/sync/batch_semaphore.rs b/tokio/src/sync/batch_semaphore.rs
index a9262fa0..c47fdeff 100644
--- a/tokio/src/sync/batch_semaphore.rs
+++ b/tokio/src/sync/batch_semaphore.rs
@@ -516,6 +516,9 @@ impl Semaphore {
         };
 
         if waiters.closed {
+            if acquired > 0 {
+                self.permits.fetch_add(acquired << Self::PERMIT_SHIFT, Release);
+            }
             return Poll::Ready(Err(AcquireError::closed()));
         }
 
```

How it was found: a bounded model check that runs the compiled MIR of the semaphore on all interleavings of small scenarios. The trigger needs a second poll of a queued future before it is woken; how often real code does this was not measured.

## 2. Tokio PR description: loom test for `Notify` drop vs `notify_waiters` (#3652)

Title: `sync: add loom tests for dropping a Notified while notify_one and notify_waiters race`

This adds three loom tests to `tokio/src/sync/tests/loom_notify.rs`. They check that dropping a `Notified` never loses a `notify_one` permit while other threads call `notify_one` or `notify_waiters`.

Why: no existing loom test covers the #3652 bug on current code. We removed the #3652 guard from `drop_notified` on master `fc0d151` (the `if waiters.is_empty()` check before storing `EMPTY`). All 9 existing loom Notify tests still pass. `drop_vs_notify_waiters_and_one` fails with `permit lost`.

Results with `LOOM_MAX_PREEMPTIONS=2`:
- master: `test result: ok. 12 passed`
- master with the guard removed: `drop_vs_notify_waiters_and_one` fails; the other 11 pass

```diff
diff --git a/tokio/src/sync/tests/loom_notify.rs b/tokio/src/sync/tests/loom_notify.rs
index 081cfd21..b70488a3 100644
--- a/tokio/src/sync/tests/loom_notify.rs
+++ b/tokio/src/sync/tests/loom_notify.rs
@@ -328,3 +328,88 @@ fn notify_waiters_sequential_notified_await() {
         receiver.join().unwrap();
     });
 }
+
+/// A `notify_one` permit must
+/// survive dropping a `Notified` that received it, while other threads race
+/// on the lock-free paths of `Notify`.
+mod drop_forward_race {
+    use crate::sync::Notify;
+    use std::sync::Arc;
+    use loom::thread;
+    use std::future::Future;
+    use std::pin::Pin;
+    use std::task::{Context, Poll};
+
+    fn poll_once<F: Future>(f: Pin<&mut F>) -> Poll<F::Output> {
+        let waker = futures::task::noop_waker();
+        f.poll(&mut Context::from_waker(&waker))
+    }
+
+    /// Two notify_one calls, one dropped waiter, nobody consumes: a permit
+    /// must remain.
+    #[test]
+    fn drop_vs_notify_one() {
+        loom::model(|| {
+            let notify = Arc::new(Notify::new());
+            let mut f1 = Box::pin(notify.clone().notified_owned());
+            assert!(poll_once(f1.as_mut()).is_pending());
+            let (n1, n2) = (notify.clone(), notify.clone());
+            let a = thread::spawn(move || n1.notify_one());
+            let b = thread::spawn(move || n2.notify_one());
+            let c = thread::spawn(move || drop(f1));
+            a.join().unwrap();
+            b.join().unwrap();
+            c.join().unwrap();
+            let mut f = Box::pin(notify.notified());
+            assert!(poll_once(f.as_mut()).is_ready(), "permit lost");
+        });
+    }
+
+    /// One notify_one, one dropped waiter, one racing consumer polled once:
+    /// the consumer either completed, or completes on its next poll.
+    #[test]
+    fn drop_vs_consumer() {
+        loom::model(|| {
+            let notify = Arc::new(Notify::new());
+            let mut f1 = Box::pin(notify.clone().notified_owned());
+            assert!(poll_once(f1.as_mut()).is_pending());
+            let n1 = notify.clone();
+            let n2 = notify.clone();
+            let a = thread::spawn(move || n1.notify_one());
+            let c = thread::spawn(move || drop(f1));
+            let d = thread::spawn(move || {
+                let mut f2 = Box::pin(n2.notified_owned());
+                if poll_once(f2.as_mut()).is_pending() {
+                    Some(f2)
+                } else {
+                    None
+                }
+            });
+            a.join().unwrap();
+            c.join().unwrap();
+            if let Some(mut f2) = d.join().unwrap() {
+                assert!(poll_once(f2.as_mut()).is_ready(), "permit lost");
+            }
+        });
+    }
+
+    /// The tokio#3652 shape with racing threads: notify_waiters, notify_one
+    /// and drop of the waiter. A fresh future must then find the permit.
+    #[test]
+    fn drop_vs_notify_waiters_and_one() {
+        loom::model(|| {
+            let notify = Arc::new(Notify::new());
+            let mut f1 = Box::pin(notify.clone().notified_owned());
+            assert!(poll_once(f1.as_mut()).is_pending());
+            let (n1, n2) = (notify.clone(), notify.clone());
+            let a = thread::spawn(move || n1.notify_waiters());
+            let b = thread::spawn(move || n2.notify_one());
+            let c = thread::spawn(move || drop(f1));
+            a.join().unwrap();
+            b.join().unwrap();
+            c.join().unwrap();
+            let mut f = Box::pin(notify.notified());
+            assert!(poll_once(f.as_mut()).is_ready(), "permit lost");
+        });
+    }
+}
```

## 3. Pingora PR #1037 comment: bug still present on master

The bug this PR fixes is still on master. At `3f87e92` (2026-11-09), `pingora-memory-cache/src/read_through.rs` is byte-identical to this PR's base `4487f7b`.

I added only this PR's regression test to master and ran `cargo test -p pingora-memory-cache test_cancelled_writer_does_not_block_later_readers`. Result: `RTCache::get() is stuck: stale CacheLock left in lockers after writer cancellation`, `test result: FAILED. 0 passed; 1 failed`. With the PR applied, the test passes.

So on master, if a `get()` task holding the cache lock is cancelled during `lookup()`, every later `get()` of that key blocks.

Test (from this PR, added to `mod tests` in `read_through.rs`):

```rust
    // Issue #931: a cancelled writer leaves its CacheLock behind in `lockers` with zero
    // permits, so every later request for the same key blocks forever.
    static LOOKUP_CALLS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    static LOOKUP_ENTERED: once_cell::sync::Lazy<tokio::sync::Notify> =
        once_cell::sync::Lazy::new(tokio::sync::Notify::new);

    struct HangingLookup;

    #[async_trait]
    impl Lookup<i32, i32, ()> for HangingLookup {
        async fn lookup(
            _key: &i32,
            _extra: Option<&()>,
        ) -> Result<(i32, Option<Duration>), Box<dyn ErrorTrait + Send + Sync>> {
            if std::sync::atomic::AtomicUsize::fetch_add(
                &LOOKUP_CALLS,
                1,
                std::sync::atomic::Ordering::SeqCst,
            ) == 0
            {
                /* the writer's lookup never completes on its own */
                LOOKUP_ENTERED.notify_one();
                std::future::pending::<()>().await;
            }
            Ok((1, None))
        }
    }
    #[tokio::test]
    async fn test_cancelled_writer_does_not_block_later_readers() {
        let cache: RTCache<i32, i32, HangingLookup, ()> = RTCache::new(10, None, None);
        let cache = Arc::new(cache);

        let cache_c = cache.clone();
        let writer = tokio::spawn(async move { cache_c.get(&1, None, None).await });

        /* wait until the writer is inside lookup(), so its lock is registered */
        LOOKUP_ENTERED.notified().await;

        /* cancel the writer while its lookup is still awaiting */
        writer.abort();
        let _ = writer.await;

        /* a later request for the same key must still make progress */
        let later = tokio::time::timeout(Duration::from_secs(5), cache.get(&1, None, None)).await;
        assert!(
            later.is_ok(),
            "RTCache::get() is stuck: stale CacheLock left in lockers after writer cancellation"
        );
        assert_eq!(later.unwrap().1, CacheStatus::Miss);
    }
```

## 4. Hyper issue: panicking tracing subscriber loses the HTTP/2 reset of a cancelled request

Title: `client/h2: if a tracing subscriber panics on "send_when canceled", RST_STREAM is never sent`

Version: master `21da6a59`, features `full,tracing`, `--cfg hyper_unstable_tracing`.

`SendWhen::poll` (`src/client/dispatch.rs:370`) emits `trace!("send_when canceled")` before `this.when.as_mut().cancel()`. If the tracing subscriber panics on that event, the cancel signal is never sent, and the server never gets RST_STREAM for the dropped request. This is the case fixed by #4040, but on the panic path.

Severity is low: it needs a subscriber that panics. Tokio fixed a similar issue for its semaphore in #8542. A possible fix is to send the cancel before emitting the event.

Reproduction: save as `tests/h2_unwind_gap.rs` and run

```
RUSTFLAGS='--cfg hyper_unstable_tracing' cargo test --features full,tracing \
  --test h2_unwind_gap -- --test-threads=1
```

Observed on master: `test result: ok. 2 passed`. The control test gets RST_STREAM. In `panic_after_detection_loses_rst`, the subscriber panics and no RST_STREAM arrives within 2 s.

```rust
// Test-only harness for the unwind gap in Hyper fix 5b17a69 (issue #4040).
// Copied into hyper's tests/ by unwind_gap.sh; needs `--features full,tracing`
// and RUSTFLAGS='--cfg hyper_unstable_tracing'.
//
// Trigger: a user-installed tracing Subscriber that panics on the event
// `trace!("send_when canceled")`, which SendWhen::poll emits after
// poll_canceled returned Ready and before ResponseFutMap::cancel sends on
// cancel_tx. No hyper source is patched.
#![deny(warnings)]

use std::future::poll_fn;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use bytes::Bytes;
use http_body_util::Full;
use hyper::client::conn;
use hyper::Request;
use tokio::sync::oneshot;

#[path = "support/mod.rs"]
#[allow(dead_code, unused_imports)]
mod support;
use support::{TokioExecutor, TokioIo};

static PANICKED: AtomicBool = AtomicBool::new(false);

struct PanicOn {
    armed: bool,
}

struct Msg(String);
impl tracing::field::Visit for Msg {
    fn record_debug(&mut self, f: &tracing::field::Field, v: &dyn std::fmt::Debug) {
        if f.name() == "message" {
            self.0 = format!("{:?}", v);
        }
    }
}

impl tracing::Subscriber for PanicOn {
    fn enabled(&self, _: &tracing::Metadata<'_>) -> bool {
        true
    }
    fn new_span(&self, _: &tracing::span::Attributes<'_>) -> tracing::span::Id {
        tracing::span::Id::from_u64(1)
    }
    fn record(&self, _: &tracing::span::Id, _: &tracing::span::Record<'_>) {}
    fn record_follows_from(&self, _: &tracing::span::Id, _: &tracing::span::Id) {}
    fn event(&self, e: &tracing::Event<'_>) {
        let mut m = Msg(String::new());
        e.record(&mut m);
        if self.armed && m.0 == "send_when canceled" {
            PANICKED.store(true, Ordering::SeqCst);
            panic!("user subscriber panics on send_when canceled");
        }
    }
    fn enter(&self, _: &tracing::span::Id) {}
    fn exit(&self, _: &tracing::span::Id) {}
}

// Same scenario as hyper's own regression h2_pipe_task_cancelled_on_response_future_drop.
async fn server_got_rst() -> bool {
    let (client_io, server_io) = tokio::io::duplex(1024);
    let (rst_tx, rst_rx) = oneshot::channel::<bool>();

    tokio::spawn(async move {
        let mut builder = h2::server::Builder::new();
        builder.initial_window_size(0);
        let mut h2 = builder.handshake::<_, Bytes>(server_io).await.unwrap();
        let (req, _respond) = h2.accept().await.unwrap().unwrap();
        tokio::spawn(async move {
            let _ = poll_fn(|cx| h2.poll_closed(cx)).await;
        });
        let mut body = req.into_body();
        let got_rst = tokio::time::timeout(Duration::from_secs(2), body.data())
            .await
            .map_or(false, |frame| matches!(frame, Some(Err(_)) | None));
        let _ = rst_tx.send(got_rst);
    });

    let (mut client, conn) = conn::http2::Builder::new(TokioExecutor)
        .handshake::<_, Full<Bytes>>(TokioIo::new(client_io))
        .await
        .expect("http handshake");
    tokio::spawn(async move {
        let _ = conn.await;
    });
    let req = Request::post("http://localhost/")
        .body(Full::new(Bytes::from(vec![b'x'; 50])))
        .unwrap();
    let res = tokio::time::timeout(Duration::from_millis(5), client.send_request(req)).await;
    assert!(res.is_err(), "should timeout waiting for response");
    rst_rx.await.expect("server task should complete")
}

// Control: subscriber installed but never panics; the fix sends RST_STREAM.
#[tokio::test]
async fn control_no_panic_server_gets_rst() {
    let _g = tracing::subscriber::set_default(PanicOn { armed: false });
    assert!(server_got_rst().await, "server should receive RST_STREAM");
}

// Gap: the subscriber panics in send_task between detection and Sender::send.
#[tokio::test]
async fn panic_after_detection_loses_rst() {
    let _g = tracing::subscriber::set_default(PanicOn { armed: true });
    let got = server_got_rst().await;
    assert!(PANICKED.load(Ordering::SeqCst), "trigger did not fire");
    assert!(!got, "gap refuted: server received RST_STREAM despite unwind");
}
```
