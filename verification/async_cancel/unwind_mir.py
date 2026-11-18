"""Check Pingora writer-lock ownership on panic/unwind paths of compiler MIR.

Explores every normal and cleanup (unwind) edge of the real `RTCache::get`
coroutine resume and drop functions. Abstract phase of this activation's
writer-lock obligation:

- U: no lock published by this activation
- P: `HashMap::insert` into the lockers map returned; no guard holds the lock
- G: the frame's `Option<CacheLockGuard>` slot was assigned by the guard
  constructor (`Option::map` with the constructor closure) and not yet dropped
- X: dropping that slot unwound; see the destructor report for which effects ran
- D: discharged: the guard-slot drop returned (fixed), or the explicit
  `HashMap::remove` after `add_permits` returned (buggy parent)

Safe exits: `return` in U/D, or in G with the frame suspended in the guard
variant (cancellation then runs the drop function, also checked); `resume`
(unwinding out of poll or drop) only in U/D, because the compiler sets the
frame to Panicked and never drops it again. `unwind terminate` aborts the
process and is reported separately.

Branches are explored without their conditions, except one fact tracked
path-sensitively: a place assigned `Option::None` (directly, or through a tuple
field moved into it) has discriminant 0, so a switch on it takes only its 0
edge. Calls listed in NO_UNWIND have their unwind edges removed; that list is
an explicit assumption, printed with every result.
"""

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Calls assumed not to unwind (`--assume`). Each pattern matches a terminator.
# Justifications are in UNWIND.md; none of them is user-supplied code.
NO_UNWIND = {
    "arc-clone": r"<Arc<CacheLock> as Clone>::clone\(",
    "arc-deref": r"<Arc<CacheLock> as Deref>::deref\(",
    "option-as-ref": r"Option::<Arc<CacheLock>>::as_ref\(",
    "guard-ctor": r"Option::<&Arc<CacheLock>>::map::<CacheLockGuard",
    "map-guard": r"(?:RwLockWriteGuard<'_, parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>> as Deref(?:Mut)?>::deref(?:_mut)?\(|RwLock::<parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>::write\()",
    "map-ops": r"HashMap::<u64, Arc<CacheLock>>::(?:get|remove|insert)",
    "add-permits": r"Semaphore::add_permits\(",
    "drop-lock-values": r"^drop\(_\d+\) -> .*$",  # refined by DROP_LOCAL_TYPES
    "guard-drop": r"^drop\(.*Option<read_through::CacheLockGuard<'_>>\)\)",
    "is-some-and": r"Option::<&Arc<CacheLock>>::is_some_and::<",
}
# drop(_N) is assumed no-unwind only for locals of these types.
DROP_LOCAL_TYPES = (
    "std::option::Option<std::sync::Arc<read_through::CacheLock>>",
    "parking_lot::lock_api::RwLockWriteGuard<'_, parking_lot::RawRwLock, std::collections::HashMap<u64, std::sync::Arc<read_through::CacheLock>>>",
)


@dataclass(frozen=True)
class Edge:
    """One control-flow edge; `kind` is normal or unwind, or an exit kind."""

    source: int
    target: int | None
    kind: str
    case: str | None = None


def blocks(text: str) -> dict[int, list[str]]:
    """Parse rustc's textual basic blocks, including cleanup blocks."""
    result: dict[int, list[str]] = {}
    for match in re.finditer(
        r"^    bb(\d+)(?: \(cleanup\))?: \{\n(.*?)^    \}", text, re.M | re.S
    ):
        index = int(match[1])
        if index in result:
            raise ValueError(f"duplicate block bb{index}")
        lines = [line.strip() for line in match[2].splitlines() if line.strip()]
        if not lines:
            raise ValueError(f"empty block bb{index}")
        result[index] = lines
    if 0 not in result:
        raise ValueError("missing entry block")
    return result


