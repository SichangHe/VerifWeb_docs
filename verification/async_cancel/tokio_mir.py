"""Extract Tokio #3652 `Notified` drop facts from compiler MIR.

Each fact is checked on every normal-return path of one real function in the
crate MIR emitted by rustc, tracking local assignments along the path.
Unwind and panic edges are out of scope.

Usage: python -m verification.async_cancel.tokio_mir CRATE.mir
"""

import re
import sys

from verification.async_cancel.hyper_mir import LOCAL, Fn, function

STATE = "sync::notify::"
ATOMIC = r"Atomic::<usize>::"


def successors(line: str) -> list[tuple[str | None, str]]:
    """Normal successors labelled by switch value; diverging calls have none."""
    if line in ("return;", "unreachable;", "resume;"):
        return []
    if line.startswith("goto -> "):
        return [(None, line.removeprefix("goto -> ").rstrip(";"))]
    if line.startswith("switchInt("):
        arms = line.split("-> [", 1)[1].rstrip("];")
        return [tuple(a.split(": ")) for a in arms.split(", ")]
    m = re.search(r"-> \[(?:return|success): (bb\d+)", line) or re.search(r"-> (bb\d+);$", line)
    if m:
        return [(None, m[1])]
    if re.search(r"-> unwind (continue|unreachable);$", line):
        return []  # call that never returns normally, e.g. panic
    raise ValueError(f"unsupported terminator: {line}")


def paths(f: Fn, start: str = "bb0"):
    """All acyclic normal paths from start to `return`, as (block, arm taken) steps."""
    stack = [(start, [])]
    while stack:
        block, trail = stack.pop()
        if block in [b for b, _ in trail]:
            raise ValueError(f"cycle at {block} in {f.name}")
        last = f.graph[block][-1]
        if last == "return;":
            yield trail + [(block, None)]
        for label, target in successors(last):
            stack.append((target, trail + [(block, label)]))


class Walk:
    """Replay a path, keeping each local's latest right-hand side."""

    def __init__(self, f: Fn, path):
        self.f, self.path, self.env = f, path, {}

    def events(self):
        """Yield (line, arm label of this block's terminator) after updating env."""
        for block, label in self.path:
            for line in self.f.graph[block]:
                m = re.fullmatch(rf"({LOCAL}) = (.*?)(?: -> \[.*|;)", line)
                yield line, label
                if m:
                    self.env[m[1]] = m[2]

    def resolve(self, x: str) -> str:
        """Follow `copy _k`/`move _k` chains to the defining right-hand side."""
        x = re.sub(r"^(copy|move) ", "", x)
        seen = set()
        while x in self.env and x not in seen:
            seen.add(x)
            rhs = self.env[x]
            m = re.fullmatch(rf"(?:copy|move) ({LOCAL})", rhs)
            if not m:
                return rhs
            x = m[1]
        return x


def call_args(line: str, callee: str) -> list[str] | None:
    m = re.fullmatch(rf"{LOCAL} = {callee}\((.*)\) -> .*", line)
    return [a.strip() for a in m[1].split(", ")] if m else None


def switch_on(line: str) -> str | None:
    m = re.fullmatch(rf"switchInt\((?:move|copy) ({LOCAL})\) -> .*", line)
    return m[1] if m else None


def is_state_field(walk: Walk, arg: str, param: str | None = None) -> bool:
    """`arg` derefs `&((*N).0: AtomicUsize)` (N the Notify reference), or the
    `&AtomicUsize` parameter `param` when given."""
    d = walk.resolve(arg)
    m = re.fullmatch(rf"<AtomicUsize as Deref>::deref\((?:move|copy) ({LOCAL})\)", d)
    if not m:
        return False
    return m[1] == param if param else is_state_ref(walk, m[1])


def is_state_ref(walk: Walk, arg: str) -> bool:
    return bool(re.fullmatch(
        rf"&\(\(\*({LOCAL})\)\.0: loom::std::atomic_usize::AtomicUsize\)", walk.resolve(arg)
    ))


