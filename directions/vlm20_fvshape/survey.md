(authored by agents unless marked 🧑)

# Where formal verification (FV) worked in industry, and the shape of a good FV target

Method: quotes were copied from the primary papers/pages named in each entry (PDFs fetched with curl, text via pdftotext, 2026-11-09). Quotes are verbatim except line breaks. "Inference" marks my own reading. Nothing was published. Scholar was not needed.

Sources not reached or not quoted, so those facts are unsupported here: seL4 deployers (the "Who is using seL4?" page returned only navigation text), Google-internal FV beyond BoringSSL, Verus industrial deployment, Microsoft Research pages (rate-limited).

## 1. AWS Zelkova (IAM / resource policy analysis)
- What was verified: AWS access-control policies, translated to SMT. Source: Backes et al., FMCAD 2018, https://cdn.amazon.science/56/3c/7d75bca84c56b9b1ed1999beec0c/semantic-based-automated-reasoning-for-aws-access-policies-using-smt.pdf
  - "ZELKOVA translates policies and properties into Satisfiability Modulo Theories (SMT) formulas and uses SMT solvers to check the validity of the properties."
- Property: questions over all requests.
  - "ZELKOVA can answer the questions “Is this resource accessible by a particular user?” and “Can an arbitrary user write to this resource?”."
- Deployed by AWS inside S3, Config, Macie, Trusted Advisor, GuardDuty.
  - "Used many millions of times every day, ZELKOVA analyzes policies attached to resources"
- Why it fit:
  - the spec is the policy language itself: "The property to be verified is specified in the policy language itself, eliminating the need for a different specification or formalism for properties."
  - tests cannot cover all requests: "Zelkova uses mathematics to talk about all possible requests" is my shortened paraphrase; verbatim from https://aws.amazon.com/blogs/security/protect-sensitive-data-in-the-cloud-with-automated-reasoning-zelkova/ via a summarizer: "Other techniques guess and check, but Zelkova knows." (summarizer output, treat as lower confidence)
  - it is fast despite hardness: "99% of policy questions can be answered in less than 160 milliseconds."

## 2. AWS Tiros (VPC network reachability)
- What: static analysis of customer virtual networks via off-the-shelf theorem provers. Source: Backes et al., CAV 2019, https://d1.awsstatic.com/whitepapers/Security/Reachability_Analysis_for_AWS-based_Networks.pdf
  - "Tiros is the foundation of a recently introduced network security analysis feature in the Amazon Inspector service now available to millions of customers building applications in the cloud."
- Property: network security invariants.
  - "Customers or regulators want to make sure that their VPC networks retain security invariants as their complexity grows."
- Deployer: AWS; customer Bridgewater.
  - "Bridgewater Associates worked with AWS Professional Services to build a Tiros-based solution which proves invariants of new AWS-based network designs before they are deployed"
- Why it fit:
  - testing is inadequate: "allows users to gain assurance about the security of their networks that would be impossible through testing."
  - compliance value: "It can also reduce the cost and time-to-market for regulated customers looking to establish compliance certification for cloud-based applications."

## 3. s2n / SAW (AWS TLS library)
- What: s2n's HMAC, DRBG, and TLS handshake code proved against Cryptol specs. Source: Chudnov et al., CAV 2018, http://www0.cs.ucl.ac.uk/staff/b.cook/CAV18_s2n.pdf
  - "We describe formal verification of s2n, the open source TLS implementation used in numerous Amazon services."
- Property: for HMAC, the code matches a spec tied to a security property.
  - "The HMAC specification establishes the cryptographic security property of interest." (adjacent text: "if the key is not known, then HMAC is [a pseudorandom function]"; the quote above is verbatim, the bracketed gloss is not.)
- Deployer: AWS/Galois, in CI.
  - "The proof is applied as part of the continuous integration system for s2n (which uses Travis CI) and runs every time a code change is pushed or a pull request is issued. In one year of code changes only three manual updates to the proof were required."
- Why it fit:
  - fixed, public spec (HMAC, NIST) and small hot code
  - customers in regulated industries: "Formal verification provides customers from these industries with concrete information about how security is established in Amazon Web Services."
  - proof maintenance was cheap enough to run on every commit (quote above)

