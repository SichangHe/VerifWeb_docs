# net_id: NETWORK / IDENTITY / OTHERS. Standards errors vs formal methods
Labels: FACT (quoted, source) / INF (inference) / OPN (opinion). Searched 2026-11-13. Nothing published.
Caveat: quotes come from search-tool excerpts; several are tool paraphrase, marked (paraphrase). Verify against PDF before citing.

## 1. How often standards are wrong
- FACT McQuistin et al. TMA 2023 https://www.smcquistin.uk/assets/papers/mcquistin2023errare.pdf : errata Jan 2001-Dec 2022 = 6,759 (3,288 editorial, 3,471 technical) over 2,240 RFCs; "share (42.5%) of errata are verified"; "32% attract at least one errata filing" among standards-track RFCs.
- FACT (same) technical = "mistakes in the technical content of the RFC that are likely to result in incorrect, non-conforming, implementations", e.g. "erratum 5996, which reports a mistake in the pseudocode of an algorithm".
- FACT (same) RFC 793 (TCP) has 47 errata; RFC 791: 17; RFC 4601: 114 (max).
- FACT (same) "of the 930 RFCs with HFDU errata, only 40% have been updated or obsoleted by a subsequent RFC" (paraphrase by search tool): most known errors are never fixed in-document.
- FACT GitHub analysis of errata.json, spot-checked 2026-10-29: 8,116 errata; Verified 3,758; HFDU 2,431; Rejected 1,167; Reported 760; Technical 4,414, Editorial 3,702. https://github.com/munimtechnologies/rfc-errata-hfdu-graveyard . (third party, AI-made; check against https://www.rfc-editor.org/errata_search.php). Verified-AND-technical ~3,543 per search snippet of rfc-editor page (unconfirmed filter).
- INF errata are sampled by who bothers to report; they undercount semantic flaws (races, non-termination) that nobody files as errata. Errata type labels (technical/editorial) do not say ambiguity vs contradiction vs race: no kind-breakdown found. OPEN.
- No 3GPP CR statistics found (not searched deeply). OPEN.

