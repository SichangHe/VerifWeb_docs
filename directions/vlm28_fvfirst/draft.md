# draft candidates (authored by agents)

Sources: bugs.md, bugs2.md (verbatim quotes + URLs), prior.md (Google Scholar, 2020+), gpt_ideas.md, gemini_ideas.md.

C1 proxy/backend agree on request boundaries (Pingora, hyper)
- prove: for every byte stream, proxy and backend split it into the same request sequence, incl. early responses, unread bodies, Upgrade, connection reuse
- why proof: 2-safety over two programs and all byte streams; differential fuzzing (HTTP Garden 2024, T-Reqs CCS 2021) finds bugs but cannot show absence
- FV contribution: relational stream refinement across parser + connection manager of two components; parser correctness alone (EverParse, Vest) insufficient
- bugs: hyper CVE-2021-21299; Pingora CVE-2025-4366 (cache hit body not drained), CVE-2026-2833 (Upgrade)
- tool: Verus (+Vest parsers)
- prior: none found on Scholar for verified HTTP/1.1 parsing; EverParse 2019, Vest USENIX Sec 2025

C2 HTTP/2 flow-control credit returned and no stream starves (h2 + Pingora)
- prove: under fair scheduling and an upstream that eventually drains or times out, credit of every cancelled stream is eventually returned; live streams progress
- why proof: liveness; safety counters stay consistent ("nothing errors"), a finite test cannot tell slow from stuck
- FV contribution: liveness of async Rust (tokio futures, cancellation) with linear ghost credit tokens; Anvil/Lion did controllers/runtimes, not protocol credit across a proxy
- bugs: pingora #910 2026 zombie streams; h2 #975 2026 permanent deadlock; h2 #853 2025
- tool: Verus + Anvil-style TLA embedding
- prior: Scholar found no FV of HTTP/2 flow control (PRETT2 ESORICS 2024 is fuzzing)

C3 collaborative-editing convergence incl. save/load/sync paths (Automerge/Yjs/Loro; extends TeamTypeV)
- prove: any two replicas that have received the same set of ops show the same doc, regardless of delivery order, pending ops, snapshot vs update import, save/reload
- why proof: quantifies over all delivery orders and causal gaps; existing bugs live in rare gap+snapshot interleavings
- FV contribution: convergence proofs cover the abstract merge; this extends to the persistence/sync layer (a doc equals its reload) of a production Rust CRDT; Zakhour 2023: no tool could prove Automerge
- bugs: Loro #1215 2026 (pending ops never applied after snapshot), Yjs #824 2026 (doc and its reload differ), Automerge #595 2023
- tool: Verus
- prior: Zakhour et al. PACMPL 2023; Gomes et al. 2017 (pre-2020)

C4 WHATWG URL parser proof kept in sync with the living standard (rust-url, used by Servo)
- prove: rust-url refines a mechanized WHATWG URL spec; after every spec commit, agents re-establish the proof or report the exact divergence
- why proof: parser agreement over all strings; differential cross-testing (S&P WS 2022) samples
- FV contribution: proof maintenance against an evolving prose standard (not code/toolchain evolution like KVerus 2026)
- bugs: idna CVE-2024-12224 (Punycode masking); Orange Tsai Black Hat 2017 parser inconsistency → SSRF
- tool: Verus + agents
- prior: Scholar found no mechanized URL standard

C5 cookie handling: Servo cookie jar refines RFC 6265bis; browser serializer and server parser agree
- prove: (a) jar never stores/sends a cookie violating prefix/SameSite/domain rules; (b) any Cookie header the browser emits parses to the same name/value pairs on a verified server parser
- why proof: all cookie strings and orderings; bugs are odd-string corner cases
- FV contribution: refinement to a mechanized RFC + relational browser/server property
- bugs: Chrome CVE-2022-2860 (__Host- bypass, Cookie Crumbles 2023); Werkzeug CVE-2023-23934 ("=__Host-test=bad" parsed as "__Host-test=bad")
- tool: Verus
- prior: WebSpec S&P 2023 (browser model, not implementation); Cookie Crumbles

C6 credentials never leave their allowed destinations across redirects (reqwest / Servo net)
- prove: noninterference: changing a secret credential cannot change bytes sent to non-permitted origins, over arbitrary redirect chains
- why proof: 2-safety (two runs), unbounded redirect chains
- FV contribution: relational proof over mutable header state in a real Rust HTTP client
- bugs: curl CVE-2022-27774 2022
- tool: Verus
- prior: not searched on Scholar

C7 QUIC control-queue memory bounds (quinn-proto)
- prove: every outbound control queue is bounded for all frame sequences
- why proof: bug needs crafted 2-step sequence; maintainers' informal proof in a comment missed a path
- FV contribution: resource-bound invariants for a sans-IO transport
- bugs: quinn GHSA-hmxj-32vh-65vr 2026 ("two code paths that push into this queue, and only one of them is bounded")
- tool: Verus
- prior: Ivy QUIC (safety, testing, liveness untreated)

C8 certificate validation across policy changes (rustls-webpki / Verdict)
- prove: old and new validators agree except on an approved change; name-constraint semantics = language inclusion
- bugs: RUSTSEC-2026-0099 2026 wildcard vs permitted subtree
- prior: Verdict USENIX Sec 2025, ARMOR S&P 2024 (strong prior)

C9 CDN purge eventually takes effect everywhere
- bugs: Cloudflare status 2026-11-06 "Stale content may be served until expired"
- issue: CDN code proprietary; implementable only as own model/prototype
- prior: none found

C10 Servo ipc-channel cancellation safety
- bugs: ipc-channel #450 2026 "try_recv_timeout loses messages on Windows" (title only)
- weak evidence

dropped already: Wasm/Cranelift (Crocus ASPLOS 2024, Arrival PLDI 2025 strong prior; too PL)
