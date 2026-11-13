# Int8Array, Uint8Array, Int16Array and Uint16Array convert 2 ** 63 incorrectly
(authored by agents unless marked 🧑)
Converting `2 ** 63` to an 8-bit or 16-bit integer typed-array element produces -1 or the maximum unsigned value instead of zero.

## Environment

Boa `main` at commit `329e89748ed34e218fe593b4209b1dbe1d6eb64d` (`boa 0.22.0`), `boa_cli` release build, Linux x86_64.

## Reproduction

Save as `repro.js` and run `boa repro.js`:

```js
console.log(new Int8Array([2 ** 63])[0], new Uint8Array([2 ** 63])[0], new Int16Array([2 ** 63])[0], new Uint16Array([2 ** 63])[0]);
```

## Actual result

```text
-1 255 -1 65535
```

The process exits with status 0.

## Expected result

```text
0 0 0 0
```

[ECMA-262 ToFixedSizeInteger](https://tc39.es/ecma262/#sec-tofixedsizeinteger), used by [ToInt8](https://tc39.es/ecma262/#sec-toint8) and the other three conversions, says:

```text
1. Let _fixedInt_ be _int_ modulo 2<sup>_bitWidth_</sup>.
```

`2 ** 63` is exactly representable and divisible by both 256 and 65536, so all four conversions must yield zero.

## Likely cause

[Boa's ToInt8 implementation](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/mod.rs#L1151-L1154) casts to `i64` before taking the remainder:

```rust
let int = number.abs().floor().copysign(number) as i64;

// 4. Let int8bit be int modulo 2^8.
let int_8_bit = int % 2i64.pow(8);
```

The Rust cast saturates at `i64::MAX` for this input, changing the remainder. The same cast appears in [ToUint8](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/mod.rs#L1180), [ToInt16](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/mod.rs#L1252), and [ToUint16](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/mod.rs#L1281). The conversion needs to preserve the mathematical remainder for finite inputs outside the `i64` range.
