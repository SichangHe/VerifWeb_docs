"""Check current Tokio `Notify` for lost `notify_one` permits by interpreting its MIR.

The real compiled bodies of `notify_with_strategy`, `notify_locked`,
`Notify::notify_waiters` (with `lock_waiter_list`, `NotifyGuard::notify_waiters`,
`inner_notify_waiters`), `NotifiedProject::poll_notified` and
`NotifiedProject::drop_notified` are executed by an abstract interpreter.
Nothing about these functions is modelled by hand; only library calls
(atomics, mutex, linked list, per-waiter notification) have abstract semantics,
listed in TOKIO_CURRENT.md.

Abstraction (sound over-approximation for safety):
- `state` word: its 2 state bits exactly; the notify_waiters counter is not
  stored. A value is "fresh" if read while the reader holds the lock (the
  counter only changes under the lock, so it then equals the current counter).
- futures in `State::Waiting` are counted by membership, saturating at 2
  (meaning >= 2): `main` (in the waiter list, no notification), `grd` (in a
  notify_waiters guarded list), `one`, `all` (unlinked, notification set).
  Init and Done futures are unbounded and untracked.
- at most one thread holds the mutex; it is tracked exactly. Threads not
  holding it form an ever-growing set: once some thread can be parked at a
  configuration, arbitrarily many can be, at every later state.
- interleaving points: every access to `state`, every lock acquire, and the
  lock-free read of a waiter's notification. Code between them runs atomically.
- C11 loads of `state`: under the lock, WAITING is read exactly and EMPTY vs
  NOTIFIED may be stale; without the lock any value may be read. RMWs and
  stores act on the latest value.

Property: a pending permit exists iff `state == NOTIFIED`, or a Waiting future
holds `One`, or the lock holder is a future that removed its own `One` and has
not yet re-delivered it. Every step that is not a receive (a future consuming
the permit and completing) must preserve "a permit is pending".

Usage: python -m verification.async_cancel.tokio_current CRATE.mir [--mutate NAME]
"""

import re
import sys
from dataclasses import dataclass, replace

from verification.async_cancel.hyper_mir import function

E, W, N = 0, 1, 2
CONST = {"sync::notify::EMPTY": E, "sync::notify::WAITING": W, "sync::notify::NOTIFIED": N,
         "false": 0, "true": 1}
UNK = ("unk",)
MEMBERS = ("main", "grd", "one", "all")
STATE_FIELD = "loom::std::atomic_usize::AtomicUsize"

SIGS = {
    "notify_with_strategy": r">::notify_with_strategy\(_1: &Notify",
    "notify_locked": r"^notify_locked\(_1: &mut",
    "notify_waiters": r"470:12>::notify_waiters\(_1: &Notify\)",
    "lock_waiter_list": r">::lock_waiter_list\(_1: &Notify\)",
    "guard_notify_waiters": r">::notify_waiters\(_1: notify::NotifyGuard",
    "inner_notify_waiters": r">::inner_notify_waiters\(_1: &Notify",
    "poll_notified": r"^notify::<impl at tokio/src/sync/notify.rs:\d+:1: \d+:\d+>::poll_notified\(_1: NotifiedProject",
    "drop_notified": r">::drop_notified\(_1: NotifiedProject",
}
CALLS = {  # callee text in MIR -> function interpreted by following its body
    "notify_locked": "notify_locked",
    "Notify::lock_waiter_list": "lock_waiter_list",
    "notify::NotifyGuard::<'_>::notify_waiters": "guard_notify_waiters",
    "Notify::inner_notify_waiters": "inner_notify_waiters",
}


class Unsupported(Exception):
    pass


def freeze(env: dict) -> tuple:
    return tuple(sorted(env.items()))


def sat_add(a: int, b: int) -> int:
    return min(2, a + b)


def decs(n: int) -> list[int]:
    """Possible values after removing one element from a saturated count."""
    return [0] if n == 1 else [1, 2] if n == 2 else []


@dataclass(frozen=True)
class Frame:
    fn: str
    block: str
    idx: int
    env: tuple
    ret: str | None  # caller local receiving the return value


@dataclass(frozen=True)
class Thread:
    kind: str                  # entry name, e.g. "drop", "poll", "notify_one"
    frames: tuple
    holder: bool = False
    self_state: str | None = None   # Init | Waiting | Done (futures only)
    member: str | None = None       # membership of self while holding the lock, or "any"
    owe: bool = False               # holder removed its own One and has not re-delivered it
    moved: bool = True              # counter changed but main list not yet moved to grd


