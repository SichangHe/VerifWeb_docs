# Tab isolation inside one JS-engine process: feasibility sketch
(authored by agents unless marked 🧑)

Labels: [F] fact measured/ran here, [B] belief/recall, unverified, [I] inference.

## Built
- `mem/bench.js`: N copies of the same toy page (2000 objects) as N `vm` contexts, N worker isolates, or N node processes. Metric: summed PSS (shared pages split fairly), minus parent baseline.
- `model/`: Rust model of a two-realm heap with a write barrier and a shared-immutable space. Randomized-op test of the invariant "everything realm R reaches is R-owned or Shared, and Shared points only to Shared."

## Run
- `cd mem; for m in ctx worker proc; do for n in 1 10 50; do node bench.js $m $n; done; done` (raw: `mem/results.jsonl`)
- `cd model; cargo run --release`

## Results
[F] Per-tab PSS (KB), Node 22, toy page:
- vm context: 1191 (N=1), 541 (N=10), 437 (N=50)
- worker isolate: 3393, 1153, 777
- process: 9590, 9292, 8978
So one-process contexts cost ~20x less than processes here. Caveat [F]: a bare Node process is ~9 MB, not Chrome's ~300 MB/tab; Chrome's cost is mostly the page's DOM/layout/GPU/renderer state, not the JS engine. [I] Savings from merging only the *JS engine* are small compared with 300 MB; the claim needs the whole renderer in-process, which is much larger than a JS verification target. Also `vm` contexts share one isolate/heap, so they are NOT isolated against engine bugs; that is the point of the claim.
[F] Model: without the barrier 19975/20000 random runs break the invariant (e.g. realm 0 reaches realm 1's mutable object); with the barrier 0/20000 in 60-step runs. This is testing, not proof; it shows only that the property is non-trivial and that three rules are needed: no cross-realm store, share only deep-immutable objects, import only Shared or own objects.

## What a verified component would exclude [B]
Recall, not web-checked; verify before citing:
- JIT type confusion / bounds-check elimination bugs giving arbitrary read/write in the heap (e.g. CVE-2020-6418, CVE-2021-30551, V8). In a one-heap design these become cross-tab leaks; verifying the JIT's typing/range reasoning, or the barrier, closes them.
- Typed array / ArrayBuffer OOB (e.g. CVE-2019-5782).
- GC bugs (use-after-free, missed write barrier), the exact class the model's barrier covers.
- NOT excluded: Spectre-style speculative leaks (CVE-2017-5753), timing channels, DOM/browser-API bugs. Process isolation (Site Isolation) was built largely because of Spectre [B]; in-process verification does not address it. This is the biggest blocker.

## Blockers
1. Spectre/side channels: no functional-correctness proof covers them.
2. Scope: leaks come from the JIT, runtime, and the DOM bindings; "the engine" is millions of lines. Surveyed tools (see `/ssd1/sichangheagent/phd_labs/ara/research_projects/web_js_survey/rust_verifiers.md`) target Rust; V8/SpiderMonkey are C++ [B: SpiderMonkey has Rust parts].
3. Only the engine is verified, unless JIT output is checked per run (Speaker 1's point): need translation validation of generated code, or restricted JIT output.
4. Shared state (strings, atoms, code cache, builtins) is the savings source and also the leak surface; the model's Shared space is the abstraction, and the real work is proving it deep-immutable.
5. Verus not installed; no proof attempted. [I] The model is small enough for Verus/Kani; Kani is easier on this Rust (bounded model checking of `store/share/import`).

## Differentiators vs prior work [B]
- Site Isolation: process boundary, trusted OS/MMU, costs memory; this: language-level boundary, needs proof, saves memory, loses Spectre protection.
- Wasm SFI / RLBox / VeriWasm: isolate *untrusted code* inside a trusted host; this isolates *two peers inside the engine* where the engine itself is the isolation mechanism. VeriWasm checks compiled Wasm binaries (translation-validation style, fits blocker 3).
- Verified JIT work (CompCert-style, Jitk for kernel BPF, Wasm-JIT verification efforts): prove semantics preservation; this wants a non-interference/memory-safety property across realms, weaker than full correctness and so more tractable. [I]
- Cloudflare Workers / V8 isolates already run many tenants per process; they rely on unverified V8 plus extra OS sandboxing [B]. A verified barrier would be the novel piece.

## Next (bite-sized)
1. Port model to Kani/Verus with real `Vec` heap, prove the invariant for all ops.
2. Add GC (moving, per-realm arenas) to the model; prove GC preserves the invariant.
3. Pick one engine (QuickJS, small, C) and check whether its realm API admits the barrier; measure per-context cost with real DOM-less pages.
