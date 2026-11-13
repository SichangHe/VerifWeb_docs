(authored by agents unless marked 🧑)

My opinion: the promising thesis is not “solve prompt injection.” It is “restore browser security principals across the agent path.” The browser already knows about origins, SiteInstances, renderer processes, frames, storage, and the compositor; current agents largely collapse those distinctions back into one powerful reasoning context.

“Novel” below means I did not find the same mechanism in the literature or public Chrome design as of November 6, 2026. That is not proof nobody is working on it.

### landscape constraints

Several obvious versions of this idea are already occupied.

CaMeL makes control flow independent of untrusted data: its authors say “untrusted data retrieved by the LLM can never impact the program flow.” [MIT CSAIL CSS Group](https://css.csail.mit.edu/6.5660/2026/readings/camel.pdf?utm_source=chatgpt.com) FIDES is already formal IFC for agents: Costa et al. say it “tracks confidentiality and integrity labels, deterministically enforces security policies.” [arXiv](https://arxiv.org/abs/2505.23643?utm_source=chatgpt.com) Progent already offers a “domain-specific language for flexibly expressing privilege control policies.” [arXiv](https://arxiv.org/abs/2504.11703?utm_source=chatgpt.com)

AgentDojo and WASP mainly occupy evaluation. AgentDojo calls itself “an evaluation framework for agents that execute tools over untrusted data.” [NeurIPS Proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html?utm_source=chatgpt.com) WASP is specifically an “end-to-end evaluation of Web Agent Security against Prompt Injection attacks.” [NeurIPS Proceedings](https://proceedings.nips.cc/paper_files/paper/2025/hash/1c9818387f5dd0a0bc151214660f059d-Abstract-Datasets_and_Benchmarks_Track.html?utm_source=chatgpt.com)

Browser-specific isolation is no longer untouched either. Chrome says Agent Origin Sets “limit[] the agent to only access data from origins that are related to the task at hand.” [blog.google](https://blog.google/security/architecting-security-for-agentic/?hl=en&utm_source=chatgpt.com) SOPGuard observes that “the agent itself can serve as an automated data-flow channel” and tracks origin labels across that channel. [arXiv](https://arxiv.org/html/2606.14027) The 2026 IEEE S&P process-isolation paper found architectures where “privileged processes manage user prompts and agent operations, while untrusted renderer processes are isolated.” [WSP Lab](https://wsp-lab.github.io/papers/lee-sp26.pdf)

There are two particularly important recent landmines. Prismata already does fine-grained web-page confinement: “dynamic trust derivation produces permission labels for page content”; however, “Prismata operates in the textual input modality.” [Hugging Face+1](https://huggingface.co/buckets/huggingchat/papers-content/tree/2607/2607.08147.md) And Baya, posted November 4, 2026, now occupies compile-before-browsing: it “compiles the user's request into an executable Python program that calls a Trusted Website API.” [arXiv](https://arxiv.org/abs/2611.06039?utm_source=chatgpt.com)

That leaves the following three directions.

---

## 1. make the agent obey Site Isolation: one reasoning principal per origin

Opinion: this is the strongest direction.

**thesis.** A single LLM context spanning mutually distrusting origins is conceptually the same mistake that Site Isolation was designed to avoid for JavaScript. Make the agent itself origin-compartmentalized.

Concretely, associate an agent state/context with each SiteInstance or origin:

agent_state[origin]

An origin-local agent may see that origin's renderer output and propose actions only against that origin. It cannot directly see another origin's state, conversation history, or observations. Cross-origin work happens only through a small browser-resident broker, analogous to postMessage, carrying explicit typed values and provenance.

A useful formal property is noninterference modulo explicit declassification:

> changing attacker-controlled state at origin A cannot change actions at origin B unless the broker emitted an explicitly authorized A→B message

The monitor could be small Rust/Verus code. You are not verifying Chromium or the LLM; you prove that every path from an origin-local model to another origin's actuator crosses the checked broker.

**why this is different.** CaMeL/FIDES/Progent retain one logical agent and control its flows/tools. This proposal instead turns web origins into actual principals of the agent architecture. AgentDojo/WASP do not provide the mechanism.

Chrome Origin Sets are close but materially different. Inference from Google's public description: they gate which origins the planning agent may read or write; the design does not describe separate planner state/context for each origin. SOPGuard similarly labels cross-origin values rather than isolating the cognition that processes them. Prismata confines page elements within an agent observation.

The IEEE S&P process-isolation work is the nearest collision, but it primarily studies the boundary between untrusted renderers and the privileged agent/background process. This proposal recursively applies the browser's isolation model *inside the privileged agent itself*: mutually distrusting origins should not converge into one privileged cognition process.

**first two weeks.** Do not touch Chromium initially.

Build a BrowserGym/Playwright prototype with:

1. separate LLM conversation history per origin
2. an origin-local action API
3. a 200–500 line Rust broker
4. three explicit transfer operations, such as copy_text(A,B), compare(A,B), and user_authorized_transfer(A,B,value)
5. a small Verus proof that origin A cannot directly produce an actuator command for B

Then take perhaps 20 cross-origin cases from SOPBench plus a few WASP-style injections. Compare ordinary shared-context ReAct against compartmentalized execution. The interesting result is not merely lower attack success; demonstrate an attack that succeeds against an arbitrarily compromised origin-local LLM but is mechanically impossible against the broker.

**biggest risk.** Useful browsing is inherently cross-origin. “Read this article and email a summary” genuinely requires A→B influence. If every real task requires a giant declassification hole, the architecture degenerates into FIDES with origins attached.

That is also the intellectually interesting question: what is the smallest cross-origin communication abstraction that preserves useful web tasks without recreating an unrestricted shared LLM context?

A dissertation could combine web measurement—measuring required cross-origin information flows on real tasks—with a verified browser mechanism.

---

## 2. an agent-specific CSP for same-origin distrust

Opinion: highest conceptual upside, but highest deployment risk.

**thesis.** The web's origin principal is too coarse for agents.

A GitHub issue, Reddit comment, product review, advertisement, and the site's trusted UI can all become text inside one agent context. Some are even same-origin. Traditional SOP therefore cannot distinguish “GitHub's application UI” from “attacker-controlled issue text.”

Introduce a browser-enforced, site-declared integrity policy for agents—working name: agent-facing CSP.

For example, a server could declaratively mark regions as roughly:

- trusted control/interface
- readable data
- untrusted user content
- third-party content
- agent-actionable elements

The important part is not those exact labels. The security rule is that content cannot promote its own authority. A user comment marked “data” may be summarized, but text inside it can never cause the browser to widen the agent's action capabilities.

The policy must be rooted in something attacker content cannot manufacture: an HTTP response header, CSP-style nonce, iframe boundary, or browser-issued token—not arbitrary HTML attributes.

A Verus-friendly invariant is monotonic integrity:

effective_capability(child) <= effective_capability(parent/policy)

unless an authenticated policy declaration explicitly raises it.

**why this is different.** CaMeL/FIDES/Progent reason about generic data or tools; they do not obtain principals from the web application's own structure.

Chrome Origin Sets and SOPGuard work primarily at origin granularity. They cannot distinguish trusted and attacker-generated material sharing an origin.

Prismata is the important competitor. It already infers developer/user/hosted-party/external regions and assigns capabilities. The differentiator must therefore be strong: do **not** build another better DOM classifier. Instead ask whether websites can state security intent explicitly so that the browser provides a deterministic guarantee rather than inferring ownership with an LLM.

This is analogous to the difference between an XSS classifier and CSP/Trusted Types.

**first two weeks.** Define a tiny formal policy language and build three miniature sites:

1. GitHub-like issue tracker
2. Reddit-like discussion page
3. marketplace with seller descriptions/reviews

Implement the enforcement layer in Playwright or a Chromium patch. Give trusted UI and UGC different policy capabilities. Put arbitrarily strong prompt injections in the UGC.

The demo should be crisp: even if the agent follows every malicious instruction it reads, it cannot turn a read-only review into authority to click “delete account,” navigate cross-site, or submit another form.

Then prove the capability monotonicity property for the enforcement algorithm in Verus.

**biggest risk.** Adoption.

A mechanism requiring every website to add new headers/markup may make a nice security model but a weak systems paper. You probably need an incremental deployment story: derive most boundaries from existing iframes, sandbox attributes, CSP, shadow DOM/component ownership, or templating structure; allow explicit declarations only where existing web metadata is insufficient.

Also, this does not solve malicious first-party sites or classical XSS. That scope should be explicit.

---

## 3. preserve origin provenance through the compositor: Site Isolation for screenshots

Opinion: this is the most underexplored technically, and probably the best backup to #1.

**thesis.** Modern multimodal agents destroy browser provenance at exactly the wrong place: the browser carefully isolates frames/renderers, then flattens their output into one screenshot and hands all pixels to one VLM.

Instead, make the browser's visual observation API principal-preserving.

The compositor/browser already has structural knowledge about frames and rendering surfaces. Export observations as origin-labelled visual planes or frame surfaces rather than an undifferentiated screenshot. A model processing pixels from origin A receives authority only to propose actions against A. Cross-origin visual composition requires an explicit broker operation.

The guarantee should avoid claiming anything about whether a VLM “understands” provenance. Make provenance affect *what data enters which model invocation and which actuator that invocation can reach*.

For example:

visual_context(origin A) -> VLM_A -> actions only on A

rather than:

flatten(all origins) -> VLM -> actions anywhere

A trusted coordinator can request typed results from these isolated visual workers when cross-origin comparison is necessary.

This directly extends Site Isolation from JS heaps to AI perception.

**why this is different.** Generic model guards are already crowded. WebInject and related work attack screenshot-based agents; WebInject describes agents “generating actions based on screenshots of the webpages.” [ACL Anthology](https://aclanthology.org/2025.emnlp-main.104/?utm_source=chatgpt.com) Brave demonstrated malicious instructions in screenshots being “processed as commands rather than (untrusted) content.” [Brave](https://brave.com/blog/unseeable-prompt-injections/?utm_source=chatgpt.com)

But those are attacks/model defenses. Prismata's current mechanism explicitly stops at textual input. Chrome's Origin Sets can exclude irrelevant iframe origins, but its public description is an origin-access policy, not a compositor-to-VLM provenance abstraction.

The core novelty would therefore be browser architecture, not another multimodal prompt-injection detector.

**first two weeks.** Use CDP/Playwright, not the Chromium compositor initially.

Recover the frame tree, render/crop each frame separately, attach its origin, and give each frame to a separate model invocation whose output is constrained to elements within that frame/origin. Reproduce:

1. a malicious cross-origin iframe injection
2. a benign page combining first- and third-party frames
3. a visual-prompt-injection case

Then compare ordinary flattened screenshots against origin-separated observations.

The tiny verified component maps:

frame -> origin -> observation capability -> allowed action targets

Prove that an observation carrying only origin A pixels cannot generate a command delivered to B through this interface.

If the prototype works, the real systems contribution becomes moving the primitive down into Chromium's renderer/compositor boundary.

**biggest risk.** A pixel does not always have a clean security principal.

A first-party renderer can display same-origin UGC, cross-origin images, canvas content, CSS overlays, or text copied from elsewhere. Frame provenance solves cross-frame attacks, not same-origin semantic distrust. That is why this direction complements #2 rather than subsuming it.

The other risk is utility: VLMs may rely on whole-page visual context. You need to measure how much performance is lost when visual context follows security boundaries.

---

## which areas I would avoid

Fact: several subareas are now crowded enough that I would not make them the thesis unless there is a sharply different systems primitive.

**Very crowded:** prompt-injection classifiers/guard models, attack-generation techniques, and new benchmark suites. Recent examples include WARD, WebAgentGuard, BrowseSafe++, WebInject/VPI-style work, AgentDojo, and WASP. BrowseSafe++ even reports adapted attacks reaching “up to 95.41% success.” [arXiv](https://arxiv.org/abs/2610.17457?utm_source=chatgpt.com)

**Crowded:** generic deterministic policy enforcement around an agent—capabilities, IFC, tool-call reference monitors, preplanning/compile-then-execute. CaMeL, FIDES, Progent, and now Baya occupy much of that design space.

**Rapidly becoming crowded:** simply “bring SOP to agents” or “restrict which origins the agent accesses.” Chrome Origin Sets, the Roesner/Kohlbrenner study, and SOPGuard are already there.

**Not empty, but viable:** process isolation for browser agents. “Site Isolation is Dead” means another paper merely discovering IPC bugs is less special. A new security abstraction built *from* Site Isolation could still be strong.

**My inference:** the least occupied intersections are (a) making origin/process boundaries constrain *agent cognition/state*, (b) browser-enforced sub-origin integrity for UGC, and (c) carrying browser provenance into multimodal perception.

### recommendation

Opinion: pursue **#1 first**. It has the cleanest thesis sentence, makes essential use of the web rather than merely applying PL to an agent, naturally combines measurement with Verus, and gives a model-independent security theorem.

The pitch to the advisors would be roughly:

> browsers stopped mutually distrusting websites from sharing a process; agentic browsers put them back together inside one LLM context. can we extend Site Isolation to the agent itself, with a verified cross-origin broker, while retaining enough cross-site functionality to be useful?

That feels substantially more distinctive than “another prompt-injection defense.”