@dataclass(frozen=True)
class Shared:
    st: int
    main: int
    grd: int
    one: int
    all: int
    holder: Thread | None

    def count(self, m: str) -> int:
        return getattr(self, m)


def permit(s: Shared) -> bool:
    return s.st == N or s.one > 0 or (s.holder is not None and s.holder.owe)


class Machine:
    def __init__(self, crate: str):
        self.fns = {}
        for name, sig in SIGS.items():
            f = function(crate, sig)
            if isinstance(f, str):
                raise Unsupported(f"{name}: {f}")
            self.fns[name] = f
        # promoted constants such as `&NOTIFIED` used by assert_eq!
        self.promoted = {}
        for m in re.finditer(r"^const (?:notify::<impl at [^>]*>|sync::notify::NotifiedProject::<'_>)::(\w+)::promoted\[(\d+)\]: &usize = \{.*?_1 = const (sync::notify::\w+);", crate, re.M | re.S):
            self.promoted[(f"sync::notify::NotifiedProject::<'_>::{m[1]}", m[2])] = ("int", CONST[m[3]])
        self.guard_locals = {
            name: set(re.findall(r"(_\d+): std::sync::MutexGuard<", f.name + "\n" + crate_lets(crate, f.name)))
            for name, f in self.fns.items()
        }

    # ----- entries -----
    def entries(self) -> list[Thread]:
        out = []
        for strat in ("Fifo", "Lifo"):
            env = {"_1": ("notify",), "_2": ("enum", strat)}
            out.append(Thread(f"notify_{strat}", (Frame("notify_with_strategy", "bb0", 0, freeze(env), None),)))
        out.append(Thread("notify_waiters", (Frame("notify_waiters", "bb0", 0, freeze({"_1": ("notify",)}), None),)))
        proj = ("agg", (("notify",), ("selfstate",), ("snapshot",), ("waiter", "self")))
        for fn, kind in (("poll_notified", "poll"), ("drop_notified", "drop")):
            for st in ("Init", "Waiting", "Done"):
                env = {"_1": proj, "_2": UNK}
                out.append(Thread(kind, (Frame(fn, "bb0", 0, freeze(env), None),),
                                  self_state=st, member="any" if st == "Waiting" else None))
        return out

    # ----- one atomic step of a thread -----
    def step(self, t: Thread, s: Shared):
        sys.setrecursionlimit(20000)
        """Yield (thread or None if finished, shared, events). Runs until the next interleaving point."""
        results = []
        self._run(t, s, 0, [], results)
        return results

    def _run(self, t: Thread, s: Shared, ops: int, ev: list, out: list, fuel: int = 400):
        if fuel == 0:
            raise Unsupported(f"no interleaving point within 400 statements in {t.frames[-1].fn}")
        fr = t.frames[-1]
        f = self.fns[fr.fn]
        lines = f.graph[fr.block]
        line = lines[fr.idx]
        env = dict(fr.env)
        last = fr.idx == len(lines) - 1
        where = f"{fr.fn}:{fr.block}"

        def go(t2, s2, ops2=ops, ev2=ev):
            self._run(t2, s2, ops2, ev2, out, fuel - 1)

        def at(block, env2, t2=None, s2=None, ops2=None, ev2=None):
            t2 = t2 or t
            if ("loop", fr.fn, block) in ev:
                # back edge within one step: yield here (finer interleaving is still sound)
                nf = replace(t2.frames[-1], block=block, idx=0, env=freeze(env2))
                out.append((replace(t2, frames=t2.frames[:-1] + (nf,)), s2 or s, ev if ev2 is None else ev2))
                return
            ev2 = (ev if ev2 is None else ev2) + [("loop", fr.fn, block)]
            nf = replace(t2.frames[-1], block=block, idx=0, env=freeze(env2))
            go(replace(t2, frames=t2.frames[:-1] + (nf,)), s2 or s, ops if ops2 is None else ops2, ev if ev2 is None else ev2)

        def nxt(env2, t2=None, s2=None, ops2=None, ev2=None):
            t2 = t2 or t
            nf = replace(t2.frames[-1], idx=fr.idx + 1, env=freeze(env2))
            go(replace(t2, frames=t2.frames[:-1] + (nf,)), s2 or s, ops if ops2 is None else ops2, ev if ev2 is None else ev2)

        def stop(t2, s2, ev2):
            out.append((t2, s2, ev2))

        if not last:
            m = re.fullmatch(r"(_\d+) = (.*);", line)
            if m:
                env[m[1]] = self.expr(m[2], env, t, s, where)
                return nxt(env)
            m = re.fullmatch(r"\(\*(_\d+)\) = (?:move|copy) (_\d+);", line)
            if m and env.get(m[1]) == ("selfstate",):
                v = env.get(m[2], UNK)
                if v[0] != "variant":
                    raise Unsupported(f"{where}: self state set to {v}")
                return nxt(env, t2=replace(t, self_state=v[1]))
            raise Unsupported(f"{where}: statement {line}")

        # terminators
        if line == "return;":
            ev = [e for e in ev if e[0] != "loop"]
            ret = env.get("_0", UNK)
            if len(t.frames) == 1:
                if t.holder:
                    raise Unsupported(f"{where}: returns holding the lock")
                return stop(None, s, ev + [("return", t.kind, t.self_state)])
            caller = t.frames[-2]
            cenv = dict(caller.env)
            cenv[fr.ret] = ret
            cf = replace(caller, env=freeze(cenv))
            # resume at the caller's call target block
            return go(replace(t, frames=t.frames[:-2] + (self.after_call(cf),)), s)
        if line in ("unreachable;",):
            return  # rustc-proved impossible
        if line == "resume;":
            raise Unsupported(f"{where}: resume on a normal path")
        m = re.fullmatch(r"goto -> (bb\d+);", line)
        if m:
            return at(m[1], env)
        m = re.fullmatch(r"switchInt\((?:move |copy )?(_\d+)\) -> \[(.*)\];", line)
        if m:
            v = env.get(m[1], UNK)
            arms = [a.split(": ") for a in m[2].split(", ")]
            val = v[1] if v[0] in ("int", "bool") else None
            taken = [b for k, b in arms if k != "otherwise" and val is not None and int(k) == val]
            if not taken and val is not None:
                taken = [b for k, b in arms if k == "otherwise"]
            if val is None:
                if v != UNK:
                    raise Unsupported(f"{where}: switch on {v}")
                taken = [b for _, b in arms]
            for b in dict.fromkeys(taken):
                at(b, env)
            return
        m = re.fullmatch(r"drop\((_\d+)\) -> (?:\[return: (bb\d+), .*\]|(bb\d+));", line)
        if m:
            target = m[2] or m[3]
            if m[1] in self.guard_locals[fr.fn]:
                return self.unlock(t, s, ev, out, target, env, where, fuel)
            return at(target, env)  # Waker, WakeList, NotifyWaitersList, guard Waiter: no shared effect
        m = re.fullmatch(r"(_\d+) = (.*?)\((.*)\) -> (?:\[return: (bb\d+), unwind.*\]|unwind .*|bb\d+);", line)
        if m:
            return self.call(t, s, ops, ev, out, env, m[1], m[2], split_args(m[3]), m[4], where, fuel)
        raise Unsupported(f"{where}: terminator {line}")

    def after_call(self, cf: Frame) -> Frame:
        """The caller frame points just past its call line; move to the call's return block."""
        line = self.fns[cf.fn].graph[cf.block][cf.idx - 1]
        target = re.search(r"-> \[return: (bb\d+)", line)[1]
        return replace(cf, block=target, idx=0)

    # ----- expressions (no shared effects) -----
    def expr(self, rhs: str, env: dict, t: Thread, s: Shared, where: str):
        rhs = re.sub(r"^no_retag ", "", rhs)
        get = lambda x: env.get(x, UNK)
        if m := re.fullmatch(r"(?:copy|move) (_\d+)", rhs):
            return get(m[1])
        if m := re.fullmatch(r"&(?:mut )?(_\d+)", rhs):
            return get(m[1])
        if m := re.fullmatch(r"const (.*)::promoted\[(\d+)\]", rhs):
            return self.promoted.get((m[1], m[2]), UNK)
        if m := re.fullmatch(r"const (.*)", rhs):
            if m[1] in CONST:
                return ("int", CONST[m[1]]) if "notify" in m[1] else ("bool", CONST[m[1]])
            return UNK
        if m := re.fullmatch(r"&\(\(\*(_\d+)\)\.0: " + re.escape(STATE_FIELD) + r"\)", rhs):
            if get(m[1]) != ("notify",):
                raise Unsupported(f"{where}: state field of {get(m[1])}")
            return ("stateref",)
        if m := re.fullmatch(r"&\(\(\*(_\d+)\)\.1: loom::std::mutex::Mutex<.*>\)", rhs):
            return ("mutex",)
        if m := re.fullmatch(r"&\(\(\*(_\d+)\)\.2: sync::notify::AtomicNotification\)", rhs):
            w = get(m[1])
            if w[0] != "waiter":
                raise Unsupported(f"{where}: notification of {w}")
            return ("notifref", w[1])
        if re.fullmatch(r"&\(\(\*(_\d+)\)\.1: loom::std::unsafe_cell::UnsafeCell<.*>\)", rhs):
            return ("wakercell",)
        if m := re.fullmatch(r"(?:copy|move) \((_\d+)\.(\d+): .*\)", rhs):
            v = get(m[1])
            if v[0] == "agg":
                return v[1][int(m[2])]
            return UNK
        if m := re.fullmatch(r"(?:copy|move) \(\((_\d+) as (Err|Ok|Some)\)\.0: .*\)", rhs):
            v = get(m[1])
            if v[0] == "res":
                return v[2]
            if v[0] == "opt":
                return v[1]
            return UNK
        if m := re.fullmatch(r"move \(\(\(\((_\d+) as Some\)\.0: sync::notify::Notification\) as One\)\.0: .*\)", rhs):
            return ("enum", "unknown-strategy")
        if m := re.fullmatch(r"copy \(\*(_\d+)\)", rhs):
            v = get(m[1])
            return ("snapshotval",) if v == ("snapshot",) else v
        if m := re.fullmatch(r"\(move (_\d+), move (_\d+)\)", rhs):
            return ("agg", (get(m[1]), get(m[2])))
        if m := re.fullmatch(r"discriminant\((.*)\)", rhs):
            return self.discriminant(m[1], env, t, where)
        if m := re.fullmatch(r"(Eq|Ne)\((?:move|copy) (_\d+), (?:move |copy )?(.*)\)", rhs):
            a = get(m[2])
            b = get(m[3]) if m[3].startswith("_") else self.expr(m[3], env, t, s, where)
            if a[0] == "calls" or b[0] == "calls":
                calls, other = (a, b) if a[0] == "calls" else (b, a)
                if other != ("snapshotval",):
                    raise Unsupported(f"{where}: counter compared with {other}")
                mis = self.mismatch(calls[1], t)
                if mis is None:
                    return UNK
                return ("bool", int(mis if m[1] == "Ne" else not mis))
            if a[0] == "int" and b[0] == "int":
                return ("bool", int((a[1] == b[1]) == (m[1] == "Eq")))
            return UNK
        if m := re.fullmatch(r"notify::State::(\w+)", rhs):
            return ("variant", m[1])
        if m := re.fullmatch(r"NotifyOneStrategy::(\w+)", rhs):
            return ("enum", m[1])
        if rhs == "Notification::All":
            return ("notifval", "All")
        if m := re.fullmatch(r"Notification::One\((?:copy|move) (_\d+)\)", rhs):
            return ("notifval", "One")
        if re.fullmatch(r"Option::<.*>::None", rhs):
            return ("opt", None)
        if re.fullmatch(r"\{closure.*|notify::NotifyGuard::<'_> \{.*|Poll::<\(\)>::.*|core::panicking::AssertKind::\w+|std::sync::atomic::Ordering::\w+|\(move _\d+, move _\d+\)|&\(\*_\d+\)", rhs):
            if rhs.startswith("notify::NotifyGuard"):
                fields = re.findall(r"\w+: (?:copy|move) (_\d+)", rhs)
                return ("agg", tuple(get(x) for x in fields))
            if rhs.startswith("&(*"):
                return get(rhs[3:-1])
            return UNK
        return UNK

    def discriminant(self, place: str, env: dict, t: Thread, where: str):
        if place.startswith("(*") and env.get(place[2:-1]) == ("selfstate",):
            return ("int", ["Init", "Waiting", "Done"].index(t.self_state))
        if m := re.fullmatch(r"\(\((_\d+) as Some\)\.0: sync::notify::Notification\)", place):
            v = env.get(m[1], UNK)
            if v[0] == "notif" and v[1]:
                return ("int", 0 if v[1] == "One" else 1)
            raise Unsupported(f"{where}: discriminant of {v}")
        v = env.get(place, UNK)
        if v[0] == "res":
            return ("int", 0 if v[1] else 1)
        if v[0] == "notif":
            return ("int", 0 if v[1] is None else 1)
        if v[0] == "opt":
            return ("int", 0 if v[1] is None else 1)
        if v[0] == "enum" and v[1] in ("Fifo", "Lifo"):
            return ("int", 0 if v[1] == "Fifo" else 1)
        return UNK

    def mismatch(self, word, t: Thread):
        """Does the notify_waiters counter differ from this future's snapshot?"""
        if word[0] != "word" or not word[2] or not t.holder:
            return None   # stale read: either outcome
        if t.self_state == "Init":
            return None   # snapshot taken at creation: either outcome
        if t.member in ("main", "grd"):
            return t.member == "grd"
        raise Unsupported(f"counter compared by a future with membership {t.member}")

    # ----- calls -----
    def call(self, t, s, ops, ev, out, env, dst, callee, args, target, where, fuel):
        get = lambda a: env.get(re.sub(r"^(copy|move) ", "", a), UNK) if re.fullmatch(r"(copy |move )?_\d+", a) else UNK

        def cont(val, t2=t, s2=s, ops2=ops, ev2=ev, env2=None):
            e = dict(env if env2 is None else env2)
            e[dst] = val
            fr = t2.frames[-1]
            nf = replace(fr, block=target, idx=0, env=freeze(e))
            self._run(replace(t2, frames=t2.frames[:-1] + (nf,)), s2, ops2, ev2, out, fuel - 1)

        if target is None:   # diverging call: panic
            msg = re.search(r'const "(.*?)"', ",".join(args))
            out.append(("panic", s, ev + [("panic", where, msg[1] if msg else callee)]))
            return
        name = CALLS.get(callee)
        if name:
            p = self.fns[name]
            params = re.findall(r"(_\d+): ", p.name.split(") ->")[0])
            cenv = {f"_{i + 1}": get(a) for i, a in enumerate(args)}
            if len(cenv) != len(params):
                raise Unsupported(f"{where}: arity of {name}")
            caller = replace(t.frames[-1], idx=t.frames[-1].idx + 1, env=freeze(env))
            nt = replace(t, frames=t.frames[:-1] + (caller, Frame(name, "bb0", 0, freeze(cenv), dst)))
            self._run(nt, s, ops, ev, out, fuel - 1)
            return
        a = [get(x) for x in args]
        st_op = re.fullmatch(r"Atomic::<usize>::(load|compare_exchange|store)", callee)
        if callee == "<AtomicUsize as Deref>::deref" or callee.startswith("<NonNull<notify::Waiter> as From<") \
                or callee.startswith("NonNull::<notify::Waiter>::as_ref") or callee.startswith("<std::sync::MutexGuard<"):
            return cont(a[0])
        if st_op or callee == "atomic_inc_num_notify_waiters_calls":
            if a[0] != ("stateref",):
                raise Unsupported(f"{where}: atomic on {a[0]}")
            if ops:
                out.append((t, s, ev))   # yield before the next interleaving point
                return
            return self.state_op(t, s, ev, out, env, dst, callee, a, cont, where)
        if callee == "loom::std::mutex::Mutex::<util::linked_list::LinkedList<notify::Waiter>>::lock":
            if t.holder:
                raise Unsupported(f"{where}: re-entrant lock")
            if ops:
                out.append((t, s, ev))
                return
            if s.holder is not None:
                return   # blocked
            for t2, s2 in self.acquire(t, s):
                cont(("guard",), t2=t2, s2=s2, ops2=1, ev2=ev + [("lock", t.kind)])
            return
        if callee.startswith("std::mem::drop::<std::sync::MutexGuard<"):
            return self.unlock(t, s, ev, out, target, env, where, fuel, dst)
        if callee == "get_state":
            w = a[0]
            return cont(("int", w[1]) if w[0] == "word" else UNK)
        if callee == "set_state":
            w, k = a[0], (a[1] if a[1] != UNK else self.expr(args[1], env, t, s, where))
            if w[0] != "word" or k[0] != "int":
                raise Unsupported(f"{where}: set_state({w}, {k})")
            return cont(("word", k[1], w[2]))  # counter bits kept
        if callee == "inc_num_notify_waiters_calls":
            w = a[0]
            if w[0] != "word" or not w[2]:
                raise Unsupported(f"{where}: counter increment of {w}")
            return cont(("word", w[1], "inc"))
        if callee == "get_num_notify_waiters_calls":
            return cont(("calls", a[0]))
        if callee == "Result::<usize, usize>::is_ok":
            return cont(("bool", int(a[0][1])) if a[0][0] == "res" else UNK)
        if callee == "Option::<Notification>::is_some":
            return cont(("bool", int(a[0][1] is not None)) if a[0][0] == "notif" else UNK)
        if callee == "AtomicNotification::load":
            return self.notif_load(t, s, ops, ev, out, a[0], cont, where)
        if callee == "AtomicNotification::store_release":
            who, val = a[0][1], a[1]
            if who != "popped" or val[0] != "notifval":
                raise Unsupported(f"{where}: store_release on {who} of {val}")
            if not t.holder:
                raise Unsupported(f"{where}: notification set without the lock")
            if val[1] == "One":
                return cont(UNK, t2=replace(t, owe=False), s2=replace(s, one=sat_add(s.one, 1)), ev2=ev + [("deliver_one",)])
            return cont(UNK, s2=replace(s, all=sat_add(s.all, 1)))
        if callee == "AtomicNotification::clear":
            if a[0][1] != "self" or t.member not in ("one", "all"):
                raise Unsupported(f"{where}: clear of {a[0]} with membership {t.member}")
            return cont(UNK, t2=replace(t, member="consumed", owe=False), ev2=ev + [("receive", t.member)])
        if callee.startswith("util::linked_list::LinkedList::<notify::Waiter>::"):
            return self.list_op(t, s, out, callee.rsplit("::", 1)[1], a, cont, where)
        if callee.startswith("Option::<NonNull<notify::Waiter>>::unwrap"):
            if a[0] == ("opt", None):
                out.append(("panic", s, ev + [("panic", where, "unwrap on None")]))
                return
            return cont(a[0][1])
        if callee.startswith("std::mem::take::<util::linked_list::LinkedList"):
            if not t.holder:
                raise Unsupported(f"{where}: list taken without the lock")
            return cont(("list", "taken"), t2=replace(t, moved=True), s2=replace(s, main=0, grd=sat_add(s.grd, s.main)))
        if callee == "NotifyWaitersList::<'_>::new":
            return cont(("grdlist",))
        if callee == "NotifyWaitersList::<'_>::pop_back_locked":
            if not t.holder:
                raise Unsupported(f"{where}: guarded pop without the lock")
            cont(("opt", None))
            for g in decs(s.grd):
                cont(("opt", ("waiter", "popped")), s2=replace(s, grd=g))
            return
        if callee == "Waker::wake" or callee.startswith("WakeList::") or callee.startswith("std::mem::drop::<Option<Waker>>") \
                or callee.startswith("unsafe_cell::UnsafeCell::") or callee.startswith("Option::<") \
                or callee.startswith("Pin::<") or callee == "notify::Waiter::new":
            return cont(UNK)  # local or user-code effects only; see TOKIO_CURRENT.md
        raise Unsupported(f"{where}: unknown call {callee}")

    def acquire(self, t: Thread, s: Shared):
        """Become the holder. A Waiting future picks which counted future it is."""
        t = replace(t, holder=True, moved=True)
        if t.member != "any":
            yield t, replace(s, holder=t)
            return
        for m in MEMBERS:
            for n in decs(s.count(m)):
                t2 = replace(t, member=m, owe=(m == "one"))
                yield t2, replace(s, **{m: n}, holder=t2)

    def unlock(self, t, s, ev, out, target, env, where, fuel, dst=None):
        if not t.holder:
            raise Unsupported(f"{where}: unlock without holding")
        if not t.moved:
            raise Unsupported(f"{where}: counter changed without moving the waiter list")
        s2 = replace(s, holder=None)
        if t.kind == "poll" and t.self_state == "Waiting" and t.member in MEMBERS:
            s2 = replace(s2, **{t.member: sat_add(s2.count(t.member), 1)})
        ev2 = ev + [("unlock", t.kind)] + ([("lost_own_one", where)] if t.owe else [])
        member = "any" if t.self_state == "Waiting" and t.kind == "poll" else t.member
        t2 = replace(t, holder=False, owe=False, member=member)
        e = dict(env)
        if dst:
            e[dst] = UNK
        fr = t2.frames[-1]
        t2 = replace(t2, frames=t2.frames[:-1] + (replace(fr, block=target, idx=0, env=freeze(e)),))
        out.append((t2, s2, ev2))

    def state_op(self, t, s, ev, out, env, dst, callee, a, cont, where):
        if callee == "atomic_inc_num_notify_waiters_calls":
            if not t.holder:
                raise Unsupported(f"{where}: counter increment without the lock")
            return cont(UNK, t2=replace(t, moved=s.main == 0), ops2=1, ev2=ev + [("fetch_add",)])
        op = callee.rsplit("::", 1)[1]
        if op == "load":
            vals = ([W] if s.st == W else [E, N]) if t.holder else [E, W, N]
            for v in vals:
                cont(("word", v, t.holder), ops2=1)
            return
        if op == "store":
            v = a[1]
            if v[0] != "word" or not v[2] or not t.holder:
                raise Unsupported(f"{where}: store of {v} (holder={t.holder}); counter bits may be stale")
            t2 = replace(t, owe=False) if v[1] == N else t
            if v[2] == "inc":
                t2 = replace(t2, moved=s.main == 0)
            return cont(UNK, t2=t2, s2=replace(s, st=v[1]), ops2=1, ev2=ev + [("store", s.st, v[1])])
        exp, new = a[1], a[2]
        if exp[0] != "word" or new[0] != "word":
            raise Unsupported(f"{where}: CAS({exp}, {new})")
        actual = ("word", s.st, t.holder)
        if exp[1] == s.st:
            t2 = replace(t, owe=False) if new[1] == N else t
            evs = ev + [("cas", s.st, new[1])]
            if s.st == N and new[1] == E:
                evs = evs + [("receive", "notified")]
            cont(("res", True, actual), t2=t2, s2=replace(s, st=new[1]), ops2=1, ev2=evs)
            if exp[2]:
                return   # fresh expected value: counter bits match, success is certain
        cont(("res", False, actual), ops2=1)

    def notif_load(self, t, s, ops, ev, out, ref, cont, where):
        if ref[1] != "self":
            raise Unsupported(f"{where}: notification load of {ref}")
        if t.holder:
            kind = {"one": "One", "all": "All"}.get(t.member)
            return cont(("notif", kind))
        # lock-free read by the owning future: may be stale (None) if set
        if ops:
            out.append((t, s, ev))
            return
        if t.member != "any":
            raise Unsupported(f"{where}: lock-free notification read with membership {t.member}")
        cont(("notif", None), ops2=1)
        for m, kind in (("one", "One"), ("all", "All")):
            for n in decs(s.count(m)):
                # this future is one of the counted `m` futures; it leaves the count when it completes
                cont(("notif", kind), t2=replace(t, member=m), s2=replace(s, **{m: n}), ops2=1)

    def list_op(self, t, s, out, op, a, cont, where):
        if not t.holder:
            raise Unsupported(f"{where}: list {op} without the lock")
        if op == "is_empty":
            return cont(("bool", int(s.main == 0 and t.member != "main")))
        if op == "push_front":
            if a[1] != ("waiter", "self") or t.self_state != "Init":
                raise Unsupported(f"{where}: push_front of {a[1]}")
            return cont(UNK, t2=replace(t, member="main"))
        if op == "remove":
            if a[1] != ("waiter", "self"):
                raise Unsupported(f"{where}: remove of {a[1]}")
            if t.member in ("main", "grd"):
                return cont(UNK, t2=replace(t, member="unlinked"))
            return cont(("opt", None))
        if op in ("pop_back", "pop_front"):
            if t.member == "main":
                raise Unsupported(f"{where}: pop while self is listed")
            cont(("opt", None)) if s.main == 0 else None
            for n in decs(s.main):
                cont(("opt", ("waiter", "popped")), s2=replace(s, main=n))
            return
        raise Unsupported(f"{where}: list op {op}")

    # ----- exploration -----
    def explore(self, limit: int = 2_000_000):
        init = Shared(E, 0, 0, 0, 0, None)
        parent = {init: None}
        lf = list(dict.fromkeys(self.entries()))
        lf_set = set(lf)
        violations, panics = [], []
        states = [init]
        work = [(init, t) for t in lf]
        done = set()

        def add_state(s2):
            states.append(s2)
            work.extend((s2, t) for t in lf)
            if s2.holder:
                work.append((s2, s2.holder))

        while work:
            s, t = work.pop()
            if (s, t) in done:
                continue
            done.add((s, t))
            for t2, s2, ev in self.step(t, s):
                if t2 == "panic":
                    panics.append((s, t.kind, ev))
                    continue
                ev = [e for e in ev if e[0] != "loop"]
                receive = any(e[0] == "receive" for e in ev)
                if t2 is not None and t2.holder:
                    s2 = replace(s2, holder=t2)
                elif t2 is not None and t2 not in lf_set:
                    lf_set.add(t2)
                    lf.append(t2)
                    work.extend((x, t2) for x in states)
                if permit(s) and not permit(s2) and not receive:
                    violations.append((s, t.kind, ev, s2))
                if s2 not in parent:
                    parent[s2] = (s, t.kind, tuple(ev))
                    add_state(s2)
                    if len(parent) > limit:
                        raise Unsupported("state limit")
        return parent, lf, violations, panics


