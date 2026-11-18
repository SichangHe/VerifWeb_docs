"""Real-artifact tests for unwind_mir.py; see UNWIND.md.

Usage: python -m verification.async_cancel.unwind_mir_test FIXED_DUMP_DIR PARENT_DUMP_DIR
(each is a `-Zdump-mir-dir` from real_pingora/build_unwind.sh)
"""

import re
import sys
from pathlib import Path

from verification.async_cancel.unwind_mir import NO_UNWIND, analyze, bad

WINDOW = {"guard-ctor", "option-as-ref", "drop-lock-values", "guard-drop"}


def pair(directory: str) -> tuple[str, str]:
    found = []
    for kind in ("coroutine_resume", "coroutine_drop"):
        files = list(Path(directory).glob(f"*-get-{{closure#0}}.*.{kind}.0.mir"))
        files = [f for f in files if "get_stale" not in f.name]
        if len(files) != 1:
            raise SystemExit(f"expected one get {kind} dump in {directory}")
        found.append(files[0].read_text())
    return found[0], found[1]


def violations(resume: str, drop: str, names: set[str]) -> set[tuple[str, str, str, str]]:
    results, spec = analyze(resume, drop, names)
    return {
        (label, e.kind, e.state.phase, re.sub(r":.*", "", e.origin))
        for label, r in results
        for _, e in r.exits
        if bad(e, spec.guard_state)
    }


def main(fixed_dir: str, parent_dir: str) -> int:
    fixed, fixed_drop = pair(fixed_dir)
    parent, parent_drop = pair(parent_dir)
    failures = 0

    def expect(name: str, ok: bool) -> None:
        nonlocal failures
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
        failures += not ok

    expect("fixed, window+guard-drop assumptions: no violation",
           not violations(fixed, fixed_drop, WINDOW))
    none = violations(fixed, fixed_drop, set())
    expect("fixed, no assumptions: only window (P) and guard-destructor (X) unwinds",
           bool(none) and {v[2] for v in none} <= {"P", "X"}
           and sum(v[2] == "P" for v in none) == 4)
    par = violations(parent, parent_drop, set(NO_UNWIND))
    lookup = any(v[1] == "resume" and v[2] == "P" for v in par)
    expect("parent, all assumptions: lookup-path unwind leaves lock published", lookup)

    guard = "drop((((*_346) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>)) -> [return: bb264, unwind terminate(cleanup)];"
    if fixed.count(guard) == 1:
        mutated = fixed.replace(guard, "goto -> bb264;")
        got = violations(mutated, fixed_drop, WINDOW)
        expect("mutation: skip guard drop in resume cleanup -> rejected (G at resume)",
               any(v[:3] == ("resume", "resume", "G") for v in got))
    else:
        expect("mutation site: resume cleanup guard drop", False)

    dguard = "drop((((*_1) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>)) -> [return: bb44, unwind terminate(cleanup)];"
    if fixed_drop.count(dguard) == 1:
        got = violations(fixed, fixed_drop.replace(dguard, "goto -> bb44;"), WINDOW)
        expect("mutation: skip guard drop in drop cleanup -> rejected",
               any(v[0] == "drop" and v[2] == "G" for v in got))
    else:
        expect("mutation site: drop cleanup guard drop", False)

    none_reader = "_80 = Option::<Arc<CacheLock>>::None;"
    if fixed.count(none_reader) == 1:
        got = violations(fixed.replace(none_reader, "_80 = copy _81;"), fixed_drop, WINDOW)
        expect("mutation: reader slot not known None -> reader branch reachable, rejected", bool(got))
    else:
        expect("mutation site: reader None", False)
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
