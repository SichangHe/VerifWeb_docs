"""Check real MIR and semantic mutants with the actual Verus executable."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from verification.async_cancel.cleanup_mir_check import functions
from verification.async_cancel.cleanup_semantics import translate


def main() -> int:
    """Report failures only; each verifier invocation uses one thread."""
    if len(sys.argv) != 3 or sys.argv[1] in {"-h", "--help"}:
        print(
            "usage: python -m verification.async_cancel.cleanup_semantics_test CRATE.mir VERUS"
        )
        return 2
    full = Path(sys.argv[1]).read_text()
    verus = Path(sys.argv[2]).resolve()
    text = "\n".join(
        body
        for body in functions(full)
        if (
            "::drop(" in body.splitlines()[0]
            and "CacheLockGuard" in body.splitlines()[0]
        )
        or "::drop::{closure#0}(" in body.splitlines()[0]
    )
    cases = [
        ("real crate", full, True, True),
        (
            "renumbered locals",
            re.sub(
                r"_(\d+)",
                lambda m: "_" + str(int(m[1]) + 100) if int(m[1]) > 2 else m[0],
                text,
            ),
            True,
            True,
        ),
        (
            "equivalent CFG",
            text.replace("return: bb10", "return: bb99").replace(
                "    bb10: {",
                "    bb99: {\n        goto -> bb10;\n    }\n\n    bb10: {",
            ),
            True,
            True,
        ),
        (
            "reversed branch",
            text.replace("0: bb10, otherwise: bb7", "0: bb7, otherwise: bb10"),
            True,
            False,
        ),
        (
            "wrong removal key",
            text.replace(
                "    let _17: &u64;", "    let _17: &u64;\n    let _19: u64;"
            ).replace(
                "_17 = &((*_1).1: u64);", "_19 = const 0_u64;\n        _17 = &_19;"
            ),
            True,
            False,
        ),
        (
            "same pointer operands",
            text.replace("ptr_eq(copy _2, copy _3)", "ptr_eq(copy _2, copy _2)"),
            True,
            False,
        ),
        (
            "unknown instruction",
            text.replace("        return;", "        unsupported;\n        return;", 1),
            False,
            False,
        ),
        (
            "wrong notification",
            text.replace("const 10_usize", "const 9_usize"),
            False,
            False,
        ),
        (
            "missing guard release",
            text.replace(
                "drop(_6) -> [return: bb11, unwind continue];", "goto -> bb11;"
            ),
            False,
            False,
        ),
        (
            "dropping borrowed guard does not release lock",
            re.sub(
                r"    let mut _6: (.+);",
                r"\g<0>\n    let _999: &\1;",
                text,
            ).replace(
                "drop(_6) -> [return: bb11, unwind continue];",
                "_999 = &_6;\n        drop(_999) -> [return: bb11, unwind continue];",
            ),
            False,
            False,
        ),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cleanup-semantics-") as temporary:
        for name, mir, expected_translation, expected_proof in cases:
            source, error = translate(mir)
            if (error is None) != expected_translation:
                failures.append(f"{name}: unexpected translation result: {error}")
                continue
            if source is None:
                continue
            proof = Path(temporary) / "obligation.rs"
            _ = proof.write_text(source)
            result = subprocess.run(
                [str(verus), "--num-threads", "1", str(proof)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=temporary,
            )
            if (result.returncode == 0) != expected_proof:
                failures.append(
                    f"{name}: unexpected Verus result:\n{result.stdout}\n{result.stderr}"
                )
            elif (
                not expected_proof
                and "postcondition not satisfied" not in result.stdout + result.stderr
            ):
                failures.append(
                    f"{name}: failed for a reason other than the map postcondition"
                )
    for failure in failures:
        print(failure)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
