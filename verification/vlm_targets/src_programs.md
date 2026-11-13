# Real failures in individual JS programs / pages / packages
(authored by agents unless marked 🧑)

Quotes fetched 2026-11-03 unless marked UNVERIFIED. "Property" = what a verifier/monitor could check.

## 1. Cloudflare WAF regex outage, 2019-07-02 (ReDoS)
- URL: https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/
- Quote: "contained a regular expression that backtracked enormously and exhausted CPU used for HTTP/HTTPS serving."
- Also: "a single WAF rule that contained a poorly written regular expression that ended up creating excessive backtracking" (tail of pattern: `.*(?:.*=.*)`).
- Root cause: nested/adjacent unbounded `.*` gives super-linear backtracking, deployed globally without a CPU guard.
- Property: match time is O(input length) (or bounded step budget) for every rule on every input.
- Caveat: the WAF regexes ran in Lua/PCRE, not JS; the bug class is the same as JS RegExp ReDoS.

## 2. polyfill.io supply-chain injection, 2024
- URL: https://sansec.io/research/polyfill-supply-chain-attack
- Quote: "However, in February this year, a Chinese company bought the domain and the Github account."
- Also: "this domain was caught injecting malware on mobile devices via any site that embeds cdn.polyfill.io."
- Root cause: sites load a mutable third-party script by URL with full page privileges; the domain's owner changed.
- Property: a loaded third-party script's bytes match a pinned hash (SRI), and it never navigates/redirects the top frame to a non-allowlisted origin.

## 3. event-stream / flatmap-stream, 2018
- URL: https://github.com/dominictarr/event-stream/issues/116
- Quote (issue author): "After he adds it at almost the exact same time the injection is added to `flatmap-stream`, he bumps the version and publishes."
- Also: "It includes the portion of code not found in the **unminified** source of `flatmap-stream@0.1.1` but found in the **minified** source."
- Root cause: maintainer rights handed to a stranger, who added a dependency whose payload decrypted only inside the Copay build and stole wallet keys.
- Property: a dependency never reads wallet/credential data or patches other packages' files (`@zxing/library`); published artifact equals its source repo build.

## 4. left-pad unpublish, 2016-03-22
- URL: https://blog.npmjs.org/post/141577284765/kik-left-pad-and-npm
- Quote: "Azer unpublished his `kik` package and 272 other packages."
- Also: "The duration of the disruption was 2.5 hours."
- Root cause: transitive builds depend on a mutable registry name; author could delete a 11-line package that babel/atom pulled in.
- Property: every resolved dependency version is retrievable and content-hash-pinned (lockfile integrity); builds do not fail on a registry deletion.

## 5. lodash `defaultsDeep` prototype pollution, CVE-2019-10744
- URL: https://nvd.nist.gov/vuln/detail/CVE-2019-10744 (text via https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2019-10744)
- Quote: "Versions of lodash lower than 4.17.12 are vulnerable to Prototype Pollution. The function defaultsDeep could be tricked into adding or modifying properties of Object.prototype using a constructor payload."
- Root cause: recursive merge follows attacker-controlled keys (`constructor.prototype`) into shared prototypes.
- Property: after any call on untrusted input, `Object.prototype` (and other built-in prototypes) are unchanged.

## 6. British Airways Magecart skimmer, 2018
- URL: https://web.archive.org/web/2019/https://www.riskiq.com/blog/labs/magecart-british-airways-breach/ (original riskiq.com URL now redirects to Microsoft; archived copy fetched)
- Quote: "we saw this script was a modified version of the Modernizr JavaScript library, version 2.6.2 to be precise."
- Also: "Send the data in the form of JSON to a server hosted on baways.com"
- Root cause: attacker edited a first-party static script served on the payment flow; it read card-form fields and POSTed them to a lookalike domain.
- Property: no script on the payment page reads card fields or sends them to an origin outside the payment-processor allowlist (CSP connect-src + SRI on all scripts).
- Secondary source (ICO penalty notice) returned 403; not checked.

## 7. Client-side JS bug study (Ocariza, Pattabiraman, Mesbah)
- URL: https://www.cs.ubc.ca/~amesbah/docs/ocariza-ase2013.pdf (fetch timed out; bibliographic ID from memory, UNVERIFIED). IEEE page https://ieeexplore.ieee.org/document/6571611 also not retrievable.
- Quote: NOT RETRIEVED. From memory, UNVERIFIED: the study finds most faults are DOM-related (JS code calling the DOM with wrong/absent element or attribute). Confirm before citing.
- Root-cause class: JS code assumes DOM state (element exists, has attribute) that does not hold at that time.
- Property: every DOM lookup in executed code returns non-null before dereference; no uncaught TypeError from null DOM result.

## 8. Event races in web apps (Petrov, Vechev, Raychev, Yahav, PLDI 2012; EventRacer follow-up)
- URL: https://dl.acm.org/doi/10.1145/2254064.2254092 (403; abstract NOT RETRIEVED, UNVERIFIED). Author PDF attempt https://files.sri.inf.ethz.ch/website/papers/pldi12-race.pdf returned HTML, not PDF.
- Quote: NOT RETRIEVED.
- Root-cause class: unordered async events (load, timers, XHR callbacks, user input) access the same JS/DOM/HTML-form state with no happens-before order.
- Property: no two conflicting accesses to the same variable/DOM node/form field are unordered under the web happens-before relation (race-freedom).

## Not done
- Unhandled-rejection/promise-race outage and Node.js concurrency-bug study: no concrete source found in the time spent.