def edges(index: int, terminal: str) -> list[Edge]:
    """Classify every successor of one terminator; reject unknown forms."""
    if terminal in ("return;", "resume;", "unreachable;"):
        return [Edge(index, None, terminal[:-1])]
    if m := re.fullmatch(r"goto -> bb(\d+);", terminal):
        return [Edge(index, int(m[1]), "normal")]
    if m := re.fullmatch(r"switchInt\(.+\) -> \[(.+)\];", terminal):
        return [
            Edge(index, int(c[2]), "normal", c[1])
            for c in re.finditer(r"(\w+): bb(\d+)", m[1])
        ]
    m = re.fullmatch(r".* -> \[(.+)\];", terminal)
    if not m:
        if m := re.fullmatch(r".* -> bb(\d+);", terminal):
            return [Edge(index, int(m[1]), "normal")]
        raise ValueError(f"unsupported terminator: {terminal}")
    result: list[Edge] = []
    for part in (p.strip() for p in m[1].split(", ")):
        if c := re.fullmatch(r"(?:return|success): bb(\d+)", part):
            result.append(Edge(index, int(c[1]), "normal"))
        elif c := re.fullmatch(r"unwind: bb(\d+)", part):
            result.append(Edge(index, int(c[1]), "unwind"))
        elif part == "unwind continue":
            result.append(Edge(index, None, "resume"))
        elif part.startswith("unwind terminate"):
            result.append(Edge(index, None, "abort"))
        elif part != "unwind unreachable":
            raise ValueError(f"unsupported successor {part!r} in {terminal}")
    if not result:
        raise ValueError(f"no successor: {terminal}")
    return result


def dispatch(text: str) -> tuple[str, dict[int, int]]:
    """Return the frame place and the state -> entry-block map."""
    entry = blocks(text)[0]
    frame = selector = None
    for line in entry[:-1]:
        if m := re.fullmatch(r"(_\d+) = discriminant\(\((\*_\d+)\)\);", line):
            selector, frame = m[1], m[2]
    if frame is None or not entry[-1].startswith(f"switchInt(move {selector}) -> ["):
        raise ValueError("unsupported coroutine entry dispatch")
    return frame, {int(m[1]): int(m[2]) for m in re.finditer(r"(\d+): bb(\d+)", entry[-1])}


def local_types(text: str) -> dict[str, str]:
    return {m[1]: m[2] for m in re.finditer(r"let (?:mut )?(_\d+): (.+);", text)}


def assumed(terminal: str, types: dict[str, str], names: set[str]) -> str | None:
    """Name of the NO_UNWIND assumption covering this terminator's unwind edge."""
    for name in sorted(names):
        if not re.search(NO_UNWIND[name], terminal):
            continue
        if name == "drop-lock-values":
            local = re.match(r"drop\((_\d+)\)", terminal)
            if not local or types.get(local[1]) not in DROP_LOCAL_TYPES:
                continue
        return name
    return None


@dataclass(frozen=True)
class State:
    node: int
    phase: str
    saved: int | None
    nones: frozenset[str]


def strip_type(place: str) -> str:
    """`(_33.1: T)` -> `_33.1`; frame places keep their text."""
    m = re.fullmatch(r"\((_\d+\.\d+): .+\)", place)
    return m[1] if m else place


def statements(lines: list[str], frame: str, state: State) -> State:
    """Apply straight-line statements: saved state and the None facts."""
    saved, nones = state.saved, set(state.nones)
    for line in lines[:-1]:
        if m := re.fullmatch(rf"discriminant\(\({re.escape(frame)}\)\) = (\d+);", line):
            saved = int(m[1])
            continue
        m = re.fullmatch(r"(.+?) = (.+);", line)
        if not m:
            continue
        lhs, rhs = strip_type(m[1]), m[2]
        nones = {n for n in nones if n != lhs and not n.startswith(lhs + ".")}
        if re.fullmatch(r"Option::<.+>::None", rhs):
            nones.add(lhs)
        elif t := re.fullmatch(r"\((?:move|copy) (_\d+), (?:move|copy) (_\d+)\)", rhs):
            nones |= {f"{lhs}.{i}" for i, x in enumerate(t.groups()) if x in nones}
        elif (t := re.fullmatch(r"(?:move|copy) (.+)", rhs)) and strip_type(t[1]) in nones:
            nones.add(lhs)
        elif (t := re.fullmatch(r"discriminant\((.+)\)", rhs)) and t[1] in nones:
            nones.add("#zero:" + lhs)
        for borrowed in re.findall(r"&mut (\S+)", rhs):
            nones.discard(borrowed)
    return State(state.node, state.phase, saved, frozenset(nones))


@dataclass(frozen=True)
class Spec:
    frame: str
    guard: str | None  # exact guard-slot place text, fixed side only
    guard_state: int | None


