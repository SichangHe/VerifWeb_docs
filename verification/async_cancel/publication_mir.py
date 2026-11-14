"""Interpret the restricted normal-return Pingora map-miss publication path."""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from verification.async_cancel.cleanup_mir_check import functions


@dataclass(frozen=True)
class Value:
    """A symbolic value, reference location, or aggregate with explicit sort."""

    sort: str
    label: str = ""
    items: tuple["Value", ...] = ()


@dataclass
class State:
    """Concrete symbolic path, including its historical publication identity."""

    env: dict[str, Value] = field(default_factory=dict)
    publication: tuple[Value, ...] | None = None
    locked: bool = False
    allocations: int = 0
    trace: list[str] = field(default_factory=list)


def blocks(text: str) -> dict[str, list[str]] | str:
    """Read compiler-formatted blocks and reject duplicate or empty blocks."""
    result: dict[str, list[str]] = {}
    for match in re.finditer(
        r"^    (bb\d+)(?: \(cleanup\))?: \{\n(.*?)^    }", text, re.M | re.S
    ):
        name, body = match.groups()
        if name in result:
            return "duplicate block"
        result[name] = [line.strip() for line in body.splitlines() if line.strip()]
        if not result[name]:
            return "empty block"
    return result if result else "no basic blocks"


def bare(text: str) -> str:
    """Remove enclosing parentheses and top-level place type annotations."""
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        enclosed = True
        for index, char in enumerate(text):
            depth += (char == "(") - (char == ")")
            if depth == 0 and index != len(text) - 1:
                enclosed = False
                break
        if not enclosed:
            break
        text = text[1:-1]
        depth = 0
        for index, char in enumerate(text):
            depth += (char == "(") - (char == ")")
            if depth == 0 and text[index : index + 2] == ": ":
                text = text[:index]
                break
    return text


def deref(value: Value | None, state: State) -> Value | None:
    """Read a local reference or immutable external view."""
    if value and value.sort == "ref":
        return state.env.get(value.label)
    if value and value.sort == "view":
        return value.items[0]
    return None


def assignment(text: str) -> tuple[str, str] | None:
    """Split a place assignment outside parenthesized type projections."""
    depth = 0
    for index, char in enumerate(text):
        depth += (char == "(") - (char == ")")
        if depth == 0 and text[index : index + 3] == " = ":
            return text[:index], text[index + 3 :]
    return None


def location(text: str, state: State) -> str | None:
    """Resolve local and coroutine-field storage without collapsing aliases."""
    text = bare(text)
    if re.fullmatch(r"_\d+", text):
        return text
    if text.startswith("*"):
        value = evaluate(text[1:], state)
        return value.label if value and value.sort == "ref" else None
    match = re.fullmatch(r"(.+)\.(\d+)", text)
    if match:
        base = bare(match[1])
        variant = re.fullmatch(r"(.+) as variant#(\d+)", base)
        if variant and evaluate(variant[1], state) == Value("frame"):
            return f"frame:{variant[2]}:{match[2]}"
        if evaluate(base, state) == Value("frame"):
            return f"frame:input:{match[2]}"
    return None


