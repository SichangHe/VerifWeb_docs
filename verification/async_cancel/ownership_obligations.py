"""Translate actual publication and resume outputs into Verus ownership equations."""

from itertools import product

from verification.async_cancel.publication_mir import (
    PublicationTrace,
    State,
    Value,
    prepare,
    retained_env,
    trace_case,
)


def observation(state: State) -> dict[str, Value]:
    """Include retained abstract storage and the observable poll/publication outputs."""
    result = retained_env(state)
    if "_0" in state.env:
        result["return"] = state.env["_0"]
    result["locked"] = Value("int", str(int(state.locked)))
    if state.publication is not None:
        result["publication"] = Value("guard", items=state.publication)
    return result


def descendants(value: Value) -> set[Value]:
    """Collect nested terms for a deterministic symbolic vocabulary."""
    return {value}.union(*(descendants(item) for item in value.items))


def case_items(
    trace: PublicationTrace, guard_slot: str, guard_state: str, number: int
) -> str:
    """Emit base, actual step equations, and induction for one publishing schedule."""
    first, second = observation(trace.first), observation(trace.second)
    expected = {
        guard_slot: Value("some", items=(first["publication"],)),
        "state": Value("int", guard_state),
        "return": Value("pending"),
        "locked": Value("int", "0"),
        "publication": first["publication"],
    }
    slots = sorted(first.keys() | second.keys() | expected.keys())
    values: set[Value] = set[Value]().union(
        *(
            descendants(value)
            for value in [*first.values(), *second.values(), *expected.values()]
        )
    )
    sorts = sorted({value.sort for value in values})
    atoms = sorted(
        {
            (value.sort, value.label)
            for value in values
            if (not value.items or value.label) and value.sort != "int"
        }
    )

    def term(value: Value) -> str:
        """Translate structure and actual allocation/operand identities, never truth values."""
        tag = sorts.index(value.sort)
        if value.items:
            label = (
                f"symbols[{atoms.index((value.sort, value.label))}]"
                if value.label
                else "0"
            )
            return f"OwnershipValue::Aggregate({tag}, {label}, seq![{', '.join(term(item) for item in value.items)}])"
        scalar = (
            value.label
            if value.sort == "int"
            else f"symbols[{atoms.index((value.sort, value.label))}]"
        )
        return f"OwnershipValue::Atom({tag}, {scalar})"

    def optional(value: Value | None) -> str:
        """Represent an uninitialized slot explicitly instead of inventing a value."""
        return "None" if value is None else f"Some({term(value)})"

    initial = ",\n        ".join(optional(first.get(slot)) for slot in slots)
    following = ",\n        ".join(
        f"before[{index}]"
        if first.get(slot) == second.get(slot)
        else optional(second.get(slot))
        for index, slot in enumerate(slots)
    )
    facts = "\n        && ".join(
        f"frame[{slots.index(slot)}] == {optional(value)}"
        for slot, value in expected.items()
    )
    fresh = [
        f"symbols[{left}] != symbols[{right}]"
        for left, (left_sort, left_label) in enumerate(atoms)
        for right, (right_sort, right_label) in enumerate(atoms)
        if left < right
        and left_sort == right_sort == "arc"
        and (left_label.isdigit() or right_label.isdigit())
    ]
    premise = " && ".join([f"symbols.len() == {len(atoms)}", *fresh])
    stem = f"ownership_{number}"
    return f"""
pub open spec fn {stem}_initial(symbols: Seq<int>) -> Seq<Option<OwnershipValue>> {{
    seq![{initial}]
}}

pub open spec fn {stem}_next(before: Seq<Option<OwnershipValue>>, symbols: Seq<int>) -> Seq<Option<OwnershipValue>> {{
    seq![{following}]
}}

pub open spec fn {stem}_invariant(frame: Seq<Option<OwnershipValue>>, symbols: Seq<int>) -> bool {{
    frame == {stem}_initial(symbols)
        && {facts}
}}

pub proof fn {stem}_base(symbols: Seq<int>)
    requires {premise},
    ensures {stem}_invariant({stem}_initial(symbols), symbols),
{{}}

pub proof fn {stem}_step(before: Seq<Option<OwnershipValue>>, symbols: Seq<int>)
    requires {premise}, {stem}_invariant(before, symbols),
    ensures {stem}_invariant({stem}_next(before, symbols), symbols),
{{}}

pub open spec fn {stem}_after(polls: nat, symbols: Seq<int>) -> Seq<Option<OwnershipValue>>
    decreases polls,
{{
    if polls == 0 {{ {stem}_initial(symbols) }}
    else {{ {stem}_next({stem}_after((polls - 1) as nat, symbols), symbols) }}
}}

pub proof fn {stem}_pending_induction(polls: nat, symbols: Seq<int>)
    requires {premise},
    ensures {stem}_invariant({stem}_after(polls, symbols), symbols),
    decreases polls,
{{
    if polls == 0 {{ {stem}_base(symbols); }}
    else {{
        {stem}_pending_induction((polls - 1) as nat, symbols);
        {stem}_step({stem}_after((polls - 1) as nat, symbols), symbols);
    }}
}}
"""


# 🧑 "prove real code conforms to spec, not only a model"
def generate(resume: str, emitted: str) -> tuple[str | None, str | None]:
    """Return Verus items derived without invoking Python ownership postcondition checks."""
    prepared = prepare(resume, emitted)
    if isinstance(prepared, str):
        return None, prepared
    items: list[str] = []
    for hits in product((False, True), repeat=3):
        trace = trace_case(
            prepared.blocks,
            prepared.constructor,
            prepared.prefix,
            hits,
            prepared.layout,
        )
        if isinstance(trace, str):
            return None, trace
        if trace is not None:
            items.append(
                case_items(
                    trace,
                    prepared.layout.guard_slot,
                    prepared.layout.guard_state,
                    len(items),
                )
            )
    if not items:
        return None, "no enumerated execution covers direct insertion"
    return (
        "pub enum OwnershipValue { Atom(int, int), Aggregate(int, int, Seq<OwnershipValue>) }\n"
        + "\n".join(items),
        None,
    )
