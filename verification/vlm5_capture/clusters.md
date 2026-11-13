# Direction clusters
(authored by agents unless marked 🧑)

Hits are `sampler:item numbers` in samples/S_*.md. Samplers: B=browsersec, J=jsrt, C=pc, P=pl, G=gpt, M=gemini. Prior = TARGETS.md / WRITEUP.md / other out/ dirs. Clustering is one agent's judgment; source in scripts/clusters.py.

## New (no prior coverage) (46)

- **Proof repair / spec drift across commits** [6/6] B:32 C:19 J:29 P:8 M:24 G:16,65,78
- **Specs from tests (test262 / WPT / regression tests)** [5/6] J:10,11 C:22 P:2 M:18 G:5
- **Verified ECMAScript builtins / abstract ops / JS interpreter oracle** [4/6] B:28 J:7,8,9 C:10 P:6
- **Parallel style/layout data-race freedom** [4/6] B:27 J:25 M:5 G:20
- **Spec strength via implementation mutants** [4/6] B:16 C:6 M:16 G:6
- **Proof decomposition / trusted boundary / abstraction layers** [4/6] C:33 P:27 M:21 G:13,62,77
- **Unsafe FFI / JS-Rust bindings / WebIDL contracts** [3/6] B:34 P:34 G:46,47
- **Same-origin policy / origin / ORB** [3/6] B:3 P:23 G:27,28
- **Cookie jar / SameSite** [3/6] B:25 P:22 G:29
- **IPC message validation / Constellation lifecycle** [3/6] B:22 P:9 M:9
- **postMessage / structured clone** [3/6] J:31 M:7 G:31,32
- **Spec vacuity / weakness / strength ordering** [3/6] C:8 P:14 G:9,73,74
- **Benchmark of cut-proof / browser-patch tasks** [3/6] B:9 C:1 G:17
- **Cost-of-verification curves / cost-aware agents / negative result** [3/6] C:2,18,32 M:22 G:14
- **Fuzzing <-> proof synergy** [3/6] B:33 P:35 G:67,68
- **Deoptimization state reconstruction** [2/6] J:2 G:41
- **Inline caches / hidden-class shape transitions** [2/6] B:21 J:3,6
- **JS bytecode verifier** [2/6] B:20 G:42
- **CSP evaluation** [2/6] B:13 G:59
- **Fetch / redirect / body consumption** [2/6] P:30 G:25
- **Permissions / capabilities / iframe sandbox / API typestate** [2/6] B:31 G:24,30,60,61
- **Media / font / encoding decoders** [2/6] B:23 P:33
- **DOM tree invariants** [2/6] J:26 G:18
- **JS parser early errors / AST invariants** [2/6] J:22 G:43
- **Counterexample-guided spec strengthening / cex->tests** [2/6] P:4 G:10
- **Cross-verifier comparison (Verus/Dafny/Lean/F*)** [2/6] C:34 P:26
- **SMT brittleness / ghost-code minimization** [2/6] P:16 M:23
- **RL / fine-tuning / prompting on verifier signal** [2/6] C:21,29 P:36
- **Reusable browser lemma / skill library** [2/6] P:13 G:75,76
- **Human-in-the-loop spec review / negative requirements** [2/6] C:30 G:70,71
- **NaN-boxing / tagged value representation** [1/6] M:13
- **Proof-carrying JS admission** [1/6] G:3
- **CSS box-model / layout geometry invariants** [1/6] M:6
- **Navigation / history / session state** [1/6] G:35,36,37
- **Cache partitioning** [1/6] G:34
- **HTTP framing parsers (request smuggling)** [1/6] B:24
- **Content-blocker filter engine (adblock-rust)** [1/6] M:27
- **Constant-time browser crypto glue** [1/6] B:36
- **Verified web-API polyfills** [1/6] C:12
- **Transpile buggy client JS to verified Wasm** [1/6] M:25
- **Incremental verification in browser builds** [1/6] G:15
- **Agent stuck-ness / restart policies** [1/6] C:3,4
- **Model-generation longitudinal study** [1/6] C:20
- **Where agents fail on concurrency** [1/6] C:24
- **Semantic equivalence of refactorings** [1/6] G:79
- **JS breakage taxonomy census** [1/6] C:11

## Partially covered (15)

