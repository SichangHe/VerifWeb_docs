# Independent review of Boa builtin claims
(authored by agents unless marked 🧑)

All four requested bug claims are **confirmed on main and the latest release**. The precision bug is already reported upstream. The Atomics panic is confirmed, but current ECMA-262 requires RangeError for this particular length-tracking repro, whereas the installed V8 throws TypeError. Array.prototype.at was excluded as requested.

## Versions and method

Checked on 2026-11-04. GitHub's main endpoint returned `329e89748ed34e218fe593b4209b1dbe1d6eb64d`; its latest-release endpoint returned `v0.22` (commit `337a3668a0dc86dd401ea20906e782249a64a228`). The four relevant source files have no diff between these revisions.

I wrote and ran the four adjacent `.js` repros independently. Main used the existing `out/poke_esmeta/work/boa_bin/bin/boa`; its build provenance is the earlier investigator's statement, “I built `boa_cli` from git HEAD 329e897,” in [their report](../poke_esmeta/REPORT.md). I did not independently rebuild that binary. Release used a freshly downloaded [official Linux executable](https://github.com/boa-dev/boa/releases/download/v0.22/boa-x86_64-unknown-linux-gnu), saved as `boa022`. Both identify themselves as `boa 0.22.0`.

No builds were needed; the initial `free -g` showed 97 GiB available. No upstream messages or issues were submitted. V8 comparison used Node 22.21.1, V8 `12.4.254.21-node.33`. No SpiderMonkey shell (`js`, `js102`, `js128`) or `d8` was on PATH.

[runs.txt](runs.txt) preserves stdout, stderr, and exit codes. To repeat, run each of `integers.js`, `slice.js`, `atomics.js`, and `precision.js` with each executable. Both Boa versions give identical results below; panics exit 101, other runs exit 0.

