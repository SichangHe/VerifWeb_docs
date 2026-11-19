"""Run the batch-semaphore checker on real MIR and on its MIR mutations.

Expected, on scenarios where the semaphore is never closed: unmutated exits 0;
each mutation exits 1 (violation) or 2 (rejected as unsupported, e.g. a
waiter linked twice) in at least one scenario. Scenarios with close are run by
the checker itself; on master they exit 1 (the close-path leak).
Each run is a separate process, so memory is freed between scenarios.
Usage: python -m verification.async_cancel.tokio_semaphore_test CRATE.mir
"""

import subprocess
import sys

from verification.async_cancel.tokio_semaphore import MUTATIONS, OPEN


def run(path: str, scenario: str, mutation: str | None) -> int:
    cmd = [sys.executable, "-m", "verification.async_cancel.tokio_semaphore", path, "--scenario", scenario]
    if mutation:
        cmd += ["--mutate", mutation]
    return subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode


def main(path: str) -> int:
    bad = 0
    for sc in OPEN:
        got = run(path, sc.name, None)
        print(f"unmutated {sc.name}: exit {got}")
        bad += got != 0
    for name in MUTATIONS:
        codes = [run(path, sc.name, name) for sc in OPEN]
        ok = any(c in (1, 2) for c in codes)
        print(f"{name}: exits {codes} ({'rejected' if ok else 'NOT REJECTED (bad)'})")
        bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
