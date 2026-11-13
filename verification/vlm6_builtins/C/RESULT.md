# Group C (%TypedArray%, ArrayBuffer, DataView, Atomics) on Boa 329e897
(authored by agents unless marked 🧑)
Method: differential testing vs node (not Verus/z3). t1.js: ~19 index values x 17 ops x 3 types (out1/outn).
t2.js: ~200 edge cases, run one per process (cases) because Boa panics abort the script (out2b/out2bn).
All other behaviors (clamping, relative index, ctor offset/length, set offset, with, indexOf, DataView/Atomics index checks) matched node.
Differences only in error messages, allocation limits (ArrayBuffer(2**31+) throws RangeError), and isLockFree(1.5) (Boa is spec-correct).

## Confirmed bugs (real Boa)
1. Int8/Uint8/Int16/Uint16 conversion saturates for |x| >= 2**63 (Int32/Uint32 are fine).
   Repro r4.js / r5.js:
     var a=new Int8Array(1); a[0]=2**64;  // Boa -1, expected 0
     var u=new Uint8Array(1); u[0]=2**64; // Boa 255, expected 0
     var b=new Uint16Array(1); b[0]=1e300; // Boa 65535, expected 0
     new Int16Array(1).fill(1e300)[0]     // Boa -1, expected 0
     dv.setInt16(0,1e300); dv.getInt16(0) // Boa -1, expected 0
     Atomics.store(new Int16Array(1),0,1e300); // same wrong value
   Also 1e20: Int16/Uint16 give -1/65535, expected 0. Threshold: 2**63-1024 ok, 2**63 wrong.
   Affects element set, fill, DataView.set{Int8,Uint8,Int16,Uint16}, Atomics. Negative large values give 0 (correct by luck, except 1e20 ones fine).
   Likely a f64 `as i64/u64`-then-narrow saturating cast. Spec: ToInt8/ToUint16 etc. = modulo 2^N of the mathematical integer.
   test262: no test with values >= 2**63 found (grep for 2**64/1e300 in TypedArray*/DataView gave no hits). Boa issues: none found via gh search.
2. PANIC ArrayBuffer.prototype.slice when an argument's valueOf shrinks a resizable buffer (r1.js):
     const b=new ArrayBuffer(8,{maxByteLength:16});
     b.slice({valueOf(){b.resize(2);return 0}},8);
   Boa: panic "range end index 8 out of range for slice of length 2" at core/engine/src/builtins/array_buffer/mod.rs:741. Expected (node): returns zero-filled length-8 buffer, no throw.
3. PANIC Atomics.store (and presumably other Atomics ops) when the index valueOf shrinks a resizable buffer (r2.js):
     const b=new ArrayBuffer(8,{maxByteLength:16}); const u=new Int32Array(b);
     Atomics.store(u,{valueOf(){b.resize(0);return 0}},1);
   Boa: panic "range end index 8 out of range for slice of length 0" at array_buffer/mod.rs:116. Expected: TypeError/RangeError (node: TypeError).
   Both panics are in the same file; spec requires revalidation after user-code conversion.

## Not bugs / proof-only
No Verus/z3 proofs written; bugs found by testing, so all three are confirmed on real Boa.
Files: t1.js t2.js out*.txt r1-r5.js.
