# vlm41_jssem: JavaScript semantics as a thesis foundation
(authored by agents unless marked 🧑)

Labels: [F] fact (verbatim quotes, URLs and years are in notes.md), [I] inference, [O] opinion, [?] I don't know. Reading only; nothing built, run or published.

## Short answer

Sichang asked "how far are we from... having... Those things." My answer: a machine-checked semantics of modern JavaScript does not exist, and neither does one of the browser APIs. The pieces that do exist sit in different places and do not connect:
- [F] in a proof assistant: JSCert (Coq) covers ES5 only, has been dormant since 2019, and passes 1796 of 2782 core test262 tests (2014). The other current proof-assistant piece is Warblre/Linden (Rocq, EPFL), which covers ES2023 regexes only, passes 495/498, is maintained daily, and proves regex rewrites correct.
- [F] executable but not proved: ESMeta (KAIST) extracts an interpreter from ECMA-262 itself and has run in ECMA-262's and Test262's CI since Nov 2022. It is maintained (commit on 2026-11-09). ECMA-SL stops at ES6 (92%), and KJS is ES5.1 and abandoned since 2016.
- [F] DOM and events: the only mechanized DOM is the Isabelle core-DOM node tree (2018, no JS attached). JaVerT.Click (ES5 strict, symbolic execution rather than proofs, dormant since 2020) is the only tool that has reasoned about real DOM and event library code.
- [F] not found: any proved-correct JS rewriter, archive rewriter, or JS-to-X compiler. Prototype pollution work is detection only, e.g. Bullseye (NDSS 2026).

[I] The Wasm route is the model. Wasm's spec is written in a DSL (SpecTec) that generates the prose, plus Coq and Isabelle definitions. WasmCert-Rocq passes the full Wasm 2.0 test suite. JS has the first half of that pipeline (ESMeta parses the official spec) but no proof-assistant backend and no host/DOM layer.

## What a PhD could build (opinion)

[O] Foundation: a Rocq (or Lean) backend for ESMeta, i.e. generate a proof-assistant semantics from the ECMA-262 text each year instead of writing it by hand. This attacks the reason JSCert and ECMA-SL died: [F] the ECMA-SL authors say the standard's "rapid growth in size and complexity ... makes it difficult to keep the implementation up to date." Validate the generated semantics by running test262 on the extracted interpreter, as Warblre does.

[O] First paper, with caveats as Harsha allowed: a generated semantics for a slice, proved faithful by test262 plus line-by-line correspondence, with one application proof. Possible caveats: no Proxy, no async, no host hooks, a sequential heap, a trusted extraction step. A good slice is the builtins plus core statements that archive rewriters touch.

Applications it unlocks, best fit first:
1. the archive rewriter Harsha reframed: "produce [a] kind of rewriter ... guaranteed to be correct". [I] This needs host APIs (`fetch`, `location`, `Date`, `Math.random`) and is therefore the hardest. A first version could prove that a source-to-source rewrite (e.g. wrapping `location` accesses) preserves behavior under a modelled host, with the host model trusted. Linden's proved regex rewrites are the precedent for this proof shape.
2. engine conformance: use the semantics as a proved oracle for builtins. [F local] poke_esmeta found a Boa crash (`"abc".at(-1e300)`) in about an hour, and Barrière and Pit-Claudel got regex fixes merged into V8.
3. script checks such as "this library cannot pollute `Object.prototype`". [I] This is feasible on the language core alone, so it needs no DOM. No prior proofs exist, so it would be novel, but [?] whether real libraries are tractable is unknown.

## Biggest risks

- [I] Spec churn: JISET reports an average of "9645.5" updated steps between ES7 and ES10. Without generation, a hand-written semantics rots, as JSCert and ECMA-SL did.
- [I] Host and DOM layer: no standard gives DOM algorithms in a form like ECMA-262's, and a hand-built model of them must be trusted. Every web application (archives included) depends on this layer.
- [I] Competition: KAIST (ESMeta) and EPFL (Pit-Claudel) are both active and are the natural people to build a Rocq backend. [?] I don't know whether either is already doing it; worth asking them before committing.
- [O] Fit: [local memory, human's earlier filter] the human said to avoid ideas needing a JS semantics model unless essential, and to avoid "too PL" framings for these advisors. This direction is squarely PL. Whether the archive story makes it essential is the human's judgment.

## Not covered
- [?] Google Scholar hit a CAPTCHA after 11 queries (not bypassed). Searches for Lean/Iris/Isabelle JS, JSExplain and prototype pollution are therefore thin, so "not found" there is weak evidence.
- PDFs I could not get (paywalled or blocked): JaVerT POPL'18, Gillian II, JaVerT.Click ECOOP'20, SpecTec PLDI'24, JSkel, JSExplain WWW'18, Webspec.

Details and all quotes: notes.md. Prior local work: vlm27_mapback, vlm11_jsengine, vlm14_engine, poke_esmeta.
