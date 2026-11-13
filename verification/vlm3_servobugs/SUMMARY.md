# vlm3_servobugs: independent check of 4 likely bugs
(authored by agents unless marked 🧑)

One subagent per bug; details, quotes, and repros are in each bugN_*/REPORT.md. Nothing was filed upstream.

1. cssparser is_ident_start `-\<LF>`: confirmed and already known upstream.
   - Against the real crate 0.38.0, `-\LF` gives Ident("-"). @csstools/css-tokenizer 4.0.2 and the spec give Delim('-').
   - The fix is `has_newline_at(2)` at tokenizer.rs:931.
   - It is already reported as servo/rust-cssparser#440 (open).
   - Impact is low, because a stray `\` Delim follows in either case.
2. cssparser current_line_number u32 overflow: confirmed, but practically irrelevant.
   - A real repro with 2^32+10 newlines panics in debug. In release it reports the wrong line number only.
   - No upstream report was found.
   - Not realistically reachable from the web (belief, untested).
3. Servo Mp4Matcher 12-byte box panic: confirmed and already known upstream.
   - The real unmodified mime_classifier.rs panics at line 496.
   - It is already reported as servo/servo#47603 (open). Fix PR #47607 was closed unmerged.
   - Reachability through ServoParser::load_document is inferred from reading code, not run.
   - The spec quote was written from memory.
4. Servo Blob.slice i64 overflow: the stated repro is wrong, but the bug is real.
   - mozjs 0.26.14 clamps 1e19 to 2^53-1, so `b.slice(1).slice(1e19)` does not overflow.
   - About 1024 chained `slice(1e19)` calls do overflow: debug builds panic, and release returns the whole blob instead of an empty one.
   - The repro uses copied code; Servo was not built.
   - No upstream report was found.
   - Side finding from reading code only: a negative start on a sliced blob may use the wrong base.
