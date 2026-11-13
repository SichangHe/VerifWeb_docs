# part_res1: recheck of msg_1110_results.txt (4 paragraphs)
(authored by agents) Originals fetched with curl/pdftotext/arXiv PDFs into dl/res1/. Papers Nieto 2022 and Karayel 2022 read from /hdd1/sichanghe/paper_collection (already present).

## WRONG / OVERSTATED (first)

1. "VeriFx for 35 CRDTs" (Editor sync, prior work). Verdict: overstated. Source arXiv 2207.02502, intro: "we implemented and verified 35 CRDTs ... From these 35 CRDTs, 34 were verified in a matter of seconds and 1 could not be verified due to its recursive nature." (the 1 is RGA, the text CRDT). Correct text: VeriFx verified 34 of 35 CRDTs; RGA failed.

2. "browser-as-a-service vendors (Browserbase, Browserless) do the opposite, one VM or process per browser, as the safer choice" and report "They say outright that this is the safer choice" (Shared process, prior work). Verdict: Browserbase confirmed (VM per browser; blog says packing browsers "expands the blast radius"); Browserless claim "says outright safer" is NOT supported. Browserless (https://www.browserless.io/blog/session-isolation): "Browserless gives every connection a fresh remote browser process instead of one shared profile." and "Browserless isolates browser state. That isn't the same as giving every session its own virtual machine, container, host, or network. If your threat model needs those infrastructure boundaries, add them." It says its isolation is weaker than VM isolation, not that process-per-browser is the safer choice versus shared processes. Correct text: Browserbase says one VM per browser is the stronger isolation; Browserless uses a process per connection and says VM/container separation is an add-on.

3. "Nieto et al 2022 ... (safety only, counters and sets, no text)" (Editor sync, prior work). Verdict: minor omission. Source Table 3 lists 12 CRDTs: PN-Counter, G-Counter, Two-Part Set, Add-Wins Set, Remove-Wins Set, Grow-Only Set, LWW Register, Multi-Value Register, plus product/map combinators. Correct: counters, sets, registers, combinators; no list/text CRDT found (no RGA/sequence CRDT). Safety-only claim confirmed (see below).

## CONFIRMED

Editor sync, widely used Rust code
- "53M npm downloads/month vs 0.37M Automerge, 0.81M Loro": confirmed. api.npmjs.org last-month, 2026-10-11..2026-11-09: yjs 52,977,710; @automerge/automerge 370,089; loro-crdt 811,540.
- "Yrs ... Jupyter real-time collaboration via pycrdt": confirmed. jupyter_ydoc pyproject.toml: `"pycrdt >=0.14.0,<0.15.0"`. (pycrdt README "based on Yrs" per report, not re-fetched.) Server side only.
- "AppFlowy" uses Yrs: confirmed. yjs README "Who is using Yjs": "[Appflowy](https://www.appflowy.io/) - They use Yrs"; AppFlowy-Collab Cargo.toml `yrs = { version = "0.25", features = ["sync"] }`.
- "Automerge sync ~1.3k lines, no unsafe, no async": confirmed with caveat. rust/automerge/src: sync.rs 2495 lines (`mod tests` at line 854) + state.rs 214 + bloom.rs 160 + message_builder.rs 118 = ~1,345 physical non-test lines (incl. comments/blank). Tokei code-only for sync.rs non-test part is 554, so "lines" is physical lines, not code LOC. `grep -w unsafe` and `grep -w async` in the four sync files: 0 hits.
- "Yrs the one in real products": judgment, supported by the above.

Shared process, prior work
- Cloudflare "V8 isolates plus memory protection keys": confirmed. https://blog.cloudflare.com/safe-in-the-sandbox-security-hardening-for-cloudflare-workers/ : "we have deployed internal modifications to V8 to use memory protection keys to isolate the isolates from each other. There are up to 15 different keys available on a modern x64 CPU". Security model page: "Cloudflare can run many isolates within a single process."
- "production Spectre leak reported in 2026": confirmed. https://blog.cloudflare.com/revisiting-spectre-attacks-on-workers/ dated August 19, 2026: "we managed to demonstrate a remote Spectre attack reliably leaking up to 12 bit/s with a 99% accuracy in the production environment of Cloudflare Workers." (Body: "In production, we achieved a leakage rate of up to 12 bit/s with an accuracy of more than 99%.") Note: demonstrated by the researchers, disclosed on Cloudflare's blog.
- Browserbase one VM per browser: confirmed. https://docs.browserbase.com/guides/security : "Browser isolation: Each browser runs in a dedicated VM, providing strong isolation at the hardware virtualization layer." and table "Isolation | 1 browser per VM". Blog https://www.browserbase.com/blog/why-you-can-t-just-run-chromium-in-a-sandbox: packing "more browsers into one sandbox ... expands the blast radius of a bad or corrupted browser process."
- Browserless "one process per connection": confirmed (quote in item 2).
- "Site Isolation is Dead" (S&P 2026), agentic browsers leak via agent-renderer channels: confirmed. sid.pdf abstract (2026 IEEE S&P, DOI 10.1109/SP63933.2026.00241): "privileged processes manage user prompts and agent operations, while untrusted renderer processes are isolated, with inter-process communication (IPC) channels serving as their bridge"; "all tested agentic browsers and extensions are vulnerable to these attacks, revealing that existing implementations often fail to properly account for IPC channels." Study covers "two open-source agentic browsers and seven agentic extensions".

Editor sync, prior work
- Gomes et al. 2017 Isabelle, text/sets/counters: confirmed. arXiv 1707.01747 abstract: Isabelle/HOL framework; RGA, ORSet, Counter proofs (775/270/55 lines).
- WOOT 2022 (Karayel, Gonzalez, Distributed Computing 35:145-164, published 4 Jan 2022): confirmed. "the property for WOOT remained open for 14 years ... Isabelle/HOL proof assistant to machine-check its correctness."
- Nieto 2022 verified real causal-broadcast library, safety only: confirmed. Sec. 4: "We proved specifications of our implementation that satisfy the three safety properties above." OCaml subset over UDP-like Aneris network ("messages can get lost, duplicated, and re-ordered").
- "no liveness proof on real code for any editor": negative claim, unverifiable by this check; Trillium (Timany et al.) shows one CRDT liveness proof, but no editor.

Editor sync, harder than consensus?
- "Raft's proof ~45,000 lines": confirmed as quoted secondary. Blau, arXiv 2006.09823, intro: "Woos et al. [2016] use on the order of 45,000 lines of proof scripts to verify the complete Raft protocol in their system." (Not checked against Woos et al. itself.)
- "CRDT convergence proof ~2,000": confirmed approximately. Gomes 2017 Sec. 8: "around 620 lines for our network model, around 380 lines for the abstract convergence proof, 775 lines for the RGA proof, around 270 lines for the ORSet proof, and around 55 lines for the Counter proof. Additional shared code ... around 170 lines" = 2,100 (2,270 with shared). Not like-for-like with Raft (different property); the report says so.
- "sync liveness needs fairness proofs, done only for one counter": confirmed. Nieto 2022 Sec. 8: Timany et al. 2021 is "the only related work that proves eventual delivery ... they only verify one example CRDT (a G-Counter)". Fairness: Trillium (Timany et al., arXiv 2109.07863 intro): "The challenging part is incorporating the notion of fairness of the inter-replica communication; if messages from one replica are just ignored, then eventual consistency will never be reached." Caveat: this is for proofs on code; Pek et al. 2015 did liveness proofs of anti-entropy models (the memo says "done only for one counter" without "on code").
- "convergence alone is cheap (merge that throws away edits converges)": Gomes 2017 LWW "at the cost of losing user input" per report; not re-opened.
- "12 papers added to paper_collection": not checked (internal).
