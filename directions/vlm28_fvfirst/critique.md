# critique of draft.md candidates (FV reviewer pass, 2026-11-09)
(authored by agents unless marked 🧑)

Basis: draft.md, bugs.md, bugs2.md, prior.md, memory direction_filters, two extra web searches
(verified HTTP/1.1 parser; verified cookie jar RFC 6265bis): neither found a verified implementation.
Fact vs inference: verdicts are my opinion; cost estimates are guesses.

## C1 proxy/backend agree on request boundaries -- KEEP (rank 1)
- FV is the contribution: the artifact is a mechanized RFC 9112 framing spec (incl. Upgrade, early response, unread body, reuse) plus a proof that each side refines it; agreement follows by transitivity, so no heavy relational logic is needed
- bugs are real and recent (hyper 2021, Pingora 2025 and 2026), and fuzzing (Garden, T-Reqs) cannot show absence
- risk: Verus has weak async/tokio support; must verify a sans-IO framing core (connection state machine over bytes), not the whole proxy
- novelty: no verified HTTP/1.1 framing found; EverParse/Vest cover syntax only, not connection-level state

## C2 HTTP/2 credit and no starvation -- CUT (defer)
- real bugs, but the property is liveness of async Rust: Verus does not do liveness natively, so this is a PL research project (fairness, cancellation, wakers), too PL and too costly for a small team
- the safety half (credit conservation: sum of credits is consistent) is cheap but does not catch the deadlock bugs
- revisit only as a stretch goal if C1's sans-IO h2 core proves easy

## C3 collaborative-editing convergence incl. save/load -- KEEP (rank 3), narrow
- distributed angle, three real issue reports in different libraries (Loro, Yjs, Automerge) on one bug shape: import of snapshot vs updates with pending ops
- FV claim worth making: import(snapshot) equals replay of the same ops, with a pending-op buffer; scope to a small CRDT core, not Automerge in full (Zakhour 2023 says full Automerge is hard)
- weakness: these bugs were found by users/fuzzing, so testing partly works; and "convergence proofs" lean PL. Sell it as "persistence layer", not "CRDT theory"
- unclear web link; frame as local-first web apps

## C4 WHATWG URL parser kept in sync with standard -- CUT
- the agent-maintenance angle is the novelty, but the proof is decoration: the real difficulty is a prose standard with ambiguities, and WPT already tests it heavily
- mechanizing the URL spec is large (host/IDNA/percent-encoding); rust-url is a hot path and the only evidence is idna CVE-2024-12224, an old-version corner case
- fails the "hot path, no evidence" filter

## C5 cookie jar refines RFC 6265bis -- MERGE with C6 (rank 2)
- part (b), serializer/parser agreement, is a small roundtrip lemma; part (a) refinement to a prose RFC is only as good as the formalized spec, and the Chrome/Firefox bugs were design flaws (Cookie Crumbles), not Servo bugs: no Servo bug evidence
- privacy/cookie niche and Servo are on-filter; no verified jar exists (my search agrees with prior.md)
- alone it is thin and testable by WPT; combined with C6 it becomes a coherent story

## C6 credentials never leave allowed destinations over redirects -- MERGE with C5 (rank 2)
- noninterference over a finite set of header classes is mostly checkable by testing/exhaustive case analysis; FV alone is weakly necessary
- but "what leaves the browser to which origin" (cookies + Authorization + Referer, across redirects) is one clear privacy invariant with a real-world story (curl CVE-2022-27774, cookie leaks)
- merged title: "Servo net never sends credentials/cookies to a disallowed origin"; state it as a safety invariant over the redirect/cookie state machine, not as 2-safety, to avoid PL framing
- need to find a Servo-specific bug or near-miss to justify; if none, this drops to rank 4

## C7 QUIC control-queue bounds -- CUT
- one real bug, but a bounded-queue invariant is shallow and a fuzz test plus assertion would settle it; the maintainers' fix already restores it
- FV not clearly necessary; fine as a throwaway case study inside C1's toolchain, not a direction

## C8 cert validation across policy changes -- CUT
- Verdict (USENIX Sec 2025) and ARMOR (S&P 2024) are strong prior; policy-change diffing adds little

## C9 CDN purge eventual effect -- CUT
- code is proprietary: only a model of an imagined system, nobody adopts it; TLA+ model would not be tied to real code. Fails "cannot implement/adopt"

## C10 Servo ipc-channel cancellation safety -- CUT
- evidence is a title only (Windows try_recv_timeout); platform-specific OS behavior, not provable cheaply; hot-path-ish

## ranked keep list
1. C1 verified HTTP/1.1 framing agreement (sans-IO core, Verus)
2. C5+C6 Servo net: cookie/credential destination invariants (needs a Servo bug to be convincing)
3. C3 CRDT persistence/import equivalence (narrow core only)
Deferred stretch: C2 (safety-only credit accounting)
