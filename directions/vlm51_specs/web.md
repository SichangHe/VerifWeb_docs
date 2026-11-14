# web-standards slice (vlm51). dates: queries run 2026-11-13. FACT=quoted/counted, INF=inference, OPN=opinion

## 1. how often specs are wrong (gh search API counts, 2026-11-13)
FACT whatwg/html: 6199 issues total. whatwg/html has NO "bug" label (labels: editorial, clarification, interop, needs tests, normative change, topic:*).
FACT html issues matching in title/body: "race condition" 11, "infinite loop" 10, "undefined behavior" 9, "ambiguous" 68, "underspecified" 14, "contradict" 21. needs-tests 97. topic: event loop 52, topic: frames/navigables 92, topic: history 109.
  INF keyword counts are noisy lower bounds, not bug counts.
FACT tc39/ecma262: 1440 issues; label "spec bug" 80 total (15 open); "editorial change" 98. Labels include "completion records", "layering".
FACT WebAssembly/spec: 783 issues; label "bug" only 4 (labels sparse -> not usable as a rate).
FACT total issues: whatwg/dom 771, fetch 1025, url 463, streams 635.
INF no web spec tracks "spec is wrong" uniformly; label-based rates are unreliable. Kinds seen in the data below: type errors (wrong/missing value, wrong index, wrong arity), reference errors, inconsistencies between mechanisms (CSP vs HTML), algorithm not satisfying stated invariant (history), prose/formal drift.

## 2. found by mechanized/formal methods
- JSTAR (ASE 2021, KAIST) https://plrg.korea.ac.kr/assets/data/publication/ase21-park-jstar.pdf
  FACT abstract: finds "157 type-related specification bugs with 59.2% precision; 93 out" of them confirmed by TC39, over 864 ecma262 versions 2018-2021 (checkers: reference, arity, assertion, operand).
  FACT ESMeta (successor, integrated in ecma262/test262 CI) https://github.com/es-meta/esmeta ; tycheck command.
- JEST (ICSE 2021) https://arxiv.org/pdf/2102.07498 FACT: "it detected 44 engine bugs in four different engines and 27 specification bugs in ES11." (differential testing using spec-derived interpreter, not proof)
- ESMeta-to-Lean probe: see vlm42_esmeta/REPORT.md (not redone).
- Warblre (ICFP'24) https://arxiv.org/pdf/2403.11919 FACT: "we prove that JavaScript regex matching always terminates and is safe (no assertion failures); we identify subtle corner cases that led to mistakes in previous publications". Earlier models: "we found mistakes in both" (one incomplete). Translated "over 33 pages of pseudocode". Follow-up 2507.13091 (backtracking-tree semantics), 2603.26139 (complexity).
  INF no ecma262 errata reported in the paper's text I searched; result = spec is terminating+assert-safe (positive), bugs were in prior models. Could not verify absence of errata beyond grep.
- Wasm SpecTec (PLDI'24 https://dl.acm.org/doi/10.1145/3656440 ; adopted 2025-03-27 https://webassembly.org/news/2025-03-27-spectec/)
  FACT adoption post: "It is hard to avoid ambiguities, contradictions, oversights, and serious bugs in such an approach." and "While building SpecTec we discovered numerous bugs in the hand-crafted prose, and there are probably many more we didn't spot." (no count given)
  FACT (search summary of PLDI paper, not verified in full text): retrospective on past fixes: 3 type errors, 7 prose errors, 3 semantic errors (table.grow missing stack value; wrong memory index in memory.fill/init; wrong pop count on label exit) would have been prevented; 10 bugs in proposals (2 type, 2 prose, 4 semantics, 2 editorial).
  FACT P4-SpecTec (same method, arXiv 2608.00639): 24 bugs = 9 spec patches + 15 p4c bugs (via search summary).
- WebSpec (S&P'23) https://arxiv.org/abs/2201.01649 FACT: 10 invariants over 5 components; "two new logical flaws" (__Host- cookie prefix attack; "a new inconsistency between the inheritance rules for the Content Security Policy and a planned change in the HTML standard"), 3 earlier-known flaws in current platform, 5 in old versions. Follow-up USENIX Sec'24 Bernardo et al "Web Platform Threats" matches WPT traces to model.
  INF catches security-level interaction bugs, not algorithm-level ones; Coq model is hand-written, abstract.
- Brewster & Jeffrey, navigation history, arXiv 1608.05444 (2016) FACT abstract: "We show that the specification-aligned model does not satisfy this property, by exhibiting a series of counter-examples, which motivate four patches to the model... browsers are inconsistent in their implementation". Property: traverse(d) then traverse(d') = traverse(d+d'). Spec has since been rewritten (navigables); INF the old finding is for a retired spec text; whether new spec satisfies it is OPEN (I found no 2022+ formalization; did not search exhaustively).
- Implementers: Ladybird/Servo literal-implementation bugs: whatwg/html#12861,#12961,#12362,#6927 (see vlm48 d.md A6, not redone).
- JSCert/KJS/JaVerT: not re-examined (older, ES5 era, mostly found engine bugs/test262 issues; from memory, unverified).

## 3. parseable algorithmic specs
- ecma262: <emu-alg> in ecmarkup; ESMeta/JISET parse the structured English into IR (FACT per JSTAR abstract: "compiles each abstract algorithm written in a structured natural language to ... IRES"). SpecTec makes the Wasm spec itself the source (generates prose+LaTeX).
- WHATWG HTML/DOM/URL/Fetch/Streams: Bikeshed/Wattsi, numbered steps in `<ol>`, "Let x be", "If ... then", "Queue a task". INF same step-style but looser than ecma262 (no emu-alg type annotations, WebIDL types). I did not find a published full parser/IR for WHATWG step algorithms (searched only lightly). OPN this is the open gap and ESMeta-style frontend for WHATWG is the natural project.
- Tooling checks: webidl2, Bikeshed, ecmarkup lint structure/links only (INF, unverified here).

## summary of kinds by method
formal/type-check finds: type/arity/reference errors, invariant violations, prose-vs-semantics drift, cross-spec interactions. Implementers find: races/underspecification/ordering (event loop, navigation). INF concurrency bugs (event loop, navigation, streams) are least covered by prior formal work.
