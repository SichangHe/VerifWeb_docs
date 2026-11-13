# Independent cssparser review
(authored by agents unless marked 🧑)

Both reported cssparser bugs reproduce. Every reported final Verus count reproduces. These are proofs of rewritten models, not verification of the original crate. The main summary omits one trusted assumption in its An+B claim.

## Evidence and scope

Reviewed `out/vlm3_servo/cssparser_tokenizer/REPORT.md`, `cssparser_misc/REPORT.md`, their proof files, and their claims in `SUMMARY.md`. Commands ran on copies under `out/cx_servo/css_work/`. Downloaded cssparser 0.38.0 from <https://crates.io/api/v1/crates/cssparser/0.38.0/download>; its tokenizer, nth, serializer, and unicode_range files are byte-identical to the supplied upstream copies. All following log paths are relative to `out/cx_servo/css_work/`.

Reran `tools/verus-x86-linux/verus FILE` (misc files with `--triggers-mode silent`). Each successful log contains the exact form `verification results:: N verified, 0 errors`:

- `tok.log`: 19; `tok2.log`: 41
- `urange.log`: 18; `ser.log`: 9; `ser2.log`: 10
- `nth.log`: 4; `nth_full.log`: 11; `color.log`: 6

Expected failures also reproduced: `lineno_overflow.log` says `verification results:: 1 verified, 1 errors`; `nth_nopre_fails.log` says `verification results:: 3 verified, 1 errors`; `nth_full_nopre_fails.log` says `verification results:: 10 verified, 1 errors`. All three contain `error: possible arithmetic underflow/overflow` at the reported arithmetic operation.

## Findings requiring correction

1. **Overstated in SUMMARY:** “`nth_full.rs` (11): An+B parsing cannot panic or overflow, given that the tokenizer produces b ≥ 0 (source reading)”. The proof also trusts `parse_number_saturate_neg`: `#[verifier::external_body]` and `{ unimplemented!() }` in `cssparser_misc/nth_full.rs:68`. Its contract supplies successful negative-number parsing without checking the body. The component report discloses this correctly: “this is an assumption in the proof.” Add that qualification to the summary, and say “the parser model” rather than implying the upstream Parser is verified.

2. **Wrong cross-reference:** tokenizer F2 cites “CSS Syntax 3 sec 4.3.9/4.3.10” for valid escapes and identifier starts. The current W3C document uses §§4.3.8/4.3.9. The substantive conclusion is correct; use the stable links below.

3. **Wrong exact threshold in SUMMARY:** “more than 2^32 newlines” is unnecessarily restrictive. Starting at line zero, the increment overflows on newline number 2^32, not only after it. The reproduced 2^32+5 case remains valid.

4. **Overstated if read as a formal upstream safety result:** misc says “each `from_utf8_unchecked` use is sound”; SUMMARY says “`from_utf8_unchecked` only ever sees ASCII”. The proof replaces these calls with byte-vector pushes, and does not prove Rust string slicing or the correspondence to each upstream loop. It proves ASCII hex-escape output and the shared serializer model. Source inspection supports the upstream conclusion: `hex_escape` builds bytes from backslash, hex digits, and space; `char_escape` gets ASCII from the original loops. Preserve that distinction. The report already acknowledges “UTF-8 validity / char-boundary slicing not modelled”.

## Tokenizer claim audit

- **Confirmed, within the model:** “has_at_least / is_eof / next_byte / byte_at / has_newline_at / next_byte_unchecked: no overflow, no OOB, exact results”; “advance(n): position stays <= len”; newline behavior, hex/decimal helpers, hex digit bound and stop condition, and whitespace termination. These contracts/invariants are present in `tok.rs`, whose 19 checks reran. Preconditions include `len < 2^32`; these are not unrestricted crate guarantees.
- **Confirmed, within the disclosed abstraction:** round-one “consume_escape ... result is a valid scalar value”. `tok.rs:157` ensures scalar range/nonzero, but its non-ASCII arm returns replacement without consuming input. The report explicitly discloses that difference. Round two correctly limits scalar correctness to the hex path; `consume_char` only ensures position movement, not the returned decoded value.
- **Confirmed:** “consume_comment ... FIRST `*/`”; `tok2.rs:252` has a quantified no-earlier-terminator postcondition, plus exact end position and EOF case. Strings' error/newline, success/end, progress and fast-path-byte claims match `consume_quoted_string` postconditions. Owned decoded content is not proved, as reported.
- **Confirmed:** identifier-start equality is equality to a copied implementation predicate, not correctness against CSS. The concrete disagreement proof uses `seq![45u8, 92u8, 10u8]`. Name stop/progress claims match the wrapper contract and terminating core loops.
- **Confirmed:** numeric bounds/progress, digit-region membership, and integer clamp match `tok2.rs:564` contracts. Saturating-u64 accumulation replaces f64. The claim “f64 arithmetic ... is NOT modelled” is accurate; the proof does not establish equivalence of the complete numeric token value to upstream floating-point parsing.
- **Confirmed:** the listed omissions and transformations are visible: byte slices, rewritten macro branches, omitted debug assertions/columns/source-map/function handling, and explicit 64-bit usize. `utf8_ok` imposes the stated weak consequences of valid UTF-8; it is not full validity. The report says “Decoded value is unconstrained”, correctly describing the proof contract, even though the executable replacement computes a value.
- **Confirmed bug F2:** real-crate release rerun (`ident_repro.log`) prints `"-\\\n" -> ["Ident(\"-\")", "Delim('\\\\')", "WhiteSpace(\"\\n\")"]`. `tokenizer.rs:931` contains `b'\\' => !tokenizer.has_newline_at(1),` while the current position is still the hyphen. Numeric tail calls the same predicate before consuming a dimension name, so its analogous effect follows directly from source. No reference tokenizer was needed to establish the contradiction with the standard.
- **Confirmed bug F1:** new repro `cssparser_tokenizer/linenum_exp/src/bin/overflow.rs` builds 2^32+5 newline bytes and `a`, then calls `Parser::next`. `overflow_release.log` prints `SourceLocation { line: 5, column: 2 }`; `overflow_debug.log` reports `tokenizer.rs:476:9:` and `attempt to add with overflow`. Reran with `cargo run --offline --release --bin overflow --manifest-path .../Cargo.toml` and the same command without `--release`; dev profile has overflow checks enabled. The `len < 2^32` proof excludes this case as claimed.
- **Confirmed source inference, not runtime test:** >4 GiB column truncation follows from `column ... as u32` in `current_source_location`. The statement that Servo would load such a stylesheet “only adversarially” is **unverifiable** here; no Servo loading behavior was tested.
- **Confirmed scope disclosure:** URL parsing, column bookkeeping, decoded content correctness, full UTF-8 validity and token dispatch remain open. “No bug found” in round one is a historical statement, not a no-bug guarantee.

