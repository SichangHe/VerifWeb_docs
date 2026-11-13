(authored by agents unless marked 🧑)

# engine: browser engine components worth formal verification
Tags: [F] fact with quote+URL, [I] inference, [O] opinion.
Limits: WebFetch quotes are fragments (<125 chars). Two final searches (Wasm JIT CVEs, cookie parsing) were blocked by an API safeguard error; not retried, so candidates 6 and 8 lack CVE evidence. Scholar not used.

## 1. JIT range analysis (SpiderMonkey/V8)
- why: [F] Bug 1528829 / CVE-2019-9793: "The issue lets an attacker produce an arbitrary value in compiled JavaScript code," "for which the range analysis will infer a fully controlled, incorrect range." https://bugzilla.mozilla.org/show_bug.cgi?id=1528829
- done: [F] VeRA, PLDI 2020, https://dl.acm.org/doi/10.1145/3385412.3385968 (page 403; search-result summary only): SMT-verified 22 Firefox range-analysis routines, found a six-year-old bug. [F] Translation validation for V8 JIT, ICSE 2024: https://kihongheo.kaist.ac.kr/publications/icse24.pdf (title only read).
- new: [I] other JIT passes (bounds-check elimination, load elimination, Wasm tier-up) and range analysis of floating point; verification inside the real build, not a C++ subset. [O] highest payoff: JIT bugs are the top exploit source.

## 2. URL parsing (WHATWG vs RFC 3986)
- why: [F] CVE-2021-32786: "Because of this parsing differential, `mod_auth_openidc` can be tricked into thinking that an URL is "safe"" ; browsers "will follow the redirection to an unintended host." https://www.sonarsource.com/blog/security-implications-of-url-parsing-differentials/
- done: [F] partial only: danbri/factoidal issue 1188, Lean 4 proof that the path-segment rule equals RFC 3986 removeDotSegments; whole parser "only tested" (search summary). https://github.com/danbri/factoidal/issues/1188. No peer-reviewed full proof found (queries: "formal verification URL parser differential WHATWG URL mechanized").
- new: [I] verified WHATWG parser (Lean/Coq/F*) plus proof of exactly which inputs differ from RFC 3986, usable by servers to reject differential inputs.

## 3. HTTP/1.1 message framing (request smuggling)
- why: [F] source for the problem class (arXiv 2606.10649 summary): smuggling "lives in the gap" between processors' decisions about where a request ends. https://arxiv.org/pdf/2606.10649 (not opened; quote from search summary, treat as weak).
- done: none found for a proof about smuggling in browsers/proxies (query: "formal verification HTTP request smuggling parser proof Coq OR Isabelle OR Dafny"). [F] related: TRX verified PEG parser in Coq https://arxiv.org/pdf/1105.2576; arXiv 2606.10649 is automata/monitoring.
- new: [I] verified HTTP/1.1 framing parser (EverParse-style) with a theorem that two conforming parsers agree on message boundaries. [O] needs a real-world CVE citation; not gathered.

## 4. Browser security mechanisms model (CORS, CSP, cookies, service workers, frames)
- why: [F] WebSpec abstract: manual review "has proved to be error-prone due to the extensiveness of modern browser specifications." https://arxiv.org/abs/2201.01649
- done: [F] WebSpec: "the first formal security framework for the analysis of browser security mechanisms"; Coq model, ten invariants, Z3 via SMT-lib; found two new logical flaws. Same URL. Older: Akhawe et al. Alloy (bounded, cannot prove), Bohannon Featherweight Firefox (Coq), WIM (pen-and-paper) per search summary; survey https://www.sciencedirect.com/science/article/pii/S2352220816301055.
- new: [I] the model is of the spec, not of Chromium/Firefox code: conformance of the engine to it is unverified. Unproven (only counterexample search) invariants; storage partitioning, Fetch, COOP/COEP not confirmed covered. [O] model-to-code link is the open gap.