def evaluate(text: str, state: State) -> Value | None:
    """Evaluate supported MIR rvalues; unknown expressions have no value."""
    if text.startswith("move "):
        value = evaluate(text[5:], state)
        if value and owns_guard(value):
            return None
        return value
    text = re.sub(r"^(?:no_retag copy |copy |move )", "", text)
    if text.startswith("&"):
        place = re.sub(r"^&(?:mut )?", "", text)
        target = location(place, state)
        if target:
            return Value("ref", target)
        value = evaluate(place, state)
        return Value("view", items=(value,)) if value else None
    text = bare(text)
    target = location(text, state)
    if target:
        return state.env.get(target)
    if text.startswith("*"):
        return deref(evaluate(text[1:], state), state)
    match = re.fullmatch(r"(.+)\.(\d+)", text)
    if match:
        value = evaluate(match[1], state)
        index = int(match[2])
        if value and value.sort in {"tuple", "closure", "context"}:
            return value.items[index] if index < len(value.items) else None
        if value == Value("self") and index == 2:
            return Value("map", "self.lockers")
        if value == Value("self") and index == 0:
            return Value("cache", "self.cache")
        if value == Value("cache", "self.cache") and index == 2:
            return Value("hasher", "self.cache.hasher")
        return None
    if text in {"const true", "const false"}:
        return Value("int", "1" if text == "const true" else "0")
    if text in {"const ()", "()", ""}:
        return Value("unit")
    if text == "Option::<Arc<CacheLock>>::None":
        return Value("none")
    match = re.fullmatch(r"Option::<Arc<CacheLock>>::Some\((.+)\)", text)
    if match:
        value = evaluate(match[1], state)
        return Value("some", items=(value,)) if value and value.sort == "arc" else None
    match = re.fullmatch(r"discriminant\((.+)\)", text)
    if match:
        value = evaluate(match[1], state)
        if value and value.sort in {"some", "none"}:
            return Value("int", "1" if value.sort == "some" else "0")
        if value and value.sort == "poll":
            return Value("int", "1")
        if value == Value("frame"):
            return state.env.get("state")
        return None
    match = re.fullmatch(r"(move _\d+), (move _\d+)", text)
    if match:
        values = tuple(evaluate(arg, state) for arg in match.groups())
        if all(isinstance(value, Value) for value in values):
            return Value("tuple", items=tuple(v for v in values if v is not None))
    match = re.fullmatch(r"\{closure@([^}]+)} \{ self: (.+), hashed_key: (.+) }", text)
    if match:
        owner, key = evaluate(match[2], state), evaluate(match[3], state)
        if owner and key:
            return Value("closure", match[1], (owner, key))
    match = re.fullmatch(
        r"CacheLockGuard::<'_> \{ lockers: (.+), hashed_key: (.+), lock: (.+) }", text
    )
    if match:
        values = [evaluate(arg, state) for arg in match.groups()]
        values[0] = deref(values[0], state)
        if [v.sort if v else None for v in values] == ["map", "key", "arc"]:
            return Value("guard", items=tuple(v for v in values if v is not None))
    if re.fullmatch(r"Poll::<.+>::Pending", text):
        return Value("pending")
    match = re.fullmatch(r"std::future::ResumeTy\((.+)\)", text)
    if match and evaluate(match[1], state) == Value("context_raw"):
        return Value("context", items=(Value("context_raw"),))
    match = re.fullmatch(
        r"(.+) as (?:std::ptr::NonNull<std::task::Context<'_>>|&mut std::task::Context<'_>) \(Transmute\)",
        text,
    )
    if match:
        value = evaluate(match[1], state)
        if value is not None and value == Value("context_raw"):
            return Value("view", items=(value,)) if " as &mut " in text else value
    return None


def owns_guard(value: Value) -> bool:
    """Reject moving the saved guard rather than retaining stale initialization."""
    return value.sort == "guard" or any(owns_guard(item) for item in value.items)


def call(name: str, args: str, state: State, constructor: str) -> Value | str:
    """Use explicit normal-return contracts on checked symbolic arguments."""
    if not constructor and name != "<Arc<CacheLock> as Clone>::clone":
        return "unsupported constructor call"
    values = [evaluate(arg, state) for arg in args.split(", ")] if args else []
    if any(value is None for value in values):
        return "unknown call argument"
    actual = [value for value in values if value is not None]
    read = [deref(value, state) for value in actual]
    write = "parking_lot::lock_api::RwLock::<parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>::write"
    guard = "parking_lot::lock_api::RwLockWriteGuard<'_, parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>"
    read_guard = "parking_lot::lock_api::RwLockReadGuard<'_, parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>"
    if name == "MemoryCache::<K, T>::get::<K>":
        if (
            read == [Value("cache", "self.cache"), Value("lookup_key")]
            and state.publication is None
        ):
            return Value("tuple", items=(Value("none"), Value("cache_status")))
    if name == "ahash::RandomState::hash_one::<&K>":
        if (
            read == [Value("hasher", "self.cache.hasher"), Value("lookup_key")]
            and state.publication is None
        ):
            return Value("key", "hashed_key")
    if name == write.removesuffix("write") + "read":
        if (
            read == [Value("map", "self.lockers")]
            and state.publication is None
            and not state.locked
        ):
            state.locked = True
            return Value("read_guard", items=(Value("map", "self.lockers"),))
    if name == f"<{read_guard} as Deref>::deref":
        if (
            len(read) == 1
            and read[0]
            and read[0].sort == "read_guard"
            and state.locked
            and state.publication is None
        ):
            return Value("view", items=read[0].items)
    if name == "Option::<&Arc<CacheLock>>::cloned":
        if actual == [Value("none")] and state.publication is None:
            return Value("none")
    if name == write and len(read) == 1 and read[0] and read[0].sort == "map":
        state.locked = True
        return Value("write_guard", items=(read[0],))
    if name in {f"<{guard} as Deref>::deref", f"<{guard} as DerefMut>::deref_mut"}:
        if (
            len(read) == 1
            and read[0]
            and read[0].sort == "write_guard"
            and state.locked
        ):
            return Value("view", items=read[0].items)
    if name == "HashMap::<u64, Arc<CacheLock>>::get::<u64>":
        if [v.sort if v else None for v in read] == ["map", "key"] and state.locked:
            return Value("none")
    if name == "CacheLock::new_arc" and not actual:
        state.allocations += 1
        return Value("arc", str(state.allocations))
    if name == "<Arc<CacheLock> as Clone>::clone":
        if len(read) == 1 and read[0] and read[0].sort == "arc":
            return read[0]
    if name == "HashMap::<u64, Arc<CacheLock>>::insert" and len(actual) == 3:
        value = deref(actual[0], state)
        if (
            value
            and value.sort == "map"
            and [v.sort for v in actual[1:]] == ["key", "arc"]
            and state.locked
            and state.publication is None
        ):
            state.publication = (value, *actual[1:])
            return Value("removed")
    if name == "Option::<Arc<CacheLock>>::as_ref" and len(read) == 1:
        value = read[0]
        if value and value.sort == "some":
            return Value("some", items=(Value("view", items=value.items),))
        if value and value.sort == "none":
            return value
    match = re.fullmatch(
        r"Option::<&Arc<CacheLock>>::map::<CacheLockGuard<'_>, \{closure@([^}]+)}>",
        name,
    )
    if (
        match
        and len(actual) == 2
        and actual[1].sort == "closure"
        and actual[1].label == match[1]
    ):
        if actual[0].sort == "none":
            return actual[0]
        if actual[0].sort == "some":
            captures = tuple(deref(value, state) for value in actual[1].items)
            if any(value is None for value in captures):
                return "unknown closure capture"
            capture = Value(
                "closure",
                actual[1].label,
                tuple(Value("view", items=(v,)) for v in captures if v),
            )
            return construct(constructor, capture, actual[0].items[0])
    if name == "<CB as Lookup<K, T, S>>::lookup::<'_, '_, '_>" and len(actual) == 2:
        if deref(actual[0], state) == Value("lookup_key") and actual[1] == Value(
            "extra"
        ):
            return Value("future")
    if name.endswith(" as IntoFuture>::into_future") and actual == [Value("future")]:
        return actual[0]
    if name.startswith("Pin::<&mut Pin<Box<dyn Future<") and name.endswith(
        ">::new_unchecked"
    ):
        if len(read) == 1 and read[0] == Value("future"):
            return Value("pin", items=(actual[0],))
    if name.startswith("<Pin<Box<dyn Future<") and name.endswith(" as Future>::poll"):
        if (
            len(actual) == 2
            and actual[0].sort == "pin"
            and deref(actual[0].items[0], state) == Value("future")
            and deref(actual[1], state) == Value("context_raw")
        ):
            return Value("poll")
    return f"unsupported call or arguments: {name}"


