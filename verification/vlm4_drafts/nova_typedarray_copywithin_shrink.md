# %TypedArray%.prototype.copyWithin panics when argument conversion shrinks the buffer below an index
(authored by agents unless marked 🧑)
> Nova has no SECURITY.md (checked the repository root and `.github/`); file as a GitHub issue at https://github.com/trynova/nova/issues.

If a `valueOf` callback shrinks a resizable buffer so that its new length is below `start` or `target`, `copyWithin` panics in Rust instead of copying nothing.

## Environment

Reproduced on 2026-11-04 on Linux x86_64 with a release build of `nova_cli` from Nova main commit `877ef1629c47dc4ea495335912975b271d0e3b82`, which was upstream main's HEAD at that time. Node v22.21.1 is shown only as a cross-check.

To reproduce, save the JavaScript below as `repro.js` and run `nova_cli eval repro.js`.

## Reproduction

```js
const b = new ArrayBuffer(8, {maxByteLength: 16});
const t = new Uint8Array(b);
t.set([1, 2, 3, 4, 5, 6, 7, 8]);
t.copyWithin({valueOf() { b.resize(3); return 0; }}, 4);
print(t.join());
```

## Actual result

Nova exits with status 101:

```text
range end index 7 out of range for slice of length 3
```

## Expected result

```text
1,2,3
```

Node prints the same. [ECMA-262 %TypedArray%.prototype.copyWithin](https://tc39.es/ecma262/#sec-%typedarray%.prototype.copywithin) re-reads the length and clamps the count:

```text
Set taRecord to ? ValidateTypedArrayBounds(obj, seq-cst).
Set length to TypedArrayLength(taRecord).
NOTE: Side-effects of the above steps may have reduced the size of obj, in which case copying should proceed with the longest still-applicable prefix.
Set count to min(count, length - startIndex, length - targetIndex).
```

Here count = min(4, 3 - 4, 3 - 0) = -1, so nothing is copied.

## Likely cause

[`typed_array_intrinsic_object.rs` L790](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/builtins/indexed_collections/typed_array_objects/typed_array_intrinsic_object.rs#L790) subtracts `usize` values that can underflow:

```rust
let count = count.min(new_len - start_index).min(new_len - target_index);
```

`new_len - start_index` wraps (3 - 4) in release builds, so `count` stays 4 and the copy indexes past the shrunk buffer. A `saturating_sub` would give 0 and skip the copy.

The test262 test `built-ins/TypedArray/prototype/copyWithin/coerced-target-start-end-shrink.js` shrinks only to lengths larger than the indices, so it does not cover this case.
