# formal-verification-first web directions (vlm28_fvfirst)

(authored by agents unless marked 🧑)

## Bottom line

- We generated 10 candidates: my own list, plus ideas from GPT (gpt_ideas.md) and Gemini (gemini_ideas.md).
- A separate critic subagent, reviewing as a formal-verification researcher, kept 3 and deferred 1. It cut the other 6 as "FV is decoration", strong prior work, or not implementable. The full critique is in critique.md.
- The manager asked for 8-10 directions. Only 3 or 4 survive an honest critique (opinion). The cut ones are listed at the end with the reason for each.
- Scholar found no prior formal verification for HTTP/1.1 framing, verified cookie jars, or HTTP/2 flow control. Details are in prior.md.
- Evidence files: bugs.md and bugs2.md hold verbatim quotes with URLs, re-read from the primary sources. All files are in this directory.

## Keep 1: the proxy and the backend agree on where each request ends (Pingora, hyper)

- Theorem: for every byte stream, a verified HTTP/1.1 framing core splits it into the same request sequence as the RFC 9112 spec. The proof covers early responses, unread bodies, Upgrade, and connection reuse. If both proxy and backend refine that spec, they agree with each other.
- Why only a proof settles it: it is a property over all byte streams and two programs. Differential fuzzing finds bugs but cannot show they are absent (the HTTP Garden, arXiv 2024; T-Reqs, CCS 2021).
- What FV adds: a mechanized, connection-level framing spec plus refinement of a real Rust core. Verified parsers such as EverParse and Vest (USENIX Security 2025) cover message syntax, not connection state (critic's inference).
- Real bugs:
  - Pingora CVE-2025-4366 (2025, https://rustsec.org/advisories/RUSTSEC-2025-0037.html): "did not properly drain the downstream request body on cache hits. This allows an attacker to craft malicious HTTP/1.1 requests which could lead to request smuggling or cache poisoning."
  - Pingora CVE-2026-2833 (2026, https://nvd.nist.gov/vuln/detail/CVE-2026-2833): "causing the proxy to pass through the rest of the bytes on the connection to a backend before the backend has accepted the upgrade."
  - hyper CVE-2021-21299 (2021, RUSTSEC-2021-0020)
- Tool: Verus, on a sans-IO core (protocol logic with no I/O). Verus handles async code poorly.
- Prior work: Scholar returned no verified HTTP/1.1 framing.

## Keep 2: Servo never sends cookies or credentials to an origin that should not get them

This merges two candidates: the cookie jar, and credentials across redirects.

- Theorem: across any chain of redirects and any cookie strings, Servo's network layer attaches a cookie or an Authorization header only to the destinations RFC 6265bis and the fetch rules allow. Second, any Cookie header Servo emits parses to the same pairs on a verified server-side parser.
- Why only a proof settles it: the bugs come from odd strings and long redirect chains, so the space is unbounded. The critic warns that the redirect part alone is "mostly checkable by testing" (opinion).
- What FV adds: refinement of a real browser network stack to a mechanized cookie RFC. Neither the critic's search nor Scholar found a verified cookie jar. WebSpec (S&P 2023) models the browser; it does not verify an implementation.
- Real bugs:
  - Chrome CVE-2022-2860 (2022, https://nvd.nist.gov/vuln/detail/CVE-2022-2860): "allowed a remote attacker to bypass cookie prefix restrictions via a crafted HTML page." The underlying research, Cookie Crumbles (USENIX Security 2023), says: "We found that this design introduces a novel attack vector that can bypass even the __Host- prefix."
  - Werkzeug CVE-2023-23934 (2023, https://github.com/advisories/GHSA-px8h-6qxv-m22q): "Werkzeug <= 2.2.2 will parse the cookie `=__Host-test=bad` as `__Host-test=bad`."
  - curl CVE-2022-27774 (2022, https://curl.se/docs/CVE-2022-27774.html): "curl leaking credentials to other servers when it follows redirects from auth protected HTTP(S) URLs"
- Gap: no Servo-specific bug was found. The critic says that without one, this idea drops below Keep 3.
- Fit: the privacy/cookie niche and Servo. It also connects to the kept SSO direction, since session cookies are what SSO hands out.
- Tool: Verus.

## Keep 3: a collaborative document equals its own reload (Loro, Yjs, Automerge; extends TeamTypeV)

- Theorem: for a small Rust CRDT core with a buffer of pending operations, importing a snapshot gives the same state as replaying the same operations. Any two replicas that hold the same set of operations show the same document, whatever the delivery order. (A CRDT is a data type whose replicas merge without coordination.)
- Why only a proof settles it: the claim covers all delivery orders and all causal gaps. The known bugs hide in rare interleavings of a gap with a snapshot. Users or fuzzing found those bugs, so a proof adds only "the whole class is absent" (critic).
- What FV adds: existing convergence proofs cover the abstract merge algorithm. This would cover the persistence and sync layer. Zakhour et al. (PACMPL 2023, via Scholar): "very complex CRDTs like Automerge ... None of the tools in our evaluation is able to prove them"
- Real bugs, all reports from 2023 to 2026:
  - Loro #1215 (2026, https://github.com/loro-dev/loro/issues/1215): "the pending changes enter the oplog but are never applied to the document state."
  - Yjs #824 (2026, https://github.com/yjs/yjs/issues/824): "So the doc and its own reload show different content."
  - Automerge #595 (2023), titled: "Automerge.save does not persist orphan changes, potentially leading to a loss of convergence"
- Fit: distributed, and builds directly on TeamTypeV. Risks: it may read as "CRDT theory" (too PL), and the web link is through local-first web apps.
- Tool: Verus.

## Deferred: HTTP/2 flow-control credit is eventually returned (h2, Pingora)

- Theorem: under fair scheduling, with an upstream that eventually drains or times out, the flow-control credit of every cancelled stream eventually returns, so no stream waits forever.
- Real bugs:
  - pingora #910 (2026, https://github.com/cloudflare/pingora/issues/910): "a downstream `RST_STREAM` is not acknowledged by pingora if it arrives while the proxy is blocked writing the request body to the upstream"
  - h2 #975 (2026, https://github.com/hyperium/h2/issues/975): "two h2 peers can deadlock permanently."
- Why only a proof settles it: this is liveness, and the counters stay consistent while the connection is stuck. Scholar found no FV of HTTP/2 flow control.
- The critic cut it as "too PL and too costly" because it means liveness for async Rust.
- My opinion: this is the most FV-central candidate. It matches the human's liveness background and the Anvil method (an embedding of TLA, a temporal logic, in Verus). Whether the cost is acceptable is a judgment call for the human.

## Cut, with reason (critic's opinion)

- WHATWG URL proofs kept in sync with the living standard: the proof is decoration, the Web Platform Tests already cover the parser heavily, and the parser is on the hot path with thin bug evidence (only idna CVE-2024-12224).
- QUIC control-queue bound in quinn (GHSA-hmxj-32vh-65vr, 2026): the bug is real ("only one of them is bounded"), but an assertion plus fuzzing would settle it.
- Certificate validation across policy changes (rustls-webpki RUSTSEC-2026-0099): strong prior work in Verdict (USENIX Security 2025) and ARMOR (S&P 2024).
- CDN purge eventually takes effect: the code is proprietary, so nothing could be adopted. Cloudflare's 2026-11-06 status page does say "Stale content may be served until expired."
- Servo ipc-channel cancellation safety: the only evidence is an issue title.
- Wasm compiler (Cranelift): dropped early because of strong prior work (Crocus ASPLOS 2024, Arrival PLDI 2025) and because it is too PL.
