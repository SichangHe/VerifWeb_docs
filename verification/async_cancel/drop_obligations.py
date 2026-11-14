"""Generate Verus certificates for actual cancellation control-flow graphs."""

import re
from dataclasses import dataclass

from verification.async_cancel.check_drop_paths import Block, blocks, preserve_guard


@dataclass(frozen=True)
class Claim:
    """One suspended guard slot and its compiler-selected cancellation entry."""

    variant: int
    slot: int
    entry: int


def claims(resume: str, drop: str, graph: dict[int, Block], guard: str) -> list[Claim]:
    """Read paired compiler metadata without invoking the Python safety check."""
    names: list[str] = []
    for text, kind in ((resume, "coroutine_resume"), (drop, "coroutine_drop")):
        name = re.search(r"^// MIR for `(.+)` 0 " + kind + r"$", text, re.MULTILINE)
        if not name:
            raise ValueError(f"expected {kind} dump")
        names.append(name[1])
    if names[0] != names[1]:
        raise ValueError("dumps describe different functions")
    entry = [line.strip() for line in graph[0].body.splitlines()]
    selector = re.fullmatch(r"(_\d+) = discriminant\(\(\*_1\)\);", entry[0])
    if (
        len(entry) != 2
        or not selector
        or not entry[1].startswith(f"switchInt(move {selector[1]}) -> [")
    ):
        raise ValueError("unsupported coroutine entry dispatch")
    targets = {int(m[1]): int(m[2]) for m in re.finditer(r"(\d+): bb(\d+)", entry[1])}
    fields = {
        match[1]: match[2]
        for match in re.finditer(
            r"^        field (_s\d+): (.+);$", resume, re.MULTILINE
        )
    }
    result: list[Claim] = []
    for match in re.finditer(
        r"^            Suspend\d+ \((\d+)\): \[([^]]*)\],$", resume, re.MULTILINE
    ):
        variant, slots = match[1], match[2]
        for index, slot in enumerate(s.strip() for s in slots.split(",") if s.strip()):
            if slot not in fields:
                raise ValueError("variant contains an unknown layout field")
            if re.search(r"\b" + re.escape(guard) + r"\b", fields[slot]):
                if int(variant) not in targets:
                    raise ValueError("missing guard variant dispatch")
                result.append(Claim(int(variant), index, targets[int(variant)]))
    if not result:
        raise ValueError("no suspended guard slot found")
    return result


def certificate(graph: dict[int, Block], claim: Claim) -> str:
    """Propose reachable states; Verus checks closure and return safety separately."""
    place = re.compile(
        rf"drop\(\(\(\(\*_1\) as variant#{claim.variant}\)\.{claim.slot}: .+\)\) -> \[return: bb\d+,"
    )
    edges = [
        (node, target, bool(place.match(block.terminal)) and normal)
        for node, block in sorted(graph.items())
        for target, normal in block.successors
    ]
    pending = [(claim.entry, False)]
    reached: set[tuple[int, bool]] = set()
    while pending:
        node, completed = pending.pop()
        if (node, completed) in reached:
            continue
        reached.add((node, completed))
        if not completed:
            preserve_guard(graph[node], claim.variant, claim.slot)
        pending.extend(
            (target, completed or finishes)
            for source, target, finishes in edges
            if source == node
        )
    returns = [node for node, block in graph.items() if block.terminal == "return;"]
    if not any(node in returns for node, _ in reached):
        raise ValueError("no reachable normal return; refusing vacuous result")
    invariant = " ||\n        ".join(
        f"(node == {node} && completed == {str(done).lower()})"
        for node, done in sorted(reached)
    )
    relation = (
        " ||\n        ".join(
            f"(node == {source} && next == {target} && after == (completed || {str(finishes).lower()}))"
            for source, target, finishes in edges
        )
        or "false"
    )
    terminal = " || ".join(f"node == {node}" for node in returns) or "false"
    name = f"drop_v{claim.variant}_s{claim.slot}"
    return f"""
pub open spec fn {name}_inv(node: int, completed: bool) -> bool {{
    {invariant}
}}

pub open spec fn {name}_edge(node: int, completed: bool, next: int, after: bool) -> bool {{
    {relation}
}}

pub open spec fn {name}_return(node: int) -> bool {{ {terminal} }}

proof fn {name}_initial()
    ensures {name}_inv({claim.entry}, false),
{{}}

proof fn {name}_preserved(node: int, completed: bool, next: int, after: bool)
    requires {name}_inv(node, completed), {name}_edge(node, completed, next, after),
    ensures {name}_inv(next, after),
{{}}

proof fn {name}_safe(node: int, completed: bool)
    requires {name}_inv(node, completed), {name}_return(node),
    ensures completed,
{{}}

pub proof fn {name}_finite_path(path: Seq<(int, bool)>, end: int)
    requires
        0 <= end < path.len(),
        path[0] == ({claim.entry}int, false),
        forall|i: int| 0 <= i < end ==> #[trigger] {name}_edge(
            path[i].0, path[i].1, path[i + 1].0, path[i + 1].1),
    ensures
        {name}_inv(path[end].0, path[end].1),
        {name}_return(path[end].0) ==> path[end].1,
    decreases end,
{{
    if end == 0 {{
        {name}_initial();
    }} else {{
        {name}_finite_path(path, end - 1);
        assert({name}_edge(path[end - 1].0, path[end - 1].1,
            path[(end - 1) + 1].0, path[(end - 1) + 1].1));
        {name}_preserved(path[end - 1].0, path[end - 1].1, path[end].0, path[end].1);
    }}
    if {name}_return(path[end].0) {{
        {name}_safe(path[end].0, path[end].1);
    }}
}}
"""


# 🧑 "the human requires proving the real code conforms to the spec, not only a model"
def generate(
    resume: str, drop: str, variant: int, slot: int
) -> tuple[str | None, str | None]:
    """Return Verus items or unsupported-input error; safety is left to Verus."""
    try:
        graph = blocks(drop)
        selected = [
            claim
            for claim in claims(resume, drop, graph, "CacheLockGuard")
            if (claim.variant, claim.slot) == (variant, slot)
        ]
        if len(selected) != 1:
            return None, "selected slot is not a unique suspended CacheLockGuard"
        return certificate(graph, selected[0]), None
    except ValueError as error:
        return None, str(error)
