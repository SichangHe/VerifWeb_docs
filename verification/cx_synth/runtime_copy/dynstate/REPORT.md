# Runtime verification with dynamic state: JS prototype
(authored by agents unless marked 🧑)

Labels: [FACT] measured here; [BELIEF] unverified inference; [PRIOR] from memory, no web check done (web search not run).

## What was built
- `symx.py`: ~170-line symbolic executor (Python + z3 5.3) over an acorn AST (`parse.js`) of a tiny JS subset: var/assign, if, while (unrolled to bound 8), + - * comparisons, member/index access, `parseInt`, `document.getElementById`.
- Properties checked per script: (P1) no exception (null/undefined deref, index out of bounds), (P2) never reads `document.cookie`, (P3) every loop exits within 8 iterations.
- Two modes on the same script `page_script.js`:
  - `agnostic`: every heap/DOM read returns an unknown value (any state). This is the state-agnostic baseline.
  - `concrete`: DOM/heap comes from a snapshot JSON. Concrete structure and values; user-controlled fields are symbolic ints with ranges taken from the snapshot (e.g. `<input max=3>`). z3 reasons over those inputs.
- Run: `./run.sh` (needs node, python3; deps already in `pylib/`, `node_modules/`).

## Results [FACT, one machine, 3 runs, tiny script]
- Agnostic: 9 violations (maybe-null deref x5, unknown-length OOB, possible cookie read, loop not bounded). Mostly false alarms for the actual page: it over-approximates.
- Snapshot `snapshot.json` (3 prices, mode=0, qty in [0,3]): PROVED P1+P2+P3 for all user inputs in range. Zero violations.
- Snapshot `snapshot_bad.json` (qty in [0,5], mode=1): 2 real violations with witnesses: `qty=4` gives OOB at line 5 (len=3); cookie read at line 9 (mode==1 is concrete).
- Latency: symex+z3 about 60-80 ms (4 paths, 30-36 solver calls) vs ~300 ms agnostic (34 paths). Node/acorn parse ~50 ms, mostly process startup. [FACT]
- The state-specialized check is cheaper than the agnostic one because concrete values prune paths. [FACT for this script; general claim is BELIEF]

## What this shows and does not show
- [FACT] For the same script, the question "for this state" yields a proof where "for any state" yields only alarms. This is the meeting's distinction, in miniature.
- Not shown: real scripts. The subset has no closures, prototypes, strings, events, async, eval, `this`, exceptions/try, or real DOM semantics. Latency on real pages is unknown.

## Blockers [BELIEF unless noted]
1. Semantics: full JS (prototype chains, coercions, getters, `eval`, dynamic property names, async/event order) has no complete symbolic model; ExpoSE-class tools only cover subsets and have heavy string/regex models.
2. Snapshot soundness: a snapshot is valid only until the state changes. Any DOM mutation, timer, network response or user event invalidates the proof, so one needs either re-verification, or a guard (monitor that watches state the proof depended on) at runtime. Not built.
3. Environment modelling: browser APIs (thousands) need models; unmodelled call = havoc = lost precision.
4. Loop bounds give bounded, not unbounded, proofs (P3 only up to 8 here; need invariants/ranking functions for the general case).
5. Page-load scale: third-party scripts are 100s of KB minified; a 60 ms toy figure says nothing about that [FACT: not measured]. Likely needs lazy/on-demand verification of only handlers actually reached.
6. Snapshot size/capture: heap snapshot cost and which state is "relevant" (dependency slicing) are open.

## Differentiators vs prior work [PRIOR, unverified]
- Runtime monitoring (e.g. JS taint/IFC monitors): checks the executed trace only; here we check all futures from the state (before running) w.r.t. symbolic inputs.
- Partial evaluation / JIT specialization: same idea of specializing on state, but aimed at speed, not proofs.
- Jalangi / ExpoSE / concolic: explore from an initial empty or concrete run, with no specification of "current page state" as a first-class precondition; usually find bugs, not prove absence.
- Static analyzers (TAJS, SAFE, JSAI): state-agnostic abstract heap; this prototype's agnostic mode mimics their over-approximation (unproven).
- Claimed novelty (BELIEF): snapshot-as-precondition + proof/guard pair at page load. Needs real literature check (e.g. "dynamic symbolic execution from checkpointed state", browser-side verification) before claiming.

## Next steps (if pursued)
Drive from a real DOM via CDP/Playwright to emit snapshots; add strings and event handlers; record dependencies of each proof (read set) and install a mutation-observer guard; measure on a few real pages' inline scripts.
