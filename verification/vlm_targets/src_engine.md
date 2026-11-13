# Real-world JS engine failures (V8 / SpiderMonkey)
(authored by agents unless marked 🧑)

Method: pages fetched with curl and tag-stripped; quotes copied from the stripped text. JavaScriptCore: no case verified (gap). Irregexp (V8): no in-the-wild case found; see item 7.

## Cases

### 1. CVE-2020-6418 (V8 TurboFan, ITW 0-day): side-effect modeling
- Source: https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2020/CVE-2020-6418.html (crbug 1053604)
- Quote: "There is a mistake in the handling of kJSCreate: if the object in question is not the output of kJSCreate, then the loop continues without marking the result as unreliable. This is incorrect because kJSCreate can have side-effects, for example by using a Proxy as third argument to Reflect.construct."
- Class: map inference skipped the "unreliable" marking for a side-effecting node, so inlined Array.pop assumed a stale elements kind (SMI vs double).
- Violated: any operation on the effect chain that may write must invalidate inferred object maps (side-effect model must be sound).

### 2. CVE-2021-37975 (V8 GC, ITW 0-day): ephemeron marking
- Source: https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2021/CVE-2021-37975.html (crbug 1252918)
- Quote: "When handling ephemerons (WeakMap, WeakSet etc.), a logic bug in the v8 garbage collector means that live objects may remain unmarked and be collected, leading to use-after-free."
- Class: the iterative ephemeron fixpoint exits while `current_ephemerons` still holds entries made live by the marking-worklist drain.
- Violated: marking must reach the fixpoint (every reachable object marked) before sweeping.

### 3. CVE-2021-4102 (V8 TurboFan + GC, ITW 0-day): write-barrier elision
- Source: https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2021/CVE-2021-4102.html (crbug 1278387)
- Quote: "An optimization in EarlyOptimizationPhase that elides ChangeTaggedToInt32 -> ChangeInt31ToTaggedSigned caused a HeapNumber to be stored to an object in a field with a TaggedSigned representation. A check before EarlyOptimizationPhase in SimplifiedLoweringPhase makes the correct assumption that write barriers can be elided when storing anything to a field in an object with the TaggedSigned representation."
- Class: a later peephole removes a Smi-truncation node after write-barrier elision was already decided on the assumption that node existed.
- Violated: compiler phases must preserve cross-phase invariants (a pointer store into old space needs a barrier; the barrier decision must match the final stored type).

### 4. CVE-2022-3723 (V8 TurboFan, ITW 0-day): weak FieldType + dependency
- Source: https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2022/CVE-2022-3723.html
- Quote: "When optimizing property stores, turbofan correctly handled the "None" FieldType case only for the "kStore" AccessMode but not for the "kStoreInLiteral" case. That made it possible to change the value of a FieldType "None" field without generalizing the FieldType, and so without deoptimizing any code that still relies on the previous FieldType."
- Class: one store path (kStoreInLiteral) missed a case that the sibling path handled; the weak-Map GC clearing interacts with elided CheckMaps.
- Violated: code that elided a CheckMap must be deoptimized whenever its field-type dependency changes.

