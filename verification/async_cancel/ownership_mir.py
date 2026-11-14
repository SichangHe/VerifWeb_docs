"""Recognize the reviewed Pingora registration-to-suspension MIR fragment.

This intentionally accepts one pinned pattern, not arbitrary Rust programs.
It checks the conditional argument documented in OWNERSHIP_MIR.md.
"""

import re
import sys
from pathlib import Path

from verification.async_cancel.cleanup_mir_check import fingerprint
from verification.async_cancel.ownership_mir_pattern import (
    CONSTRUCTOR_DIGEST,
    RESUME_DIGESTS,
)


def canonical(text: str) -> tuple[str, ...]:
    """Ignore indentation and empty lines, preserving each complete statement."""
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def check(resume: str, emitted: str) -> str:
    """Check complete reviewed blocks and the concrete constructor function.

    The theorem is conditional on entering bb14, taking the map-miss branch,
    and normal returns of calls through suspension. Ready and unwind exits
    leave the checked fragment. No all-writer-path coverage is claimed.
    """
    header = (
        "// MIR for `read_through::<impl at "
        "pingora-memory-cache/src/read_through.rs:167:1: 171:25>"
        "::get::{closure#0}` 0 coroutine_resume"
    )
    if not resume.startswith(header + "\n"):
        raise ValueError("not the pinned get coroutine_resume function")
    matches = list(
        re.finditer(
            r"^    bb(\d+)(?: \(cleanup\))?: \{\n(.*?)^    \}",
            resume,
            re.M | re.S,
        )
    )
    blocks: dict[int, str] = {}
    for match in matches:
        index = int(match[1])
        if index in blocks:
            raise ValueError(f"duplicate block bb{index}")
        blocks[index] = match[2]
    for index, expected in RESUME_DIGESTS.items():
        if index not in blocks or fingerprint(blocks[index]) != expected:
            raise ValueError(f"unreviewed registration/polling block bb{index}")
    layout = (
        "Suspend4 (7): [_s0, _s1, _s2, _s4, _s5, _s6, _s7, "
        "_s8, _s16, _s17, _s19, _s20],"
    )
    declarations = (
        "field _s6: u64;",
        "field _s7: Option<Arc<CacheLock>>;",
        "field _s8: Option<Arc<CacheLock>>;",
        "field _s16: Option<CacheLockGuard<'_>>;",
        layout,
    )
    lines = canonical(resume)
    if any(lines.count(declaration) != 1 for declaration in declarations):
        raise ValueError("unreviewed coroutine layout")
    constructors = list(
        re.finditer(
            r"^fn [^\n]*::get::\{closure#0\}::\{closure#0\}\([^\n]*\n.*?^\}",
            emitted,
            re.M | re.S,
        )
    )
    if len(constructors) != 1 or fingerprint(constructors[0][0]) != CONSTRUCTOR_DIGEST:
        raise ValueError("unreviewed concrete guard constructor")
    return (
        "reviewed fragment matched: map-miss registration carries Some guard "
        "with the inserted Arc identity, map and key into Pending state 7; "
        "resumed Pending polling retains it (conditional; see OWNERSHIP_MIR.md)"
    )


def main() -> None:
    """Accept paired artifacts from one pinned build."""
    if len(sys.argv) != 3:
        sys.exit(
            "usage: python -m verification.async_cancel.ownership_mir RESUME.mir EMITTED.mir"
        )
    try:
        print(check(Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text()))
    except (OSError, ValueError) as error:
        sys.exit(f"ownership check failed: {error}")


if __name__ == "__main__":
    main()
