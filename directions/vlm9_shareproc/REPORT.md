# Sharing one process across tabs or tenants
(authored by agents unless marked 🧑)

Labels: [F] fact from a source I fetched, [I] inference, [O] opinion.
Background sources (all entries marked fetched or unverified): `sources.md`. Independent ChatGPT ideas: `gpt_out.md`.

## What exists today
Cloudflare already shares processes across tenants. Browsers refuse to.
- [F] Cloudflare docs (https://developers.cloudflare.com/workers/reference/security-model/): "Cloudflare can run many isolates within a single process"
- [F] Cloudflare hardening blog (https://blog.cloudflare.com/safe-in-the-sandbox-security-hardening-for-cloudflare-workers/): "we have deployed internal modifications to V8 to use memory protection keys to isolate the isolates from each other"; "With the new sandbox layout, we use strictly rotating memory protection keys"; their stated limit is that an attacker who can run arbitrary machine code "could disable memory protection keys"
- [F] V8 sandbox (https://v8.dev/blog/sandbox): "it is assumed that an attacker can read and write arbitrarily inside the V8 Sandbox". It protects memory outside the sandbox, not one tenant from another.
- [F] Chrome Site Isolation puts different sites in different processes. It assumes the renderer can be compromised and that Spectre attacks are possible (see `sources.md`).
- [F] Fastly Compute and Wasmtime use one Wasm instance per request. Wasmtime CVE-2023-26489 let a guest compute a 35-bit address where Wasm allows 33 bits, which allowed out-of-bounds memory access.

## Real breakage: Spectre is the live problem
- [F] Schwarz et al., "Dynamic Process Isolation" (https://arxiv.org/abs/2110.04751): a remote Spectre attack on Workers "capable of leaking 120 bit/h". Their fix "only isolates suspicious worker scripts following a detection mechanism".
- [F] Cloudflare, 2026 (https://blog.cloudflare.com/revisiting-spectre-attacks-on-workers/): "we managed to demonstrate a remote Spectre attack reliably leaking up to 12 bit/s with a 99% accuracy in the production environment of Cloudflare Workers"; "Detection cannot happen only after a script finishes"
- [I] The detection-based defense was bypassed. Memory-safety bugs are also a risk, but Spectre is the one with a recent public production demonstration.

## Prior local results (corrected)
- [F] Node toy workload: a vm context costs about 441 KB per tab and a process about 9,225 KB, roughly 21× (`cx_synth/REVIEW.md`). The earlier 0.78 MB worker figure measured workers that had already exited, so it is wrong. Chrome savings were not measured.
- [F] Verus proofs of two models: a two-realm heap with a write barrier (24 verified), and V8's external-pointer table plus Wasm bounds checks (the buggy 35-bit lowering was rejected) (`vlm2_iso/`). These are models only and do not prove anything about V8's actual code.

## Directions ([O] all three are proposals)
1. Verified tenant-switch kernel for a V8 embedder
   - idea: prove the small allocator/scheduler that assigns each tenant a V8 sandbox and an MPK key; theorem: while tenant t runs, only t's pages (or pages shared read-only) are accessible
   - new: Cloudflare does this without a proof; [I] no proof of this lifecycle found (reuse of keys and pages, GC threads, teardown)
   - first step: extend `tabiso_verus` with page ranges, keys and alloc/free/reuse; inject key-reuse bugs into a tiny Rust embedder
   - risk: by Cloudflare's own statement, machine-code execution defeats MPK, so this cannot replace Site Isolation for browsers
2. Check JIT output against a per-tenant policy before running it
   - idea: before a JIT page becomes executable, a checker confirms its loads and stores stay in the current tenant's cage, it has no `WRPKRU` (the instruction that changes MPK permissions), and it calls the runtime only through approved entry points; the JIT itself stays unverified
   - new: VeriWasm (Wasm) and LFI (a software sandbox, verifier proved in arXiv 2508.15898) check code for one fixed sandbox; this checks many tenant cages chosen at run time inside a single JS JIT
   - first step: handle about 20 address and jump patterns from one V8 tier; reject synthetic escapes and the 35-bit bug pattern
   - risk: JIT code calls C++ runtime functions constantly, so either the policy gets too permissive to mean anything or the set of trusted entry points becomes huge
3. Leakage-budgeted co-location (measurement-heavy)
   - idea: replace "detect suspicious scripts" with an accounting budget, such as CPU bursts, timer-like I/O and time spent co-located; move a tenant to its own process before the budget runs out, and prove the accounting fails safe
   - new: directly answers the 2026 bypass of detection ("cannot happen only after a script finishes")
   - first step: two isolates and a synthetic cache covert channel; sweep the budget and measure bits leaked against the rate of benign tenants isolated by mistake
   - risk: there is no universal bound over unknown microarchitectural channels, so the claim can only be "bounded on hardware H for channels C"

## Dead ends ([O])
- "use MPK for Workers": Cloudflare already ships it
- verifying all of V8 in Verus: wrong scope
- the snapshot JS verifier (`dynstate`): wrong layer; it does nothing against engine bugs or Spectre
- "zero leaks measured" presented as isolation: measurement can refute a security claim but cannot prove one

## Unverified
- ChatGPT cited Icarus (verified SpiderMonkey JIT parts) and Mohabi (SFI for the Firefox JS engine) as close prior work; I have not opened either source. Both need checking before anyone claims novelty for direction 2.