### 5. CVE-2021-21220 (V8 TurboFan, Pwn2Own 2021; not confirmed ITW): numeric typing / bounds-check elimination
- Source (exploitation): https://www.thezdi.com/blog/2021/12/15/exploitation-of-cve-2021-21220-from-incorrect-jit-behavior-to-rce
- Quote: "V8 might remove array bounds checking if it concluded that typer_index is always zero (or, in general, if typer_index * 10 is provably always inside the bounds of the array). [...] In the event that JITted code produces an erroneous numeric result, though, it may be possible fool the V8 engine into thinking typer_index must be zero, while in actuality it will be set to a different (erroneous) value."
- NVD text (generic): "Insufficient validation of untrusted input in V8 in Google Chrome prior to 89.0.4389.128 allowed a remote attacker to potentially exploit heap corruption via a crafted HTML page." (https://nvd.nist.gov/vuln/detail/CVE-2021-21220)
- Class: JIT computes a wrong numeric result, so the Typer's range is too narrow; bounds-check elimination (later removed in V8) turns it into OOB.
- Violated: Typer ranges must over-approximate every runtime value. The root-cause instruction for CVE-2021-21220 itself is UNVERIFIED (I read only part 3 of the ZDI series).

### 6. CVE-2019-11707 (SpiderMonkey IonMonkey, ITW, also found by Fuzzilli): speculation guards
- Source: https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2019/CVE-2019-11707.html (Bugzilla 1544386)
- Quote: "In essence, the JIT failed to ensure that calling Array.prototype.pop would not end up loading an array element from a prototype of the array."
- Also: "This bug was independently found through fuzzing with Fuzzilli."
- Class: JIT specialized Array.pop without guarding against indexed elements/accessors on the prototype.
- Violated: speculated type and side-effect-freedom of an inlined builtin must hold for every heap shape the guards admit.

### 7. Regex engines (weak coverage)
- CVE-2025-1934 (SpiderMonkey RegExp, GC): https://www.mozilla.org/en-US/security/advisories/mfsa2025-14/ ; rated moderate, not ITW.
  Quote: "It was possible to interrupt the processing of a RegExp bailout and run additional JavaScript, potentially triggering garbage collection when the engine was not expecting it."
  Class: re-entrancy into JS during regexp-to-interpreter bailout while the engine holds unrooted/unstable state.
  Violated: GC may only run at points where the engine's state is rooted/consistent. (Fuzzer attribution: UNVERIFIED.)
- CVE-2016-1688 (V8 Irregexp, old): https://nvd.nist.gov/vuln/detail/CVE-2016-1688
  Quote: "The regexp (aka regular expression) implementation in Google V8 before 5.0.71.40, as used in Google Chrome before 51.0.2704.63, mishandles external string sizes, which allows remote attackers to cause a denial of service (out-of-bounds read) via crafted JavaScript code."
  Violated: compiled regexp must bound reads by the actual subject-string length. NVD gives no deeper RCA; root-cause detail UNVERIFIED.
- Searches found no Project Zero ITW RCA for any regexp bug. The PZ RCA index (https://googleprojectzero.github.io/0days-in-the-wild/rca.html) has V8, SpiderMonkey and WebKit entries, none about regexp.

## Aggregate statistics
1. V8 share of Chrome ITW 0-days, 2021 (6 of 14 = 43%, my arithmetic):
   "Chromium had a record high number of 0-days detected and disclosed in 2021 with 14." and "6 JavaScript Engine - v8 (CVE-2021-21148, CVE-2021-30551, CVE-2021-30563, CVE-2021-30632, CVE-2021-37975, CVE-2021-38003)"
   https://projectzero.google/2022/04/the-more-you-know-more-you-know-you.html
2. Memory-corruption dominance: "Out of the 58 in-the-wild 0-days for the year, 39, or 67% were memory corruption vulnerabilities." Of these: "17 use-after-free". Same URL.
3. Attacker's Chrome chain used only JIT bugs: "All vulnerabilities used by the attacker are in V8, Chrome's JavaScript engine" and "they are JIT compiler bugs." (WebFetch paraphrase boundary: the two fragments were returned split; the exact joined sentence is UNVERIFIED.) https://projectzero.google/2021/01/in-wild-series-chrome-exploits.html
4. Variants: Maddie Stone's 2022 review, "Over 40% of itw 0-days are variants" (tweet text as surfaced by search; primary Google blog post not opened, UNVERIFIED): https://x.com/maddiestone/status/1684595410781020160

## Notes
- Fuzzilli's README says side-effect bugs are hard for generic fuzzers; PZ on CVE-2020-6418: "JIT side-effect related bugs are likely hard to discover through generic JavaScript engine fuzzing approaches, as, without specific compiler instrumentation, they don't normally result in observable misbehaviour at runtime (i.e., a crash)."
- Fuzzilli bug showcase: https://github.com/googleprojectzero/fuzzilli (README, "bug showcase").
- Several search results mentioned 2026 CVEs with implausible IDs; I did not use them.
