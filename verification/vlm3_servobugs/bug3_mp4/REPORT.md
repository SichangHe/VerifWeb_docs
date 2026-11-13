# Mp4Matcher::matches panic for box_size < 16 — verdict: CONFIRMED
(authored by agents unless marked 🧑)

Commit d275164b2bf624ee5844b22522d10c81b8f606ab (checkout verified; also equals servo/servo main HEAD today, file unchanged there).
File: https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/shared/net/mime_classifier.rs

## Code (lines 463-502)
- Length guard: `if data.len() < 12 { return false; }` (the summary's "line 481" check is the Step 5 box_size guard below)
- Step 5 guard: `if (data.len() < box_size) || !box_size.is_multiple_of(4) { return false; }`
  Only rejects box_size > len or not multiple of 4. box_size 0, 4, 8, 12 pass.
- Step 6: `data[4..].starts_with(b"ftyp")`
- L494-496: `data[8..].starts_with(&mp4) || data[16..box_size].chunks(4).any(...)`
  If bytes 8..10 are not "mp4", `data[16..box_size]` runs with box_size < 16: start > end, so Rust panics
  ("range start index 16 out of range" when len is 12, or "slice index starts at 16 but ends at 12" when len >= 16).

## Spec (https://mimesniff.spec.whatwg.org/#matches-the-signature-for-mp4)
"3. If length is less than 12, return false. 4. Let box-size be the four bytes from sequence[0] to sequence[3], interpreted as a 32-bit unsigned big-endian integer. 5. If length is less than box-size or if box-size modulo 4 is not equal to 0, return false. 6. ... 'ftyp' ... return false. 7. If the three bytes from sequence[8] to sequence[10] are equal to 0x6D 0x70 0x34 ("mp4"), return true. 8. Let bytes-read be 16. 9. While bytes-read is less than box-size, ... 12. Return false."
(Paraphrased from memory of spec text; Servo's own comments in the code mirror these steps.) The spec's loop simply does not execute when box-size <= 16 and returns false. Servo's slice does not model that; it is a bug, not spec behavior.

## Repro (real file, unmodified)
/hdd1/sichangheagent/vl_meeting_work/out/vlm3_servobugs/bug3_mp4/repro : tiny crate that `#[path]`-includes the real mime_classifier.rs, stubbing only `LoadContext` and depending on `mime`. `cargo test` there:
- Mp4Matcher.matches(00 00 00 0C 'ftyp' 'isom') panics (also box_size 8 and 0).
- Control with brand "mp42" returns true (no panic).
- End-to-end: `MimeClassifier::default().classify(LoadContext::AudioVideo, Off, Off, &None, 12 bytes)` panics:
  `mime_classifier.rs:496:17: range start index 16 out of range for slice of length 12`.
Not built: full Servo / `cargo test -p servo-net-traits` (its lib has `test = false`; tests live in a separate tests crate). 
Note: the summary's example bytes `00 00 00 0C 66 74 79 70 ...` only panic if bytes 8-10 are not "mp4"; e.g. "isom".

## Reachability (inference from reading callers, not executed)
Mp4Matcher is in audio_video_classifier, reached via:
1. `MimeClassifier::classify` with LoadContext::Browsing when Content-Type is absent/unknown (`sniff_unknown_type` calls audio_video_classifier, L241), or when supplied type is audio/video (L135).
   Caller: components/script/dom/servoparser/mod.rs:1131 `load_document`, using navigation_params.resource_header. So a navigation to a response with no/unknown Content-Type whose first bytes are a short ftyp box (e.g. 12-byte `0000000C ftyp isom`) hits it.
   https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/script/dom/servoparser/mod.rs#L1131
2. `ResourceFetchMetadata::resource_content_type_metadata` (components/shared/net/lib.rs:1235), used by stylesheet_loader.rs:394 (Style context, which does not use the AV classifier) and possibly others; AudioVideo-context callers were not found in this tree.
Panic location is therefore the script thread (document load), not the net thread. Effect: script-thread panic, i.e. a content-triggerable crash/DoS of that page's script thread (and likely the process or pipeline); exact consequence not tested. Not memory-unsafe.

## Upstream
Already reported: https://github.com/servo/servo/issues/47603 "mime_classifier.rs: Indexing error in Mp4Matcher::matches for box_size < 16" (OPEN, A-network, filed 2026-08-28 by wood-ghost; maintainer suggests `.get(16..box_size)`; a commenter gives wpt-style undersized-ftyp files). Fix PR #47607 "net: Fix mime sniff mp4 bug" was CLOSED unmerged (2026-09-30). Main still has the bug. Not a new finding; nothing filed by us.
Suggested fix: `data.get(16..box_size).is_some_and(|s| s.chunks(4).any(|c| c.starts_with(&mp4)))`.
