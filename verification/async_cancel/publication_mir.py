"""Check direct publication over cache/map outcomes under normal returns."""

import re
import sys
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

from verification.async_cancel.cleanup_mir_check import functions
from verification.async_cancel.mir_blocks import blocks


@dataclass(frozen=True)
class Value:
    """A symbolic value, reference location, or aggregate with explicit sort."""

    sort: str
    label: str = ""
    items: tuple["Value", ...] = ()


@dataclass(frozen=True)
class FrameLayout:
    """Capture values and suspension slots checked against compiler metadata."""

    inputs: dict[str, Value]
    initial_state: str
    guard_slot: str
    guard_state: str


def frame_layout(resume: str, emitted: str) -> FrameLayout | str:
    """Cross-check factory operands, raw debug fields and saved layout declarations."""
    factories = [
        body
        for body in functions(emitted)
        if re.match(r"fn read_through::[^\n(]+::get\(", body)
    ]
    if len(factories) != 1:
        return "missing unique coroutine factory"
    factory = factories[0]
    signature = re.match(
        r"fn .*::get\((_\d+): &RTCache<K, T, CB, S>, (_\d+): &K, (_\d+): Option<Duration>, (_\d+): Option<&S>\) -> \{async fn body of RTCache<K, T, CB, S>::get\(\)\} \{",
        factory,
    )
    parsed = blocks(factory)
    if not signature or isinstance(parsed, str) or set(parsed) != {"bb0"}:
        return "unsupported coroutine factory signature or body"
    lines = parsed["bb0"]
    aggregate = re.fullmatch(r"_0 = \{coroutine@[^}]+\} \{ (.+) \};", lines[0])
    if len(lines) != 2 or lines[1] != "return;" or not aggregate:
        return "unsupported coroutine capture initialization"
    roles = ("self", "key", "ttl", "extra")
    types = ("&RTCache<K, T, CB, S>", "&K", "Option<Duration>", "Option<&S>")
    values = (
        Value("view", items=(Value("self"),)),
        Value("view", items=(Value("lookup_key"),)),
        Value("ttl"),
        Value("extra"),
    )
    params = dict(zip(signature.groups(), values, strict=True))
    captures: list[tuple[str, str]] = re.findall(
        r"(\w+): (?:copy|move) (_\d+)", aggregate[1]
    )
    if len(captures) != 4 or {name for name, _ in captures} != set(roles):
        return "unsupported coroutine capture fields"
    if not re.fullmatch(
        r"\w+: (?:copy|move) _\d+(?:, \w+: (?:copy|move) _\d+){3}", aggregate[1]
    ):
        return "unsupported coroutine capture operands"
    inputs: dict[str, Value] = {}
    pointers: set[str] = set()
    for index, (name, operand) in enumerate(captures):
        debug: list[tuple[str, str, str]] = re.findall(
            rf"^    debug {name} => \(\(\*(_\d+)\)\.(\d+): (.+)\);$",
            resume,
            re.MULTILINE,
        )
        role = roles.index(name)
        if (
            len(debug) != 1
            or debug[0][1] != str(index)
            or short_type(debug[0][2]) != types[role]
        ):
            return "raw capture debug projection disagrees with factory"
        if params.get(operand) != values[role]:
            return "factory captures the wrong parameter"
        pointers.add(debug[0][0])
        inputs[f"frame:input:{index}"] = params[operand]
    fields: list[tuple[str, str]] = re.findall(
        r"^        field (_s\d+): (.+);$", resume, re.MULTILINE
    )
    declared = dict(fields)
    variants: list[tuple[str, str]] = re.findall(
        r"^            \w+\s*\((\d+)\): \[([^]]*)\],$", resume, re.MULTILINE
    )
    slots = {
        state: entries.split(", ") if entries else [] for state, entries in variants
    }
    unresumed: list[str] = re.findall(
        r"^            Unresumed\((\d+)\): \[\],$", resume, re.MULTILINE
    )
    if (
        len(declared) != len(fields)
        or len(slots) != len(variants)
        or len(unresumed) != 1
    ):
        return "invalid coroutine field or variant declarations"
    saved: dict[str, tuple[str, str]] = {}
    for name, ty in zip(
        (*roles, "hashed_key", "_guard"),
        (*types, "u64", "Option<CacheLockGuard<'_>>"),
        strict=True,
    ):
        identities: list[str] = re.findall(
            rf"coroutine debug {name} => (_s\d+);", resume
        )
        projections: list[tuple[str, str, str, str]] = re.findall(
            rf"debug {name} => \(\(\(\*(_\d+)\) as variant#(\d+)\)\.(\d+): (.+)\);",
            resume,
        )
        if (
            len(identities) != 1
            or len(projections) != 1
            or declared.get(identities[0]) != ty
        ):
            return "saved field lacks matching typed compiler identity"
        pointer, variant, index, projected_type = projections[0]
        entries = slots.get(variant, [])
        if (
            pointer not in pointers
            or int(index) >= len(entries)
            or entries[int(index)] != identities[0]
            or short_type(projected_type) != ty
        ):
            return "saved projection disagrees with coroutine layout"
        saved[name] = (variant, index)
    if len(pointers) != 1:
        return "capture projections disagree on frame pointer"
    variant, index = saved["_guard"]
    return FrameLayout(inputs, unresumed[0], f"frame:{variant}:{index}", variant)