- **Standards prose -> Verus spec translation / ambiguity** [4/6] B:35 P:7,32 M:19 G:48,72 — partial: WRITEUP 2 notes specs are hand transcriptions
- **Multi-agent adversarial spec audit / consensus** [4/6] B:17 C:7 M:17 G:7,8 — partial: WRITEUP 2 (review agents caught claim errors)
- **JIT IR passes / lowering / constant folding** [3/6] J:28 G:39 M:15 — partial: TARGETS 3 (cross-phase invariants only)
- **JIT translation validation** [3/6] J:27 C:26 P:19 — partial: WRITEUP 3 cites TurboTV as related work only
- **Wasm validator / compiler / bounds checks / JS-Wasm boundary** [3/6] B:18,19 J:12,13,14,15 P:17 — partial: TARGETS 5, WRITEUP 1.5 (bounds-check model)
- **HTML tokenizer / tree builder / mXSS round-trip** [3/6] B:5 P:11 M:8 — partial: TARGETS 8 (considered, not tried)
- **CSS selector matching / cascade** [3/6] B:10 J:24 P:10 — partial: WRITEUP 1.7 (cssparser tokenizer only)
- **Differential spec testing vs engines / triangulation** [3/6] B:14 C:9,31 G:49,69 — partial: WRITEUP 1.8 differential tests across engines (not of specs)
- **TCB accounting / proof coverage / cheating detection** [3/6] C:27,28 P:15 G:63,64 — partial: WRITEUP 2 (one proof rested on false trusted assumption)
- **Bug reports -> properties -> proofs** [2/6] P:31 G:4,66 — partial: WRITEUP 1 derives each target from a CVE by hand
- **Dynamic colocation admission / proof-guided process placement** [2/6] M:2 G:2,52,53 — partial: vlm_runtime/tabiso measures memory, no admission policy
- **HTML sanitizer correctness** [2/6] B:6 P:12 — partial: WRITEUP 1 'also considered, not tried'
- **TLA+ -> Verus executable refinement** [2/6] C:23 M:28 — partial: WRITEUP 1.8 TLA+ model not linked to code
- **Verified information-flow checker for JS** [1/6] B:12 — partial: TARGETS 12 states the property, no checker
- **RegExp matcher equivalence / linear time** [1/6] J:23 — partial: TARGETS 13 (linear time, not tried)

## Covered by prior work (14)

- **State-conditioned proof + runtime guard / verified fast path** [6/6] B:11 J:18 C:14 P:5 M:3,4 G:44,51,80 — covered: WRITEUP 3, vlm_runtime/dynstate
- **Per-script / third-party JS contracts** [5/6] B:29 J:19 C:15 P:24,25 G:50 — covered: TARGETS 12, WRITEUP 1.10 (crawler canaries)
- **Event loop / microtasks / promises / async ordering** [5/6] B:26 J:20,21 P:29 M:26 G:21,22,23 — covered: TARGETS 9, WRITEUP 1.8, vlm_questions/q3_liveness
- **Lightpanda / headless crawler safety and resource bounds** [5/6] B:30 C:16 P:21 M:10,11 G:54,55,56,57,58 — covered: vlm_runtime/lightpanda, cx_maint/lightpanda
- **Verifier feedback for agents (unsat cores, localization)** [5/6] B:15 C:5 P:3 M:20 G:11,12 — covered: vlm_questions/q1_verus_feedback
- **JIT range analysis / bounds-check elimination** [4/6] B:1,2 P:18 M:12 G:38 — covered: TARGETS 2, WRITEUP 1.2 (z3 on V8 typer rules)
- **GC marking / write barrier / incremental progress** [4/6] B:8 J:4,30 P:20 M:14 — covered: TARGETS 4, WRITEUP 1.4 (Boa GC)
- **Single-process tab / realm / worker isolation** [4/6] J:16,17 C:25 M:1 G:1,19,33 — covered: TARGETS 6, WRITEUP 1.6, vlm_runtime/tabiso
- **GC roots / stack maps / rooting contract** [3/6] B:7 J:5 G:45 — covered: TARGETS 10, WRITEUP 1.9 (Kani)
- **URL / JSON parser vs WHATWG** [3/6] B:4 P:1 G:26 — covered: TARGETS 7, WRITEUP 1.7
- **JIT side-effect model / speculation guards** [2/6] J:1 G:40 — covered: TARGETS 1, WRITEUP 1.1
- **Verus scalability on real code size** [2/6] C:17 P:28 — covered: vlm_questions/q2_verus_scale
- **Agent-written Verus for a Servo component** [1/6] C:13 — covered: vlm3_servo, WRITEUP 1.7
- **Built-in prototype integrity** [0/6]  — covered: TARGETS 11 (prior only)
