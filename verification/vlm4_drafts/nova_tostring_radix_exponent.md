# Number.prototype.toString(radix) uses exponent notation when radix is not 10
(authored by agents unless marked 🧑)
> Nova has no SECURITY.md (checked the repository root and `.github/`); file as a GitHub issue at https://github.com/trynova/nova/issues.

For large and small magnitudes, `toString(radix)` with a radix other than 10 returns a mantissa-and-exponent string. In radix 15 and above, `e` is a digit, so the result reads as a different number.

## Environment

Reproduced on 2026-11-04 on Linux x86_64 with a release build of `nova_cli` from Nova main commit `877ef1629c47dc4ea495335912975b271d0e3b82`, which was upstream main's HEAD at that time. Node v22.21.1 is shown only as a cross-check.

To reproduce, save the JavaScript below as `repro.js` and run `nova_cli eval repro.js`.

## Reproduction

```js
print([(2 ** 53).toString(16), (2 ** 60).toString(2), (1e-7).toString(16)].join(" "));
```

## Actual result

```text
2.0ed 1.0e111100 1.ad7f29abcaf48e-6
```

## Expected result

```text
20000000000000 1000000000000000000000000000000000000000000000000000000000000 0.000001ad7f29abcaf48
```

Node prints the same. [ECMA-262 Number::toString](https://tc39.es/ecma262/#sec-numeric-types-number-tostring) returns plain digits in this case; exponent notation comes only after the radix-10 assertion:

```text
If radix ≠ 10 or n is in the inclusive interval from -5 to 21, then
```

## Likely cause

[`to_string_radix_n`](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/types/language/number.rs#L1328) formats floats with `lexical::write_float_options::JAVASCRIPT_LITERAL` (also at [L1336](https://github.com/trynova/nova/blob/877ef1629c47dc4ea495335912975b271d0e3b82/nova_vm/src/ecmascript/types/language/number.rs#L1336)), which switches to exponent notation based on magnitude regardless of radix.
