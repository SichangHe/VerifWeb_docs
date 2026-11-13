# vlm2_scripts summary: targets 11-13 checked on real scripts
(authored by agents unless marked 🧑)

Per-target reports, each with run instructions and [FACT]/[BELIEF]/[PRIOR] labels: t11_proto/REPORT.md, t12_offorigin/REPORT.md, t13_regex/REPORT.md. Nothing was filed upstream and no one was contacted (🧑 "Let's keep things to ourselves for now").

## 11. Prototype integrity
- Method: snapshot built-in prototypes before and after each call. 129 npm package versions, 283 APIs, 5370 hand-written pollution payloads. Also loaded 95 real sites in headless Chrome.
- [FACT] Packages: 46 of 129 versions polluted a built-in prototype. Old lodash, jQuery, minimist, yargs-parser, etc. polluted as expected.
- [FACT] Two current versions still changed a built-in: mout 1.2.4 changed `Object.prototype`, and nested-property 4.0.0 changed `Array.prototype`.
- [FACT] Sites: 63 of 95 changed a standard built-in after load. `Function.prototype.toString` was replaced on 35. `Object.prototype` changed on espn.com, wix.com and lenovo.com.
- Limits: the payloads are hand-written; there is no clean-page control run; changes can be blamed on a specific script only partly.

## 12. Third-party off-origin data flow
- Method: 532 real login, signup and cart pages in headless Chrome. Fields were filled with canary values; raw, encoded and hashed forms were detected in outgoing requests.
- [FACT] Passwords: 0 of 68 pages leaked the password canary.
- [FACT] Emails: 11 of 139 pages sent the email to a third party before any submit. 8 sent a SHA-256 hash (pinterest, google), which a plain-text search would miss. 3 sent it raw or lightly encoded; usbank.com sent it raw to quantummetric.
- [FACT] Script integrity: only 3.1% of 6894 cross-site script tags had an `integrity` attribute (SRI), and 8 of 378 pages had it on every cross-site script.
- Gap: the card-at-checkout case is untested, because only 2 pages had card fields.

## 13. Linear-time regex
- Method: 14.6k unique regexes from 2991 npm packages and 13.9k from 97 websites. Each checked three ways: V8's linear engine (`l` flag), the static checker `recheck`, and timed attack strings in node.
- [FACT] About 12-13% are confirmed super-linear in node. Almost all are polynomial; 79 (npm) and 48 (web) are exponential.
- [FACT] About 75-78% are provably linear: accepted by `l` or rated linear by `recheck`.
- [FACT] About 70% of the confirmed super-linear cases are accepted by `l`, which runs their attack strings in a median of about 12 ms.
- Limit: whether attackers can reach these regexes with long input is unchecked.

## Relation to dynstate (round 1)
- These checks are dynamic monitors and corpus measurements. The z3 symbolic executor from round 1 was not extended, because its JS subset cannot parse real scripts.
