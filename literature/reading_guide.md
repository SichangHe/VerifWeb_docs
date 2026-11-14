# Reading guide for the VL papers (Nov 13 update of the Nov 10 guide)
(authored by agents unless marked 🧑)

This covers the 88 papers agents added to /hdd1/sichanghe/paper_collection for this line, in five groups. Each entry gives the file name, what the paper shows, and why it matters to us. File names are relative to paper_collection. ★ marks the 8 to read first. The Nov 13 update adds 29 papers: groups 1, 2, 3 got new entries at their end (marked "Added Nov 13"), group 6 (sync liveness) and group 7 (the 8 breadth directions) are new; each new paper was read only at abstract/introduction level. Read-first additions (my pick, opinion): Mostly Automated Verification of Liveness (LVR, POPL 2024), Evaluating Ongoing Access Attacks on the Web (CCS 2026), Empirical Security Analysis of SFI (V8 sandbox, CCS 2025), Adore (PLDI 2022), Automated Verification of Idempotence for Stateful Serverless (OSDI).

How these were read: helper agents read the extracted text of every paper (pdftotext of the PDF, or the `.md` next to it), normally the abstract, introduction, results and conclusion, not every page. No paper is "not read". Where less was read, the entry says so. The "what I take" lines and the "why" lines are my inference; the "shows" lines are from the papers. Longer notes with a verbatim quote per paper are in `work/out_*.md` next to this file.

## Read these 8 first

