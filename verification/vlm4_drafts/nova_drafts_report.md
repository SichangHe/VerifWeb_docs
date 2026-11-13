# nova_drafts report
(authored by agents unless marked 🧑)

4 new drafts; nothing filed or contacted. Each repro re-run once from the final draft text on Nova main 877ef16 and Boa main 329e897 (both still HEAD); all still reproduce.

- nova_int_conversion_saturation: https://github.com/trynova/nova/issues (Nova has no SECURITY.md; the draft says so at top)
- nova_tostring_radix_exponent: same destination
- nova_typedarray_copywithin_shrink (panic): same destination
- boa_setfrombase64_resize (panic): Boa Matrix (SECURITY.md) or https://github.com/boa-dev/boa/issues. Expected output cross-checked with Bun 1.3.4 (JSC) because Node 22 lacks setFromBase64

Skipped because vfy_hunt2/REVIEW.md did not rate them new:
- Nova lastIndex, toExponential, toPrecision: test262 FAILs already listed; toPrecision is the same bug as Boa #5225
- Nova hypot and padEnd: not spec violations
- Boa Atomics.add and fromCharCode(2**64): extensions of existing drafts boa_atomics_store_resize and boa_typedarray_int_conversion; could be added there as notes

Left: no reviewer pass on the drafts; no builds (used vfy_hunt2 binaries).
