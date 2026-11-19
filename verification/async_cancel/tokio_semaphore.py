"""Check Tokio's batch semaphore for lost permits by interpreting its real MIR.

The compiled bodies of `Acquire::poll`, `Acquire::project`,
`Semaphore::poll_acquire`, `Waiter::assign_permits`,
`Semaphore::add_permits_locked`, `<Acquire as Drop>::drop`,
`Semaphore::release`, `Semaphore::close`, `Semaphore::try_acquire` and
`Semaphore::forget_permits` are executed statement by statement on concrete
values. Only library calls (atomics, mutex, intrusive list, wakers, coop
budget) have hand-written semantics, listed in TOKIO_SEMAPHORE.md.

A scenario fixes the initial permits and a set of actors, each on its own
thread:
- fut(n): an `Acquire` for n permits. Repeatedly: poll it (any number of times,
  regardless of wakeups) or drop it. After `Ready(Ok)` the permits are held;
  the future is then dropped and the permits may later be released.
- release(k), close, try(k) (then optionally release k), forget(k)
Every interleaving is explored at the granularity of atomic accesses and lock
acquisitions; the coop budget (`poll_proceed`) may return Pending at any poll;
`compare_exchange_weak` may fail spuriously; a lock-free load of a waiter's
`state` may return any value at least the current one (an older value).

Properties, checked at every reachable state:
- P1 conservation: whenever no operation is running,
  available + sum over queued futures of (num - state) + held
  == initial + released - forgotten
- P2 at every terminal state (all actors finished): the wait queue is empty
- P3 no reachable panic; P4 every reachable state can reach a terminal state

Usage: python -m verification.async_cancel.tokio_semaphore CRATE.mir [--mutate NAME] [--scenario NAME]
"""

import re
import sys
from dataclasses import dataclass

from verification.async_cancel.hyper_mir import function

IMPL = r"batch_semaphore::<impl at tokio/src/sync/batch_semaphore\.rs:\d+:\d+: \d+:\d+>::"
SIGS = {
    "poll": IMPL + r"poll\(_1: Pin<&mut batch_semaphore::Acquire",
    "project": IMPL + r"project\(_1: Pin",
    "poll_acquire": IMPL + r"poll_acquire\(_1:",
    "assign_permits": IMPL + r"assign_permits\(_1:",
    "add_permits_locked": IMPL + r"add_permits_locked\(_1:",
    "drop": IMPL + r"drop\(_1: &mut batch_semaphore::Acquire",
    "release": IMPL + r"release\(_1:",
    "close": IMPL + r"close\(_1:",
    "try_acquire": IMPL + r"try_acquire\(_1:",
    "forget_permits": IMPL + r"forget_permits\(_1:",
}
CALLS = {
    "batch_semaphore::Semaphore::poll_acquire": "poll_acquire",
    "batch_semaphore::Waiter::assign_permits": "assign_permits",
    "batch_semaphore::Semaphore::add_permits_locked": "add_permits_locked",
    "batch_semaphore::Acquire::<'_>::project": "project",
}
MAX_PERMITS = (2**64 - 1) >> 3
CONSTS = {
    "sync::batch_semaphore::Semaphore::PERMIT_SHIFT": 1,
    "sync::batch_semaphore::Semaphore::CLOSED": 1,
    "sync::batch_semaphore::Semaphore::MAX_PERMITS": MAX_PERMITS,
    "false": 0, "true": 1,
}
DISC = {"None": 0, "Some": 1, "Ok": 0, "Err": 1, "Ready": 0, "Pending": 1,
        "Continue": 0, "Break": 1, "Closed": 0, "NoPermits": 1}
U = ("u",)
STALE = True   # --sc disables stale loads
INTERLEAVE = re.compile(r"Atomic::<usize>::\w+|loom::std::mutex::Mutex::<Waitlist>::lock")


class Unsupported(Exception):
    pass


class Choice(Exception):
    """Raised when the oracle has no recorded choice; n alternatives exist."""
    def __init__(self, n):
        self.n = n


class Panic(Exception):
    pass


@dataclass(frozen=True)
class Scenario:
    name: str
    initial: int
    futs: tuple        # permits requested per future
    others: tuple      # ("release", k) | ("close",) | ("try", k) | ("forget", k)


SCENARIOS = {s.name: s for s in [
    Scenario("two_waiters_release_close", 0, (1, 2), (("release", 1), ("release", 2), ("close",))),
    Scenario("three_futures", 1, (1, 1, 2), (("release", 2),)),
    Scenario("try_forget", 2, (2, 1), (("try", 1), ("forget", 1), ("close",))),
    Scenario("batch_partial", 1, (2, 2), (("release", 1), ("release", 2))),
    Scenario("try_forget_open", 2, (2, 1), (("try", 1), ("forget", 1), ("release", 1))),
]}
OPEN = [s for s in SCENARIOS.values() if ("close",) not in s.others]   # semaphore never closed


