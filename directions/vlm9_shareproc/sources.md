# vlm9 shared-process isolation: sources (fetched 2026-11-06)
(authored by agents unless marked 🧑)
Legend: [F] fetched, quote from the fetch tool's extraction (WebFetch summarizes via a small model; quotes may be imperfect, re-check before citing). [U] unverified/not fetched.

## Cloudflare Workers / workerd
- (1) Sharing+isolation. https://developers.cloudflare.com/workers/reference/security-model/ [F]
  - "Importantly, this means Cloudflare can run many isolates within a single process."
  - "a customer who signs up for the Free plan will not be scheduled in the same process as an Enterprise customer."
  - "The layer 2 sandbox uses Linux namespaces and `seccomp` to prohibit all access to the filesystem and network."
- (2) Threat model. same URL [F]
  - "Any time you have more than one tenant running code on the same machine, Spectre attacks are possible."
  - Blog: https://blog.cloudflare.com/mitigating-spectre-and-other-security-threats-the-cloudflare-workers-security-model/ [F] "We can't live life pretending that no further bugs will ever be discovered."
  - Note: page says protections apply to hosted Workers; local workerd lacks some.
- (3) Breakage.
  - Schwarzl et al., arXiv 2110.04751 https://arxiv.org/abs/2110.04751 [F]: remote Spectre attack on Workers "is capable of leaking 120 bit/h." Fix: "a process isolation mechanism that only isolates suspicious worker scripts following a detection mechanism." (DyPrIs, ESORICS 2022, "Robust and Scalable Process Isolation against Spectre in the Cloud", DOI 10.1007/978-3-031-17146-8_9; FP rate 0.61%; PDF https://gruss.cc/files/scalableisolation.pdf [U, only seen in search listing])
  - Cloudflare blog admits: "No one has 'fixed' Spectre. Not even when using heavyweight virtual machines." [F]; "we have not been able to develop an attack that actually works in production." [F]
  - Mitigations: "`Date.now()` returns the time of the last I/O. It does not advance during code execution."; "multi-threading and shared memory are not permitted in Workers." [F]
  - Cost of strict isolation: "the CPU cost can easily be 10x what it is with a shared process." [F]
  - No Workers-specific CVE found/fetched. [U]

## Deno Deploy
- (1) https://docs.deno.com/deploy/manual/ [F]: "Deploy Classic applications run on fast, light-weight V8 isolates rather than virtual machines, powered by the Deno runtime."
  - Page says nothing on process sharing or threat model. Possible deeper source: deno.com blog "anatomy of an isolate cloud" [U, not fetched].
- (2) not found. (3) none fetched.

## Fastly Compute
- (1) https://docs.fastly.com/products/compute [F]: "Per-request isolation and lightweight sandboxing create an environment focused on performance and security." and "Each incoming request creates one function instance."
  - Wasm/Lucet->Wasmtime: process sharing details not on this page. [U]
- (2) no explicit threat model on page. Wasmtime/Swivel/VeriWasm below cover Fastly's stack.
- (3) VeriWasm paper "describes how VeriWasm was deployed at Fastly" (search listing, NDSS 2021) [U page; abstract not fetched].

## Vercel Edge Functions
- (1) https://vercel.com/docs/functions/runtimes/edge [F]: "The Edge runtime is built on top of the V8 engine, allowing it to run in isolated execution environments that don't require a container or virtual machine."
  - "Dynamic code execution is not available in Middleware with the `edge` runtime configured for security reasons." Docs now recommend migrating to Node.js; Next.js 16.3 drops `runtime='edge'`.
- (2) no threat model stated. (3) none fetched.

## V8 isolates + V8 sandbox
- (1)/(2) https://v8.dev/blog/sandbox [F]
  - "it is assumed that an attacker can read and write arbitrarily inside the V8 Sandbox."
  - "The goal is to prevent memory corruption outside of the sandbox."
  - "The basic idea behind the sandbox is to isolate V8's (heap) memory"
  - Software-only: "no suitable hardware feature is available today"
  - Scope: only heap inside sandbox. Isolate-to-isolate isolation in one process is NOT a stated goal on this page (inference).
