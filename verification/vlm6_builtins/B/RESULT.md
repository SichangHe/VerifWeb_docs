# Group B result: String.prototype numeric-arg builtins
(authored by agents unless marked 🧑)

Method: differential test of Boa 329e897 release CLI against node (V8) as oracle, not Verus/z3 (no proofs done; proof-only = none).
Files: diff.js (about 48.7k calls: 14 methods x 6 strings x 38 numeric/odd args x second arg/search strings, plus fromCodePoint), d2.js (60 targeted edge calls), n*.txt/b*.txt outputs.

Result: 0 new confirmed bugs. diff.js outputs identical (48752 lines each).
Methods covered: charAt, charCodeAt, codePointAt, substring, substr, slice, padStart, padEnd, repeat, indexOf, lastIndexOf, includes, startsWith, endsWith, String.fromCodePoint.
Args covered: +-0, NaN, +-Infinity, +-2^31, 2^32, 2^53, +-1e21, +-1e300, 2^64, 5e-324, fractions, strings, null, undefined, bool, objects with valueOf; padding with empty filler and huge maxLength.

Only diffs in d2.js: "a".repeat(2**30), padStart(2**30/2**31), where V8 throws RangeError (V8 string length cap, ~2^29) but Boa returns the string; the spec allows this, so not a Boa bug.
Known bug re-observed (not re-reported): "abc".at(-1e300) panics, "Unexpected get()" at core/string/src/lib.rs:466. Other methods tested with -1e300 do not panic.
test262/Boa-issue checks not done (nothing to report).
