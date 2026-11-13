(authored by agent)

# rust-url 2.5.8 vs WHATWG URL: differential check (TARGETS.md target 7)

Verdict: the property "rust-url parse(s,b) == WHATWG basic URL parser" does NOT hold for url 2.5.8.
Nothing was filed upstream and no maintainer was contacted (human instruction: keep local).
Upstream issues were only read, to triage.

## Setup
- sut: `url = "=2.5.8"` (idna 1.1.0) via `harness/` (Rust binary, JSONL in/out; `batch` and `prop` modes)
- reference 1: npm `whatwg-url` 17.3.0 (JS port of the spec; passes 896/896 of WPT urltestdata)
- reference 2: Node 22.21.1 builtin URL (Ada 2.9.2); older than spec, disagrees with whatwg-url on ~8% of fuzz cases, so used only as a tiebreaker
- base handling: rust = `Url::parse(base)?.join(input)`; ref = `new URL(input, base)`
- compared fields: href, protocol, username, password, host, hostname, port, pathname, search, hash, origin
- data: WPT `urltestdata.json` and `setters_tests.json` fetched from raw.githubusercontent.com/web-platform-tests/wpt master on 2026-11-03 (`data/`)

## Commands (cwd = this dir)
- build: `cd harness && cargo build --release`; refs: `cd ref && npm i whatwg-url`
- WPT: `node wpt.js` (full failure list: `data/wpt_rust_failures.txt`)
- fuzz: `node fuzz.js SEED N OUT.jsonl` (generator `gen.js`); run with seeds 11-18, 21-44, N=2,000,000 each
- minimize + cluster: `node minimize.js 3000 data/min_all.jsonl data/fz_1[1-8].jsonl data/fz_2*.jsonl`; `node cluster.js`; `node classify.js`
- property test: `node prop.js SEED N OUT.jsonl` (seeds 101-104, N=2,000,000)

## Counts
- WPT urltestdata: 896 tests; rust-url fails 69 (7.7%); whatwg-url fails 0; Node/Ada fails 15
  - setters_tests.json: see Round 2 below
  - skipped upstream: not checked in rust-url's own harness
- differential fuzz: 64,000,000 cases (32 seeds); 30.06M parsed OK by reference; 2,910,747 divergences (4.5%); 0 panics
  - the generator is divergence-seeking (schemes, file:, drive letters, `..`, `%2e`, IPv4/IPv6, IDNA, userinfo, ports, C0 controls, bases, WPT-mutation); the 4.5% rate is not a real-world rate
  - 3000 randomly sampled divergences (from 1.54M in seeds 11-18, 21-44) were delta-minimized (input and base) and clustered
- property test (parse -> serialize -> parse equal, `as_str` idempotent, components equal, `join(self)==self`): 8,000,000 cases, 406 violations; 100% are the file-host/drive-letter bug (P1 below)

## Minimized divergences (rust vs spec). Verdict: rust-url wrong in every case
Spec = https://url.spec.whatwg.org/ (basic URL parser). "Upstream" = servo/rust-url issue read via gh; all OPEN unless noted.
Share = fraction of the 3000 minimized sample (heuristic classifier `classify.js`; shares are approximate).

1. D1 caret in path percent-encode set (~25%)
   - `parse("^", base "t:/")`: rust `t:/^`, spec `t:/%5E`
   - spec: path percent-encode set (adds U+005E); path state
   - upstream: #1140 (CLOSED 2026-07-08; fix not in 2.5.8)
2. D2 file: empty path segments dropped (~28%, shares overlap with D3)
   - `parse("file:////")`: rust `file:///`, spec `file:////`; `file://localhost//a//../..` likewise
   - spec: file state / path state, "shorten a URL's path", only drops when path non-empty segments; empty segments kept
   - upstream: #1160 (`..` case); the plain `file:////` form is covered by WPT failures, not separately reported as far as I read