## 2. Who found what
Found by FORMAL METHODS on the spec (spec flaw, not implementation bug):
- Zave, Chord (Alloy), SIGCOMM CCR 2012 https://www.pamelazave.com/chord.html : FACT "no published version of Chord is correct" under the papers' own failure assumptions; "not one of the seven claimed invariants is actually an invariant" (site paraphrase). Chord had a claimed proof of eventual reachability. Fix + proof: TSE 2017 arXiv 1502.06461. FACT per Wikipedia: AWS engineers credit this work for starting formal methods. Kind: wrong invariants / liveness.
- Zave, SIP (Promela/Spin), IPTComm 2008 https://link.springer.com/chapter/10.1007/978-3-540-89054-6_13 : "explains some problems in SIP revealed by it". Later (arXiv 2509.13208) "records seven possible race conditions". Kind: races, informal/inconsistent prose.
- TLS 1.3 draft 10, Tamarin, Cremers et al. S&P 2016 https://people.cispa.io/cas.cremers/downloads/papers/CHSV2016-TLS13.pdf : "uncover a potential attack in which an adversary is able to successfully impersonate a client during a PSK-resumption handshake" (extension feature, disclosed to TLS WG, fixed in draft 11). CCS 2017 (draft 21): new behaviour, client cannot tell if post-handshake auth succeeded. FACT. Pre-RFC: formal analysis ran in the standardization loop (best case).
- OAuth 2.0 (Fett/Kuesters/Schmitz, CCS 2016, arXiv 1601.01229): "the authors found several new attacks and could only prove security after developing fixes" (paraphrase). OIDC (CSF 2017, arXiv 1704.08539). FAPI (S&P 2019, arXiv 1901.11520): "partly severe attacks that broke authentication, authorization and session integrity" (paraphrase); fixed version proved. FAPI 2.0 analysis accompanied standardization: https://dl.acm.org/doi/10.1145/3699716 . Note: WIM is a pen-and-paper model, not machine-checked (paraphrase); Tamarin reproductions exist.
- 5G AKA, Basin et al. CCS 2018 https://dl.acm.org/doi/10.1145/3243734.3243846 : FACT "We also extract precise requirements from the 3GPP standards defining 5G and we identify missing security goals." Full text: missing assumption (5.2.1), missing key confirmation (5.2.2), traceability attack persists. Cremers/Dehnel-Wild NDSS 2019: "5G-AKA critically relies on unstated assumptions on the inner channels" + authentication vuln in Feb 2018 drafts. Whether 3GPP adopted fixes in TS 33.501: NOT confirmed. OPEN.
- EMV, Basin/Sasse/Toro-Pozo S&P 2021 https://emvrace.github.io/ : Tamarin found Visa contactless PIN bypass ("The core problem is that the PIN verification request is not authenticated", tested in FR/BE); follow-ups: card brand mixup (USENIX Sec 2021, Maestro >USD 400), Mastercard (USENIX Sec 2023). Kind: security flaw in spec design; real-money exploit.
- Bluetooth: Chang/Shmatikov FCS 2007 (ProVerif, numeric comparison concurrent sessions break); Sethi et al. arXiv 1902.07550 (misbinding; "not clear to us why the existing models missed the attack"); Claverie et al. 2024 Tamarin https://link.springer.com/chapter/10.1007/978-3-031-51479-1_6 (pairing mode confusion, "several unreported attacks"); NDSS 2023 passkey entry: two new attacks (group guessing, ghost); NDSS 2026 BLE SC "PE confusion attack". INF: repeated new finds over 17 years = each model covers a slice; spec is huge.
- ARM v8-M, Reid OOPSLA 2017 https://alastairreid.github.io/papers/oopsla2017-whoguardstheguards.pdf : FACT "Despite the fact that the ARM v8-M specification had previously been extensively tested, we found twelve bugs (including two security bugs) that have all been fixed by ARM." Also English prose "ambiguous, imprecise, incorrect" (paraphrase). Method: SMT on executable spec. Sail POPL 2019: Sail checks "2695 bounds-checking problems found in the ARM specification" (paraphrase); small bugs in ASL found via address-translation proof.
- RISC-V Sail: model work led to spec contributions: page faults in page-table walks; "ambiguities in how interrupt delegation was specified" (slides https://www.cl.cam.ac.uk/~jrh13/spisa19/slides_04.pdf). 2025 summit: Sail + Jasper found 30 hardware bugs, 4 broke CHERI guarantees (https://lists.riscv.org/g/tech-golden-model/attachment/381/0/riscv-nasummit2025-sail-slides.pdf). Reid critique: spec "scattered across four artifacts" https://alastairreid.github.io/riscv-spec-issues/ .
- C/C++11 memory model, Batty et al. POPL 2011 https://www.cl.cam.ac.uk/~pes20/cpp/ : Isabelle/HOL model; effect: committee paper N3132 "discusses some issues with the N3092 text that led to those changes" (Rapperswil July 2010). Specific defects (my memory, NOT confirmed here): happens-before/consume, release sequences, SC fences. Later: POWER compile mapping (POPL 2012).
- MLS RFC 9420: ETK, ePrint 2025/229: "MLS achieves a weaker form of security than was suggested by previous analyses" when external proposals/commits allowed; "does not realize FCGKA when used with ... EUF-CMA" signatures. Computational proof, post-RFC. Earlier draft-stage finds (group splitting, signature confusion): sources not retrieved.
- Ethereum beacon chain Dafny (Cassez et al., TACAS 2022, arXiv 2110.12909): "uncovered several issues and proposed verified fixes"; scope: runtime-error freedom of state machine, NOT consensus. Also found a Dafny soundness bug. Gasper accountable safety proved in Coq (Runtime Verification). SoK arXiv 2608.21935: Dafny work is "closer to software correctness ... than to consensus-level theorems" (paraphrase).
- DNS: GRoot SIGCOMM 2020 (109 bugs in campus config; ~160k blackholing issues at provider) = config bugs, not spec bugs. SCALE/Ferret NSDI 2022: 30 new bugs in 8 implementations (dissertation). Both = implementation/config; the RFC-ambiguity angle was not found in results. OPEN.
- QUIC Ivy, McMillan/Zuck SIGCOMM 2019: "find a bunch of interesting bugs in implementations ... including vulnerabilities to denial-of-service attacks and an information leak similar to ... Heartbleed" (Galois summary https://www.galois.com/articles/quic-testing-a-quick-replication); a "potential DoS in the protocol" (another summary); ~1 bug/day. Crochet et al. 2021 (https://dl.acm.org/doi/10.1145/3488660.3493803, arXiv 2503.01374): 7 implementations, draft-18 to draft-29, "found ambiguities in the QUIC specification". Mostly implementation bugs.
- TCP Netsem HOL4, Bishop et al. JACM 2018 https://www.cl.cam.ac.uk/~pes20/Netsem/ : specs checked against thousands of traces from FreeBSD/Linux/WinXP; "Many differences between these were identified, and a number of bugs." Spec was written after the fact, validated against implementations; RFC defects not itemized in results. FACT: "rigorous specification is feasible for protocols as complex as TCP."

Found by IMPLEMENTERS/ATTACKERS or hand proof gap (formal methods missed):
- Selfie, TLS 1.3 PSK reflection, Drucker/Gueron, ePrint 2019/347 https://eprint.iacr.org/2019/347 (J. Cryptology 2021): "first attack on TLS 1.3 after the standard's official release" (tool paraphrase); existing symbolic and hand proofs "ignored the case of external PSKs" (paraphrase). Later re-found by CPSA (Springer 2021). INF: a formal model is only as strong as its assumed key-use roles; the proofs had a modeling gap, not a tool failure.
- Not searched here: KNOB/BLURtooth style Bluetooth attacks, BGP, Signal, Matrix, USB/PCIe, POSIX/SibylFS, filesystems. OPEN.

## Kinds seen (INF, from above)
- missing assumption / unstated channel property (5G AKA, Selfie)
- missing authentication of a message (EMV, TLS PSK-resumption)
- races/concurrent sessions (SIP, Bluetooth SSP)
- wrong claimed invariant / liveness (Chord)
- ambiguity in prose (ARM prose, RISC-V delegation, QUIC)
- memory-model inconsistencies (C11)
- spec scope too weak vs claim (MLS, FAPI)
- Not seen: pure non-termination in a standard (deadlock check on SIP model passed). OPEN.

## 3. Machine-parseable specs
- FACT ARM ASL: "In 2017 ARM released a machine-readable version of large parts of the ARMv8.2-A ASL" (Sail POPL 2019 https://www.cl.cam.ac.uk/~pes20/sail/sail-popl2019.pdf); public v8.5 and v9.3 ASL exist (Armstrong page).
- RISC-V: official spec is prose; Sail model is the formal one, adopted as golden model effort (separate artifact). 
- Ethereum: consensus-specs are executable Python (INF from Dafny port "follows official specs"); not independently fetched, verify at github.com/ethereum/consensus-specs.
- 3GPP: ASN.1 for RRC/NGAP messages (my knowledge, not fetched); AKA algorithms in prose + tables. 
- RFCs: ABNF and YANG checkable. FACT McQuistin: YANG RFCs pre-checker 0.63 technical errata/2yr vs post-checker 0.33; "The trend for editorial filings is the opposite"; "This suggests that the formal checks do reduce errata" (n=24 vs 58, small). Syntax checkers catch syntax only; protocol behaviour is in prose.
- OAuth/OIDC/TLS/QUIC/SIP: prose + some pseudocode; every analysis above required a human re-modeling step. INF.
- C standard, POSIX: prose; Sail-like formal models are separate (Batty, SibylFS not fetched).

## 4. Open
- Pattern INF: most formal finds come from a researcher hand-building a model from prose; spec being machine-readable (ARM) gave the largest bug yield per effort (SMT on the spec itself), consistent with 12 bugs after heavy testing.
- Unknown: fraction of RFC technical errata that are semantic vs typo-level; fraction of formally-found flaws that are fixed in the standard (3GPP TS 33.501 adoption unconfirmed; HFDU 40% fixed).
- Unknown: negative results (standards modeled with no flaw found) not systematically available; publication bias.
- Unfetched: BGP, DNS RFC ambiguity (Kakarla HotNets 2021 "How Complex is DNS?"), MPTCP, HTTP/2/3, WebAuthn (Hanzlik et al.), Signal (Cohn-Gordon), Matrix, USB/PCIe, POSIX SibylFS, Ethereum Gasper attacks (bouncing, reorg).
- OPN: strongest evidence of "standard wrong": Chord, EMV, 5G AKA, ARM, FAPI, TLS draft 10; each found by model-then-prove loop, many pre-publication, so "wrong" often meant draft-wrong.
