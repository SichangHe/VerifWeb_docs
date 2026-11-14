"""Run generated ownership obligations and actual MIR mutants through Verus."""

import subprocess
import sys
import tempfile
from pathlib import Path

from verification.async_cancel.ownership_obligations import generate
from verification.async_cancel.publication_mir_test import rename, replace


def main() -> int:
    """Require unsafe supported mutants to translate and fail their proof obligations."""
    if len(sys.argv) != 4:
        print(
            "usage: python -m verification.async_cancel.ownership_obligations_test RESUME.mir CRATE.mir VERUS"
        )
        return 2
    resume = Path(sys.argv[1]).read_text()
    emitted = Path(sys.argv[2]).read_text()
    verus = Path(sys.argv[3]).resolve()
    cases = [
        ("real", resume, emitted, True, True),
        ("renamed", rename(resume), rename(emitted), True, True),
        (
            "different allocation",
            replace(
                resume,
                "_70 = <Arc<CacheLock> as Clone>::clone(move _71)",
                "_70 = CacheLock::new_arc()",
            ),
            emitted,
            True,
            False,
        ),
        (
            "disarmed initially",
            replace(
                resume,
                "_263 = const ();\n        goto -> bb192;",
                "(((*_346) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>) = Option::<Arc<CacheLock>>::None;\n        goto -> bb192;",
            ),
            emitted,
            True,
            False,
        ),
        (
            "disarmed on resume",
            replace(
                resume,
                "        _274 = move _367;\n        goto -> bb193;",
                "        _274 = move _367;\n        (((*_346) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>) = Option::<Arc<CacheLock>>::None;\n        goto -> bb193;",
            ),
            emitted,
            True,
            False,
        ),
        (
            "unsupported",
            replace(resume, "_79 = move _69;", "_79 = unsupported(copy _69);"),
            emitted,
            False,
            False,
        ),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ownership-obligations-") as temporary:
        for name, source, crate, translated, proved in cases:
            items, error = generate(source, crate)
            if (items is not None and error is None) != translated:
                failures.append(f"{name}: unexpected translation result {error}")
                continue
            if items is None:
                continue
            proof = Path(temporary) / "ownership.rs"
            _ = proof.write_text(
                "use vstd::prelude::*;\nverus! {\n" + items + "\n}\nfn main() {}\n"
            )
            result = subprocess.run(
                [str(verus), "--num-threads", "1", str(proof)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=temporary,
                check=False,
            )
            output = result.stdout + result.stderr
            if (result.returncode == 0) != proved:
                failures.append(f"{name}: unexpected proof result\n{output}")
            elif not proved and "postcondition not satisfied" not in output:
                failures.append(
                    f"{name}: failure was not an ownership postcondition\n{output}"
                )
    for failure in failures:
        print(failure)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
