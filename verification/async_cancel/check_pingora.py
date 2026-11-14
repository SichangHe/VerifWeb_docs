"""Run the conditional Pingora ownership, destruction and cleanup proof chain."""

import subprocess
import sys
import tempfile
from pathlib import Path

from verification.async_cancel.check_drop_paths import check as check_drop
from verification.async_cancel.cleanup_semantics import translate
from verification.async_cancel.drop_obligations import generate
from verification.async_cancel.entry_coverage import check as check_coverage
from verification.async_cancel.publication_mir import check as check_publication
from verification.async_cancel.publication_mir import frame_layout


def main() -> int:
    """Require paired real artifacts and discharge the generated map obligations."""
    if len(sys.argv) != 5:
        print(
            "usage: python -m verification.async_cancel.check_pingora RESUME.mir DROP.mir CRATE.mir VERUS"
        )
        print(__doc__)
        return 0 if sys.argv[1:] == ["--help"] else 2
    resume_path, drop_path, crate_path, verus_path = map(Path, sys.argv[1:])
    try:
        resume = resume_path.read_text()
        drop = drop_path.read_text()
        emitted = crate_path.read_text()
        prefix = check_coverage(resume)
        if isinstance(prefix, str):
            print(f"entry coverage rejected: {prefix}")
            return 1
        error = check_publication(resume, emitted, prefix)
        if error:
            print(f"ownership rejected: {error}")
            return 1
        layout = frame_layout(resume, emitted)
        if isinstance(layout, str):
            print(f"frame layout rejected: {layout}")
            return 1
        reports = check_drop(resume, drop, "CacheLockGuard")
        slot = layout.guard_slot.rsplit(":", 1)[1]
        expected = (
            f"variant {layout.guard_state} slot {slot}: "
            "every normal return follows successful guard-slot drop"
        )
        if expected not in reports:
            print("drop check did not cover the ownership check's guard slot")
            return 1
        proof, error = translate(emitted)
        if error or proof is None:
            print(f"cleanup translation rejected: {error}")
            return 1
        drop_items, error = generate(resume, drop, int(layout.guard_state), int(slot))
        if error or drop_items is None:
            print(f"drop translation rejected: {error}")
            return 1
        marker = "\n}\n\nfn main()"
        if proof.count(marker) != 1:
            print("unsupported proof module layout")
            return 1
        proof = proof.replace(marker, drop_items + marker)
        with tempfile.TemporaryDirectory(prefix="pingora-proof-") as directory:
            path = Path(directory) / "cleanup.rs"
            _ = path.write_text(proof)
            result = subprocess.run(
                [str(verus_path.resolve()), "--num-threads", "1", str(path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=directory,
                check=False,
            )
        if result.returncode:
            print(result.stdout + result.stderr)
            return 1
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"conditional check failed: {error}")
        return 1
    print(
        "conditional lookup-outcome/Pending cleanup chain passed; see CONDITIONAL_CHECK.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
