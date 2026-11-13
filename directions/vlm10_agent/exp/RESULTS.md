# Pilot: agent-targeted cloaking, Tranco top 500 (run 2026-11-06)
(authored by agents unless marked 🧑)

Scripts: `fetch.py`, `analyze.py`. Data: `data/` (tranco list, `fetched.jsonl` with full visible text, `flagged.json`).

## Method [F]
- Tranco top-1m list, first 500 domains. Fetched `https://<domain>/` once per client, in this order per site: Chrome 141 (Windows), ChatGPT-User, Claude-User, GPTBot, Chrome again. 8 sites in parallel, 0.5s pause between a site's fetches, 15s timeout, redirects followed, plain `requests`, no JS.
- UA strings (my reconstruction of the vendor-documented strings, not re-verified against vendor docs this session):
  - ChatGPT-User: `Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot`
  - Claude-User: `Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-User/1.0; +Claude-User@anthropic.com)`
  - GPTBot: `Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.1; +https://openai.com/gptbot`
- Visible text: BeautifulSoup, scripts/styles/noscript/template removed. Fetched content was only parsed, never executed; Python ran with `-I`.
- Noise = word-set Jaccard(Chrome1, Chrome2). Flags per agent UA vs Chrome1:
  - blocked: agent status >=400 where Chrome's differs, or connection error
  - status: other status difference (e.g. 200 vs 202)
  - redirect-host: final hostname differs
  - diff: Jaccard < noise-0.1 and < 0.9
  - instruction-like: regex (ignore previous/prior/above, AI agent, LLM, assistant, language model, ChatGPT, Claude, system prompt, GPT) matching in agent text but not in Chrome text.
- Only sites where Chrome1 returned <400 are analysed.

## Counts [F]
- 500 sites. Chrome1 failed on 236 (134 ConnectionError, 18 SSLError, 22 timeouts, ~60 HTTP 4xx). Likely many are apex domains needing `www.` or CDN/infra domains; I did not retry. 264 analysed.
- Chrome-vs-Chrome noise: median Jaccard 1.00; a few dynamic pages lower (google.com 0.89, googlesyndication 0.73, goodreads/intuit/checkpoint 0.00 because Chrome2 got a block/challenge).
- Among 264 (any of the 3 agent UAs):
  - blocked: 38 (ChatGPT-User 28, Claude-User 22, GPTBot 36). Mostly 403; also 402 (x.com), 406, 429, 451, 999, connection error.
  - status-only difference: 5
  - redirect to a different host: 12
  - content differs beyond noise (status OK): 23
  - instruction-like phrases absent from Chrome: 1 (sharepoint.com; false positive, see below)

## Examples [F unless marked]
1. openai.com: Chrome 200 (449,955 B); ChatGPT-User, Claude-User, GPTBot all 403, empty text. [I] Cloudflare-style bot gating that also blocks OpenAI's own UA string because the UA is spoofed without verified IPs.
2. medium.com: agents 403, text `Just a moment...` (Chrome: `Medium Medium: Read and write stories...`). Challenge page.
3. reddit.com, pinterest.com: ChatGPT-User and GPTBot 403; Claude-User got 200 (reddit, pinterest). Per-UA selective blocking: the one clear UA-specific split.
4. theguardian.com, digicert.com, instagram.com: only Claude-User differed (Guardian 403; digicert 1,029 B vs 69,362 B; instagram Jaccard 0.01).
5. yahoo.com: GPTBot 429 `Edge: Too Many Requests`; ChatGPT-User 404; Claude-User 200 (Jaccard 0.65). [I] possibly rate-limit/WAF noise.
6. google.com: all agent UAs got a reduced page: `Google All Images Sign in × Privacy Terms Settings...` vs Chrome `Google About Store Gmail Images Sign in What's on your mind? ... AI Mode`. Jaccard 0.24. Same for googlesyndication.com, withgoogle.com. [I] Google serves a legacy/no-JS page to unrecognised UAs; benign.
7. bilibili.com: agents redirected to `.../blackboard/fe/activity-CjJbuaD7Xw.html`: `浏览器下载建议 您的浏览器版本过低哦...` ("your browser is too old"). Chrome got the real homepage. UA sniffing.
8. weibo.com: Chrome sent to `passport.weibo.com/visitor/...` (`Sina Visitor System`); agents got the real page at `weibo.com/us`. Agents got more content than Chrome.
9. dailymotion.com, booking.com, sentry.io: Chrome got near-empty text (`Dailymotion`; 202 empty; Chrome with 628 KB) while GPTBot/ChatGPT got full page (dailymotion, booking) or empty text (sentry: agents 19 KB, empty visible text, Chrome full). Mixed direction; likely JS/challenge shells.
10. microsoft.com / sharepoint.com: Chrome text began `Your request has been blocked. This could be due to several reasons.`; agents got the full en-us page (`Microsoft – AI, Cloud, Productivity...`). The sole "instruction-like" hit (sharepoint: `Secure AI chat powered by the latest large language models`) is ordinary marketing copy present only because Chrome was blocked. Chrome-side blocking, not cloaking.
Also: amazon.com/.co.uk: agents 202 with identical 2,007 B body to Chrome (Jaccard 1.0; Chrome also got a challenge-size page). twitter.com/x.com: agents 402 (55 B) vs Chrome 200. cnn.com: agents 451 (38 B). charter.net: agents 403 with the same 328,467 B body as Chrome.

## Findings
- [F] Agent UAs are blocked far more than Chrome: ~14% of analysable sites block at least one (36/264 for GPTBot).
- [F] Genuine injected instruction text aimed at agents: 0 found in this sample.
- [I] Most "content differs" cases are bot walls, challenge pages, legacy-page fallbacks, or UA sniffing, not adversarial cloaking. Chrome itself was sometimes the one challenged (microsoft, weibo, dailymotion, booking), so "differs" is not "worse for agents".
- [I] 0/264 is consistent with the low base rate the directions doc anticipated; the sample (top 500, homepage) is too small and too benign to bound it tightly.

## Limitations
- No JS rendering, so JS-served content and JS challenges look like empty pages.
- Homepages only; apex domain over HTTPS only (no `www.` retry), 236 sites lost.
- UA only: no TLS/HTTP2 fingerprint, no vendor IP ranges, so real bot-verification (reverse DNS, signed requests) fails by design; the blocks above are what a spoofed UA gets, not what the real ChatGPT-User/Claude-User crawlers get.
- One fetch per client per site: transient 429/403 and A/B variation not separated from cloaking beyond the single Chrome repeat. Single vantage point (one IP/region).
- Instruction-like regex is crude (false positives on marketing copy about AI); no check of hidden/non-visible text, comments, or headers.
- "Top 10 manually inspected" were chosen from the flagged list by variety; inspection used truncated text snippets, not full diffs.