def execute(
    program: dict[str, list[str]], entry: str, state: State, constructor: str
) -> State | str:
    """Follow evaluated branches until return; reject cycles and unknown operations."""
    visited: set[str] = set()
    block = entry
    while block not in visited:
        if block not in program:
            return f"missing block {block}"
        visited.add(block)
        state.trace.append(block)
        lines = program[block]
        next_block: str | None = None
        for index, line in enumerate(lines):
            terminal = False
            edge = re.fullmatch(
                r"(.+) -> \[return: (bb\d+), unwind(?: continue|: bb\d+)];", line
            )
            goto = re.fullmatch(r"goto -> (bb\d+);", line)
            switch = re.fullmatch(r"switchInt\((.+)\) -> \[(.+)];", line)
            if edge:
                drop = re.fullmatch(r"drop\((.+)\)", edge[1])
                pair = assignment(edge[1])
                invocation = re.fullmatch(r"(.+)\((.*)\)", pair[1]) if pair else None
                if drop:
                    value = evaluate(drop[1], state)
                    if (
                        value
                        and value.sort in {"write_guard", "read_guard"}
                        and state.locked
                    ):
                        state.locked = False
                    elif not value or value.sort != "removed":
                        return f"unsupported drop in {block}"
                    target = location(drop[1], state)
                    if target:
                        _ = state.env.pop(target, None)
                elif invocation and pair:
                    target = location(pair[0], state)
                    value = call(invocation[1], invocation[2], state, constructor)
                    if not target or isinstance(value, str):
                        return f"{block}: {value}"
                    state.env[target] = value
                else:
                    return f"unsupported call terminator in {block}"
                next_block, terminal = edge[2], True
            elif goto:
                next_block, terminal = goto[1], True
            elif switch:
                value = evaluate(switch[1], state)
                choices = [
                    (match[1], match[2])
                    for match in re.finditer(r"(\d+|otherwise): (bb\d+)", switch[2])
                ]
                if (
                    ", ".join(f"{key}: {target}" for key, target in choices)
                    != switch[2]
                    or not value
                    or value.sort != "int"
                    or len(dict(choices)) != len(choices)
                ):
                    return f"unsupported switch in {block}"
                targets = dict(choices)
                next_block = targets.get(value.label, targets.get("otherwise"))
                terminal = True
            elif line == "return;":
                if index != len(lines) - 1:
                    return "instruction after return"
                return state
            else:
                storage = re.fullmatch(r"Storage(Live|Dead)\((_\d+)\);", line)
                assign = assignment(line[:-1]) if line.endswith(";") else None
                discriminant = re.fullmatch(r"discriminant\((.+)\) = (\d+);", line)
                if storage:
                    _ = state.env.pop(storage[2], None)
                elif line == "nop;" or re.fullmatch(r"PlaceMention\(.+\);", line):
                    pass
                elif discriminant and evaluate(discriminant[1], state) == Value(
                    "frame"
                ):
                    state.env["state"] = Value("int", discriminant[2])
                elif assign:
                    target = location(assign[0], state)
                    value = evaluate(assign[1], state)
                    if not target or value is None:
                        return f"unsupported assignment in {block}: {line}"
                    state.env[target] = value
                else:
                    return f"unsupported instruction in {block}: {line}"
            if terminal:
                if index != len(lines) - 1 or not next_block:
                    return "invalid terminator"
        if next_block is None:
            return f"unterminated block {block}"
        block = next_block
    return "unsupported cycle"


