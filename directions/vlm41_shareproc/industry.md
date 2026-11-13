(authored by agents unless marked 🧑)

vlm41 industry survey: process sharing and tenant isolation
Gathered 2026-11-10. [F]=quoted fact, [I]=my inference. Quotes come from WebFetch/WebSearch tool output (the fetch tool sometimes trims quotes; a few are trimmed, marked "trimmed"). Publication year is given where the source showed it; "year n/s" = not shown by the fetch, check before citing.
Not redone (already in REPORT.md): Cloudflare security-model page, MPK blog, Spectre 2026 blog, V8 sandbox blog.

== Cloudflare Browser Rendering / Browser Run ==
process model: Chromium in a container per browser (not Workers isolates), except new Kitesurf which is isolate based.
[F] "Browser Rendering ... run containers on our network, without even knowing it." and RBI "provides Chromium browsers that run on Cloudflare, in containers" (blog.cloudflare.com/container-platform-preview/, 2025).
[F] container platform runs gVisor/Firecracker/QEMU: "we're able to support gVisor, Firecracker microVMs, and traditional VMs with QEMU." For builds: "we must avoid reusing containers to provide strong isolation between customers." (same post). Which sandbox backs Browser Run: not found.
[F] Tabs vs sessions: "Instead of launching a new browser for each task, consider opening multiple tabs or running multiple actions within the same browser instance." and for clean state "incognito browser contexts," which "isolate cookies and cache with other sessions." (developers.cloudflare.com/browser-run/limits/, 2026). Context: that is the same customer reusing one browser, not cross-tenant.
[F] "Browsers close upon task completion or sixty seconds of inactivity"; keep_alive up to 20 min (same page).
[I] cross-tenant boundary = one container per browser; multiple tabs/contexts inside one Chromium share a browser process tree by customer choice. Official docs do not state a cross-tenant guarantee: "doesn't explain how Browser Rendering isolates sessions" (fetch of developers.cloudflare.com/browser-rendering/, 2026). Not found.
Kitesurf (Cloudflare blog, 2026-08-06, blog.cloudflare.com/kitesurf/): runs in Workers V8 isolates.
[F] "Every next page or out-of-process iframe (OOPIF) uses Dynamic Workers to spin up a long-lived PageScript isolate" with "a clean globalThis and the DOM document object."
[F] "we built this browser on the assumption that every page load is untrusted input and every session starts fresh."
[F] "But the platform only gets us the boundary between isolates." "We still have to enforce the same principle at the application level" (cookie jars per page via SandboxOutbound; "Anything that fails our policy gets a 403").
[I] Kitesurf deliberately mimics Chrome's site-per-process with one isolate per page/OOPIF, but shares worker processes with other Workers tenants per the Workers model. Post does not say whether sessions share an OS process. Not found.

== Deno Deploy / Subhosting ==
process model: one process per deployment, one V8 isolate inside it. Not shared across deployments.
[F] "Each deployment executes its own JavaScript code in its own V8 isolate in its own process." (deno.com/blog/anatomy-isolate-cloud, year n/s, believed 2021)
[F] "While V8 isolates alone do not provide a perfect sandbox, they do a good enough job for many use cases." plus layers: separate OS process per deployment, seccomp syscall filtering, resource monitoring ("Deployments that consume too many resources are terminated"), separate control/data networks, custom restricted Deno build, Rust. (trimmed)
[F] "Layered security is generally considered to be a good practice, but in this case it is a necessity." (trimmed)
[F] Subhosting claim: "Deno Subhosting is a robust platform designed to allow Software as a Service (SaaS) providers to securely run code written by their customers." (docs.deno.com/subhosting/manual/, 2026). Same docs: Deploy and Subhosting run on "the same underlying infrastructure."
[F] Docs page on Deploy Classic: "Deploy Classic applications run on fast, light-weight V8 isolates rather than virtual machines" (docs.deno.com/deploy/manual/, 2026).
[F] Deno Sandbox (separate product, beta announced 2026-02-03 per rywalker.com secondary source): per-sandbox Firecracker microVM; "Regular Deno Deploy apps use V8 Isolates"; not primary-sourced, verify at deno.com/deploy/sandbox.
Whether current (2026) Deploy still uses process-per-deployment: not found in docs.
[I] Strongest process-level answer among isolate vendors: tenant = process, so a V8 bug is contained to one tenant unless escape to OS; contrast with Workers, which packs tenants into one process (see REPORT.md).

== Fastly Compute ==
process model: many requests, including from different customers, in one OS process; each request a fresh Wasm instance.
[F] "every customer request runs in a fresh instance of the module" and "no memory is shared with any other request handler, nor with any other customer's code." (fastly.com/blog/defense-in-depth-stopping-a-wasm-compiler-bug-before-it-became-a-problem, year n/s)
[F] "multiple requests are handled from within a single operating system process." (same post)
[F] "we place instance heaps more than 4GiB apart in virtual-memory space, with guard regions (unmapped memory) between them." (same post)
[F] "Per-request isolation and lightweight sandboxing create an environment focused on performance and security." (docs.fastly.com/products/compute, 2026)
[F] Wasmtime docs-level: default new sandbox per request; opt-in reusable sandboxes (secondary summary of Fastly docs; quote not captured). Process boundary as Spectre mitigation: Bytecode Alliance says Wasm isolation is "lighter than a process" and Wasmtime has Spectre mitigations (trimmed paraphrase, bytecodealliance.org/articles/security-and-correctness-in-wasmtime).
[I] Same shared-process, software-fault-isolation design as Workers; guarantee is memory isolation via Wasm + guard regions, not a hardware/OS boundary. The post itself says the shared process is why a compiler bug could in theory expose data.

