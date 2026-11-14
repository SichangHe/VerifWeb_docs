"""Compile and check paired Pingora MIR in a fresh temporary directory."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


# 🧑 "the human requires proving the real code conforms to the spec, not only a model"
def run(checkout: Path, cache: Path, verus: Path) -> int:
    """Direct one compilation's MIR outputs into private paths, then check them."""
    checkout, cache, verus = checkout.resolve(), cache.resolve(), verus.resolve()
    if not (checkout / "Cargo.lock").is_file() or not verus.is_file():
        print("build check requires a checkout with Cargo.lock and a Verus executable")
        return 2
    env = dict(os.environ)
    env.update(
        RUSTC_BOOTSTRAP="1",
        CARGO_BUILD_JOBS="2",
        CARGO_TARGET_DIR=str(cache / "target"),
        CARGO_BUILD_BUILD_DIR=str(cache / "build"),
    )
    with tempfile.TemporaryDirectory(prefix="pingora-build-check-") as directory:
        output = Path(directory)
        emitted = output / "crate.mir"
        dump = output / "dump"
        result = subprocess.run(
            [
                "cargo",
                "rustc",
                "--locked",
                "-p",
                "pingora-memory-cache",
                "--lib",
                "--",
                f"--emit=mir={emitted}",
                "-Zdump-mir=coroutine",
                f"-Zdump-mir-dir={dump}",
            ],
            cwd=checkout,
            env=env,
            timeout=600,
            check=False,
        )
        if result.returncode:
            print("MIR compilation failed")
            return 1
        prefix = "pingora_memory_cache.read_through-*-get-{closure#0}.-------."
        resumes = list(dump.glob(prefix + "coroutine_resume.0.mir"))
        drops = list(dump.glob(prefix + "coroutine_drop.0.mir"))
        if len(resumes) != 1 or len(drops) != 1 or not emitted.is_file():
            print(
                "compilation did not produce exactly one get-resume/drop pair and crate MIR"
            )
            return 1
        if any(path.stat().st_size == 0 for path in [emitted, *resumes, *drops]):
            print("compilation produced empty MIR")
            return 1
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "verification.async_cancel.check_pingora",
                str(resumes[0]),
                str(drops[0]),
                str(emitted),
                str(verus),
            ],
            cwd=Path(__file__).resolve().parents[3],
            timeout=120,
            check=False,
        ).returncode


def main() -> int:
    """Require external CPU scheduling; accept checkout, build cache and Verus."""
    if len(sys.argv) != 4:
        print(
            "usage: python -m verification.async_cancel.real_pingora.build_check CHECKOUT CACHE VERUS"
        )
        print(
            "Run under cpu-run LOW and a 16 GiB/512-task systemd scope; see BUILD_CHECK.md."
        )
        return 0 if sys.argv[1:] == ["--help"] else 2
    try:
        return run(*map(Path, sys.argv[1:]))
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"build check failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