3. D3 file: host dropped before drive letter (~13%)
   - `parse("file://h/C:")`: rust `file:///C:`, spec `file://h/C:`; also `/C:/` against base `file://host/`
   - spec: file host state sets host; host is cleared only when the *buffer* is a Windows drive letter (i.e. `file://C:/`), not when the path starts with one
   - upstream: #1126 (CLOSED 2026-07-31, fix not in 2.5.8)
4. P1 same bug breaks roundtrip (406/406 property violations)
   - `join("/./C:/a", base "file://host/path")` gives `file://host/C:/a` (host kept) but `Url::parse` of that string gives `file:///C:/a`
   - violates parse(serialize(u)) == u and idempotence. Also `u.join(u.as_str()) != u`
   - upstream: #1101 (file:// roundtrip mismatch), #1102
5. D4 backslash in non-special URLs (~13%)
   - `parse("\\\\x:8", base "b:/")`: rust `b://x:8`, spec `b:/\\x:8` (backslash is not a separator in non-special URLs)
   - `parse("d://%:\\")`: rust accepts `d://%/\`; spec fails (port state: non-digit `\`, non-special, port-invalid)
   - spec: relative state / relative slash state / authority & port state `is special` conditions
   - upstream: #1155 (port), #1156 (host on join); `\\a` WPT cases fail too
5b. D4' special base + `///x` (~2%): `parse("///c", base "http:.")`: rust failure, spec `http://c/`
   - spec: special authority ignore slashes state skips extra slashes
   - upstream: #1164