def short_type(text: str) -> str:
    """Normalize only namespace prefixes differing between these MIR printouts."""
    return re.sub(r"(?:std::option::|std::time::|read_through::)", "", text)


@dataclass
class State:
    """Concrete symbolic path, including its historical publication identity."""

    env: dict[str, Value] = field(default_factory=dict)
    publication: tuple[Value, ...] | None = None
    locked: bool = False
    allocations: int = 0
    trace: list[str] = field(default_factory=list)
    hits: tuple[bool, ...] = ()
    gets: int = 0
    no_publication_exit: bool = False
    allocation_body: bool = False

    def get_result(self, payload: Value) -> Value | str:
        """Select one enumerated get result; reject unbounded additional gets."""
        if self.gets == len(self.hits):
            return "get result schedule exhausted"
        hit = self.hits[self.gets]
        self.gets += 1
        return Value("some", items=(payload,)) if hit else Value("none")


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
    match = re.fullmatch(r"const (\d+)_usize", text)
    if match:
        return Value("usize", match[1])
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
    match = re.fullmatch(r"CacheLock \{ lock_start: (.+), lock: (.+) }", text)
    if match:
        values = [evaluate(arg, state) for arg in match.groups()]
        if [value.sort if value else None for value in values] == [
            "instant",
            "semaphore",
        ]:
            return Value(
                "cache_lock",
                items=tuple(value for value in values if value is not None),
            )
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
    values = [evaluate(arg, state) for arg in args.split(", ")] if args else []
    if any(value is None for value in values):
        return "unknown call argument"
    actual = [value for value in values if value is not None]
    if state.allocation_body:
        if name == "Semaphore::new" and len(actual) == 1 and actual[0].sort == "usize":
            return Value("semaphore", actual[0].label)
        if name == "std::time::Instant::now" and not actual:
            return Value("instant")
        if (
            name == "Arc::<CacheLock>::new"
            and len(actual) == 1
            and actual[0].sort == "cache_lock"
        ):
            state.allocations += 1
            return Value("arc", str(state.allocations), tuple(actual))
        return "unsupported allocation primitive or arguments"
    if not constructor and name != "<Arc<CacheLock> as Clone>::clone":
        return "unsupported constructor call"
    read = [deref(value, state) for value in actual]
    write = "parking_lot::lock_api::RwLock::<parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>::write"
    guard = "parking_lot::lock_api::RwLockWriteGuard<'_, parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>"
    read_guard = "parking_lot::lock_api::RwLockReadGuard<'_, parking_lot::RawRwLock, HashMap<u64, Arc<CacheLock>>>"
    if (
        name == "MemoryCache::<K, T>::get::<K>"
        and read == [Value("cache", "self.cache"), Value("lookup_key")]
        and state.publication is None
    ):
        result = state.get_result(Value("cached_value"))
        if isinstance(result, str):
            return result
        return Value("tuple", items=(result, Value("cache_status")))
    if (
        name == "ahash::RandomState::hash_one::<&K>"
        and read == [Value("hasher", "self.cache.hasher"), Value("lookup_key")]
        and state.publication is None
    ):
        return Value("key", "hashed_key")
    if (
        name == write.removesuffix("write") + "read"
        and read == [Value("map", "self.lockers")]
        and state.publication is None
        and not state.locked
    ):
        state.locked = True
        return Value("read_guard", items=(Value("map", "self.lockers"),))
    if (
        name == f"<{read_guard} as Deref>::deref"
        and len(read) == 1
        and read[0]
        and read[0].sort == "read_guard"
        and state.locked
        and state.publication is None
    ):
        return Value("view", items=read[0].items)
    if (
        name == "Option::<&Arc<CacheLock>>::cloned"
        and len(actual) == 1
        and state.publication is None
    ):
        if actual[0] == Value("none"):
            return actual[0]
        if actual[0].sort == "some" and len(actual[0].items) == 1:
            arc = deref(actual[0].items[0], state)
            if arc and arc.sort == "arc":
                return Value("some", items=(arc,))
    if name == write and len(read) == 1 and read[0] and read[0].sort == "map":
        state.locked = True
        return Value("write_guard", items=(read[0],))
    if (
        name in {f"<{guard} as Deref>::deref", f"<{guard} as DerefMut>::deref_mut"}
        and len(read) == 1
        and read[0]
        and read[0].sort == "write_guard"
        and state.locked
    ):
        return Value("view", items=read[0].items)
    if (
        name == "HashMap::<u64, Arc<CacheLock>>::get::<u64>"
        and [v.sort if v else None for v in read] == ["map", "key"]
        and state.locked
    ):
        return state.get_result(
            Value("view", items=(Value("arc", f"existing:{state.gets}"),))
        )
    if name == "CacheLock::new_arc" and not actual:
        state.allocations += 1
        return Value("arc", str(state.allocations))
    if (
        name == "<Arc<CacheLock> as Clone>::clone"
        and len(read) == 1
        and read[0]
        and read[0].sort == "arc"
    ):
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
    if (
        name == "<CB as Lookup<K, T, S>>::lookup::<'_, '_, '_>"
        and len(actual) == 2
        and deref(actual[0], state) == Value("lookup_key")
        and actual[1] == Value("extra")
    ):
        return Value("future")
    if name.endswith(" as IntoFuture>::into_future") and actual == [Value("future")]:
        return actual[0]
    if (
        name.startswith("Pin::<&mut Pin<Box<dyn Future<")
        and name.endswith(">::new_unchecked")
        and len(read) == 1
        and read[0] == Value("future")
    ):
        return Value("pin", items=(actual[0],))
    if (
        name.startswith("<Pin<Box<dyn Future<")
        and name.endswith(" as Future>::poll")
        and len(actual) == 2
        and actual[0].sort == "pin"
        and deref(actual[0].items[0], state) == Value("future")
        and deref(actual[1], state) == Value("context_raw")
    ):
        return Value("poll")
    return f"unsupported call or arguments: {name}"