def crate_lets(crate: str, header: str) -> str:
    start = crate.index("fn " + header)
    return crate[start:crate.index("\n}\n", start)]


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


def trace(parent, s) -> list[str]:
    out = []
    while parent[s] is not None:
        p, kind, ev = parent[s]
        out.append(f"{kind}: {list(ev)} -> st={s.st} main={s.main} grd={s.grd} one={s.one} all={s.all}")
        s = p
    return out[::-1]


def check(crate: str, show: bool = True) -> int:
    """0: property holds; 1: violation; 2: unsupported input."""
    try:
        m = Machine(crate)
        parent, lf, violations, panics = m.explore()
    except Unsupported as e:
        print(f"UNSUPPORTED: {e}")
        return 2
    drops = [v for v in violations if v[1] == "drop"]
    if show:
        print(f"abstract shared states: {len(parent)}; lock-free thread configurations: {len(lf)}")
        print(f"permit-losing non-receive steps: {len(violations)} (by drop: {len(drops)})")
        print(f"reachable panics: {sorted({(k, e[-1][1], e[-1][2]) for _, k, e in panics})}")
    if violations:
        s, kind, ev, s2 = min(violations, key=lambda v: len(trace(parent, v[0])))
        print("COUNTEREXAMPLE (abstract trace from the empty state):")
        for line in trace(parent, s):
            print("  " + line)
        print(f"  {kind}: {ev} -> st={s2.st} main={s2.main} grd={s2.grd} one={s2.one} all={s2.all}  (permit lost)")
        return 1
    print("HOLDS: no reachable non-receive step loses a pending notify_one permit")
    return 0


