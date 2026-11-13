Q3: Why no published LLM-agent results proving liveness of real distributed systems?
(authored by agents unless marked 🧑)

Verdict: Partly wrong premise. One LLM-agent liveness paper exists (Oct 2026), on TLA+ specs, not real systems. No source answers "why so few"; the explanations below are inference. Searches were limited (a few queries); absence claims are "not found", not "does not exist".

## 1. Human liveness proofs: expensive (FACT)

IronFleet (SOSP'15, Hawblitzel et al.) https://sigops.org/s/conferences/sosp/2015/current/2015-Monterey/250-hawblitzel-online.pdf
- "to our knowledge, IronFleet is the first system to mechanically verify liveness properties of a practical protocol"
- Effort: "real systems required approximately 3.7 person-years."
- Table (SLOC proof / minutes to verify): IronRSL Liveness 7869 / 115; IronRSL protocol 1202 / 4; IronRSL refinement 3379 / 26; IronKV Liveness 2093 / 23. (Liveness is the largest and slowest part of IronRSL's protocol layer.)
- "Verdi does not prove any liveness properties." (related-work section)

Anvil (OSDI'24, Sun, Xu et al., Verus, K8s controllers) https://www.usenix.org/publications/loginonline/anvil-building-formally-verified-kubernetes-controllers
- "we spent around two person-months on verifying ESR for the ZooKeeper controller"; other two "around two person-weeks" (reused strategy+invariants).
- Proof SLOC (Table 1): ZooKeeper 8,352 proof vs 1,134 verified impl; RabbitMQ 7,228 vs 1,598; FluentBit 8,395 vs 1,208. (About 5-7x proof:impl.)
- Fairness: "if A remains enabled (A can possibly occur), then A eventually occurs; this condition is referred to as weak fairness"
- Not checked by me: Anvil paper itself (usenix.org/system/files/osdi24-sun-xudong.pdf).

Ivy / liveness-to-safety (Padon et al., POPL'18; Temporal Prophecy arXiv 2106.00966): reduces liveness to safety so safety invariant tools apply. Only seen via a search summary, no verbatim quote fetched. UNVERIFIED.
Kondo (OSDI'24, Zhang et al.): search summary says it targets safety proofs only. UNVERIFIED, no quote.
TLAPS liveness; Dafny/Verus temporal libraries: IronFleet and Anvil are the two temporal-logic-in-Dafny/Verus instances found. No TLAPS liveness source fetched.

## 2. LLM/agent results

TLA-Verus (arXiv 2610.14923, Strelbytska, Szilagyi, Meszaros, Huszar; Reasonable + Cambridge) https://arxiv.org/html/2610.14923v1
- Abstract: "TLC and TLAPS cannot provide satisfactory proofs of arbitrary temporal logic properties"; pipeline produces "fully machine checkable proofs of both safety and liveness properties". Builds on Anvil's temporal library.
- "Liveness is the hardest type, and not because these tasks are the longest."
- "Liveness is where strong models break first". Liveness solved 58/110 vs 73-76 for other three types (eval set).
- Scale: "the algorithmic pipeline found proofs for 3,094 out of 5,160." Liveness 304 proven of 809 well-posed (about 37.6%; the combination of Tables 8+9 is the fetcher's calculation, not the authors').
- Feedback: "Otherwise the verifier's error output is fed back for revision"; Verus gives "no counterexample." Budget: "up to V=10 verification attempts per sample"; "Every model below 20% uses all ten verification attempts on nearly every sample".
- Limitation: "inability to reliably differentiate between false statements and true statements for which finding a proof is too difficult". Refinement to implementation "is left for future work."
- Scope: specs from TLA+ corpora (not a running real system). Paper reports no wall-clock timeouts.
- Caveat: I read via a summarizing fetcher; quotes are as returned, not checked against the PDF.

Other (titles/abstract metadata only; contents not verified):
- IC3+LLM inductive invariants for distributed protocols, arXiv 2605.24619 (Cao ... Ma, Nanjing). Keywords: "distributed protocols, inductive invariants, TLA+, model checking, large language models". Liveness coverage: unknown; inference: safety.
- VeruSAGE, arXiv 2512.18436 (Yang, Neamtu, Hawblitzel, Lorch, Lu): agent verification of Verus systems; a search summary says it includes an Anvil controller task. Result numbers not read.
- ExVerus arXiv 2603.25810: search summary says an Anvil-controller proof failure needed an inductive invariant. UNVERIFIED.
- TraceFix arXiv 2605.07935: per search summary deliberately skips liveness. UNVERIFIED.

## 3. Why liveness is harder (sources' own words)

- IronFleet: "Liveness properties are much harder to verify than safety properties." and "Liveness, in contrast, requires reasoning about infinite series of system states. Such reasoning creates challenges for automated theorem provers (§2.4), often causing the prover to time out rather than return a successful verification or a useful error message."
  -> Directly supports the meeting's "timeouts / no feedback" point. Primary source.
- IronFleet also: protocol "must satisfy fairness properties"; assumptions like fair network are part of the theorem.
- TLA-Verus: fairness assumptions are hard: "determining when an assumption is a fair addition, similarly remains a challenge".
- Anvil ;login: liveness bugs "notoriously hard to detect"; testing "cannot decide whether the controller will never realize the desired state or is just running slow."

## 4. Labs (FACT as found; "entire lab" claim NOT verified)
- Anvil: Tianyin Xu's group (UIUC; tianyin.github.io hosts the paper) with VMware Research code (github.com/vmware-research/verifiable-controllers). Affiliations from search summaries, not checked.
- IronFleet: Microsoft Research (Hawblitzel, Lorch); VeruSAGE shares Hawblitzel/Lorch, plus Shan Lu.
- Ivy: Padon, Sagiv, McMillan et al.
- TLA-Verus: Reasonable (company).
- I could not determine which lab the meeting means by "an entire lab just dedicated to distributed liveness".

## 5. Answer to "why haven't we seen it?" (INFERENCE, mixed with meeting hypotheses)
- Supported by sources: it IS hard (IronFleet 3.7 py, 7.9k liveness proof lines; Anvil 2 person-months for one controller), and provers time out without useful errors (IronFleet quote). LLM agents need verifier feedback to iterate; silent timeouts remove it. TLA-Verus shows liveness is the weakest category even with Verus feedback.
- "Maybe they're using it internally": no source found either way. Unfalsifiable from public data.
- Missing-signal caveat: first public LLM liveness paper appears Oct 2026, i.e. 3 weeks before the meeting; the field is new, not necessarily stalled. Anvil-derived benchmarks (VeruSAGE, RVBench) are 2025-26.
- No source says "LLM liveness proofs on real systems fail because X". That causal claim is unestablished.
