# poke_icache: Verus model of shapes + inline caches vs CVE-2020-6418
(authored by agents unless marked 🧑)

## What was tried
`icache.rs` (~190 lines, Verus 0.2026.11.02 with the z3 4.16 swap) models:
- shapes `{nslots, dbl}` in an append-only table; objects `{shape, slots}`; heap wf = slot count and value representation (Smi vs Double) match the shape
- 3 transitions: add field, elements kind Smi->Double, normalize (drop slots)
- a monomorphic inline cache `{shape, offset, dbl}`
- JIT map inference over an effect chain (`NoWrite | Write | Create{out,shape}`), modeled on V8 `InferReceiverMapsUnsafe`; Write/Create may run arbitrary user code (proxy traps) that applies any wf-preserving transition

Proved (`correct.log`: "verification results:: 8 verified, 0 errors", <1 s):
- `lemma_transitions_wf`: all transitions preserve heap wf
- `ic_hit_safe`: cached shape check passes => cached offset in bounds and value has the cached representation
- `ic_stable`: IC entries stay valid across any transition
- `infer_sound`: a "reliable" inferred shape equals the object's actual shape at the use point
- `elided_check_safe`: optimized load with elided shape check is in bounds and type-correct

## Mutant = CVE-2020-6418 bug shape
`icache_mutant.rs` flips one flag: on `Create` whose output is not the tracked object, inference keeps the reliable bit instead of clearing it. Verus rejects it: `infer_sound` fails with "error: postcondition not satisfied" on both postconditions (`mutant.log`).

Source, Project Zero RCA, Samuel Groß and Sergei Glazunov,
https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2020/CVE-2020-6418.html, verbatim:
> "Bug class: Incorrect side-effect modelling in JIT Compiler"
>
> "The function NodeProperties::InferReceiverMapsUnsafe is responsible for inferring the Map of an object. From the source code documentation: "This information can be either 'reliable', meaning that the object is guaranteed to have one of these maps at runtime, or 'unreliable', meaning that the object is guaranteed to have HAD one of these maps". In the latter case, the caller has to ensure that the object has the correct type, either by using CheckMap nodes or CodeDependencies."
>
> "There is a mistake in the handling of kJSCreate: if the object in question is not the output of kJSCreate, then the loop continues without marking the result as unreliable. This is incorrect because kJSCreate can have side-effects, for example by using a Proxy as third argument to Reflect.construct. The bug can then for example be triggered by inlining Array.pop and changing the elements' kind from SMIs to Doubles during the unexpected side effect."

The model's Smi->Double transition and the Create-with-side-effects step mirror this directly.

## Caveats (facts about the model)
- the mutant is rejected by proof failure, not by a constructed counterexample execution; I did not write a witness lemma
- tiny abstraction: one IC, a linear effect chain, no polymorphic ICs, no CodeDependencies/deopt, no relation to real V8 code
- inferred-shape spec for "unreliable" ("HAD one of these maps") not proved

## Worth pursuing? (opinion)
- as a demo: yes; it took ~1 hour and the CVE maps cleanly onto a one-line mutant
- as research: only if tied to real code (e.g. verifying a Rust JIT's map-inference pass, or extracting the effect model from V8's operator flags); the toy model itself is easy and proves little beyond the definition of "reliable"