Specification quotations below retain the ECMA-262 source notation verbatim. I fetched [spec.html at 7628258](https://github.com/tc39/ecma262/blob/7628258064c18d831a7f74ecf3a997bd6345d0bb/spec.html), saved locally as [spec.html](spec.html).

## 1. Narrow integer conversion: confirmed

[integers.js](integers.js):

```js
console.log(new Int8Array([2 ** 63])[0], new Uint8Array([2 ** 63])[0], new Int16Array([2 ** 63])[0], new Uint16Array([2 ** 63])[0]);
```

Boa: `-1 255 -1 65535`. V8: `0 0 0 0`.

[ECMA-262 ToInt8](https://tc39.es/ecma262/#sec-toint8) says:

```text
1. Let _int_ be ? ToIntegerOrInfinity(_arg_).
1. Return 𝔽(ToFixedSizeInteger(_int_, ~signed~, 8)).
```

[ToFixedSizeInteger](https://tc39.es/ecma262/#sec-tofixedsizeinteger) says:

```text
1. If _int_ = +∞ or _int_ = -∞, return 0.
1. Let _fixedInt_ be _int_ modulo 2<sup>_bitWidth_</sup>.
1. NOTE: The following step does not change the two's complement representation of _fixedInt_.
1. If _signed_ is ~signed~ and _fixedInt_ ≥ 2<sup>_bitWidth_ - 1</sup>, set _fixedInt_ to _fixedInt_ - 2<sup>_bitWidth_</sup>.
1. Return _fixedInt_.
```

The same operation underlies ToUint8, ToInt16, and ToUint16 with their respective widths and signs. Since 2^63 is divisible by both 256 and 65536, all four expected results are zero.

Boa [value/mod.rs:1151–1154](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/mod.rs#L1151-L1154):

```rust
let int = number.abs().floor().copysign(number) as i64;

// 4. Let int8bit be int modulo 2^8.
let int_8_bit = int % 2i64.pow(8);
```

The cast saturates before the remainder is computed. The identical cast appears at [1180](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/mod.rs#L1180), [1252](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/mod.rs#L1252), and [1281](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/mod.rs#L1281). This confirms the reported boundary failure, without asserting that every value above it necessarily produces a wrong final remainder.

## 2. ArrayBuffer.slice after shrinking: confirmed

[slice.js](slice.js) fills an eight-byte resizable buffer with 7, then calls:

```js
const result = b.slice({valueOf() { b.resize(2); return 0; }}, 8);
```

Boa: `range end index 8 out of range for slice of length 2`, at `array_buffer/mod.rs:741`. V8: `8 7,7,0,0,0,0,0,0`.

[ECMA-262 ArrayBuffer.prototype.slice](https://tc39.es/ecma262/#sec-arraybuffer.prototype.slice) explicitly limits the copy after callbacks:

```text
1. Let _currentLength_ be _obj_.[[ArrayBufferByteLength]].
1. Let _maxCount_ be _currentLength_ - _first_.
1. If _maxCount_ > 0, then
  1. Let _count_ be min(_newLength_, _maxCount_).
  1. Perform CopyDataBlockBytes(_toBlock_, 0, _fromBlock_, _first_, _count_).
1. Return _new_.
```

The new allocation retains length eight; only two source bytes survive. Boa instead uses the original copy length at [array_buffer/mod.rs:741](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/array_buffer/mod.rs#L741):

```rust
to_buf[..new_len].copy_from_slice(&from_buf[first..first + new_len]);
```

## 3. Atomics.store after shrinking: confirmed

[atomics.js](atomics.js) uses an eight-byte resizable buffer and catches JavaScript exceptions:

```js
Atomics.store(new Int32Array(b), {valueOf() { b.resize(0); return 0; }}, 1)
```

Boa terminates with `range end index 8 out of range for slice of length 0`, at `array_buffer/mod.rs:116`. V8 prints `TypeError` and exits normally.

[ECMA-262 Atomics.store](https://tc39.es/ecma262/#sec-atomics.store) requires:

```text
1. Perform ? RevalidateAtomicAccess(_ta_, _byteIndexInBuffer_).
```

[RevalidateAtomicAccess](https://tc39.es/ecma262/#sec-revalidateatomicaccess) includes:

```text
1. Let _taRecord_ be ? ValidateTypedArrayBounds(_ta_, ~unordered~).
1. Assert: _byteIndexInBuffer_ ≥ _ta_.[[ByteOffset]].
1. Let _elementSize_ be TypedArrayElementSize(_ta_).
1. Let _elementLastByteIndex_ be _byteIndexInBuffer_ + _elementSize_ - 1.
1. If _elementLastByteIndex_ ≥ _taRecord_.[[CachedBufferByteLength]], throw a *RangeError* exception.
```

Here the length-tracking view at offset zero is not itself out of bounds after shrinking to zero, but the requested four-byte element is. Thus the current algorithm requires RangeError. V8's TypeError is an observed comparator result, not the current normative answer.

Boa's purported revalidation at [atomics/mod.rs:243–247](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/atomics/mod.rs#L243-L247) reuses the old `buf_len`:

```rust
// 4. Perform ? RevalidateAtomicAccess(typedArray, indexedPosition).
let ta = ta.borrow();
let ta = ta.data();
let mut buffer = ta.viewed_array_buffer().as_buffer_mut();
let Some(mut buffer) = buffer.bytes_with_len(buf_len) else {
```

The helper eventually executes [array_buffer/mod.rs:256–258](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/array_buffer/mod.rs#L256-L258):

```rust
pub(crate) fn bytes_with_len_mut(&mut self, len: usize) -> Option<&mut [u8]> {
    if let Some(s) = self.data.as_deref_mut() {
        Some(&mut s[..len])
```

`#[track_caller]` immediately above the helper accounts for the panic reporting its caller at line 116. This review does not generalize the result to untested Atomics operations.

## 4. Minimum subnormal toPrecision: confirmed, already known

[precision.js](precision.js): `console.log((5e-324).toPrecision(1));`

Boa: `0e+101`. V8: `5e-324`.

[ECMA-262 Number.prototype.toPrecision](https://tc39.es/ecma262/#sec-number.prototype.toprecision) requires:

```text
1. Let _exponent_ and _intSignificand_ be integers such that 10<sup>_precisionCount_ - 1</sup> ≤ _intSignificand_ &lt; 10<sup>_precisionCount_</sup> and for which _intSignificand_ × 10<sup>_exponent_ - _precisionCount_ + 1</sup> - _number_ is as close to zero as possible. If there are two such sets of _exponent_ and _intSignificand_, pick the _exponent_ and _intSignificand_ for which _intSignificand_ × 10<sup>_exponent_ - _precisionCount_ + 1</sup> is larger.
```

For precision one and the smallest positive binary64 value, the nearest one-digit decimal is 5 × 10^-324.

Boa [number/mod.rs:493](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/number/mod.rs#L493):

```rust
suffix = format!("{this_num:.100}");
```

This rounds the value to zero before significant digits are selected. The all-zero string reaches [line 362](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/number/mod.rs#L362):

```rust
(flt.len() as i32) - 1
```

That produces exponent 101 from the 102-character fixed-format string.

The original report says “No matching Boa issue was found.” This is now contradicted by [open issue #5225](https://github.com/boa-dev/boa/issues/5225), filed by HiteshShonak on 2026-03-22, titled “`Number.prototype.toPrecision` returns wrong output for subnormal floats like `Number.MIN_VALUE`”. Its repro states:

```js
Number.MIN_VALUE.toPrecision(1)
// returns "0e+101" in Boa, expected "5e-324"
```

## Test262 and issue-search limits

Inspected test262 revision `831359a4192ef83b8c50f91363d2ff739fe550f6`. These are scoped source searches, not a complete test262 execution or proof of absence:

- Integer conversion: [conversion-operation.js](https://github.com/tc39/test262/blob/831359a4192ef83b8c50f91363d2ff739fe550f6/test/built-ins/TypedArrayConstructors/internals/Set/conversion-operation.js) uses `testTypedArrayConversions(byteConversionValues, function(TA, value, expected, initial) {`. The shared [byteConversionValues.js](https://github.com/tc39/test262/blob/831359a4192ef83b8c50f91363d2ff739fe550f6/harness/byteConversionValues.js) includes `9007199254740992, // 2 ** 53` but no finite input at the 2^63 threshold. Searches for powers 63/64, `1e300`, and `MAX_VALUE` in TypedArrayConstructors and DataView found only BigInt rejection tests, not this narrow Number conversion case.
- ArrayBuffer.slice: no `.resize(` call found in its test directory. Existing detach/species tests do not establish shrinking-buffer coverage.
- Atomics: `.resize(` searches across its test directory found only the two `notify/retrieve-length-before-index-coercion-non-shared*.js` tests, not a store test. Staging searches found detached-buffer Atomics tests, not a resizing store repro.
- Precision: no `MIN_VALUE`, `5e-324`, or subnormal case found in its 17 test files. [exponential.js](https://github.com/tc39/test262/blob/831359a4192ef83b8c50f91363d2ff739fe550f6/test/built-ins/Number/prototype/toPrecision/exponential.js#L92-L93) tests `assert.sameValue((n).toPrecision(1), "1e-21");`, far above the failing magnitude.

Read-only GitHub issue searches used `gh issue list -R boa-dev/boa --state all --search QUERY --json number,title,url`, with queries `toPrecision`, `Atomics resize`, `"Atomics.store"`, `ArrayBuffer slice`, `"ArrayBuffer" "panic"`, `saturating`, `"Int8"`, and `"Int16"`. Only #5225 directly matched these bugs. Related #4860 is titled “TypedArray iteration methods may panic on mid-iteration buffer detachment”; it concerns a different trigger and operation. No exact existing issue was found for the other three claims; search results cannot establish novelty conclusively.
