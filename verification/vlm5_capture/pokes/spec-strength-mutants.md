# Poke: spec strength via implementation mutants (cluster hit by 4/6 samplers, new)
(authored by agents unless marked 🧑)
Method: one web search. No experiment was run.

Fact: this direction is crowded. Prior art found:
- MutDafny (arXiv 2511.15403): "Specifications killed 79% of mutants on average" across 112,810 mutants.
- Lahiri 2024 (arXiv 2406.09757): symbolic testing of specs using output mutants. It names Verus as a target.
- VeriContest (arXiv 2605.08553): uses cargo-mutants and LLM mutants on Verus postconditions. "identifies 60 incomplete postconditions".
- PostcondBench (arXiv 2605.03356); LeetProof (arXiv 2604.16584).

Inference: the generic method is taken. What remains open is the browser instantiation: mutants drawn from real browser bug-fix diffs (Servo/Boa history), checked against agent specs. This merges with the "bug reports -> properties" cluster.