1. Verifying Strong Eventual Consistency in Distributed Systems (what has been proved about text merge, and on what)
2. Modular Verification of Op-Based CRDTs in Separation Logic (the one proof on real CRDT code, with its cost)
3. AMC- Towards Trustworthy and Explorable CRDT Applications with the Automerge Model Checker (the only work on Automerge's own code)
4. Towards Automated Auditing for Account and Session Management Flaws in Single Sign-On Deployments (how big the SSO revocation problem is)
5. Establishing Browser Security Guarantees through Formal Shim Verification (the closest proof of session isolation in a browser)
6. Dynamic Process Isolation (why many tenants in one JS process is risky)
7. JavaScript Language Design and Implementation in Tandem (short overview of the only JS semantics that stays current)
8. Smart Casual Verification of the Confidential Consortium Framework (how industry ties a model to real distributed code)

## 1. Editor sync and CRDTs

What I take from these 16: the machine-checked proofs of text merge are about models of an algorithm (RGA in Gomes 2017, WOOT in Karayel 2022). The one proof about real running code (Nieto 2022) covers counters, sets and maps, not text. The only work on Automerge's Rust code (AMC) is bounded checking. None of these papers verifies Automerge, Loro or Yrs code. On "as hard as consensus?": no paper here compares the two directly; Kleppmann and Howard 2020 gives the theory of when merging needs no agreement.

- ★ `Verifying Strong Eventual Consistency in Distributed Systems, Victor B. F. Gomes, Martin Kleppmann, Dominic P. Mulligan, Alastair R. Beresford, OOPSLA, 2017.pdf`
  - shows: First machine-checked convergence proofs (Isabelle) for three CRDTs including the list CRDT RGA, with a network model that delays, drops and reorders messages; the RGA proof is about 775 lines.
  - why: The core prior work for Harsha's question. It proves a model of the algorithm, and RGA is simpler than what Yrs, Loro and Automerge do (formatting, moves, compression).
- ★ `Modular Verification of Op-Based CRDTs in Separation Logic, Abel Nieto, Léon Gondelman, Alban Reynaud, Amin Timany, Lars Birkedal, OOPSLA, 2022.pdf`
  - shows: Coq/Iris proofs about real OCaml code: a causal broadcast library and 12 CRDTs (counters, sets, registers, maps), at roughly 10 to 20 proof lines per code line.
  - why: Best answer to "model or real code". It has no list or text CRDT and no Rust, which is our gap.
- ★ `AMC- Towards Trustworthy and Explorable CRDT Applications with the Automerge Model Checker, Andrew Jeffery, Richard Mortier, PaPoC, 2023.pdf`
  - shows: A model checker in Rust (Stateright) that explores all orderings of edits and syncs on the real Automerge library and checks convergence and save/load; the search is bounded, so it is not a proof.
  - why: The only paper that touches real Automerge code. It shows what bounded checking finds and leaves the unbounded proof open.
- `Strong eventual consistency of the collaborative editing framework WOOT, Emin Karayel, Edgar Gonzàlez, Distributed Computing, 2022.pdf`
  - shows: First proof (Isabelle, on a model) that the WOOT text CRDT converges; the question had been open for 14 years with only bounded checks.
  - why: Shows text-merge convergence can be subtle enough to need a new proof idea.
- `VeriFx- Correct Replicated Data Types for the Masses, Kevin De Porre, Carla Ferreira, Elisa Gonzalez Boix, arXiv, 2022.pdf`
  - shows: A small language whose CRDT code is verified automatically by Z3 and translated to Scala or JavaScript; 35 CRDTs verified, real bugs found, but the list CRDT RGA timed out.
  - why: Shows where automatic proof stops: sets and maps work, the list merge our libraries depend on does not.
  - read depth: Only the verification results were read.
- `The Art of the Fugue- Minimizing Interleaving in Collaborative Text Editing, Matthew Weidner, Martin Kleppmann, arXiv, 2023.pdf`
  - shows: Defines "maximal non-interleaving" (two people typing at the same spot do not get their letters mixed) and proves on paper that FugueMax has it; many older algorithms fail it.
  - why: A concrete property we could state for the real libraries; the paper says a proof for Yjs was still in progress.
- `A highly-available move operation for replicated trees, Martin Kleppmann, Dominic P. Mulligan, Victor B. F. Gomes, Alastair R. Beresford, IEEE TPDS, 2021.pdf`
  - shows: A CRDT for moving subtrees, proved in Isabelle (2,495 proof lines) with Scala code extracted from the proof; the extracted code ran 9.5x slower than hand-written code.
  - why: Closest example of going from proof to running code for one hard merge rule, with cost numbers.
- `Collaborative Text Editing with Eg-walker- Better, Faster, Smaller, Joseph Gentle, Martin Kleppmann, arXiv, 2024.pdf`
  - shows: A newer text merge algorithm that replays edit history instead of storing CRDT state, measured against Automerge and Yjs; correctness is a paper proof plus random tests.
  - why: The merge algorithms keep changing, so a proof of today's library code aims at a moving target.
- `Peritext- A CRDT for Collaborative Rich Text Editing, Geoffrey Litt, Sarah Lim, Martin Kleppmann, Peter van Hardenberg, CSCW, 2022.pdf`
  - shows: A rich-text (bold, links) merge algorithm with a paper convergence proof and random tests; what users intend is argued by examples only.
  - why: Automerge and Loro ship rich text, and its spec is the unsettled part.
- `Met- Model Checking-Driven Explorative Testing of CRDT Designs and Implementations, Yuqi Zhang, Yu Huang, Hengfeng Wei, Xiaoxing Ma, JSEP, 2024.pdf`
  - shows: Model check a TLA+ design of a CRDT, then replay the checker's traces as tests on the real code (CRDT-Redis); found bugs in both design and code.
  - why: A cheaper middle route than a full code proof that could apply to the Rust libraries.
- `Byzantine Eventual Consistency and the Fundamental Limits of Peer-to-Peer Databases, Martin Kleppmann, Heidi Howard, arXiv, 2020.pdf`
  - shows: Paper proof that a replicated database can tolerate any number of misbehaving nodes exactly when its transactions are safe under merge (I-confluent).
  - why: Theory of when merging needs no consensus. Not about verifying code.
- `Certified Program Models for Eventual Consistency, Edgar Pek, Pranav Garg, Muntasir Raihan Rahman, Indranil Gupta, P. Madhusudan, preprint, 2015.pdf`
  - shows: Models the repair protocols of Dynamo-style stores as C programs and proves eventual consistency with VCC (about 6 person-months); the merge function is assumed correct.
  - why: It assumes exactly the part we want to prove.
- `Delta State Replicated Data Types, Paulo Sérgio Almeida, Ali Shoker, Carlos Baquero, arXiv, 2016.pdf`
  - shows: Defines delta CRDTs (send only small changes) with paper proofs of consistency.
  - why: Background for the sync side of Automerge and Yrs; only proved on paper.
- `Verifying Strong Eventual Consistency in δ-CRDTs, Taylor Blau, arXiv, 2020.pdf`
  - shows: A bachelor's thesis extending the Gomes 2017 Isabelle framework to state-based and delta CRDTs, for simple counters and sets.
  - why: Shows that framework extends to the delta sync style, for simple types only.
  - read depth: Read in part (long thesis).
- `Keep CALM and CRDT On, Shadaj Laddad, Conor Power, Mae Milano, Alvin Cheung, Natacha Crooks, Joseph M. Hellerstein, VLDB, 2022.pdf`
  - shows: A vision paper: use the CALM theorem to tell which reads of a CRDT are safe without coordination; no proofs, no system.
  - why: Only a reminder that CRDT guarantees cover updates, not reads.
- `Making CRDTs Byzantine Fault Tolerant, Martin Kleppmann, PaPoC, 2022.pdf`
  - shows: A short sketch of how to make CRDTs tolerate misbehaving nodes; the proof is left as future work.
  - why: Byzantine faults are out of scope for a first effort.

Added Nov 13 (Scholar, 2022+; abstract and introduction read):

- `Certified Mergeable Replicated Data Types, Vimala Soundarapandian, Adharsh Kamath, Kartik Nagar, KC Sivaramakrishnan, PLDI, 2022.pdf`
  - shows: Peepul, an F* library where efficient CRDT code (counters, sets, a queue and others) is verified against a specification with an SMT solver and extracted to OCaml for use in Irmin; goes beyond convergence to arbitrary specifications. "we present Peepul, a pragmatic approach to building and verifying efficient RDTs."
  - why: Verification of extracted, running code for list-like (queue) types with a cost report; closer to our need than model-level proofs, but no text CRDT and no Rust.
  - read depth: abstract, introduction and evaluation numbers only.
- `Type-Checking CRDT Convergence, George Zakhour, Pascal Weisenburger, Guido Salvaneschi, PLDI, 2023.pdf`
  - shows: Propel, a language whose type system proves the merge is commutative, associative and idempotent for concrete implementations; compared with four other tools, some of which time out. "Propel is able to automatically deduce the properties that are relevant for common CRDT implementations found in open-source libraries even in cases in which competitors timeout."
  - why: A route to proving the merge laws on real implementations in a Scala embedding; unclear whether it scales to the sequence CRDTs in Yrs, Loro and Automerge (not tested in the abstract).
  - read depth: abstract and introduction.
- `Synthesizing CRDTs from Sequential Data Types with Verified Lifting, Shadaj Laddad, Conor Power, Mae Milano, Alvin Cheung, Joseph M. Hellerstein, OOPSLA, 2022.pdf`
  - shows: Katara synthesizes CRDTs from a sequential type plus an ordering constraint, and verifies them automatically. "our synthesized CRDTs are fully, automatically verified, eliminating entire classes of common errors"
  - why: Gives a correctness definition for CRDTs based on a sequential reference, which could serve as the spec for a text CRDT; the paper's examples are small types, so text is not shown to be reachable.
  - read depth: abstract and introduction.
- `Sal- Multi-modal Verification of Replicated Data Types, Pranav Ramesh, Vimala Soundarapandian, KC Sivaramakrishnan, arXiv, 2026.pdf`
  - shows: A Lean workflow for state-based CRDTs and MRDTs with kernel-checked automation, SMT fallback, and counterexamples from property-based testing; 13 types verified. "69% of verification conditions are discharged by kernel-verified automation without SMT"
  - why: Most recent tool in the verified-CRDT line and uses Lean, which our own proof work might share; 13 types, none a text CRDT as far as the abstract says. It also notes RGA had "serious anomalies discovered after publication."
  - read depth: abstract and introduction (7 pages).
- `Approaches to Conflict-free Replicated Data Types, Paulo Sérgio Almeida, ACM Computing Surveys, 2024.pdf`
  - shows: A tutorial and survey of op-based, state-based, pure op-based and delta CRDTs, and what they require (commutativity is not required of all operations; mutators must be inflations). "clarifying some misconceptions which frequently occur"
  - why: One reference for the exact definitions we would need to state properties in; background, not a verification result.
  - read depth: abstract and introduction (36 pages).

## 2. SSO and logout

What I take from these 10: three measurement papers (Ghasemisharif 2022, Lamisa 2024, Calzavara 2021) show that sessions often survive logout or revocation on real sites, and Ghasemisharif 2022 is the only one about SSO. The formal SSO proofs (Fett et al. on OAuth 2.0 and on OpenID Connect) cover login only and say they leave out logout, expiry and revocation. None of them studies the case Harsha asked about, where some tabs get logged out and others do not.

- ★ `Towards Automated Auditing for Account and Session Management Flaws in Single Sign-On Deployments, Mohammad Ghasemisharif, Chris Kanich, Jason Polakis, IEEE S&P, 2022.pdf`
  - shows: A tool that logs into sites with Facebook login and tests what happens when the user revokes the app at Facebook: under 2% of sites react correctly and 67% still allow access 10 days later.
  - why: Closest to "how big is the problem" for SSO. Google and Apple login behaved the same in 99% of cases on a 50-site subset. It does not cover one tab staying logged in after logout in another.
- `Measuring Improper Token Invalidation in Real-World Web Logins, Kazi Farhat Lamisa, Concordia University MASc thesis, 2024.md` (inside the folder of the same name, `.md` and `.pdf`)
  - shows: A tool that tests whether tokens still work after logout or password reset on real sites: 85% of 520 sites tested keep JWTs valid after logout, and 9% of 5,642 keep session cookies valid.
  - why: Best numbers on logout not ending the session. It does not test SSO logout.
- `Measuring Web Session Security at Scale, Stefano Calzavara, Hugo Jonker, Benjamin Krumnow, Alvise Rabitti, Computers & Security, 2021.md` (inside the folder of the same name, `.md` and `.pdf`)
  - shows: A crawler logged into 6,124 top sites and logged out of 3,302; on 604 (18%) cookies still worked 5 minutes after logout, and on 471 (14%) still 10 days later.
  - why: The earlier baseline that Lamisa 2024 repeats. SSO is not tested. The introduction gives a slightly different count (469 sites, 8% of all 6,124).
- `NEBULA- A Language-Independent Specification for Opaque Rotating Refresh Tokens, Matteo Teodori, arXiv, 2026.pdf`
  - shows: A written spec of refresh-token rotation, reuse detection and revocation, with ten implementations passing the same 38 tests; the author says the guarantees are argued, not machine-verified.
  - why: A ready state machine for revocation and session lifetime that nobody has proved. Single author, new, not a study of deployments.
- `A Comprehensive Formal Security Analysis of OAuth 2.0, Daniel Fett, Ralf Küsters, Guido Schmitz, CCS, 2016.md` (inside the folder of the same name, `.md` and `.pdf`)
  - shows: A hand-written model of OAuth 2.0 and a manual proof of its login properties, after fixing four attacks found on the way.
  - why: The best-known OAuth proof says it models no token expiry, no revocation and no logout.
  - read depth: Proofs not read.
- `The Web SSO Standard OpenID Connect- In-Depth Formal Security Analysis and Security Guidelines, Daniel Fett, Ralf Küsters, Guido Schmitz, arXiv, 2017.pdf`
  - shows: The same authors' model and manual proof for OpenID Connect.
  - why: It says OIDC logout is not modelled and the model has no notion of time. Same gap as their OAuth paper.
  - read depth: Proofs not read.
- `Analyzing the BrowserID SSO System with Primary Identity Providers Using an Expressive Model of the Web, Daniel Fett, Ralf Küsters, Guido Schmitz, ESORICS, 2015.md` (inside the folder of the same name, `.md` and `.pdf`)
  - shows: A hand-written model of Mozilla BrowserID with a manual proof of login properties; found a real attack.
  - why: The only formal model here with logout in it, but only as a random event; nothing is proved about sessions ending. BrowserID is discontinued.
  - read depth: Read by keyword search.
- `Only as Strong as the Weakest Link- On the Security of Brokered Single Sign-On on the Web, Tommaso Innocenti, Louis Jannett, Christian Mainka, Maximilian Westers, Tobias Wich, IEEE S&P, 2025.md` (inside the folder of the same name, `.md` and `.pdf`)
  - shows: Black-box tests of SSO brokers such as Keycloak, Cognito and Firebase: 25% of SSO sites use one, and over 50 brokers had flaws affecting over 2,000 sites.
  - why: Login flow only. Useful for knowing which SSO software is widely used.
  - read depth: Abstract and introduction only.
- `Post-quantum XML and SAML Single Sign-On, Johannes Müller, Jan Oupický, PoPETs, 2024.md` (inside the folder of the same name, `.md` and `.pdf`)
  - shows: Post-quantum signatures and encryption added to SAML SSO in OpenSAML, with speed measurements.
  - why: About cryptography, not sessions. Skip for now.
  - read depth: Abstract and conclusion only.
- `RADIUS:UDP Considered Harmful, Sharon Goldberg, Miro Haller, Nadia Heninger, Mike Milano, Dan Shumow, Marc Stevens, Adam Suhl, USENIX Security, 2024.md` (inside the folder of the same name, `.md` and `.pdf`)
  - shows: A man-in-the-middle attack on the RADIUS network login protocol using an MD5 collision.
  - why: Not web SSO, no sessions or logout. Skip for now.
  - read depth: Abstract and introduction only.

Added Nov 13 (Scholar, 2022+; abstract and introduction read):

- `Evaluating Ongoing Access Attacks on the Web, Arkaprabha Bhattacharya, Rosanna Bellini, Thomas Ristenpart, Nicola Dell, CCS, 2026.pdf`
  - shows: A test on 20 popular services of whether an attacker who once had access keeps it after the victim follows the service's remediation guidance, over 75 access routes (11 types, including SSO and passkeys). "14 of these offer an access route that is irrevocable or not properly remediated by service-provided guidance, leaving adversarial access intact."
  - why: Newest measurement of "revocation does not actually revoke"; it includes session managers ("Log out of all other sessions"). It is manual (20 services), and the threat model is account monitoring in interpersonal abuse, not a single SSO deployment.
  - read depth: abstract and introduction.
- `Pre-hijacked accounts- An Empirical Study of Security Failures in User Account Creation on the Web, Avinash Sudhodanan, Andrew Paverd, USENIX Security, 2022.pdf`
  - shows: Five account pre-hijacking attacks that mix classic and SSO sign-up; of 75 services analysed, "at least 35" were vulnerable; some attacks depend on a service that "does not expire past sessions by default upon password reset" and on a recovery that does not invalidate active sessions (from the paper's assumptions table).
  - why: Gives a concrete cause of sessions surviving a credential change, in SSO-related flows; the paper is about account creation, so session invalidation is one cause among several.
  - read depth: abstract, introduction and Table 1.
- `SSO-Monitor- Fully-Automatic Large-Scale Landscape, Security, and Privacy Analyses of Single Sign-On in the Wild, Maximilian Westers, Tobias Wich, Louis Jannett, Vladislav Mladenov, Christian Mainka, Andreas Mayer, arXiv, 2023.pdf`
  - shows: An automatic crawler that finds and runs SSO logins (1,632 sites with Apple, Facebook or Google login in the Tranco top 10k) and finds CSRF, token-leak and privacy problems. "We show that this assumption is a fallacy." (that best practices are widely deployed)
  - why: Tooling to measure SSO at scale; a possible base for a logout or revocation test. A text search for "revoc" and "logout" in the paper finds nothing, so it does not itself test revocation.
  - read depth: abstract, introduction and results summary.
- `SoK- SSO-Monitor - The Current State and Future Research Directions in Single Sign-On Security Measurements, Louis Jannett, Maximilian Westers, Tobias Wich, Christian Mainka, Andreas Mayer, Vladislav Mladenov, IEEE, 2024.pdf`
  - shows: Surveys 36 SSO measurement tools, finds gaps, and presents an extended SSO-Monitor at 93% detection accuracy. "We observe unreliable measurements and a lack of reproducibility, making comparisons between studies difficult, if not impossible."
  - why: Map of what SSO measurements exist and where they are weak; useful before designing any revocation measurement. Venue in the file name is only "IEEE, 2024": I did not confirm the exact venue from the PDF.
  - read depth: abstract and introduction.

## 3. Shared process and isolation

What I take from these 21: no paper isolates many sessions inside one JS engine process with a proof. Proofs exist for one sandbox staying inside its own memory (the LFI verifier proof, VeriWasm, vWasm, VeriZero, RockSalt) and for tab isolation when each tab has its own process (Quark). Systems that pack many sandboxes into one process (LFI, TME-Box, Swivel) have no proofs. Spectre breaks in-process tenant isolation in practice (Dynamic Process Isolation), and no proof here covers it.

- ★ `Establishing Browser Security Guarantees through Formal Shim Verification, Dongseok Jang, Zachary Tatlock, Sorin Lerner, USENIX Security, 2012.pdf`
  - shows: Quark: a browser whose small kernel is written and proved in Coq, including that no tab can affect how the kernel treats another tab, and cookie isolation by domain.
  - why: Closest prior proof that sessions cannot see each other's data. Its isolation comes from one OS process per tab, and timing channels are excluded.
- ★ `Dynamic Process Isolation, Martin Schwarzl, Pietro Borrello, Andreas Kogler, Kenton Varda, Thomas Schuster, Daniel Gruss, Michael Schwarz, arXiv, 2021.pdf`
  - shows: A measured Spectre attack leaking 120 bits per hour across tenants inside Cloudflare Workers (many tenants' JavaScript in one process), plus a defense that moves suspicious tenants to their own process.
  - why: Direct evidence that many tenants in one JS process leak through Spectre, so our design needs a side-channel story.
- `Site Isolation is Dead- How Site Isolation is Broken in Agentic Browsers and Extensions, Suyoung Lee, Seongho Keum, Changoo Lee, Dongwon Shin, Sanghyun Hong, Byoungyoung Lee, Sooel Son, IEEE S&P, 2026.pdf`
  - shows: A compromised page process in 2 agentic browsers and 7 agent extensions can forge prompts to the agent and read its stored keys and chat history over IPC; all 9 were vulnerable.
  - why: The only paper on agent browsers. A guarantee for agent sessions must cover the agent's message channels, not just memory.
- `Mohabi- Disaggregating and Sandboxing the Firefox JavaScript Engine, Abhishek Sharma, Anand Balaji, Zachary Yedidia, et al., Deian Stefan, Hovav Shacham, Shravan Narayan, OSDI, 2026.pdf`
  - shows: Mohabi: Firefox's whole JS engine, JIT output included, runs inside an SFI sandbox at about 25% cost on JS benchmarks; one sandbox per content process.
  - why: Sandboxing a production JS engine is feasible, but it protects the browser from the engine, not sessions from each other, and nothing is proved.
- `Automated Formal Verification of a Software Fault Isolation System, Matthew Sotoudeh, Zachary Yedidia, FMCAD, 2025.pdf`
  - shows: An SMT proof that programs accepted by the real LFI verifier never read or write outside their sandbox, checked against the official ARM64 instruction model in about 20 hours of compute.
  - why: A mostly automatic proof for a real SFI verifier. The runtime and anything between sessions are not covered.
- `Lightweight Fault Isolation- Practical, Efficient, and Secure Software Sandboxing, Zachary Yedidia, ASPLOS, 2024.pdf`
  - shows: LFI: an SFI system for ARM64 that fits about 65,000 sandboxes of 4 GiB in one address space at 7% overhead, with a small machine-code verifier.
  - why: Strongest answer on "many sandboxes in one process". No JS engine integration; the proof of its verifier came later (Sotoudeh and Yedidia 2025).
- `Доверя́й, но проверя́й- SFI safety for native-compiled Wasm, Evan Johnson, David Thien, Yousef Alhessi, Shravan Narayan, et al., Stefan Savage, Deian Stefan, NDSS, 2021.pdf`
  - shows: VeriWasm: a checker for the x86 output of the Lucet Wasm compiler, with a Coq soundness proof on a model; tested on 103 real Fastly client binaries.
  - why: A deployed case of many tenants in one process where the compiler need not be trusted. The tool's Rust code and Spectre are not covered.
- `Provably-Safe Multilingual Software Sandboxing using WebAssembly, Jay Bosamiya, Wen Shih Lim, Bryan Parno, USENIX Security, 2022.pdf`
  - shows: Two Wasm compilers: vWasm, proved in F* to keep code inside its sandbox, and rWasm, which emits safe Rust so the Rust compiler gives the guarantee.
  - why: A machine-checked sandbox proof exists, but the property is "stays in its sandbox", not "tenants cannot observe each other".
- `Isolation Without Taxation- Near-Zero-Cost Transitions for WebAssembly and SFI, Matthew Kolosick, Shravan Narayan, Evan Johnson, Conrad Watt, Michael LeMay, Deepak Garg, Ranjit Jhala, Deian Stefan, POPL, 2022.pdf`
  - shows: Makes calls into a Wasm sandbox as cheap as plain function calls, and proves on a formal model that a checker (VeriZero) guarantees this is safe.
  - why: A proof style for sandbox boundaries we may reuse; it covers one sandbox against its host.
  - read depth: Proof appendix not in the text.
- `Swivel- Hardening WebAssembly against Spectre, Shravan Narayan, Craig Disselkoen, Daniel Moghimi, Sunjay Cauligi, Evan Johnson, Zhao Gang, Anjo Vahldiek-Oberwagner, Ravi Sahita, Hovav Shacham, Dean Tullsen, Deian Stefan, USENIX Security, 2021.pdf`
  - shows: Swivel: compiler changes that stop Spectre attacks between Wasm sandboxes in one process, at under 10.3% cost for its randomized versions.
  - why: In-process Wasm tenants need extra Spectre defenses and these can be cheap; argued and tested, not proved.
- `TME-Box- Scalable In-Process Isolation through Intel TME-MK Memory Encryption, Martin Unterguggenberger, Lukas Lamster, David Schrammel, Martin Schwarzl, Stefan Mangard, NDSS, 2025.pdf`
  - shows: TME-Box: uses Intel memory encryption keys to isolate up to 32,000 sandboxes in one process at 5 to 10% overhead.
  - why: Hardware can give many in-process domains. No proof, Spectre out of scope, JIT code not handled.
- `Donky- Domain Keys – Efficient In-Process Isolation for RISC-V and x86, David Schrammel, Samuel Weiser, Stefan Steinegger, Martin Schwarzl, Michael Schwarz, Stefan Mangard, Daniel Gruss, USENIX Security, 2020.pdf`
  - shows: Donky: user-mode switching between memory domains, used to put each V8 isolate in its own domain at 0 to 2% overhead; 1,024 domains on RISC-V but 16 on x86.
  - why: Closest hardware design to one V8 isolate per tenant. Stops at 16 domains on x86 and has no proof.
- `Site Isolation- Process Separation for Web Sites within the Browser, Charles Reis, Alexander Moshchuk, Nasko Oskov, USENIX Security, 2019.pdf`
  - shows: Chrome's Site Isolation: one renderer process per site, deployed to all desktop users at 9 to 13% memory overhead.
  - why: The baseline our one-process design gives up; the authors chose processes partly because of Spectre.
- `RockSalt- Better, Faster, Stronger SFI for the x86, Greg Morrisett, Gang Tan, Joseph Tassarotti, Jean-Baptiste Tristan, Edward Gan, PLDI, 2012.pdf`
  - shows: RockSalt: a Native Client SFI checker proved correct in Coq against a Coq model of 32-bit x86.
  - why: The classic proof that a checker enforces memory isolation, and a view of how much work a machine model takes.
- `ERIM- Secure, Efficient In-process Isolation with Protection Keys (MPK), Anjo Vahldiek-Oberwagner, Eslam Elnikety, Nuno O. Duarte, Michael Sammler, Peter Druschel, Deepak Garg, USENIX Security, 2019.pdf`
  - shows: ERIM: isolates a trusted part of a process with Intel protection keys at under 1% overhead for 100,000 switches per second.
  - why: Cost baseline for MPK. The 16-domain cap and the need to scan code make it a poor fit for many sessions with a JIT.
- `Retrofitting Fine Grain Isolation in the Firefox Renderer, Shravan Narayan, Craig Disselkoen, Tal Garfinkel, Nathan Froyd, Eric Rahm, Sorin Lerner, Hovav Shacham, Deian Stefan, USENIX Security, 2020.pdf`
  - shows: RLBox: a C++ framework that sandboxes Firefox's third-party libraries, shipped in production.
  - why: Shows that checking data crossing the sandbox boundary is the main engineering risk. It isolates libraries, not sessions.
- `Hodor- Intra-Process Isolation for High-Throughput Data Plane Libraries, Mohammad Hedayati, Spyridoula Gravani, Ethan Johnson, John Criswell, Michael L. Scott, Kai Shen, Mike Marty, USENIX ATC, 2019.pdf`
  - shows: Hodor: gives distrusting libraries separate domains in one process with MPK, at 90 to 98% of unprotected throughput.
  - why: MPK allows at most 7 mutually distrusting libraries here. No proof.
- `The Multi-Principal OS Construction of the Gazelle Web Browser, Helen J. Wang, Chris Grier, Alexander Moshchuk, Samuel T. King, Piali Choudhury, Herman Venter, USENIX Security, 2009.pdf`
  - shows: Gazelle: a 2009 browser built like an OS, with a small kernel and one process per site.
  - why: Origin of the browser kernel idea. Uses processes, no proof.
- `Trust and Protection in the Illinois Browser Operating System, Shuo Tang, Haohui Mai, Samuel T. King, OSDI, 2010.pdf`
  - shows: IBOS: a 2010 browser OS on a microkernel with about 42K lines of trusted code.
  - why: Argues a small trusted core makes verification possible, but does not do it.
- `Native Client- A Sandbox for Portable, Untrusted x86 Native Code, Bennet Yee, David Sehr, Gregory Dardyk, J. Bradley Chen, Robert Muth, Tavis Ormandy, Shiki Okasaka, Neha Narula, Nicholas Fullagar, IEEE S&P, 2009.pdf`
  - shows: Native Client: runs untrusted 32-bit x86 modules in the browser using segments and a code validator, at about 5% overhead.
  - why: Historical background for the checker approach.
- `Efficient Software-Based Fault Isolation, Robert Wahbe, Steven Lucco, Thomas E. Anderson, Susan L. Graham, SOSP, 1993.pdf`
  - shows: The original 1993 SFI paper: rewrite a module's machine code so it stays in its own region, at about 4% slowdown.
  - why: Historical background. Its default mode protects writes and jumps only, not reads.

Added Nov 13 (Scholar, 2022+; abstract and introduction read):

- `Empirical Security Analysis of Software-based Fault Isolation through Controlled Fault Injection, Nils Bars, Lukas Bernhard, Moritz Schloegel, Thorsten Holz, CCS, 2025.pdf`
  - shows: SbxBrk, a fuzzer that corrupts data read from the V8 heap sandbox to test the trust boundary; "We found 19 security bugs in the V8 code" (in the text). The paper notes that V8 is also used by Node.js, Electron and Cloudflare's workerd.
  - why: Direct evidence that V8's in-process isolation, which multi-tenant JS hosts lean on, is still being broken; the in-process boundary is not proof-backed.
  - read depth: abstract and introduction.
- `SandDriller- A Fully-Automated Approach for Testing Language-Based JavaScript Sandboxes, Abdullah AlHamdan, Cristian-Alexandru Staicu, USENIX Security, 2023.pdf`
  - shows: Dynamic testing of language-based sandboxes (vm2, SES and others) that found 8 unique zero-day sandbox escapes; "we report 13 distinct security problems" across them; says Cloudflare uses such techniques for resource sharing.
  - why: Shows how breakable same-process JS sandboxes are in practice, which bears on putting many tenants in one JS process.
  - read depth: abstract and introduction.
- `SandVenture- Escaping JavaScript Sandboxes with Objective-driven Input Generation, Mingi Jung, Hyeon Heo, Seongil Wi, IEEE EuroS&P, 2026.pdf`
  - shows: A newer fuzzer for JS sandboxes. "SandVenture successfully discovered 85 sandbox-escaping bugs, including four CVEs, in 11 sandboxes." It finds 31% more unique bugs than SandDriller under the same conditions.
  - why: Updates SandDriller with a larger bug count; read the two together.
  - read depth: abstract and introduction.
- `Are your Sites Truly Isolated- Automatically Detecting Logic Bugs in Site Isolation Implementations, Jan Drescher, David Klein, Martin Johns, NDSS, 2026.pdf`
  - shows: The first automatic search for Site Isolation bypasses in Chrome and Firefox, using a compromised-renderer IPC fuzzer and leak oracles. "Our work uncovered four security vulnerabilities in Chrome and Firefox"
  - why: Process-per-site is the main alternative to many tenants in one process, and it also has logic bugs at the browser-process boundary; complements Site Isolation papers already in READING.md.
  - read depth: abstract and introduction.
- `NatiSand- Native Code Sandboxing for JavaScript Runtimes, Marco Abbadini, Dario Facchinetti, Gianluca Oldani, Matthew Rossi, Stefano Paraboschi, RAID, 2023.pdf`
  - shows: A Deno component using Landlock, eBPF and seccomp to confine native programs and libraries that JS runtimes run. "no isolation guarantees are provided" for binaries and shared libraries in Node.js, Deno and Bun today.
  - why: Shows the gap where JS-level isolation ends (native code), and an OS-level fix with measured overhead (I did not read the overhead numbers).
  - read depth: abstract and introduction.
- `Hierarchical Integration of WebAssembly in Serverless for Efficiency and Interoperability, Mohammadamin Baqershahi, Changyuan Lin, Visal Saosuo, Paul Chen, Mohammad Shahrad, NSDI, 2026.pdf`
  - shows: Wasabi packs different customers' Wasm workloads into the same container sandbox for density, with resource-aware scaling and overbooking. "Language runtimes such as WebAssembly (Wasm) can reduce isolation overhead without compromising security."
  - why: A current example of the density-versus-isolation trade for multi-tenant serverless using language-level isolation; Wasm rather than JS.
  - read depth: abstract and introduction.

## 4. JavaScript semantics

What I take from these 24: full-language JS semantics in a prover or in K stop at ES5 (2009). The only prover work on a recent edition covers regular expressions (Warblre). The one line that follows the yearly standard automatically is KAIST's (JISET, ESMeta, JEST, JSTAR), and it does testing and type checking, not proofs. Nobody here proves anything about a real engine except Icarus, which covers a rewritten part of Firefox's JIT. WebAssembly (the WasmCert-Coq thesis) shows what a proved and maintained semantics looks like.

- ★ `JavaScript Language Design and Implementation in Tandem, Sukyoung Ryu, Jihyeok Park, CACM, 2024.pdf`
  - shows: A short overview of ESMeta: it extracts an executable spec from the standard's text each year and has run in the standard's own CI since 2022; its tools found 44 engine bugs and 27 spec bugs.
  - why: The quickest way into the only approach that keeps up with the yearly standard. It gives tests, not proofs.
  - read depth: The extracted text was garbled; read the PDF.
- `JISET- JavaScript IR-based Semantics Extraction Toolchain, Jihyeok Park, Jihee Park, Seungmin An, Sukyoung Ryu, ASE, 2020.pdf`
  - shows: JISET: builds a parser and an executable semantics from the ECMAScript text for ES7 to ES10; about 95% of the algorithm steps compile automatically and it passed all 18,064 applicable Test262 tests.
  - why: The base a JS semantics for us would most likely start from. About half of Test262 was excluded (non-strict mode, modules, many built-ins).
- `A Trusted Mechanised JavaScript Specification, Martin Bodin, Arthur Charguéraud, Daniele Filaretti, Philippa Gardner, Sergio Maffeis, Daiva Naudžiūnienė, Alan Schmitt, Gareth Smith, POPL, 2014.pdf`
  - shows: JSCert: a Coq model of the core of ES5, plus an interpreter proved correct against it; passes 1,796 of 2,782 core tests.
  - why: The baseline for a trusted spec in a prover. ES5 only and incomplete.
  - read depth: Coq rule sections not read.
- `KJS- A Complete Formal Semantics of JavaScript, Daejun Park, Andrei Ştefănescu, Grigore Roşu, PLDI, 2015.pdf`
  - shows: KJS: an executable ES5.1 semantics in the K framework that passes all 2,782 core tests, found engine bugs, and verified small programs.
  - why: A complete ES5 semantics with a program verifier is feasible. Nothing on ES6 or later.
- `A Coq Mechanization of JavaScript Regular Expression Semantics, Noé De Santo, Aurèle Barrière, Clément Pit-Claudel, ICFP, 2024.pdf`
  - shows: Warblre: a line-by-line Coq translation of the regex chapter of ES2023, with proofs that matching terminates; passes 495 of 498 regex tests.
  - why: The only prover work on a recent edition, and it claims an update costs about as much as the spec change. Regexes only.
- `Icarus- Trustworthy Just-In-Time Compilers with Symbolic Meta-Execution, Naomi Smith, Abhishek Sharma, John Renner, David Thien, et al., Ranjit Jhala, Deian Stefan, SOSP, 2024.pdf`
  - shows: Icarus: parts of Firefox's JIT (inline cache generators) rewritten in a DSL and checked by a solver, so that every stub the JIT could generate is safe; it caught 6 real past bugs.
  - why: Proof-level JIT verification exists, for a small rewritten subset, and it uses no JS semantics. Bears on Ramesh's remark that JIT proofs may be in scope.
- `Designing and Maintaining an Efficient WebAssembly Mechanisation, Xiaojia Rao, Imperial College London PhD thesis, 2025.pdf`
  - shows: A thesis on WasmCert-Coq: a Coq model of Wasm kept up to date from 1.0 to 2.0, whose extracted interpreter passes the official tests, plus a program logic.
  - why: What "feasible" looks like for a much smaller language. It says keeping up with the spec "remains a demanding task".
  - read depth: Chapters 2 to 5 not read.
- `A Trusted Infrastructure for Symbolic Analysis of Event-based Web APIs, Gabriela Cunha Sampaio, Imperial College London PhD thesis, 2022.pdf`
  - shows: A thesis that models DOM events, Promises, WebMessaging and WebWorkers on top of the JaVerT tool and finds six bugs in three libraries.
  - why: The closest work on web APIs next to a JS semantics. Hand-built and limited to ES5.
  - read depth: Chapters 2 to 5 not read in detail.
- `A Formal Semantics of the Core DOM in Isabelle-HOL, Achim D. Brucker, Michael Herzberg, WWW Companion, 2018.pdf`
  - shows: A model of the DOM node tree in Isabelle, with proofs that the main operations are correct and keep the tree well formed.
  - why: The only machine-checked DOM model here. It says linking to real browser code is its most important future work.
- `JEST- N+1-version Differential Testing of Both JavaScript Engines and Specification, Jihyeok Park, Seungmin An, Dongjun Youn, Gyeongwon Kim, Sukyoung Ryu, ICSE, 2021.pdf`
  - shows: JEST: generates test programs from the extracted ES11 semantics and runs them on four engines; found 44 engine bugs and 27 spec bugs.
  - why: Shows the standard itself has bugs and that an extracted spec works as a reference answer for engine testing, which we could do for Boa.
- `Translation Validation for JIT Compiler in the V8 JavaScript Engine, Seungwan Kwon, Jaeseong Kwon, Wooseok Kang, Juneyoung Lee, Kihong Heo, ICSE, 2024.pdf`
  - shows: TurboTV: a solver-based checker that validates single compilations of V8's TurboFan; it covers 306 of 914 operators and found all 9 known bugs in its benchmark.
  - why: Partial JIT checking works; it found no new V8 bug.
- `JaVerT 2.0- Compositional Symbolic Execution for JavaScript, José Fragoso Santos, Petar Maksimović, Gabriela Sampaio, Philippa Gardner, POPL, 2019.pdf`
  - shows: JaVerT 2.0: a symbolic execution tool for ES5 Strict programs with paper soundness proofs; found a bug in a real library.
  - why: Program analysis works on ES5 Strict; ES6 would need more.
- `Gillian, Part I- A Multi-language Platform for Symbolic Execution, José Fragoso Santos, Petar Maksimović, Sacha-Élie Ayoun, Philippa Gardner, PLDI, 2020.pdf`
  - shows: Gillian: a symbolic execution platform that takes the memory model as a parameter, with JS (ES5 Strict) and C instances.
  - why: Reusable infrastructure if we wrote a newer JS front end.
- `Formal Verification for JavaScript Regular Expressions- A Proven Mechanized Semantics and Its Applications (Extended Version), Aurèle Barrière, Victor Deng, Clément Pit-Claudel, POPL, 2026.pdf`
  - shows: A shorter regex semantics in Rocq, proved equivalent to Warblre, used to check regex rewrites and to prove the PikeVM matching algorithm.
  - why: Shows the second layer we would need: a faithful model plus a model that is easy to prove with.
- `JSTAR- JavaScript Specification Type Analyzer using Refinement, Jihyeok Park, Seungmin An, Wonho Shin, Yusung Sim, Sukyoung Ryu, ASE, 2021.pdf`
  - shows: JSTAR: a type analysis over the extracted spec that found 93 real type bugs in the standard, with about 40% false alarms.
  - why: The standard's text is a shaky foundation on its own.
  - read depth: Text was garbled; conclusion not found.
- `ECMA-SL - A Platform for Specifying and Running the ECMAScript Standard, Luís Miguel Alves Loureiro, IST MSc thesis, 2021.pdf`
  - shows: ECMA-SL: an ES5.1 reference interpreter that follows the standard line by line and passes 12,026 of 12,068 applicable tests; no proofs.
  - why: Has a useful table comparing earlier semantics by tests passed. Its JISET number (62.4% of ES10 tests) differs from the JISET paper's own claim; I did not resolve this.
  - read depth: Implementation chapters not read.
- `Utilising and Scaling the WebAssembly Semantics (Dagstuhl Seminar 25241), Amal Ahmed, Andreas Rossberg, Deian Stefan, Conrad Watt, Michelle Thalakottur, Dagstuhl Reports, 2025.pdf`
  - shows: Notes from a 2025 seminar on Wasm semantics: who works on what, and open problems.
  - why: A cheap map of Wasm verification and its main risk, the formal spec falling behind.
- `A Typed Intermediate Language for Specifying the ECMAScript Standard, André Filipe Ferreira do Nascimento, IST MSc thesis, 2023.pdf`
  - shows: Adds static types to ECMA-SL; says the last version it supports is ES6 (2015).
  - why: A direct statement that keeping a hand-written interpreter current is the open problem.
  - read depth: Abstract, contributions and conclusion only.
- `Implementation-Based Generation of the ECMAScript Standard, Patrícia Alexandra Ferreira Pereira, IST MSc thesis, 2024.pdf`
  - shows: Generates the HTML of the standard from the ECMA-SL interpreter; reports 92% of ES6 tests passed.
  - why: Same ECMA-SL line as the two theses above. Its related-work table looks wrong in places.
  - read depth: Abstract, one section and conclusion only.
- `Optimization-Directed Compiler Fuzzing for Continuous Translation Validation, Jaeseong Kwon, Bongjun Jang, Juneyoung Lee, Kihong Heo, PLDI, 2025.pdf`
  - shows: Optimuzz: a fuzzer aimed at chosen compiler optimizations; found 55 new LLVM bugs but only reproduced 4 known TurboFan bugs.
  - why: Weak evidence for JS JITs.
- `On the computational complexity of JavaScript regex matching, in Rocq, Victor Deng, Aurèle Barrière, Clément Pit-Claudel, arXiv, 2026.pdf`
  - shows: Rocq proofs about how hard JS regex matching is (PSPACE-complete in one setting).
  - why: Off our path. Porting to ES2025 is left to future work, a sign that updates lag.
- `Featherweight Firefox- Formalizing the Core of a Web Browser, Aaron Bohannon, Benjamin C. Pierce, WebApps, 2010.pdf`
  - shows: A 2010 paper model of a browser core (windows, DOM, cookies, a toy script language) with no proofs.
  - why: A reference for what a browser model must include.
- `Local Hoare Reasoning about DOM, Philippa A. Gardner, Gareth D. Smith, Mark J. Wheelhouse, PODS, 2008.pdf`
  - shows: A 2008 paper logic for a small part of DOM tree updates.
  - why: Background. It found holes in the DOM standard.
- `Bullseye- Detecting Prototype Pollution in NPM Packages with Proof of Concept Exploits, Tariq Houis, Shaoqi Jiang, Mohammad Mannan, Amr Youssef, NDSS, 2026.pdf`
  - shows: Runs npm packages' tests with attack inputs and found prototype pollution in 290 packages.
  - why: Library bugs above the engine. Off target for us.
  - read depth: Abstract and introduction only.

## 5. Distributed-systems outages and verification

What I take from these 17: in industry, model checking a design (AWS 2014, Cosmos DB) and tying the model to real code by replaying logs (Smart Casual Verification) are what found bugs at a cost of a few person-months. Full proofs of real distributed code remain expensive, and AutoMan is the newest attempt to cut that cost. Config changes are a large outage class where testing already catches most known cases (Ctests). Stated open problems are liveness, scale beyond a few nodes, models drifting from code (the consensus survey), and slow performance collapse (AWS 2014).

- ★ `Smart Casual Verification of the Confidential Consortium Framework, Heidi Howard, Markus A. Kuppe, Edward Ashton, Amaury Chamayou, Natacha Crooks, NSDI, 2025.pdf`
  - shows: For the system under Azure Confidential Ledger, TLA+ specs of its Raft variant were model checked and tied to the C++ code by replaying logs against the spec; six bugs found before production.
  - why: The most complete recent example of linking a model to real distributed code, at about 2 engineer-months for the consensus part.
- `Use of Formal Methods at Amazon Web Services, Chris Newcombe, Tim Rath, Fan Zhang, Bogdan Munteanu, Marc Brooker, Michael Deardeuff, technical report, 2014.pdf`
  - shows: AWS used TLA+ on the designs of S3, DynamoDB and EBS and found bugs in each; engineers learned it in 2 to 3 weeks.
  - why: The classic case for model checking designs. It names a class it cannot model: sustained performance degradation.
- `Understanding Inconsistency in Azure Cosmos DB with TLA+, A. Finn Hackett, Joshua Rowe, Markus Alexander Kuppe, ICSE-SEIP, 2023.pdf`
  - shows: A small TLA+ model of what clients can observe from Cosmos DB at each consistency level; it explained the root cause of a past Azure outage. About 2 person-months.
  - why: A spec of user-visible behaviour, not of the implementation, can prevent outages in services that depend on it.
- `AutoMan- Facilitating Verified Distributed Systems Development Through Automatic Code Generation and Manual Optimizations, Zihao Zhang, Ti Zhou, Christa Jenkins, Omar Chowdhury, Shuai Mu, SOSP, 2025.pdf`
  - shows: AutoMan: generates implementation code and proof obligations from a TLA spec, with hand optimization of hot paths; applied to Multi-Paxos, PBFT and a key-value store.
  - why: Attacks the main cost of verified distributed code. It still needs a hand-written spec and does not cover shared-state concurrency.
- `Testing Configuration Changes in Context to Prevent Production Failures, Xudong Sun, Runxiang Cheng, Jianyan Chen, Elaine Ang, Owolabi Legunsen, Tianyin Xu, OSDI, 2020.pdf`
  - shows: Ctests: turn a system's existing tests into tests of a configuration change; caught 96.9% of 64 real failures in five cloud systems.
  - why: Sizes the config-change outage class and sets the bar a formal approach must beat.
- `Systematization of Knowledge- Formal Verification of Consensus Protocols, Nikita Bondarev, Kirill Ziborov, Yury Yanovich, arXiv, 2026.pdf`
  - shows: A survey of over 20 verified consensus protocols and their gaps.
  - why: A quick list of open problems: liveness, scale beyond 4 to 10 nodes, models that differ from the Go or Rust code. Blockchain-focused.
- `Uncovering Bugs in Distributed Storage Systems during Testing (Not in Production!), Pantazis Deligiannis, Matt McCutchen, Paul Thomson, et al., Shaz Qadeer, Wolfram Schulte, FAST, 2016.pdf`
  - shows: P#: Azure engineers tested real storage code under systematically explored interleavings and failures; 8 serious bugs found.
  - why: A testing baseline on real code that any verification proposal should beat.
- `Lessons from the evolution of the Batfish configuration analysis tool, Matt Brown, Ari Fogel, Daniel Halperin, Victor Heorhiadi, Ratul Mahajan, Todd Millstein, SIGCOMM, 2023.pdf`
  - shows: Lessons from Batfish, a tool that simulates router configurations to check network policies.
  - why: A verification tool with real users. Its accuracy problems come from the many config features, not from software bugs.
- `Semantic-based Automated Reasoning for AWS Access Policies using SMT, John Backes, Pauline Bolignano, Byron Cook, Catherine Dodge, Andrew Gacek, Kasper Luckow, Neha Rungta, Oksana Tkachuk, Carsten Varming, FMCAD, 2018.pdf`
  - shows: Zelkova: turns AWS access policies into solver formulas to decide who can access what; called millions of times a day.
  - why: Verification at very large scale, on policies, not on service code.
- `Kani- A Model Checker for Rust, Remi Delmas et al., arXiv, 2026.pdf`
  - shows: Kani: a bounded model checker for real Rust code, used in CI on Firecracker and the Rust standard library; found six unknown bugs.
  - why: A low-effort way to check real Rust. It checks local properties, not protocols.
- `Lessons from Building an Auto-Active Verifier in Lean, George Pîrlea, Vladimir Gladshtein, Qiyuan Zhao, Ilya Sergey, Dafny Workshop, 2026.pdf`
  - shows: A short talk paper on Veil, a verifier for distributed protocols built inside Lean; more than 10x slower than Ivy.
  - why: A tool we might use. It reports no bugs found.
- `Applying Formal Verification to Microkernel IPC at Meta, Quentin Carbonneaux, Noam Zilberstein, Christoph Klee, Peter W. O'Hearn, Francesco Zappa Nardelli, CPP, 2022.pdf`
  - shows: Two Meta engineers proved two lock-free queues correct in Coq/Iris on a pseudocode model, in person-months.
  - why: A cost data point. Single machine.
- `Continuous Formal Verification of Amazon s2n, Andrey Chudnov, Nathan Collins, Byron Cook, Joey Dodds, Brian Huffman, Colm MacCárthaigh, Stephen Magill, Eric Mertens, Eric Mullen, Serdar Tasiran, Aaron Tomb, Eddy Westbrook, CAV, 2018.pdf`
  - shows: Automatic proofs of the real C code of AWS's TLS library run on every commit; 3 manual proof updates were needed in a year.
  - why: Proofs can survive code change when they are automatic and the spec is stable. Not a distributed system.
- `VeriSMo- A Verified Security Module for Confidential VMs, Ziqiao Zhou, Anjali, Weiteng Chen, Sishuai Gong, Chris Hawblitzel, Weidong Cui, OSDI, 2024.pdf`
  - shows: VeriSMo: a Rust security module for confidential VMs proved in Verus against a hostile hypervisor.
  - why: Verus handles real systems Rust at thousands of lines. Single node.
- `3DGen- AI-Assisted Generation of Provably Correct Binary Format Parsers, Sarah Fakhoury, Markus Kuppe, Shuvendu K. Lahiri, Tahina Ramananandro, Nikhil Swamy, arXiv, 2024.pdf`
  - shows: 3DGen: LLM agents write format specs from RFC text and a verified toolchain produces C parsers; tried on 20 formats.
  - why: AI can ease spec writing but is only as good as its tests. Parsers only.
- `Configuration Validation with Large Language Models, Xinyu Lian, Yinfang Chen, Runxiang Cheng, Jie Huang, Parth Thakkar, Minjia Zhang, Tianyin Xu, arXiv, 2023.pdf`
  - shows: Ciri: asks LLMs to check config files; caught 33 to 45 of 51 real misconfigurations.
  - why: Fast screening with no guarantee.
- `Making Deployments Safe at Meta- Health Checks for Continuous Change-Safety, Prakash KL, Anton Korenkov, Uttam Thakore, Christopher Hegre, arXiv, 2026.pdf`
  - shows: Meta's health checker gates every code and config change during rollout; false alarms were cut from 12.1% to 2.7%.
  - why: Describes the bad-change outage class. Monitoring, not verification.

## 6. Sync protocols' liveness under message loss

Added Nov 13. Performal and the Aneris reliable-network paper also verify real code, so they count under group 5 too. Scholar searches for group 5 found nothing new outside the collection.

- `Mostly Automated Verification of Liveness Properties for Distributed Protocols with Ranking Functions, Jianan Yao, Runzhou Tao, Ronghui Gu, Jason Nieh, POPL, 2024.pdf`
  - shows: LVR reduces liveness of distributed protocols to safety by synthesizing ranking functions; verified several protocols including versions of Paxos with limited user guidance, at 128 and 165 lines of manual input for sliding window and multi-Paxos. "most liveness properties for distributed protocols can be reduced to a set of safety properties with the help of ranking functions"
  - why: Sliding window is a retransmission-style protocol close to a sync protocol under loss; it works on protocol models, not on code, and I did not check how loss is modelled.
  - read depth: abstract, introduction and the effort numbers.
- `Verifying Reliable Network Components in a Distributed Separation Logic with Dependent Separation Protocols, Léon Gondelman, Jonas Kastberg Hinrichsen, Mário Pereira, Amin Timany, Lars Birkedal, ICFP, 2023.pdf`
  - shows: A Coq-verified reliable communication library over UDP (handshake, retransmission, acknowledgement) in Aneris, used under an RPC library and a replicated key-value store. "Our library is implemented in an OCaml-like language on top of UDP and features characteristic traits of existing protocols"
  - why: The most direct example of verified code that turns lossy delivery into reliable delivery, which a CRDT sync layer relies on. The paper states network communication is unreliable (dropped, reordered, duplicated). It proves safety-style specifications; I saw no liveness theorem for retransmission (the word appears only as a cited topic).
  - read depth: abstract and introduction.
- `Performal- Formal Verification of Latency Properties for Distributed Systems, Tony Nuda Zhang, Upamanyu Sharma, Manos Kapritsos, PLDI, 2023.pdf`
  - shows: Proves upper bounds on latency of real implementations (distributed lock, ZooKeeper, a MultiPaxos RSM) in the IronFleet style; proof sizes 406 lines for the lock and 1,429 (no failure) to 4,666 (with failure) for IronRSL. "rigorous upper bounds for the latency of three applications"
  - why: Bounded time to deliver is a stronger form of liveness; its failure model and proof cost are a guide for what proving "eventually synced" on real code might cost. Also fits direction 5.
  - read depth: abstract, introduction and proof sizes.

## 7. Breadth directions (out/vlm46_breadth/REPORT.md)

Added Nov 13; abstract-level reading only. Empty subsections mean Scholar found no peer-reviewed paper; REPORT.md's "no proof exists" claims stay unconfirmed.

### 7.1. Raft membership reconfiguration

- `Adore- Atomic Distributed Objects with Certified Reconfiguration, Wolf Honoré, Ji-Yong Shin, Jieung Kim, Zhong Shao, PLDI, 2022`
  - shows: an abstract model (Adore) for Paxos/Raft-style protocols with first-class reconfiguration, and a Coq proof of safety. "we completed the first mechanized proof of safety of a reconfigurable consensus protocol"
  - why: the closest machine-checked statement of reconfiguration safety; it is protocol-level, so the gap to real Rust code (openraft) is the open part.
  - read depth: abstract only
- `Smart Casual Verification of the Confidential Consortium Framework, Heidi Howard, Markus A. Kuppe, Edward Ashton, Amaury Chamayou, Natacha Crooks, NSDI, 2025` (already in the collection; not re-added)
  - shows: TLA+ specs bound to the C++ implementation by trace validation and model-checking-guided testing, in CI. "find six subtle bugs in the design and implementation"
  - why: the nearest prior work on checking a real Raft-derived implementation (including its reconfiguration) against a spec; the method to compare with.
  - read depth: abstract only
- `ReCraft- Self-Contained Split, Merge, and Membership Change of Raft Protocol, Kezhi Xiong, Soonwon Moon, Joshua H. Kang, Bryant Curto, et al., DSN, 2025`
  - shows: a Raft reconfiguration protocol (split, merge, membership change), implemented in etcd, with a safety and liveness proof (paper-level). "We prove the safety and liveness of ReCraft"
  - why: shows reconfiguration changes are still being designed for Raft implementations; its etcd patch and pen-and-paper proof are a target for a mechanized check.
  - read depth: abstract only

### 7.2. HTTP framing agreement across proxy chains

- `HTTP Request Synchronization Defeats Discrepancy Attacks, Cem Topcuoglu, Kaan Onarlioglu, Steven Sprecher, Engin Kirda, arXiv, 2025`
  - shows: a proposed defense where each hop propagates what it parsed so later hops can check agreement. "there exists no scalable, general defense against discrepancy attacks"
  - why: states the chain-agreement property as a design goal, which is what a proof would have to establish; also the newest "no general defense" claim to check.
  - read depth: abstract only
- `Gudifu- Guided Differential Fuzzing for HTTP Request Parsing Discrepancies, Bahruz Jabiyev, Anthony Gavazzi, Kaan Onarlioglu, Engin Kirda, RAID, 2024`
  - shows: graybox differential fuzzing of whole HTTP requests across proxies, finding more discrepancies than earlier fuzzers. "minor HTTP parsing discrepancies between them can lead to various severe attacks"
  - why: the strongest testing baseline after T-Reqs and HTTP Garden (both already collected); defines what a proof must beat.
  - read depth: abstract only

### 7.3. Mixed-version rolling upgrades

- No new paper kept. Zhang SOSP 2021 and UpFuzz NSDI 2026 are already collected. Scholar returned only unrelated results for protocol-level upgrade verification (see wanted list).

### 7.4. Durable execution / exactly-once effects

- `Automated Verification of Idempotence for Stateful Serverless Applications, Haoran Ding, Zhaoguo Wang, Zhuohao Shen, Rong Chen, Haibo Chen, OSDI, 2023`
  - shows: Flux, an automatic verifier of "idempotence consistency" (a retry is invisible to users) for serverless functions. "Flux has successfully identified previously unknown issues in 12 applications"
  - why: the only checked definition of retry-safety I found with real bugs; fits the property "effects happen once under crash and retry".
  - read depth: abstract only
- `Executing Microservice Applications on Serverless- Correctly, Konstantinos Kallas, Haoran Zhang, Rajeev Alur, Sebastian Angel, Vincent Liu, POPL, 2023`
  - shows: a framework (µ2sls) with a formalization of serverless implementations under failure and re-execution. "provides formal guarantees that the generated serverless implementations are correct"
  - why: gives a formal model of re-execution plus side effects, which Durable Functions (OOPSLA 2021) lacks; no engine code is verified.
  - read depth: abstract only
- `ExoFlow- A Universal Workflow System for Exactly-Once DAGs, Siyuan Zhuang, Stephanie Wang, Eric Liang, Yi Cheng, Ion Stoica, OSDI, 2023`
  - shows: exactly-once recovery as a layer separate from execution, with task annotations for nondeterminism. "provide exactly-once semantics as a separate layer from execution"
  - why: a design baseline for what "exactly-once" is promised in workflow engines, and what annotations it needs (nondeterminism), relevant to Restate's journal.
  - read depth: abstract only
- `Netherite- Efficient Execution of Serverless Workflows, Sebastian Burckhardt, Badrish Chandramouli, David Justo, Konstantinos Kallas, et al., VLDB, 2022`
  - shows: a production-oriented engine for Durable Functions with partitioned, pipelined persistence. "Netherite achieves lower latency and higher throughput than the original DF engine"
  - why: the implementation companion to the Durable Functions semantics; shows the gap between the proven model and an engine that group-commits causally dependent steps.
  - read depth: abstract only

### 7.5. Lease and fencing safety under process pauses

- No new paper kept. LeaseGuard, PaxosLease Revisited, the Cockroach leader-lease page and Grove are already collected. Scholar's results were non-peer-reviewed (GoFetchLock, an S3-hosted PDF) or unrelated.

### 7.6. Liveness under partial network partitions

- No new paper kept (Alquraan OSDI 2018 and Nifty OSDI 2020 already collected). Omni-Paxos (EuroSys 2023) is wanted but could not be downloaded.

### 7.7. Transactional streaming

- No new paper kept. Scholar returned no peer-reviewed verification of Kafka transactions; the results were thesis work, trade-press-like articles and a VLDBJ survey that I could not download (see wanted list).

### 7.8. Claimed isolation levels

- `Validating Database System Isolation Level Implementations with Version Certificate Recovery, Jack Clark, Alastair F. Donaldson, John Wickerson, Manuel Rigger, EuroSys, 2024`
  - shows: Emme, a white-box checker that recovers version order from the database, handles predicates, tested on PostgreSQL, CockroachDB and TiDB. "We present version certificate recovery, a method of recovering the version order"
  - why: checks the claimed level (including repeatable read vs serializable) in TiDB, the Rust-TiKV system in the report; a faster, more precise oracle than Elle.
  - read depth: abstract only
- `AWDIT- An Optimal Weak Database Isolation Tester, Lasse Møldrup, Andreas Pavlogiannis, PLDI, 2025`
  - shows: a provably optimal tester for Read Committed, Read Atomic and Causal Consistency histories. "improving significantly over the state of the art"
  - why: the current best black-box oracle for weak levels; the "claimed level" check for weak modes would reuse it.
  - read depth: abstract only
- `Viper- A Fast Snapshot Isolation Checker, Jian Zhang, Ye Ji, Shuai Mu, Cheng Tan, EuroSys, 2023`
  - shows: a sound and complete black-box SI checker built on BC-polygraphs. "viper, an SI checker that is sound, complete, and fast"
  - why: SI is the claimed level of TiDB/TiKV; this is the standard SI checker to compare a proof-based approach against.
  - read depth: abstract only

### 7.9 Wanted but not downloaded (breadth)
- Protocol-level upgrade verification (direction 3), liveness-under-partial-connectivity proofs (direction 6), a peer-reviewed lease/fencing-under-pause paper (direction 5), a Kafka-transactions verification paper (direction 7): Scholar found none; the "no machine-checked proof" claims in REPORT.md stay unrefuted but unconfirmed.

Downloaded on 2026-11-13 and now in the collection: Omni-Paxos (EuroSys 2023), the transactional stream processing survey (arXiv preprint of the VLDB Journal paper), Zhu's UT Austin thesis. Ding et al. NSDI 2025 was already in the collection. Http/3 will not save you from request smuggling (Pisu et al., NCA 2024) was obtained through USC library access (PDF only).

## Wanted but not downloaded (groups 1-6)

- None remaining from these groups.
- `Fairness and Liveness under Weak Consistency` (Abdulla et al.) was downloadable but not added: it is about hardware memory models (TSO), not network sync.

Downloaded on 2026-11-13 and now in the collection: A Refinement Methodology for Distributed Programs in Rust (OOPSLA 2025), Mocket (EuroSys 2023; paywalled ACM PDF, kept as PDF only, no text in the repo), Undo and Redo Support for Replicated Registers (arXiv version), Composing CRDTs Convergent by Construction (OOPSLA 2026), Exploring the Complexities of Passkey Revocation (CCS 2026, from the CISPA repository). Through USC library access (PDF only, no text in the repo): Login, Logout, Reset (SecureComm 2025), Nano-MCP (GAST 2026) and Protect the Gate (CSNet 2023).

Google Scholar showed a CAPTCHA on 2026-11-13 after four searches; it was not bypassed.

## What this guide leaves out

- Eight papers are in none of the lists I was given but were added in the same hours, so I included them: the four on configuration and deployment (Ctests, Ciri, Meta health checks, 3DGen) and four in the SSO group (OAuth 2.0 analysis, BrowserID, post-quantum SAML, RADIUS).
- The lists also name papers that were already in the collection before this round (IronFleet, Verdi, Perennial, Grove, Anvil, Verus, Basilisk, Atmosphere, Cedar, Verifying the Rust Standard Library, ShardStore, Fonseca 2017, TraceLinking). I did not reread those.
- Papers the lists say could not be downloaded are not here, for example Shapiro's CRDT report, JaVerT (POPL 2018), SpecTec, Veil (CAV 2025) and Coyote.
- The file named "Met ... JSEP, 2024" holds the arXiv 2022 text, per the agent that added it.