## 4. HACL* / Project Everest (Firefox NSS, Linux kernel)
- What: verified crypto library. Source: https://project-everest.github.io/
  - "HACL* is a formally verified library of modern cryptographic algorithms" (summarizer-extracted; page also says each primitive is verified for "memory safety, functional correctness, and secret independence")
- Deployers (from raw page text): "Code from HACL*, ValeCrypt and EverCrypt is deployed in several production systems, including Mozilla Firefox , the Linux kernel, mbedTLS, the Tezos blockchain, the ElectionGuard electronic voting SDK, and the Wireguard VPN."
- Caveat on the page: "Still, HACL*, Vale, and EverCrypt remain ongoing research projects" (truncated in my capture; the page text continues "and shoul[d]...").
- Why it fit (inference): small pure functions, public specs (RFCs/NIST), constant-time requirement not testable by functional tests, and the output is plain C that drops into existing codebases ("provides efficient, readable, standalone C code for each algorithm", summarizer-extracted).

## 5. Fiat-Crypto (Chrome / BoringSSL)
- What: Coq-proved generator of field-arithmetic C code for P-256 and Curve25519. Source: Erbsen et al., IEEE S&P 2019, https://adam.chlipala.net/papers/FiatCryptoSP19/FiatCryptoSP19.pdf
  - "Implementations from our library were included in BoringSSL to replace existing specialized code, for inclusion in several large deployments for Chrome, Android, and CloudFlare."
- Property: functional correctness of modular arithmetic.
  - "short high-level code with machine-checked proofs of functional correctness"
- Deployer: Google (BoringSSL), at scale.
  - "today about half of HTTPS connections opened by Web browsers worldwide use our fast verified code"
- Why it fit:
  - hand-written assembly was hard to change and review: "While the BoringSSL developers had not previously found it worthwhile to modify 64-bit assembly code and review the changes, they made use of our code-generation pipeline"
  - proof effort amortized by generation: "implementation and proof effort scales with the number and complexity of conceptually different algorithms, not their use cases."
  - the baseline cost is expert time: "expert time is spent on annotating the now-munged code with assertions"

## 6. seL4 (microkernel)
- What: kernel C code and binary proved against an abstract spec; plus access control and information-flow noninterference. Source: Klein et al., ACM TOCS 2014, https://sel4.systems/Research/pdfs/comprehensive-formal-verification-os-microkernel.pdf
  - "a proof that the binary code of the kernel correctly implements the C semantics, a proof of correct access-control enforcement, a proof of information-flow noninterference"
- Deployer: not sourced in this run (see top).
- Why it fit:
  - kernel is the trust root: "The target of our verification, the kernel, is the most critical part of a system, which is our motivation for starting system verification with this component."
  - design made small: "We discuss the kernel design we used to make its verification tractable." Size: "10 000 lines of code ... its now 480 000 lines of Isabelle proofs and specifications."
  - cost: "11 py on the seL4-specific proof" (about 20 py total including frameworks and tools).
  - proofs were maintainable: "kept current as the requirements, design and implementation of the system evolve over almost a decade."

## 7. CompCert (Airbus flight control)
- What: C compiler proved to preserve semantics. Source: https://compcert.org/compcert-C.html
  - "All intermediate languages are given formal semantics, and each of the transformation passes is proved to preserve semantics."
- Deployer: Airbus France. Source: https://www.absint.com/compcert/index.htm (vendor page)
  - "For over a decade now, Airbus France has been deploying CompCert at the Toulouse plant. Among other things, the compiler has helped meet performance-gain objectives by reducing the worst-case execution time of the targeted software."
- Limits stated by the project: "the formal guarantees of semantic preservation apply only to whole programs that have been compiled as a whole by CompCert C."
- Why it fit:
  - the target is "life-critical and mission-critical software written in C" (compcert.org) where certification credit matters
  - the spec is the C semantics, which exists; the property is a single theorem for all programs, so the proof cost is paid once
  - Airbus also got a performance win, not only assurance (AbsInt page above)

## 8. Linux eBPF verifier (a verification target, not a verified artifact)
- What: Agni checks the soundness of the verifier's range analysis, with logic extracted from kernel C. Source: Vishwanathan et al., CAV 2023, https://people.cs.rutgers.edu/~sn349/papers/agni-cav2023.pdf
  - "We automatically generate verification conditions that encode the operation of the eBPF verifier directly from the Linux kernel's C source code and check it against our specification."
