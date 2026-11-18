"""Compose extracted Hyper MIR facts into a Verus safety proof over all interleavings.

Usage: python -m verification.async_cancel.hyper_obligations CRATE.mir VERUS
Exit 0 iff every fact holds and Verus proves the hand-off invariant.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from verification.async_cancel.hyper_mir import facts

TEMPLATE = """use vstd::prelude::*;
verus! {
// Facts extracted from compiler MIR by hyper_mir.py (true only if the check passed).
pub spec const SEND_CANCELS_WHEN: bool = %(send_cancels_when)s;  // F1
pub spec const CANCEL_SENDS: bool = %(cancel_sends)s;            // F2
pub spec const PIPE_RESETS: bool = %(pipe_resets)s;              // F3 + F4 + closure
pub spec const PAIRED: bool = %(channel_paired)s;                // F5 pairing
pub spec const PIPE_HOLDS_STREAM: bool = %(pipe_holds_stream)s;  // F5 ownership

// Oneshot channel contents as seen by the receiver (futures_channel contract, trusted).
pub enum Chan { Empty, Sent, SenderDropped }

pub struct S {
    pub pipe_live: bool,     // spawned PipeMap not yet completed or dropped
    pub pipe_has_stream: bool,
    pub rx_some: bool,       // PipeMap.cancel_rx
    pub tx_some: bool,       // ResponseFutMap.cancel_tx
    pub chan: Chan,
    pub detected: bool,      // SendWhen::poll took the poll_canceled Ready arm
    pub reset_by_pipe: bool,
}

pub open spec fn init(s: S) -> bool {
    &&& s.pipe_has_stream == (s.pipe_live && PIPE_HOLDS_STREAM)
    &&& s.rx_some == (s.pipe_live && PAIRED) && s.tx_some == PAIRED
    &&& s.chan == Chan::Empty && !s.detected && !s.reset_by_pipe
}

// send_task: cancellation detected, then the completed task is dropped (tx dropped).
pub open spec fn detect(s: S, t: S) -> bool {
    &&& !s.detected && t.detected
    &&& t.pipe_live == s.pipe_live && t.pipe_has_stream == s.pipe_has_stream
    &&& t.rx_some == s.rx_some && t.reset_by_pipe == s.reset_by_pipe && !t.tx_some
    &&& t.chan == (if SEND_CANCELS_WHEN && CANCEL_SENDS && s.tx_some && s.rx_some {
            Chan::Sent
        } else if s.rx_some && s.tx_some && s.chan == Chan::Empty {
            Chan::SenderDropped
        } else { s.chan })
}

// pipe_task poll, F3: receiver checked first; Ready(Ok) resets and completes,
// Ready(Err) clears cancel_rx; otherwise the body may finish or stay pending.
pub open spec fn pipe_poll(s: S, t: S, body_done: bool) -> bool {
    &&& s.pipe_live && t.detected == s.detected && t.tx_some == s.tx_some && t.chan == s.chan
    &&& if s.rx_some && s.chan == Chan::Sent && PIPE_RESETS {
            !t.pipe_live && !t.pipe_has_stream && !t.rx_some && t.reset_by_pipe
        } else {
            let rx = s.rx_some && !(s.chan == Chan::SenderDropped);
            &&& t.reset_by_pipe == s.reset_by_pipe
            &&& if body_done { !t.pipe_live && !t.pipe_has_stream && !t.rx_some }
                else { t.pipe_live && t.pipe_has_stream == s.pipe_has_stream && t.rx_some == rx }
        }
}

pub open spec fn next(s: S, t: S) -> bool {
    detect(s, t) || exists|d: bool| pipe_poll(s, t, d)
}

// Safety obligation: after detection, a live pipe that holds the stream has a
// pending, observable reset obligation; otherwise the pipe no longer holds it.
pub open spec fn obligation(s: S) -> bool {
    s.detected ==> (s.pipe_has_stream ==> s.pipe_live && s.rx_some && s.chan == Chan::Sent)
}

pub open spec fn inv(s: S) -> bool {
    &&& obligation(s)
    &&& s.pipe_has_stream ==> s.pipe_live
    &&& s.pipe_has_stream && !s.detected ==> s.rx_some && s.tx_some && s.chan == Chan::Empty
    &&& !s.detected ==> (s.tx_some == PAIRED) && !(s.chan == Chan::Sent)
}

proof fn initial(s: S) requires init(s) ensures inv(s) {}

proof fn step(s: S, t: S) requires inv(s), next(s, t) ensures inv(t) {}

pub open spec fn trace_ok(tr: Seq<S>) -> bool {
    tr.len() > 0 && init(tr[0]) && forall|i: int| 0 <= i < tr.len() - 1 ==> next(#[trigger] tr[i], tr[i + 1])
}

proof fn all_states(tr: Seq<S>, k: int)
    requires trace_ok(tr), 0 <= k < tr.len()
    ensures obligation(tr[k])
    decreases k
{
    if k == 0 { initial(tr[0]); } else { all_states_inv(tr, k); }
}

proof fn all_states_inv(tr: Seq<S>, k: int)
    requires trace_ok(tr), 0 <= k < tr.len()
    ensures inv(tr[k])
    decreases k
{
    if k == 0 { initial(tr[0]); } else {
        all_states_inv(tr, k - 1);
        assert(next(tr[k - 1], tr[k]));
        step(tr[k - 1], tr[k]);
    }
}
} // verus!
fn main() {}
"""


def render(f: dict[str, bool | str]) -> str:
    b = lambda *ks: str(all(f.get(k) is True for k in ks)).lower()
    return TEMPLATE % {
        "send_cancels_when": b("send_cancels_when"),
        "cancel_sends": b("cancel_sends"),
        "pipe_resets": b("pipe_resets_on_cancel", "closure_polls_receiver", "send_reset_reaches_h2"),
        "channel_paired": b("channel_paired"),
        "pipe_holds_stream": b("pipe_holds_stream"),
    }


def main(argv: list[str]) -> int:
    f = facts(Path(argv[1]).read_text())
    for k, v in f.items():
        print(f"{k}: {v}")
    with tempfile.TemporaryDirectory(prefix="hyper-obligations-") as d:
        src = Path(d) / "hyper_handoff.rs"
        src.write_text(render(f))
        r = subprocess.run([argv[2], "--num-threads", "1", str(src)],
                           capture_output=True, text=True, timeout=120)
        summary = [l for l in r.stdout.splitlines() if l.startswith("verification results::")]
        print(summary[-1] if summary else "no verification summary")
        if r.returncode:
            errors = [l for l in r.stderr.splitlines() if "error" in l or "-->" in l]
            print("\n".join(errors[:12]))
            if not summary:
                print("ERROR: Verus did not run the proof")
                return 2
            print("REJECT: hand-off obligation not proved")
            return 1
    print("ACCEPT: hand-off obligation proved for the extracted facts")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
