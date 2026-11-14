# Finding wrong standards by trying to formally verify them

(authored by agents unless marked 🧑)

Request (🧑, relayed by manager): "This by itself is not interesting, but the implication is interesting. The implication is that many standards may be wrong, and we may be able to find them by trying to formally verify those standards. Have agents look into this idea."

Trigger: WHATWG HTML navigation/session-history bugs (whatwg/html#12861, #12961, #12362, #6927), found because Ladybird implements the spec literally (vlm48_dirs/d.md A6).

Evidence files: vlm51_specs/web.md (web), vlm51_specs/net_id.md (network, identity, other), vlm51_specs/scholar.md (literature), vlm51_specs/probe/ (feasibility probe). Quotes there came from search and fetch tools that may trim or paraphrase; check the source before citing externally. Google Scholar returned a CAPTCHA on the first query; we did not bypass it, and used web search, arXiv, ACM and USENIX pages instead.

## Answer in short

Standards are often wrong, and formal methods have a strong record of finding the flaws. Their success clusters in two places. Security protocols (TLS, OAuth, 5G, EMV, Bluetooth) get checked in Tamarin or ProVerif by hand-written models. Specs that are already machine-readable (ECMAScript, WebAssembly, ARM) get checked by tools that read the spec text directly. Concurrency bugs in large algorithmic web specs (HTML event loop, navigation, streams) are found by implementers, not by tools (INFERENCE from the surveyed work). No tool parses WHATWG-style algorithms the way ESMeta parses ECMAScript. That gap is the natural research contribution (OPINION).

## How often standards are wrong (facts, with caveats)

- IETF: McQuistin et al. (TMA 2023) count 6,759 RFC errata from 2001 to 2022, 3,471 of them technical, and "32% [of standards-track RFCs] attract at least one errata filing". RFC 793 (TCP) alone has 47. INFERENCE: errata undercount semantic flaws such as races, because filing one requires someone to notice.
- ECMAScript: ecma262 has 80 issues labelled "spec bug" out of 1,440. JSTAR (a type checker over the spec) found 157 type bugs across spec versions from 2018 to 2021, and TC39 confirmed 93 of them.
- HTML: whatwg/html has no bug label. Keyword counts are noisy lower bounds: "ambiguous" 68, "contradict" 21, "race condition" 11, "infinite loop" 10. The labels `topic: history` (109 issues) and `topic: event loop` (52) mark where the trigger bugs live.
- Missing data: we found no breakdown of errata by kind, no 3GPP change-request statistics, and no count of modeled standards that turned out flawless (publication bias).

## Kinds of flaws, and who found them

Formal methods found these flaws in the standard itself (facts, per vlm51_specs/net_id.md and web.md):
- security flaws: TLS 1.3 draft 10 PSK client impersonation (Tamarin, fixed in draft 11); OAuth/OIDC/FAPI "partly severe attacks" (Fett, Küsters, Schmitz); 5G-AKA missing assumptions and traceability (Basin et al. CCS 2018; Cremers and Dehnel-Wild NDSS 2019; 3GPP fixed most); EMV Visa contactless PIN bypass (Basin et al.); WebSpec (S&P 2023) found 2 new browser-spec flaws, a `__Host-` cookie attack and a CSP vs HTML inheritance inconsistency
- wrong invariants: Zave (Alloy): "no published version of Chord is correct"; the 2016 navigation-history model (arXiv 1608.05444) showed the then-current HTML spec violates "traversing by δ then δ' equals traversing by δ+δ'"
- type, reference and consistency errors: JSTAR/ESMeta on ECMAScript (above); Wasm SpecTec, "ten errors in five proposals ready for inclusion" (PLDI 2024); P4-SpecTec, "24 bugs across the official P4 specification and the reference compiler"; ARM v8-M, "twelve bugs (including two security bugs)" (Reid)
- ambiguity: QUIC (Ivy) "ambiguities in the QUIC specification"; RISC-V Sail, interrupt delegation and page faults; SCTP RFC 9260 (Ginesin et al., USENIX Security 2024); RFCScope (LLM-based, not formal, ASE 2025): 31 new ambiguities in 14 RFCs, 3 now official errata
- memory model: C++11 (Batty et al.) led to committee changes

Implementers and attackers found these:
- races and non-termination in HTML navigation (Ladybird, the trigger bugs)
- the Selfie attack on TLS 1.3, which existing proofs missed because they "ignored the case of external PSKs"

INFERENCE: the formal finds are mostly security properties of small protocols and type or consistency errors in machine-readable specs. We found no 2022+ formalization of the HTML event loop or navigation. Concurrency in large algorithmic specs is the least-covered kind.

## Which standards are precise enough for a tool

- ECMAScript: `<emu-alg>` structured steps; ESMeta compiles them to an IR and runs in ecma262 CI (fact).
- WebAssembly: SpecTec is now the source of the standard (fact).
- ARM: machine-readable ASL, public for v8.5 and v9.3 (fact). RISC-V: Sail model beside the prose (fact).
- Ethereum consensus: executable Python spec (fact per source; not fetched).
- WHATWG HTML, DOM, Fetch, Streams, URL: numbered step algorithms in Bikeshed, looser than ecma262. We found no published parser or IR for them (light search).
- IETF RFCs: mostly prose; ABNF and YANG checkers are syntax-only. YANG RFCs averaged 0.33 technical errata after the checker was introduced vs 0.63 before (fact; n=58 vs 24; correlation, not proven cause).

## Feasibility probe: rediscovering whatwg/html#12861 (vlm51_specs/probe/REPORT.md)

- Fact: an 88-line explicit-state Python model of 6 spec transitions found the #12861 trace in about 30 minutes: a queued same-document finalization overwrites "ongoing navigation", the later cross-document navigation aborts, and load never fires. It also found a sibling trace (the second navigation is dropped silently) that a commenter had already raised in the issue.
- Caveat (inference): the issue told the agent which field and steps to model. Finding this blind would mean modeling all ~8 spec sites that write "ongoing navigation", estimated at 10x the work.
- Judgment calls: where the interleaving points sit inside "apply the history step", and whether a silent return counts as failure. A tool would have to make these choices systematically.
- Reuse: #12961 and #12362 fit the same three-thread structure (script, session-history queue, in-parallel navigate steps) but need more state. Estimate: 2 to 4x the model size.

## What a research contribution could look like (opinion)

Build an ESMeta-like front end for WHATWG step algorithms: parse the Bikeshed algorithms into an IR that has explicit event-loop tasks, "in parallel" steps and task queues. Then model-check generic properties that need no per-spec writing: every navigation or fetch terminates observably, shared fields are never overwritten by an unrelated task, and asserts and invariants hold. Run it across HTML, Fetch, Streams, Service Workers and IndexedDB.

Measures:
- recall on known bugs: rediscover a corpus of resolved spec issues (e.g. the 109 `topic: history` issues), checking the spec version before each fix
- new bugs confirmed by the editors
- the fraction of spec algorithms translated without hand edits
- the false-positive rate (JSTAR's 59.2% precision is a reference point)

The novelty argument (inference): prior tools handle sequential specs (ESMeta, SpecTec) or hand-modeled protocols (Tamarin). Concurrency inside a large algorithmic spec is not covered. Risk: WHATWG prose is less regular than ecma262, so the front end may need LLM help. RFCScope shows LLMs can find ambiguity, but its output is not a sound model.

## Most promising standards to try first

1. WHATWG HTML navigation and session history: recent open bugs (2026), spec-following implementations (Ladybird, Servo) to confirm against, and the probe shows a small model reproduces a known one.
2. HTML event loop plus Fetch/Streams: same algorithm style and same concurrency constructs, so the front end built for (1) transfers.
3. Service Worker lifecycle and IndexedDB transactions: state machines with lifecycle races; vlm48_dirs/d.md A1 and A4 cite real bugs.
4. ECMAScript async functions and generators: the parser (ESMeta) already exists, so it is cheap to test whether concurrency properties add anything beyond its type checks. Its novelty is lower.
5. IETF transport (QUIC, SCTP): prior models exist, so value would come from automation across many RFCs, not from a first model.

## Gaps

- Not searched: BGP, MPTCP, HTTP/2 and HTTP/3, WebAuthn, Signal, Matrix, POSIX/SibylFS, JSCert/KJS/JaVerT details.
- Not done: a full-text check of quoted numbers; whether anyone is already model-checking the rewritten navigation spec (none found).
