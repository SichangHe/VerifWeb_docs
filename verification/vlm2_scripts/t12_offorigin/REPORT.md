# Target 12: do third-party scripts move sensitive data off-origin? Measured on 532 real URLs
(authored by agents unless marked 🧑)

Date 2026-11-03. Canary values only; no form submitted, no account, no purchase. Typing alone (no submit) was enough to trigger most of the leaks below.

## Takeaway
- [FACT measured] raw passwords: 0 of 68 pages with a filled password field sent the canary password (raw or encoded) to another registrable domain
- [FACT measured] emails: 11 of 139 pages with a filled email field sent the canary email to a third-party site, pre-submit, within ~4 s of typing
  - 8 pages (5 sha256-hex to pinterest.com, 3 sha256-base64 to google.com; Zoom, Disney+, Eventbrite, Asana, Shein, Wish...): hashed email via ad-tag "enhanced matching"
  - 3 pages: plaintext/base64/url-encoded email: usbank.com -> quantummetric.com (raw, in fetch body, session-replay script `cdn.quantummetric.com/qscripts/quantum-usbank.js`); cosmopolitan.com -> attentivemobile.com (base64, `cdn.attn.tv/.../unified-tag.js`); login.taobao.com -> mmstat.com (double-url-encoded, `g.alicdn.com/.../havana-nlogin` script; mmstat is Alibaba's own analytics, so "third party" is a same-company guess [BELIEF])
- [FACT measured] hashing is the dominant form: a plain-text grep for the canary would have missed 8 of 11 email-leak pages
- [FACT measured] card number/CVV: only 2 pages (eff.org/donate, supporters.eff.org/donate) exposed card fields in my crawl, 0 leaks. The sample is too small to say anything about checkout pages (see Limits)
- [FACT measured] generic text fields (search boxes etc.): 9 pages sent the canary to a third party. Most are search/RUM vendors (Algolia, Typesense, Datadog RUM, Dynatrace, Shopify); these are search queries or monitoring, not necessarily sensitive. Not counted in the headline
- [FACT measured] 1 hit was a false positive: freelancer.com "cvv" canary matched as hex of 3 digits inside a URL token (f-cdn.com). Short canaries (3 digits) collide; the CVV result is unreliable
- [FACT measured] SRI: of 6894 cross-site `<script src>` tags on 378 pages (registrable-domain test), 215 (3.1%) had `integrity`; only 8 of 378 pages had integrity on every cross-site script. Heaviest no-SRI hosts (pages): googletagmanager.com 537 tags, adobedtm.com 449, doubleclick.net 262, tiqcdn.com 191, facebook.net 176. (Tag counts are per script tag, summed over pages.) Dynamic scripts inserted by tag managers are not in this count if they were not in the DOM at the end
- [FACT measured] reading: on pages where I filled fields, a third-party-origin script was on the stack of a sensitive-field listener on 143 pages and of a `.value` read on 59. Top third-party registering global key/input listeners: googletagmanager.com 47 pages, cloudflareinsights.com 21, gstatic.com 20 (reCAPTCHA), openai.com 11, datadoghq-browser-agent.com 10, clarity.ms 10, px-cloud.net 9, contentsquare.net 9
- [FACT measured] median 17 third-party requests per page (first-load + typing); top contacted: googletagmanager.com (174 pages), google.com (166), doubleclick.net (143)

## What property was actually tested
- Property (from TARGETS.md 12): "no script reads payment or credential fields and sends them to an origin outside an allowlist"
- Allowlist used: same registrable domain (tldts) as the final page URL. So a first-party CDN on another domain counts as third party; this over-counts (e.g. taobao/mmstat) and I checked the hits by hand only for the ones named above
- Violations by that definition are common for email (11/139) and absent for password (0/68). Whether they are "bad" is a policy question: hashed-email ad matching is a documented feature, quantummetric session replay is contracted by the bank [BELIEF]. BA/polyfill-style malicious theft was not observed [FACT: no such hit among 532 URLs]
- SRI alone would not have prevented any hit: the leaking scripts were mostly dynamic or vendor-updated tags (tag managers, Pinterest `main.*.js`, Quantum Metric) [BELIEF: they are not pinned by hash; I did not inspect each tag's integrity attribute]

## Method
- `crawl.mjs`: Playwright-core driving /usr/bin/google-chrome (headless, no sandbox), 1 fresh context per URL, 25 s goto limit (domcontentloaded) + 3.5 s settle
- fills every visible input/textarea (max 15) in the main frame and up to 5 iframes using `focus()` + real keystrokes (keydown/keyup/input fire), Tab to blur, waits 4 s; classifies field by type/name/id/autocomplete/placeholder into password/email/phone/card/cvv/name/text
- canaries per page: random email, password, Luhn-valid card (4929...), 3-digit cvv, phone, name, text
- `hook.js` (init script): hooks `HTMLInputElement/TextArea.value` getter, `FormData`, `addEventListener` for key/input/change/paste, `fetch`, XHR, `sendBeacon`, `Image.src`, `WebSocket.send`; each event records the stack's script URLs
- network side: CDP `Network.requestWillBeSent` (url, headers, postData, initiator stack for script attribution) and `webSocketFrameSent`. Each third-party request is searched for canary variants: raw, lowercase, url-encoded (x1, x2), hex, base64 and url-safe base64 (3 alignments), md5/sha1/sha256/sha512 as hex and base64
- not covered: salted/custom hashes, encryption, compressed/binary bodies (gzip, protobuf, JSON inside a deflate), requests from workers/other-origin iframes' own scripts, `Image` requests have no script initiator (they show scripts only via hook.js, not in the hit table); the CDP `postData` may be truncated for large bodies
- positive control: `control.mjs` serves a malicious third-party script that leaks email (url-encoded Image, SHA-256 via fetch), password (base64 sendBeacon), card (XHR body). `control.jsonl`: detector found all of them [FACT measured]. Control result also shows script attribution missing for Image beacons
- extends round-1 work only conceptually: dynstate (`vlm_runtime/dynstate`) and the Lightpanda monitor were NOT reused; Lightpanda's default skips `<img>`, iframe and `sendBeacon`, so it would miss these sinks [PRIOR from lightpanda REPORT.md]. I used Chrome because the sinks matter. Not run on Lightpanda.

## Coverage numbers [FACT measured]
- 532 URLs (398 login/signup/account pages + 134 donation/subscription/cart pages), `urls.txt`, `urls2.txt`; 505 loaded with requests, 27 errored (14 ERR_HTTP2_PROTOCOL, 5 ERR_NETWORK_CHANGED, 3 timeout, 3 ERR_HTTP_RESPONSE, 1 download, 1 hard timeout; belief: bot blocking, no stealth used)
- 228 pages had at least one fillable visible field (437 fields; 14 in iframes). 277 loaded pages had none (landing pages, JS-gated login, cookie-banner overlay, cart empty)
- pages with a filled field by class: email 139, password 68, text 115, name 15, phone 6, card 2, cvv 2

## Limits
- no real checkout: card pages need items in a cart and often payment fields live in a cross-origin processor iframe (Stripe etc.); only 2 pages had card fields. Target 12's headline case (checkout card data) is therefore NOT tested; the evidence is for email/password at login/signup
- pre-submit only: leaks that occur at submit were not exercised
- single vantage (this IP, one run, headless Chrome); consent banners were not accepted, so many trackers may not have fired (belief: leak rate is a lower bound). Not repeated
- a canary email is `@canary-mail.test`, which some ad tags may drop or reject; unaffected by hashing
- registrable-domain first-party test is crude

## Run
```
cd /hdd1/sichangheagent/vl_meeting_work/out/vlm2_scripts/t12_offorigin
npm i playwright-core tldts                       # already installed here
node crawl.mjs urls.txt  crawl1.jsonl 8           # args: list, output, concurrency (~1 h for 398)
node crawl.mjs urls2.txt crawl2.jsonl 5
cat crawl1.jsonl crawl2.jsonl > crawl_all.jsonl
node analyze.mjs crawl_all.jsonl analysis.txt     # tables printed above
node control.mjs & node crawl.mjs urls_control.txt control.jsonl 1   # positive control (kill the server after)
```
Files: `crawl.mjs`, `hook.js`, `analyze.mjs`, `control.mjs`, `urls*.txt`, raw data `crawl_all.jsonl` (per URL: requests count, canary hits with attributed script, hook log, SRI list), `analysis.txt`.

## Next steps [BELIEF]
- add a cart-seeding flow for demo shops (WooCommerce/Magento/nopCommerce) to reach first-party card fields; accept consent banners; do the submit step on a test merchant with a sandbox card
- verify each leaking script by hand and diff its bytes across runs to test "bytes match a pinned hash"