def transition(spec: Spec, terminal: str, edge: Edge, phase: str) -> str:
    """Obligation phase after one edge of a terminator."""
    normal = edge.kind == "normal"
    if " = HashMap::<u64, Arc<CacheLock>>::insert(" in terminal and normal:
        if phase != "U":
            raise ValueError(f"second publication in phase {phase}")
        return "P"
    if spec.guard is None:
        if " = HashMap::<u64, Arc<CacheLock>>::remove::<u64>(" in terminal and normal and phase == "P":
            return "D"
        return phase
    if terminal.startswith(spec.guard + " = Option::<&Arc<CacheLock>>::map::<CacheLockGuard"):
        return "G" if normal and phase == "P" else phase
    if terminal.startswith(f"drop({spec.guard})") and phase == "G":
        return "D" if normal else "X"
    if spec.guard in terminal and not terminal.startswith(f"drop({spec.guard})"):
        raise ValueError(f"unsupported use of guard slot: {terminal}")
    return phase


@dataclass(frozen=True)
class Exit:
    state: State
    kind: str
    origin: str


@dataclass
class Result:
    states: list[State]
    steps: list[tuple[int, int]]
    exits: list[tuple[int, Exit]]
    starts: list[int]
    assumed_used: set[str]


def explore(text: str, spec: Spec, starts: dict[int, str], names: set[str]) -> Result:
    """Reachable abstract states; `origin` names the first unwind under obligation."""
    parsed = blocks(text)
    cfg = {i: edges(i, lines[-1]) for i, lines in parsed.items()}
    types = local_types(text)
    for line in (x for b in parsed.values() for x in b[:-1]):
        if spec.guard and line.startswith(spec.guard + " = "):
            raise ValueError(f"unsupported guard-slot write: {line}")
    ids: dict[tuple[State, str], int] = {}
    order: list[tuple[State, str]] = []
    steps: list[tuple[int, int]] = []
    exits: list[tuple[int, Exit]] = []
    used: set[str] = set()

    def intern(key: tuple[State, str]) -> int:
        if key not in ids:
            ids[key] = len(order)
            order.append(key)
            pending.append(key)
        return ids[key]

    pending: list[tuple[State, str]] = []
    start_ids = [intern((State(n, p, None, frozenset()), "")) for n, p in starts.items()]
    while pending:
        key = pending.pop()
        state, origin = key
        here = ids[key]
        lines = parsed[state.node]
        mid = statements(lines, spec.frame, state)
        terminal = lines[-1]
        zero = re.fullmatch(r"switchInt\(move (_\d+)\) -> .+", terminal)
        known_zero = zero is not None and "#zero:" + zero[1] in mid.nones
        out = cfg[state.node]
        if known_zero:
            out = [e for e in out if e.case == "0"] or [e for e in out if e.case == "otherwise"]
        for edge in out:
            if edge.kind in ("unwind", "resume", "abort"):
                name = assumed(terminal, types, names)
                if name:
                    used.add(name)
                    continue
            phase = transition(spec, terminal, edge, mid.phase)
            why = origin
            if not why and edge.kind in ("unwind", "resume") and mid.phase in "PGX":
                why = f"bb{state.node}: {terminal}"
            if not why and edge.kind == "unwind" and phase == "X":
                why = f"bb{state.node}: {terminal}"
            after = State(edge.target if edge.target is not None else -1, phase, mid.saved, mid.nones)
            if edge.target is None:
                exits.append((here, Exit(after, edge.kind, why)))
            else:
                steps.append((here, intern((after, why))))
    return Result([s for s, _ in order], steps, exits, start_ids, used)


def bad(exit: Exit, guard_state: int | None) -> bool:
    """Exit that leaves a published lock without a live owner or completed cleanup."""
    if exit.kind in ("abort", "unreachable") or exit.state.phase in "UD":
        return False
    return not (
        exit.kind == "return" and exit.state.phase == "G" and exit.state.saved == guard_state
    )


