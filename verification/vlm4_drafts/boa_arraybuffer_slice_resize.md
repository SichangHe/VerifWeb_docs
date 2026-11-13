# ArrayBuffer.prototype.slice panics when start conversion shrinks the buffer
(authored by agents unless marked 🧑)
> Boa SECURITY.md: "If you find any potential vulnerability, join our [Matrix](https://matrix.to/#/#boa:matrix.org) space and contact anyone who is an admin."

A `start` argument whose `valueOf` shrinks a resizable buffer makes `ArrayBuffer.prototype.slice` panic in Rust instead of returning a buffer.

## Environment

Reproduced on 2026-11-04 on Linux x86_64 with a release build of `boa_cli` (`boa 0.22.0`) from Boa main commit `329e89748ed34e218fe593b4209b1dbe1d6eb64d`, which was upstream main's HEAD at that time.

To reproduce, save the JavaScript below as `repro.js` and run `boa repro.js`.

## Reproduction

```js
const b = new ArrayBuffer(8, {maxByteLength: 16});
new Uint8Array(b).fill(7);
const result = b.slice({valueOf() { b.resize(2); return 0; }}, 8);
console.log(result.byteLength, Array.from(new Uint8Array(result)).join(','));
```

## Actual result

Boa exits with status 101. The panic reports:

```text
Message:  range end index 8 out of range for slice of length 2
Location: core/engine/src/builtins/array_buffer/mod.rs:741
```

## Expected result

```text
8 7,7,0,0,0,0,0,0
```

The result retains the requested length eight. Only the two surviving bytes are copied; the rest remain zero.

[ECMA-262 ArrayBuffer.prototype.slice](https://tc39.es/ecma262/#sec-arraybuffer.prototype.slice) requires the copy to use the buffer's current length after argument conversion and allocation:

```text
1. Let _currentLength_ be _obj_.[[ArrayBufferByteLength]].
1. Let _maxCount_ be _currentLength_ - _first_.
1. If _maxCount_ > 0, then
  1. Let _count_ be min(_newLength_, _maxCount_).
  1. Perform CopyDataBlockBytes(_toBlock_, 0, _fromBlock_, _first_, _count_).
1. Return _new_.
```

## Likely cause

[Boa's copy](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/array_buffer/mod.rs#L741) uses the original requested length without limiting it to the bytes remaining after the callback:

```rust
to_buf[..new_len].copy_from_slice(&from_buf[first..first + new_len]);
```
