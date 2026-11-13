# T1: side-effect soundness of V8 map inference (InferMapsUnsafe), CVE-2020-6418 shape reproduced
(authored by agents unless marked 🧑)

## Modeled
Effect-chain walk of `NodeProperties::InferReceiverMapsUnsafe` (V8 tag 8.0.426.15, `src_v8/node-properties-8.0.cc` L399-527; fetched from raw.githubusercontent.com) and its successor `InferMapsUnsafe` (V8 main, `src_v8/node-properties-main.cc` L406+, fetched 2026-11-03).
Fact (diff of the two files): main's `kJSCreate` case has the extra line `result = kUnreliableMaps;  // JSCreate can have side-effect.`; 8.0 has a bare `break`. That line is the CVE-2020-6418 fix shape. I did not check that 8.0.426.15 is exactly the vulnerable release.

Model (`model.py`): a chain of effect nodes, oldest to newest, walked newest to oldest as in the C++ loop. 9 abstract opcodes: CheckMaps(recv), CheckMaps(other), StoreField[map](recv, const), StoreField[map](recv, dynamic), StoreField[map](other), StoreElement, pure read (kNoWrite), Call (default, !kNoWrite), JSCreate(other).
Concrete semantics: receiver has one real map `r`. CheckMaps(recv, M) passes only if r in M (else deopt). Map-store to recv with a constant sets r=v. Any other write/JS-running op sets r to an arbitrary value (other-object stores can alias; JSCreate can run a Proxy trap).

## Property
If the inference returns *reliable* with map set S (CheckMaps set, or {v} for a constant map store), then the receiver's real map at the end of the chain is in S, for every op sequence. Equivalently, every effectful op between the proving node and the use must have downgraded the result to unreliable.

## Result
Z3 (per sequence: is "reliable but r not in S" satisfiable?), all 9^1..9^4 sequences (7,380 sequences), loops/EffectPhi/allocation renaming not modeled:
- buggy variant (8.0 JSCreate = `break`): 396 violations. Minimal counterexample: `(CheckMaps_recv, JSCreate_other)`. Reading: CheckMaps(o, M); `JSCreate` (Proxy trap changes o's map); then a use that trusts M, i.e. the CVE-2020-6418 shape.
- fixed variant (main, JSCreate marks unreliable): 0 violations (proved for length <= 4, bounded).
The other opcodes (Call, other-object map store, dynamic map store) are handled soundly in both; only the JSCreate arm differs.

## Verbatim output (`run_out.txt`)
```
BUGGY (8.0, no JSCreate marking): maxlen=4 violations=396
   ('CheckMaps_recv', 'JSCreate_other')
   ('StoreMap_recv_const', 'JSCreate_other')
   ('CheckMaps_recv', 'CheckMaps_recv', 'JSCreate_other')
   ('CheckMaps_recv', 'CheckMaps_other', 'JSCreate_other')
   ('CheckMaps_recv', 'StoreMap_recv_const', 'JSCreate_other')
FIXED (main): maxlen=4 violations=0
real 7.2s
```

## Rerun
`cd /hdd1/sichangheagent/vl_meeting_work/out/vlm2_jit/t1_side_effects && /usr/bin/python3 model.py 4`
(needs `/usr/bin/python3 -m pip install --user z3-solver`, got 5.3.3; the default `python3` here is a venv without z3; don't use `-I`, it hides the user site.)

## Limitations
- Model, not the C++: opcodes are 9 abstract classes, not V8's ~hundreds; the "which opcodes are kNoWrite" table is assumed, not extracted from `operator-properties`/`opcodes.h`. The model's JSCreate is deliberately treated as writing, which is the ground truth of the CVE; it is not derived from V8.
- Bounded (length <= 4), not an unbounded proof; one receiver, no aliasing structure beyond "other may alias".
- Not modeled: EffectPhi/loops, FinishRegion renaming, JSCreate-as-receiver, MapGuard, the stable-map constant shortcut (needs code dependencies), JSCreatePromise.
- The checker is partly circular: "default case marks unreliable iff !kNoWrite" is correct only if every opcode's kNoWrite flag is correct. That is the real remaining risk (the CVE was a wrong effect assumption in one arm, not a wrong flag), and is not tested here. Natural next step: extract flags from the opcode tables and check them against a runtime monitor.
- Verus not used: Z3 Python was faster for bounded enumeration over symbolic map sets.
