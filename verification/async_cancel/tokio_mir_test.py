"""Checker-input mutations of the fixed Tokio MIR; each must break one fact.

Usage: python -m verification.async_cancel.tokio_mir_test FIXED_CRATE.mir
"""

import sys

from verification.async_cancel.tokio_mir import facts

MUTATIONS = {
    "drop_store_guarded": ("switchInt(copy _22) -> [1: bb15, otherwise: bb18]", "switchInt(copy _22) -> [2: bb15, otherwise: bb18]"),
    "drop_stores_empty": ("_24 = set_state(move _25, const sync::notify::EMPTY)", "_24 = set_state(move _25, const sync::notify::NOTIFIED)"),
    "drop_forwards_one": ("_35 = notify_locked(copy _36, copy _38, move _39)", "_35 = notify_other(copy _36, copy _38, move _39)"),
    "locked_sets_notified": ("_7 = set_state(copy _3, const sync::notify::NOTIFIED)", "_7 = set_state(copy _3, const sync::notify::EMPTY)"),
    "locked_hands_one": ("_28 = NotificationType::OneWaiter;", "_28 = NotificationType::AllWaiters;"),
}


def main(path: str) -> int:
    text = open(path).read()
    if any(v is not True for v in facts(text).values()):
        print("unmutated input must pass")
        return 1
    bad = 0
    for fact, (old, new) in MUTATIONS.items():
        if text.count(old) != 1:
            print(f"{fact}: mutation site not unique ({text.count(old)})")
            bad += 1
            continue
        got = facts(text.replace(old, new))[fact]
        print(f"{fact}: {'rejected' if got is not True else 'ACCEPTED (bad)'}")
        bad += got is True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