# ----- places -----
def parse_place(p: str):
    """Return a projection list: [("local", n), "deref", ("f", k), ("as", V), ...]."""
    p = p.strip()
    if re.fullmatch(r"_\d+", p):
        return [("local", p)]
    if not (p.startswith("(") and p.endswith(")")):
        raise Unsupported(f"place {p}")
    inner = p[1:-1]
    if inner.startswith("*"):
        return parse_place(inner[1:]) + ["deref"]
    if inner.startswith("("):
        depth = 0
        for i, ch in enumerate(inner):
            depth += ch == "("
            depth -= ch == ")"
            if depth == 0:
                break
        base, rest = inner[:i + 1], inner[i + 1:]
    else:
        m = re.match(r"_\d+", inner)
        base, rest = m[0], inner[m.end():]
    if m := re.match(r"\.(\d+): ", rest):
        return parse_place(base) + [("f", int(m[1]))]
    if m := re.fullmatch(r" as (\w+)", rest):
        return parse_place(base) + [("as", m[1])]
    raise Unsupported(f"place {p}")


class World:
    """Mutable copy of one global state during a step."""

    def __init__(self, st, sc):
        (self.counter, self.closed, queue, self.holder, fst, fq, phases, held,
         self.forgotten, self.released, threads, seen) = st
        self.seen = list(seen)
        self.queue = list(queue)
        self.fst, self.fq, self.phases, self.held = list(fst), list(fq), list(phases), list(held)
        self.threads = [None if t is None else [[f[0], f[1], f[2], dict(f[3]), f[4]] for f in t] for t in threads]
        self.sc = sc

    def freeze(self):
        th = tuple(None if t is None else tuple((f[0], f[1], f[2], tuple(sorted(f[3].items())), f[4]) for f in t)
                   for t in self.threads)
        return (self.counter, self.closed, tuple(self.queue), self.holder, tuple(self.fst), tuple(self.fq),
                tuple(self.phases), tuple(self.held), self.forgotten, self.released, th, tuple(self.seen))


def initial_state(sc: Scenario):
    n = len(sc.futs) + len(sc.others)
    return (sc.initial << 1, 0, (), None, tuple(sc.futs), (0,) * len(sc.futs),
            ("new",) * n, (0,) * n, 0, 0, (None,) * n, tuple(sc.futs))


