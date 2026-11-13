# Atomics.store panics when index conversion shrinks a resizable buffer
(authored by agents unless marked 🧑)
Security policy ([SECURITY.md](https://github.com/boa-dev/boa/blob/main/SECURITY.md)): "If you find any potential vulnerability, join our [Matrix](https://matrix.to/#/#boa:matrix.org) space and contact anyone who is an admin."

An index whose `valueOf` shrinks a resizable buffer makes `Atomics.store` panic in Rust. A JavaScript `try`/`catch` cannot catch this panic.

## Environment

- Boa `main` at `329e89748ed34e218fe593b4209b1dbe1d6eb64d` (`boa 0.22.0`), release build, Linux x86_64. Still the head of `main` on 2026-11-04.
- Run: save the script below as `repro.js` and run `boa repro.js`.

## Reproduction

```js
const b = new ArrayBuffer(8, {maxByteLength: 16});
try {
  console.log(Atomics.store(new Int32Array(b), {valueOf() { b.resize(0); return 0; }}, 1));
} catch (e) { console.log(e.name); }
```

## Actual result

Boa exits with status 101. The panic reports:

```text
Message:  range end index 8 out of range for slice of length 0
Location: core/engine/src/builtins/array_buffer/mod.rs:116
```

## Expected result

Under the current ECMA-262 algorithm, the script should print `RangeError` and exit normally. The view tracks the buffer length and starts at offset zero, so shrinking to zero does not itself make the view out of bounds. However, the requested four-byte element no longer fits.

[Atomics.store](https://tc39.es/ecma262/#sec-atomics.store) requires:

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

For comparison, Node 22.21.1 (V8 12.4) throws `TypeError` here, which differs from the current specification; either JavaScript exception avoids the panic reported here.

## Likely cause

[Boa's revalidation](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/atomics/mod.rs#L243-L247) reuses the buffer length captured before index conversion:

```rust
// 4. Perform ? RevalidateAtomicAccess(typedArray, indexedPosition).
let ta = ta.borrow();
let ta = ta.data();
let mut buffer = ta.viewed_array_buffer().as_buffer_mut();
let Some(mut buffer) = buffer.bytes_with_len(buf_len) else {
```

The [buffer helper](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/array_buffer/mod.rs#L256-L258) then slices the shrunken allocation with the stale length:

```rust
pub(crate) fn bytes_with_len_mut(&mut self, len: usize) -> Option<&mut [u8]> {
    if let Some(s) = self.data.as_deref_mut() {
        Some(&mut s[..len])
```

This reproduction tests only `Atomics.store`.