def construct(text: str, capture: Value, arc: Value) -> Value | str:
    """Interpret the actual concrete closure, including its map/key projections."""
    parsed = blocks(text)
    if isinstance(parsed, str):
        return parsed
    match = re.match(
        r"fn .*\((_\d+): \{closure@([^}]+)}, (_\d+): &Arc<CacheLock>\)", text
    )
    if not match or match[2] != capture.label:
        return "unsupported constructor signature"
    result = execute(parsed, "bb0", State({match[1]: capture, match[3]: arc}), "")
    if isinstance(result, str):
        return result
    value = result.env.get("_0")
    return (
        Value("some", items=(value,))
        if value and value.sort == "guard"
        else "constructor did not return a guard"
    )


# 🧑 "the human requires proving the real code conforms to the spec, not only a model"
def check(
    resume: str, emitted: str, required_prefix: tuple[str, ...] | None = None
) -> str | None:
    """Check initial dispatch through cache/map misses, Pending and resumption."""
    program = blocks(resume)
    constructors = [
        body
        for body in functions(emitted)
        if "::get::{closure#0}::{closure#0}(" in body.splitlines()[0]
    ]
    frame = re.search(r"debug self => \(\(\(\*(_\d+)\) as variant#7\)\.0:", resume)
    if isinstance(program, str) or len(constructors) != 1 or not frame:
        return "unsupported function, constructor, or frame layout"
    constructor = constructors[0]
    initial = State(
        {
            "_1": Value("tuple", items=(Value("view", items=(Value("frame"),)),)),
            "_2": Value("context_raw"),
            "state": Value("int", "0"),
            "frame:input:0": Value("view", items=(Value("self"),)),
            "frame:input:1": Value("view", items=(Value("lookup_key"),)),
            "frame:input:2": Value("ttl"),
            "frame:input:3": Value("extra"),
        }
    )
    first = execute(program, "bb0", initial, constructor)
    if isinstance(first, str):
        return first
    if (
        required_prefix is not None
        and tuple(first.trace[: len(required_prefix)]) != required_prefix
    ):
        return "interpreted execution does not cover the unique insertion prefix"
    expected = (
        Value("some", items=(Value("guard", items=first.publication),))
        if first.publication
        else None
    )
    if (
        not expected
        or first.env.get("frame:7:8") != expected
        or first.env.get("_0") != Value("pending")
        or first.env.get("state") != Value("int", "7")
        or first.locked
    ):
        return "Pending lacks the matching guard or expected suspension state"
    retained = {
        key: value
        for key, value in first.env.items()
        if key.startswith("frame:") or key == "state"
    }
    resumed = State(dict(retained), first.publication, allocations=first.allocations)
    resumed.env.update(
        {
            "_1": Value("tuple", items=(Value("view", items=(Value("frame"),)),)),
            "_2": Value("context_raw"),
        }
    )
    second = execute(program, "bb0", resumed, constructor)
    if isinstance(second, str):
        return second
    after = {
        key: value
        for key, value in second.env.items()
        if key.startswith("frame:") or key == "state"
    }
    if (
        after != retained
        or second.publication != first.publication
        or second.env.get("_0") != Value("pending")
        or second.locked
    ):
        return "resume does not preserve the guarded Pending invariant"
    return None


def main() -> int:
    """Read paired compiler MIR artifacts and report this conditional check."""
    if len(sys.argv) != 3:
        print(
            "usage: python -m verification.async_cancel.publication_mir RESUME.mir EMITTED.mir"
        )
        return 2
    error = check(Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text())
    print(
        f"publication check failed: {error}"
        if error
        else "conditional publication dataflow accepted; see PUBLICATION_MIR.md"
    )
    return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(main())