- (3) Bypasses: same page [F]: attacker "would first need an additional vulnerability: a V8 Sandbox bypass."; "there are still a number of issues to resolve before it becomes a strong security boundary"; "recent V8 exploits already had to work their way past the sandbox".
  - Specific bypass CVE IDs: not fetched. [U] (search attempt was blocked.)

## Chrome Site Isolation
- (1) https://www.chromium.org/Home/chromium-security/site-isolation/ [F]
  - "ensures that pages from different websites are always put into different processes, each running in a sandbox."
  - Same-site origins share a process: "allows multiple origins within a site to share the same process."
  - "only a subset of sites are isolated on Android, to reduce overhead."
- (2) same URL [F]: "determined attackers will be able to find a way to compromise a renderer process." and Spectre attacks "make reading arbitrary renderer process memory possible, even without bugs in Chrome."
- (3) Chrome-specific CVEs: not fetched. [U]

## Wasm isolation: Wasmtime, Lucet/RLBox, Fastly
- (1)/(2) https://docs.wasmtime.dev/security.html [F]
  - Goal: "execute untrusted code in a safe manner inside of a sandbox."
  - "Wasmtime implements what's necessary for the WebAssembly specification, for example memory isolation between instances."
  - Spectre: "Wasmtime implements a few forms of basic spectre mitigations at this time"; "Mitigating Spectre continues to be a subject of ongoing research"; default memory accesses rely on page faults, no bounds checks.
- (3) Wasmtime CVEs:
  - CVE-2023-26489, https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-ff4p-7xrq-q5r8 [F]: "a wasm-controlled load/store operation could read/write addresses up to 35 bits away from the base of linear memory." (guest OOB, x86_64 Cranelift)
  - Advisory list https://github.com/bytecodealliance/wasmtime/security/advisories [F], no CVE IDs shown (GHSA only). Titles seen, Oct 2026: GHSA-897f-g5gm-fmxm (Critical) "Bit-packing in Cranelift compiler causes silent overflow and miscompilation"; GHSA-mghf-wjfp-p5xm (Critical) "Cranelift backend on aarch64 can jump to incorrect target on large Wasm `br_table` instruction"; GHSA-qw58-7h65-crq2 (Low) "Cross-engine type confusion with host-created struct-types-with-supertypes". Escape impact is my inference, not stated. Not opened individually.
  - Swivel https://arxiv.org/abs/2102.12730 [F]: "Unfortunately, Spectre attacks can bypass Wasm's isolation guarantees." Wasm is "used in production to isolate different clients on edge clouds and function-as-a-service platforms."

## Prior work on verifying/measuring shared-process isolation
- DyPrIs / Dynamic Process Isolation (Schwarzl, Borrello, Kogler, Varda, Schuster, Gruss, Schwarz; ESORICS 2022): arXiv 2110.04751 [F]; measured leakage on Workers; HPC-based detection; Black Hat Asia 2022 slides https://i.blackhat.com/Asia-22/Friday-Materials/AS-22-Borrello-Dynamic-Process-Isolation.pdf [U]
- Swivel (Narayan et al., USENIX Sec 2021), arXiv 2102.12730 [F]: Spectre-hardened Wasm compilation; "randomized ... under 10.3% overhead", deterministic 3.3%-240.2%.
- VeriWasm (Johnson et al., NDSS 2021, "Trust but verify: SFI safety for native-compiled Wasm"): static offline verifier of x86-64 from Lucet; https://www.ndss-symposium.org/ndss-paper/ (search result only) [U]; code https://github.com/PLSysSec/veriwasm [U]
- RLBox (Narayan et al., USENIX Sec 2020) https://www.usenix.org/conference/usenixsecurity20/presentation/narayan; arXiv 2003.00572 [search listing only, U]: type-system-enforced sandbox boundary, Wasm or process sandbox in Firefox.
- Okapi (arXiv 2312.08156) "Efficiently Safeguarding Speculative Data Accesses in Sandboxed Environments" [title only, U].
- Iris / verified Wasm: NOT searched. [U]  (Kolosick et al. "Isolation without taxation" arXiv 2105.00033 appeared as a title only, U.)
