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
