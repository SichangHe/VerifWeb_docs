# Target 2: V8 typer integer-range rules checked in z3
(authored by agents unless marked 🧑)

## Source
- V8 `src/compiler/operation-typer.cc`, main @ 3a06b466fd19d49b7c2b3eb78985f6f7dac0e218 (fetched from chromium.googlesource.com; copy in `src/v8/operation-typer.cc`, commit in `src/v8/COMMIT`).
- Functions: NumberAdd/AddRanger, NumberSubtract/SubtractRanger, NumberMultiply/MultiplyRanger, NumberModulus, NumberBitwiseOr/And/Xor, NumberShiftLeft/ShiftRight/ShiftRightLogical (10 rules).

## Method
Per rule: assert x in [lmin,lmax], y in [rmin,rmax] (input ranges symbolic), compute the typer's output range as coded in C++, ask z3 for a concrete result outside it. unsat = sound for the encoded domain. Bitwise/shift: 32-bit bitvectors with JS semantics (shift count = y & 31; shr operands as uint32). Add/Sub/Mod: int32-range inputs, exact in 64 bits. Mul: unbounded integers (nlsat; 64-bit bitvector mul timed out, see below). Mutants (deliberately broken rules) confirm the checker can fail.

## Results (verbatim, `result.txt`, `result_mul.txt`)
```
NumberAdd/AddRanger: unsat
NumberSubtract/SubtractRanger: unsat
NumberMultiply/MultiplyRanger: unknown
NumberModulus: unsat
NumberBitwiseOr: unsat
NumberBitwiseAnd: unsat
NumberBitwiseXor: unsat
NumberShiftLeft: unsat
NumberShiftRight: unsat
NumberShiftRightLogical: unsat
--- mutation sanity (checker must find bugs) ---
MUTANT And: max=min(lmax,rmax) always: sat
  counterexample: {'y': 2147483633, 'rmin': 2147483676, 'lmax': 536821744, 'rmax': 2147483634, 'x': 4294967295, 'lmin': 2147483650}
MUTANT ShiftLeft: no overflow check: sat
  counterexample: {'y': 1, 'rmin': 0, 'lmax': 2684445089, 'rmax': 31, 'x': 2650847441, 'lmin': 2174951939}
MUTANT Or: min=max(lmin,rmin) always: sat
  counterexample: {'y': 3042604874, 'rmin': 2623832675, 'lmax': 1073873916, 'rmax': 1614446438, 'x': 828000214, 'lmin': 3374917857}
--- CVE-2021-21220-style shape (modeled, not the original code) ---
MUTANT Truncate-keeps-range: sat
  counterexample: {'v': 8589934079, 'a': 0, 'b': 8589934592}
MUTANT sign-ext-vs-zero-ext (typer thinks sign bit is 0): sat
  counterexample: {'xv': 2147483648}
NumberMultiply/MultiplyRanger (Int, unbounded): unsat
MUTANT Multiply: two corners only: sat
[rmax = 0, x = 1, lmax = 1, lmin = 0, y = -1, rmin = -1]
```
(The first Multiply line `unknown` is the 64-bit bitvector attempt, 90 s timeout; the `unsat` in result_mul.txt is the authoritative one. Counterexample values are printed by z3 as unsigned bitvectors.)

Reading:
- All 10 rules: no counterexample in the modeled domain. No unsound rule found in current V8 main.
- 3 bitwise mutants + 1 multiply mutant found `sat`, so the checks are not vacuous.
- CVE-2021-21220-style section: these are two hand-written buggy models (typer keeps an int64 range across a 32-bit truncation; typer assumes sign bit 0 for a value that is sign-extended). Both are `sat`. They show the bug shape is catchable, but they are my models, not the actual V8 code of that CVE, and the second is nearly tautological. Treat as illustration only.

## Rerun
```
cd /hdd1/sichangheagent/vl_meeting_work/out/vlm2_jit/t2_typer
venv/bin/python -u check_typer.py   # ~2-3 min (Multiply line times out)
venv/bin/python -u check_mul.py
```
(venv = python3 + `pip install z3-solver`; z3-solver reports 5.3.3).

## Limitations
- Doubles are modeled as exact integers. Real V8 uses double arithmetic: Add/Sub/Mul on ranges beyond 2^53, infinities, NaN and -0 handling are NOT modeled. Add/Sub/Mod inputs are limited to int32 ranges; Mul is unbounded-integer.
- Only the integer-range branches were encoded. Type-lattice parts (Type::Range construction/normalization, NumberToInt32 truncation of wider ranges, Union with MinusZero/NaN) are assumed correct.
- Modulus: y == 0 excluded (typer returns NaN separately); -0 results ignored.
- Soundness vs the operation semantics only; not vs. the actual machine code Turbofan emits (the layer where CVE-2021-21220-class bugs live: lowering/representation changes).
- Verus not used; z3 python only.
