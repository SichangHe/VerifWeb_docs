# Closest prior FV work (Google Scholar, as_ylo=2020)
(authored by agents unless marked 🧑)

Raw results: /hdd1/sichangheagent/vl_meeting_work/out/vlm28_fvfirst/scholar/q1..q13.txt (JSON, field "text").
Query for topic N is in q(N) (q1=topic 1 ... q13=topic 13). No CAPTCHA hit; all 13 ran.
Snippets are verbatim from Scholar result text (with Scholar's own "…" elisions).
"Not covered" lines are my inference, not from the sources.
Scholar snippets are query-keyed fragments; they do not show a paper's full claims.

## 1. HTTP parsing / request smuggling
No verified HTTP/1.1 parser or parser-differential proof surfaced. Closest are empirical/differential-testing works.
- The HTTP garden: discovering parsing vulnerabilities in HTTP/1.1 implementations by differential fuzzing of request streams. B Kallus, P Anantharaman, M Locasto et al. arXiv 2024.
  - "HTTP parsing discrepancies: the HTTP Garden. The … For example, we have discovered HTTP request smuggling …"
  - Not covered: any proof; fuzzing finds discrepancies but cannot show absence.
- T-reqs: Http request smuggling with differential fuzzing. B Jabiyev, S Sprecher, K Onarlioglu et al. ACM CCS 2021.
  - "As we show, the protocol values still trigger unexpected parsing …"
  - Not covered: formal spec or verification; grammar-based fuzzing only.
- PathFault: Automated Exploit Generator for Web Services via HTTP Message Parser Discrepancies. J Kim, Y Shin. ICISC 2025.
  - "This work enables precise white-box analysis of HTTP parsing … generator that produces formally verified payloads"
  - Not covered: verifies payloads, apparently not the parsers (inference from snippet).
- Pointer: Grenfeldt et al. (IEEE 2021): "is to use a verified ABNF parser [13]. This would prevent any syntax parsing errors" (suggestion only).

## 2. WHATWG URL parser verification
No mechanized URL standard surfaced.
- yoU aRe a Liar://A Unified Framework for Cross-Testing URL Parsers. DK Ajmani, I Koishybayev et al. IEEE S&P Workshops 2022.
  - "a list of parsers and tools we used to test for URL parsing inconsistencies."
  - Not covered: testing only, no formal model.
- URL location ambiguity. J Reynolds. UIUC thesis 2022.
  - "in URL parsing across more than a dozen URL parsers that …"
  - Not covered: empirical/user study, no proof.
- Adjacent: Computer-aided formal security analysis of the Web platform. L Veronese. TU Wien thesis 2024 (WebSpec line; does not mention URL parsing in the snippet).

## 3. Cookie policy formal model / verified cookie jar
No verified cookie jar surfaced. Formal Web-platform models touch cookies.
- WebSpec: Towards machine-checked analysis of browser security mechanisms. L Veronese, B Farinier, P Bernardo et al. IEEE S&P 2023.
  - "Scripts in our model can update the DOM, set and get cookies using Document.…"
  - Not covered: machine-checks invariants over a browser model; does not verify a cookie-jar implementation or RFC 6265bis storage-model algorithms (inference).
- Cookie crumbles: Breaking and fixing web session integrity. M Squarcina, P Adão, L Veronese et al. USENIX Security 2023.
  - "capabilities of standard threat models that are relevant to violations of cookie integrity."
  - Not covered: analysis of integrity attacks plus fixes; the jar's parsing/eviction logic is not verified (inference).
- Web Platform Threats: Automated Detection of Web Security Issues With WPT. P Bernardo, L Veronese et al. USENIX Security 2024.
  - "Noticing this ambiguity in the RFC, we investigated how different …"
  - Not covered: test-based; no proofs.

## 4. CRDT / OT convergence verification
- Type-checking CRDT convergence. G Zakhour, P Weisenburger et al. PACMPL (OOPSLA/PLDI-era) 2023.
  - "Further, we found that very complex CRDTs like Automerge [Kleppmann 2017] (a JSON CRDT) are challenging to prove. None of the tools in our evaluation is able to prove them …"
  - Not covered: the Automerge algorithm itself is not proven; no implementation-level (Rust/Verus) verification.
- Scholar returned only 2 results for the combined query (second is irrelevant). Isabelle/Coq/Verus CRDT works (e.g. Gomes et al. 2017, pre-2020) did not surface; a narrower follow-up query is needed.

## 5. Wasm compiler verification
- Lightweight, modular verification for webassembly-to-native instruction selection (Crocus). A VanHattum, M Pardeshi, C Fallin et al. ASPLOS 2024.
  - "'s ISLE domain-specific language (DSL) for specifying how IR terms translate to machine … Crocus's design (§3), and evaluate its results on Cranelift (§4), a production Wasm compiler …"
  - Not covered: per the follow-up paper, requires every intermediate rule verified and ISA semantics were hand-written; (follow-up snippet below).
- Scaling Instruction-Selection Verification against Authoritative ISA Semantics (Arrival). M McLoughlin, A Sheng, C Fallin, B Parno et al. PLDI/ACM 2025.
  - "'s ability to verify Cranelift instruction selection for Wasm compilation on … , Crocus required that every intermediate rule be verified … vWasm [14] is a Wasm-to-x86 compiler with end-to-end …"
  - Not covered: lowering rules only; not mid-end (egraph/optimization) rules or regalloc/emission (inference).
- WaVe: a verifiably secure WebAssembly sandboxing runtime. E Johnson, E Laufer, Z Zhao et al. IEEE S&P 2023 (appeared under q11).
  - "The alternative to binary verification is to formally verify the SFI compiler […"
  - Not covered: runtime sandbox, not compiler lowering.

## 6. QUIC formal verification
- Verifying QUIC implementations using Ivy. C Crochet, T Rousseaux, M Piraux et al. EPIQ 2021.
  - "Another approach [8] is to produce a mathematical model for the protocol and its requirements, and then use formal verification to automatically assess correctness."
  - Not covered: compositional testing against Ivy spec, not proving the implementation; liveness untreated (see next).
- Towards verification of QUIC and its extensions. C Crochet, JF Sambon. UCLouvain thesis.
  - "Verifying QUIC liveness properties are complex. McMillan …"
  - Not covered: liveness left hard/open per snippet.
- Network simulator-centric compositional testing. T Rousseaux, C Crochet, J Aoga, A Legay. FormaliSE 2024 (snippet title "Conference on Formal …").
  - "NCT is a simulation-based formal verification approach pre…"
  - Not covered: simulation-based, not deductive.
- Survey remark (Joarder, Fung, IEEE TNSM 2024): "Ivy [14] for defining QUIC and finding vulnerabilities, focusing on safety properties. However, they did not test liveness …"

## 7. CDN / cache invalidation TLA+
No CDN-specific TLA+ work surfaced. Only generic cache-coherence protocols.
- FUSEE: A fully memory-disaggregated key-value store. J Shen, P Zuo et al. FAST/USENIX 2023.
  - "To guarantee cache coherence, an invalidation bit is stored … We formally verify FUSEE in TLA+ [35] for safety and absence …"
  - Not covered: RDMA KV store, not HTTP caching/CDN purge semantics.
- Pegasus: Tolerating skewed workloads in distributed storage with In-Network coherence directories. J Li, J Nelson et al. OSDI 2020.
  - "a TLA+ specification of the protocol which we …"
  - Not covered: coherence directory in switches, not CDN.
- Semantic Fractures at System Boundaries in Cloud Platforms. SR Bej, M Dwivedi, A Jain. IEEE conf. 2026.
  - "cache invalidation delay and event …" (taxonomy mentioning TLA+/Alloy)
  - Not covered: taxonomy, no concrete model.

## 8. CSP / CORS formal semantics
- WebSpec (above, S&P 2023).
  - "level of Web specifications have also affected CORS [9], CSP [49], … the interaction between Content Security Policy and local …"
  - Not covered: no verified CSP/CORS evaluator implementation (inference).
- Computer-aided formal security analysis of the Web platform. L Veronese. TU Wien thesis 2024.
  - "We show here how to formally verify the security of the fix we …"
  - Not covered: as above.
- Head(er)s Up! Detecting Security Header Inconsistencies in Browsers. J Rautenstrauch et al. ACM CCS-era 2025.
  - "We also sample the tests and verify the recorded outcomes …"
  - Not covered: differential testing, no proofs.

## 9. Verified X.509
- ARMOR: A formally verified implementation of X.509 certificate chain validation. J Debnath, C Jenkins, Y Sun, SY Chau, O Chowdhury. IEEE S&P 2024.
  - "We present ARMOR, the first substantial effort towards an X.509 certificate chain validation logic (… With ARMOR, our main goal is to develop a relational specification for X.509 certificate …"
  - Not covered: Dafny-based (not Verus); does not cover broader stack per Verdict paper.
- Towards Practical, End-to-End Formally Verified X.509 Certificate Validators with Verdict. Z Lin, M McLoughlin, P Singh et al. USENIX Security 2025.
  - "validation logic in complex, production-level X.509 validators. We also tested ARMOR, CERES, and Hammurabi … ARMOR's parser rejects all of the root certificates in the test suite, which …"
  - Not covered: this is the Verus-style entry (inference from authors/venue); snippet doesn't state the tool.
- Hammurabi: A framework for pluggable, logic-based X.509 certificate validation policies. J Larisch, W Aqeel, M Lum et al. ACM CCS 2022.
  - "mechanism—the low-level implementation code responsible for parsing certificates, verifying cryptographic signatures, and executing policy rules. The separation of mechanism and …"
  - Not covered: policy layer is logic-based; mechanism not verified (inference).
- Also: An RPKI Certificate Validator for Formal Correctness (Teng et al., 2025): "a formally verified RPKI validator based on ARMOR."

## 10. OAuth / OIDC
- Formal security analysis of the OpenID FAPI 2.0: Accompanying a standardization process. P Hosseyni, R Küsters, T Würtele. IEEE CSF 2024.
  - "on the Web Infrastructure Model (WIM) [25], which is the most detailed formal model of the Web infrastruc…"
  - Not covered: manual protocol-level proofs; no verified implementation.
- Formal Security Analysis of the OpenID Financial-grade API 2.0. Hosseyni, Küsters, Würtele. OpenID Foundation/2022.
  - "a REST/JSON model protected by OAuth with high security … was conducted using the Web Infrastructure Model (WIM), …"
  - Not covered: token refresh specifics not visible.
- AuthSaber: Automated Safety Verification of OpenID Connect Programs. T Al Rahat, Y Feng, Y Tian. ACM CCS 2024.
  - "our verification problem to an instance of LTL model checking. … Since there are no other formal verification tools available for …"
  - Not covered: client-program safety, not WIM-style whole-ecosystem model.
- Also: Formal analysis of web protocols and mechanized security proofs. P Hosseyni. Stuttgart thesis 2026 (mechanized WIM-style work; snippet only shows scope).

## 11. Browser process / site isolation FV
No formal verification of site isolation surfaced; only testing/attacks.
- Are your Sites Truly Isolated? Automatically Detecting Logic Bugs in Site Isolation Implementations. J Drescher, D Klein, M Johns. NDSS 2026.
  - "in the NVD for one of the browsers whose description contains the term Site Isolation. For both browsers, we only consider bugs filed after Site Isolation was rolled out …"
  - Not covered: bug finding, no proof.
- State of Browser Process-Isolation: The Same-Site Weakness. F Kilger et al. IEEE conf 2026.
  - "all browsers implementing site isolation also isolate by scheme, while all …"
  - Not covered: measurement.
- Retrofitting fine grain isolation in the Firefox renderer. S Narayan, C Disselkoen et al. USENIX Security 2020.
  - "require applications to be formally verified correct (in contrast …"
  - Not covered: RLBox sandboxing, not process-isolation model.

## 12. HTTP/2 flow control deadlock freedom
No relevant FV surfaced (weakest topic).
- PRETT2: Discovering HTTP/2 DoS Vulnerabilities via Protocol Reverse Engineering. C Lee, I Jafarov, S Dietrich, H Lee. ESORICS 2024.
  - "flow control across various HTTP/2 implementations has largely depended on manual inspection. … the flow control of popular HTTP/2 implementations using stateful fuzzing by PRETT2."
  - Not covered: fuzzing, no deadlock-freedom proof.
- Implementability of Global Distributed Protocols Modulo Network Architectures. E Li, T Wies. PACMPL 2026.
  - "another without introducing deadlocks or protocol violations in the distributed implementation of a global protocol."
  - Not covered: generic framework, not HTTP/2.
- Multiparty session typing in Java, deductively. J Bouma, S de Gouw, SS Jongmans. TACAS 2023.
  - "global type and liveness (communication deadlock freedom) are assured; else, a bug …"
  - Not covered: generic session types, not HTTP/2 windows.

## 13. Proof maintenance / repair as specs evolve
- KVerus: Scalable and resilient formal verification proof generation for Rust code. Y Liu, X Wan, Y Wang et al. ACM 2026 (venue "41st ...", likely ASE).
  - "KVerus, a practical LLM-assisted workflow for Verus proof generation in evolving Rust repositories. … They must also maintain these proofs as the implementation and the Verus toolchain …"
  - Not covered: tracks code/toolchain evolution; not external living-standard spec changes (inference).
- Proof Repair Utilizing Large Language Models: A Case Study on the Copland Remote Attestation Proofbase. A Tahat, D Hardin, A Petz, P Alexander. 2024 (Springer workshop).
  - "Our LLM-generated proofbase currently consists of over … repair for evolving formal attestation protocol specifications."
  - Not covered: single Copland proofbase (Coq), small domain.
- AutoVerus: Automated proof generation for Rust code. C Yang, X Li et al. OOPSLA 2025.
  - "The LLM is quickly evolving and Verus is also evolving. It is …"
  - Not covered: generation, not repair across spec revisions.
- Also: Proof automation with large language models (PALM). M Lu, B Delaware, T Zhang. ASE 2024: "a novel generate-then-repair approach that first prompts an LLM to generate an initial proof and then leverages targeted symbolic methods to iteratively repair lowlevel problems."
