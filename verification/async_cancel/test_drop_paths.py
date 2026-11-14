"""Mutation tests of drop-path checking against actual rustc output."""

import re
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from verification.async_cancel.check_drop_paths import check


class DropPathsTest(unittest.TestCase):
    def test_pingora_dump(self) -> None:
        directory = os.environ.get("PINGORA_MIR_DIR")
        if directory is None:
            self.skipTest("set PINGORA_MIR_DIR to test the real Pingora dumps")
        scratch = Path(directory)
        prefix = "pingora_memory_cache.read_through-{impl#3}-get-{closure#0}.-------."
        resume = (scratch / (prefix + "coroutine_resume.0.mir")).read_text()
        drop = (scratch / (prefix + "coroutine_drop.0.mir")).read_text()
        reports = check(resume, drop, "CacheLockGuard")
        self.assertEqual(len(reports), 5)
        self.assertEqual(
            reports[-1],
            "variant 7 slot 8: every normal return follows successful guard-slot drop",
        )
        redirected, count = re.subn(
            r"(_\d+) = discriminant\(\(\*_1\)\);",
            r"\g<0>\n        \1 = const 0_isize;",
            drop,
            count=1,
        )
        self.assertEqual(count, 1)
        with self.assertRaisesRegex(ValueError, "unsupported coroutine entry dispatch"):
            _ = check(resume, redirected, "CacheLockGuard")
        bypassed, count = re.subn(
            r"drop\((.+CacheLockGuard<'_>.+) -> \[return: (bb\d+),[^\n]+;",
            r"goto -> \2;",
            drop,
            count=1,
        )
        self.assertEqual(count, 1)
        with self.assertRaisesRegex(ValueError, "without guard-slot drop"):
            _ = check(resume, bypassed, "CacheLockGuard")

        guard_drop = re.search(r"drop\((.+CacheLockGuard<'_>.+)\) -> \[return:", drop)
        self.assertIsNotNone(guard_drop)
        assert guard_drop is not None
        place = guard_drop[1]
        disarmed = drop.replace(
            f"drop({place})",
            f"{place} = Option::<CacheLockGuard<'_>>::None;\n        drop({place})",
            1,
        )
        with self.assertRaisesRegex(ValueError, "unsupported statement"):
            _ = check(resume, disarmed, "CacheLockGuard")
        exposed = drop.replace(
            f"drop({place})", f"_999 = &mut {place};\n        drop({place})", 1
        )
        with self.assertRaisesRegex(ValueError, "unsupported statement"):
            _ = check(resume, exposed, "CacheLockGuard")

    def test_compiler_output_and_mutations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="async-drop-check.") as directory:
            scratch = Path(directory)
            fixture = Path(__file__).parent / "probes" / "mir_guard.rs"
            result = subprocess.run(
                [
                    "env",
                    "RUSTC_BOOTSTRAP=1",
                    "rustup",
                    "run",
                    "1.99.1",
                    "rustc",
                    "--edition=2021",
                    str(fixture),
                    "--emit=mir",
                    "-o",
                    str(scratch / "out.mir"),
                    "-Zdump-mir=coroutine",
                    f"-Zdump-mir-dir={scratch}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            resumes = list(scratch.glob("*.coroutine_resume.0.mir"))
            drops = list(scratch.glob("*.coroutine_drop.0.mir"))
            self.assertEqual(len(resumes), 1)
            self.assertEqual(len(drops), 1)
            resume = resumes[0].read_text()
            drop = drops[0].read_text()
            self.assertEqual(len(check(resume, drop, "Guard")), 1)

            bypassed, count = re.subn(
                r"drop\((.+Guard<'_>.+) -> \[return: (bb\d+),[^\n]+;",
                r"goto -> \2;",
                drop,
                count=1,
            )
            self.assertEqual(count, 1)
            with self.assertRaisesRegex(ValueError, "without guard-slot drop"):
                _ = check(resume, bypassed, "Guard")

            with self.assertRaisesRegex(ValueError, "different functions"):
                _ = check(
                    resume, drop.replace("MIR for `guarded", "MIR for `other"), "Guard"
                )
            with self.assertRaisesRegex(ValueError, "no suspended"):
                _ = check(resume, drop, "AbsentGuard")
            with self.assertRaisesRegex(ValueError, "unsupported terminator"):
                _ = check(resume, drop.replace("return;", "imaginary;"), "Guard")

            shared_target, count = re.subn(
                r"(drop\(.+Guard<'_>.+ -> \[return: )(bb\d+)(, unwind: )bb\d+",
                r"\1\2\3\2",
                drop,
                count=1,
            )
            self.assertEqual(count, 1)
            with self.assertRaisesRegex(ValueError, "without guard-slot drop"):
                _ = check(resume, shared_target, "Guard")


if __name__ == "__main__":
    _ = unittest.main()