== Vercel Fluid compute / Edge ==
process model: Fluid shares one instance and one process across concurrent invocations of the same function (same project). Different projects/customers: docs silent on process, but unit is a microVM in classic mode.
[F] "Instead of using a microVM for each function invocation, multiple invocations can share the same physical instance (a global state/process) concurrently." (vercel.com/docs/fluid-compute, page last_updated 2026-08-24)
[F] "each function uses a microVM for isolation" in traditional serverless (same page).
[F] claimed guarantee is only error isolation: "Unhandled errors won't crash other concurrent requests running on the same instance" and "This means one broken request won't crash other requests". No claim of memory/secret isolation between concurrent requests; shared module scope is the developer's problem (third-party summary, not official quote).
[F] Edge runtime: "built on top of the V8 engine, allowing it to run in isolated execution environments that don't require a container or virtual machine." (vercel.com/docs/functions/runtimes/edge, via search snippet, year n/s). Now deprecated page title "Edge Functions (Deprecated)".
Whether different customers share a Fluid instance/microVM: not found; instance is per deployment function as far as docs imply [I].
[I] Fluid = same-tenant concurrency sharing; the trust boundary stays at the microVM, which is per function/deployment, so sharing a process is among one tenant's own requests. This is the clean contrast to Workers.

== Netlify Edge Functions ==
[F] "All this dynamic processing happens in a secure runtime based on Deno directly from the worldwide network edge location closest to each user" (docs.netlify.com/build/edge-functions/overview/, 2026).
Isolation, process model, sandbox: not found in Netlify docs (the words isolation/process/sandbox do not appear on the overview page).
[F] 2022 HN launch thread (secondary): "Netlify and Supabase use Deno's infrastructure for code execution", and Deno Deploy "can run many isolates very tightly packed on a single machine." Treat as hearsay; Netlify's current docs do not name Deno Deploy.
[I] If still on Deno Deploy/Subhosting, process-per-deployment applies; unverified.

== Lightpanda (source: github.com/lightpanda-io/browser, cloned HEAD 2bb333c, 2026-11-10) ==
process model: ONE OS process serves many CDP connections; one worker THREAD per connection, each with its own Browser and V8 isolate. Not a process per session. No site isolation, no OOPIFs in the Chrome sense.
[F] src/server/Server.zig: "One thread driving a Browser." spawnWorker uses std.Thread.spawn per connection; default --cdp-max-connections 16 (src/Config.zig).
[F] src/mcp/HttpServer.zig: "Lets many clients drive one process, each on its own browsing session. Threading rule: V8 isolates are thread-affine, so each session gets a worker thread that owns its Server and does all of its browser work; sessions run in parallel."
[F] src/browser/Browser.zig: "Pool for FinalizerCallback.Identity structs ... Scoped to the Browser (i.e. the V8 Isolate's lifetime)". So isolate per Browser = per connection.
[F] src/browser/Session.zig: "A Session represents a browsing context group (cookie jar, session storage, navigation history) within a Browser."
[F] src/server/cdp/CDP.zig: "from CDP's point of view our Browser and our Session more or less maps to a BrowserContext." createBrowserContext returns error.AlreadyExists if one exists, so a connection has at most one BrowserContext. Newer Browser.newSession closes the previous session first.
[F] README (raw.githubusercontent.com/lightpanda-io/browser/main/README.md, 2026): "Each connection is routed to its own browsing session — its own page, cookies and memory"; "Two agents that send the same Mcp-Session-Id share one browsing context (sharing)". Session id is the only access control; no claim of a security boundary.
[I] Isolation is thread + V8 isolate + separate heap/cookie jar; all share the process address space, HTTP client pool ("Other sessions may be holding every connection (see --http-max-concurrent)", src/browser/tools.zig) and malloc. No stated security guarantee against hostile pages; Zig memory-unsafe code plus shared process means a memory bug in one session could reach others [I]. Claimed guarantee is state isolation (cookies, page, memory) only. Whether cross-connection isolation is intended as a security boundary: not found.
Note: Lightpanda's V8 build is not documented here to use the V8 sandbox or pointer compression cage; not checked.

