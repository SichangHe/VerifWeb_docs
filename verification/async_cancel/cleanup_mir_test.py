"""Mutation checks against actual compiler output; no synthetic baseline."""

import sys
from pathlib import Path

from verification.async_cancel.cleanup_mir_check import check, functions


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] in {"-h", "--help"}:
        print("usage: python -m verification.async_cancel.cleanup_mir_test CRATE.mir")
        return 2
    original = Path(sys.argv[1]).read_text()
    errors = check(original)
    if errors:
        print(f"actual MIR rejected: {errors}")
        return 1
    mutations = {
        "wrong removal key": (
            "_17 = &((*_1).1: u64);",
            "_17 = &const 0_u64;",
        ),
        "unconditional removal": (
            "switchInt(copy _7) -> [0: bb10, otherwise: bb7];",
            "goto -> bb7;",
        ),
        "remove only when identity differs": (
            "switchInt(copy _7) -> [0: bb10, otherwise: bb7];",
            "switchInt(copy _7) -> [0: bb7, otherwise: bb10];",
        ),
        "wrong notification lock": (
            "_4 = <Arc<CacheLock> as Deref>::deref(move _5)",
            "_4 = <Arc<CacheLock> as Deref>::deref(move _13)",
        ),
        "skipped notification": (
            "_2 = Semaphore::add_permits(move _3, const 10_usize) -> [return: bb2, unwind continue];",
            "goto -> bb2;",
        ),
        "wrong permit count": (
            "Semaphore::add_permits(move _3, const 10_usize)",
            "Semaphore::add_permits(move _3, const 1_usize)",
        ),
        "wrong compared lock": (
            "Arc::<CacheLock>::ptr_eq(copy _2, copy _3)",
            "Arc::<CacheLock>::ptr_eq(copy _2, copy _2)",
        ),
        "skipped write guard release": (
            "drop(_6) -> [return: bb11, unwind continue];",
            "goto -> bb11;",
        ),
        "unsupported instruction": (
            "        _17 = &((*_1).1: u64);",
            "        _17 = &((*_1).1: u64);\n        _7 = const true;",
        ),
    }
    failed = False
    for name, (before, after) in mutations.items():
        if original.count(before) != 1:
            print(f"{name}: mutation target not unique")
            failed = True
        elif not check(original.replace(before, after)):
            print(f"{name}: mutation accepted")
            failed = True
    target = next(
        body
        for body in functions(original)
        if "::drop(" in body.splitlines()[0]
        and "CacheLockGuard" in body.splitlines()[0]
    )
    for name, changed in (
        ("missing destructor", original.replace(target, "")),
        ("duplicate destructor", original + "\n" + target),
    ):
        if not check(changed):
            print(f"{name}: mutation accepted")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
