# cssparser tokenizer (cssparser 0.38.0, src/tokenizer.rs; copy in src_upstream/)
(authored by agents unless marked 🧑)

Result: PARTIAL (bite-sized helpers proved; no whole token function). Rerun:
`timeout 300 /hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus tok.rs` -> `19 verified, 0 errors`.

## Proved (tok.rs, ~183 lines, ~45% spec/proof)
- has_at_least / is_eof / next_byte / byte_at / has_newline_at / next_byte_unchecked: no overflow, no OOB, exact results.
- advance(n): position stays <= len.
- consume_newline: CRLF consumed as one, else one byte; position advances 1-2, line_start==position, line_no+1 does not overflow.
  Invariant used: `line_no <= position` (each newline eats >=1 byte) -- this is what makes the u32 `+= 1` safe given len < 2^32.
- byte_to_hex_digit == spec hexval, result < 16; byte_to_decimal_digit correct.
- consume_hex_digits: 0..6 digits, value < 16^digits (<= 2^24, no u32 overflow), stops only at 6 digits / EOF / non-hex byte.
- consume_escape (as returning u32): never panics; result is a valid scalar value (<=0x10FFFF, not surrogate, nonzero).
- skip_whitespace minus the comment branch: terminates, in bounds, stops at a non-whitespace byte or EOF.

## Changes to the original
- `&str` -> `&[u8]` (str unsupported); `input.as_bytes()[i]` -> `input[i]`.
- Dropped `advance`'s `cfg!(debug_assertions)` loop (turned into a documented precondition: in-bounds only; the "no newline / no 4-byte leader" debug_asserts are not stated).
- `match_byte!` macro -> if/else chains; `is_ascii_digit` -> range compare (not supported by Verus without assume_specification).
- consume_escape returns u32 not char (char::from_u32 replaced by explicit scalar test); the final `consume_char` arm (UTF-8 decode via `chars().next().unwrap()` + unsafe get_unchecked) is modelled only for ASCII; non-ASCII returns U+FFFD (UNMODELLED, so this arm is not verified).
- Omitted: wrapping_add/sub column tracking (`current_line_start_position`) -- only line_start in newline case modelled; consume_comment, consume_numeric, consume_string, consume_ident not ported (time).
- Added `global size_of usize == 8;`.

## Failures (verbatim, trimmed) and lessons
1. `error: `core::num::impl&%6::is_ascii_digit` is not supported (note: you may be able to add a Verus specification ... assume_specification` -> replaced by range test.
2. `error: to dereference a mutable reference parameter in a postcondition, disambiguate by wrapping it in either `old` or `final``: new Verus needs `final(self)` / `old(self)` in `ensures` of `&mut` fns (not in `&self` fns, where `final(self)` gives E0308 "types differ in mutability").
3. `error: cannot test variant in exec mode` (`hexval(b) is Some` in exec code) -> byte comparisons.
4. `error: possible arithmetic underflow/overflow` at `self.position + n < self.input.len()` even though wf bounded len < 2^32 -- cause: Verus usize is arch-agnostic; fixed by `global size_of usize == 8;`. The message gives no hint of this; found by an `assert` that passed while the overflow check still failed.
5. `error: postcondition not satisfied ... failed this postcondition` (consume_newline) -- `line_no < 0xffff_ffff` was not preserved by `+= 1`; real fix is invariant `line_no <= position`.
6. `invariant not satisfied at end of loop body` on `value < 0x100_0000` (hex loop) and postcondition on stop-condition after `break`: Verus forgets break-branch facts after the loop; rewrote with a `stop` flag plus invariant. Bound needed pow16 lemma proved by case split with `reveal_with_fuel(pow16, 7)` (induction attempt failed: `postcondition not satisfied` since the 2^20 bound is not inductive).