== Browserbase ==
process model: one microVM per browser, one session per browser; no sharing.
[F] "Each browser runs in a dedicated VM, providing strong isolation at the hardware virtualization layer." "Browserbase follows a zero-trust architecture, assuming that any browser may be compromised." "Every browser runs in an isolated subnet with strict firewalls to prevent lateral movement." "After each session, the virtual machine is killed and recreated from scratch" (docs.browserbase.com/guides/security, year n/s, 2025-26). Table entry "1 browser per VM".
[F] "No GPU access ... To avoid known security risks associated with shared GPU memory attacks." (same)
[F] Blog (browserbase.com/blog/why-you-can-t-just-run-chromium-in-a-sandbox, year n/s): "the container boundaries typically share the host kernel" ; "a kernel-level escape can collapse both the outer agent sandbox boundary and parts of Chromium's"; packing many browsers in one sandbox "expands the blast radius of a bad or corrupted browser process."
[I] Strongest guarantee in this set; explicitly argues against both containers and shared browsers. Within a session, tabs share the one Chromium, so Chrome's own process policy applies.

== Steel ==
[F] design: one dedicated browser instance per session, "One session for every machine" (launch post/HN, 2024, news.ycombinator.com/item?id=42245573; founder's wording). docs.steel.dev/overview/sessions-api/overview: sessions are "isolated browser instances", each with "its own state, cookies, and storage" (search summary, trimmed).
[F] self-hosted steel-browser: one Docker container, a single active session at a time; creating a new session relaunches the browser (secondary summaries). 
Cloud orchestration details (VM vs container): not found.

== Hyperbrowser ==
[F] docs.hyperbrowser.ai sessions: "isolated browser instances running in the cloud" (summary). Blog claims each session runs in its own container with its own cookies/storage/cache, pre-warmed containers (tech.hyperbrowser.ai blog, 2025-26; marketing, unverified). Kernel-level boundary (container vs VM): not found. Container implies shared host kernel [I].

== Browserless ==
process model: one fresh browser process per connection; explicitly NOT a VM/container per session.
[F] "Browserless gives every connection a fresh remote browser process instead of one shared profile." "Browserless isolates browser state. That isn't the same as giving every session its own virtual machine, container, host, or network." "If your threat model needs those infrastructure boundaries, add them." (browserless.io/blog/session-isolation, year n/s)
[F] persistent sessions use "an isolated userDataDir" per session (docs.browserless.io/baas/session-management/persisting-state).
[I] Honest weakest claim of the set: process boundary + profile dir on shared host/kernel; sessions are separate Chrome processes so Chrome's sandbox is the barrier.

== Chrome (source: chromium.googlesource.com/chromium/src/+/main/docs/process_model_and_site_isolation.md, current main, 2026) ==
[F] default model: tabs/sites get processes under a limit; "Chromium tries to balance 'using more processes to improve parallelism and using fewer processes to conserve memory.'" (trimmed quote of the doc's own text, as returned by the fetch tool)
[F] desktop soft limit from available memory; over it Chromium "randomly reusing same-site processes". Doc's example: a new example.com tab joins an existing example.com process but "a chromium.org tab will create a 101st process." So reuse beyond the limit is same-site only, because process locks prevent mixing locked sites.
[F] Android: "Chromium on Android does not set this soft process limit, and instead relies on the OS to discard processes."
[F] Android Site Isolation is partial: "there is a threshold of about 2 GB of device RAM required to support any level of Site Isolation on Android"; below it "Site Isolation is disabled to avoid requiring multiple renderer processes in a given tab." On >=2 GB: "Chromium only uses dedicated (locked) processes for some sites"; all other sites go into unlocked processes that can serve any site. Isolated set = sites users commonly log into plus sites where this user typed a password, used OAuth, or got a COOP header. Full isolation via chrome://flags/#enable-site-per-process.
[F] Android WebView: "Android WebView does not yet support multiple renderer processes or out-of-process iframes."
[F] OOPIFs reuse aggressively: iframe goes into an existing same-site process "(in any browsing context group)" since iframes are assumed "less resource demanding".
[F] Never shared: "documents from different profiles or StoragePartitions can never share the same renderer process."
[F] Origin-Agent-Cluster: "This is not a security guarantee and may not always be honored."
[F] iOS Chrome (WebKit) lacks "support for out-of-process iframes or Site Isolation."
[F] Historic: process-per-site-instance default at launch let cross-site subframes stay in their parent's process.
[I] Chrome's security guarantee when processes are shared: on desktop full Site Isolation means same process implies same site; the soft limit never mixes sites. The exceptions where unrelated sites share a renderer are Android (unlocked processes for non-isolated sites, <2 GB devices, WebView) and iOS. Quotes above are from the fetch tool's extraction, so confirm wording against the doc before citing.
[I] Relevance to browser-as-a-service: contexts within one Chrome share the browser process and (per MERJ, secondary) not necessarily renderers; for hostile cross-tenant use, vendors that care (Browserbase) put a VM around each browser.

== Patterns across all ==
[I] Granularity of the hard boundary: Browserbase = microVM per browser; Deno Deploy = process per deployment; Browserless/Steel/Hyperbrowser/CF Browser Run = process or container per browser; Fluid = microVM per function, process shared among that function's own concurrent requests; Workers/Fastly/Lightpanda = many tenants/sessions in one process with a language-level isolate, Wasm instance, or thread boundary.
[I] Only Fastly (guard-region layout, fresh instance) and Cloudflare (other report) state a memory-isolation argument for shared-process; Lightpanda and Vercel claim state/error isolation only.
