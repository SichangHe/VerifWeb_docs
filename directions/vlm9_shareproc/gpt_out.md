(authored by agents unless marked 🧑)

The most promising framing is not “replace processes with verification.” It is: identify the smallest same-process mechanism whose invariants, if proved or continuously measured, justify removing a process boundary.

Two 2024–2026 results materially tighten the novelty bar: Icarus verifies real SpiderMonkey JIT components, and Mohabi now sandboxes the Firefox JS engine with SFI. Mohabi says it uses “software-based fault isolation (SFI) to ensure JavaScript engine bugs cannot affect the rest of the browser.” [CSE Web+1](https://cseweb.ucsd.edu/~dstefan/pubs/smith%3A2024%3Aicarus.pdf?utm_source=chatgpt.com)

### 1. verified multi-tenant compartment manager for V8/workerd

- idea: make a tiny allocator/scheduler the security kernel for tenant → V8 sandbox → pages → pkey; prove ownership, key reuse, sandbox placement, tenant switches, GC/helper-thread entry, exceptions, and teardown
- concrete theorem: while executing tenant t, every accessible tenant page is owned by t or explicitly shared-read-only; no reachable out-of-bounds address lands on another accessible tenant
- new: Cloudflare already has MPK + one isolate per V8 sandbox, so MPK itself is not novel; the gap is a machine-checked lifecycle invariant tied to the real allocator/scheduler
- Cloudflare explicitly says “we use strictly rotating memory protection keys” and arranges no same-key sandbox in the relevant 32-GiB neighborhood. [Cloudflare Blog](https://blog.cloudflare.com/safe-in-the-sandbox-security-hardening-for-cloudflare-workers/)
- vs V8 sandbox: V8 assumes “an attacker can read and write arbitrarily inside the V8 Sandbox”; it protects outside memory, not your cross-tenant scheduler/allocator correctness. [V8](https://v8.dev/blog/sandbox?utm_source=chatgpt.com)
- vs RLBox/VeriWasm: those protect library/SFI boundaries; RLBox uses “static information flow enforcement, and lightweight dynamic checks,” while VeriWasm is “a static offline verifier for native x86-64 binaries compiled from Wasm.” [USENIX+1](https://www.usenix.org/conference/usenixsecurity20/presentation/narayan?utm_source=chatgpt.com)
- 2 weeks: extend your Verus heap model to page ranges+pkeys+alloc/free/reuse; implement the same state machine in a tiny Rust V8 embedder and inject key-reuse/placement bugs
- biggest risk: Cloudflare's MPK threat model excludes arbitrary machine-code execution; their text says if attackers had it, “they could disable memory protection keys.” Thus this alone cannot replace browser Site Isolation. [Cloudflare Blog](https://blog.cloudflare.com/safe-in-the-sandbox-security-hardening-for-cloudflare-workers/)

Assessment: highest feasibility; respectable novelty only if the proof connects closely to executable runtime code rather than another abstract model.

### 2. tenant-relative verifier for dynamically generated JS machine code

- idea: before any JIT page becomes executable, validate that machine code cannot escape the *current tenant*: memory addresses must use the tenant cage/base, WRPKRU is forbidden, indirect control flow is constrained, and host access uses typed gates
- key distinction: validate an isolation policy, not JavaScript semantic correctness; the JIT/compiler can remain buggy provided its output passes the checker
- vs VeriWasm: same “verify after compilation” philosophy, but VeriWasm handles Wasm binaries with a static sandbox; your policy has dynamic V8/SpiderMonkey tenant state and runtime/JIT transitions. [NDSS Symposium](https://www.ndss-symposium.org/ndss-paper/%D0%B4%D0%BE%D0%B2%D0%B5%D1%80%D1%8F%D0%B9-%D0%BD%D0%BE-%D0%BF%D1%80%D0%BE%D0%B2%D0%B5%D1%80%D1%8F%D0%B9-sfi-safety-for-native-compiled-wasm/?utm_source=chatgpt.com)
- vs Icarus: Icarus ports/verifies “a significant part of Firefox’s inline cache generator”; you validate final emitted code from an otherwise untrusted production JIT. [CSE Web](https://cseweb.ucsd.edu/~dstefan/pubs/smith%3A2024%3Aicarus.pdf?utm_source=chatgpt.com)
- biggest overlap is Mohabi/LFI: LFI's verifier has already been formally shown to accept code that “never read[s] or write[s] to memory outside of a designated sandbox region.” [Repositum](https://repositum.tuwien.at/bitstream/20.500.12708/219561/1/Sotoudeh-2025-Automated%20Formal%20Verification%20of%20a%20Software%20Fault%20Isolation...-vor.pdf?utm_source=chatgpt.com)
- therefore novelty must be multi-domain: one shared runtime/process, many dynamically selected tenant cages, plus verified gates/shared immutable code—not simply another one-region SFI verifier
- 2 weeks: validate ~20 x86-64 addressing/control-flow forms emitted by one JIT tier; reject synthetic absolute-address/`WRPKRU` escapes and your 35-bit-style bad lowering
- biggest risk: real JS JITs constantly call C++ runtime stubs and manipulate shared metadata; either the policy becomes permissive enough to be useless or the trusted gate surface explodes

Assessment: strongest verification thesis if you can articulate the multi-tenant property sharply; highest engineering risk.

### 3. leakage-budgeted dynamic isolation

- idea: replace “does this Worker look malicious?” with “how much observation opportunity has this tenant accumulated?”; process-isolate/migrate before a measured leakage budget is exhausted
- state could count synchronous CPU bursts, repeated timer-like network I/O, co-residency duration, yields, and possibly PMU signals; verification proves accounting/migration is fail-closed
- new vs Schwarz et al.: DyPrIs is “a process-isolation mechanism that only isolates suspicious worker scripts following a detection mechanism.” [arXiv](https://arxiv.org/abs/2110.04751?utm_source=chatgpt.com)
- the gap is important because Cloudflare's 2026 reassessment says “Detection cannot happen only after a script finishes” and reports a production attack “leaking up to 12 bit/s with a 99% accuracy.” [Cloudflare Blog](https://blog.cloudflare.com/revisiting-spectre-attacks-on-workers/?utm_source=chatgpt.com)
- vs Swivel: Swivel tries to prevent speculative Wasm leakage structurally; it says malicious Wasm cannot “break out of the Wasm sandbox nor coerce victim code … to leak secret data.” [USENIX](https://www.usenix.org/conference/usenixsecurity21/presentation/narayan?utm_source=chatgpt.com)
- your claim would be weaker but applicable to arbitrary JS: conditional bound ≤ B bits before forced separation for explicitly measured channel families
- 2 weeks: two isolates + synthetic/covert cache channel; vary an observation budget N, force migration at N, measure recovered bits and benign false-isolation rate
- biggest risk: there is no credible universal bound over unknown microarchitectural channels; the result must say “bounded under model M on hardware H,” never “equivalent to process isolation”

Assessment: potentially the most novel measurement paper; security theorem necessarily conditional.

### dead ends

- **“use MPK for Workers.”** Already done: Cloudflare says it “deployed internal modifications to V8 to use memory protection keys to isolate the isolates from each other.” [Cloudflare Blog](https://blog.cloudflare.com/safe-in-the-sandbox-security-hardening-for-cloudflare-workers/)
- **snapshot-specialized JS verification as the isolation argument.** Wrong layer. It constrains guest behavior under assumptions; it says nothing about V8 bugs, JIT corruption, host bindings, or Spectre. Keep dynstate for application-policy work, not tenant containment.
- **your current heap-ownership proof as sufficient evidence.** Good specification seed, but without correspondence to GC/JIT/native memory operations, a compromised engine simply bypasses the modeled barrier.
- **“V8 sandbox lets us put hostile browser sites together.”** Insufficient threat model. Chromium Site Isolation explicitly aims for each renderer to contain “pages from at most one web site” and assumes renderer compromise plus speculative attacks. [Chromium](https://www.chromium.org/developers/design-documents/site-isolation/?utm_source=chatgpt.com)
- **verify all of V8/SpiderMonkey in Verus.** Scope is wrong. Icarus and Mohabi suggest the tractable boundary is generated code, gates, allocation, or SFI—not the whole optimizing engine.
- **measure zero observed leaks and call it isolation.** Measurement can falsify a security claim or calibrate a fallback policy; absence of a measured channel is not a proof.

If I were choosing a PhD-sized path, I would pursue **#2 with #1 as the trusted runtime underneath**: “verified multi-domain confinement for production JS JITs.” #3 is a good independent measurement paper and a useful fallback when speculative noninterference is too strong.
