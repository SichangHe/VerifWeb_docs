"""Recognize two audited, pinned Pingora MIR bodies by their fingerprints.

This is an audit fingerprint, not a general MIR verifier. The fingerprint
includes operand provenance, branch edges, unwind edges, declarations and types.
Dependency semantics and correct source/build identity remain assumptions.
"""

import hashlib
import re
import sys
from pathlib import Path

# 🧑 "the human requires proving the real code conforms to the spec, not only a model"
EXPECTED_DIGESTS = (
    "8129540f9e45cee3237bae12fe46aad28cf463d9d7d06ea132c044098db0ddf5",
    "51f9900d3dbc19d5f7d39afb45397b5281a2d2273dd9a242a93a4e9989b68af7",
)


def functions(text: str) -> list[str]:
    """Extract compiler-formatted top-level functions, including their headers."""
    return re.findall(r"^fn [^\n]+\{\n.*?^}", text, re.M | re.S)


def canonical(body: str) -> tuple[str, ...]:
    """Ignore indentation and empty lines only; retain all instruction text."""
    return tuple(line.strip() for line in body.splitlines() if line.strip())


def fingerprint(body: str) -> str:
    """Hash reviewed instructions without storing generated MIR artifacts."""
    return hashlib.sha256("\n".join(canonical(body)).encode()).hexdigest()


def check(text: str) -> list[str]:
    """Return rejection reasons, or accept the exact audited pair of bodies."""
    actual = functions(text)
    errors: list[str] = []
    for closure, expected in zip((False, True), EXPECTED_DIGESTS, strict=True):
        marker = "::drop::{closure#0}(" if closure else "::drop("
        owner = "read_through::<impl at " if closure else "CacheLockGuard"
        candidates = [
            body
            for body in actual
            if marker in body.splitlines()[0] and owner in body.splitlines()[0]
        ]
        label = "pointer comparison closure" if closure else "CacheLockGuard::drop"
        if len(candidates) != 1:
            errors.append(f"{label}: expected one body, found {len(candidates)}")
        elif fingerprint(candidates[0]) != expected:
            errors.append(f"{label}: unsupported change to audited MIR template")
    return errors


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] in {"-h", "--help"}:
        print("usage: cleanup_mir_check.py CRATE.mir (rustc --emit=mir output)")
        return 2
    errors = check(Path(sys.argv[1]).read_text())
    if errors:
        for error in errors:
            print(error)
        return 1
    print("accepted audited cleanup bodies; dependency semantics remain trusted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