def drop_facts(f: Fn) -> dict[str, bool | str]:
    """Facts D1-D4 on `<Notified as Drop>::drop`."""
    out = {"drop_acts_only_when_waiting": True, "drop_store_guarded": True,
           "drop_stores_empty": True, "drop_forwards_one": True}
    bad = lambda k, why: out.__setitem__(k, out[k] if out[k] is not True else why)
    n_paths = 0
    for p in paths(f):
        n_paths += 1
        w = Walk(f, p)
        loaded = None          # local holding notify.state.load(SeqCst)
        took = set()           # facts about branches taken so far on this path
        waiting_arm = False
        for line, label in w.events():
            s = switch_on(line)
            if s:
                d = w.resolve(s)
                if d == "discriminant((*_3))" and label == "1":
                    waiting_arm = True
                if re.fullmatch(r"util::linked_list::.*::is_empty\(.*\)", d) and label == "otherwise":
                    took.add("empty")
                g = re.fullmatch(r"get_state\((?:copy|move) (_\d+)\)", d)
                if g and loaded and w.resolve(g[1]) == loaded_def and label == "1":
                    took.add("waiting")
                opt = took_opt(took)
                if opt and d == f"discriminant({opt})":
                    took.add(f"opt{label}")
                if opt and d == f"discriminant((({opt} as Some).0: {STATE}NotificationType))":
                    took.add(f"kind{label}")
            if (a := call_args(line, ATOMIC + "load")) and is_state_field(w, a[0]):
                if not waiting_arm:
                    bad("drop_acts_only_when_waiting", "lock/load outside the Waiting arm")
                loaded = line.split(" = ")[0]
                loaded_def = line.split(" = ", 1)[1].split(" -> ")[0]
            m = re.fullmatch(rf"({LOCAL}) = copy \(\(\*({LOCAL})\)\.2: std::option::Option<{STATE}NotificationType>\);", line)
            if m and re.fullmatch(r"std::cell::UnsafeCell::<notify::Waiter>::get\(copy _4\)", w.resolve(m[2])):
                took.add(f"optlocal:{m[1]}")
            if (a := call_args(line, ATOMIC + "store")) and is_state_field(w, a[0]):
                if not {"empty", "waiting"} <= took:
                    bad("drop_store_guarded", "a path stores notify.state without both "
                        "list-empty and loaded-state-WAITING branches")
                v = w.resolve(a[1])
                if not re.fullmatch(rf"set_state\(move _\d+, const {STATE}EMPTY\)", v):
                    bad("drop_stores_empty", f"stored value {v}")
            if (a := call_args(line, "notify_locked")):
                ok = (len(a) == 3 and is_state_ref(w, a[1]) and loaded
                      and w.resolve(a[2]) == w.resolve(loaded))
                if not ok:
                    bad("drop_forwards_one", f"notify_locked arguments {a}")
                took.add("forwarded")
        if {"opt1", "kind1"} <= took and "forwarded" not in took:
            bad("drop_forwards_one", "a OneWaiter path returns without notify_locked")
        if not waiting_arm and loaded:
            bad("drop_acts_only_when_waiting", "non-Waiting path touches state")
    if n_paths == 0:
        return {k: "no return path" for k in out}
    if not any_forward_arm(f):
        out["drop_forwards_one"] = "no OneWaiter arm found"
    return out


def took_opt(took: set[str]) -> str | None:
    return next((t.split(":")[1] for t in took if t.startswith("optlocal:")), None)


def any_forward_arm(f: Fn) -> bool:
    return any("notify_locked(" in l for ls in f.graph.values() for l in ls)


