"""Translate a small, fail-closed subset of cleanup MIR to Verus map obligations."""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from verification.async_cancel.cleanup_mir_check import functions


@dataclass(frozen=True)
class Value:
    """A symbolic value with a checked semantic sort."""

    sort: str
    expr: str


@dataclass
class State:
    """Path-local symbolic store and map effect."""

    env: dict[str, Value]
    effect: str = "before"
    conditions: tuple[str, ...] = ()
    locked: bool = False
    notified: bool = False


@dataclass
class Program:
    """Parsed basic blocks; declarations rely on well-typed compiler input."""

    blocks: dict[str, list[str]] = field(default_factory=dict)


def parse(body: str) -> Program | str:
    """Require every executable line to belong to a recognized basic block."""
    program = Program()
    current: str | None = None
    executable = False
    for raw in body.splitlines()[1:-1]:
        line = raw.strip()
        match = re.fullmatch(r"(bb\d+)(?: \(cleanup\))?: \{", line)
        if match:
            current = match[1]
            if current in program.blocks:
                return "duplicate basic block"
            program.blocks[match[1]] = []
            executable = True
        elif current is not None and line == "}":
            current = None
        elif current is not None and line:
            program.blocks[current].append(line)
        elif executable and line:
            return f"unsupported text outside block: {line}"
        elif line and not re.fullmatch(r"(?:debug .*;|let .*;|scope \d+ \{|})", line):
            return f"unsupported declaration: {line}"
    return program if "bb0" in program.blocks else "missing entry block"


def operand(text: str, state: State) -> Value | None:
    """Resolve local aliases, references, and u64 constants."""
    borrowed = text.startswith(("&", "&mut "))
    text = re.sub(r"^(?:copy |move |&mut |&)", "", text)
    if re.fullmatch(r"_\d+", text):
        value = state.env.get(text)
        if borrowed and value and value.sort == "guard":
            return Value("guard_ref", value.expr)
        if borrowed and value and value.sort == "guard_ref":
            return None
        return value
    match = re.fullmatch(r"const (\d+)_u64", text)
    return Value("key", match[1] + "u64") if match else None


def assignment(rhs: str, state: State) -> Value | None:
    """Interpret projections by operand identity, not local numbering."""
    match = re.fullmatch(r"(?:&|no_retag copy )\(\(\*(_\d+)\)\.(\d+): .+\)", rhs)
    if match:
        base = state.env.get(match[1])
        if base == Value("self", "self"):
            return {
                "0": Value("lockers", "lockers"),
                "1": Value("key", "key"),
                "2": Value("arc", "owner"),
            }.get(match[2])
        if base == Value("lock", "owner") and match[2] == "1":
            return Value("semaphore", "owner")
        return None
    match = re.fullmatch(r"no_retag copy \((_\d+)\.0: .+\)", rhs)
    if match:
        value = state.env.get(match[1])
        return Value("arc", value.expr) if value and value.sort == "closure" else None
    match = re.fullmatch(r"\{closure@[^}]+} \{ self: (move _\d+) }", rhs)
    if match:
        value = operand(match[1], state)
        return Value("closure", value.expr) if value and value.sort == "arc" else None
    return operand(rhs, state)


def call(name: str, args: str, state: State, predicate: str) -> Value | str:
    """Apply explicit trusted dependency contracts to checked arguments."""
    actual = args.split(", ")
    values = [operand(arg, state) for arg in actual]
    sorts = [value.sort if value else None for value in values]
    exprs = [value.expr if value else "" for value in values]
    if name == "<Arc<CacheLock> as Deref>::deref" and sorts == ["arc"]:
        return Value("lock", exprs[0])
    if name == "Semaphore::add_permits" and sorts == ["semaphore", None]:
        if exprs[0] == "owner" and actual[1] == "const 10_usize" and not state.locked:
            state.notified = True
            return Value("unit", "()")
    if (
        name
        == "parking_lot::lock_api::RwLock::<parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>::write"
        and sorts == ["lockers"]
    ):
        if (
            state.notified
            and not state.locked
            and not any(value.sort == "guard" for value in state.env.values())
        ):
            state.locked = True
            return Value("guard", "guard")
    guard_type = "parking_lot::lock_api::RwLockWriteGuard<'_, parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>"
    if name in {
        f"<{guard_type} as Deref>::deref",
        f"<{guard_type} as DerefMut>::deref_mut",
    }:
        if sorts == ["guard_ref"] and state.locked:
            return Value("map", "map")
    if (
        name == "HashMap::<u64, Arc<CacheLock>>::get::<u64>"
        and sorts == ["map", "key"]
        and state.locked
    ):
        return Value("option", f"{state.effect}|{exprs[1]}")
    if re.fullmatch(
        r"Option::<&Arc<CacheLock>>::is_some_and::<\{closure@[^}]+}>", name
    ) and sorts == ["option", "closure"]:
        snapshot, key = exprs[0].split("|")
        comparison = predicate.replace("capture", exprs[1]).replace(
            "entry", f"({snapshot})[{key}]"
        )
        return Value("bool", f"(({snapshot}).dom().contains({key}) && ({comparison}))")
    if name == "Arc::<CacheLock>::ptr_eq" and sorts == ["arc", "arc"]:
        return Value("bool", f"{exprs[0]} == {exprs[1]}")
    if (
        name == "HashMap::<u64, Arc<CacheLock>>::remove::<u64>"
        and sorts == ["map", "key"]
        and state.locked
    ):
        state.effect = f"({state.effect}).remove({exprs[1]})"
        return Value("removed", "removed")
    return f"unsupported call or arguments: {name}({args})"


