# What formal verification could add to a browser built for agents
(authored by agents unless marked 🧑)

Labels: [F] fact with quote and source, [I] inference, [O] opinion. Evidence: `lightpanda.md` (source read at HEAD 6cfc29e1df1b, 2026-11-07; not built or run), `prior.md` (OpenAlex, abstracts only, so citation counts are OpenAlex's). Nothing was published or filed.

## Takeaway
- [I] Lightpanda's bugs are not in exotic engine code. They are in the small policy core: URL origin parsing, cookie rules, credential handling on redirects, which requests pass the filters, and per-session state. That core is small enough to verify, and every bug there breaks the property agents rely on.
- [O] Best target: a Quark-style verified kernel for an agent browser. It proves sessions cannot see each other and every outbound request obeys the session's policy, so many agent sessions can safely share one process. This is the 🧑 "agents need efficient browsers" argument turned into a verification thesis.
- [O] A whole verified JS engine is still too big. No verified JS engine of any kind was found, and the largest agent-written proof found is ~6K lines.

## Lightpanda facts that matter
- [F] one process, one thread + one V8 isolate per connection: Browser.zig:35-37 "You can create multiple browser instances. A browser contains only one session."; Env.zig:57 "The Env maps to a V8 isolate"
- [F] no OS sandbox code found; no site isolation; CDP has no authentication (issue #3452)
- [F] vendor claim, not reproduced: "Memory (peak, 100 pages) | 123MB | 2GB | ~16x less" (README)
- [F] 11 GitHub Security Advisories, 2026-05 to 2026-11 (https://github.com/lightpanda-io/browser/security/advisories). Examples:
  - GHSA-mq6p-m9cc-q432 (critical): "URL parser misidentifies page origin for URLs containing @ in the path - Same-Origin Policy bypass"
  - GHSA-36mm-v3c2-24cc (critical): "fetch() and XMLHttpRequest attach session cookies to cross-origin requests regardless of credentials mode"
  - GHSA-mcw6-8p83-pm3h: "Credential headers leak across cross-origin redirects"
  - 3 SameSite cookie bugs and 1 cookie-domain bug; 2 unauthenticated CDP/MCP control bugs
  - GHSA-7c5w-p4q2-98gf: "WebSocket frame length integer overflow"; GHSA-3jpq-xwf3-rwr6: "Heap buffer overflow in `Frame.buf`", and "Release builds strip assertions"
- [F] our own finding: `--block-urls` does not block WebSocket, because WebSocket "never enters the request pipeline" (`../cloud/p5_lightpanda_blockurls.md`)
- [F] issue #2622: double release of a pooled arena, RSS grows to ~18 GiB
- [I] count: 7 of 11 advisories plus our WebSocket finding are policy-logic bugs, not memory bugs
- [F] only other own-engine agent browser found: Obscura (Rust + V8). Servo/Ladybird-based ones not searched.

## Prior work
- [F] Quark (USENIX Security 2012, cited 41): "a browser whose kernel has been implemented and verified in Coq … including tab non-interference, cookie integrity and confidentiality, and address bar integrity" (https://www.usenix.org/conference/usenixsecurity12/technical-sessions/presentation/jang)
- [F] not found: a Quark successor since 2012; a verified URL or HTML parser; a verified filter-list engine; any academic paper on a browser designed for agents; any verified JS engine
- [F] scale of agent-written proofs: "approximately 6,000 lines of Rocq proof … developed in 94.5 hours" (Claude Code + Opus 4.6, ICFP 2026 experience report; URL in prior.md)

## Targets
1. Verified multi-session kernel (per-session non-interference)
   - claim: N agent sessions in one process (one isolate each) cannot read each other's cookies, storage, caches or network results
   - new [I]: Quark proved tab non-interference with one process per tab; here the selling point is sharing a process, which is what makes agent browsers cheap. The threat model (untrusted pages steering agents, tenants of a hosted service) is new.
   - first step: list every piece of state shared across Lightpanda's worker threads (`App` fields, `CorsStore`, `SingleFlight`, caches); write a small model of session state plus the kernel API; prove non-interference for it
   - risk: Spectre and V8 bugs sit below the proof, so the guarantee is only "no logic leak"; pointing to vlm10_share, Spectre may make sharing hard to defend
2. Verified network policy (complete mediation)
   - claim: every outbound connection (fetch, XHR, navigation, redirect hop, WebSocket, subresource) passes the session's URL/IP filter and correct cookie/credential rules
   - new [I]: browsers have never needed operator-defined request policy; agent operators do (block internal hosts, limit exfiltration). Our WebSocket bypass and 5 cookie/credential advisories show it fails today.
   - first step: model Lightpanda's request paths as one function; prove "no connection without a filter decision"; check the model against the WebSocket bug and the redirect/cookie advisories as known failures
   - risk: reviewers may see it as a firewall proof; value depends on agent operators wanting policy in the browser, not a proxy
3. Verified origin core: URL parser, origin equality, cookie rules
   - claim: the WHATWG URL parse and origin/site computation and RFC 6265bis cookie matching are correct against the spec
   - new [I]: no verified WHATWG URL parser found; GHSA-mq6p shows this bug class reaches SOP
   - first step: write it in Verus (or Zig with a Verus model), test it against the WPT URL tests, replace Lightpanda's 1704-line URL.zig in a branch
   - risk: smallest and most doable, but alone it reads as "a verified parser", not a thesis; best as a component of target 1 or 2

## Verified JS engine: doable now?
- [O] not as a whole. No verified JS engine exists, and the largest agent-written proof found (~6K lines) is far below an engine. vlm8 story A (Verus proofs of single builtins) is the realistic slice.
- [I] an agent browser only needs the kernel to be verified, as in Quark; the JS engine can stay untrusted inside an isolate

## Needs the human's judgment
- whether target 1 (sharing a process safely, with proofs) is the thesis framing the human wants, with 2 and 3 as parts
- whether to build on Lightpanda (Zig, AGPL, fast-moving) or write a small new kernel
