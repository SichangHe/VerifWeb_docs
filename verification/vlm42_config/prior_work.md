# Prior work: validator/consumer agreement and config-induced failures

(authored by agents unless marked 🧑)

Scope: "validator accepts x ⇒ consumer does not crash on x". Searches: Google Scholar, 7 queries, year >= 2018, raw output in scholar/q1..q7.txt (no CAPTCHA hit). Quotes are verbatim from the PDFs read; PDFs/text are in /hdd1/sichanghe/paper_collection (nothing git-added).

## Papers relied on (PDF read)

1. Testing Configuration Changes in Context to Prevent Production Failures. Sun, Cheng, Chen, Ang, Legunsen, Xu. OSDI 2020.
   Quote: "Existing misconfiguration detection and configuration validation techniques only check configuration values. These techniques cannot detect common types of failure-inducing configuration changes, such as those that cause code to fail or those that violate hidden constraints."
   Quote: "Failures typically occur when valid configuration changes expose dormant software bugs [55] and when configuration changes violate undocumented, hidden configuration constraints."
   Relation: states the exact gap (validator passes, consumer fails) as empirical motivation; the remedy is testing (ctests reuse existing tests), which finds instances, not a proof of the implication.

2. Configuration Validation with Large Language Models. Lian, Chen, Cheng, Huang, Thakkar, Zhang, Xu. arXiv 2310.09690 (2023, v2 2024).
   Quote: "Recent studies [70], [88] report that many parameters are uncovered by existing validators, even in mature software projects."
   Quote: "it is non-trivial to validate a parameter, which could have many different correctness properties, such as type, range, semantic meaning, dependencies with other parameters, etc.; encoding all of them into validators is laborious and error-prone"
   Relation: confirms validators are hand-written, incomplete, and unlinked to consumer code; LLM judgment gives no soundness guarantee.

3. Making Deployments Safe at Meta: Health Checks for Continuous Change-Safety. KL, Korenkov, Thakore, Hegre. arXiv 2608.20513 (Aug 2026, experience report).
   Quote: "discuss how the system is integrated with tiered and phased rollouts so that regressions trigger automatic rollback."
   Relation: runtime detection after partial deployment (canary style); shows the production answer is detect-and-roll-back, not prove-before-deploy. Not checked against the Google canary paper (see below).

4. EverParse: Verified Secure Zero-Copy Parsers for Authenticated Message Formats. Ramananandro et al. USENIX Security 2019.
   Quote: "The resulting code is verified to be safe (no overflow, no use after free), correct (parsing is the inverse of serialization) and non-malleable".
   Relation: proves the parser is safe on all byte inputs, so the loader half is "total"; targets binary TLV formats, not config schemas, and says nothing about downstream consumers of parsed values.

5. Hardening Attack Surfaces with Formally Proven Binary Format Parsers (EverParse3D). Swamy et al. PLDI 2022.
   Quote: "we present EverParse3D, a parser generator for binary message formats that yields performant C code backed by fully automated formal proofs of memory safety" (abstract, first lines as extracted; the remainder of the sentence was not checked).
   Relation: same as 4, deployed at scale (Windows); proves parser safety, not consumer behavior.

6. Vest: Verified, Secure, High-Performance Parsing and Serialization for Rust. Cai, Singh, Lin, Bosamiya, Gancher, Surbatovich, Parno. USENIX Security 2025 (collection folder says 2026).
   Quote: "Vest, the first framework for high-performance, formally verified binary parsers and serializers that combines expressivity and ease of use with state-of-the-art correctness and security guarantees".
   Relation: closest in toolchain (Rust + Verus); gives verified parse/serialize round-trip, so a parser's accepted language is precisely specified, which a consumer proof could take as precondition.

7. 3DGen: AI-Assisted Generation of Provably Correct Binary Format Parsers. Fakhoury, Kuppe, Lahiri, Ramananandro, Swamy. arXiv 2404.10362 (2024).
   Quote: "3DGen produces a 3D specification that conforms to a test suite, and which yields safe, efficient, provably correct, parsing code in C."
   Relation: LLM-generated format spec checked by tests, then verified parser; the spec is trusted only up to tests, same trust gap as a hand-written validator.

8. The Prusti Project: Formal Verification for Rust. Astrauskas et al. NFM 2022.
   Quote: "By default, Prusti checks that a Rust program will not panic (terminate with an error after reaching an unrecoverable state) at runtime, whether due to an explicit panic!(...) call or e.g. due to bounds-checks and integer overflows."
   Relation: provides the panic-freedom proof obligation for the consumer given a precondition; the precondition ("validator accepted x") must come from somewhere.

9. Verus: Verifying Rust Programs using Linear Ghost Types. Lattuada et al. OOPSLA 2023 (file lattuada2023verus.pdf).
   Quote: "In Rust, indexing into a vector always performs a bounds check; it is memory-safe because it will always panic rather than access memory-out-of-bounds."
   Relation: shows that in safe Rust the crash mode is panic, which Verus can rule out with preconditions via `requires`/`ensures`; so "validator accepts x" can be encoded as a `requires` on the consumer. This is my reading, not a claim of the paper.

## Seen but not relied on (not read or not obtainable)

- Tang et al., "Holistic Configuration Management at Facebook", SOSP 2015 and PCheck (Xu et al., OSDI 2016): pre-2018, user-named, not re-read here. Citation [55] in the ctest paper is the Facebook source for "16% of service-level incidents ... are induced by configuration changes" (that is ctest's claim, quoted second-hand).
- Ye et al., "Accuracy, scalability, coverage: A practical configuration verifier on a global WAN", SIGCOMM 2020: Scholar snippet only ("on the WAN might have some hidden inconsistencies or ... be forwarded to M and immediately crash M"). Network-config verification, paywalled, not fetched.
- "Canary Analysis Service", ACM Queue 2018: fetch returned a stub page, not read.
- "No panic! Verification of Rust programs by symbolic execution" and "Surveying the Rust verification landscape": titles from Scholar only, not fetched.
- ASN1*, "Secure Parsing and Serializing with Separation Logic Applied to CBOR/CDDL/COSE", "Access Control as Verified Parse Constraints" (already in collection): verified-parser family, not read for this task.
- Ctest4j, "Configuration testing: Testing configuration values as code and with code", "Test-case prioritization for configuration testing", Egida (early-error-detection config deployment): Scholar titles only.

## What is NOT covered by prior work (INFERENCE)

- No paper found that states or proves a validator-consumer contract of the form "validator accepts x ⇒ consumer is panic-free/crash-free on x". Evidence is absence in 7 Scholar queries plus the ctest paper's own claim that validators "only check configuration values"; absence in search is not proof of absence.
- Verified-parser work (EverParse, Vest, 3DGen) proves the parser total or safe, but stops at the parsed value; it does not connect the accept set to the downstream consumer's preconditions.
- Panic-freedom tools (Prusti, Verus) prove consumer properties only relative to a hand-written precondition; nothing found generates that precondition from the validator or checks that the validator implies it.
- Empirical and testing work (ctest, LLM validation, Meta health checks, canaries) finds or contains failures after the fact; none yields a pre-deployment guarantee over all accepted configs.
- The validator and consumer being separate programs (often separate languages/teams) is assumed by ctest's framing but no work found formalizes the interface between them.
