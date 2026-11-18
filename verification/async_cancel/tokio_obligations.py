"""Compose extracted Tokio `Notify` MIR facts into a Verus permit-preservation proof.

Usage: python -m verification.async_cancel.tokio_obligations CRATE.mir VERUS
Exit 0 iff every fact holds and Verus proves that dropping a `Notified`
future never loses a pending `notify_one` permit.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from verification.async_cancel.tokio_mir import facts

TEMPLATE = """use vstd::prelude::*;
verus! {
// Facts extracted from compiler MIR by tokio_mir.py (true only if the check passed).
pub spec const ACTS_WAITING: bool = %(acts_waiting)s;    // D1: drop acts only in State::Waiting
pub spec const GUARDED: bool = %(guarded)s;              // D2: store only if list empty and loaded state WAITING
pub spec const STORES_EMPTY: bool = %(stores_empty)s;    // D3: the stored value is EMPTY
pub spec const FORWARDS: bool = %(forwards)s;            // D4: OneWaiter drop calls notify_locked(state, notify_state)
pub spec const LOCKED_OK: bool = %(locked_ok)s;          // N1 + N2: notify_locked semantics

// Notify.state low bits: 0 EMPTY, 1 WAITING, 2 NOTIFIED. Counts of Notified futures
// in State::Waiting: still listed (notified None), removed with OneWaiter or AllWaiters.
pub struct S { pub st: int, pub list: int, pub one: int, pub all: int }

pub open spec fn init(s: S) -> bool { s.st == 0 && s.list == 0 && s.one == 0 && s.all == 0 }

// A notify_one permit is pending: stored in the state, or assigned to a future.
pub open spec fn permit(s: S) -> bool { s.st == 2 || s.one > 0 }

pub open spec fn inv(s: S) -> bool {
    &&& 0 <= s.st <= 2 && s.list >= 0 && s.one >= 0 && s.all >= 0
    &&& (s.st == 1) == (s.list > 0)
}

// notify_locked(waiters, state, curr) under the lock (N1, N2).
pub open spec fn locked(s: S, curr: int, t: S) -> bool {
    if !LOCKED_OK { true }
    else if curr == 1 {
        s.list > 0 && t.list == s.list - 1 && t.one == s.one + 1 && t.all == s.all
            && t.st == (if t.list == 0 { 0 } else { s.st })
    } else {
        t.st == 2 && t.list == s.list && t.one == s.one && t.all == s.all
    }
}

// Drop's store (D2, D3): `loaded` is the state read under the lock.
pub open spec fn after_store(s: S, loaded: int, m: S) -> bool {
    &&& m.list == s.list && m.one == s.one && m.all == s.all
    &&& if s.list == 0 && (!GUARDED || loaded == 1) {
            if STORES_EMPTY { m.st == 0 } else { 0 <= m.st <= 2 }
        } else { m.st == s.st }
}

pub enum Step { NotifyOne, NotifyWaiters, PollInit, PollWake, DropListed, DropOne, DropAll, DropIdle }

pub open spec fn step(s: S, t: S, k: Step) -> bool {
    match k {
        Step::NotifyOne => if s.st != 1 { t == S { st: 2, ..s } } else { locked(s, s.st, t) },
        Step::NotifyWaiters => if s.st == 1 {
            t == S { st: 0, list: 0, all: s.all + s.list, ..s } } else { t == s },
        Step::PollInit => if s.st == 2 { t == S { st: 0, ..s } }
            else { t == S { st: 1, list: s.list + 1, ..s } },
        Step::PollWake => (s.one > 0 && t == S { one: s.one - 1, ..s })
            || (s.all > 0 && t == S { all: s.all - 1, ..s }),
        // Cancellation: a Waiting future is dropped. Its entry is removed first.
        Step::DropListed => s.list > 0 && (!ACTS_WAITING || {
            let r = S { list: s.list - 1, ..s };
            after_store(r, s.st, t) }),
        Step::DropOne => s.one > 0 && (!ACTS_WAITING || exists|m: S| {
            #[trigger] after_store(S { one: s.one - 1, ..s }, s.st, m) &&
            // drop passes its notify_state local: the stored EMPTY if it stored, else the load
            if FORWARDS { locked(m, m.st, t) } else { t == m } }),
        Step::DropAll => s.all > 0 && (!ACTS_WAITING || {
            let r = S { all: s.all - 1, ..s };
            after_store(r, s.st, t) }),
        // Drop of a future in Init or Done: D1 says nothing happens.
        Step::DropIdle => ACTS_WAITING ==> t == s,
    }
}

pub open spec fn is_drop(k: Step) -> bool {
    k is DropListed || k is DropOne || k is DropAll || k is DropIdle
}

proof fn preserves(s: S, t: S, k: Step) requires inv(s), step(s, t, k) ensures inv(t) {
    if k is DropOne {
        let m = choose|m: S| after_store(S { one: s.one - 1, ..s }, s.st, m) &&
            if FORWARDS { locked(m, m.st, t) } else { t == m };
    }
}

// Obligation: dropping a Notified future never loses a pending notify_one permit.
proof fn drop_keeps_permit(s: S, t: S, k: Step)
    requires inv(s), step(s, t, k), is_drop(k), permit(s)
    ensures permit(t)
{
    if k is DropOne {
        let m = choose|m: S| after_store(S { one: s.one - 1, ..s }, s.st, m) &&
            if FORWARDS { locked(m, m.st, t) } else { t == m };
    }
}

pub open spec fn trace_ok(tr: Seq<S>, ks: Seq<Step>) -> bool {
    &&& tr.len() > 0 && ks.len() == tr.len() - 1 && init(tr[0])
    &&& forall|i: int| 0 <= i < ks.len() ==> step(#[trigger] tr[i], tr[i + 1], ks[i])
}

proof fn reach(tr: Seq<S>, ks: Seq<Step>, k: int)
    requires trace_ok(tr, ks), 0 <= k < tr.len()
    ensures inv(tr[k])
    decreases k
{
    if k > 0 {
        reach(tr, ks, k - 1);
        assert(step(tr[k - 1], tr[k], ks[k - 1]));
        preserves(tr[k - 1], tr[k], ks[k - 1]);
    }
}

proof fn every_drop_in_every_trace(tr: Seq<S>, ks: Seq<Step>, i: int)
    requires trace_ok(tr, ks), 0 <= i < ks.len(), is_drop(ks[i]), permit(tr[i])
    ensures permit(tr[i + 1])
{
    reach(tr, ks, i);
    assert(step(tr[i], tr[i + 1], ks[i]));
    drop_keeps_permit(tr[i], tr[i + 1], ks[i]);
}
} // verus!
fn main() {}
"""


def render(f: dict[str, bool | str]) -> str:
    b = lambda *ks: str(all(f.get(k) is True for k in ks)).lower()
    return TEMPLATE % {
        "acts_waiting": b("drop_acts_only_when_waiting"),
        "guarded": b("drop_store_guarded"),
        "stores_empty": b("drop_stores_empty"),
        "forwards": b("drop_forwards_one"),
        "locked_ok": b("locked_sets_notified", "locked_hands_one"),
    }


def main(argv: list[str]) -> int:
    f = facts(Path(argv[1]).read_text())
    for k, v in f.items():
        print(f"{k}: {v}")
    with tempfile.TemporaryDirectory(prefix="tokio-obligations-") as d:
        src = Path(d) / "tokio_notify.rs"
        src.write_text(render(f))
        r = subprocess.run([argv[2], "--num-threads", "1", str(src)],
                           capture_output=True, text=True, timeout=120)
        summary = [l for l in r.stdout.splitlines() if l.startswith("verification results::")]
        print(summary[-1] if summary else "no verification summary")
        if r.returncode:
            errors = [l for l in (r.stderr + r.stdout).splitlines() if "error" in l or "-->" in l]
            print("\n".join(errors[:12]))
            if not summary:
                print("ERROR: Verus did not run the proof")
                return 2
            print("REJECT: permit-preservation obligation not proved")
            return 1
    print("ACCEPT: dropping a Notified never loses a notify_one permit, for the extracted facts")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