- Result: "we have discovered new bugs in older versions and proved the soundness of range analysis in the latest version of the Linux kernel."
- Deployer: Rutgers researchers; the paper does not say the kernel adopts Agni in CI. My earlier search summary said a follow-on aims at CI, not verified here.
- Why it fit:
  - a verifier is a small decision procedure whose soundness is precisely statable: abstract interpretation gives the spec ("We provide the specification of soundness for range analysis").
  - high cost of error: the verifier gates untrusted code in the kernel (inference).
  - the status quo lacks assurance: "the Linux kernel does not provide any soundness guarantees for these operators."

## 9. Azure SecGuru (ACLs, forwarding, BGP contracts)
- What: network contracts checked with Z3 bit-vector formulas. Source: Bjorner and Jayaraman, ICDCIT 2015, https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/nbjorner-icdcit2015.pdf
  - "They are checked using the SecGuru tool that continuously monitors configurations in Azure."
- Property example: "there is a policy that says that SSH ports on fabric devices should not be open to guest virtual machines."
- Deployer: Microsoft Azure.
  - "In continuous validation, SecGuru checks policies over ACLs on every router update as well as once a day. This is more than 40,000 checks per month, where each check takes 150-600 ms."
- Impact: "SecGuru had a measurable positive impact in prohibiting policy misconfigurations during build-out, raising in average of one alert per day"
- Why it fit: configs change often while policies do not: "While these policies themselves rarely change, IP addresses do change frequently, which makes using SecGuru as a regression test useful."

## 10. Batfish (network configuration analysis)
- Source: https://www.batfish.org/
  - "Batfish finds errors and guarantees the correctness of planned or current network configurations."
- Deployer/origin: "Batfish was originally developed by researchers at Microsoft Research, UCLA, and USC. It was later enhanced and maintained by Intentionet. Since the Intentionet team joined AWS, it has been an AWS-managed open source project"
- Why it fit (inference): same traits as SecGuru; input is a configuration (finite, parseable), the semantics is the network's forwarding behavior, changes are checked before rollout ("planned ... configurations"). The page claims "It enables safe and rapid network evolution, without the fear of outages or security breaches." No outcome numbers were captured.

## 11. P4 verification (p4v, Gauntlet)
- p4v (Barefoot Networks, SIGCOMM 2018): http://www.cs.cornell.edu/~jnfoster/papers/p4v.pdf (fetched from cs.cornell.edu path)
  - "p4v is able to verify critical safety properties for switch.p4, a program that implements the functionality of on a modern data center switch, in under three minutes."
  - why: "Testing is expensive, since modern devices handle dozens of different packet formats and protocols, each requiring distinct test inputs."
  - deployer: the authors are Barefoot Networks employees plus academics; production use is not stated in the text I read.
- Gauntlet (NYU, OSDI 2020): https://www.usenix.org/system/files/osdi20-ruffy.pdf
  - "Gauntlet detected 96 new and distinct bugs (62 crash and 34 semantic), which we confirmed with the respective compiler developers."
  - deployment: "it now runs within P4C's continuous integration pipeline."
  - this is bug finding by translation validation, weaker than proof.
- Why it fit: P4 is a small, restricted language (no loops), so symbolic semantics is tractable (inference, not quoted).

## 12. GRoot (DNS zone files)
- What: static verifier of DNS zone files. Source: Kakarla et al., SIGCOMM 2020, http://web.cs.ucla.edu/~todd/research/sigcomm20.pdf
  - "GRoot uses a new, fast verification algorithm based on generating and enumerating DNS query equivalence classes."
- Property: no rewrite loops, blackholing and similar.
- Results: "When applied to internal zone files consisting of over 3.5 million records from a large infrastructure service provider, GRoot revealed around 160k issues of blackholing, initiating a cleanup."
- Deployer: not stated as production deployment; the provider is unnamed. Treat as research with an industrial case study.
- Why it fit:
  - real outages: "DNS misconfiguration related outages have rendered popular services like GitHub, HBO, LinkedIn, and Azure inaccessible for extended periods."
  - infinite query space collapsed into finitely many classes: "enabling proactive and exhaustive checking for common DNS bugs; by contrast, existing solutions are reactive and incomplete."
  - spec exists as an RFC-derived model: "we develop a formal semantic model of DNS resolution."

