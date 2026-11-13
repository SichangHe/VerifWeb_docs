# Has anyone announced an ECMA-262 -> Rocq/Lean/Isabelle backend (like SpecTec)?
(authored by agents unless marked 🧑)

Short answer: No public announcement or release found (as of 2026-11-10). Absence is an inference from limited search, not proof.

## Facts (with quotes)

1. EPFL (Warblre authors) say ESMeta has no proof-assistant backend and call building one future work. (fact, 2024)
   Quote: "Unfortunately, it also does not yet support generation of definitions suitable for use in an interactive theorem prover such as Coq. To be able to rebuild our work on top of ESMeta, we would need to extend the JISET intermediate representation and translator to work with the regex specification style, and to add a translator from it to Coq; this could constitute interesting future work"
   Source: De Santo, Barriere, Pit-Claudel, "A Coq Mechanization of JavaScript Regular Expression Semantics", ICFP 2024, https://arxiv.org/abs/2403.11919 (in paper_collection).
   Same paper: "Instead of manually translating ECMAScript pseudocode, the ESMeta project uses JISET, an automatic translator, to transpile ECMAScript pseudocode into a custom intermediate representation" and JISET "does not support the regex chapter".

2. EPFL's follow-ups stayed manual/hand-written Rocq, not generated. (fact; the inference is that no generator existed by 2026)
   - Linden, POPL 2026, https://arxiv.org/abs/2507.13091 (in paper_collection): "Warblre [...], an existing line-by-line embedding of the ECMAScript regex specification into Rocq". The text contains no mention of ESMeta (grep: 0 hits).
   - Deng, Barriere, Pit-Claudel, "On the computational complexity of JavaScript regex matching, in Rocq", https://arxiv.org/abs/2603.26139. Builds on Linden/Warblre; 0 ESMeta hits. (Not saved to collection; I did not rely on its content beyond this.)
   - Warblre repo: https://github.com/LindenRegex/Warblre (not checked in detail).

3. ESMeta repo and org show no such backend. (fact)
   - github.com/es-meta org repos (GitHub API): esmeta, esmeta-debugger-client, ecma-visualizer, es-meta.github.io, ecma-visualizer-resources, snippets, logos, docs, unicode-gen. None is a proof-assistant exporter.
   - GitHub issue search in repo es-meta/esmeta for "coq", "rocq", "lean", "isabelle", "proof assistant": total_count 0 each. (Issue search only; code search needs auth, so not done. Local clone README grep also found nothing, but the grep command errored on a zsh glob, so treat that as unverified.)
   - Web search surfaced the README listing only extract/compile/tycheck/gen-poly/fuzz/inject-style commands.

4. KAIST/Korea Univ (Ryu, Park) 2025-2026 output is on testing, typing, polyfills, visualization, not proof export. (fact from search listings)
   - RPLS 2025 talk "Trusted JavaScript Language Environments with ESMeta" (Park), https://pldi25.sigplan.org/details/rpls-2025-papers/5/Trusted-JavaScript-Language-Environments-with-ESMeta ; same session as Ryu's SpecTec talk. Slides grep (https://plrg.korea.ac.kr/assets/data/slides/2025/rpls25-esmeta.pdf, plss25-esmeta.pdf) for coq/rocq/lean/isabelle: no hits (pdftotext).
   - Search listings: FSE 2025 demo "JSSpecVis"; ASE 2026 "MiniPoly: Automatic Extraction of Efficient JavaScript Polyfill from Language Specification"; TOSEM 2026 "Selective Feature-Sensitive Coverage for Conformance Testing of Programming Languages" (https://doi.org/10.1145/3808231). I did not open these.
   - Only forward-looking hint, about Rust, not ECMA-262: "Applying the ESMeta approach to Rust can help efficiently generate machine-checkable proof sketches, especially with mechanized semantics extracted from mechanized specifications." Ryu & Park, "JavaScript Language Design and Implementation in Tandem", CACM 2024, https://plrg.korea.ac.kr/assets/data/publication/cacm24-ryu-esmeta.pdf (in paper_collection). This is a vision sentence, not an announcement.

5. Other related work (fact unless marked).
   - JISET (ASE 2020), the translator from ECMA-262 prose to IR (in paper_collection).
   - JSCert (ES5, Coq, hand-written) is cited by Warblre as the earlier mechanization; Warblre says combining JSCert with its regex work is a direction. No JSCert successor generated from ES2015+ spec found.
   - Lean regex work by Zhuchko et al. is cited in Warblre/search summaries; regex only, manual. Not fetched by me.
   - Wasm SpecTec (the analogy): https://arxiv.org/abs/2311.07223. Not re-read here.

## Inferences
- Inference: as of Warblre (2024), EPFL regarded an IR-to-Coq translator on ESMeta as unbuilt; nothing since shows it was built by either group.
- Inference: the closest "analogous" thing is the Warblre/Linden hand-written Rocq line-by-line embedding of ECMA-262 section 22.2, not a generator.
- Gap: I did not use Google Scholar, arXiv listing search, or Lean Zulip/Rocq discourse, and web search is US-only and summary-based. A private or unannounced effort is possible. Answer is "no found", not "none exists".

## Papers saved
All relied-on papers already present in /hdd1/sichanghe/paper_collection (Warblre ICFP 2024, Linden POPL 2026, JISET ASE 2020, CACM 2024). Scratch downloads (incl. 2603.26139, slides) in lit/dl/, not added to collection; nothing git-added.
