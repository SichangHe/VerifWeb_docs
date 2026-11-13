# On-the-fly verification of page JavaScript: legit?
(authored by agents unless marked 🧑)

Sources: literature quotes with URLs are in [lit.md](lit.md); corpus numbers come from [scan/scan.mjs](scan/scan.mjs) run over existing local data (no new crawl).

## The remark
From the Nov 3 meeting transcript (speakers unnamed in the file):
- Speaker 1: "Because it would also require, like, on-the-fly verification of the JavaScript code on the page you're loading, right? ... you're pulling in some code on the fly, you're reasoning, should you run this in a separate process, or can you afford to run this… For the memory isolation problem?"
- Speaker 5: "the runtime verification has the dynamic state context, and that's the difference. The question is, for the given state, what is the behavior of this? As opposed to, for any given state, what is the behavior?"
- Speaker 5: "pick bite-sized problems and make slow headway."

## Verdict
- Legit: yes. Checking untrusted code right before running it is an established idea with production systems (fact, below).
- New: partly (belief). Load-time checks on page JS were done around 2009-2012 (Chugh et al., Gatekeeper, JSand). I found no 2018-2026 browser load-time verifier of page JS (searches only; absence not proven). The "proof for the current page state, dropped when the state changes" framing appears to be the open part.
- Feasible as stated (decide process sharing for arbitrary page JS): no, in my opinion. Feasible for narrow properties with a fallback: plausible (opinion).

## Precedent (facts)
- Proof-carrying code: the host can "easily and quickly validate the proof" of untrusted code (Necula, POPL 1997).
- eBPF verifier runs on every program loaded into Linux. Its size limit "is set to 1 million" instructions, and "All these limits can be hit with a sufficiently complex program" (kernel docs).
  - it rejects safe code: "safe extensions being rejected by the verifier" (Rex, ATC 2025)
  - it accepted unsafe code: CVE-2023-2163, "unsafe code paths being incorrectly marked as safe, resulting in arbitrary read/write in kernel memory"
- NaCl, RockSalt, VeriWasm, LFI: check machine code for isolation. All target small regular instruction sets, not a dynamic language.
- Page JS specifically:
  - Chugh et al. PLDI 2009: check known code statically and compute "a minimal set of syntactic residual checks that are performed on the remaining code when it is dynamically loaded"; "almost no run-time overhead" on "large real-world websites". Closest prior work to the remark.
  - Gatekeeper 2009: "1,341 verified warnings in 684 widgets, no false negatives"; works on restricted widgets, not whole pages.
  - ConScript 2010, JSand 2012, TreatJS 2015: runtime enforcement (monitors, wrappers), not proofs.
- JS static analyzers do not scale soundly to real pages:
  - TAJS: promising "on small and medium size programs"
  - Jelly (PLDI 2024): state-of-the-art analyses "mostly ignore" dynamic operations; recall 75.9% → 88.1% on Node.js apps
  - Richards et al. ECOOP 2011: any ahead-of-time analysis "is forced to make pessimistic assumptions about the impact of dynamically created code"

## How much real page JS a checker faces
Published: median page loads 558 KB (mobile) of JS over 22 requests (Web Almanac 2024).

Local corpus (facts; 2879 script files from 97 sites, fetched for the earlier regex study):
- size: median 2.7 MB of JS per site, 25 files; 90th percentile 7.5 MB
- parse alone: acorn parse takes median 309 ms per site (90th pct 859 ms) on one core; 370 files (13%) did not parse
- dynamic code: 62 of 97 sites contain direct `eval`, `Function(...)`, string timers, or `with`
  - lower bound: indirect forms like `window.eval` were not counted
- assignments through `.prototype`/`__proto__`: 74 of 97 sites (includes ordinary class setup, so overstates pollution)
- only 5 of 97 sites are free of all the above in every file
- earlier run: 63 of 95 sites changed a built-in prototype after load (vlm2_scripts t11)

Inference: a whole-page sound check in milliseconds is out of reach; parsing alone costs hundreds of ms. A checker must be incremental, cached per script hash, and scoped to a narrow property.

## Which properties could be decided fast (beliefs)
- syntactic/capability properties ("this script never touches `document.cookie`, password fields, or network APIs, and has no eval"): fast (one pass, cacheable). Useful for privacy. Defeated by reflection (`window[x]`), so sound only with a fail-closed rule. Median 2.15 computed member accesses per KB suggests many scripts would fail it.
- information flow ("password value never reaches a network call"): Chugh-style residual checks. Useful for privacy; our crawl found 11 of 139 pages sending email to third parties before submit, so there is a real target.
- isolation for process sharing: the remark's target, and the hardest. The risk is engine bugs, not script behavior; a script-level proof does not protect against a JIT bug, and Spectre-style leaks are outside any such proof. Our earlier measurement suggests memory savings need the whole renderer shared (vlm_runtime/tabiso).
- state-conditional properties ("for this snapshot, no exception / no cookie read"): our prototype did this in ~130-190 ms, but only for a tiny JS subset.

## Best concrete form and first paper (opinion)
- form: an eBPF-style checker for web pages: per script hash, prove a narrow capability or flow property under assumptions about the current page state (e.g. pristine built-ins), guard those assumptions at run time, fall back to today's behavior when a check fails or a guard trips
- bite-sized first paper: "how much of real page JS admits a cheap sound check of property P"
  - P = no access to password/cookie/storage sinks, or no flow from password fields to network
  - use the 2879-script corpus: fraction checkable, false-rejection causes, time per script, cache hit rate across sites (shared libraries)
  - compare against Chugh et al. 2009 on modern pages
- not first: process-sharing decisions

## Risks
- false rejections dominate (eBPF's lived experience); on JS, the dynamic-code numbers above predict many
- checker bugs become security holes (eBPF CVEs); a verified checker is a later paper
- novelty: Chugh et al. 2009 already did load-time residual checks on real sites; the new claim must be state-conditional proofs plus guards, or modern-scale measurement
- process sharing gains depend on engine-level isolation that script verification cannot provide

## Gaps
- paper bodies were not readable; scale numbers inside papers (NaCl validator speed, VeriWasm timing) are unverified
- corpus caveats: one crawl, first-load scripts only, one file truncated at 8 MB, acorn parse time on a cold run
