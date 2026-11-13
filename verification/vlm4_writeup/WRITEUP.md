# Verification targets for JavaScript and the browser: first pass
(authored by agents unless marked 🧑)

Draft for the human to edit. Nothing here has been sent. Written in the student's voice.

At the Nov 3 meeting you asked me to:
- 🧑 "Write down 10 different things that you might like to verify, either about individual JavaScripts or the engine itself."
- 🧑 "Think about, if you had to work in this space, what are the… Possible questions? What are the… you know, the correctness issues that you would address, what are the tools you would use"
- 🧑 and you warned "you need to have some differentiator"

Short version. I picked ten targets, each motivated by a reported real-world failure. For most I built a small check. The experiments and source reading identified eight defects in real code, two of them already reported upstream (section 4). Every proof below is about a model or transcription I wrote, not the shipped engine. For a differentiator I propose building on the meeting's "for the given state" question: prove a property of a script assuming the page state captured at load, and guard that assumption at run time (section 3). I found no published system that does this, but a search can't show it's new.

## 1. Ten things to verify

Each item gives the failure that motivates it, the property, and what I tried. Results are on models unless stated.

Engine: JIT and GC
1. The JIT's side-effect model is sound. CVE-2020-6418 (V8, exploited in the wild): Project Zero says "kJSCreate can have side-effects, for example by using a Proxy". Property: an IR node that can run user code must invalidate any inferred heap/type facts that code may change. Tried: a z3 model of V8's map inference over 9 abstract opcodes whose effects I assigned by hand, checked on all sequences of up to 4 of them. The model of V8 8.0 gives 396 violations, the smallest with the CVE's shape; the model of the checked main revision gives 0. This is consistent with the CVE, not an independent discovery.
2. The typer (the pass that assigns each value a range of possible numbers) only produces ranges that contain every runtime value. Motivation: CVE-2021-21220, a range mismatch. Tried: z3 on 10 integer range rules from V8's `operation-typer.cc`, with inputs restricted to int32 and divide-by-zero excluded. Nine pass in a bit-vector model; multiplication timed out there and passed only in an unbounded-integer model. Four deliberately broken variants give counterexamples. Floats (NaN, -0, infinities) and the generated machine code implicated in that CVE are not checked.
3. Decisions made in one compiler phase stay valid after later phases. CVE-2021-4102: a write barrier was elided based on an assumption a later phase broke. Tried: a Verus proof on a toy IR with no control flow. It uses allocation folding across a call, a different mechanism in the same family. Removing the guard makes the proof fail with a 4-instruction witness.
4. The garbage collector never frees a reachable object. CVE-2021-37975 (V8, in the wild): "live objects may remain unmarked and be collected, leading to use-after-free." Tried this on Boa, a JS engine in Rust; see section 4.

Engine: isolation
5. Sandboxed code can't cause unauthorized memory accesses. Wasmtime CVE-2023-26489 computed "a 35-bit effective address instead of WebAssembly's defined 33-bit". Tried: a Verus model of a Wasm bounds check, which rejects the 35-bit version. Also a Verus model of V8's sandbox pointer table: a lookup returns a valid pointer only if the entry's type tag matches. It verifies assuming only trusted code writes the table; it doesn't show the pointer is to the right object. I found no prior proof of that table.
6. Two tabs in one process can't reach each other's objects. This is the meeting's case (🧑 "if we run two tabs in a single process"). Tried: a Verus proof that a heap with two realms and a write barrier keeps everything reachable from a realm either its own or shared and immutable, for any operation sequence. Spectre-style leaks are out of scope.

Browser components (mostly Rust, in Servo)
7. Parsers match their spec: URL (WHATWG), CSS tokenizer, MIME sniffing. Orange Tsai: "It's all about the inconsistency between URL parser and requester". Tried: Verus on transcriptions of cssparser and Servo code (bugs in section 4). The specs are prose algorithms, so any spec I check against is my transcription.
8. The event loop runs all pending promise jobs before the next timer, as HTML requires. Tried: differential testing of 9,430 generated programs across engines (Boa result in section 4). TLA+ and Verus models of a fixed scheduler pass, but nothing links those models to Boa's code.
9. Rust DOM code obeys the GC rooting contract. Servo #24621 crashed because a destructor touched an already-collected object. Tried: a Kani model that tells that pattern apart from a correct destructor.

Individual scripts
10. Scripts on a page don't send what the user types to other sites. Real cases: British Airways (attackers edited a script served on its payment page) and polyfill.io (a third-party script host bought by a new owner). Tried: crawled 532 URLs and typed canaries (unique test values) into forms without submitting. Before submit, 11 of 139 pages with an email field sent the email canary to another registrable domain: 8 hashed (ad matching), 3 readable or reversibly encoded. I detected no password canary leaving on 68 pages with a password field. A different domain isn't always a different company, and the detector misses some encodings and channels. 215 of 6,894 cross-site script tags (3.1%) had an `integrity` attribute (Subresource Integrity, which pins a script to a hash).

Also considered, not tried: prototype pollution by libraries (lodash CVE-2019-10744), HTML sanitizer round-trips (DOMPurify mXSS), regex blowup (Cloudflare 2019).

## 2. Questions, correctness issues, tools

