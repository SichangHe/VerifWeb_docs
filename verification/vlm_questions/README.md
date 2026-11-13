# Nov 3 open questions: answers
(authored by agents unless marked 🧑)

Details, verbatim quotes and URLs are in the three files below; caveats are marked there.

- q1_verus_feedback.md: what Verus tells the agent per failed attempt
  - the meeting claim is partly wrong: errors name the failed requires/ensures/assert clause with source spans
  - the claim holds for timeouts ("rlimit exceeded"), unsplit big conjunctions (--expand-errors exists but has bugs), and counterexamples (an SMT model exists internally but is not exposed)
- q2_verus_scale.md: how much code Verus handles
  - "thousands of lines" is right: largest is Anvil, ~3.9K exec + ~24K proof lines; SOSP'24 total 6.1K exec / 31K proof
  - "half an hour" is too pessimistic: seconds to ~20 min, under 3 min per controller; 87% of functions verify in under 10 s
  - no evidence of more than 10K lines of executable code
- q3_liveness.md: why no agent liveness results on real systems
  - no causal source found; human liveness proofs are costly (IronFleet IronRSL liveness 7.9K lines, 115 min to check)
  - IronFleet confirms the timeout-without-feedback point
  - one LLM liveness paper, TLA-Verus (arXiv Oct 2026): TLA+ specs only, ~38% success on liveness
  - "entire lab" not identified; "used internally" has no evidence
