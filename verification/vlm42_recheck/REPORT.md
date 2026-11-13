# vlm42_recheck: source recheck of the posted memo and msg_1110_results.txt
(authored by agents unless marked 🧑)

Why: many quotes came through a page-summarizing fetch tool. Every item below was re-opened with raw tools (gh api, curl, pdftotext). Details and full quotes: part_res1.md, part_res2.md, part_res3.md (results file), and this file (memo). Raw copies in dl/.

## Corrections to make first

1. results, JS semantics: "the way WebAssembly's spec now generates its own Coq/Isabelle definitions" is WRONG. SpecTec README (WebAssembly/spec, spectec/README.md): "various artefacts could be generated through dedicated backends: ... the _Coq_ and _Isabelle_ definitions for mechanisation". Repo has LaTeX, prose, interpreter backends only; no Coq/Isabelle backend found. Fix: "generates LaTeX, prose and an interpreter; Coq/Isabelle backends are a stated goal".
2. results, breadth first: "the bad updates passed validation" (all four outages) is WRONG as a blanket claim. True for CrowdStrike ("one of the two Template Instances passed validation despite containing problematic content data"); partly Azure ("the configuration passed through the protection safeguard"); Google Cloud says "it did not have appropriate error handling nor was it feature flag protected" (no validator); Cloudflare 18 Nov: no validation statement, file "doubled in size" past a limit.
3. results, editor sync: "VeriFx for 35 CRDTs" is OVERSTATED. arXiv 2207.02502: "From these 35 CRDTs, 34 were verified in a matter of seconds and 1 could not be verified due to its recursive nature" (the 1 is RGA, the text CRDT).
4. results, shared process: Browserless does NOT say process-per-browser is "the safer choice". It says: "Browserless isolates browser state. That isn't the same as giving every session its own virtual machine, container, host, or network." Browserbase claim confirmed ("Each browser runs in a dedicated VM").
5. memo, editor sync: Loro #1040 is not "copies silently diverge". Its title: "Importing a shallow snapshot into a doc with concurrent ops stalls as permanently pending ..."; body: "silently buffers the whole import as `pending` — `toJSON()` stays empty". It is a silent stall (no merge), arguably divergence only loosely. #1215 does fit ("leaves the document state out of sync with its oplog"; "The divergence then spreads"). Posted memo not edited.
6. memo, sign-out: citation "Ghasemisharif and Kanich" omits the third author. PDF: "Mohammad Ghasemisharif, Chris Kanich, and Jason Polakis". Quote itself confirmed.

Minor (no fix needed unless wanted): Nieto 2022 also covers registers and combinators, not only "counters and sets" (still no text CRDT). Warblre "proves regex rewrites": the rewrite proofs are in Linden, same group, built on Warblre. Jepsen NATS 679,153/1,367,069 is from a file-corruption test, not a plain crash. Lamisa "85% of 520": the 520 are JWT-using sites, not random sites.

## Memo items (posted comment = memo.txt, checked identical)

Confirmed:
- chat-platform #650: body "So having two active tabs can randomly log someone out about every 15 minutes." (johannesjahn, 2026-10-21)
- soliplex #670 title: "Web: Multiple tabs break with IdP that rotates refresh tokens" (tseaver, 2026-11-01)
- NEBULA (arXiv 2608.04115): "this is not an exotic capability but the default behaviour of retrying mobile clients and multi-tab browsers."
- Ghasemisharif et al. S&P 2022: "We also note that 318 RPs continued accepting cookies 10 days after revocation."
- Fett et al. 2017: "We do not model less used features, in particular OIDC logout, ..."
- Automerge #772 title: "Dropped messages in the sync protocol cause infinite loops"; #1284 title: "Rust sync can loop infinitely if a message is lost". Both open.
- Lightpanda many sessions per process: README "For serving several agents from one process ... Each connection is routed to its own **browsing session** — its own page, cookies and memory".
- VeriWasm checks native-compiled Wasm (title "SFI safety for native-compiled Wasm"); LFI verifies compiled machine code. "ahead of time" fits both (inference from the papers).

Unverifiable in this pass (characterizations, not quotes; papers not re-opened): RockSalt, Icarus ("verified parts of the compiler once"), TurboTV ("checked that each compilation is correct"). They match what I know of these papers (belief), and "nobody checks ... per-session" is a negative claim that no source can confirm.

## Results-file items
All other numbers and quotes confirmed: npm downloads (yjs 52,977,710; Automerge 370,089; Loro 811,540, 2026-10-11..11-09), Yrs in Jupyter/AppFlowy, Automerge sync ~1.3k physical lines with no unsafe/async, Cloudflare MPK and 12 bit/s Spectre leak (2026-08-19), Site Isolation is Dead, Gomes 2017 (~2,100 proof lines), WOOT 2022, Raft ~45,000 lines (via Blau secondary), S&P 2022 "less than 2%"/"67%", JSCert last substantive commit 2019-04-09, ESMeta in ECMA-262 CI since 2022-11-03, all outage dates/quotes, AWS 14.5 h, etcd 2022, browsers <10% of 2025 zero-days.
Unverifiable: "AWS's own TLA+ program didn't cover it" (absence claim; the AWS postmortem never mentions TLA+); "no liveness proof on real code for any editor" (negative claim).
