# JS bundler/minifier security: is Calvin's question real?
(authored by agents unless marked 🧑)

Question (Calvin Ardi, Nov 19 meeting, transcript L593-600): "a lot of applications, they use JavaScript, and then they use bundlers, and tree shaking, and minification ... I think that obscures potentially ... possible security issues ... You tree shake out B, but you actually needed to use A and B together ... you get yourself into some, like, weird, insecure state ... the neat thing about JavaScript is you can measure that"

## Bottom line
- fact: bundler security CVEs exist, but the ones found are about code the bundler *adds* (runtime glue), not about tree shaking/minification changing program meaning
- fact: meaning-changing bugs in minifiers/tree shakers are common in issue trackers; none found was filed or exploited as a security problem
- inference: Calvin's exact scenario ("A needs B, B shaken out -> insecure") has no documented real-world instance that I found. evidence is thin
- opinion: the defensible project is "semantics preservation of bundling/minification", with security as a motivating subset; leading with security alone is a weak claim today

## Evidence 1: CVEs in bundler-injected code (DOM clobbering)
- CVE-2024-43788, webpack < 5.94.0 (GHSA-4vvj-4cpr-p986): "a DOM Clobbering vulnerability in Webpack's AutoPublicPathRuntimeModule that can lead to cross-site scripting (XSS)"; "the real-world exploitation of this gadget in the Canvas LMS" (NVD/GHSA text via https://www.sentinelone.com/vulnerability-database/cve-2024-43788/)
- CVE-2024-47068, Rollup < 2.79.2 / 3.29.5 / 4.22.4 (GHSA-gcx4-mw62-g8wm): DOM clobbering "when bundling scripts with properties from `import.meta` (e.g., `import.meta.url`) in `cjs`/`umd`/`iife` format" leading to XSS (https://nvd.nist.gov/vuln/detail/cve-2024-47068). Vite production builds use Rollup
- takeaway: the bundler's emitted runtime is trusted code nobody reviews; both bugs came from the same DOM-clobbering gadget research line (Khodayari & Pellegrino, S&P 2023, https://scnps.co/papers/sp23_domclob.pdf, cited in the webpack advisory)
- this is not "transformation changed meaning"; it is "transformation inserted vulnerable code"

## Evidence 2: tree shaking dropping needed code (correctness, not yet security)
- expo/expo issue #52417 (Expo Metro tree shaking, recent, experimental flags): "a side-effect-only import (import './polyfill') is removed from the bundle when an import with specifiers comes before it in the same module"; real case: barcode-detector@3.2.0's `./polyfill.js`, "which installs globalThis.BarcodeDetector, is removed" (https://github.com/expo/expo/issues/52417)
  - closest match to Calvin's "you needed A and B together"
  - a bundler bug, not user misconfiguration
- common misconfiguration: package.json `"sideEffects": false` makes webpack/Rollup drop side-effect-only imports (polyfills, CSS); developer-asserted, unchecked
  - inference: a security-relevant side-effect module (e.g. a polyfill that freezes prototypes, a Trusted Types policy setup, a CSP/sanitizer hook) could be dropped this way; no instance found

## Evidence 3: minifier miscompilations (Terser examples)
- terser #1780: compress turns `"n=" + -x + 1` (x=5) into numeric addition; "should print `n=-51` but prints `n=-4`"
- terser #1789: inlines the wrong block-level function declaration; output prints 0 instead of 1
- terser #1307: top-level compression removed an object still referenced -> `ReferenceError`
- terser #1582: `--mangle-props undeclared` renames `globalThis.MyGlobal` but not bare `MyGlobal`, "silently produces broken code"
- (all at https://github.com/terser/terser/issues/NNNN); none tagged security, no Terser CVE found
- belief (unverified this session): esbuild, SWC, Closure Compiler trackers have similar bug classes; Closure ADVANCED mode and Terser `unsafe*` options explicitly assume program properties they do not check

## Rust-written tools
- fact: SWC, Turbopack, Rolldown, oxc (and its minifier) are Rust; esbuild is Go; webpack, Rollup (core), Terser, Parcel v1 are JS (Parcel v2 uses SWC)
- implication: Rust gives memory safety of the tool, says nothing about whether output preserves meaning; a Rust-side verification angle would be about the transformation logic, not the language

## Prior work
- measurement: Skolka, Staicu, Pradel, "Anything to Hide? Studying Minified and Obfuscated Code in the Web", WWW 2019: minification/obfuscation affects "38% of all client-side scripts" on top-100k sites; also tested tools against library test suites
- testing: OBsmith (arXiv 2510.10066, ACM 10.1145/3798204): LLM-generated programs, compares original vs obfuscated/minified output; TransFuzz (SANER 2023): differential testing of transpilers incl. Babel, 73 bugs
- verification: no verified JS minifier, tree shaker or bundler found. nearest: mechanized JS semantics (JSCert, KJS; see directions/vlm41_jssem), Warblre (Coq JS regex), CompCert/CakeML-style verified compilers, translation validation as a technique
- not found: any paper on bundler/tree-shaking *testing* specifically (search, not exhaustive)

## What would be new (per human note: check prior work first)
- candidate claim: first translation validation (per-build equivalence check) for tree shaking/minification of real web bundles
  - prior work tests tools on synthetic programs (OBsmith, TransFuzz) or measures prevalence (Skolka); none checks shipped bundles against their sources
  - hard part: full JS semantics; a scoped version checks only side-effect retention (which top-level effects survive) — tractable, and it is exactly Calvin's A/B case
- candidate claim: audit bundler-emitted runtime code as a security gadget class (generalizing the two DOM-clobbering CVEs) — security, but static analysis, little formal methods
- unknown: whether any of these hits an exploitable bug in the wild; that is the risk

## Measurability
- fact: shipped bundles are public; many sites publish source maps, which map minified output back to original modules
- inference: one can crawl sites, recover module lists via source maps, detect bundler + version from runtime signatures (webpack/Rollup runtime code is recognizable), and flag sites on vulnerable versions (CVE-2024-43788/47068) — a straightforward measurement paper
- inference: checking semantic equivalence on real sites needs the original sources; source maps sometimes embed them (`sourcesContent`)
