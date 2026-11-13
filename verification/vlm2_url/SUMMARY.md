# vlm2_url: targets 7 (URL vs WHATWG) and 8 (sanitizer fixed point)
(authored by agents unless marked 🧑)

Nothing filed upstream; no maintainer contacted (per human: "Don't file those issues").

## Target 7: rust-url 2.5.8 does not match WHATWG
- Verus proof (`verus_path/README.md`): port of rust-url path code proved equal to a hand-transcribed WHATWG path state except where the drive-letter check `last_slash_can_be_removed` fires without a scheme check; there a lemma proves divergence.
  - `http://h/C:/../x` -> `http://h/C:/x` (spec: `/x`), same family as rust-url #1130
  - base `file:///a/C:` + `..` hits `debug_assert!` parser.rs:1321 (debug panic, wrong URL in release)
  - also `file:///c|` not normalized; `file:///a/C:` + `x` -> `C:x`
  - limits: spec-level port, not executable Rust; percent-encoding/query/fragment not modelled
- Differential (`diff_url/README.md`), reference npm whatwg-url 17.3.0:
  - WPT urltestdata: rust-url fails 69/896 (whatwg-url 0)
  - 64M fuzz cases: 2.91M divergences, 0 panics; minimized sample of 3000 always shows rust-url wrong
  - parse∘serialize: 406/8M violations, one bug (`file://host/C:/..` host lost on reparse)
  - most root causes already in upstream issues; apparently new: tab not stripped before drive-letter check (`file:b:\tx`), `b://@` accepted, unencoded space in opaque path `l: #`
- setters (`url::quirks::set_*`): WPT setters fail 22/278 (whatwg-url 0); 32.4M setter fuzz -> 1.2% divergent, 0 panics; 29 outputs unparseable (e.g. `a://:p@`)
  - apparently new: `pathname="//"` turns `o:/` into `o://` (spec `o:/.//`); `host=":"` empties host; file `host="/"` not cleared; leading tab before `/` not stripped
- filtered rare-cause fuzz (125M cases) found almost nothing beyond the above (not a proof)

## Target 8: ammonia 4.2.1 + html5ever
- default config: no script-capable output found (~10M execs, 157 known mXSS payloads, parse5 differential)
- but not a fixed point: `clean(clean(x)) != clean(x)` on ~6.5% fuzz outputs (e.g. `<a><table><a>`); same nesting family as DOMPurify mXSS, no exploit found
- real XSS in non-default config: allowing `noscript` lets `<noscript><img src=x onerror=alert(1)></noscript>` through; scripting-off parsers (DOMParser, mail clients) build a live `onerror`
- gaps: Kani 0.68 ICEs on ammonia deps; deep-nesting run timed out without result; no real browser used
- details: `html_sanitize/README.md`
