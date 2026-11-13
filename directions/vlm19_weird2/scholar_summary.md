(authored by agents unless marked 🧑)

Source: the 11 Google Scholar captures in scholar/*.txt. Each capture holds only result snippets, not full papers. So "formal verification" verdicts below rest on snippet text, not on reading the papers. "No" means no visible sign of formal proof in the snippet.

shim

1. "Visiblev8: In-browser monitoring of javascript in the wild" J Jueckstock, A Kapravelos - Proceedings of the Internet Measurement …, 2019 - dl.acm.org
   Snippet: "framework for transparent dynamic analysis of JS interaction" and "instrumented wrapper functions or proxy objects". Closest: it builds the instrumentation itself, and does not test page-side detection.
2. "Advanced attack and vulnerability scanning for the modern web" M Musch - 2023 - leopard.tu-braunschweig.de
   Snippet: "this instrumentation is completely transparent to". Claim is asserted, not proven.
3. "Scriptprotect: mitigating unsafe third-party javascript practices" M Musch, M Steffens, S Roth, B Stock… - Proceedings of the 2019 …, 2019 - dl.acm.org
   Snippet: "a nonintrusive transparent protective measure". Also: "on 9 sites our crawlers were blocked". Empirical evidence that sites detect crawlers.
Formal verification of this property: no. Results are empirical or engineering claims of transparency.

archive

1. "A framework for evaluation of composite memento temporal coherence" SG Ainsworth, ML Nelson, H Van de Sompel - arXiv preprint arXiv …, 2014 - arxiv.org
   Snippet: a memento is "temporally coherent with respect to a root memento when it can be shown that the embedded memento's …". Closest: defines the coherence property for composite mementos.
2. "Replaying Archived Twitter: When your bird is broken, will it bring you down?" K Garg, HR Jayanetti, S Alam… - 2021 ACM/IEEE joint …, 2021 - ieeexplore.ieee.org
   Snippet: "helped us determine if the memento is replaying the tweets". Empirical replay study.
3. "Challenges in replaying archived Twitter pages" K Garg, HR Jayanetti, S Alam, MC Weigle… - International Journal on …, 2024 - Springer
   Snippet: "The tweet section of Twitter's old UI is temporally coherent". Empirical.
Formal verification of this property: partial. Ainsworth et al. give a formal-style definition of temporal coherence. No result in the snippets proves a replay system preserves it.

har

No close hit for a HAR-file sanitizer. The query returned weak matches only.
1. "One Click to Leak: Characterizing the Real-World Usage and Threat Impact of MNO-based Single Sign-On Websites" J Huang, M Liu, P Chen, B Liu, Y Zhang… - arXiv preprint arXiv …, 2026 - arxiv.org
   Snippet: "we use Puppeteer-Har to generate HAR files" and "leaked developer credentials". Closest: HAR files are the source of the leak here.
2. "You Have Been LaTeXpOsEd: A Systematic Analysis of Information Leakage in Preprint Archives Using Large Language Models" RA Dubniczky, B Borsos, T Bisztray… - arXiv preprint arXiv …, 2025 - arxiv.org
   Snippet: "Table 4 presents sanitized examples of real-world credential leaks extracted from LaTeX comments". Closest on sanitization leaking credentials, though not HAR.
Formal verification of this property: no.

c2pa

1. "Verifying provenance of digital media: Security analysis of C2PA and its implementation" E Golaszewski, N Krawetz, AT Sherman… - Cryptology ePrint …, 2026 - eprint.iacr.org
   Snippet: "the claim generator shall ensure the exclusion range only contains content from C2PA Manifest". Closest: analyzes the exclusion-range rule directly.
2. "ZK-Disclosure: Privacy-Preserving Information Disclosure for Digital Evidence with C2PA and zk-SNARKs" J Marinho, E Schiller, A Debauge… - 2025 Annual Computer …, 2025 - ieeexplore.ieee.org
   Snippet: "we formally identified an undetectable tampering attack". Formal-style analysis of a C2PA tampering gap.
3. "PointCloud-ID: Deterministic Cross-Format Identity and Attribute-Aware Integrity Verification for Geospatial Point Clouds" A Urias - 2026 - researchsquare.com
   Snippet: "C2PA custom assertion beside the standard hard binding". Adjacent, not about hash-exclusion ranges.
Formal verification of this property: partial. Snippets do not show whether Golaszewski et al. give a machine-checked proof or only an analysis. Read the paper before relying on this.

distill

1. "Focusagent: Simple yet effective ways of trimming the large context of web agents" I Kerboua, SO Shayegan, M Thakkar, XH Lù… - arXiv preprint arXiv …, 2025 - arxiv.org
   Snippet: "text is included in the observation but not visible to the user" (accessibility-tree trimming). Closest on pruning.
2. "Prismata: Confining Cross-Site Prompt Injection in Web Agents" C Villa, AE Ozdarendeli, S Tan, RA Popa - arXiv preprint arXiv:2607.08147, 2026 - arxiv.org
   Snippet: "We count a descendant as actionable if it is a non-hidden" and "pruning non-visible". Closest on hidden/visible pruning as a security control.
3. "Indirect prompt injection in the wild: An empirical study of prevalence, techniques, and objectives" S Khodayari, X Zhang, B Acharya… - arXiv preprint arXiv …, 2026 - arxiv.org
   Snippet: "∼87% of injections are non-visible, of which 70% are hidden". Empirical.
Formal verification of this property: no. Visibility handling is heuristic or empirical in every snippet.

prerender

1. "PreSight: A Vision for an Instantaneous Web" I Khor, S Ahmad, A Wildani - Proceedings of the 3rd Workshop on …, 2024 - dl.acm.org
   Snippet: a vision paper on speculation rules. Privacy is raised, not proven.
2. "Exposing cookie policy flaws through an extensive evaluation of browsers and their extensions" G Franken, T Van Goethem… - IEEE Security & Privacy, 2019 - ieeexplore.ieee.org
   Snippet: "requests initiated through prerender functionality include strict". Closest: prerender leaks state (cookie policy) in real browsers.
3. "Doubly dangerous: Evading phishing reporting systems by leveraging email tracking techniques" A Chand, N Nikiforakis, P Vadrevu - 34th USENIX Security Symposium …, 2025 - usenix.org
   Snippet: "non-deterministic pre-rendering". Empirical side effect.
Formal verification of this property: no. The closest work finds leaks by measurement, not by proof.

swatomic

1. "Continuous deployment at Facebook and OANDA" T Savor, M Douglas, M Gentili, L Williams… - Proceedings of the 38th …, 2016 - dl.acm.org
   Snippet: "reverting the deployed update to the previous version". Closest on rollout and version skew, but operational.
2. "Service workers" VK Kotaru - … Reliable, Performant Web Applications for Desktop and …, 2022 - Springer
   Snippet: "an approach and a strategy for updating service workers" for a "single-page application (SPA)". Closest on SW and SPA update mixing.
3. "Holistic configuration management at facebook" C Tang, T Kooburat, P Venkatachalam… - Proceedings of the 25th …, 2015 - dl.acm.org
   Snippet: homegrown tools for managing updates across applications. Systems paper, not a model.
Formal verification of this property: no.

chunk

1. "Withholding the Completing Chunk: Exact Release-Boundary Equivalence for Production Streaming Guardrails" CM Frost - arXiv preprint arXiv:2608.10279, 2026 - arxiv.org
   Snippet: "the resulting monitor is release-boundary" and "chunk-invariant at release time". Closest: proves output invariance under chunk boundaries, but for LLM guardrails, not HTML parsing.
2. "Static Analysis for Efficient Streaming Tokenization" AW Li, Y Yang, K Mamouras - Proceedings of the 31st ACM International …, 2026 - dl.acm.org
   Snippet: "we conclude that the loop invariant holds at end of". Streaming tokenizers with static analysis, not an HTML parser.
3. "TDOM: LaTeX Authoring Without the Compile Wait Verified Incremental Typesetting over a Live Document Tree" K Kawaguchi, T Kokawa - 2026 - fermion.company
   Snippet: "an equivalence test" and "The invariant tests for the editing path passed 20/20". Testing, not proof, and not HTML.
Formal verification of this property: partial. Frost gives a formal equivalence result for a related streaming property. No result covers HTML parser output under network chunking.

redirect

1. "Poisoned by the Host: Large-Scale Measurement of Host Name Poisoning in Web Applications" R Yang, H Wang, Z Sun, Z Liu… - 2026 IEEE Symposium on …, 2026 - ieeexplore.ieee.org
   Snippet: "We use Nginx and Apache to represent originside request". Closest: measures host-header issues in web stacks.
2. "ReqsMiner: Automated Discovery of CDN Forwarding Request Inconsistencies and DoS Attacks with Grammar-based Fuzzing." L Zheng, X Li, C Wang, R Guo, H Duan, J Chen… - NDSS, 2024 - researchgate.net
   Snippet: "enabling the detection of differing requests during forwarding". Fuzzing, not proof.
3. "CornerCase: Automated Extremal Testing of Protocol Implementations using LLMs" R Singha, K Qian, S Saikrishnan, T Zhao… - arXiv preprint arXiv …, 2026 - arxiv.org
   Snippet: "induce redirect loops, leading to repeated requests". Testing, not proof.
Formal verification of this property: no. No hit covers verifying rewrite or redirect rules for loops or open redirects.

tcf

1. "Johnny can't revoke consent either: measuring compliance of consent revocation on the web" GP Kancherla, N Bielova, C Santos… - PETS 2025-Privacy …, 2025 - hal.science
   Snippet: "consent strings from __tcfapi with the consent strings found". Closest: compares TC strings against observed behavior. Empirical.
2. "A study of gdpr compliance under the transparency and consent framework" M Smith, A Torres-Agüero, R Grossman, P Sen… - Proceedings of the …, 2024 - dl.acm.org
   Snippet: "we use the strings to assess TCF". Empirical.
3. "Consent verification monitoring" M Robol, TD Breaux, E Paja, P Giorgini - ACM Transactions on Software …, 2023 - dl.acm.org
   Snippet: "We propose a formal consent framework to support". Closest on formal treatment of consent, not TCF string format.
Formal verification of this property: partial. Robol et al. give a formal model of consent, not a verified TC string parser or CMP checker. The TCF measurement papers are empirical.

robots

1. "Somesite i used to crawl: Awareness, agency and efficacy in protecting content creators from ai crawlers" E Liu, E Luo, S Shan, GM Voelker, BY Zhao… - Proceedings of the …, 2025 - dl.acm.org
   Snippet: "experimenting with robots.txt parsers from both Google and [70]" and "a parser is fully compliant with RFC 9309. Case 1." Closest: tests parser compliance with RFC 9309.
2. "Nectar: An Active Defense Middleware for Economic Deterrence of Web Scrapers" I Khurana, A Kumar - 2026 International Conference on …, 2026 - ieeexplore.ieee.org
   Snippet: "The parser is based on a deterministic finite automaton over the robots.txt grammar from RFC 9309". Uses a DFA model, but no proof of parser correctness appears in the snippet.
3. "Agent Compliance with robots. txt SOM Directives: Empirical Evidence of the Discovery Gap" D Hurley - 2026 - dbhurley.com
   Snippet: "parsers (100%) parse the SOM-extended robots.txt without errors, preserving all Allow/Disallow rules exactly as specified by RFC 9309". Empirical test against real parsers.
Formal verification of this property: no. Parser correctness is checked by testing. The Nectar DFA is a design, not a verification.
