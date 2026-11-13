# Servo as an agent renderer: web compat and automation
(authored by agents unless marked 🧑)

Research only (reading and searching; nothing built or run), 2026-11-08. Servo source: shallow clone of github.com/servo/servo at the 2026-11-08 commit, in `src/servo`.

## Direct answers
- CDP: no. The source tree has no CDP server. Servo's devtools server speaks the Firefox remote debugging protocol, not CDP. So Puppeteer and Playwright cannot drive it as they normally do.
- WebDriver BiDi: no. Servo passes 0.0% of the WPT BiDi tests.
- WebDriver classic: yes. `servoshell --webdriver[=port]` starts it, and it passes 86.5% of the WPT classic WebDriver tests. Selenium-style W3C clients work with it.
- Headless: yes. There is a `--headless` flag. I found no documented headless-specific blockers.
- Web compat: behind every major engine, mainly in CSS layout. DOM is at parity (98.0% vs Chrome's 99.8%). CSS overall is 55.6% (Ladybird 90.2%).
- Real-site compatibility (top-sites studies): I don't know. I found no systematic report.

## Automation evidence
- Servo `components/devtools/lib.rs` (2026-11-08 commit): "An actor-based remote devtools server implementation. Only tested with nightly Firefox versions at time of writing. Largely based on reverse-engineering of Firefox chrome devtool logs".
- grep over `components/` and `ports/` for "cdp", "chrome devtools", and protocol-level "bidi" found no automation code. ("bidi" only appears as Unicode bidirectional text.)
- `components/webdriver_server/` exists, with session, actions, capabilities, timeouts, and user prompts.
- `ports/servoshell/prefs.rs`: "Whether or not to run servoshell in headless mode. While running in headless mode, image output is supported."
- Servo blog, [This month in Servo, 2025-07-17](https://servo.org/blog/2025/07/17/this-month-in-servo/): "Work continues on our WebDriver server, which can be used to automate Servo". It also says Servo rejects the `goog:chromeOptions` capability with "Session not created due to invalid capabilities". That is the Chrome-specific option many client libraries send by default.
- Implication (inference): an agent stack that needs CDP (Puppeteer, Playwright, browser-use) would need either a CDP-to-WebDriver shim or a WebDriver-classic driver. Classic WebDriver has no network interception and no event streaming. Those features are the reason BiDi and CDP exist.
- Unverified third-party claims I saw in search results (not quoted from a primary source): one WebDriver session per process, and memory growth over long single-window runs (servo-reader project, Servo 0.7.0).

## WPT pass rates
Source: [wpt.fyi API](https://wpt.fyi/api/runs?label=master&label=experimental&product=servo&max-count=1), latest experimental runs, all started 2026-11-08. Builds: Chrome 159.0.8150.0, Firefox 162.0a1, Safari Technology Preview 256, Servo 0.8.0-caee2c181, Ladybird 1.0-5e4800fe4ed.

Metric: passing subtests ÷ all subtests, summed over each directory. I computed this myself from wpt.fyi's per-test summary files. It is not wpt.fyi's per-test-normalized score, so absolute numbers differ from the dashboard; the comparison between engines is the useful part. Caveat: each engine ran on a different WPT commit (the runs are not aligned), so treat gaps of about 1 point as noise.

Order in every row: Chrome / Firefox / Safari / Ladybird / Servo.
- all: 97.7 / 95.9 / 95.5 / 96.5 / 90.6
- dom: 99.8 / 98.4 / 98.3 / 98.5 / 98.0
- html: 97.6 / 94.7 / 94.8 / 95.0 / 85.7
- html parsing (`html/syntax`): 99.3 / 96.2 / 96.6 / 96.1 / 95.0
- forms (`html/semantics/forms`): 98.8 / 93.3 / 90.8 / 93.7 / 88.9
- fetch: 94.2 / 92.7 / 88.4 / 89.7 / 85.7
- cookies: 97.7 / 93.8 / 80.8 / 96.4 / 85.3
- css (all): 95.5 / 87.6 / 92.6 / 90.2 / 55.6
- css flexbox: 99.5 / 96.7 / 96.5 / 93.2 / 68.7
- css grid: 99.5 / 95.2 / 95.8 / 94.0 / 65.3
- webdriver classic: 96.7 / 97.7 / 82.6 / 89.6 / 86.5
- webdriver bidi: 96.3 / 88.0 / 0.0 / 59.8 / 0.0

Servo's own dashboard ([servo.org/wpt](https://servo.org/wpt/)) loads its numbers with JavaScript, so my fetch could not read them. The page defines its scores as "percentages of total enabled tests within the suite that pass".

## Takeaways
- For DOM, HTML parsing, and forms, Servo is close to other engines. This matters most for agents that read the DOM or accessibility data.
- Weak CSS layout means screenshots, and coordinates computed from layout, will often be wrong on real sites. That matters for vision-based agents.
- The automation path today is WebDriver classic only. Using Servo with standard agent tooling would need new protocol work, either CDP or BiDi.