def certificate(name: str, result: Result, guard_state: int | None) -> str:
    """Verus items: Python proposes the reachable set; Verus checks closure and safety."""
    phases = "UPGXD"
    inv = " ||\n        ".join(f"s == {i}" for i in range(len(result.states)))
    step = " ||\n        ".join(f"(s == {a} && t == {b})" for a, b in result.steps) or "false"
    exit_rows = [
        f"(s == {i} && k == {['return', 'resume', 'abort', 'unreachable'].index(e.kind)} && ph == {phases.index(e.state.phase)} && sv == {-1 if e.state.saved is None else e.state.saved})"
        for i, e in result.exits
    ]
    exit_rel = " ||\n        ".join(exit_rows) or "false"
    starts = " || ".join(f"s == {i}" for i in result.starts)
    gs = -1 if guard_state is None else guard_state
    return f"""
pub open spec fn {name}_inv(s: int) -> bool {{
    {inv}
}}
pub open spec fn {name}_start(s: int) -> bool {{ {starts} }}
pub open spec fn {name}_step(s: int, t: int) -> bool {{
    {step}
}}
/// k: 0 return, 1 resume (unwind out), 2 abort, 3 unreachable; ph: U P G X D
pub open spec fn {name}_exit(s: int, k: int, ph: int, sv: int) -> bool {{
    {exit_rel}
}}
pub open spec fn {name}_ok(k: int, ph: int, sv: int) -> bool {{
    k == 2 || k == 3 || ph == 0 || ph == 4 || (k == 0 && ph == 2 && sv == {gs})
}}
proof fn {name}_closed(s: int, t: int)
    requires {name}_inv(s), {name}_step(s, t),
    ensures {name}_inv(t),
{{}}
proof fn {name}_safe(s: int, k: int, ph: int, sv: int)
    requires {name}_inv(s), {name}_exit(s, k, ph, sv),
    ensures {name}_ok(k, ph, sv),
{{}}
pub proof fn {name}_every_path(path: Seq<int>, k: int, ph: int, sv: int)
    requires
        path.len() > 0,
        {name}_start(path[0]),
        forall|i: int| 0 <= i < path.len() - 1 ==> #[trigger] {name}_step(path[i], path[i + 1]),
        {name}_exit(path[path.len() - 1], k, ph, sv),
    ensures {name}_ok(k, ph, sv),
{{
    assert forall|i: int| 0 <= i < path.len() implies {name}_inv(path[i]) by {{
        {name}_reach(path, i);
    }}
    {name}_safe(path[path.len() - 1], k, ph, sv);
}}
proof fn {name}_reach(path: Seq<int>, i: int)
    requires
        0 <= i < path.len(),
        {name}_start(path[0]),
        forall|j: int| 0 <= j < path.len() - 1 ==> #[trigger] {name}_step(path[j], path[j + 1]),
    ensures {name}_inv(path[i]),
    decreases i,
{{
    if i > 0 {{
        {name}_reach(path, i - 1);
        assert({name}_step(path[i - 1], path[(i - 1) + 1]));
        {name}_closed(path[i - 1], path[i]);
    }}
}}
"""


def guard_slot(resume: str, frame: str) -> tuple[str, int] | None:
    """The unique suspended Option<CacheLockGuard> slot, from the compiler layout."""
    fields = {m[1]: m[2] for m in re.finditer(r"^        field (_s\d+): (.+);$", resume, re.M)}
    found = []
    for m in re.finditer(r"^            Suspend\d+ \((\d+)\): \[([^]]*)\],$", resume, re.M):
        for i, slot in enumerate(s.strip() for s in m[2].split(",")):
            if "CacheLockGuard" in fields.get(slot, ""):
                found.append((int(m[1]), i, fields[slot]))
    if not found:
        return None
    if len(found) != 1:
        raise ValueError("more than one guard slot")
    state, index, _ = found[0]
    return f"((({frame}) as variant#{state}).{index}: std::option::Option<read_through::CacheLockGuard<'_>>)", state


def analyze(resume: str, drop: str, names: set[str]) -> tuple[list[tuple[str, Result]], Spec]:
    """Explore resume and drop for one side; entries come from compiler dispatch."""
    for text, kind in ((resume, "coroutine_resume"), (drop, "coroutine_drop")):
        if not re.search(rf"^// MIR for `.+::get::{{closure#0}}` 0 {kind}$", text, re.M):
            raise ValueError(f"expected RTCache::get {kind} dump")
    out = []
    spec = None
    for label, text in (("resume", resume), ("drop", drop)):
        frame, targets = dispatch(text)
        found = guard_slot(resume, frame)
        guard, gstate = found if found else (None, None)
        spec = Spec(frame, guard, gstate)
        # writer suspension: the variant holding the guard (fixed), or the
        # lookup-pending variant 7 (parent, same layout position; see UNWIND.md)
        writer = gstate if gstate is not None else 7
        starts: dict[int, str] = {}
        for state, entry in targets.items():
            phase = "U"
            if state == writer:
                phase = "G" if guard else "P"
            starts[entry] = phase
        out.append((label, explore(text, spec, starts, names)))
    assert spec is not None
    return out, spec


