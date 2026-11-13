# Isolation failures (browsers / JS runtimes)
(authored by agents unless marked 🧑)

Status: 5 items verified from primary sources; V8-sandbox-escape and UXSS items NOT found
(web search was blocked by a safeguard mid-task). Quotes below were fetched via a
summarizing fetcher except the USENIX one (pdftotext, exact). Re-check quotes before citing.

## 1. CVE-2023-29017 (vm2, GHSA-7jxr-cg7f-gpgv) - Node vm sandbox escape
- URL: https://github.com/advisories/GHSA-7jxr-cg7f-gpgv
- Quote: "vm2 was not properly handling host objects passed to `Error.prepareStackTrace` in case of unhandled async errors."
- Class: host (outer-realm) objects leak into guest callbacks without proxy wrapping.
- Violated: no unproxied object reference from the host context is reachable from guest code (e.g. via host Function constructor -> arbitrary host code).
- Note: in-process "context" separation is only as strong as the wrapper layer; vm2 is discontinued (unverified here).

## 2. CVE-2023-26489 (Wasmtime/Cranelift) - Wasm linear-memory escape
- URL: https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-ff4p-7xrq-q5r8
- Quote: "address-mode computation mistakenly would calculate a 35-bit effective address instead of WebAssembly's defined 33-bit"
- Also: "The memory may belong to other WebAssembly instances when using the pooling allocator, for example."
- Class: compiler lowering bug (x86_64 addressing-mode folding skipped 32-bit truncation) defeats guard-region bounds enforcement.
- Violated: every guest load/store address lies within [base, base+4GiB+guard) of its own linear memory; no access to other instances' memory.

## 3. Spook.js (Spectre against Chrome Strict Site Isolation)
- URL: https://www.spookjs.com/  (paper: https://www.spookjs.com/files/spook-js.pdf, path inferred, unverified; IEEE S&P 2022)
- Quote: "we show that Chrome's Strict Site Isolation implementation consolidates webpages based on their eTLD+1 domain"
- Quote: "Spectre is fundamentally a hardware vulnerability where footprints of speculative execution are not cleaned up completely"
- Class: speculative execution leaks across in-process boundaries; site isolation draws the process boundary at eTLD+1, so same-eTLD+1 pages share an address space.
- Violated: no data of origin B is readable (even transiently) from code of origin A; here, same-eTLD+1 different-origin pages share a process.

## 4. Spectre vs V8 isolates, Cloudflare Workers (design statement, not a CVE)
- URL: https://blog.cloudflare.com/mitigating-spectre-and-other-security-threats-the-cloudflare-workers-security-model/
- Quote: "The V8 team at Google has stated in no uncertain terms that V8 itself cannot defend against Spectre."
- Also: "yes, isolates (which we use) also have bugs."
- Class: tenants share one address space and microarchitectural state; software cannot hide timing/speculation channels.
- Violated: no information flow from tenant A's memory to tenant B except via explicit APIs. Cloudflare's mitigation: no high-res timers, no multithreading, and moving suspicious Workers to their own process.

## 5. V8 Sandbox (in-process memory cage) - the threat model, as design admission
- URL: https://v8.dev/blog/sandbox
- Quote: "it is assumed that an attacker can read and write arbitrarily inside the V8 Sandbox."
- Quote: "V8 vulnerabilities are rarely "classic" memory corruption bugs (use-after-frees, out-of-bounds accesses, etc.)"
- Class: JIT/logic bugs give arbitrary in-cage R/W; only the cage (pointer tables, offsets, ~1% overhead per the same post) stops it reaching outside.
- Violated if bypassed: every memory access performed by V8 on attacker-influenced data lands inside the cage. NOT FOUND: a specific public sandbox-bypass CVE ID/URL (unverified; search them in Chrome Releases / V8 bug tracker, "V8 Sandbox bypass" VRP category).

## 6. NOT FOUND (unverified, to do)
- Universal XSS / SOP bug: no CVE retrieved. Candidate class only; do not cite.
- Cross-V8-Context/Isolate leak CVE: none retrieved.

## Memory cost of process-per-site
- Source: Reis et al., "Site Isolation: Process Separation for Web Sites within the Browser", USENIX Security 2019. https://www.usenix.org/system/files/sec19-reis.pdf
- Quote: "finding that it incurs a total memory overhead of 9-13% in practice and increases page load latency by less than 2.25%"
- Quote: "the 50% increase in renderer process count is significant, but this does not necessarily translate to an equivalent increase in memory overhead"
- Counter-argument (Cloudflare, same URL as #4): "If we had to run a separate process for every guest, the number of tenants we could support would be drastically reduced"; "the CPU cost can easily be 10x what it is with a shared process."
- Takeaway: ~10% memory is affordable for ~10s of processes per browser; for thousands of tenants per host (Workers) it is not, hence in-process isolation and its residual risk.
