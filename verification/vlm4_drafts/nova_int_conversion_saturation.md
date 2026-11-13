# ToInt32, ToUint32 and the narrow integer conversions saturate instead of wrapping for |x| ≥ 2 ** 63
(authored by agents unless marked 🧑)
> Nova has no SECURITY.md (checked the repository root and `.github/`); file as a GitHub issue at https://github.com/trynova/nova/issues.

Numbers of magnitude 2 ** 63 or more convert to -1 or the maximum unsigned value instead of the value modulo 2 ** bitWidth. This affects bitwise and shift operators, typed-array stores, `Math.clz32` and `String.fromCharCode`.

## Environment

Reproduced on 2026-11-04 on Linux x86_64 with a release build of `nova_cli` from Nova main commit `877ef1629c47dc4ea495335912975b271d0e3b82`, which was upstream main's HEAD at that time. Node v22.21.1 is shown only as a cross-check.

To reproduce, save the JavaScript below as `repro.js` and run `nova_cli eval repro.js`.

## Reproduction

```js
print([(2 ** 64) | 0, (2 ** 63) | 0, (1e20) >>> 0, new Int8Array([2 ** 63])[0], new Uint16Array([1e300])[0], Math.clz32(2 ** 64), String.fromCharCode(2 ** 64).charCodeAt(0)].join());
```

## Actual result

```text
-1,-1,4294967295,-1,65535,0,65535
```

## Expected result

```text
0,0,1661992960,0,0,32,0
```

Node prints the same. [ECMA-262 ToFixedSizeInteger](https://tc39.es/ecma262/#sec-tofixedsizeinteger), used by ToInt32, ToUint32, ToInt16, ToUint16, ToInt8 and ToUint8, says:

```text
Let fixedInt be int modulo 2^bitWidth.
```

`2 ** 63`, `2 ** 64` and `1e300` are multiples of 2 ** 32, so they give 0; `1e20` modulo 2 ** 32 is 1661992960.

## Likely cause

[ToInt32](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/abstract_operations/type_conversion.rs#L694) truncates through `i64`:

```rust
number.into_f64_(agent).trunc() as i64 as i32
```

Rust's `f64 as i64` saturates at `i64::MAX` / `i64::MIN`, so the low bits are lost. The same pattern is at [L733](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/abstract_operations/type_conversion.rs#L733) (u32), [L769](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/abstract_operations/type_conversion.rs#L769) (i16), [L805](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/abstract_operations/type_conversion.rs#L805) (u16), [L841](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/abstract_operations/type_conversion.rs#L841) (i8) and [L877](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/abstract_operations/type_conversion.rs#L877) (u8).