## 5. Browser kernel / site isolation / process architecture
- why: [I] site isolation is the main defense against renderer compromise; no CVE gathered.
- done: [F] QUARK, USENIX Security 2012, Coq shim verification of a WebKit-based browser kernel: https://www.usenix.org/system/files/conference/usenixsecurity12/sec12-final217.pdf (PDF unreadable; description from search summary). No mechanized proof for Chrome site isolation found (query: "formal verification browser extension model OR service worker OR site isolation OR IndexedDB mechanized proof").
- new: [I] model of Chrome's process-per-site policy, browser-process IPC permission checks, and the Origin/COOP rules, proved to enforce "renderer of site A cannot read data of site B" under renderer compromise.

## 6. WebAssembly semantics and engines
- why: [F] CertiCoq-Wasm found "an incorrect modelling of shifts in WasmCert" (search summary) https://www.cl.cam.ac.uk/~jp622/certicoq-wasm.pdf. Wasm engine CVE not gathered (search blocked).
- done: [F] WasmCert-Isabelle and WasmCert-Coq, https://www.doc.ic.ac.uk/~pg/publications/Watt2021Two.html ; WasmRef-Isabelle verified interpreter used as Wasmtime fuzzing oracle, https://www.researchgate.net/publication/371359866 ; Watt 2018 proof "exposed several issues with the official WebAssembly specification" (search summary, https://www.researchgate.net/publication/322190983).
- new: [I] Wasm 3.0 features (GC, exceptions, tail calls) and engine JIT/validator conformance; verified validators for V8/SpiderMonkey. Core spec is already well covered, so [O] lower novelty than 1.

## 7. WebGPU shaders (WGSL translators)
- why: [F] DarthShader: it "found 39 faults across Chrome, Firefox, and Safari"; Chrome "assigned CVEs to 15 of them" (fetch summary, paraphrase of abstract) https://arxiv.org/abs/2409.01824
- done: none found for a mechanized WGSL semantics or verified translator (query: "WGSL formal semantics mechanized WebGPU shader compiler verification Tint Naga bug"). Only testing: WGSLsmith (http://www.doc.ic.ac.uk/~afd/papers/2026/SPLASH-ISSTA-WGSLsmith.pdf), DarthShader.
- new: [I] formal WGSL semantics (integer overflow, uniformity analysis, out-of-bounds robustness) and a verified WGSL-to-SPIR-V/MSL/HLSL pass. [O] big effort; start with the uniformity analysis.

## 8. Storage lifetime/memory safety (IndexedDB, and similar browser-process services)
- why: [F] "CVE-2026-15107: Use after free in IndexedDB in Google Chrome prior to 150.0.7871.115 allowed a remote attacker to execute arbitrary code inside a sandbox via a crafted HTML page." Also CVE-2021-30633, CVE-2019-5826, CVE-2017-5091, CVE-2011-3091 (same search result list; https://www.cvedetails.com/cve/CVE-2021-30633/).
- done: none found for IndexedDB semantics or implementation (same query as 5). [F] related: service-worker IDB trust study (not formal) https://dl.acm.org/doi/fullHtml/10.1145/3471621.3471845.
- new: [I] these are C++ lifetime bugs; verification is better by memory-safe rewrite or Rust/ownership proofs of the transaction/cursor state machine than by spec modeling. [O] likely cheaper to prevent by language choice.

## 9. Browser extensions
- why: [I] no CVE gathered.
- done: [F] IBEX, "Verified Security for Browser Extensions" (Guha et al.): refinement types, extensions checked statically against access-control policies. https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/paper-camera-ready.pdf (from search summary). Predates Manifest V3.
- new: [I] Manifest V3 permission/declarativeNetRequest semantics and content-script isolation model.

## Not covered
- cookie parsing differentials (RFC 6265bis), CSS/HTML parsing (HTML5 tokenizer spec-conformance proofs), Fetch/CORS implementation conformance, TLS/QUIC stacks (verified elsewhere, e.g. miTLS), Wasm JIT CVEs.
