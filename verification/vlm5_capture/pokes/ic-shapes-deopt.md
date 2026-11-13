# Poke: inline caches / shape transitions; deopt reconstruction (new)
(authored by agents unless marked 🧑)
Method: one web search. No experiment was run.

- Fact: the search returned no formal-verification work on IC or hidden-class transitions. It returned only design papers: RIC (PLDI 2019), Hidden Inheritance (OOPSLA 2020), and Serrano CC 2019. Serrano states informal invariants: "objects' hidden class must be in sync with objects' prototype during their whole lifetimes".
- Recall, not checked this session: Barrière et al., POPL 2021 (CoreJIT) formalizes speculation and deopt in Coq. WRITEUP already cites it, so the deopt direction has an existing foundation.
- Inference: the IC/shape-transition invariant looks like an open, cheap Verus target. A shape tree plus transition plus IC lookup model is about 1 day of work. Serrano's invariants can serve as the spec. It is engine-relevant: type-confusion CVEs come from stale maps.
