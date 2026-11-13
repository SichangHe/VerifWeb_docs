# T13: Does regex matching take linear time? Measured on real npm and web scripts
(authored by agents unless marked 🧑)

Nothing was filed or sent upstream. All data stays local.

## Takeaway
[FACT measured] About 1 in 7 unique regexes in real code is super-linear, and
almost all of those are polynomial, not exponential. Most of them can still be
made linear by V8's `l` flag. The property "match time is linear" is false
for 14% of regexes and checkable for the rest.

## Corpus
- npm: latest tarball of 2991 packages (list in work/pkgs.txt). 60,411 regex
  occurrences, 14,652 unique (flags+source), from `.js/.mjs/.cjs`, including `.min.js`.
- Web: 97 sites, page scripts fetched via headless Chrome (work/web.sh). 2,782 files,
  278 MB, 56,045 occurrences, 13,865 unique.
- Extraction: acorn tokenizer, regex literals plus `RegExp("string"[,"flags"])`.
  Concatenated `RegExp` arguments are skipped. [FACT measured] 357 files failed full parse; partial tokens were used.
- Sampling bias: the top-package list is dependent-count order; "top" is not rigorous. [BELIEF]

## Method (work/analyze.js)
a. V8 linear engine: `new RegExp(src, flags+'l')` accepts or throws (node `--enable-experimental-regexp-engine`).
b. Static: `recheck` 4.6 (hybrid automaton + fuzz checker; complexity safe/linear/polynomial/exponential).
c. Dynamic: recheck's attack string, pump count doubled from 4 until 2 s timeout, 400 kB cap, run in a `vm` context with timeout.
   "Confirmed" = timeout, or log-log slope > 1.3, or one point > 200 ms.

## Results [FACT measured]
npm (14,557 valid unique):
- V8 `l` accepts: 10,462 (71.9%)
- recheck safe: 12,271 (4,608 linear, 7,663 "safe"); vulnerable 2,045 (1,966 polynomial, 79 exponential); unknown 241 (timeouts, invalid)
- Dynamically confirmed super-linear: 1,941 (13.3%)
- V8-linear OR recheck-linear: 11,422 (78.5%)

web (13,772 valid unique):
- V8 `l` accepts: 9,238 (67.1%)
- recheck safe 11,862; vulnerable 1,781 (1,733 polynomial, 48 exponential); unknown 129
- Confirmed: 1,687 (12.2%)
- V8-linear OR recheck-linear: 10,350 (75.2%)

Of confirmed: npm 1,392 and web 1,102 are accepted by `l`. On their attack strings
the linear engine took median 13 ms / 11 ms, and none exceeded 500 ms. So `l` fixes ~70-72% of true positives.
Not `l`-compatible: backreferences, lookarounds (a lookbehind or complex lookahead), etc.
Exponential confirmed: npm 79, web 48 (they are hard cases: e.g. CSS tokenizers
`^'(?:[^\n\r\f\\']|\\(?:\r\n?|\n|\f)|\\[\s\S])*'`, `^(.*\.)*(meta\.com)\.?$`).

Caveats:
- "Confirmed" includes 2 s timeouts at 32 kB. These are quadratic cases (`^\s+|\s+$`, `\/+$`, `#.*$`).
  Practical risk depends on whether input is attacker-controlled and long; I did not check that. [BELIEF] Most hits are on trimmed/internal strings.
- "Safe" for recheck is not a proof; the checker can time out (unknown) and I count it as not safe.
- Counts are unique regexes; occurrence-weighted rates differ (not computed).
- Vulnerable-but-not-confirmed (~100 each) are likely false positives or too slow to confirm in 2 s.

## Examples seen widely [FACT measured]
`^\s+|\s+$` (111 packages, 43 sites; quadratic: 32 kB of spaces then a non-space took ~2 s),
lodash template regexes `<%=([\s\S]+?)%>`, `hasOwnProperty|(function).*?(?=\\\()| for .+?(?=\\\])` (188 packages).

## Data and rerun
- data/pkgs_rx.json, data/web_rx.json: extracted regexes; data/out/*.jsonl: per-regex results;
  data/confirmed_{pkgs,web}.json: confirmed TPs with timing points.
- Run: `cd work; node extract.js ../untrusted_pkgs/tgz ../data/pkgs_rx.json` (2.5 min);
  `node extract_web.js ../untrusted_web/js ../data/web_rx.json`;
  `for i in $(seq 0 23); do node --enable-experimental-regexp-engine analyze.js ../data/pkgs_rx.json $i 24 ../data/out/pkgs_$i.jsonl & done`
  (5 min on 128 cores); then `python3 -I agg.py` from data/.
- Fetching: fetch.sh (npm), web.sh (sites). Downloaded content is only in untrusted_*/.
- Not done: PCRE-style prefix/backtracking limits, occurrence weighting, CVE-matching, taint check on inputs.
