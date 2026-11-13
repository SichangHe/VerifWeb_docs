# Target 11: built-in prototypes stay unchanged after library calls
(authored by agents unless marked 🧑)

Nothing was filed upstream and no maintainer or project was contacted (human rule: "Don't file those issues" / "Let's keep things to ourselves for now"). All results are local.

## Takeaways
- The property is violated by many old library versions and is held by current versions of nearly all libraries tested. [FACT measured] 46 of 129 package versions have at least one API that changed a built-in under my payloads.
- Pollution is not only `Object.prototype`. [FACT measured] Targets that are arrays or functions let the same payloads change `Array.prototype` and `Function.prototype`. Several payloads also replaced `toString` (`Object.prototype.toString` and the Array/Function ones) with a string, which a "new key appeared" check on `Object.prototype` alone would label differently.
- On real sites, third parties modify built-ins routinely: 63 of 95 loaded sites changed at least one ES built-in. The property "built-ins unchanged" is therefore not true of normal web pages, so a web checker needs an allowlist (polyfills) rather than zero tolerance.

## Method
- Monitor (`monitor.js`): snapshots about 59 intrinsic roots in Node (constructors, prototypes, Math/JSON/Reflect/Intl, iterator/generator prototypes). Per own key (strings and symbols) it records enumerable/writable/configurable flags, value identity or primitive value, accessor identity, `[[Prototype]]`, extensibility, and global names. It diffs before and after each call and restores afterwards.
- Library trials (`cases.js`, `worker.js`, `run_all.js`): one fresh child process per (package version, API). Each API gets payloads from this grid.
  - Merge-style APIs: `__proto__`, `constructor.prototype`, nested and array variants, crossed with targets `{}`, `[]`, function and `{a:{}}`.
  - Path-setter APIs: dotted, bracket and array paths with `__proto__` and `constructor.prototype`, same targets.
  - Parsers (minimist, yargs-parser, qs, ini, flat, xml2js, json-schema), plus custom exploits (y18n `setLocale('__proto__')`, object-path `withInheritedProps`, mout, dot-object, property-expr).
- Web crawl (`pages/crawl.js`): headless `/usr/bin/google-chrome` via playwright-core. An init script snapshots built-ins at document start in every frame; the main frame is re-snapshotted after load + 6 s + scroll. Calls to `Object.defineProperty`/`defineProperties`/`assign`/`setPrototypeOf` and `Reflect.*` equivalents on roots are hooked to log stacks.
- Sites: 98 hand-picked popular domains (`sites.txt`), `https://www.<domain>`.

## Library results [FACT measured]
- Scale: 129 package versions, 283 APIs (some entries are variants), 5370 trials; 75 APIs changed a built-in in at least one trial, 1169 trials changed one. Rows: `results/libs_summary.txt`; raw: `results/libs.jsonl`.
- Vulnerable on these payloads:
  - lodash 3.10.1, 4.17.4, 4.17.5, 4.17.11: merge/mergeWith/defaultsDeep and set/setWith/update/zipObjectDeep polluted (4.17.4: 24 of 24 merge trials). 4.17.12 and 4.17.15: merge was clean but set/setWith/update/zipObjectDeep still polluted. 4.17.19, 4.17.20, 4.17.21, latest: 0 changes in all trials.
  - lodash.merge 4.6.1, lodash.mergewith 4.6.0, lodash.defaultsdeep 4.6.0, lodash.set 4.3.2.
  - jQuery 1.12.4, 2.1.4, 3.3.1 `$.extend(true)`: 14 of 24 trials; 3.4.0, 3.5.0, 3.7.1: 0.
  - set-value 1.0.0, 2.0.0, 3.0.0; dot-prop 4.2.0, 5.1.0; deep-extend 0.4.0, 0.5.0; hoek 4.2.0; merge 1.2.0 `recursive`; defaults-deep 0.2.3; assign-deep 0.4.7, 1.0.0; merge-deep 3.0.0, 3.0.2; mixin-deep 1.2.0; object-path 0.9.2; pathval 1.1.0; nested-property 0.0.7; property-expr 2.0.2; dot-object 1.7.0.
  - minimist 0.0.10, 1.2.0 (3 of 3 payloads); yargs-parser 13.1.1, 15.0.0, 18.1.0; ini 1.3.5; flat 4.0.0, 5.0.0; y18n 4.0.0 (custom exploit only).
