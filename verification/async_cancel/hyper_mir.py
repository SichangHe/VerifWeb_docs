"""Extract Hyper #4040 cancellation hand-off facts from compiler MIR.

Each fact is a check over every normal-return path of one real generic function
in the crate MIR emitted by rustc. Unwind edges are out of scope.
"""

import re
import sys
from dataclasses import dataclass

from verification.async_cancel.mir_blocks import blocks

LOCAL = r"_\d+"


@dataclass
class Fn:
    """One MIR body: blocks plus the unique right-hand side of each local."""

    name: str
    graph: dict[str, list[str]]
    defs: dict[str, str]


def function(crate: str, signature: str) -> Fn | str:
    """Find exactly one function whose header matches the signature regex."""
    heads = [
        m for m in re.finditer(r"^fn (.*)\{$", crate, re.MULTILINE)
        if re.search(signature, m[1])
    ]
    if len(heads) != 1:
        return f"{len(heads)} functions match {signature!r}"
    start = heads[0].end()
    end = crate.index("\n}\n", start)
    text = crate[start : end + 1]
    graph = blocks(text + "    }\n" if not text.endswith("    }\n") else text)
    if isinstance(graph, str):
        return graph
    defs: dict[str, str] = {}
    for lines in graph.values():
        for line in lines:
            m = re.fullmatch(rf"({LOCAL}) = (.*?)(?:;| -> \[.*)", line)
            if m:
                if m[1] in defs and defs[m[1]] != m[2]:
                    defs[m[1]] = "<multiple>"
                else:
                    defs[m[1]] = m[2]
    return Fn(heads[0][1], graph, defs)


def successors(line: str) -> list[tuple[str | None, str]]:
    """Normal-control successors of a terminator, labelled by switch value."""
    if line in ("return;", "unreachable;", "resume;"):
        return []
    if line.startswith("goto -> "):
        return [(None, line.removeprefix("goto -> ").rstrip(";"))]
    if line.startswith("switchInt("):
        arms = line.split("-> [", 1)[1].rstrip("];")
        out = []
        for arm in arms.split(", "):
            label, target = arm.split(": ")
            out.append((label, target))
        return out
    m = re.search(r"-> \[return: (bb\d+)", line) or re.search(r"-> (bb\d+);$", line)
    if m:
        return [(None, m[1])]
    if "-> [return:" not in line and "->" in line:
        raise ValueError(f"unsupported terminator: {line}")
    return []


def paths(f: Fn, start: str, prefix: list[str] | None = None):
    """All normal paths from a block to `return`; fails on a cycle."""
    stack = [(start, [])]
    while stack:
        block, trail = stack.pop()
        if block in trail:
            raise ValueError(f"cycle at {block} in {f.name}")
        trail = trail + [block]
        lines = f.graph[block]
        succ = successors(lines[-1])
        if lines[-1] == "return;":
            yield (prefix or []) + [line for b in trail for line in f.graph[b]]
        if lines[-1] == "unreachable;":
            continue
        for _, target in succ:
            stack.append((target, trail))


def arm(f: Fn, scrutinee: str, value: str) -> str | None:
    """Block entered when `discriminant(scrutinee)` takes the given value."""
    for lines in f.graph.values():
        for i, line in enumerate(lines):
            m = re.fullmatch(rf"({LOCAL}) = discriminant\({re.escape(scrutinee)}\);", line)
            if m and lines[-1].startswith(f"switchInt(move {m[1]})"):
                return dict((k, t) for k, t in successors(lines[-1]))[value]
    return None


def def_of(f: Fn, local: str) -> str:
    return f.defs.get(local, "<none>")


def projected_self(f: Fn, place: str, field: int, ty: str) -> bool:
    """`place` is `&mut (P.field: ty)` or `copy (P.field: ty)` with P = project(copy _1)."""
    m = re.fullmatch(
        rf"(?:&mut|no_retag copy) \(({LOCAL})\.{field}: (.*)\)", place
    )
    return bool(
        m
        and ty in m[2]
        and re.fullmatch(r".*::project\(copy _1\)", def_of(f, m[1]))
    )


def calls_on_every_path(f: Fn, start: str, call: str, check) -> str | None:
    """Every path from start reaches a call matching `call` whose arg passes check."""
    for path in paths(f, start):
        ok = False
        for line in path:
            m = re.fullmatch(rf"{LOCAL} = {call}\((?:move|copy) ({LOCAL})(.*)\) -> \[.*", line)
            if m and check(m[1], m[2]):
                ok = True
                break
        if not ok:
            return f"{f.name}: a path from {start} returns without {call}"
    return None


