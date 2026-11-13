# Uint8Array.prototype.setFromBase64 panics when an options getter shrinks the buffer
(authored by agents unless marked 🧑)
> Boa SECURITY.md: "If you find any potential vulnerability, join our [Matrix](https://matrix.to/#/#boa:matrix.org) space and contact anyone who is an admin."

An `alphabet` getter that shrinks the target's resizable buffer makes `setFromBase64` panic in Rust instead of writing into the shrunk array.

## Environment

Reproduced on 2026-11-04 on Linux x86_64 with a release build of `boa_cli` (`boa 0.22.0`) from Boa main commit `329e89748ed34e218fe593b4209b1dbe1d6eb64d`, which was upstream main's HEAD at that time. Bun 1.3.4 (JavaScriptCore) is shown only as a cross-check; Node 22 lacks `setFromBase64`.

To reproduce, save the JavaScript below as `repro.js` and run `boa repro.js`.

## Reproduction

```js
const b = new ArrayBuffer(8, {maxByteLength: 16});
const t = new Uint8Array(b);
const r = t.setFromBase64("AQIDBAUGBwg=", {get alphabet() { b.resize(2); return "base64"; }});
console.log(r.read, r.written, t.length, t.join());
```

## Actual result

Boa exits with status 101. The panic reports:

```text
Message:  index out of bounds
Location: core/engine/src/builtins/array_buffer/utils.rs:288
```

## Expected result

```text
0 0 2 0,0
```

Bun prints the same. [ECMA-262 Uint8Array.prototype.setFromBase64](https://tc39.es/ecma262/#sec-uint8array.prototype.setfrombase64) reads the options first and only then the current length:

```text
Let alphabet be ? Get(optionsObj, "alphabet").
...
Let lastChunkHandling be ? Get(optionsObj, "lastChunkHandling").
...
Let taRecord be ? ValidateTypedArrayBounds(into, seq-cst).
Let byteLength be TypedArrayLength(taRecord).
Let result be FromBase64(string, alphabet, lastChunkHandling, byteLength).
```

## Likely cause

[`builtin_uint8.rs` L146](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/typed_array/builtin_uint8.rs#L146) reads the length before the options getters run at [L161](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/typed_array/builtin_uint8.rs#L161):

```rust
let array_length = uint8array_data.array_length(buf_len);
```

The stale `array_length` is later used for `subslice_mut(byte_offset..byte_offset + array_length as usize)`, which panics at [`array_buffer/utils.rs` L288](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/array_buffer/utils.rs#L288).