## 13. Meta Infer (and, for contrast, Google)
- Source: Distefano et al., CACM 2019, https://cacm.acm.org/research/scaling-static-analyses-at-facebook/ (text read from the UCSD PDF copy https://cseweb.ucsd.edu/~dstefan/cse227-spring20/papers/distefano:scaling.pdf)
  - "the fix rate rocketed to over 70%. The same program analysis, with same false positive rate, had much greater impact when deployed at diff time."
  - and the batch deployment: "the fix rate—the proportion of reported issues that developers resolved—was near zero."
- Caveat: Infer is compositional static analysis (separation logic bi-abduction), not a proof of functional correctness. The lesson is about deployment fit, not spec precision.
- Why it fit: the property is a fixed bug class (null deref, races) needing no per-project spec, and it runs in the code-review workflow.
- Google: the only Google FV item sourced here is Fiat/BoringSSL (entry 5). I did not find Google-internal FV deployments in this run.

## 14. IronFleet / Verus (research, no deployment sourced)
- IronFleet, Hawblitzel et al., SOSP 2015, https://sigops.org/s/conferences/sosp/2015/current/2015-Monterey/250-hawblitzel-online.pdf
  - "We prove that each obeys a concise safety specification, as well as desirable liveness requirements."
  - cost: "In total, developing the IronFleet methodology and applying it to build and verify two real systems required approximately 3.7 person-years." Ratio: "proof annotation to executable code is 3.6 to 1."
- Verus, Lattuada et al., arXiv 2303.05491, https://arxiv.org/abs/2303.05491 (PDF fetched)
  - "This paper presents Verus, an SMT-based tool for formally verifying Rust programs." The SOSP 2024 abstract claims lower effort ("3-61x faster" came from a search summary, not a page I read; unverified).
- Deployer: research groups (CMU, MSR, VMware Research, ETH). No industrial deployment evidence captured.
- Why it fits less: large, concurrent, stateful systems need big specs and proofs; a concise spec (replicated state machine) is what made it feasible.

## The shape of a good FV target

Each trait lists entries that show it. "Absent" notes counter-examples.

1. A precise spec already exists or is cheap to write.
   - Public standard: HMAC/NIST (3, 4), C semantics (7), DNS resolution rules (12), P4 semantics (11)
   - Spec embedded in the artifact's own language: Zelkova policies (1)
   - Small spec for a big system: IronFleet's "concise safety specification" (14)
2. The decision problem is small and mechanical, so solvers can decide it.
   - SMT over strings/bit-vectors: Zelkova (1), SecGuru (9), Tiros (2)
   - Finite equivalence classes over infinite inputs: GRoot (12)
   - Range-analysis soundness as SMT conditions: Agni (8)
3. Input space too large for tests; exhaustive claim is the product.
   - Zelkova "all possible requests" (1); Tiros "impossible through testing" (2); p4v on testing cost (11); GRoot "proactive and exhaustive" (12)
4. High cost of error.
   - Security/compliance: Zelkova (1), Tiros (2), s2n (3); trust root: seL4 (6), eBPF verifier (8); safety-critical: CompCert (7); outages: GRoot (12), SecGuru (9)
5. Small, stable, self-contained code under proof.
   - seL4 ~10 000 lines designed for tractability (6); crypto primitives (3, 4, 5)
6. Reuse across many deployments amortizes proof cost.
   - Fiat "scales with ... conceptually different algorithms, not their use cases" (5); CompCert one theorem for all programs (7); Zelkova millions of daily invocations (1)
7. Fits the workflow: continuous, automatic re-proof.
   - s2n CI (3), SecGuru on every router update (9), Gauntlet in P4C CI (11), Infer at diff time (13)
   - Counter-signal: Infer's batch 0% vs diff-time 70% fix rate shows the same analysis fails outside the workflow (13)
8. Output slots into existing systems without changing the stack.
   - HACL*/Fiat emit C (4, 5); Zelkova is behind AWS services (1); CompCert replaces a compiler (7)
9. Where it did not (yet) cross into industry in my sources: large concurrent systems with big specs (14); full-kernel proofs when the deployer was not sourced (6). Inference: the costs there are 3.7 to 20 person-years and 3.6:1 proof-to-code.

Skeptical note: success stories are selected. Tool-reported numbers (millions of calls, ~half of HTTPS) are claims by the authors or vendors. I found no counter-examples (failed FV deployments) in this run.
