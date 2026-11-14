"""Check real cancellation CFG certificates and a bypass mutant with Verus."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from verification.async_cancel.drop_obligations import generate


def main() -> int:
    """Require actual paired artifacts and report only integration failures."""
    if len(sys.argv) != 4:
        print(
            "usage: python -m verification.async_cancel.drop_obligations_test RESUME.mir DROP.mir VERUS"
        )
        return 2
    resume, drop = (Path(name).read_text() for name in sys.argv[1:3])
    verus = Path(sys.argv[3]).resolve()
    bypass, count = re.subn(
        r"drop\((.+CacheLockGuard<'_>.+) -> \[return: (bb\d+),[^\n]+;",
        r"goto -> \2;",
        drop,
        count=1,
    )
    if count != 1:
        print("expected pinned guard-drop edge")
        return 1
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="drop-obligations-") as directory:
        for label, mir, valid in (
            ("real CFG", drop, True),
            ("guard bypass", bypass, False),
        ):
            items, error = generate(resume, mir, 7, 8)
            if error or items is None:
                failures.append(f"{label}: translation failed before Verus: {error}")
                continue
            path = Path(directory) / "proof.rs"
            _ = path.write_text(
                "use vstd::prelude::*;\nverus! {\n" + items + "\n}\nfn main() {}\n"
            )
            result = subprocess.run(
                [str(verus), "--num-threads", "1", str(path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=directory,
                check=False,
            )
            output = result.stdout + result.stderr
            if (result.returncode == 0) != valid:
                failures.append(f"{label}: unexpected Verus result:\n{output}")
            elif not valid and "postcondition not satisfied" not in output:
                failures.append(
                    f"{label}: failed for a reason other than return safety:\n{output}"
                )
    for failure in failures:
        print(failure)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
