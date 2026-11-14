"""Exercise the restricted ownership certificate on real compiler output."""

import os
import unittest
from pathlib import Path

from verification.async_cancel.ownership_mir import check


class OwnershipTests(unittest.TestCase):
    """Mutate each link in the registered-lock-to-guard argument."""

    def test_real_mir(self) -> None:
        resume_path = os.environ.get("PINGORA_RESUME_MIR")
        emitted_path = os.environ.get("PINGORA_EMITTED_MIR")
        if not resume_path or not emitted_path:
            self.skipTest("set PINGORA_RESUME_MIR and PINGORA_EMITTED_MIR")
        resume = Path(resume_path).read_text()
        emitted = Path(emitted_path).read_text()
        self.assertIn("reviewed fragment matched", check(resume, emitted))
        mutations = (
            ("insert identity", "_77 = move _70;", "_77 = move _69;"),
            (
                "writer Some",
                "_78 = Option::<Arc<CacheLock>>::Some(move _79);",
                "_78 = Option::<Arc<CacheLock>>::None;",
            ),
            (
                "reader None branch",
                "switchInt(move _81) -> [1: bb59, otherwise: bb180];",
                "switchInt(move _81) -> [1: bb180, otherwise: bb59];",
            ),
            (
                "tuple correlation",
                "_33 = (move _78, move _80);",
                "_33 = (move _80, move _78);",
            ),
            (
                "wrong captured key",
                "_256 = &(((*_346) as variant#7).5: u64);",
                "_256 = &_76;",
            ),
            (
                "bypass map",
                "return: bb182, unwind: bb262",
                "return: bb183, unwind: bb262",
            ),
            (
                "guard disarmed before pending",
                "        discriminant((*_346)) = 7;",
                """        (((*_346) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>) = Option::<CacheLockGuard<'_>>::None;
        discriminant((*_346)) = 7;""",
            ),
            (
                "resumed poll bypass",
                "        goto -> bb193;",
                "        goto -> bb182;",
            ),
            (
                "guard layout",
                "_s8, _s16, _s17, _s19, _s20],",
                "_s8, _s17, _s16, _s19, _s20],",
            ),
        )
        for label, old, new in mutations:
            with self.subTest(label=label):
                self.assertEqual(resume.count(old), 1)
                with self.assertRaises(ValueError):
                    _ = check(resume.replace(old, new), emitted)
        constructor_mutations = (
            (
                "constructor clone identity",
                "_5 = <Arc<CacheLock> as Clone>::clone(copy _2)",
                "_5 = CacheLock::new_arc()",
            ),
            (
                "constructor key",
                "hashed_key: move _4, lock: move _5",
                "hashed_key: const 0_u64, lock: move _5",
            ),
            (
                "constructor lockers",
                "lockers: copy _3, hashed_key: move _4",
                "lockers: copy _6, hashed_key: move _4",
            ),
        )
        for label, old, new in constructor_mutations:
            with self.subTest(label=label):
                self.assertEqual(emitted.count(old), 1)
                with self.assertRaises(ValueError):
                    _ = check(resume, emitted.replace(old, new))


if __name__ == "__main__":
    _ = unittest.main()
