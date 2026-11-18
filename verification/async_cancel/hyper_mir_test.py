"""Checker-input mutations of the fixed Hyper MIR; each must break one fact.

Usage: python -m verification.async_cancel.hyper_mir_test FIXED_CRATE.mir
"""

import sys

from verification.async_cancel.hyper_mir import facts

MUTATIONS = {
    "send_cancels_when": ("ResponseFutMap::<B, E>::cancel(move _26)", "ResponseFutMap::<B, E>::other(move _26)"),
    "cancel_sends": ("futures_channel::oneshot::Sender::<()>::send(copy _5, const ())", "std::mem::drop::<futures_channel::oneshot::Sender<()>>(copy _5)"),
    "pipe_resets_on_cancel": ("send_reset(move _11, const h2::Reason::CANCEL)", "send_reset(move _11, const h2::Reason::NO_ERROR)"),
    "channel_paired": ("_7 = move (_8.1: futures_channel::oneshot::Receiver<()>)", "_7 = move (_9.1: futures_channel::oneshot::Receiver<()>)"),
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