class Machine:
    def __init__(self, crate: str):
        self.fns = {}
        for name, sig in SIGS.items():
            f = function(crate, sig)
            if isinstance(f, str):
                raise Unsupported(f"{name}: {f}")
            self.fns[name] = f
        self.promoted = {}
        for m in re.finditer(r"^const " + IMPL + r"(\w+)::promoted\[(\d+)\]: &usize = \{\n(.*?)\n\}", crate, re.M | re.S):
            v = re.search(r"_1 = const (\d+)_usize;", m[3])
            if v:
                self.promoted[(m[1], m[2])] = int(v[1])

    # ----- actions available to an idle actor -----
    def actions(self, w: World, a: int):
        sc = w.sc
        nf = len(sc.futs)
        ph = w.phases[a]
        if a < nf:
            fut = ("r", ("fut", a))
            if ph in ("new", "pend"):
                return [("poll", "poll", {"_1": fut, "_2": U}), ("drop", "drop", {"_1": fut})]
            if ph == "err":
                return [("drop", "drop", {"_1": fut})]
            if ph == "held":
                return [("drop_held", "drop", {"_1": fut})]
            if ph == "held_dropped":
                return [("release_held", "release", {"_1": ("r", ("sem",)), "_2": ("i", sc.futs[a])})]
            return []
        op = sc.others[a - nf]
        sem = ("r", ("sem",))
        if ph != "new":
            if op[0] == "try" and ph == "held":
                return [("release_held", "release", {"_1": sem, "_2": ("i", op[1])})]
            return []
        if op[0] == "release":
            return [("release", "release", {"_1": sem, "_2": ("i", op[1])})]
        if op[0] == "close":
            return [("close", "close", {"_1": sem})]
        if op[0] == "try":
            return [("try", "try_acquire", {"_1": sem, "_2": ("i", op[1])})]
        if op[0] == "forget":
            return [("forget", "forget_permits", {"_1": sem, "_2": ("i", op[1])})]
        raise Unsupported(f"actor {op}")

    def finish(self, w: World, a: int, kind: str, ret):
        nf = len(w.sc.futs)
        if kind == "poll":
            if ret == ("e", "Pending", ()):
                w.phases[a] = "pend"
            elif ret == ("e", "Ready", (("e", "Ok", (U,)),)):
                w.phases[a] = "held"
                w.held[a] = w.sc.futs[a]
            elif ret[:2] == ("e", "Ready") and ret[2][0][1] == "Err":
                w.phases[a] = "err"
            else:
                raise Unsupported(f"poll returned {ret}")
        elif kind == "drop":
            w.phases[a] = "dropped"
        elif kind == "drop_held":
            w.phases[a] = "held_dropped"
        elif kind == "release_held":
            w.phases[a] = "done"
            w.held[a] = 0
        elif kind == "release":
            w.phases[a] = "done"
            w.released += w.sc.others[a - nf][1]
        elif kind == "close":
            w.phases[a] = "done"
        elif kind == "try":
            if ret[1] == "Ok":
                w.phases[a] = "held"
                w.held[a] = w.sc.others[a - nf][1]
            else:
                w.phases[a] = "done"
        elif kind == "forget":
            w.phases[a] = "done"
            w.forgotten += ret[1]

    # ----- one step: run thread a until just before its next interleaving point -----
    def step(self, st, sc, a: int, choices: list):
        w = World(st, sc)
        self.oracle = list(choices)
        self.used = 0
        ev = []
        if w.threads[a] is None:
            acts = self.actions(w, a)
            if not acts:
                return None
            kind, fn, args = acts[self.choose(len(acts))]
            w.threads[a] = [[fn, "bb0", 0, dict(args), kind]]
        self.run(w, a, ev)
        return w.freeze(), ev

    def choose(self, n: int) -> int:
        if n == 1:
            return 0
        if self.used < len(self.oracle):
            c = self.oracle[self.used]
            self.used += 1
            return c
        raise Choice(n)

    def run(self, w: World, a: int, ev: list):
        self._w, self._a = w, a
        ops = 0
        for _ in range(5000):
            frames = w.threads[a]
            fr = frames[-1]
            fn, block, idx, env = fr[0], fr[1], fr[2], fr[3]
            lines = self.fns[fn].graph[block]
            line = lines[idx]
            where = f"{fn}:{block}"
            if idx < len(lines) - 1:
                fr[2] += 1
                self.statement(w, a, line, where)
                continue
            # terminator
            if line == "return;":
                ret = env.get("_0", U)
                frames.pop()
                if not frames:
                    if w.holder == a:
                        raise Unsupported(f"{where}: returns holding the lock")
                    w.threads[a] = None
                    self.finish(w, a, fr[4], ret)
                    ev.append(("done", a, fr[4]))
                    return
                self.write(w, a, fr[4], ret)
                continue
            if line == "unreachable;":
                raise Unsupported(f"{where}: reached unreachable")
            if line == "resume;":
                raise Unsupported(f"{where}: resume on a normal path")
            if m := re.fullmatch(r"goto -> (bb\d+);", line):
                fr[1], fr[2] = m[1], 0
                continue
            if m := re.fullmatch(r"switchInt\((.*)\) -> \[(.*)\];", line):
                v = self.operand(w, a, m[1], where)
                arms = [x.split(": ") for x in m[2].split(", ")]
                tgt = next((b for k, b in arms if k != "otherwise" and int(k) == v[1]), None) \
                    or next(b for k, b in arms if k == "otherwise")
                fr[1], fr[2] = tgt, 0
                continue
            if m := re.fullmatch(r"assert\((!?)(.*?), .*\) -> \[success: (bb\d+), .*\];", line):
                v = self.operand(w, a, m[2], where)[1]
                if bool(v) == (m[1] == "!"):
                    raise Panic(f"{where}: assert {line[:60]}")
                fr[1], fr[2] = m[3], 0
                continue
            if m := re.fullmatch(r"drop\((.*?)\) -> (?:\[return: (bb\d+), .*\]|(bb\d+));", line):
                v = self.read(w, a, parse_place(m[1]), where)
                if self.has_guard(v):
                    self.unlock(w, a, where)
                fr[1], fr[2] = m[2] or m[3], 0
                continue
            if m := call_parts(line):
                dst, callee, args, target = m
                vals = [self.operand(w, a, x, where) for x in args]
                relock = callee.startswith("Option::<std::sync::MutexGuard<'_, Waitlist>>::unwrap_or_else") \
                    and vals[0][1] == "None"
                if INTERLEAVE.fullmatch(callee) or relock:
                    if ops:
                        return
                    ops += 1
                if target is None:
                    raise Panic(f"{where}: {callee}")
                name = CALLS.get(callee)
                if name:
                    fr[1], fr[2] = target, 0
                    frames.append([name, "bb0", 0, {f"_{i + 1}": v for i, v in enumerate(vals)}, dst])
                    continue
                ret = self.library(w, a, callee, vals, args, where, ev)
                self.write(w, a, dst, ret)
                fr[1], fr[2] = target, 0
                continue
            raise Unsupported(f"{where}: terminator {line}")
        raise Unsupported(f"{fn}: no interleaving point within 5000 statements")

    def statement(self, w, a, line, where):
        if re.match(r"(StorageLive|StorageDead|nop|PlaceMention|FakeRead|AscribeUserType)\b", line):
            return
        m = re.fullmatch(r"(.*?) = (.*);", line)
        if not m:
            raise Unsupported(f"{where}: statement {line}")
        self.write(w, a, m[1], self.rvalue(w, a, m[2], where))

    # ----- memory -----
    def resolve(self, w, a, proj, where):
        """Turn a projection list into an absolute location tuple."""
        loc = None
        for p in proj:
            if p == "deref":
                v = self.get(w, loc, where)
                if v == U:
                    loc = ("U",)   # the task Context: opaque, never read
                    continue
                if v[0] != "r":
                    raise Unsupported(f"{where}: deref of {v}")
                loc = v[1]
            elif p[0] == "local":
                loc = ("L", len(w.threads[a]) - 1, p[1])
            else:
                loc = loc + (p,)
        return loc

    def read(self, w, a, proj, where):
        return self.get(w, self.resolve(w, a, proj, where), where)

    def get(self, w, loc, where):
        if loc[0] == "L":
            v = self.cur_frames[loc[1]][3].get(loc[2], U)
            for p in loc[3:]:
                v = sub(v, p, where)
            return v
        if loc[0] == "C":
            return ("i", loc[1])
        if loc[0] == "U":
            return U
        if loc[0] == "fut":
            i, rest = loc[1], loc[2:]
            if rest == (("f", 1),):
                return ("r", ("sem",))
            if rest == (("f", 2),):
                return ("i", w.sc.futs[i])
            if rest == (("f", 3),):
                return ("i", w.fq[i])
        if loc[0] == "wl":
            self.need_lock(w, where)
            if loc[1:] == (("f", 1),):
                return ("i", w.closed)
        raise Unsupported(f"{where}: read of {loc}")

    def write(self, w, a, place, v):
        where = "write"
        proj = parse_place(place)
        loc = self.resolve(w, a, proj, where)
        if loc[0] == "L":
            env = self.cur_frames[loc[1]][3]
            if len(loc) == 3:
                env[loc[2]] = v
            else:
                env[loc[2]] = put(env.get(loc[2], U), loc[3:], v)
            return
        if loc[0] == "fut" and loc[2:] == (("f", 3),):
            w.fq[loc[1]] = v[1]
            return
        if loc[0] == "wl" and loc[1:] == (("f", 1),):
            self.need_lock(w, where)
            w.closed = v[1]
            return
        raise Unsupported(f"write of {loc}")

    @property
    def cur_frames(self):
        return self._w.threads[self._a]

    def need_lock(self, w, where):
        if w.holder != self._a:
            raise Unsupported(f"{where}: wait list accessed without the lock")

    def has_guard(self, v):
        if v == ("g",):
            return True
        if v[0] in ("e", "t"):
            return any(self.has_guard(x) for x in v[-1])
        return False

    def unlock(self, w, a, where):
        if w.holder != a:
            raise Unsupported(f"{where}: unlock without holding")
        w.holder = None

    # ----- operands and rvalues -----
    def operand(self, w, a, s, where):
        self._w, self._a = w, a
        s = s.strip()
        if m := re.fullmatch(r"(?:no_retag )?(?:copy|move) (.*)", s):
            return self.read(w, a, parse_place(m[1]), where)
        if m := re.fullmatch(r"const (\d+)_usize", s):
            return ("i", int(m[1]))
        if m := re.fullmatch(r"const ([\w:]+)", s):
            if m[1] in CONSTS:
                return ("i", CONSTS[m[1]])
            if m := re.fullmatch(r"const " + IMPL + r"(\w+)::promoted\[(\d+)\]", s):
                return ("r", ("C", self.promoted[(m[1], m[2])]))
            return U
        if m := re.fullmatch(r"const (.*)::promoted\[(\d+)\]", s):
            fn = re.search(r"::(\w+)$", m[1])[1]
            return ("r", ("C", self.promoted[(fn, m[2])]))
        if s.startswith("const "):
            return U
        if s.startswith("_") or s.startswith("("):
            return self.read(w, a, parse_place(s), where)
        raise Unsupported(f"{where}: operand {s}")

    def rvalue(self, w, a, s, where):
        self._w, self._a = w, a
        if m := re.fullmatch(r"&(?:raw )?(?:mut |const )?(.*)", s):
            return ("r", self.resolve(w, a, parse_place(m[1]), where))
        if m := re.fullmatch(r"(Lt|Le|Gt|Ge|Eq|Ne|Shl|Shr|BitAnd|BitOr|SubWithOverflow|AddWithOverflow)\((.*)\)", s):
            x, y = [self.operand(w, a, o, where)[1] for o in split_args(m[2])]
            op = m[1]
            if op in ("SubWithOverflow", "AddWithOverflow"):
                r = x - y if op[0] == "S" else x + y
                return ("t", (("i", r % 2**64), ("i", int(not 0 <= r < 2**64))))
            r = {"Lt": lambda: x < y, "Le": lambda: x <= y, "Gt": lambda: x > y, "Ge": lambda: x >= y,
                 "Eq": lambda: x == y, "Ne": lambda: x != y, "Shl": lambda: (x << y) % 2**64,
                 "Shr": lambda: x >> y, "BitAnd": lambda: x & y, "BitOr": lambda: x | y}[op]()
            return ("i", int(r))
        if m := re.fullmatch(r"discriminant\((.*)\)", s):
            v = self.read(w, a, parse_place(m[1]), where)
            if v[0] != "e":
                raise Unsupported(f"{where}: discriminant of {v}")
            return ("i", DISC[v[1]])
        if m := re.fullmatch(r"\((.*)\)", s):
            if not re.match(r"(move|copy|const) ", m[1]):
                return self.operand(w, a, s, where)
            return ("t", tuple(self.operand(w, a, x, where) for x in split_args(m[1])))
        if m := re.fullmatch(r"[\w:<>'(), &]*?::(\w+)(?:\((.*)\))?", s):
            if m[1] in DISC:
                args = split_args(m[2]) if m[2] else []
                return ("e", m[1], tuple(self.const_or_operand(w, a, x, where) for x in args))
            if re.match(r"std::sync::atomic::Ordering::|core::panicking::AssertKind::", s):
                return U
        if s.startswith("{closure") or s.startswith("["):
            return U
        return self.const_or_operand(w, a, s, where)

    def const_or_operand(self, w, a, s, where):
        if s in ("const ()", "const AcquireError(())"):
            return U
        return self.operand(w, a, s, where)

    # ----- library semantics -----
    def library(self, w, a, callee, v, args, where, ev):
        self._w, self._a = w, a
        sc = w.sc
        if callee in ("<AtomicUsize as Deref>::deref", "Pin::<&mut batch_semaphore::Waiter>::new_unchecked",
                      "Pin::<&mut batch_semaphore::Acquire<'_>>::get_unchecked_mut",
                      "Pin::<&mut batch_semaphore::Waiter>::into_inner_unchecked",
                      "NonNull::<batch_semaphore::Waiter>::new_unchecked",
                      "<NonNull<batch_semaphore::Waiter> as From<&mut batch_semaphore::Waiter>>::from"):
            return v[0]
        if callee in ("<Pin<&mut batch_semaphore::Waiter> as Deref>::deref", "NonNull::<batch_semaphore::Waiter>::as_mut::<'_>"):
            return self.get(w, v[0][1], where)
        if m := re.fullmatch(r"Atomic::<usize>::(\w+)", callee):
            return self.atomic(w, a, m[1], v, where, ev)
        if callee == "loom::std::mutex::Mutex::<Waitlist>::lock":
            if v[0] != ("r", ("sem", ("f", 0))):
                raise Unsupported(f"{where}: lock of {v[0]}")
            return self.lock(w, a, where, ev)
        if callee in ("<std::sync::MutexGuard<'_, Waitlist> as Deref>::deref",
                      "<std::sync::MutexGuard<'_, Waitlist> as DerefMut>::deref_mut"):
            if self.get(w, v[0][1], where) != ("g",):
                raise Unsupported(f"{where}: deref of non-guard")
            self.need_lock(w, where)
            return ("r", ("wl",))
        if callee == "std::mem::drop::<std::sync::MutexGuard<'_, Waitlist>>":
            self.unlock(w, a, where)
            return U
        if callee == "Option::<std::sync::MutexGuard<'_, Waitlist>>::is_none":
            return ("i", int(self.get(w, v[0][1], where)[1] == "None"))
        if callee == "Option::<std::sync::MutexGuard<'_, Waitlist>>::take":
            loc = v[0][1]
            old = self.get(w, loc, where)
            self.put_loc(w, loc, ("e", "None", ()))
            return old
        if callee.startswith("Option::<std::sync::MutexGuard<'_, Waitlist>>::unwrap_or_else"):
            if v[0][1] == "Some":
                return v[0][2][0]
            # the closure only locks the wait list (add_permits_locked::{closure#0}, read in MIR)
            return self.lock(w, a, where, ev)
        if callee in ("Option::<std::sync::MutexGuard<'_, Waitlist>>::expect", "Option::<usize>::expect",
                      "Option::<NonNull<batch_semaphore::Waiter>>::unwrap"):
            if v[0][1] == "None":
                raise Panic(f"{where}: {callee} on None")
            return v[0][2][0]
        if callee == "core::num::<impl usize>::checked_add":
            r = v[0][1] + v[1][1]
            return ("e", "Some", (("i", r),)) if r < 2**64 else ("e", "None", ())
        if callee == "core::num::<impl usize>::saturating_sub":
            return ("i", max(0, v[0][1] - v[1][1]))
        if callee == "std::cmp::min::<usize>":
            return ("i", min(v[0][1], v[1][1]))
        if callee.startswith("util::linked_list::LinkedList::<batch_semaphore::Waiter>::"):
            return self.list_op(w, a, callee.rsplit("::", 1)[1], v, where)
        if callee.startswith("unsafe_cell::UnsafeCell::<Option<Waker>>::with_mut::<Option<Waker>"):
            return ("e", "None", ())   # waker taken: wakers do not touch permits
        if callee.startswith("unsafe_cell::UnsafeCell::<Option<Waker>>::with_mut::<()"):
            return U                   # waker registration
        if callee == "WakeList::can_push":
            return ("i", 1)            # capacity 32 exceeds the number of waiters in every scenario
        if callee in ("WakeList::new", "WakeList::push", "WakeList::wake_all", "std::mem::drop::<Option<Waker>>",
                      "AcquireError::closed", "RestoreOnPending::made_progress") \
                or callee.startswith("batch_semaphore::Acquire::<'a>::project::is_unpin"):
            return U
        if callee == "trace_leaf":
            return ("e", "Ready", (U,))   # taskdump not compiled in this build
        if callee == "poll_proceed":
            return [("e", "Ready", (U,)), ("e", "Pending", ())][self.choose(2)]
        if callee == "<Result<(), AcquireError> as Try>::branch":
            r = v[0]
            return ("e", "Continue", (U,)) if r[1] == "Ok" else ("e", "Break", (r,))
        if callee == "<Poll<Result<(), AcquireError>> as FromResidual<Result<!, AcquireError>>>::from_residual":
            return ("e", "Ready", (("e", "Err", (U,)),))
        if callee == "Poll::<Result<(), AcquireError>>::is_ready":
            return ("i", int(self.get(w, v[0][1], where)[1] == "Ready"))
        if callee.startswith("core::fmt::") or callee.startswith("Arguments::"):
            return U   # only on panic paths
        raise Unsupported(f"{where}: unknown call {callee}")

    def put_loc(self, w, loc, val):
        env = self.cur_frames[loc[1]][3]
        env[loc[2]] = val if len(loc) == 3 else put(env.get(loc[2], U), loc[3:], val)

    def lock(self, w, a, where, ev):
        if w.holder == a:
            raise Unsupported(f"{where}: re-entrant lock")
        if w.holder is not None:
            raise Blocked()
        w.holder = a
        if a < len(w.sc.futs):
            w.seen[a] = w.fst[a]   # the lock orders this thread after every locked write of its state
        ev.append(("lock", a))
        return ("g",)

    def atomic(self, w, a, op, v, where, ev):
        loc = v[0][1]
        if loc == ("sem", ("f", 1)):
            cur = w.counter
            setv = lambda x: setattr(w, "counter", x)
            fut = None
        elif loc[0] == "fut" and loc[2:] == (("f", 0), ("f", 0)):
            fut = loc[1]
            cur = w.fst[fut]
            setv = lambda x: w.fst.__setitem__(fut, x)
        else:
            raise Unsupported(f"{where}: atomic on {loc}")
        ev.append((op, "counter" if fut is None else f"state{fut}"))
        if op == "load":
            if fut is not None and w.holder != a and STALE:
                # lock-free read by the owner: any value between the current one and the value at the
                # owner's last synchronization (own store or lock); state only decreases
                vals = list(range(cur, w.seen[fut] + 1))
                return ("i", vals[self.choose(len(vals))])
            return ("i", cur)
        if op == "store":
            setv(v[1][1])
            if fut is not None:
                w.seen[fut] = v[1][1]
            return U
        if op == "fetch_add":
            setv(cur + v[1][1])
            return ("i", cur)
        if op == "fetch_or":
            setv(cur | v[1][1])
            return ("i", cur)
        if op in ("compare_exchange", "compare_exchange_weak"):
            spurious = op.endswith("weak") and self.choose(2) == 1
            if cur == v[1][1] and not spurious:
                setv(v[2][1])
                return ("e", "Ok", (("i", cur),))
            return ("e", "Err", (("i", cur),))
        raise Unsupported(f"{where}: atomic {op}")

    def list_op(self, w, a, op, v, where):
        self.need_lock(w, where)
        if v[0] != ("r", ("wl", ("f", 0))):
            raise Unsupported(f"{where}: list op on {v[0]}")
        node = lambda r: r[1][1] if r[0] == "r" and r[1][0] == "fut" and r[1][2:] == (("f", 0),) else None
        if op == "push_front":
            i = node(v[1])
            if i is None or i in w.queue:
                raise Unsupported(f"{where}: push_front of {v[1]}")
            w.queue.insert(0, i)
            return U
        if op == "remove":
            i = node(v[1])
            if i is None:
                raise Unsupported(f"{where}: remove of {v[1]}")
            if i in w.queue:
                w.queue.remove(i)
                return ("e", "Some", (v[1],))
            return ("e", "None", ())
        if op in ("last", "pop_back"):
            if not w.queue:
                return ("e", "None", ())
            i = w.queue[-1]
            if op == "pop_back":
                w.queue.pop()
            return ("e", "Some", (("r", ("fut", i, ("f", 0))),))
        raise Unsupported(f"{where}: list op {op}")