def execute(program: Program, initial: State, predicate: str) -> list[State] | str:
    """Enumerate acyclic normal paths and retain actual branch conditions."""
    pending: list[tuple[str, State, frozenset[str]]] = [("bb0", initial, frozenset())]
    returns: list[State] = []
    reached: set[str] = set()
    while pending:
        block, state, visited = pending.pop()
        if block in visited or block not in program.blocks:
            return "cycle or missing basic block"
        reached.add(block)
        visited = visited | {block}
        lines = program.blocks[block]
        terminated = False
        for line in lines:
            if terminated:
                return "instruction after terminator"
            edge = re.fullmatch(
                r"(.+) -> \[return: (bb\d+), unwind(?: continue|: bb\d+)];", line
            )
            switch = re.fullmatch(
                r"switchInt\((copy _\d+)\) -> \[0: (bb\d+), otherwise: (bb\d+)];", line
            )
            goto = re.fullmatch(r"goto -> (bb\d+);", line)
            if edge:
                instruction = edge[1]
                drop = re.fullmatch(r"drop\((_\d+)\)", instruction)
                invocation = re.fullmatch(r"(_\d+) = (.+)\((.*)\)", instruction)
                if drop:
                    value = state.env.get(drop[1])
                    if value and value.sort == "guard" and state.locked:
                        state.locked = False
                    elif not value or value.sort != "removed":
                        return "unsupported drop"
                elif invocation:
                    value = call(invocation[2], invocation[3], state, predicate)
                    if isinstance(value, str):
                        return value
                    state.env[invocation[1]] = value
                else:
                    return f"unsupported terminator: {instruction}"
                pending.append((edge[2], state, visited))
                terminated = True
            elif switch:
                value = operand(switch[1], state)
                if not value or value.sort != "bool":
                    return "switch requires a boolean"
                for target, condition in (
                    (switch[2], f"!({value.expr})"),
                    (switch[3], value.expr),
                ):
                    branch = State(
                        dict(state.env),
                        state.effect,
                        (*state.conditions, condition),
                        state.locked,
                        state.notified,
                    )
                    pending.append((target, branch, visited))
                terminated = True
            elif goto:
                pending.append((goto[1], state, visited))
                terminated = True
            elif line == "return;":
                returns.append(state)
                terminated = True
            else:
                assign = re.fullmatch(r"(_\d+) = (.+);", line)
                value = assignment(assign[2], state) if assign else None
                if not assign or not value:
                    return f"unsupported instruction: {line}"
                state.env[assign[1]] = value
        if not terminated:
            return "unterminated block"
    for block in program.blocks.keys() - reached:
        if not all(
            re.fullmatch(
                r"drop\(_\d+\) -> \[return: bb\d+, unwind terminate\(cleanup\)];|resume;",
                line,
            )
            for line in program.blocks[block]
        ):
            return "unsupported unreachable or unwind block"
    return returns if returns else "no normal return"


# 🧑 "the human requires proving the real code conforms to the spec, not only a model"
def translate(text: str) -> tuple[str | None, str | None]:
    """Generate path-specific map equalities from the actual MIR instructions."""
    bodies = functions(text)
    selected: list[Program] = []
    closure_types: set[str] = set()
    for marker, owner in (
        ("::drop(", "CacheLockGuard"),
        ("::drop::{closure#0}(", "read_through::<impl at "),
    ):
        matches = [
            body
            for body in bodies
            if marker in body.splitlines()[0] and owner in body.splitlines()[0]
        ]
        if len(matches) != 1:
            return None, "expected one destructor and one predicate closure"
        closure_types.update(re.findall(r"\{closure@[^}]+}", matches[0]))
        parsed = parse(matches[0])
        if isinstance(parsed, str):
            return None, parsed
        selected.append(parsed)
    if len(closure_types) != 1:
        return (
            None,
            "closure construction and invocation must name the selected closure type",
        )
    closure = execute(
        selected[1],
        State({"_1": Value("closure", "capture"), "_2": Value("arc", "entry")}),
        "",
    )
    if isinstance(closure, str):
        return None, closure
    if (
        len(closure) != 1
        or closure[0].conditions
        or closure[0].env.get("_0", Value("", "")).sort != "bool"
    ):
        return None, "unsupported closure result"
    paths = execute(
        selected[0], State({"_1": Value("self", "self")}), closure[0].env["_0"].expr
    )
    if isinstance(paths, str):
        return None, paths
    proofs: list[str] = []
    for index, path in enumerate(paths):
        if path.locked or not path.notified:
            return None, "normal return without notification or guard release"
        condition = " && ".join(path.conditions) or "true"
        proofs.append(f"""
proof fn path_{index}(before: Map<u64, int>, key: u64, owner: int)
    requires {condition},
    ensures {path.effect} == cleanup(before, key, owner),
{{}}
""")
    source = Path(__file__).with_name("cleanup_contract.rs").read_text()
    if source.count("\n}\n\nfn main()") != 1:
        return None, "unsupported contract module layout"
    return source.replace(
        "\n}\n\nfn main()", "\n" + "\n".join(proofs) + "\n}\n\nfn main()"
    ), None


def main() -> int:
    """Write a generated obligation outside the repository; Verus checks it separately."""
    if len(sys.argv) != 3 or sys.argv[1] in {"-h", "--help"}:
        print(
            "usage: python -m verification.async_cancel.cleanup_semantics CRATE.mir OUTPUT.rs"
        )
        return 2
    source, error = translate(Path(sys.argv[1]).read_text())
    if error:
        print(error)
        return 1
    if source is None:
        return 1
    _ = Path(sys.argv[2]).write_text(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
