# Literature search: "many standards may be wrong; find them by formally verifying them"

CAPTCHA status: Google Scholar returned `challenge_action_required` (CAPTCHA) on query 1
("formal verification of specifications finds bugs in standards", as_ylo=2022). I stopped Scholar
and did not retry or bypass. Queries 2-9 were NOT run on Scholar; they were run via web search
(arXiv/ACM/USENIX/ASE pages) instead. Verbatim sentences below are from the paper PDFs I downloaded
(abstracts) unless marked [search-snippet].

Bug-in-standard column: YES = reports bugs/flaws in the standard text itself.

1. Bringing the WebAssembly Standard up to Speed with SpecTec. Youn, Shin, Lee, Ryu, Breitner, Gardner, Lindley, Pretnar, Rao, Watt, Rossberg. PLDI 2024. https://dl.acm.org/doi/10.1145/3656440
   "We show that SpecTec is highly effective at discovering and preventing errors by detecting historical errors in the specification that have been corrected and ten errors in five proposals ready for inclusion in the next version of Wasm."
   Bugs in standard: YES (13 historical + 10 in proposals; adopted by Wasm 2025).
2. P4-SpecTec: Integrating a Language Mechanization Framework into the Real-World P4 Specification. Lee, Jeong, Ahn, Kwon, Ryu. arXiv 2608.00639, 2026. https://arxiv.org/abs/2608.00639
   "We mechanized the most recent P4 specification, and utilizing its executability, identified 24 bugs across the official P4 specification and the reference compiler."
   Bugs in standard: YES (24 across spec + compiler; split not stated in abstract).
3. JSTAR: JavaScript Specification Type Analyzer using Refinement. Park, An, Shin, Sim, Ryu. ASE 2021. https://dl.acm.org/doi/10.1109/ASE51524.2021.9678781
   [search-snippet] "detected 157 type-related specification bugs with 59.2% precision; 93 out of 157 bugs are true bugs. Also, JSTAR detected 14 type-related bugs in ES2021, which were confirmed by TC39."
   Bugs in standard: YES (ECMA-262). Already in collection.
4. JISET (ASE 2020) / JEST (ICSE 2021) / ESMeta (CACM 2023 overview). Park, Ryu et al. https://dl.acm.org/doi/fullHtml/10.1145/3624723
   [search-snippet, CACM article] 1,709 failed Test262 tests were due to nine specification bugs in ES2019, four newly reported and confirmed by TC39. Bugs in standard: YES. JISET, JEST already in collection.
5. A Trusted Mechanised JavaScript Specification (JSCert). Bodin et al. POPL 2014. https://dl.acm.org/doi/10.1145/2578855.2535876
   [search-snippet] found and reported three bugs in ES5/ES6 drafts, three in Test262. Bugs in standard: YES. Already in collection.
6. A Coq Mechanization of JavaScript Regular Expression Semantics. De Santo, Barrière, Pit-Claudel. ICFP 2024. https://arxiv.org/abs/2403.11919
   "we identify subtle corner cases that led to mistakes in previous publications"
   Bugs in standard: NO (finds mistakes in prior publications/engines, not the ECMA-262 text, per abstract).
7. A Formal Analysis of 5G Authentication. Basin, Dreier, Hirschi, Radomirovic, Sasse, Stettler. CCS 2018. https://arxiv.org/abs/1806.10360
   "Our automated analysis identifies the minimal security assumptions required for each security goal and we find that some critical security goals are not met, except under additional assumptions missing from the standard."
   Bugs in standard: YES (3GPP TS 33.501; reported to 3GPP, most fixed per paper 11).
8. Component-Based Formal Analysis of 5G-AKA: Channel Assumptions and Session Confusion. Cremers, Dehnel-Wild. NDSS 2019. https://people.cispa.io/cas.cremers/downloads/papers/CrDe2018-5G.pdf
   "In practice this means that following the 5G-AKA specification, a provider can easily and 'correctly' implement the standard insecurely, leaving the protocol vulnerable to a security-critical race condition."
   Bugs in standard: YES (unstated assumptions; fixes worked with 3GPP).
9. A Formal Analysis of SCTP: Attack Synthesis and Patch Verification. Ginesin, von Hippel, Defloor, Nita-Rotaru, Tuexen. USENIX Security 2024. https://arxiv.org/abs/2403.05663
   "Finally, we identify and analyze an ambiguity in the SCTP RFC."
   Bugs in standard: YES (RFC 9260 ambiguity; errata proposed; author's site later says one case may not be ambiguous). Already in collection.
10. RFCScope: Detecting Logical Ambiguities in Internet Protocol Specifications. Pawagi, Shao, Lee, Sun, Wang. ASE 2025. https://wenxiwang.github.io/papers/rfcscope/rfcscope_paper.pdf
   "RFCScope uncovers 31 new logical ambiguities spanning all seven subtypes across 14 recent RFCs. Eight of these have been confirmed by RFC authors, with three officially verified as technical errata."
   Bugs in standard: YES. Also first systematic study of 273 verified errata (taxonomy; 119 direct inconsistencies). LLM-based, not formal verification.
11. It Takes a Village: Bridging the Gaps between Current and Formal Specifications for Protocols. Basin, Foster, McMillan, Namjoshi, Nita-Rotaru, Smith, Zave, Zuck. J. ACM 2025 (arXiv 2509.13208). https://arxiv.org/abs/2509.13208
   "They can help reveal disagreements about what a protocol "is" and identify areas where further work is needed to resolve ambiguities or internal inconsistencies."
   Bugs in standard: position/survey paper; summarizes success stories (incl. 5G-AKA).
12. Uncovering Gaps Between RFC Updates and TCP/IP Implementations: LLM-Facilitated Differential Checks on Intermediate Representations. Wu, Feng, Yang, Xu. arXiv 2510.24408, 2025. https://arxiv.org/abs/2510.24408
   "However, due to the complexity of the protocol and the uncertainty of cross-layer interaction, there are often inconsistencies between the implementation of the protocol stack code and the RFC standard."
   Bugs in standard: NO (implementation-vs-RFC gaps; abstract-level).
13. RFC2TLA+: Extracting and Verifying Formal Models from RFC Documents using Continuous LLM Feedback. Ding et al. ASE 2026. https://security.csl.toronto.edu/wp-content/uploads/2026/08/gding-ase2026-rfc2tla.pdf
   [search-snippet] "When invariants are wrong, TLC exposes their inconsistency with a concrete counterexample". Bugs in standard: not established. Already in collection.
14. Validating Network Protocol Parsers with Traceable RFC Document Interpretation. Zheng, Xie, Shi, Wang, Zhang. arXiv 2504.18050, 2025. Bugs in standard: not established (parser bugs; traces to RFC sections). Already in collection.
15. RFCLLM (arXiv 2609.13389) and PSMBench (NeurIPS 2025): LLM extraction of state machines from RFCs, benchmarks; no standard bugs claimed. Already in collection.
16. Not found/verified: SAGE (Yen et al., SIGCOMM 2021, semantic parsing of RFC ambiguities, pre-2022), RFCNLP; HTML-spec executable semantics and 3GPP LLM work (no hit in the searches run).

Notes: Items 1-3, 7, 8, 10 give the strongest direct support. No query covered "HTML standard executable semantics"
specifically (web search pass returned nothing HTML-specific).