class Blocked(Exception):
    pass


def sub(v, p, where):
    if p[0] == "f":
        if v[0] == "t":
            return v[1][p[1]]
        if v[0] == "e":
            return v[2][p[1]]
    if p[0] == "as":
        if v[0] == "e" and v[1] == p[1]:
            return v
    raise Unsupported(f"{where}: projection {p} of {v}")


def put(v, path, x):
    p = path[0]
    if p[0] == "as":
        return x if len(path) == 1 else put(v, path[1:], x)
    if v[0] == "t":
        items = list(v[1])
        items[p[1]] = put(items[p[1]], path[1:], x) if len(path) > 1 else x
        return ("t", tuple(items))
    raise Unsupported(f"write into {v} at {path}")


def call_parts(line: str):
    """Split `DST = CALLEE(ARGS) -> TARGETS;` respecting nested parentheses."""
    m = re.fullmatch(r"(_\d+) = (.*)\) -> (\[return: (bb\d+), unwind.*\]|unwind .*|bb\d+);", line)
    if not m:
        return None
    body, depth = m[2], 0
    for i in range(len(body) - 1, -1, -1):
        depth += body[i] == ")"
        depth -= body[i] == "("
        if depth < 0:
            return m[1], body[:i], split_args(body[i + 1:]), m[4]
    return None


