# bug1: cssparser is_ident_start, `-\<newline>`
(authored by agents unless marked 🧑)

Verdict: CONFIRMED (independently reproduced). Already reported upstream as servo/rust-cssparser#440 (open, filed 2026-08-20 by hey-jj, against 0.37.0).

## Source (v0.38.0; tag object d128a90e..., tokenizer.rs blob a1bca2d3...)
https://github.com/servo/rust-cssparser/blob/v0.38.0/src/tokenizer.rs#L919-L937 (lines 926-935 in the checked source):
- L931: `b'\\' => !tokenizer.has_newline_at(1),`  (inside the `b'-'` arm, which already matched `byte_at(1)` == `\`)
- L935: `b'\\' => !tokenizer.has_newline_at(1),`  (top-level `\` arm; offset 1 is correct there)
Helpers (same file): `has_newline_at(offset)` tests `byte_at(offset)`; `byte_at(o)` = `input[position + o]`.
In the `-` arm, position is at `-`, so offset 1 is the backslash itself, which is never a newline: the test is always true. The byte after the backslash is offset 2. Fix: `has_newline_at(2)`.
Spec (CSS Syntax 3, "check if three code points would start an ident sequence"): "U+002D HYPHEN-MINUS: If the second code point is a name-start code point or a U+002D HYPHEN-MINUS, or the second and third code points are a valid escape, return true." Valid escape: "If the first code point is not U+005C REVERSE SOLIDUS (\), return false. Otherwise, if the second code point is a newline, return false." So the newline to test is the 3rd code point.

## Repro (repro/, cssparser =0.38.0, Cargo.lock pins it; note 0.38 API is `Parser::new(&str)`)
Reference: @csstools/css-tokenizer 4.0.2 (ref/ref.mjs).
```
input        cssparser 0.38.0                      @csstools
-\LF         Ident("-") Delim(\) WS                delim(-) delim(\) WS
-\CR, -\FF   same wrong result                     delim(-) delim(\) WS
--\LF        Ident("--") Delim(\) WS               ident("--") delim(\) WS  (agree)
@-\LF        AtKeyword("-") Delim(\) WS            delim(@) delim(-) delim(\) WS
-\a, -\EOF   ident (agree)                         ident (agree)
```
Side effect: serializing the tokens back gives `\-\<LF>` instead of `-\<LF>`.
Same wrong offset also affects `1-\LF` (Dimension unit "-") and `#-\LF` (IDHash), per issue #440 (not re-run by me; same function is_ident_start, so expected).

## Reachability / observability
- Reachable: any CSS text from web content passes through this tokenizer in Servo and Stylo (Firefox). No special feature needed.
- Impact is small. `-\<LF>` is followed by a stray `\` Delim either way, so in ordinary properties and selectors the declaration is invalid in both cases. Observable differences need token-preserving contexts: custom property values / var() substitution and cssText round-trip (serialization shows `\-` vs `-`), and `@-\<LF>` (at-rule name "-" vs delims). Not tested in an actual browser. Classification: low-severity spec conformance bug, no memory-safety issue.

## Upstream
`gh search issues`: #440 "is_ident_start reads the wrong byte for a hyphen before a backslash" (open). Its line reference (895) is from 0.37; on main the lines are 930/934. Not filed by me; no contact made.