def execute(
    program: dict[str, list[str]],
    entry: str,
    state: State,
    constructor: str,
    insertion_prefix: frozenset[str] | None = None,
) -> State | str:
    """Run until return or a graph-proved exit from all direct-insertion paths."""
    visited: set[str] = set()
    block = entry
    while block not in visited:
        if block not in program:
            return f"missing block {block}"
        if (
            insertion_prefix is not None
            and state.publication is None
            and block not in insertion_prefix
        ):
            state.no_publication_exit = True
            return state
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
            if terminal and (index != len(lines) - 1 or not next_block):
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


def check_allocation(emitted: str) -> str | None:
    """Derive the fresh zero-permit Arc contract from the actual new_arc body."""
    candidates = [
        body
        for body in functions(emitted)
        if re.match(r"fn read_through::[^\n(]+::new_arc\(", body)
    ]
    if len(candidates) != 1 or not re.fullmatch(
        r"fn read_through::[^\n(]+::new_arc\(\) -> Arc<CacheLock> \{",
        candidates[0].splitlines()[0],
    ):
        return "unsupported new_arc signature"
    program = blocks(candidates[0])
    if isinstance(program, str):
        return program
    result = execute(program, "bb0", State(allocation_body=True), "")
    if isinstance(result, str):
        return result
    lock = Value("cache_lock", items=(Value("instant"), Value("semaphore", "0")))
    if result.allocations != 1 or result.env.get("_0") != Value("arc", "1", (lock,)):
        return "new_arc does not return its fresh zero-permit CacheLock allocation"
    return None


