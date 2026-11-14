"""Check guard-slot destruction on normal-return paths in rustc coroutine MIR.

This checks a control-flow property, not guard initialization or cleanup effects.
Input must be the paired coroutine_resume/coroutine_drop dumps from one build.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Block:
    body: str
    terminal: str
    successors: tuple[tuple[int, bool], ...]


def blocks(text: str) -> dict[int, Block]:
    result: dict[int, Block] = {}
    for match in re.finditer(
        r"^    bb(\d+)(?: \(cleanup\))?: \{\n(.*?)^    \}", text, re.M | re.S
    ):
        body = match[2].strip()
        terminal = body.splitlines()[-1].strip()
        if terminal in {"return;", "resume;", "unreachable;"}:
            successors = ()
        elif " -> " in terminal and terminal.endswith(";"):
            successors = tuple(
                (int(m[2]), m[1] is not None)
                for m in re.finditer(r"(return: )?\bbb(\d+)\b", terminal)
            )
            if not successors:
                raise ValueError(f"no recognized successor: {terminal}")
        else:
            raise ValueError(f"unsupported terminator: {terminal}")
        index = int(match[1])
        if index in result:
            raise ValueError(f"duplicate block bb{index}")
        result[index] = Block(body, terminal, successors)
    if not result or 0 not in result:
        raise ValueError("missing entry block")
    for block in result.values():
        if any(target not in result for target, _ in block.successors):
            raise ValueError("successor is not a parsed block")
    return result


def check(resume: str, drop: str, guard: str) -> list[str]:
    """Prove the finite graph property, conditional on faithful MIR parsing."""
    names: list[str] = []
    for text, kind in ((resume, "coroutine_resume"), (drop, "coroutine_drop")):
        match = re.search(r"^// MIR for `(.+)` 0 " + kind + r"$", text, re.M)
        if not match:
            raise ValueError(f"expected {kind} dump")
        names.append(match[1])
    if names[0] != names[1]:
        raise ValueError("dumps describe different functions")
    fields = {
        m[1]: m[2] for m in re.finditer(r"^        field (_s\d+): (.+);$", resume, re.M)
    }
    variants = re.finditer(
        r"^            Suspend\d+ \((\d+)\): \[([^]]*)\],$", resume, re.M
    )
    graph = blocks(drop)
    entry = graph[0]
    entry_lines = [line.strip() for line in entry.body.splitlines()]
    selector = re.fullmatch(r"(_\d+) = discriminant\(\(\*_1\)\);", entry_lines[0])
    if (
        len(entry_lines) != 2
        or not selector
        or not entry.terminal.startswith(f"switchInt(move {selector[1]}) -> [")
    ):
        raise ValueError("unsupported coroutine entry dispatch")
    targets = {
        int(m[1]): int(m[2]) for m in re.finditer(r"(\d+): bb(\d+)", entry.terminal)
    }
    reports: list[str] = []
    checked = 0
    for variant_match in variants:
        variant = int(variant_match[1])
        slots = [s.strip() for s in variant_match[2].split(",") if s.strip()]
        if any(slot not in fields for slot in slots):
            raise ValueError("variant contains an unknown layout field")
        guard_slots = [
            i
            for i, slot in enumerate(slots)
            if re.search(r"\b" + re.escape(guard) + r"\b", fields[slot])
        ]
        if not guard_slots:
            reports.append(f"variant {variant}: no {guard} slot; no cleanup claim")
            continue
        if variant not in targets:
            raise ValueError(f"missing explicit drop entry for variant {variant}")
        for slot in guard_slots:
            place = re.compile(
                r"drop\(\(\(\(\*_1\) as variant#"
                + str(variant)
                + r"\)\."
                + str(slot)
                + r": .+\)\) -> \[return: bb(\d+),"
            )
            pending = [(targets[variant], False)]
            visited: set[tuple[int, bool]] = set()
            normal_returns = 0
            while pending:
                node, completed = pending.pop()
                if (node, completed) in visited:
                    continue
                visited.add((node, completed))
                block = graph[node]
                if not completed:
                    preserve_guard(block, variant, slot)
                if block.terminal == "return;":
                    if not completed:
                        raise ValueError(
                            f"variant {variant} slot {slot}: normal return at bb{node} without guard-slot drop"
                        )
                    normal_returns += 1
                match = place.match(block.terminal)
                for successor, normal_edge in block.successors:
                    pending.append(
                        (successor, completed or (match is not None and normal_edge))
                    )
            if not normal_returns:
                raise ValueError(
                    f"variant {variant} slot {slot}: no normal return; refusing vacuous result"
                )
            checked += 1
            reports.append(
                f"variant {variant} slot {slot}: every normal return follows successful guard-slot drop"
            )
    if not checked:
        raise ValueError(f"no suspended {guard} slot found")
    return reports


def preserve_guard(block: Block, variant: int, slot: int) -> None:
    """Reject instructions that could change or expose the live guard slot.

    The supported drop glue only updates boolean flags, manages local storage,
    branches, and drops direct frame fields. Other field destructors must obey
    Rust aliasing and cannot access the parent's private guard slot.
    """
    flag = re.compile(
        r"\(\(\(\*_1\) as variant#(\d+)\)\.(\d+): bool\) = const (?:false|true);"
    )
    for statement in block.body.splitlines()[:-1]:
        statement = statement.strip()
        if re.fullmatch(
            r"nop;|Storage(?:Live|Dead)\(_\d+\);|_\d+ = const (?:false|true);",
            statement,
        ):
            continue
        match = flag.fullmatch(statement)
        if match and int(match[1]) == variant and int(match[2]) != slot:
            continue
        raise ValueError(f"unsupported statement before guard drop: {statement}")
    terminal = block.terminal
    if terminal in {"return;", "resume;", "unreachable;"}:
        return
    if re.fullmatch(r"goto -> bb\d+;", terminal):
        return
    if re.fullmatch(
        rf"drop\(\(\(\(\*_1\) as variant#{variant}\)\.\d+: .+\)\) -> \[.+\];",
        terminal,
    ):
        return
    if re.fullmatch(r"switchInt\((?:copy|move) _\d+\) -> \[.+\];", terminal):
        return
    raise ValueError(f"unsupported terminator before guard drop: {terminal}")


def main() -> int:
    if len(sys.argv) != 5 or sys.argv[3] != "--guard":
        print("usage: check_drop_paths.py RESUME.mir DROP.mir --guard TYPE")
        print(__doc__)
        return 0 if sys.argv[1:] == ["--help"] else 2
    try:
        reports = check(
            Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text(), sys.argv[4]
        )
    except (ValueError, OSError) as error:
        print(f"check failed: {error}", file=sys.stderr)
        return 1
    for report in reports:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