Questions I'd expect:
- what's the spec? For engine internals I wrote contracts from the code's behavior and from invariants described in bug analyses. Web standards give prose algorithms.
- what connects a model to the implementation? Nothing yet: my C++ and Rust models are hand-written. Verus might let us verify suitable Rust code (Servo, Boa) more directly.
- proof for all states, or for this state? (section 3)
- what do LLM agents add? My guess: turning C++ rules or spec prose into checkable form. Agents built these models. Independent review agents caught mistakes in their claims, including one proof resting on a false trusted assumption, since fixed.

Correctness issues: the four groups in section 1, i.e. analysis soundness and GC completeness in the engine, memory and object isolation, spec conformance and panics in components, and data flow in scripts.

Tools I used: Verus, Kani and Miri (Rust); z3; TLA+; a Playwright crawler; differential testing of generated programs across engines. Verus worked on small arithmetic and structural models derived from real crates. These attempts left out float code and didn't verify the existing interior-mutability code (`Cell`, atomics); raw-pointer code needed rewrites and trusted contracts.

## 3. Differentiator

The meeting asked 🧑 "for the given state, what is the behavior of this? As opposed to, for any given state". My proposal on top of that: when a page loads, capture the state a script depends on, prove a property such as "this script never reads `document.cookie`" assuming that state, and install a guard on that state. If the state changes, we can no longer rely on the proof, so the browser must fall back, e.g. to a separate process or a runtime monitor. What the fallback is, is still open.

Prior work: I found no system that combines proof, state snapshot and invalidating guard. The parts exist separately: JIT speculation with deoptimization (formalized in CoreJIT, POPL 2021), staged analysis that leaves runtime checks (PLDI 2009), and analysis informed by a run (Dynamic Determinacy, PLDI 2013, whose facts still hold for every execution).

Status: my prototype symbolic executor isn't sound; a reviewer found inputs where it says "no exception" and Node throws. There is no guard yet and no measurement on real scripts.

A narrower engine-side gap: VeRA (PLDI 2020) verified selected Firefox range-analysis routines, not the full analysis or its users, and lists Chrome as future work. I found no proof of V8's typer or side-effect annotations. A related system, TurboTV (ICSE 2024), validates single compilations of loop-free functions.

## 4. Defects found

Independent reruns reproduced each at the level stated (real crate, harness with original source, or copied code). I have filed nothing upstream.

- Boa GC: use-after-free from safe Rust when a finalizer hands out a handle to a dead object. Miri flags it on 0.21.0, 0.22.0 and the tested main revision. No existing report found. Whether JS code can trigger it is untested.
- Boa event loop: the default executor (`SimpleJobExecutor`) runs timers before pending promise jobs; it disagrees with Node on 4,171 of 9,430 programs (Boa's CLI executor: 9). Our patch fixes all 4,171 but breaks cancellation: an endless promise chain no longer stops when cancelled. Needs another fix.
- Lightpanda (Zig headless browser, used for crawling): `--block-urls` blocks fetch and XHR to a forbidden host but lets a WebSocket through, on the tested nightly.
- cranelift-bitset (Wasmtime JIT): `ScalarBitSet::<u64>::from_range(64, 64)` panics in debug; our release builds return the full set instead of empty. A sibling case for an 8-bit set appeared in Wasmtime PR #6020.
- Servo `Blob.slice`: after `slice(1)`, about 1,024 chained `slice(1e19)` calls overflow an i64 in copied code: panic in debug, wrong range in release. Servo not built. No report found.
- Servo MP4 sniffing: panics on a 12-byte box, in a harness using the original source; Servo not built. Already reported (servo#47603).
- cssparser: `-\` followed by a newline tokenizes as an identifier; the spec says delimiter. Already reported (rust-cssparser#440).
- cssparser: the line counter overflows at 2^32 newlines (a 4 GiB input). Reproduced; whether the web can reach it is untested.

## Sources (for the human; not for the advisors as is)

Primary: CVE-2021-4102 analysis https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2021/CVE-2021-4102.html; VeRA https://doi.org/10.1145/3385412.3385968; TurboTV https://doi.org/10.1145/3597503.3639189; https://github.com/servo/servo/issues/47603; https://github.com/servo/rust-cssparser/issues/440; https://github.com/bytecodealliance/wasmtime/pull/6020.

Reports, under `/hdd1/sichangheagent/vl_meeting_work/out/`; reviews override originals:
- targets and failure quotes: `vlm_targets/TARGETS.md`, `cx_synth/targets_review.md`
- items 1-3: `vlm2_jit/SUMMARY.md`, `vlm3_review/job2/REPORT.md`
- items 5, 6, 9: `vlm2_iso/{sandbox_verus,tabiso_verus,servo_rooting}/REPORT.md`
- item 10: `vlm2_scripts/t12_offorigin/REPORT.md`
- Servo Verus work: `vlm3_servo/SUMMARY.md`, `cx_servo/REVIEW.md`, `vlm4_sbvfix/REPORT.md`
- prior work: `cloud/p4_prior_work_check.md`, `cx_synth/prior_review.md`
- defects: `cx_gc/REVIEW.md`, `cx_loop/REVIEW.md`, `cx_bugs/REVIEW.md` and `servo_review.md`, `vlm3_servobugs/SUMMARY.md`
- runtime prototype: `cx_synth/runtime_review.md`
- this draft's review: `cx_writeup/REVIEW.md`
