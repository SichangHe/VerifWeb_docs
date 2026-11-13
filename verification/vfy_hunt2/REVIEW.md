# vfy_hunt2: independent check of cx_hunt2/REPORT.md
(authored by agents unless marked 🧑)

## Verdict
Every claimed bug reproduces on my own fresh builds of current main. The report's spec readings are correct. No claim is wrong. Two details differ from the report; neither changes a verdict (see "Differences from the report").

| claim | verdict |
|---|---|
| Nova 1 int conversion saturates | confirmed, new |
| Nova 2 toString(radix) exponent | confirmed, new |
| Nova 3 RegExp lastIndex dropped | confirmed; test262 FAIL already listed, no issue |
| Nova 4 toExponential | confirmed; test262 FAIL already listed, no issue |
| Nova 5 toPrecision < 1e-100 | confirmed; test262 FAIL already listed, no Nova issue; same code as Boa #5225 |
| Nova 6 copyWithin panic | confirmed, new |
| Nova minor hypot / padEnd abort | reproduced; not spec violations |
| Boa setFromBase64 resize panic | confirmed, new |
| Boa Atomics.add panic | reproduced (an extension of an earlier vlm6 finding; I did not search issues for it) |
| Boa fromCharCode(2**64) | reproduced (65535; spec gives 0) |

## Setup
- fresh shallow clones in this directory; `git ls-remote HEAD` matched the report:
  - Nova 877ef1629c47dc4ea495335912975b271d0e3b82, built `tgt_nova/release/nova_cli`
  - Boa 329e89748ed34e218fe593b4209b1dbe1d6eb64d, built `tgt_boa/release/boa`
  - test262 d11543772591a5c24b3229e6195a74c73e56032e (`t262/`)
  - spec: https://tc39.es/ecma262/ (ES2027 draft) fetched 2026-11-04 as `spec/ecma262.html`
