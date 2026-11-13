# Candidate PhD stories
(authored by agents unless marked 🧑)

🧑 "What is the story? It needs to be a coherent story to be something I do for my PhD"

Three candidates. All three sources (me, GPT, Gemini) independently proposed A and B. C differs: GPT proposed C1, Gemini C2. Rankings are opinions: GPT ranked A > B > C1; Gemini said use A as the base and B or C2 as the differentiator. I agree with Gemini.

Facts come from the reports in `out/`; the reviews win where they disagree with the original reports. Raw model answers: `gpt.md`, `gemini.md`.

## A. Check JS engines against the language spec, where spec math meets machine integers (me, GPT, Gemini)
- Thesis: turn ECMA-262 algorithms into Verus specs, prove Rust engine builtins against them, and find bugs that test262 misses.
- Why it matters: the spec uses unbounded math. Engines use `i64` and saturating casts. Tests try a few values, but a proof covers every input. Example: test262's `String.prototype.at` tests "use only indices in -4..4" (poke_esmeta).
- New? I found no prior work that combines ECMA-262, Verus, and a Rust engine (vlm5_capture: "no prior art combining these"). Prior engine verification targets C++ or Wasm JITs: VeRA (PLDI 2020), TurboTV (ICSE 2024), Icarus (SOSP 2024), Crocus (ASPLOS 2024).
- Have: a proof of a port of Boa's `at` found a crash on real Boa (`"abc".at(-1e300)`), confirmed independently (vfy_at). Other confirmed bugs: Boa and Nova integer conversion and resize panics (cx_builtins, vfy_hunt2). Each Verus contract rejected its 4 chosen bugs (poke_mutants).
- Missing: specs are transcribed by hand. Proofs check hand ports, not Boa's source. Proxies and getters are not modeled. Several contracts accepted wrong behavior (cx_proofs).
- Next: (1) build ESMeta on Java 17 and generate specs from it (now blocked: host has Java 11); (2) cover one whole family of builtins, e.g. all index and conversion functions; (3) test spec strength on held-out real bug fixes.
- Risk: it reads as "bug hunting with Verus" unless the spec pipeline becomes a reusable method. Boa and Nova are small engines, not V8.

## B. Proofs that hold for the current page, guarded at runtime (me, GPT, Gemini; this is the advisors' differentiator)
- Thesis: when a page loads, prove a property of a script (e.g. "never reads `document.cookie`") assuming the page state you see, and guard that state. If the state changes, drop the proof.
- Why it matters: proving things for every possible state of JS is often intractable, and a monitor only sees one run. The advisors asked 🧑 "for the given state, what is the behavior of this? As opposed to, for any given state", and said redoing verification on the fly 🧑 "would be really novel".
- New? Searches found no system that combines proof, state snapshot, and invalidating guard (p4_prior_work_check, "[not found]"). The pieces exist apart: JIT deoptimization (CoreJIT, POPL 2021), staged analysis (PLDI 2009), Dynamic Determinacy (PLDI 2013). The review warns: "Novelty is not established" (cx_synth).
- Have: motivation from the group's kind of web data. 63 of 95 sites changed a built-in prototype after load. 11 of 139 pages sent the email to another site before submit (vlm2_scripts, cx_scripts).
- Missing: almost all of the core. The prototype symbolic executor is unsound (cx_synth). There is no guard and no measurement.
- Next: (1) a sound checker for a tiny JS subset that outputs the state it relied on; (2) a guard in Boa that drops the proof when that state changes; (3) replay crawled pages and measure how long proofs survive.
- Risk: pages may change prototypes so often that guards fire right after load, and the proofs then never pay off.

## C1. Verify the facts a JIT relies on (GPT)
- Thesis: prove V8's typer ranges and side-effect annotations sound, so optimizations that use them rest on checked facts.
- Have: bounded models reject the CVE-2020-6418 bug and pass 9 of 10 integer typer rules. They are hand-written, not V8.
- Risk (GPT): "VeRA/TurboTV/Icarus leave less conceptual whitespace". C++ makes it costly to connect proofs to V8's real code.

## C2. Keep proofs valid as the code changes (Gemini)
- Thesis: detect when commits break proofs or move outside a proof's preconditions, and repair them.
- Have: a real Smallbitvec overflow fix needed "zero proof repair" only because the proof's preconditions excluded the inputs the fix changed (vlm6_repair). There is no real repair case yet.
- Risk: the models are hand-written, so turning upstream diffs into model diffs by hand could bias the results.