def split_args(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "<({[":
            depth += 1
        elif ch in ">)}]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


# ----- exploration -----


def successors(m: Machine, st, sc):
    n = len(st[6])
    for a in range(n):
        stack = [[]]
        while stack:
            ch = stack.pop()
            try:
                r = m.step(st, sc, a, ch)
            except Choice as c:
                stack.extend(ch + [k] for k in range(c.n))
                continue
            except Blocked:
                continue
            except Panic as p:
                yield a, "panic", str(p)
                continue
            if r is not None:
                yield a, r[0], r[1]


def quiescent(st) -> bool:
    return all(t is None for t in st[10])


def conserved(st, sc) -> tuple[int, int]:
    counter, _, _, _, fst, fq, ph, held, forgotten, released, _, _ = st
    live = [p in ("new", "pend", "err") for p in ph]   # the Acquire future still exists
    have = (counter >> 1) + sum(n - s for n, s, q, l in zip(sc.futs, fst, fq, live) if q and l) + sum(held)
    return have, sc.initial + released - forgotten


def terminal(st, sc) -> bool:
    nf = len(sc.futs)
    ph = st[6]
    return quiescent(st) and all(p in ("dropped", "held_dropped", "done") for p in ph[:nf]) \
        and all(p in ("done", "held", "new") for p in ph[nf:])


def explore(m: Machine, sc: Scenario, limit=3_000_000):
    init = initial_state(sc)
    parent = {init: None}
    work = [init]
    edges = {}
    panics, p1, p2 = [], [], []
    while work:
        s = work.pop()
        succ = []
        for a, s2, ev in successors(m, s, sc):
            if s2 == "panic":
                panics.append((s, a, ev))
                continue
            succ.append(s2)
            if s2 not in parent:
                parent[s2] = (s, a, tuple(ev))
                work.append(s2)
                if len(parent) > limit:
                    raise Unsupported("state limit")
        edges[s] = succ
        if quiescent(s):
            have, want = conserved(s, sc)
            if have != want:
                p1.append(s)
        if terminal(s, sc) and s[2]:
            p2.append(s)
    # P4: backward reachability from terminal states
    rev = {}
    for s, ss in edges.items():
        for s2 in ss:
            rev.setdefault(s2, []).append(s)
    good = {s for s in edges if terminal(s, sc)}
    stack = list(good)
    while stack:
        s = stack.pop()
        for p in rev.get(s, []):
            if p not in good:
                good.add(p)
                stack.append(p)
    stuck = [s for s in edges if s not in good]
    return parent, panics, p1, p2, stuck


def show(s, sc) -> str:
    counter, closed, queue, holder, fst, fq, ph, held, forgotten, released, th, _ = s
    return (f"avail={counter >> 1} closed_bit={counter & 1} closed={closed} queue={list(queue)} "
            f"state={list(fst)} queued={list(fq)} phases={list(ph)} held={list(held)}")


def path(parent, s, sc) -> list[str]:
    out = []
    while parent[s] is not None:
        p, a, ev = parent[s]
        evs = [e for e in ev if e[0] in ("done",) or e[0] in ("compare_exchange", "store", "fetch_add", "lock")]
        out.append(f"actor {a}: {evs} -> {show(s, sc)}")
        s = p
    return out[::-1]


def check(crate: str, scenarios=None, verbose=True) -> int:
    """0: all properties hold; 1: violation; 2: unsupported input."""
    try:
        m = Machine(crate)
    except Unsupported as e:
        print(f"UNSUPPORTED: {e}")
        return 2
    worst = 0
    for sc in scenarios or SCENARIOS.values():
        try:
            parent, panics, p1, p2, stuck = explore(m, sc)
        except Unsupported as e:
            print(f"{sc.name}: UNSUPPORTED: {e}")
            worst = max(worst, 2)
            continue
        print(f"{sc.name}: initial={sc.initial} futs={list(sc.futs)} others={list(sc.others)}: "
              f"states {len(parent)}; P1 violations {len(p1)}; P2 {len(p2)}; panics {len(panics)}; stuck {len(stuck)}")
        bad = p1 or p2 or panics or stuck
        if bad and verbose:
            if p1:
                s = min(p1, key=lambda x: len(path(parent, x, sc)))
                have, want = conserved(s, sc)
                print(f"  P1 COUNTEREXAMPLE: have {have}, want {want}")
                for line in path(parent, s, sc):
                    print("    " + line)
            if panics:
                print(f"  panics: {sorted({e for _, _, e in panics})}")
            if p2:
                print(f"  P2 example: {show(p2[0], sc)}")
        if bad:
            worst = max(worst, 1)
    print("HOLDS" if worst == 0 else "VIOLATED" if worst == 1 else "UNSUPPORTED")
    return worst


MUTATIONS = {
    # poll_acquire fast path: neither store state 0 nor set `queued` (the parent of #8542),
    # combined with master's coop check after poll_acquire (#8371)
    "pre8542_fast_path": [
        ("poll_acquire", "_76 = Atomic::<usize>::store(copy _77, const 0_usize, move _81) -> [return: bb42, unwind: bb84];",
         "goto -> bb42;"),
        ("poll_acquire", "(*_5) = const true;\n        _82 = Result", "_82 = Result"),
    ],
    # Acquire::drop: never return permits assigned to the waiter
    "drop_no_return": [("drop", "switchInt(move _18) -> [0: bb10, otherwise: bb9];", "goto -> bb10;")],
    # Acquire::drop: do not unlink the waiter
    "drop_no_remove": [("drop", "_7 = util::linked_list::LinkedList::<batch_semaphore::Waiter>::remove(move _8, copy _5) -> [return: bb5, unwind: bb16];",
                        "goto -> bb5;")],
    # Acquire::poll: clear `queued` even when returning Pending
    "poll_clear_on_pending": [("poll", "switchInt(move _23) -> [0: bb19, otherwise: bb18];", "goto -> bb18;")],
}


def mutate(crate: str, name: str) -> str:
    for fn, old, new in MUTATIONS[name]:
        start = crate.index("fn " + function(crate, SIGS[fn]).name)
        end = crate.index("\n}\n", start)
        body = crate[start:end]
        if body.count(old) != 1:
            raise SystemExit(f"{name}: mutation site found {body.count(old)} times")
        crate = crate[:start] + body.replace(old, new) + crate[end:]
    return crate


def main(argv: list[str]) -> int:
    sys.setrecursionlimit(10000)
    crate = open(argv[1]).read()
    scen = None
    rest = argv[2:]
    while rest:
        if rest[0] == "--mutate":
            crate = mutate(crate, rest[1])
        elif rest[0] == "--sc":
            global STALE
            STALE = False
            rest = rest[1:]
            continue
        elif rest[0] == "--scenario":
            scen = [SCENARIOS[rest[1]]]
        rest = rest[2:]
    return check(crate, scen)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
