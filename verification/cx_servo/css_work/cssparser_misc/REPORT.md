# cssparser 0.38.0 non-tokenizer pieces (nth.rs, serializer.rs, unicode_range.rs)
(authored by agent)

Upstream: crates.io cssparser 0.38.0, copied from the local cargo registry to `src_upstream/` (nth.rs, unicode_range.rs, serializer.rs). color.rs not attempted.

Rerun (each prints "N verified, 0 errors"; ignore the GLIBC warning):
`V=/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus; $V urange.rs` (18 verified); `$V --triggers-mode silent ser.rs` (9); `$V nth.rs` (4). `nth_nopre_fails.rs` is the expected-failure variant.

## 1. unicode_range.rs: consume_hex, consume_question_marks, parse_concatenated (urange.rs): proved
Properties: no u32 overflow in `value * 0x10 + digit`; `first_hex_value << (qm*4)` and `((v+1) << (qm*4)) - 1` do not overflow/underflow; every returned start/end is <= 0x1000000 (so the later `end > char::MAX` check is the only range check needed, and all arithmetic is safe); consume_hex returns value < 16^digits; positions stay in bounds; loops terminate. Not proved: that the result equals the spec'd urange text semantics, and `start <= end` (upstream checks that in `parse`).
Changes: `&mut &[u8]` + `split_first` replaced with `(&[u8], &mut usize)`; `to_digit(16)` replaced by a hand-written `hex_digit`; `parse` and `parse_tokens` (need Parser/Token) not ported.
Verbatim failures on the way (each told the line but not why):
- `error: to dereference a mutable reference parameter in a postcondition, disambiguate by wrapping it in either old or final` : new Verus mut-ref syntax, need `*final(p)` / `*old(p)`.
- `error: loop must have a decreases clause` for exec while loops.
- `error: possible arithmetic underflow/overflow --> urange.rs:96:22  end: ((first_hex_value + 1) << (question_marks * 4)) - 1,` : the real obligation. Needs: hex value < 1<<(4*digits) tracked in consume_hex's postcondition and loop invariant, plus bit_vector lemmas (`lemma_shift`: `h+q<=6, v<1<<4h ==> ((v+1)<<4q) <= 1<<24` and `>= 1`, the latter for the `- 1`).
- `error: postcondition not satisfied ... rg.end <= 0x1000000  at this exit` : fixed by asserting `(1u32 << 24) == 0x1000000` by bit_vector and equating `usize`-shift-amount terms with the `u32` ones in the lemma.
- A pow(16,n) formulation (vstd power lemmas) was abandoned for shifts: bit_vector is simpler.
Finding: no bug. The `consumed > 6` check is what makes the shift safe; without it `<< (qm*4)` could shift past 32 bits.

## 2. serializer.rs: hex_escape, char_escape, serialize_name (ser.rs): proved
Property: `serialize_name(value, dest)` appends exactly `name_spec(value)` where name_spec is the per-byte table (name bytes and bytes >=128 copied; NUL -> EF BF BD; 0x01-0x1F and 0x7F -> `\hex `; other ASCII -> `\c`). Also proved: hex_escape's output is all ASCII (so its `unsafe from_utf8_unchecked` is sound for ASCII input; callers pass bytes known < 128 because non-ASCII bytes `continue`), slice bounds `value[chunk_start..i]` are valid, loop invariant `chunk_start <= i`.
Changes: `fmt::Write` generic dest -> `&mut Vec<u8>`; `&str` -> `&[u8]` (UTF-8 validity / char-boundary slicing not modelled; the chunk boundaries are at ASCII bytes so they are boundaries in the real code, not proved); HEX_DIGITS table -> arithmetic; `for/enumerate/match_byte!` -> while/if.
Failures: first run `invariant not satisfied before loop` came from writing `final(dest)` in a loop invariant: use `dest@` there. Also `fold_left` spec was replaced by a recursive spec fn, with an induction lemma `lemma_plain_run` (copying a run of plain bytes). Not done: serialize_identifier, serialize_unquoted_url, CssStringWriter, write_numeric (needs dtoa_short and floats).

## 3. nth.rs (nth.rs): partial
- parse_n_dash_digits byte test proved equal to its spec (4 obligations incl. loop).
- `parse_signless_b` computes `b_sign * b` with `b: i32` from an unsigned number token. Proved safe only with precondition `b >= 0`. Without it Verus reports (nth_nopre_fails.rs): `error: possible arithmetic underflow/overflow --> /tmp/nth_nopre.rs:10:5  b_sign * b`. It overflows for b == i32::MIN and b_sign == -1. Whether the tokenizer can ever give `has_sign:false` with negative `int_value` was not checked (tokenizer belongs to another agent). The full parse_nth/parse_b are not ported: they depend on Parser, Token and match_ignore_ascii_case!.

## Effort / friction
About 45 min wall clock, 15 verify runs total. Proof/spec lines are about 1.5x the ported code in urange.rs (lemmas dominate), ~2x in ser.rs. Friction: new `final()/old()` mut-ref syntax; `&mut &[u8]` and split_first need rewriting; shifts by usize need explicit casts to match lemma terms; `(v+1) << k` in specs needs `as u32` (int has no shl).
No real bugs found in these pieces. Not done: color.rs, unicode_range ToCss (formatting), serialize_string.

# Round 2 (coordinator follow-up)

Rerun: `$V --triggers-mode silent ser2.rs` (10 verified), `$V color.rs` (6), `$V --triggers-mode silent nth_full.rs` (11). `nth_full_nopre_fails.rs` is the expected failure.

