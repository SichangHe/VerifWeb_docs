(authored by agents unless marked 🧑)

**My recommendation:** lead with archive rewrite verification, offer browser request authorization as the second option, and present process sharing as a higher-risk third option. The first has the strongest group-specific advantage; the second has a smaller proof target; the third addresses your original performance question.

Evidence below comes from your supplied reviews and saved source captures. Live fetching failed, so novelty remains provisional. Project designs, rankings, and durations are my judgments. Durations assume one PhD student with regular verification guidance.

1. **Certifying JavaScript rewrites in web archives**

**Problem + why now:** archives rewrite JavaScript to replay old pages, and the group’s recent FidEx paper demonstrates persistent failures: its fixes “reduced the fraction of archived pages which violate fidelity from 15% to 9%.” — [Zhu, Sun, and Madhyastha, NSDI 2026](https://www.usenix.org/conference/nsdi26/presentation/zhu-jingyuan).

**What to verify.** Build a checker for a restricted family of archive rewrites, initially URL construction and location reads. An illustrative requirement: a script requesting a particular URL should request its designated archived counterpart, without changing the request’s method, body, or surrounding computation.

Prove this statement: **if the checker accepts a rewrite and its stated runtime conditions hold, the original and rewritten fragments have equivalent results and effects under the archive’s URL mapping.** Exceptions and permitted differences must be specified too.

The checker is proved sound once. It examines each rewrite; the runtime checks its conditions immediately before execution. For example, an operand must be a primitive string rather than an object whose conversion runs arbitrary JavaScript. Unsupported behavior gets no certificate; ordinary replay can continue explicitly uncertified.

This certifies selected fragments, not whole-page fidelity. Missing resources, rendering, and unsupported JavaScript remain outside the guarantee. Parsing, browser execution, and the adequacy of the formal JavaScript model are explicit assumptions.

**Differentiator versus prior work.** FidEx works by “tracking and comparing the execution of scripts between when a page is crawled and when its copy is loaded.” The proposed checker would certify supported transformations without requiring that paired execution. Translation validation itself is established: see Kwon et al., [“Translation validation for JIT compiler in the V8 JavaScript engine”](https://dl.acm.org/doi/abs/10.1145/3597503.3639189).

The novelty hypothesis is therefore **archive-specific equivalence, runtime conditions that make checking tractable, and substantial coverage of actual archive failures**. A solver demonstration on synthetic string substitutions would be insufficient.

**Fit to this group.** Harsha’s archive work supplies failures, infrastructure, and a baseline. Your browser experience helps identify meaningful semantics. Arvin can help align the theorem with the implementation; Ramesh can help evaluate system cost and generality. This most directly exploits the advisors’ “lots of data” and “lots of experience.”

**Bite-sized first paper: approximately 4–6 months.**

- **Build:** a checker for one recurring rewrite family, integrated with the existing replay infrastructure
- **Prove:** acceptance implies equivalence for that family, conditional on explicitly checked runtime conditions; use Lean or Rocq rather than inventing verification tooling
- **Evaluate:** historical faulty and corrected rewrites, held-out pages, certification coverage, false rejection, and replay overhead
- **First two weeks:** classify available FidEx failures and identify whether several share a small, useful semantic model

**Biggest risk; what failure teaches.** We do not know how many failures fit this restricted scope. Getters, dynamic dispatch, and browser state may defeat local checking. Stop if useful coverage requires modeling most of JavaScript or the browser. That failure would identify whether verification should target shared replay functions instead of individual rewrites; it would not automatically constitute a paper.

2. **Proving that credentialed browser requests have current authorization**

**Problem + why now:** authorization can become stale across redirects, navigation, pending asynchronous work, and session reuse; a contemporary example is Lightpanda’s advisory, “Credential headers leak across cross-origin redirects.” — [Lightpanda security advisory](https://github.com/lightpanda-io/browser/security/advisories/GHSA-mcw6-8p83-pm3h).

**What to verify.** Build a small request broker that holds API credentials and enforces permissions granted by a trusted operator or application. The browsing agent cannot expand those permissions. Each permission identifies a session, document generation, destination origin, and permitted operation.

Illustrative failure: a document queues an authenticated request, navigation revokes its permission, and the pending request subsequently runs. A destination allowlist still permits the server; the proposed broker rejects the expired permission.

Prove that:

- Every credentialed dispatch has a current permission for its session, document, destination, and operation
- Redirects require a new destination decision
- Revocation prevents subsequent dispatches
- Reusing a session cannot revive its predecessor’s permissions or credentials

Define dispatch precisely: committing a request to the transport queue. Permission checking and commitment are serialized with revocation. Bytes already queued or transmitted cannot be recalled.

Initially protect broker-held authorization headers, not all browser cookies or passwords entered into page-visible fields. Keep renderers in separate processes and enforce their network path through the broker. Proving its decision function alone would not establish that every request uses it.

**Differentiator versus prior work.** A verified browser core is not new. [Quark, USENIX Security 2012](https://www.usenix.org/conference/usenixsecurity12/technical-sessions/presentation/jang), already claims “tab non-interference, cookie integrity and confidentiality, and address bar integrity.” The supplied review also describes [SPIDES](https://arxiv.org/abs/2610.24277) as browser-agent information-flow control using “site-supplied labels.”

The candidate distinction is **an executable proof of authorization lifetime across browser events and actual dispatch**, rather than merely a policy over agent commands. Whether existing systems already cover this distinction needs investigation. “A verified security layer for agents” is too broad to establish novelty.

**Fit to this group.** This combines browser behavior, realistic workflows, and a compact concurrent state machine. Arvin’s ZENITH experience is relevant to reasoning about state transitions; your and the advisors’ web experience helps determine whether the problematic sequences matter in practice. Recent LLM work supplies context, but does not by itself prove demand.

**Bite-sized first paper: approximately 4–6 months.**

- **Build:** a Verus-verified Rust broker connected to Chromium, supporting navigation, fetch/XHR, and redirects; disable unsupported network paths in the experimental configuration
- **Prove:** permission transitions, credential selection, revocation ordering, and session reset in executable broker code
- **Evaluate:** historical redirect failures, deliberately raced navigation/revocation/reset cases, realistic task completion, and latency
- **Baselines:** a static proxy allowlist and authorization checked only when the agent invokes a tool

Document the browser adapter and OS enforcement assumptions separately.

**Biggest risk; what failure teaches.** A conventional proxy plus established capability techniques may provide almost all the benefit. The first experiment should demonstrate a useful browser-state-dependent restriction that destination filtering misses. If it cannot, this is probably engineering rather than a research contribution. If it can, it identifies exactly what browser state an external enforcement system needs.

3. **Checking JIT code before allowing tenants to share a process**

**Problem + why now:** process sharing saves resources, but generated machine code threatens its isolation boundary; Cloudflare’s hardening discussion assumes attackers cannot execute arbitrary machine code because “If they did, they could disable memory protection keys.” — [Cloudflare security hardening](https://blog.cloudflare.com/safe-in-the-sandbox-security-hardening-for-cloudflare-workers/).

**What to verify.** Before executing a tenant’s generated machine code, check that it accesses only its assigned memory and uses permitted control-flow targets and host interfaces.

Prove two things:

1. Accepted code obeys these confinement rules
2. Code is checked before execution, cannot change while executable, and loses its authority when its tenant session ends

This targets erroneous or attacker-controlled JIT output. **It does not establish whole-engine isolation by itself.** The interpreter, garbage collector, native builtins, and host bindings also require confinement. Reuse an existing whole-engine sandbox for those paths; investigate whether a verified checker closes a remaining trust assumption about generated code.

V8 isolates and pointer compression alone do not discharge these obligations. Architectural memory confinement also does not prove protection against Spectre.

**Differentiator versus prior work.** Competition is substantial:

- [Icarus, SOSP 2024](https://dl.acm.org/doi/abs/10.1145/3694715.3695949), develops JIT components “automatically, formally verified to be safe”
- [Mohabi, OSDI 2026](https://www.usenix.org/conference/osdi26/presentation/sharma), confines engines “to ensure JavaScript engine bugs cannot affect the rest of the browser”
- [LFI’s verifier proof](https://arxiv.org/abs/2508.15898) establishes that accepted programs “never read or write to memory outside of a designated sandbox region”

Thus, checking machine code or selecting a region per tenant is insufficient novelty. The hypothesis is **support for a real JS JIT’s changing code, host transitions, and tenant reuse, with an end-to-end resource benefit**. Full-text and artifact comparison could eliminate this project.

**Fit to this group.** It directly addresses your systems question and uses your browser background. Real web workloads could improve the evaluation. The fit is weaker than the other options because machine-code verification requires specialized expertise, and experienced groups already occupy this area.

**Bite-sized first paper: approximately 6–9 months, conditional on a four-week feasibility study.**

- **Build:** support for one engine, one instruction set, one JIT tier, and a restricted edge-style host API
- **Prove:** checker soundness and code installation/retirement rules, reusing existing verifier infrastructure
- **Evaluate:** adversarial code, realistic JavaScript, unsupported-code fallback, compilation latency, throughput, and memory against separate processes
- **Feasibility gate:** establish that existing machinery confines native engine execution and that checking the selected JIT tier does not require trusting its output

Measure how many comparable jobs a machine completes within a memory budget. State security differences explicitly rather than treating weaker isolation as a pure performance improvement.

**Biggest risk; what failure teaches.** Native execution or speculative reads may dominate the security problem; checking and fallback may erase the savings. Failure would locate the actual cost and trust boundary. Your “300 megabytes” observation motivates measurement, but that memory is not necessarily removable process overhead. An unfinished checker is not a negative-results paper.

Your open questions:

> “It needs to be something special, something ideally to do with the web, not just PL”

Make web behavior essential to both the theorem and evaluation. Archive rewriting depends on historical resources and browser-visible URLs. Request authorization depends on origins, redirects, navigation, and sessions. The JIT project is more general runtime research unless browser integration substantially determines its design. I would favor the first two for this preference. The group’s differentiator is access to real failures and deployment knowledge that determines what is worth proving.

> “maybe we should do something about security with the agents using the browsers. Although that is also somewhat crowded”

Yes, with a narrow browser-enforced guarantee. Assume page content can completely mislead the agent, then identify operations the browser must still prevent. Project 2 follows that approach. Its policy must come from an authority the agent cannot override. Quark and SPIDES make generic isolation and information-flow claims difficult; permission lifetime is a distinction to investigate. Correct authorization does not establish that the agent understands the user or prevent every prompt-injection consequence.

> “process isolation across browser tabs ... maybe that would be interesting for Cloudflare workers or something like that to share processes”

Yes, as an isolation-strength or resource-cost project. Cloudflare already says it “can run many isolates within a single process” in its [security model](https://developers.cloudflare.com/workers/reference/security-model/), so sharing itself is established. An edge runtime offers a smaller interface than a full browser. The research contribution must specify the additional attacker capability tolerated or the cost saved at a stated security target. You need not verify all JavaScript semantics, but you must account for the complete isolation boundary.

> “We could argue for agent infrastructure ... efficient browsers ... However, that just are used for light panda”

I interpret this as asking whether Lightpanda already covers the efficient-agent-browser story. Efficiency is a motivation, not yet a contribution. Project 2 could provide a precise authorization guarantee in an existing browser; project 3 could provide stronger isolation per unit of memory. Compare task completion, cost, and security assumptions. If existing systems already satisfy the actual requirement cheaply enough, that weakens the performance project. A proof of unrelated policy code would not repair that argument.

> “I thought we are trying to find things we want to formally verify, right?”

Yes: an archive-rewrite checker, a credentialed-request broker, and a JIT-code checker with its code-management protocol. Each requires a machine-checked theorem about executable code, or a proved connection from the implementation to its mathematical model. Measurements select worthwhile targets and demonstrate usefulness; they do not replace proofs. Runtime verification still needs a general soundness theorem for the checker, even though each invocation examines one concrete state.

> “Not sure ... how we turn them into research projects that my advisors would like.”

Bring one real failure, one precise guarantee, the closest existing system, and a short experiment that could reject each idea. My choice would be a two-week archive pilot: classify the existing failures, identify one recurring rewrite family, and write its proposed equivalence condition. Continue only if that condition covers useful real cases and existing work does not already provide it. This gives the advisors something concrete to assess before committing to a browser implementation or a large proof.

The fuller draft is saved in [PITCHES.md](/hdd1/sichangheagent/vl_meeting_work/out/vlm15_pitch/PITCHES.md).