def facts(crate: str) -> dict[str, bool | str]:
    """Return named facts; a string value records why a fact failed."""
    out: dict[str, bool | str] = {}

    def fn(sig):
        r = function(crate, sig)
        if isinstance(r, str):
            raise LookupError(r)
        return r

    # F1 SendWhen::poll: the poll_canceled Ready arm calls cancel on self.when.
    try:
        f = fn(r"dispatch\.rs.*::poll\(_1: Pin<&mut SendWhen<B, E>>")
        result = next(
            l for ls in f.graph.values() for l in ls
            if re.fullmatch(rf"{LOCAL} = Callback::<.*>::poll_canceled\(.*", l)
        ).split(" = ")[0]
        ready = arm(f, result, "0")

        def on_when(arg, rest):
            src = re.fullmatch(
                rf"Pin::<&mut ResponseFutMap<B, E>>::as_mut\(move ({LOCAL})\)", def_of(f, arg)
            )
            return bool(src and projected_self(f, def_of(f, src[1]), 0, "ResponseFutMap<B, E>"))

        out["send_cancels_when"] = (
            calls_on_every_path(f, ready, r"ResponseFutMap::<B, E>::cancel", on_when) or True
            if ready else "no poll_canceled Ready arm"
        )
    except (LookupError, StopIteration, ValueError) as e:
        out["send_cancels_when"] = str(e) or "poll_canceled not found"

    # F2 ResponseFutMap::cancel: take(self.cancel_tx); Some arm sends ().
    try:
        f = fn(r"::cancel\(_1: Pin<&mut ResponseFutMap<B, E>>\)")
        taken = next(
            l for ls in f.graph.values() for l in ls
            if re.fullmatch(rf"{LOCAL} = Option::<futures_channel::oneshot::Sender<\(\)>>::take\(copy {LOCAL}\) -> .*", l)
        )
        opt, ptr = re.fullmatch(rf"({LOCAL}) = .*take\(copy ({LOCAL})\).*", taken).groups()
        assert projected_self(f, def_of(f, ptr), 4, "Option<futures_channel::oneshot::Sender<()>>")
        some = arm(f, opt, "1")

        def is_tx(arg, rest):
            return (
                def_of(f, arg) == f"move (({opt} as Some).0: futures_channel::oneshot::Sender<()>)"
                and rest == ", const ()"
            )

        out["cancel_sends"] = (
            calls_on_every_path(f, some, r"futures_channel::oneshot::Sender::<\(\)>::send", is_tx)
            or True
        )
    except (LookupError, StopIteration, ValueError, AssertionError, TypeError) as e:
        out["cancel_sends"] = str(e) or "no take of cancel_tx field"

    # F3 PipeMap::poll: every path first polls self.cancel_rx; its Ready(Ok) arm resets self.pipe.
    try:
        f = fn(r"client\.rs.*::poll\(_1: Pin<&mut PipeMap<B>>")
        mapped = next(
            l for ls in f.graph.values() for l in ls
            if re.fullmatch(rf"{LOCAL} = Option::<&mut futures_channel::oneshot::Receiver<\(\)>>::map::<.*", l)
        )
        res, recv = re.fullmatch(rf"({LOCAL}) = .*\(move ({LOCAL}), move {LOCAL}\) -> .*", mapped).groups()
        src = re.fullmatch(rf"Option::<futures_channel::oneshot::Receiver<\(\)>>::as_mut\(copy ({LOCAL})\)", def_of(f, recv))
        assert src and projected_self(f, def_of(f, src[1]), 3, "Option<futures_channel::oneshot::Receiver<()>>")
        for p in paths(f, "bb0"):
            assert mapped in p, "a return path skips the cancel receiver poll"
        some = arm(f, res, "1")
        ready = arm(f, f"(({res} as Some).0: std::task::Poll<std::result::Result<(), futures_channel::oneshot::Canceled>>)", "0")
        ok = arm(f, f"(((({res} as Some).0: std::task::Poll<std::result::Result<(), futures_channel::oneshot::Canceled>>) as Ready).0: std::result::Result<(), futures_channel::oneshot::Canceled>)", "0")
        assert some and ready and ok, "receiver arms not found"

        def on_pipe(arg, rest):
            s = re.fullmatch(rf"Pin::<&mut PipeToSendStream<B>>::as_mut\(move ({LOCAL})\)", def_of(f, arg))
            return bool(s and projected_self(f, def_of(f, s[1]), 0, "PipeToSendStream<B>")
                        and rest == ", const h2::Reason::CANCEL")

        out["pipe_resets_on_cancel"] = (
            calls_on_every_path(f, ok, r"PipeToSendStream::<B>::send_reset", on_pipe) or True
        )
        closure = fn(r"client\.rs:481:57: 481:61\}, _2: &mut futures_channel::oneshot::Receiver<\(\)>\)")
        out["closure_polls_receiver"] = any(
            re.search(r"<futures_channel::oneshot::Receiver<\(\)> as Future>::poll\(", l)
            or re.search(r"<Pin<&mut futures_channel::oneshot::Receiver<\(\)>> as Future>::poll\(", l)
            for ls in closure.graph.values() for l in ls
        ) or "closure does not poll the receiver"
    except (LookupError, StopIteration, ValueError, AssertionError, TypeError) as e:
        out["pipe_resets_on_cancel"] = str(e) or "PipeMap has no cancel receiver"

    # F4 PipeToSendStream::send_reset resets its SendStream field.
    try:
        f = fn(r"mod\.rs.*::send_reset\(_1: Pin<&mut PipeToSendStream<S>>, _2: Reason\)")
        out["send_reset_reaches_h2"] = calls_on_every_path(
            f, "bb0", r"SendStream::<SendBuf<<S as Body>::Data>>::send_reset",
            lambda a, r: projected_self(f, def_of(f, a), 0, "h2::SendStream") and r == ", copy _2",
        ) or True
    except (LookupError, ValueError) as e:
        out["send_reset_reaches_h2"] = str(e)

    # F5 poll_pipe: spawned PipeMap owns the SendStream; its receiver pairs with the sender in ResponseFutMap.
    f = fn(r"::poll_pipe\(_1: &mut ClientTask<B, E, T>")
    lines = [l for ls in f.graph.values() for l in ls]
    pm = [l for l in lines if re.fullmatch(rf"{LOCAL} = PipeMap::<B> \{{.*", l)]
    out["pipe_holds_stream"] = False
    if len(pm) == 1:
        pipe = re.search(rf"pipe: move ({LOCAL})", pm[0])[1]
        origin = def_of(f, def_of(f, pipe).removeprefix("move "))
        out["pipe_holds_stream"] = bool(re.fullmatch(
            rf"PipeToSendStream::<B>::new\(move {LOCAL}, move ({LOCAL})\)", origin
        )) and any(
            re.fullmatch(rf"{LOCAL} = move \(_2\.3: h2::SendStream<.*>\);", l) for l in lines
        ) and any(re.search(r"H2ClientFuture::<B, T, E>::Pipe \{ pipe: (copy|move) " + pm[0].split(" = ")[0] + r" \}", l) for l in lines)

    def via_some(local, ty):
        """Follow `Some(move a)`, `a = move b`, `b = move (C.i)` back to the channel call."""
        d = re.fullmatch(rf"Option::<futures_channel::oneshot::{ty}<\(\)>>::Some\(move ({LOCAL})\)", def_of(f, local))
        if not d:
            return None
        x = d[1]
        while re.fullmatch(rf"move ({LOCAL})", def_of(f, x)):
            x = def_of(f, x).removeprefix("move ")
        m = re.fullmatch(rf"move \(({LOCAL})\.(\d): futures_channel::oneshot::{ty}<\(\)>\)", def_of(f, x))
        if m and def_of(f, m[1]) == "futures_channel::oneshot::channel::<()>()":
            return m[1], m[2]
        return None

    rfm = [l for l in lines if re.fullmatch(rf"{LOCAL} = ResponseFutMap::<B, E> \{{.*", l)]
    rx = re.search(rf"cancel_rx: move ({LOCAL})", pm[0]) if len(pm) == 1 else None
    tx = re.search(rf"cancel_tx: move ({LOCAL})", rfm[0]) if len(rfm) == 1 else None
    a = via_some(rx[1], "Receiver") if rx else None
    b = via_some(tx[1], "Sender") if tx else None
    out["channel_paired"] = bool(a and b and a[0] == b[0] and {a[1], b[1]} == {"0", "1"}) or (
        "no oneshot channel connects PipeMap.cancel_rx to ResponseFutMap.cancel_tx"
    )
    return out


def main(argv: list[str]) -> int:
    crate = open(argv[1]).read()
    result = facts(crate)
    for k, v in result.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