## Findings
- No bug found. Safety argument for `position + n` and `line_no += 1` depends on len < 2^32 (cssparser's `SourcePosition`/u32 line numbers); on larger inputs release builds wrap `line_no` silently (u32 += 1 after 2^32 newlines needs >4GB input) -- inference, not exercised.
- Unsafe `next_char`'s `.unwrap()` relies on position being on a char boundary; proving that needs a UTF-8 well-formedness model (not attempted) -- main blocker for the rest of the file, along with `Cow`/`CowRcStr`, `Vec<u8>` + `from_utf8_release_unchecked`, closures in `advance_while`, f32/f64 in consume_numeric.

## Effort
~25 min wall-clock, 9 verify iterations.

---
# Round 2 (coordinator: "prove whole token-consuming functions ...")

Files: `tok2.rs` (rerun: `timeout 900 .../verus tok2.rs` -> `41 verified, 0 errors`, ~560 lines), `lineno_overflow.rs`
(expected failure), `linenum_exp/` (real-crate experiment; main.rs now holds the `-\<LF>` test, the 4GiB test is quoted below).
Wall-clock ~50 min, ~7 verify iterations. tok2.rs supersedes tok.rs.

## Whole functions now verified (properties = memory safety/no panic/no overflow + termination + the structural postconditions below)
- consume_comment: terminates; in bounds; returns the FIRST `*/` at/after start (position == end+2, input[end..end+2]=="*/"), else position==len.
- consume_quoted_string (both fast and slow path, incl. escapes, escaped newline, NUL->U+FFFD): terminates, in bounds, progress (position > old);
  Err => stopped AT the unconsumed newline; Ok => EOF or closing quote just consumed; fast path => slice has no quote/backslash/NUL/newline.
  Not proved: the *content* of the owned Vec equals the CSS-decoded string (only length growth is modelled).
- consume_escape / consume_hex_digits / consume_char: bounds, progress when not at EOF, hex path returns a valid non-zero scalar.
  consume_char is now real (decodes 1-4 byte UTF-8) with no `next_char().unwrap()` panic, under assumption `utf8_ok` (below). Decoded value is unconstrained.
- is_ident_start == ident_start_impl (spec copy of the code); consume_name (fast + escape/slow path): terminates, in bounds, stops only at EOF / ASCII
  non-name byte / `\`+newline, and PROGRESS: ident_start => position advances (so ident tokens cannot loop forever).
- consume_numeric (sign, integer, fraction, exponent, `%`, dimension unit): given start-condition (digit, or `.digit`, after optional sign) never indexes
  out of bounds (the `next_byte_unchecked` / `byte_at(1)` / `byte_at(2)` calls are all justified), terminates, progresses, digits region
  correct. Integer path: int_value == clamp_i32(+-integer digits) -- proved for a saturating-u64 model (acc = min(value, 2^32)).
  f64 arithmetic (fraction, exponent, powf, f32 casts) is NOT modelled (Verus has no float arithmetic); `value as i32` clamp is checked on the integer model only.

## Assumptions / model changes (beyond round 1)
- `utf8_ok(input)`: for every non-continuation byte i, i + char_len <= len; no leading continuation byte; continuation bytes only follow bytes >= 0x80. These are
  weak consequences of `&str` validity, not full UTF-8 validity (an `unsafe get_unchecked(..)` + `.chars().next().unwrap()` in next_char relies on exactly this).
- wf also assumes `input.len() < 2^32` and tracks `line_no <= position`.
- Vec<u8>/Cow output: push_utf8 (model of `encode_utf8`) is verified as exec code but has only a length postcondition; `from_utf8_release_unchecked` not modelled.
- advance_while closure + the 256-entry IS_SIMPLE_NAME_BYTE table -> inline while loop + equivalent predicate `is_simple_name_byte`.
- column bookkeeping (current_line_start_position, wrapping_add/sub) still omitted; check_for_source_map / see_function omitted.

## Verus failures this round (verbatim)
1. `error: to dereference a mutable reference parameter in a postcondition, disambiguate by wrapping it in either `old` or `final`` -- also for `&mut Vec`.
2. `error: could not automatically infer triggers for this quantifier; use `#[trigger]` annotations` (comment-terminator forall).
3. `error: decreases not satisfied at end of loop` (consume_name, outer loop) -- no message says why; cause: inner `while` had no invariant relating its start position to its end (needed a `pb <= t.position` snapshot).
4. `error: while loop: resource limit (rlimit) exceeded; consider rerunning with `--profile`` (consume_name slow loop) and `error: function body check: resource limit (rlimit) exceeded` (consume_name, consume_numeric): too many/entangled invariants + postconditions. Fixes: dropped redundant invariants and proved the progress ensure via a tiny lemma (`name_stop(s,p) ==> !ident_start_impl(s,p)`) in a wrapper function; split consume_numeric's three digit loops into `skip_digits`/`skip_digits_acc`; `#[verifier::rlimit(200)]` on consume_numeric. rlimit errors give no localisation.

## FINDINGS
### F1 (real, release + debug): u32 `current_line_number` overflow on > 4 GiB input
Verus on a model without the `len < 2^32` assumption (`lineno_overflow.rs`, only `line_no <= position <= len` kept):
```
error: possible arithmetic underflow/overflow
  --> lineno_overflow.rs:11:5
   |
11 |     t.line_no += 1;
verification results:: 1 verified, 1 errors
```
Checked on the real crate (cssparser 0.38.0, path dep, input = 2^32+5 `\n` bytes then `a`, 64-bit Linux):
- overflow-checks ON (debug / `overflow-checks=true`): `thread 'main' panicked at .../src/tokenizer.rs:476:9: attempt to add with overflow` (line 476 = `self.current_line_number += 1;`).
- release: no panic; wraps silently: after the 2^32+5 newlines and `a`, `current_source_location()` = `SourceLocation { line: 5, column: 2 }` (correct line would be 4294967301). 
So it is real but needs >= 4 GiB of newlines (Servo would load such a stylesheet only adversarially). `column as u32` (current_source_location) has the analogous truncation for a >4 GiB single line (not run).
In the safe regime (len < 2^32) it is proved overflow-free via `line_no <= position`.

### F2 (real, spec-conformance, found by proof attempt on is_ident_start): `-` + `\` + newline is wrongly accepted as ident start
In is_ident_start's `b'-'` arm, `b'\\' => !tokenizer.has_newline_at(1)` inspects offset 1, which is the backslash itself (never a newline), so it is always true.
CSS Syntax 3 sec 4.3.9/4.3.10 requires the 2nd and 3rd code points to be a valid escape, i.e. offset 2 must not be a newline.
`tok2.rs::ident_start_disagreement` proves the concrete discrepancy on `seq![45,92,10]` (impl true, spec false). Real crate, release build:
```
"-\\\n"  -> ["Ident(\"-\")", "Delim('\\\\')", "WhiteSpace(\"\\n\")"]
"a-\\\n" -> ["Ident(\"a-\")", ...]   (expected/fine)
```
Spec-expected for "-\<LF>": Delim('-'), Delim('\'), WhiteSpace. Not a memory-safety issue (consume_name still progresses by consuming `-`); affects token stream only in a malformed-escape corner. (My reading of the spec; not cross-checked against a reference tokenizer. Not filed upstream.)
Same shape in the numeric tail: consume_numeric uses is_ident_start for dimension units, so `1-\<LF>` is affected the same way.

## Still open
Content correctness of decoded strings/idents (Vec contents vs CSS decode); float semantics of numeric; unquoted url / bad-url; column tracking with wrapping arithmetic; full UTF-8 validity instead of the weak `utf8_ok`; next_token_unchecked dispatch.
