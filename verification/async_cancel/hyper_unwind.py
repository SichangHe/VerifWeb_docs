"""Unwind coverage for the Hyper #4040 hand-off, from compiler MIR.

Complements hyper_mir.py (normal-return paths only). For each window in which
an unwind would break the hand-off, list every terminator with an unwind edge
inside it, and check what the receiving side does when the sender is dropped
unsent. See UNWIND.md for the trusted facts that turn these lists into claims.
"""

import re
import sys

from verification.async_cancel.hyper_mir import Fn, function
from verification.async_cancel.unwind_mir import edges


def window(f: Fn, start: str, stop: str, allow_return: bool = False) -> list[str] | str:
    """Terminators with an unwind or `unwind continue` edge on any normal path
    from block `start` until a terminator matching `stop` returns normally."""
    found: list[str] = []
    seen: set[str] = set()
    pending = [start]
    reached = False
    while pending:
        block = pending.pop()
        if block in seen:
            continue
        seen.add(block)
        terminal = f.graph[block][-1]
        out = edges(int(block[2:]), terminal)
        if any(e.kind in ("unwind", "resume") for e in out):
            found.append(f"{block}: {terminal}")
        if re.search(stop, terminal):
            reached = True
            continue
        for e in out:
            if e.kind == "normal" and e.target is not None:
                pending.append(f"bb{e.target}")
            elif e.kind == "return" and not allow_return:
                return f"a normal path from {start} returns before {stop!r}"
    return found if reached else f"{stop!r} not reached from {start}"


def arm_after(f: Fn, call: str, value: str) -> str | None:
    """Block entered when the discriminant of `call`'s result takes `value`."""
    result = None
    for lines in f.graph.values():
        for line in lines:
            if m := re.fullmatch(rf"(_\d+) = {call}.*", line):
                result = m[1]
    if result is None:
        return None
    for lines in f.graph.values():
        for line in lines:
            m = re.fullmatch(rf"(_\d+) = discriminant\({result}\);", line)
            if m and lines[-1].startswith(f"switchInt(move {m[1]})"):
                return dict(re.findall(r"(\w+): (bb\d+)", lines[-1]))[value]
    return None


def facts(crate: str) -> dict[str, object]:
    out: dict[str, object] = {}
    send_when = function(crate, r"dispatch\.rs.*::poll\(_1: Pin<&mut SendWhen<B, E>>")
    cancel = function(crate, r"::cancel\(_1: Pin<&mut ResponseFutMap<B, E>>\)")
    pipe = function(crate, r"client\.rs.*::poll\(_1: Pin<&mut PipeMap<B>>")
    if isinstance(send_when, str) or isinstance(cancel, str) or isinstance(pipe, str):
        out["applicable"] = "no cancel hand-off in this crate (parent): " + " / ".join(
            x for x in (send_when, cancel, pipe) if isinstance(x, str)
        )
        return out
    ready = arm_after(send_when, r"Callback::<.*>::poll_canceled\(", "0")
    out["U1 send_when: unwind points after detection, before cancel returns"] = (
        window(send_when, ready, r"= ResponseFutMap::<B, E>::cancel\(") if ready else "no Ready arm"
    )
    out["U2 cancel: unwind points before Sender::send returns"] = window(
        cancel, "bb0", r"= futures_channel::oneshot::Sender::<\(\)>::send\(", allow_return=True
    )  # the None arm (sender already taken) returns without sending
    # Locate the receiver result arms as hyper_mir.py does.
    mapped = next(
        x for ls in pipe.graph.values() for x in ls
        if re.fullmatch(r"_\d+ = Option::<&mut futures_channel::oneshot::Receiver<\(\)>>::map::<.*", x)
    )
    res = mapped.split(" = ")[0]
    inner = f"((({res} as Some).0: std::task::Poll<std::result::Result<(), futures_channel::oneshot::Canceled>>) as Ready).0: std::result::Result<(), futures_channel::oneshot::Canceled>)"
    arms: dict[str, str] = {}
    for lines in pipe.graph.values():
        for line in lines:
            m = re.fullmatch(r"(_\d+) = discriminant\(\(" + re.escape(inner) + r"\);", line)
            if m and lines[-1].startswith(f"switchInt(move {m[1]})"):
                arms = dict(re.findall(r"(\w+): (bb\d+)", lines[-1]))
    if "1" not in arms or "0" not in arms:
        out["U3"] = "receiver Ready(Ok)/Ready(Err) arms not found"
        return out
    # U3: on Ready(Err) (sender dropped unsent) no path resets the stream.
    resets = []
    seen: set[str] = set()
    pending = [arms["1"]]
    while pending:
        block = pending.pop()
        if block in seen:
            continue
        seen.add(block)
        terminal = pipe.graph[block][-1]
        if "PipeToSendStream::<B>::send_reset(" in terminal:
            resets.append(block)
        pending += [f"bb{e.target}" for e in edges(int(block[2:]), terminal) if e.kind == "normal" and e.target is not None]
    out["U3 pipe: sender dropped unsent (Ready(Err)) never reaches send_reset"] = not resets or f"reset at {resets}"
    out["U4 pipe: unwind points after Ready(Ok), before send_reset returns"] = window(
        pipe, arms["0"], r"= PipeToSendStream::<B>::send_reset\("
    )
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m verification.async_cancel.hyper_unwind HYPER.mir")
        return 2
    for key, value in facts(open(argv[1]).read()).items():
        if isinstance(value, list):
            print(f"{key}:")
            for v in value:
                print(f"  {v}")
        else:
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
