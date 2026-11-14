"""Check direct publication coverage and callback Ready control flow in get MIR."""

import re
import sys
from pathlib import Path

from verification.async_cancel.publication_mir import blocks


def graph(program: dict[str, list[str]]) -> dict[str, set[str]] | str:
    """Read normal successors, rejecting unknown terminators and missing targets."""
    result: dict[str, set[str]] = {}
    for name, lines in program.items():
        terminal = lines[-1]
        if terminal in {"return;", "resume;", "unreachable;"}:
            targets: set[str] = set()
        elif re.fullmatch(r"goto -> bb\d+;", terminal):
            targets = set(re.findall(r"bb\d+", terminal))
        elif re.fullmatch(
            r"switchInt\(.+\) -> \[(?:\d+: bb\d+, )*otherwise: bb\d+];", terminal
        ):
            targets = set(re.findall(r": (bb\d+)", terminal))
        elif re.fullmatch(
            r".+ -> \[(?:return|success): bb\d+, unwind(?:: bb\d+| continue| terminate\(cleanup\))];",
            terminal,
        ):
            targets = set(re.findall(r"(?:return|success): (bb\d+)", terminal))
        else:
            return f"unsupported terminator in {name}: {terminal}"
        if not targets <= program.keys():
            return f"missing successor in {name}"
        if any(" -> " in line for line in lines[:-1]):
            return f"instruction after terminator in {name}"
        result[name] = targets
    return result


def reachable(edges: dict[str, set[str]], start: str, cut: str = "") -> set[str]:
    """Compute finite graph reachability, optionally removing one block."""
    seen: set[str] = set()
    todo = [start]
    while todo:
        block = todo.pop()
        if block != cut and block not in seen:
            seen.add(block)
            todo.extend(edges[block] - seen)
    return seen


# 🧑 "the human requires proving the real code conforms to the spec, not only a model"
def check(resume: str) -> tuple[str, ...] | str:
    """Bound the structural gap around the separate bb14 publication interpreter."""
    program = blocks(resume)
    if isinstance(program, str):
        return program
    edges = graph(program)
    if isinstance(edges, str):
        return edges
    if not {"bb0", "bb14"} <= program.keys():
        return "missing function or interpreted entry"
    inserts = [
        name
        for name, lines in program.items()
        for line in lines
        if re.search(r"HashMap::<.*>::insert\(", line)
    ]
    if len(inserts) != 1:
        return "expected exactly one direct HashMap insert site"
    site = inserts[0]
    if site not in reachable(edges, "bb14") or site not in reachable(edges, "bb0"):
        return "insert is not reachable through the interpreted entry"
    if site in reachable(edges, "bb0", "bb14"):
        return "insert bypasses the interpreted entry"
    predecessors: dict[str, set[str]] = {name: set() for name in edges}
    for name, successors in edges.items():
        for successor in successors:
            predecessors[successor].add(name)
    prefix_nodes = reachable(predecessors, site) & reachable(edges, "bb0")
    prefix: list[str] = []
    current = "bb0"
    while current != site:
        if current in prefix:
            return "cycle before insertion"
        prefix.append(current)
        successors = edges[current] & prefix_nodes
        if len(successors) != 1:
            return "multiple paths to insertion"
        current = next(iter(successors))
    prefix.append(site)
    pending: set[str] = set()
    polls: list[tuple[str, str]] = []
    for name, lines in program.items():
        for line in lines:
            if re.search(r"\b_0\b", line):
                if re.fullmatch(r"_0 = Poll::<.+>::Pending;", line):
                    pending.add(name)
                elif not re.fullmatch(r"_0 = Poll::<.+>::Ready\(move _\d+\);", line):
                    return f"unsupported return-place access in {name}"
            if "<Pin<Box<dyn Future<" not in line or " as Future>::poll(" not in line:
                continue
            match = re.fullmatch(
                r"(_\d+) = <Pin<Box<dyn Future<.* as Future>::poll\(.*\) -> \[return: (bb\d+), unwind(?:: bb\d+| continue| terminate\(cleanup\))];",
                line,
            )
            if not match:
                return f"unsupported callback poll in {name}"
            polls.append((match[1], match[2]))
    if not polls or not pending:
        return "missing callback polls or suspension sites"
    for local, dispatch in polls:
        lines = program[dispatch]
        discriminants = [
            match[1]
            for line in lines
            if (match := re.fullmatch(rf"(_\d+) = discriminant\({local}\);", line))
        ]
        if len(discriminants) != 1:
            return f"unsupported callback discriminant in {dispatch}"
        if lines[-2] != f"{discriminants[0]} = discriminant({local});":
            return f"callback discriminant is not adjacent to dispatch in {dispatch}"
        for line in lines[:-2]:
            storage = re.fullmatch(r"StorageDead\((_\d+)\);", line)
            if line == f"PlaceMention({local});":
                continue
            if storage and storage[1] not in {local, discriminants[0]}:
                continue
            return f"unsupported callback dispatch prefix in {dispatch}"
        branch = re.fullmatch(
            rf"switchInt\(move {discriminants[0]}\) -> \[0: (bb\d+), 1: bb\d+, otherwise: bb\d+];",
            lines[-1],
        )
        if not branch:
            return f"unsupported callback dispatch in {dispatch}"
        ready = branch[1]
        after = reachable(edges, ready)
        if after & pending:
            return f"callback Ready in {ready} can reach Pending"
        if site in after:
            return f"callback Ready in {ready} can reach insertion"
    return tuple(prefix)


def main() -> int:
    """Read the actual compiler artifact and report only structural coverage."""
    if len(sys.argv) != 2:
        print("usage: python -m verification.async_cancel.entry_coverage RESUME.mir")
        return 2
    result = check(Path(sys.argv[1]).read_text())
    print(
        result
        if isinstance(result, str)
        else "structural entry coverage accepted; see ENTRY_COVERAGE.md"
    )
    return int(isinstance(result, str))


if __name__ == "__main__":
    raise SystemExit(main())