- my repros: `mine/*.js` (written independently; the report's are copied to `repro/` but not used)
- cross-check: node v22.21.1 (V8). No SpiderMonkey available. Node 22 lacks setFromBase64.
- memory available at build: 144 GiB

## Outputs (node | Nova)
- `mine/v1.js` `(2**64)|0, (2**63)|0, (1e20)>>>0, (1e20)<<0, Int32Array([2**64]), Int8Array([2**63]), Uint16Array([1e300]), clz32(2**64), imul(2**64,1), fromCharCode(2**64), (2**62)|0`
  - node `0,0,1661992960,1661992960,0,0,0,32,0,0,0`
  - Nova `-1,-1,4294967295,-1,-1,-1,65535,0,-1,65535,0`
- `mine/v2.js` `(2**53).toString(16|36), (2**60).toString(2), (1e-7).toString(16), (255).toString(16)`
  - node `20000000000000 2gosa7pa2gw 1000…0 0.000001ad7f29abcaf48 ff`
  - Nova `2.0ed 2.gosa7pa2gwea 1.0e111100 1.ad7f29abcaf48e-6 ff`
- `mine/v3.js` lastIndex = 1.5 / 2**32 / "2" / -1 (sticky)
  - node `1.5 | number | 4294967296 | null | 0 | 2 | 2 | -1`
  - Nova ` | undefined |  | a | 1 |  | 0 | ` (all read back as undefined; 2**32 matches instead of null)
- `mine/v4.js` `(25).toExponential(0), (3.5)…(0), (1.25)…(1), (1.5)…(0), (123)…()`
  - node `3e+1 4e+0 1.3e+0 2e+0 1.23e+2`
  - Nova `2.5e+1 3.5e+0 1.2e+0 1.5e+0 1.23e+2`
- `mine/v5.js` toPrecision of 1e-101(1), 9e-101(1), 2.2250738585072014e-308(3), 5e-324(1), 1e-99(2)
  - node `1e-101 9e-101 2.23e-308 5e-324 1.0e-99`
  - Nova and Boa both `0e+101 1e-100 0.00e+101 0e+101 1.0e-99`
- `mine/v6.js` length-tracking Uint8Array, `copyWithin({valueOf(){b.resize(3);return 0}}, 4)`
  - node `1,2,3`
  - Nova panic: "range end index 7 out of range for slice of length 3"
- `mine/m2.js` hypot: Nova `Infinity 0`; node `1.4142135623730952e+300 1.4142135623730952e-300`
- `mine/m1.js` `"a".padEnd(2**53-1)`: node RangeError; Nova "memory allocation of 9007199254740991 bytes failed", core dump
- Boa `mine/b1.js` setFromBase64 with alphabet getter resizing to 2: panic "index out of bounds" at `core/engine/src/builtins/array_buffer/utils.rs:288`
- Boa `mine/b2.js` Atomics.add, valueOf resizes to 0: panic "range end index 8 out of range for slice of length 0" at `array_buffer/mod.rs:116`
- Boa `mine/b3.js` `String.fromCharCode(2**64).charCodeAt(0)` → 65535

## Spec text (verbatim, tc39.es/ecma262)
- 7.1.7 ToFixedSizeInteger: "If int = +∞ or int = -∞, return 0.Let fixedInt be int modulo 2bitWidth.NOTE: The following step does not change the two's complement representation of fixedInt.If signed is signed and fixedInt ≥ 2bitWidth - 1, set fixedInt to fixedInt - 2bitWidth.Return fixedInt." ToInt32: "Let int be ? ToIntegerOrInfinity(arg).Return 𝔽(ToFixedSizeInteger(int, signed, 32))." (superscripts lost in extraction: 2^bitWidth)
  - so 2^64 → 0; 1e20 mod 2^32 = 1661992960
- Number::toString: "If radix ≠ 10 or n is in the inclusive interval from -5 to 21, then" → digits only; exponent form is reachable only for radix 10
- RegExpBuiltinExec: "Let lastIndex be ℝ(? ToLength(! Get(regexp, "lastIndex")))." and "If lastIndex > length, then If global is true or sticky is true, then Perform ? Set(regexp, "lastIndex", +0𝔽, true).Return null."
  - lastIndex is an ordinary writable data property, so reading it back must give the stored value (1.5, "2", …)
- toExponential: "If fractionDigits is not undefined, then Let exponent and intSignificand be integers such that 10fractionCount ≤ intSignificand < 10fractionCount + 1 and for which intSignificand × 10exponent - fractionCount - number is as close to zero as possible. If there are two such sets of exponent and intSignificand, pick the exponent and intSignificand for which intSignificand × 10exponent - fractionCount is larger."
  - fractionDigits 0 is "not undefined", so (25).toExponential(0) has 1 digit: ties pick larger → "3e+1"
- toPrecision: "Let exponent and intSignificand be integers such that 10precisionCount - 1 ≤ intSignificand < 10precisionCount and for which intSignificand × 10exponent - precisionCount + 1 - number is as close to zero as possible."
- %TypedArray%.prototype.copyWithin: "Set taRecord to ? ValidateTypedArrayBounds(obj, seq-cst).Set length to TypedArrayLength(taRecord).NOTE: Side-effects of the above steps may have reduced the size of obj, in which case copying should proceed with the longest still-applicable prefix.Set count to min(count, length - startIndex, length - targetIndex)."
  - repro: min(4, 3-4, 3-0) = -1 → countBytes ≤ 0 → loop does nothing; no error
- Uint8Array.prototype.setFromBase64: "Let optionsObj be ? GetOptionsObject(options).Let alphabet be ? Get(optionsObj, "alphabet"). … Let lastChunkHandling be ? Get(optionsObj, "lastChunkHandling"). … Let taRecord be ? ValidateTypedArrayBounds(into, seq-cst).Let byteLength be TypedArrayLength(taRecord)."
  - length must be read after the getters; Boa reads it before

## Engine source (at the commits above)
- Nova 1: https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/abstract_operations/type_conversion.rs#L694 `number.into_f64_(agent).trunc() as i64 as i32`; same pattern at L733 (u32), L769 (i16), L805 (u16), L841 (i8), L877 (u8). Rust `f64 as i64` saturates at ±2^63.
- Nova 2: https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/types/language/number.rs#L1328 and #L1336 `&lexical::write_float_options::JAVASCRIPT_LITERAL,` inside `to_string_radix_n`
- Nova 3: https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/builtins/regexp.rs#L344
  - "// If we we set a value that is not a valid index or undefined, // we need to create the backing object and set the actual // value there." then `if !new_last_index.is_valid() && value.is_undefined() {`
  - the comment says "or undefined" but code says "&& value.is_undefined()", so a non-index non-undefined value is never stored. Inverted condition is my inference from comment vs code.
- Nova 4: https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/builtins/numbers/number_prototype.rs (find via `grep -n "if f == 0"`; ~L114): `if f == 0 { Ok(f64_to_exponential(agent, x, gc).into()) } else { …with_precision… }`
- Nova 5: same file ~L273 `m = format!("{x_f64:.100}");` — 100 fractional digits cannot represent values below ~1e-100
- Nova 6: https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/builtins/indexed_collections/typed_array_objects/typed_array_intrinsic_object.rs#L790 `let count = count.min(new_len - start_index).min(new_len - target_index);` — usize underflow (wraps in release), then the slice copy panics
- Boa: https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/typed_array/builtin_uint8.rs#L146 `let array_length = uint8array_data.array_length(buf_len);` precedes L161 `Self::get_base64_options(options, context)?`; later `data.subslice_mut(byte_offset..byte_offset + array_length as usize)` panics in https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/array_buffer/utils.rs#L288 `.expect("index out of bounds")`. Its own comment ("FromBase64 does not invoke user code, so the backing buffer cannot be detached or shrunk between the bounds check above and the copy below") is true, but the user code runs before the length read is redone, which it never is.
- Paths above are as found in my clone; directory names for Nova 4/5/6 were located by `find`, I did not double-check their exact URL path segments.

## test262 coverage (d1154377) and Nova expectations
- Nova `tests/expectations.json` lists as "FAIL": `built-ins/Number/prototype/toExponential/return-values.js` (L1111), `built-ins/RegExp/prototype/exec/S15.10.6.2_A4_T8.js` (L1710; sets `re.lastIndex = "12"`), `staging/sm/Number/toPrecision-values.js` (L7579)
- no test262 file outside BigInt tests uses 2^64 / 1e20 / 18446744073709551616 for int conversion (grep found only Math/sqrt, parseInt, String/S9.8.1 — unrelated)
- `Number/prototype/toString/` radix tests: none uses large/small magnitudes with radix ≠ 10 (grep)
- `TypedArray/prototype/copyWithin/coerced-target-start-end-shrink.js`: length-tracking cases shrink to 3 with indices ≤ 2; never index ≥ new length. Agrees with report.
- `Uint8Array/prototype/setFromBase64/`: no file mentions `resize`; only `detached-buffer.js`. Agrees with report.

## Existing issues (gh search, 2026-11-04)
- trynova/nova: "ToInt32", "toString radix", "lastIndex", "toExponential", "saturat", "panic resizable" → nothing; "toPrecision" → only #359 (benchmarks, unrelated); "copyWithin" → #727 closed "Test failures related to `Array.prototype.copyWithin`" (Array, not this panic)
- Nova PRs for these terms: none relevant
- boa-dev/boa: "setFromBase64" → only #5170 closed (implementation request); "toPrecision" → #5225 open "`Number.prototype.toPrecision` returns wrong output for subnormal floats like `Number.MIN_VALUE`"; "toExponential" → #4169 open "Fix `Number.prototype.toExponential()` value rounding"

## Differences from the report
- Nova 2 is wider: small magnitudes too, `(1e-7).toString(16)` → `1.ad7f29abcaf48e-6` (node `0.000001ad7f29abcaf48`)
- Nova 4: `(1.5).toExponential(0)` → `1.5e+0` (spec `2e+0`), consistent with the report's cause
- Nova 3: sticky `lastIndex=-1` also reads back undefined
- not verified: whether test262 runs in Nova's CI actually hit these FAILs today (I trusted expectations.json content); Boa Atomics issue search (out of scope of "new" claims)