def locked_facts(f: Fn) -> dict[str, bool | str]:
    """Facts N1-N2 on `notify_locked(waiters, state, curr)`."""
    out = {"locked_sets_notified": True, "locked_hands_one": True}
    bad = lambda k, why: out.__setitem__(k, out[k] if out[k] is not True else why)
    seen = {"0": 0, "1": 0, "2": 0}
    for p in paths(f):
        w = Walk(f, p)
        arm = None
        cas = cas_ok = None
        notified = stored_notified = popped = handed = empty = False
        for line, label in w.events():
            s = switch_on(line)
            if s and arm is None and w.resolve(s) == "get_state(copy _3)":
                arm = label
                seen[label] = seen.get(label, 0) + 1
            elif s and cas and w.resolve(s) == f"discriminant({cas})":
                cas_ok = label == "0"
            elif s and re.fullmatch(r"util::linked_list::.*::is_empty\(.*\)", w.resolve(s)):
                empty = label == "otherwise"
            if (a := call_args(line, ATOMIC + "compare_exchange")) and is_state_field(w, a[0], "_2"):
                notified = a[1] == "copy _3" and w.resolve(a[2]) == f"set_state(copy _3, const {STATE}NOTIFIED)"
                cas = line.split(" = ")[0]
            if (a := call_args(line, ATOMIC + "store")) and is_state_field(w, a[0], "_2"):
                v = w.resolve(a[1])
                stored_notified = bool(re.fullmatch(rf"set_state\(copy _\d+, const {STATE}NOTIFIED\)", v))
                if arm == "1" and not (empty and v == f"set_state(copy _3, const {STATE}EMPTY)"):
                    bad("locked_hands_one", f"WAITING arm stores {v} (list empty: {empty})")
            if re.fullmatch(rf"{LOCAL} = util::linked_list::.*::pop_back\(copy _1\) -> .*", line):
                popped = True
            m = re.fullmatch(rf"\(\(\*({LOCAL})\)\.2: std::option::Option<{STATE}NotificationType>\) = move ({LOCAL});", line)
            if m and popped and one_waiter(w, m[2]):
                handed = re.fullmatch(r"NonNull::<notify::Waiter>::as_mut::<'_>\(move _\d+\)", w.resolve(m[1])) is not None
        if arm in ("0", "2") and not (notified and (cas_ok or stored_notified)):
            bad("locked_sets_notified", "an EMPTY/NOTIFIED path returns without leaving NOTIFIED")
        if arm == "1" and not handed:
            bad("locked_hands_one", "a WAITING path returns without marking a popped waiter OneWaiter")
    if not seen["1"]:
        out["locked_hands_one"] = "no WAITING arm"
    if not (seen["0"] and seen["2"]):
        out["locked_sets_notified"] = "no EMPTY/NOTIFIED arm"
    return out


def one_waiter(w: Walk, opt_local: str) -> bool:
    """`opt_local` holds `Some(NotificationType::OneWaiter)`."""
    m = re.fullmatch(rf"Option::<NotificationType>::Some\(move ({LOCAL})\)", w.resolve(opt_local))
    return bool(m) and w.resolve(m[1]) == "NotificationType::OneWaiter"


def facts(crate: str) -> dict[str, bool | str]:
    out: dict[str, bool | str] = {}
    for sig, get in (
        (r"^notify::<impl at tokio/src/sync/notify\.rs:\d+:1: \d+:\d+>::drop\(_1: &mut notify::Notified<'_>\)", drop_facts),
        (r"^notify_locked\(_1: &mut util::linked_list::LinkedList<notify::Waiter, notify::Waiter>, _2: &AtomicUsize, _3: usize\)", locked_facts),
    ):
        f = function(crate, sig)
        if isinstance(f, str):
            out[get.__name__] = f
            continue
        try:
            out.update(get(f))
        except ValueError as e:
            out[get.__name__] = str(e)
    return out


def main(argv: list[str]) -> int:
    result = facts(open(argv[1]).read())
    for k, v in result.items():
        print(f"{k}: {v}")
    return 0 if all(v is True for v in result.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
