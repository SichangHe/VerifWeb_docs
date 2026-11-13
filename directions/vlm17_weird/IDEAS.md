# Weird web + verification ideas
(authored by agents unless marked 🧑)

How made: read the human's notes (JSphere, DeGenTWeb, C2PA/photo auth, web atoms, Verus proof-agent studies, browser agents) and this project's odd findings; one generator was ChatGPT (`gpt.txt`, prompt `prompt.txt`, told to avoid msg_candidates.txt and vlm11_spread), plus my own. Novelty checks are one Google Scholar first page each (`scholar/*.txt`); "no hit" means only that, not proof of novelty. Ranking is weirdness x feasibility, my opinion.

1. arrow of time for browser security
- pitch: some facts may only move forward (logout, revoked permission, rotated key), even when back/forward cache, session restore, or archive replay brings old page state back
- builds on: archives replaying wrong; proofs surviving behavior changes
- why unusual: browsers deliberately restore the past; nobody states which facts must be exempt
- verify: chosen security facts are monotone across every restore path in a model of navigation + caches
- scholar ("bfcache logout permission revocation"): no relevant hit
- first step: list the restore paths in one engine (Servo/Lightpanda) and write the monotonicity property for "logged out"

2. behavioral fossils
- pitch: code a site removed can still run from service workers, caches, old tabs, or archives
- builds on: web atoms (what changes together), archive replay, JSphere (what scripts do)
- why unusual: deleting code is assumed to kill the behavior
- verify: after version N drops behavior X, no stored state can resurrect X
- scholar ("service worker persistence after site update"): no relevant hit
- first step: a toy PWA with one banned fetch; enumerate resurrection paths by model checking

3. web probate
- pitch: when a domain expires and someone else buys it, browser state (cookies, permissions, saved passwords, HSTS, service workers) passes to the new owner
- builds on: C2PA (identity of who produced content), site isolation work
- why unusual: origin is treated as timeless; owners are not
- verify: authority created under owner A cannot be used by owner B
- scholar: residual trust is measured (Lever et al. S&P 2016 "Domain-Z"; Lauinger et al. 2016), but those study servers/services, not browser-held state; no formal treatment seen
- first step: list which browser stores survive a simulated ownership change

4. proofs that expire
- pitch: a proof about a live site's scripts carries an expiry key = its web atom; when any atom member changes, the proof is void and re-checked
- builds on: web atoms (the human's notes already call them "evidence invalidation units"), JSphere, advisors' "on-the-fly verification" remark
- why unusual: proofs are assumed permanent
- verify: per-site script properties (no prototype change, no field exfiltration) re-proved incrementally as atoms change
- scholar: not checked
- first step: on crawled sites, measure how often atom changes would void a property, i.e. proof shelf life

5. proofs suspiciously hard to kill
- pitch: if a proof survives a real behavior change, the spec is probably weak; use history of engine commits as free mutants
- builds on: our proofs that survived behavior changes; Boa bugs found by failing proofs; LeetProof/StarVerus spec-quality gaps
- why unusual: robust proofs are seen as good
- verify: spec sensitivity: real past bug-fix commits must break some obligation
- scholar: spec mutation exists (IronSpec, OSDI 2024; MutDafny); using real commit history of web engines as mutants not seen
- first step: replay Boa's past fix commits against our existing Boa proofs; count survivors

6. double-entry ledger of browser authority
- pitch: treat permissions like money; every grant (user click, popup, postMessage, worker) is a ledger entry, and spending needs a matching credit
- builds on: Lightpanda's 9 rule bugs; agents breaking site isolation
- why unusual: browser rules are scattered checks, not a conservation law
- verify: no tab/script/agent spends authority it never received
- scholar: only LLM-agent capability papers (2026 preprints); none for browser internals
- first step: 200-line ledger model of user activation + window.open + postMessage; replay real traces

7. agent context window as a renderer process
- pitch: an LLM agent's context mixes text from many sites; treat it as a process that site isolation must govern
- builds on: our finding that agents' context breaks site isolation; browser_agent notes
- why unusual: isolation is proved for memory, not for prompt text
- verify: text labelled origin A cannot influence actions on origin B except through declared channels
- scholar: getting crowded (Christodorescu et al. 2025; WebMCP-Phalanx 2026; "agentic browsers and the same-origin policy"); mechanized proof not seen
- first step: label context chunks by origin in a toy agent loop; prove the action filter in Verus

8. archive replay as courtroom evidence
- pitch: instead of "replay looks right", compute which facts on a replayed page are provably what users saw
- builds on: archives replaying wrong; C2PA provenance
- why unusual: replay quality is treated as engineering, not chain of custody
- verify: each displayed fact has a checked path to captured bytes, time, origin
- scholar: WEFT (2025, forensic web evidence) and Nelson 2019 exist; per-fact admissibility not seen
- first step: on 100 captures, mark page regions "provable" vs "unverifiable"

9. C2PA that survives being stripped
- pitch: assume social sites delete signatures (X, Facebook do, per the human's notes); spread authenticity over k-of-n witnesses
- builds on: photo_crypto_auth, c2pa notes
- why unusual: provenance designs protect one metadata box
- verify: any k surviving witnesses authenticate the same lineage; mixes of two originals fail
- scholar: not checked
- first step: protocol model in ProVerif/Tamarin with three witnesses

10. evolving pages whose fitness is a failed proof
- pitch: generate HTML/JS (DeGenTWeb-style generation) and keep variants that break a stated theorem, not ones that crash
- builds on: DeGenTWeb, proof failures that found Boa bugs, Lightpanda bugs
- why unusual: fuzzers aim at crashes or disagreement, not theorem violation
- verify: the target invariant (e.g. event-loop order) on generated inputs
- scholar: not checked
- first step: evolve programs against our existing Boa event-loop property

Dropped: notarized rendering (vWitness, DSN 2023 is close; low feasibility); privacy policies as specs (likely known; unchecked).