def destructor(crate: str) -> list[str]:
    """For each unwind exit of CacheLockGuard::drop, which cleanup effects completed."""
    m = re.search(r"^fn [^\n]*::drop\(_1: &mut CacheLockGuard<'_>\) -> \(\) \{\n.*?^\}", crate, re.M | re.S)
    if not m:
        return ["no CacheLockGuard::drop (parent has no guard)"]
    parsed = blocks(m[0])
    report = []
    pending = [(0, (), "")]
    seen = set()
    while pending:
        node, done, origin = pending.pop()
        if (node, done, origin) in seen:
            continue
        seen.add((node, done, origin))
        terminal = parsed[node][-1]
        for edge in edges(node, terminal):
            effect = done
            if edge.kind == "normal":
                for key, pat in (("notified", "Semaphore::add_permits("), ("locked", "::write("), ("removed", "::remove::<u64>("), ("unlocked", "drop(_6)")):
                    if pat in terminal:
                        effect = done + (key,)
                if edge.case == "0" and "switchInt(copy _7)" in terminal:
                    effect = done + ("not-owner",)
            why = origin or (f"bb{node}: {terminal}" if edge.kind in ("unwind", "resume") else "")
            if edge.target is None:
                report.append(f"{edge.kind}: completed {list(effect)} via {why or 'normal path'}")
            else:
                pending.append((edge.target, effect, why))
    return sorted(set(report))


def run(resume: Path, drop: Path, crate: Path, verus: Path | None, names: set[str]) -> int:
    results, spec = analyze(resume.read_text(), drop.read_text(), names)
    print(f"side: {'fixed (guard slot ' + spec.guard + ')' if spec.guard else 'parent (no guard)'}")
    print(f"assumed no-unwind: {sorted(names) or 'none'}; used: {sorted(set().union(*(r.assumed_used for _, r in results)))}")
    failures = 0
    for label, result in results:
        violations = sorted({(e.kind, e.state.phase, e.origin or "normal path") for _, e in result.exits if bad(e, spec.guard_state)})
        aborts = sorted({e.origin or "(no open obligation)" for _, e in result.exits if e.kind == "abort" and e.state.phase in "PGX"})
        print(f"{label}: {len(result.states)} states, {len(result.exits)} exits, {len(violations)} violating (exit, phase, first unwind under obligation)")
        for v in violations:
            print(f"  VIOLATION {v[0]} in {v[1]} after {v[2]}")
        for a in aborts:
            print(f"  abort (process ends) under obligation after {a}")
        failures += len(violations)
    for line in destructor(crate.read_text()):
        print(f"destructor {line}")
    if verus is not None:
        items = "".join(certificate(f"{label}_unwind", r, spec.guard_state) for label, r in results)
        source = f"use vstd::prelude::*;\nverus! {{\n{items}\n}}\nfn main() {{}}\n"
        with tempfile.TemporaryDirectory(prefix="pingora-unwind-") as directory:
            path = Path(directory) / "unwind.rs"
            path.write_text(source)
            proc = subprocess.run([str(verus), "--num-threads", "1", "--rlimit", "200", str(path)], capture_output=True, text=True, timeout=1200, check=False, env={**os.environ, "RUST_MIN_STACK": str(1 << 30)})
        tail = [x for x in (proc.stdout + proc.stderr).splitlines() if "verification results" in x or "error" in x][:6]
        print("verus: " + " | ".join(tail))
        if proc.returncode:
            failures += 1
    return 1 if failures else 0


def main() -> int:
    args = sys.argv[1:]
    names: set[str] = set()
    if "--assume" in args:
        i = args.index("--assume")
        names = set(args[i + 1].split(",")) if args[i + 1] != "none" else set()
        if names == {"all"}:
            names = set(NO_UNWIND)
        if not names <= set(NO_UNWIND):
            print(f"unknown assumption; choose from {sorted(NO_UNWIND)}")
            return 2
        del args[i : i + 2]
    if len(args) not in (3, 4):
        print("usage: unwind_mir.py RESUME.mir DROP.mir CRATE.mir [VERUS] [--assume all|none|a,b]")
        print(__doc__)
        return 2
    try:
        return run(Path(args[0]), Path(args[1]), Path(args[2]), Path(args[3]) if len(args) == 4 else None, names)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"unwind check failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
