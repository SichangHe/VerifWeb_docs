# vlm5 capture-recapture of research directions
(authored by agents unless marked 🧑)

## Method
- Six blind samplers (samples/S_*.md) listed 235 items: four Claude samplers with different lenses (browsersec, jsrt, pc, pl), one GPT and one Gemini.
- The items were merged into 75 clusters (clusters.md; source in scripts/clusters.py). Each cluster is tagged covered, partial or new against prior work (TARGETS.md, WRITEUP.md, vlm_runtime, vlm_questions).
- Estimates come from scripts/estimate.py.

## Estimate (estimate.md)
- Observed: 74 clusters from the six samplers, 75 including prior work.
- Chao1 is 81 (six samplers) and 82 (prior work as a seventh capture).
- The pairwise Chapman median is 67. That is below the observed count, which shows the samplers are correlated (shared prompt), so the pairwise estimate is biased low.
- Belief: the true total is 85 or more. Prior work covers 14 clusters and partly covers 15. 46 are new.

## Top new directions, ranked by promise (opinion)
1. Verus specs for Boa's ECMAScript builtins, derived from ESMeta's mechanized ECMA-262 and validated by test262. Hit by 6/6 + 4/6 samplers. Answers the "where does the spec come from" question. Poke: no prior art combining these.
2. Bug-fix diffs as mutants to measure the strength of agent-written browser specs. Hit by 4/6. Poke: the generic method is crowded (MutDafny, VeriContest), so the browser-bug angle is what remains.
3. Inline-cache / shape-transition invariants. Hit by 2/6. Poke: no formal work found; Serrano CC 2019 gives informal invariants. Cheap model.
4. Proof repair and spec drift across Servo/Boa commits. Hit by 6/6. Not poked.
5. Verified implementations of cookie jar, ORB and CSP decisions. Hit by 3/6. Poke: protocol models exist (Alloy, Quark, WIM); verified Rust implementations do not.
6. Parallel style/layout data-race freedom, IPC validation, postMessage/structured clone. Each hit by 3-4/6. Not poked.

## Pokes (pokes/)
- All four pokes are web searches only. No builds or experiments were run.
- Prior-art items marked "recall" are unchecked.
- Nothing was filed upstream and no one was contacted.