- Clean on all payloads: lodash 4.17.20+, jQuery 3.4+, object-path 0.11.4/0.11.5/latest, minimist 1.2.3+, ini 1.3.7+, flat 5.0.1+, y18n 4.0.1+, dot-prop 6.0.0/latest, set-value latest, hoek (all tested versions incl. @hapi/hoek), qs (6.5.1+), json-schema, xml2js, dottie, deepmerge, extend, ramda, underscore, rfdc, clone-deep.
- Current versions that still changed a built-in:
  - mout 1.2.4: `deepMixIn`, `deepFillIn` and `namespace` with a `__proto__` payload added `Object.prototype.polluted` (3 of 8 trials).
  - nested-property 4.0.0: 2 of 32 trials added `Array.prototype.polluted` (array target, paths `__proto__.polluted` and `constructor.prototype.polluted`).
  - No issue was filed or reported (see top). Whether these are documented or intended behavior is not established.
- Surprises: mixin-deep 1.3.1 and node.extend 1.1.6 did NOT pollute here, though advisories cover older ranges; with default dependency resolution, mixin-deep 1.3.1 pulled is-extendable 1.0.1. [BELIEF] The advisory ranges assume an older dependency; I did not verify this.
- Harness notes: pollution "leak" = `({}).polluted`, `[].polluted` or a function's `.polluted` defined after the call. Error counts are reported per API (hoek errors on 6 trials by design: it throws on `__proto__` keys).

## Web results [FACT measured] (`results/web.jsonl`, `results/web_summary.txt`)
- 98 sites attempted, 95 loaded (3 navigation errors).
- 63 of 95 changed at least one ES built-in (Object, Array, String, Function, Promise, Symbol, Reflect, ...); 32 changed none (e.g. github.com, nytimes.com, reddit.com, cnn.com). Median 2 ES entries changed per site, max 361 (espn.com).
- Totals over sites: 1460 added keys, 231 replaced keys on ES roots.
- Most common: `Function.prototype.toString` replaced on 35 sites (6 with non-native code); `Error.stackTraceLimit` on 12 (non-native); `Error.prepareStackTrace` on 10; Reflect metadata API (`Reflect.metadata`, `getMetadata`, ...) added on 9 sites.
- 23 sites added many Symbol-keyed props with descriptions like `Symbol(padStart)`, `Symbol(flatMap)`, `Symbol(finally)` to String/Array/Promise/Object (338 entries). [BELIEF] These look like a Closure-compiler style polyfill; the stack hosts logged most often are `securepubads.g.doubleclick.net`, `www.microsoft.com`, `www.mit.edu`, `a.espncdn.com`, `transcend-cdn.com`, but I did not tie each symbol to a script.
- Enumerable additions to ES prototypes (these break `for...in`): 35 on prototypes such as `String.prototype.contains` (facebook.com, instagram.com, stackoverflow.com), `formatUnicorn`, `truncate`, `Date.prototype.getTimeAlias` (cloudflare.com, zoom.us), `String.prototype.supplant`, `Date.prototype.addHours`/`addYears` (weather.com).
- `Object.prototype` itself changed on 3 sites: espn.com (added `enswatch`), wix.com (7 methods and `__proto__` getter replaced by distinct native functions), lenovo.com (added `INDhasOwnProperty`, `INDisPrototypeOf`, `INDpropertyIsEnumerable`).
- 51 sites called `defineProperty`-style APIs on roots (hook log); 67 of 95 sites also changed non-ES roots (DOM/Web API prototypes such as `XMLHttpRequest.prototype.open` on 30 sites, `HTMLFormElement.prototype.submit` on 28).
- Attribution is partial: hooks only see defineProperty-style calls, not plain assignments (`Array.prototype.x = f`).

## Limits
- [FACT measured] No pristine-page control run (e.g. example.com): the baseline is taken after my init script's own hooks are installed, so no diff is attributed to them, but residual browser-injected changes are not separated out.
- Payloads are hand-written, not each package's own test suite; the original first step (test suites of the top 100 merge/clone utilities) was not done. A clean result means "none of my payloads", not safety.
- Crawl: one visit per site from one network location; consent banners not clicked; sites may serve different scripts per region or user agent. 98 sites are not the Tranco top 100.
- Node results use Node v22.21.1; the restore step is best-effort (one process per API, so state does not carry across APIs).
- NodeProf/Jalangi was not used; the monitor is a before/after snapshot, so it cannot say which line did the write.
- [PRIOR from memory] lodash CVE-2019-10744 (fixed in 4.17.12) and the later set/zipObjectDeep fixes (4.17.17-4.17.20) are consistent with the measured versions above; I did not read the advisories in this run.

## Run
`sh run.sh` (see file). Outputs go to `results/`. Downloaded packages are only in `pkgs/`.