MUTATIONS = {
    # drop_notified: store EMPTY whenever the list is empty, like the pre-#3652 code
    "drop_unguarded_store": ("drop_notified", "switchInt(move _23) -> [0: bb19, otherwise: bb16];", "goto -> bb16;"),
    # drop_notified: never forward a received One
    "drop_no_forward": ("drop_notified", "switchInt(move _33) -> [0: bb21, 1: bb27, otherwise: bb36];", "goto -> bb27;"),
    # notify_locked: on CAS failure, return without storing NOTIFIED
    "locked_err_no_store": ("notify_locked", "_17 = Atomic::<usize>::store(copy _18, move _19, move _20) -> [return: bb17, unwind continue];", "_17 = Pin::<()>::noop(copy _18) -> [return: bb17, unwind continue];"),
    # notify_locked: WAITING arm stores EMPTY even if waiters remain
    "locked_unconditional_empty": ("notify_locked", "switchInt(move _32) -> [0: bb30, otherwise: bb27];", "goto -> bb27;"),
}


def mutate(crate: str, name: str) -> str:
    fn, old, new = MUTATIONS[name]
    start = crate.index("fn " + function(crate, SIGS[fn]).name)
    end = crate.index("\n}\n", start)
    body = crate[start:end]
    if body.count(old) != 1:
        raise SystemExit(f"{name}: mutation site found {body.count(old)} times")
    return crate[:start] + body.replace(old, new) + crate[end:]


def main(argv: list[str]) -> int:
    crate = open(argv[1]).read()
    if len(argv) > 3 and argv[2] == "--mutate":
        crate = mutate(crate, argv[3])
    return check(crate)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