@dataclass
class PublicationProgram:
    """Validated syntax and structural coverage, without ownership conclusions."""

    blocks: dict[str, list[str]]
    constructor: str
    prefix: tuple[str, ...]
    layout: FrameLayout


@dataclass
class PublicationTrace:
    """Actual abstract outputs before and after one Pending resumption."""

    first: State
    second: State


def prepare(
    resume: str, emitted: str, required_prefix: tuple[str, ...] | None = None
) -> PublicationProgram | str:
    """Validate structural, layout and allocation premises without checking ownership."""
    from verification.async_cancel.entry_coverage import check as entry_check

    prefix = entry_check(resume)
    if isinstance(prefix, str):
        return prefix
    if required_prefix is not None and prefix != required_prefix:
        return "provided insertion prefix differs from structural coverage"
    allocation_error = check_allocation(emitted)
    if allocation_error:
        return allocation_error
    program = blocks(resume)
    constructors = [
        body
        for body in functions(emitted)
        if "::get::{closure#0}::{closure#0}(" in body.splitlines()[0]
    ]
    layout = frame_layout(resume, emitted)
    if isinstance(layout, str):
        return layout
    if isinstance(program, str) or len(constructors) != 1:
        return "unsupported function, constructor, or frame layout"
    return PublicationProgram(program, constructors[0], prefix, layout)


# 🧑 "the human requires proving the real code conforms to the spec, not only a model"
def check(
    resume: str, emitted: str, required_prefix: tuple[str, ...] | None = None
) -> str | None:
    """Enumerate cache/map outcomes and check every direct-publication case."""
    prepared = prepare(resume, emitted, required_prefix)
    if isinstance(prepared, str):
        return prepared
    published = False
    for hits in product((False, True), repeat=3):
        result = check_case(
            prepared.blocks,
            prepared.constructor,
            prepared.prefix,
            hits,
            prepared.layout,
        )
        if isinstance(result, str):
            return result
        published |= result
    return None if published else "no enumerated execution covers direct insertion"


def trace_case(
    program: dict[str, list[str]],
    constructor: str,
    prefix: tuple[str, ...],
    hits: tuple[bool, ...],
    layout: FrameLayout,
) -> PublicationTrace | str | None:
    """Interpret actual outcomes without asserting guard equality or preservation."""
    initial = State(
        {
            "_1": Value("tuple", items=(Value("view", items=(Value("frame"),)),)),
            "_2": Value("context_raw"),
            "state": Value("int", layout.initial_state),
            **layout.inputs,
        },
        hits=hits,
    )
    first = execute(program, "bb0", initial, constructor, frozenset(prefix))
    if isinstance(first, str):
        return first
    if first.publication is None:
        return (
            None if first.no_publication_exit else "unjustified no-publication outcome"
        )
    if tuple(first.trace[: len(prefix)]) != prefix:
        return "interpreted execution does not cover the unique insertion prefix"
    retained = retained_env(first)
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
    return PublicationTrace(first, second)


def retained_env(state: State) -> dict[str, Value]:
    """Project the abstract coroutine storage retained between polls."""
    return {
        key: value
        for key, value in state.env.items()
        if key.startswith("frame:") or key == "state"
    }


def check_case(
    program: dict[str, list[str]],
    constructor: str,
    prefix: tuple[str, ...],
    hits: tuple[bool, ...],
    layout: FrameLayout,
) -> bool | str:
    """Check the historical Python ownership conditions on an unfiltered trace."""
    trace = trace_case(program, constructor, prefix, hits, layout)
    if isinstance(trace, str):
        return trace
    if trace is None:
        return False
    first, second = trace.first, trace.second
    expected = Value("some", items=(Value("guard", items=first.publication or ()),))
    if (
        first.env.get(layout.guard_slot) != expected
        or first.env.get("_0") != Value("pending")
        or first.env.get("state") != Value("int", layout.guard_state)
        or first.locked
    ):
        return "Pending lacks the matching guard or expected suspension state"
    if (
        retained_env(second) != retained_env(first)
        or second.publication != first.publication
        or second.env.get("_0") != Value("pending")
        or second.locked
    ):
        return "resume does not preserve the guarded Pending invariant"
    return True


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
