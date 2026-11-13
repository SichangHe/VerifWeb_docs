# Prior work: many sessions in one process without seeing each other's data
(authored by agents unless marked 🧑)

Question 🧑 (Harsha, 11/10 meeting): "So what is the other prior work in this direction?"
Labels: [F] fact with quote+URL in the detail files, [I] inference, [O] opinion. Details: `industry.md` (vendors), `formal.md` (papers); earlier rounds: `../vlm9_shareproc/`, `../vlm10_share/`, `../vlm14_engine/`.

## Plain answer
- [F] in production, Cloudflare Workers, Fastly Compute and Lightpanda already put many tenants or sessions in one process. None of them has a proof. Cloudflare relies on V8 isolates plus memory protection keys and Spectre mitigations, and it reported a production Spectre leak in 2026. Fastly gives each request a fresh Wasm instance. Lightpanda only claims that sessions keep separate state.
- [F] browser-as-a-service vendors do the opposite. Browserbase runs each browser in its own VM, and Browserless runs one browser process per connection. They say outright that this is the safer choice.
- [I] in research, the pieces are proved separately: an SFI/Wasm checker for one sandbox (LFI's verifier proof, VeriWasm, VeriZero), Wasm compilation (vWasm), the Wasm system-call layer (WaVe), and tab and cookie isolation for a browser that uses a process per tab (Quark, 2012).
- [I] nothing we found proves isolation for many tenants inside one JS engine process. We also found no proof covering the tenant lifecycle (creating, freeing and reusing a tenant's memory), JIT output with one region per tenant, or Spectre. Hand-off: we searched specifically for these, so "not found" is meaningful, but we did not read every full text.
- [F] a 2026 paper adds a warning: "Site Isolation is Dead" (S&P 2026) shows agentic browsers leak across sites through IPC channels between the agent and the renderers. [I] So a guarantee for agent sessions must cover the agent and tool channels, not just memory.

## Industry: how each one isolates (industry.md)
- Cloudflare Workers [F]: "Cloudflare can run many isolates within a single process"; V8 was modified "to use memory protection keys to isolate the isolates from each other"; Spectre in production: "leaking up to 12 bit/s with a 99% accuracy" (blog.cloudflare.com, 2026)
  - their 2026 browser product, Kitesurf, runs one isolate per page: "the platform only gets us the boundary between isolates" and "We still have to enforce the same principle at the application level"
- Fastly Compute [F]: "every customer request runs in a fresh instance of the module" and "no memory is shared with any other request handler, nor with any other customer's code"; the guarantee depends on the Wasm compiler being correct, and Wasmtime CVE-2023-26489 broke it
- Deno Deploy [F]: "Each deployment executes its own JavaScript code in its own V8 isolate in its own process" (so tenants are not mixed in one process). Netlify's edge functions run on Deno, and its docs say nothing about isolation.
- Vercel Fluid [F]: concurrent calls share "a global state/process". Only error isolation is stated, and whether different customers share a process was not found.
- Lightpanda [F, source]: "Lets many clients drive one process, each on its own browsing session"; one thread + one V8 isolate per session
  - [I] all sessions share one address space and the Zig runtime, which is not memory-safe, so a memory bug in one session can reach others. No security claim is made.
- Browserbase [F]: "Each browser runs in a dedicated VM"; Browserless [F]: "isolates browser state. That isn't the same as giving every session its own virtual machine, container, host, or network"
- Chrome [F]: on desktop, a renderer process is reused only for the same site. On Android (where partial Site Isolation applies only on devices with at least 2 GB of RAM), in WebView and on iOS, unrelated sites can share a renderer.

## Research with formal guarantees (formal.md)
- one sandbox per region, proved checker: LFI (ASPLOS 2024; verifier proof arXiv 2025), VeriWasm, VeriZero (POPL 2022), RockSalt (verified NaCl checker)
- Wasm runtime: vWasm (proved compilation), WaVe (proved system-call layer), Swivel (Spectre hardening by design, with no proof)
- MPK (Intel memory protection keys): ERIM, Hodor, Donky; no proofs. [F] Hodor: hardware "supports only 16 distinct memory keys"
  - TME-Box (NDSS 2025) scales to "up to 32K concurrent sandboxes", aiming explicitly at "thousands of cloud workers per process", but has no proof
- engine sandboxing: RLBox (Firefox libraries); Mohabi (OSDI 2026) puts the whole JS engine in an SFI cage and checks JIT output before it runs. [F] The paper says its validator and runtime could be formally verified, so they are not verified yet, and it does not separate tabs or origins from each other.
- verified browser kernel: Quark (2012). [F] "We only formally prove inter-domain cookie isolation"; it uses a process per tab and excludes timing channels
- older designs that make the browser an OS for multiple principals: Gazelle (2009), IBOS (2010); no proofs

## Gaps
- [I] what is still open is the combination: many tenants in one JS engine process, a proved per-tenant memory boundary, a proved tenant lifecycle, and the agent's IPC and tool channels.
  - [O] this matches vlm9 directions 1 and 2: a verified tenant-switch kernel, and a per-tenant checker for JIT output
  - [O] TickTock (SOSP 2025) is the closest template for proving the lifecycle
- [I] no proof covers Spectre anywhere. Mitigations work by design or by detection, and Cloudflare reported in 2026 that its detection-based mitigation was bypassed.

## Limits
- I did not use Scholar this round (web search and the papers' PDFs instead). Some page years are not shown on the pages; they are marked "year n/s" in industry.md.
- Read only from search results: Bohannon's Rocq model of Firefox, arXiv 2607.28551, WAVEN (NDSS 2025).