## Tokenizer check: does an unsigned integer token give b >= 0? Yes (read-only, tokenizer.rs 0.38.0, `consume_numeric`, lines 1047-1160)
Facts from the source:
- `let (has_sign, sign) = match tokenizer.next_byte_unchecked() { b'-' => (true, -1.), b'+' => (true, 1.), _ => (false, 1.) };` so `has_sign == false` implies `sign == 1.`.
- `integral_part` accumulates digits only (>= 0, may be +inf), `fractional_part >= 0`; `let mut value = sign * (integral_part + fractional_part);` so value >= 0 when unsigned. An exponent sets `is_integer = false`, so int_value is None whenever an exponent is present (the `powf` cannot make a negative).
- `int_value = if is_integer { Some(if value >= i32::MAX as f64 { i32::MAX } else if value <= i32::MIN as f64 { i32::MIN } else { value as i32 }) }`. For value in [0, inf] this gives 0..=i32::MAX (saturating; inf also saturates).
Conclusion (inference from source reading, not machine-checked, since Verus can't model f64 parsing): for `has_sign: false`, `int_value` is in [0, i32::MAX]. So `b_sign * b` with b_sign = +/-1 cannot overflow, including at i32::MAX (-i32::MAX is representable). i32::MIN only arises with has_sign true, and parse_signless_b requires `has_sign: false`. `parse_b` uses a signed `Number` directly as b (`Ok((a, b))`), with no arithmetic. nth_full.rs encodes this tokenizer fact as the `tok_ok` well-formedness predicate and verifies parse_nth/parse_b/parse_signless_b panic- and overflow-free under it; removing the predicate gives, verbatim: `error: possible arithmetic underflow/overflow --> nth_full_nopre_fails.rs:102:73  Token::Number { has_sign: false, int_value: Some(b) } => Ok((a, b_sign * *b))`.
Caveat: if a downstream constructs Token::Number by hand (public enum), the guarantee does not hold, but then it is a caller-side issue.

## nth_full.rs: parse_nth, parse_b, parse_signless_b, parse_n_dash_digits: proved panic/overflow-free (partial functional)
Model (not upstream): `Token` enum with Number/Dimension/Ident/Delim/Ws/Other; `Parser` = token Vec + pos; `next` (skips Ws), `next_ws`, `reset` = pos assignment. match_ignore_ascii_case! -> `eq_ic` (proved against lower-case spec). Proved: all indexing in bounds, no overflow, `parse_n_dash_digits` returns b <= 0. Assumed: `parse_number_saturate_neg` is `external_body` with contract (input "-digits" gives result <= 0, never fails). This corresponds to the upstream `.unwrap()` on `parse_number_saturate`; from reading nth.rs it succeeds because "-"+digits tokenizes as one Number with int_value Some, but this is an assumption in the proof. Not proved: that (a, b) equals the An+B semantics. Changes: Parser borrow structure (tokens referenced by index); `strip_prefix('-')` -> skip flag.
Failures hit: mut-ref `final()` syntax again (ensures on `p` must say `final(p)`); `could not automatically infer triggers` (needed `#[trigger]`); `postcondition not satisfied ... at the end of the function body` for next() not returning Ws, fixed by asserting the loop-exit fact `pos < len ==> !(toks[pos] is Ws)`.

## ser2.rs: serialize_name, serialize_unquoted_url, CssStringWriter::write_str, serialize_identifier: proved
One verified loop `serialize(mode, ...)` stands for the three upstream loops (they have identical structure, differing only in byte classes and escape rule), with `ser_spec(mode, value)` = concatenation of per-byte `esc`. This is a refactor, not verbatim: three upstream loops are not each checked separately, only the shared structure plus each class/escape table. Proved: output == spec; hex_escape inputs < 128 for all three modes (non-plain bytes are ASCII), so each `from_utf8_unchecked` use is sound; slices in bounds. `serialize_identifier` proved against `ident_spec` (the "--", "-", leading "-", leading digit hex-escape cases) including that `value.as_bytes()[0]` after stripping `-` is in bounds (the lone "-" case is handled earlier). Failures: `assertion failed` at the final `dest@ =~= old(dest)@ + ident_spec(value@)` three times; fixed by restructuring into explicit `dash`/`digit` flags and ghost `pre`/`rest` (Verus could not unfold ident_spec through mutable `start`). Observation: URL serializer escapes NUL as `\0 ` (hex), while name/string use U+FFFD; consistent with CSS spec.

## color.rs: from_hex, parse_hash_color (hex/clamp only): proved
`x * 16 + y` (max 15*16+15=255) and `x * 17` (max 255) do not overflow u8 (Verus checks this because from_hex ensures v < 16); results match hex-value spec; lengths other than 3/4/6/8 give Err; indexing in bounds. Changes: `?` replaced with match; alpha `f32 = byte/255.0` omitted (returns Option<u8>). `clamp_floor_256_f32` / `clamp_unit_f32` use f32 `round`/`clamp`/`as u8`; Verus has no usable f32 arithmetic, so only an integer analogue `clamp_floor_256` is proved (no truncation). hsl/hwb -> rgb are f32 code: not attempted (blocked on floats). Note: parse_hash_color's `value.len()` match makes `value[7]` safe by construction.

## write_numeric: not attempted
Depends on f32 sign/fract and `dtoa_short`; blocked on floats and an external crate.

## Round-2 effort
About 50 min, 14 more verify runs (ser2 ~7, nth_full ~5, color 1). Totals: 6 Verus files verify. No real bugs found in cssparser 0.38.0 non-tokenizer code; the one candidate (`b_sign * b`) is excluded by the tokenizer's sign handling.
