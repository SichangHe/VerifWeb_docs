"""Exercise real compiler MIR and operand/control-flow mutations in memory."""

import os
import re
from itertools import product
from pathlib import Path

from verification.async_cancel.cleanup_mir_check import functions
from verification.async_cancel.entry_coverage import check as check_coverage
from verification.async_cancel.publication_mir import (
    blocks,
    check,
    check_case,
    frame_layout,
)


def replace(text: str, before: str, after: str) -> str:
    """Require each mutant to target exactly one real instruction."""
    assert text.count(before) == 1, before
    return text.replace(before, after)


def rename(text: str) -> str:
    """Rename non-ABI locals consistently, including the frame pointer."""
    return re.sub(
        r"_(\d+)\b",
        lambda match: f"_{int(match[1]) + 1000}" if int(match[1]) > 2 else match[0],
        text,
    )


def main() -> None:
    """Accept the real inputs and neutral renaming; reject semantic mutations."""
    resume = Path(os.environ["PINGORA_RESUME_MIR"]).read_text()
    emitted = Path(os.environ["PINGORA_EMITTED_MIR"]).read_text()
    assert check(resume, emitted) is None
    prefix = check_coverage(resume)
    assert isinstance(prefix, tuple), prefix
    assert check(resume, emitted, prefix) is None
    assert check(resume, emitted, ("bb0", "bb99999")) is not None
    assert check(rename(resume), rename(emitted)) is None
    reordered = (
        resume.replace("((*_346).0:", "((*_346).999:")
        .replace("((*_346).1:", "((*_346).0:")
        .replace("((*_346).999:", "((*_346).1:")
    )
    factory_reordered = replace(
        emitted,
        "{ self: copy _1, key: copy _2, ttl: copy _3, extra: copy _4 }",
        "{ key: copy _2, self: copy _1, ttl: copy _3, extra: copy _4 }",
    )
    assert check(reordered, factory_reordered) is None
    guard_reordered = (
        resume.replace("as variant#7).8:", "as variant#7).999:")
        .replace("as variant#7).9:", "as variant#7).8:")
        .replace("as variant#7).999:", "as variant#7).9:")
    )
    guard_reordered = replace(
        guard_reordered, "_s8, _s16, _s17, _s19", "_s8, _s17, _s16, _s19"
    )
    assert check(guard_reordered, emitted) is None
    state_renumbered = resume.replace("variant#7", "variant#8")
    state_renumbered = replace(state_renumbered, "Suspend4 (7):", "Suspend4 (8):")
    state_renumbered = replace(state_renumbered, "7: bb441", "8: bb441")
    state_renumbered = replace(
        state_renumbered, "discriminant((*_346)) = 7;", "discriminant((*_346)) = 8;"
    )
    assert check(state_renumbered, emitted) is None
    program = blocks(resume)
    assert not isinstance(program, str)
    layout = frame_layout(resume, emitted)
    assert not isinstance(layout, str), layout
    constructor = next(
        body
        for body in functions(emitted)
        if "::get::{closure#0}::{closure#0}(" in body.splitlines()[0]
    )
    assert [
        check_case(program, constructor, prefix, hits, layout)
        for hits in product((False, True), repeat=3)
    ] == [True, False, False, False, False, False, False, False]
    assert (
        check(
            replace(
                resume,
                "[0: bb14, 1: bb15, otherwise: bb13]",
                "[0: bb15, 1: bb14, otherwise: bb13]",
            ),
            emitted,
        )
        is None
    )
    mutations = [
        (
            "field _s16: Option<CacheLockGuard<'_>>;",
            "field _s16: Option<Arc<CacheLock>>;",
        ),
        ("_s8, _s16, _s17, _s19", "_s8, _s17, _s16, _s19"),
        ("coroutine debug _guard => _s16;", "coroutine debug _guard => _s7;"),
        ("debug key => ((*_346).1: &K);", "debug key => ((*_346).0: &K);"),
        (
            "    bb44: {\n        StorageDead(_57);\n        StorageDead(_56);\n        goto -> bb55;",
            "    bb44: {\n        StorageDead(_57);\n        StorageDead(_56);\n        goto -> bb31;",
        ),
        ("[0: bb444, 1: bb443", "[0: bb14, 1: bb443"),
        (
            "= copy ((*_346).0: &read_through::RTCache<K, T, CB, S>);",
            "= copy ((*_346).1: &read_through::RTCache<K, T, CB, S>);",
        ),
        ("= copy ((*_346).1: &K);", "= copy ((*_346).0: &K);"),
        (
            "= copy ((*_346).3: std::option::Option<&S>);",
            "= copy ((*_346).2: std::option::Option<&S>);",
        ),
        (
            "_21 = copy (((*_346) as variant#7).1: &K);",
            "_21 = copy (((*_346) as variant#7).0: &K);",
        ),
        (
            "_9 = MemoryCache::<K, T>::get::<K>(move _10, move _11)",
            "_9 = MemoryCache::<K, T>::get::<K>(move _11, move _10)",
        ),
        (
            "_70 = <Arc<CacheLock> as Clone>::clone(move _71)",
            "_70 = CacheLock::new_arc()",
        ),
        (
            "_78 = Option::<Arc<CacheLock>>::Some(move _79);",
            "_78 = Option::<Arc<CacheLock>>::None;",
        ),
        ("_33 = (move _78, move _80);", "_33 = (move _80, move _78);"),
        (
            "_80 = Option::<Arc<CacheLock>>::None;",
            "_80 = Option::<Arc<CacheLock>>::Some(copy _79);",
        ),
        ("[1: bb59, otherwise: bb180]", "[1: bb180, otherwise: bb59]"),
        ("return: bb183, unwind: bb261", "return: bb192, unwind: bb261"),
        (
            "_263 = const ();\n        goto -> bb192;",
            "(((*_346) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>) = Option::<Arc<CacheLock>>::None;\n        goto -> bb192;",
        ),
        (
            "_263 = const ();\n        goto -> bb192;",
            "_999 = move (((*_346) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>);\n        goto -> bb192;",
        ),
        (
            "        _274 = move _367;\n        goto -> bb193;",
            "        _274 = move _367;\n        (((*_346) as variant#7).8: std::option::Option<read_through::CacheLockGuard<'_>>) = Option::<Arc<CacheLock>>::None;\n        goto -> bb193;",
        ),
        ("discriminant((*_346)) = 7;", "discriminant((*_346)) = 6;"),
        ("_79 = move _69;", "_79 = unsupported(copy _69);"),
        (
            "_256 = &(((*_346) as variant#7).5: u64);",
            "_256 = &(((*_346) as variant#7).1: &K);",
        ),
        (
            "_253 = &(((*_346) as variant#7).6: std::option::Option<std::sync::Arc<read_through::CacheLock>>);",
            "_253 = &(((*_346) as variant#7).7: std::option::Option<std::sync::Arc<read_through::CacheLock>>);",
        ),
    ]
    for before, after in mutations:
        assert check(replace(resume, before, after), emitted) is not None, before
    before = "_0 = CacheLockGuard::<'_> { lockers: copy _3, hashed_key: move _4, lock: move _5 };"
    after = "_0 = CacheLockGuard::<'_> { lockers: copy _3, hashed_key: move _4, lock: copy _4 };"
    assert check(resume, replace(emitted, before, after)) is not None
    before = "{ self: copy _1, key: copy _2, ttl: copy _3, extra: copy _4 }"
    after = "{ self: copy _1, key: copy _1, ttl: copy _3, extra: copy _4 }"
    assert check(resume, replace(emitted, before, after)) is not None
    before = "_5 = <Arc<CacheLock> as Clone>::clone(copy _2) -> [return: bb1, unwind continue];"
    after = "_5 = CacheLock::new_arc() -> [return: bb1, unwind continue];"
    assert check(resume, replace(emitted, before, after)) is not None


if __name__ == "__main__":
    main()
