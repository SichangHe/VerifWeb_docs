"""Run the current-Tokio checker on real MIR and on four MIR mutations.

Expected: unmutated exits 0; each mutation exits non-zero (1 = permit-losing
counterexample, 2 = rejected as outside the checked assumptions).
Usage: python -m verification.async_cancel.tokio_current_test CRATE.mir
"""

import sys

from verification.async_cancel.tokio_current import MUTATIONS, check, mutate


def main(path: str) -> int:
    crate = open(path).read()
    bad = 0
    got = check(crate, show=False)
    print(f"unmutated: exit {got}")
    bad += got != 0
    for name in MUTATIONS:
        got = check(mutate(crate, name), show=False)
        print(f"{name}: exit {got} ({'rejected' if got else 'ACCEPTED (bad)'})")
        bad += got == 0
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
