"""Exercise coverage on real MIR and targeted control-flow mutations."""

import re
import sys
from pathlib import Path

from verification.async_cancel.entry_coverage import check
from verification.async_cancel.publication_mir import blocks


def main() -> int:
    """Require the compiler artifact and reject bypass, insert and Ready mutations."""
    if len(sys.argv) != 2:
        print(
            "usage: python -m verification.async_cancel.entry_coverage_test RESUME.mir"
        )
        return 2
    text = Path(sys.argv[1]).read_text()
    program = blocks(text)
    assert isinstance(program, dict)
    assert isinstance(check(text), tuple), check(text)
    insert = next(
        name
        for name, lines in program.items()
        if any("HashMap::<" in line and "::insert(" in line for line in lines)
    )
    call = program[insert][-1]
    bypass = text.replace("0: bb444", f"0: {insert}", 1)
    assert bypass != text and check(bypass) == "insert bypasses the interpreted entry"
    extra = text.replace(
        "    bb0: {", f"    bb9999: {{\n        {call}\n    }}\n\n    bb0: {{", 1
    )
    assert check(extra) == "expected exactly one direct HashMap insert site"
    pending = text.replace("0: bb191, 1: bb190", "0: bb192, 1: bb190", 1)
    assert pending != text and "can reach Pending" in (check(pending) or "")
    terminated = pending.replace(
        "return: bb189, unwind: bb251", "return: bb189, unwind terminate(cleanup)", 1
    )
    assert terminated != pending and "can reach Pending" in (check(terminated) or "")
    hidden_pending = pending.replace(
        "_0 = Poll::<(Result<T, Box<pingora_error::Error>>, CacheStatus)>::Pending;",
        "discriminant(_0) = 1;",
    )
    assert hidden_pending != pending and "unsupported return-place access" in (
        check(hidden_pending) or ""
    )
    overwritten = text.replace(
        "_271 = discriminant(_264);",
        "_271 = discriminant(_264);\n        _271 = const 0_isize;",
        1,
    )
    assert overwritten != text and "not adjacent" in (check(overwritten) or "")
    borrowed = text.replace(
        "_271 = discriminant(_264);",
        "_9999 = &mut _264;\n        _271 = discriminant(_264);",
        1,
    )
    assert borrowed != text and "unsupported callback dispatch prefix" in (
        check(borrowed) or ""
    )
    neutral = text.replace("0: bb191, 1: bb190", "0: bb9999, 1: bb190", 1)
    neutral = neutral.replace(
        "    bb0: {",
        "    bb9999: {\n        nop;\n        goto -> bb191;\n    }\n\n    bb0: {",
        1,
    )
    assert isinstance(check(neutral), tuple), check(neutral)
    renamed = re.sub(
        r"\b_(\d+)\b",
        lambda match: f"_{int(match[1]) + 1000}" if match[1] != "0" else "_0",
        text,
    )
    assert isinstance(check(renamed), tuple), check(renamed)
    alternate = text.replace("0: bb31, 1: bb32", "0: bb31, 1: bb9999", 1).replace(
        "    bb0: {", "    bb9999: {\n        goto -> bb31;\n    }\n\n    bb0: {", 1
    )
    assert alternate != text and check(alternate) == "multiple paths to insertion"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
