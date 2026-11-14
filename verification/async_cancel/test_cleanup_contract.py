"""Verify the map-effect lemma and reject removal without the identity check."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class CleanupContractTest(unittest.TestCase):
    def test_replacement_preservation(self) -> None:
        verifier = os.environ.get("VERUS")
        if verifier is None:
            self.skipTest("set VERUS to run the map-effect lemma checks")
        source = (Path(__file__).parent / "cleanup_contract.rs").read_text()
        original = "if before.dom().contains(key) && before[key] == owner {"
        self.assertEqual(source.count(original), 1)
        mutant = source.replace(original, "if before.dom().contains(key) {")
        with tempfile.TemporaryDirectory(prefix="async-cleanup-proof.") as directory:
            for name, text, expected in (
                ("original", source, 0),
                ("mutant", mutant, 1),
            ):
                with self.subTest(name=name):
                    path = Path(directory) / f"{name}.rs"
                    _ = path.write_text(text)
                    result = subprocess.run(
                        [verifier, str(path), "--num-threads", "1"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    self.assertEqual(
                        result.returncode, expected, result.stdout + result.stderr
                    )
                    if name == "mutant":
                        self.assertIn("postcondition not satisfied", result.stderr)
                    else:
                        self.assertIn("1 verified, 0 errors", result.stdout)


if __name__ == "__main__":
    _ = unittest.main()