6. D5 bogus `xn--` ASCII label (~9%)
   - `parse("http:xn--")`, `https://xn--/`, `file://xn--/p`: rust failure, spec accepts (`http://xn--/`)
   - spec: domain to ASCII; recent UTS46 change "pass through bogus xn-- labels if whole domain is ASCII" (whatwg/url#914)
   - upstream: #1135. Note the pinned WPT and whatwg-url 17.3.0 already follow the new behavior; Ada (Node 22) does not
7. D6 opaque path trailing/inner space before `?`/`#` (~2%)
   - `parse("l: #")`: rust `l: #`, spec `l:%20#`
   - spec: opaque path state (strip trailing spaces from opaque path before query/fragment, URL Standard 2025 change)
   - upstream: not found in the 400 issues I read (only #847 setters, #815). Candidate unreported
8. D7 `..` pop refuses to pop a drive-letter-shaped segment in non-file URLs (~3%)
   - `parse("..", base "c:/C:/")`: rust `c:/C:/`, spec `c:/`; `parse("..", "http://[::]/C:/")`-style, `ws:b/c|/..`
   - spec: "shorten a URL's path": drive-letter exemption applies only if scheme is file
   - upstream: #1130 (non-special `..`), #1114 (panic; I could NOT reproduce a panic on 2.5.8 with `file:..` against `file:///w:/a:`)
9. D8 drive letter `|` not normalized in some contexts (~0.5%)
   - `parse("file:///C|")` and `parse("///C|", base "file:")`: rust `file:///C|`, spec `file:///C:`
   - spec: file state / path state, "normalize a Windows drive letter" when buffer is a drive letter
   - upstream: #889
10. N1 `file:b:\tx` gets an extra slash (new)
   - `parse("file:b:\tx")`: rust `file:///b:/x`; spec (tab removed first) `file:///b:x`. Same with `\r`. Without the tab it is correct
   - spec: "remove all ASCII tab or newline from input" precedes file state; "starts with a Windows drive letter" is evaluated on the stripped string
   - upstream: not found in read issues. Candidate unreported
11. N2 non-special empty host with empty credentials accepted (new)
   - `parse("b://@")` and `a://:@`: rust `b://`, spec failure; but rust correctly fails `a://u@`
   - spec: authority state at EOF: "If atSignSeen is true and buffer is the empty string, host-missing validation error, return failure" (any scheme)
   - upstream: only #1112 (Host::parse_opaque allows empty hosts) is nearby; not the same. Candidate unreported
12. N3 blob origin (not a parser divergence)
   - `blob:ws://example.org/`: `Url::origin()` is `ws://example.org`, WPT/spec says `null` for a blob not in the blob store
   - spec: URL "origin" getter, blob case. Deliberate rust-url design; excluded from the 69 "parser" WPT failures count of href (4 of 69 are origin-only)

## Triage notes
- fact: every divergence that survived minimization had rust-url wrong; whatwg-url (spec port) agrees with WPT expected values in all 896 tests
- fact: classify.js left 93/3000 unclassified; spot-checked ones were D4 port, D8/D7 `%2e%2e` variants, N2, N1
- limits: minimization keeps the same set of differing fields, not same root cause, so one reduced case can hide a second bug; shares are heuristic; the 3000-sample is 0.2% of divergences so rare bugs may be missing; setters/IDNA-version differences not exhaustively fuzzed; only `join` entry point exercised
- whatwg-url vs Ada disagreement rate shows the reference matters: always check the reference against current WPT before blaming the SUT

# Round 2 (setters, larger minimized samples, rare-cause hunting)
Same rules: nothing filed upstream, no maintainer contact; upstream issues only read.

## New commands
- WPT setters: `node wpt_setters.js` (failures: `data/wpt_setters_rust_failures.txt`)
- setter fuzz: `node fuzz_set.js SEED N OUT.jsonl [rare]`; setters via `url::quirks::set_*` (the WHATWG-API layer in rust-url) vs `whatwg-url` setters
  - only start URLs on which rust and ref already agree on parse are used (isolates setter bugs from parser bugs); start URLs are canonicalized to the ref href
- setter minimize/cluster: `node minimize_set.js 1500 OUT.jsonl IN.jsonl`, `node cluster_set.js FILE`
- parser big minimize: 32 shards, `node minimize.js 3000 data/minB_i.jsonl data/fz_*.jsonl` (merged `data/min_big.jsonl`); `MIN=file node classify.js`
- rare-cause hunting: `node fuzz.js SEED N OUT.jsonl rare|rarefile|rarefile2` drops inputs that contain a known root-cause trigger (caret, `xn--`, backslash, drive letters, leading `///`, space before `?#`; `rare` also drops file:; `rarefile*` also drop empty-path-segment triggers)

## Counts
- WPT setters_tests.json: 278 tests; rust-url fails 22 (7.9%); whatwg-url 0; Node/Ada 14
  - failing groups: `host`/`hostname`=`xn--` (D5), `/.` path-prefix handling for non-special URLs (4 `pathname`, 2 `hostname`), file: pathname with (back)slashes (D2), pathname percent-encoding incl. `^` (D1), opaque-path trailing space on search/hash set to "" (D6), `port` setter with only tab/newline value, pathname `""` on `foo:///some/path`
- setter fuzz: 32,360,142 setter applications (40 seeds x 2M generated, 47.6M generated start URLs discarded because parse failed or diverged); 398,579 divergences (1.2%); 0 panics
  - minimized+clustered 48,000 (1500 per seed, 32 seeds); 1882 raw clusters by shape; by attribute: pathname 23,798, href 11,906, host 5,280, hostname 3,649, protocol 3,367
  - serialization check on those 48,000 rust outputs: 677 do not reparse to themselves, 29 do not reparse at all (e.g. `a://:p@`); this is the setter route to the roundtrip violation
- parser: 96,000 divergences minimized (32 seeds x 3000, 3.3% of the 2.91M) instead of 3000
- rare-cause runs (inputs with known triggers filtered out):
  - `rare` (no file:, 72M cases, 669k accepted by ref): 69 divergences, all one cause (N2)
  - `rarefile` (48M cases, 337,719 divergences, 32,000 minimized) and `rarefile2` (24,000 minimized): every cluster was D2 (file: empty segments) or D8 (`C|`) or N2; filter leaked D2 shapes (`file:////`)
  - setter `rare` (5.36M applications, 194 divergences): 176 are S2 (below), 18 are S5 (below)
  - interpretation (inference): within this generator, no root causes beyond the list below remain; the generator is limited (no IDNA-table edge cases beyond a hand list, no `encoding_override`, no unusual schemes beyond list), so this is not a proof

## Parser root-cause counts in the 96,000 minimized sample (first-match heuristic, overlapping shapes)
- D2 file empty path segments 27,385; D1 caret 24,370; D4 backslash non-special 12,882 (+~1,400 unclassified `x://y:\` port-state variants); D3 file host dropped 11,590; D5 xn-- 8,866; D4' `///x` special 2,249; D8 pop_path drive-letter exemption 3,234+886; D6 opaque space 2,233; `C|` normalization 565; blob origin 289
- N2 `b://@` 24 (rare: found only by the filtered runs at scale; 3 per 100k of the filtered stream); N1 `file:b:\t0` 5 in 96,000
- unclassified 1,422, of which ~99% are D4 port-state variants (`d://x:\`); remainder checked by eye: D6, D8, N2

## Setter divergences (rust-url wrong per spec in every case; spec = URL Standard API section, setters + basic URL parser with state override)
S1. `pathname=""` on non-special empty-host URL: `d://`.pathname="" gives `d:///`, spec `d://` (WPT-known; ~15% of sample)
S2. `pathname="//"` on non-special URL without host: `o:/`.pathname="//" gives `o://` (path became a host!), spec `o:/.//` (serializer adds "/." when host is null and path starts with an empty segment). Corrupts the URL; reparse gives a different URL. WPT-known; also `%2e//`, `/..//`. Upstream: related #601 (CLOSED, parse only); not found for the setter. Candidate unreported
S3. `protocol="file"` on `http://n/`: rust no-op, spec `file://n/` (allowed: no credentials, no port). Upstream: #553, #955 (OPEN)
S4. `host=":"` on `x:/` or `a://a`: rust sets an EMPTY host (`x:///`, `a://`), spec: host state with empty buffer before `:` returns failure, URL unchanged. Candidate unreported
S5. `host=""`/`hostname=""` on non-special URL with credentials, e.g. `a://:p@1`.host="": rust gives `a://:p@` (unparseable on reparse), spec: "if state override is given, buffer is the empty string, and either url includes credentials or url's port is non-null, return" => unchanged. Candidate unreported. Same family as N2 (credentials with empty host)
S6. `pathname` starting with tab/newline then a slash or backslash (`d:/`.pathname="\t/", `http://e`.pathname="\n\\"): rust does not strip the control first, yields `d://` / `http://e//`, spec `d:/` / `http://e/`. Setter twin of N1. Candidate unreported
S7. `host`/`hostname` = `/`, `?`, `#` on `file://x`: rust leaves the host, spec clears it (`file:///`) (file host state, empty buffer). Candidate unreported
S8. `hostname=""` on `c:/.//`: rust `c:///.//`, spec `c:////` (WPT-known `/.` handling)
S9. D1/D5/D6/D8 repeats through `pathname`, `host`, `href`, `search`/`hash` (`""` on opaque path with trailing spaces)
S10. `port` = tab/newlines only on `https://domain.com:3000`: rust removes the port, spec keeps it (WPT)
- upstream already known: #974 CLOSED (port setter prefix), #815, #847 CLOSED, #955, #553, #1118 (leading slashes dropped setting pathname for file urls, OPEN), #1102 (set_host("localhost") on file roundtrip, OPEN)

## Round-2 limits
- setter fuzz only starts from URLs on which parse agrees, so interactions between a parse bug and a setter are excluded by design
- `quirks::set_*` was tested, not the typed `Url::set_*` API (which intentionally differs, e.g. `set_host(None)`)
- rare-mode filters are string heuristics and leak (tab/newline obfuscation was fixed once; `file:////` shapes still leak)
- classification counts are heuristic and not mutually exclusive in cause
