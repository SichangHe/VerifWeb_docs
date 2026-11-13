# cssparser 0.38.0: `current_line_number` u32 overflow
(authored by agents unless marked 🧑)

Verdict: CONFIRMED as a code defect (reproduced on the real crate). Practical impact: negligible.

## Source (servo/rust-cssparser, tag v0.38.0, tag ref sha d128a90e; local copy matches version = "0.38.0")
https://github.com/servo/rust-cssparser/blob/v0.38.0/src/tokenizer.rs
- L206 `current_line_number: u32,`
- L475-476 in `consume_newline`: `self.current_line_start_position = self.position;` / `self.current_line_number += 1;` (unchecked u32 add)
- L1217 in the url-whitespace skipper: `tokenizer.current_line_number += newlines;` (same u32)
- L279-280 `line: self.current_line_number, column: (self.position - self.current_line_start_position + 1) as u32` (column also truncates to u32 on a >4 GiB single line; a related but separate narrowing cast)

## Repro (repro/, depends on `cssparser =0.38.0` from crates.io; Cargo.lock confirms 0.38.0)
Input: (2^32 + 10) newline bytes then `a` (4.29 GB; machine had 251 GB RAM, so feasible). `Parser::new(&s)`, `next()`, `current_source_location()`.
- Debug (overflow checks on), 150 s: panic `attempt to add with overflow` at cssparser-0.38.0/src/tokenizer.rs:476:9.
- Release (overflow-checks=false explicitly), 15 s: token Ident("a"), true 0-based line 4294967306, reported line 10 (wrapped mod 2^32). Column 2 is correct.
- Note the 0.38.0 API is `Parser::new(&str)`; there is no `ParserInput`.
- A newline-only run was used; I did not test the `\r\n`/form-feed variants, but they share consume_newline.
- Release profiles with overflow-checks on (e.g. some hardened builds) would panic like debug. Servo/Firefox release profile default is off (belief, not checked).

## Reachability and consequence
- Consequence of wrapping (fact from repro + code): only `SourceLocation.line` is wrong (and `column` on >4 GiB lines). Positions/slices use usize `position`, so tokens are correct. No memory unsafety seen in these lines.
- Panic case: only where overflow checks are enabled; a panic on attacker-sized input would be a DoS in that build.
- Web reachability: NOT tested. Belief: needs a single >4 GiB stylesheet with >2^32 line breaks. Browsers do not normally fetch/hold such stylesheets (Firefox string types cap near 1-2 GiB; I did not verify Servo's limits). So not realistically reachable from web content; a local-tool/embedder concern at most.

## Upstream search (gh, servo/rust-cssparser)
Issues searched: "line number overflow", "current_line_number", "4GiB", "u32 line"; PRs: "line overflow". No hits. No existing report found (search is keyword-limited).

## Does it matter?
Low. Real bug, trivial fix (saturating/wrapping add or usize), but unreachable in practice; wrong line numbers only. Not filed upstream.