### Independent CSS standard evidence

W3C CSS Syntax §4.3.8, <https://www.w3.org/TR/css-syntax-3/#starts-with-a-valid-escape>:

> If the first code point is not U+005C REVERSE SOLIDUS (\), return false.
>
> Otherwise, if the second code point is a newline, return false.
>
> Otherwise, return true.

Section 4.3.9, <https://www.w3.org/TR/css-syntax-3/#would-start-an-identifier>, under “U+002D HYPHEN-MINUS”:

> If the second code point is an ident-start code point or a U+002D HYPHEN-MINUS, or the second and third code points are a valid escape, return true. Otherwise, return false.

Downloaded document retained as `css-syntax.html`. For hyphen/backslash/newline, all three alternatives fail. Thus the reported identifier-start result is wrong under the standard.

## Miscellaneous claim audit

- **Confirmed, model scope:** unicode-range bounds, shifts, multiplication, loop termination and positions. `urange.rs` bounds hex digits by six, checks total consumed count, and proves shift lemmas before constructing the range. “Not proved ... text semantics ... and start <= end” accurately describes its contracts. The wording “only range check needed” is valid for the scalar upper bound, not ordering; the next sentence correctly acknowledges ordering.
- **Confirmed, model scope:** `ser.rs` and `ser2.rs` prove concatenation against their per-byte specifications; identifier prefix cases and slice bounds are included. The shared loop, `Vec<u8>` output and omitted fmt::Write failures are model changes. Byte class/escape tables agree with the supplied original loops on inspection. The unsafe-call qualification is above.
- **Confirmed observation:** “URL serializer escapes NUL as `\0 ` (hex), while name/string use U+FFFD” matches source and both model branches. “consistent with CSS spec” is not separately established by a serialization-standard audit here; treat that clause as **unverifiable in this review**, not as proved by Verus.
- **Confirmed:** initial nth byte predicate equivalence and multiplication failure without the nonnegative precondition. Round-two source inference excludes negative unsigned integer tokens: source says `_ => (false, 1.),`, accumulates nonnegative digits, sets `is_integer = false` for fraction/exponent, and clamps integer values. This is source reasoning, not a float proof. The quoted candidate is not a demonstrated upstream bug.
- **Confirmed, conditional:** full nth bounds/arithmetic and negative return property are checked under `tok_ok` and the trusted numeric parser, with a model `Parser` rather than the upstream borrowing/tokenization implementation. An+B semantic correctness remains unproved. The caveat about manually constructing a public Token is **overstated as a reachability suggestion**: upstream `parse_nth` takes `Parser`, not an arbitrary token; no route to inject a forged Number was demonstrated.
- **Confirmed, limited to helpers/model:** color `from_hex`, pair16, pair17 prove exact hex arithmetic and u8 safety; parse_hash_color proves length conditions and safe indexing, but its own contract does not specify returned RGB channels. The report's “results match hex-value spec” is correct for the helpers and should not imply a full parse_hash_color functional contract. Float alpha is omitted, integer clamping replaces float clamping, and hsl/hwb/write_numeric are absent as reported.
- **Confirmed counts:** “Totals: 6 Verus files verify” correctly counts urange, ser, nth, ser2, color and nth_full. No new misc bug was established by this review.

## Historical/process claims

Reported wall time, iteration counts, failed intermediate attempts, abandoned induction attempts, causes attributed to earlier solver failures, and line-count/proof-percentage estimates are **unverifiable as historical measurements** from the final artifacts. Final expected-failure files reproduce the three overflow diagnostics above. Other historical messages are plausible but their intermediate source versions/logs were not provided. Statements such as “Verus forgets break-branch facts” and “Verus has no float arithmetic” should remain descriptions of these attempts, not universal capability theorems.

No upstream contact or filing occurred.
