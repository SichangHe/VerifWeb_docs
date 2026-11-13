# Lightpanda maintainer triage
(authored by agents unless marked 🧑)

Judgment: **needs more info as submitted; likely a real blocking-policy bug once the missing reproducer is supplied**. This is my triage assessment, not a maintainer response. I found no basis in the inspected help/source to close it as intended behavior. I did not reproduce the network result.

## Fresh-directory execution

Reviewed only [the draft](../vlm4_drafts/lightpanda_blockurls_websocket.md). In the fresh directory `out/cx_maint/lightpanda`, I ran its first server command, bounded by `timeout 10s`:

```sh
python3 -I srv.py 18001 "$PWD/www" 127.0.0.1
```

Python exited 2:

```text
python3: can't open file '/hdd1/sichangheagent/vl_meeting_work/out/cx_maint/lightpanda/srv.py': [Errno 2] No such file or directory
```

The draft says “Attach as `srv.py` (62 lines)” but includes neither the script nor an attachment/link. The drafts directory contains no `srv.py`. Reimplementing the described server would test a new harness, not reproduction from the draft alone. Also, `command -v lightpanda` found no installed binary; the draft provides an identity/checksum but no acquisition command. No browser execution, CDP session, adblock test, or current-main build was performed.

## Current upstream source check

Cloned `https://github.com/lightpanda-io/browser.git` into `lightpanda/upstream`. Its checked-out `main` is `d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0`, dated `2026-11-04 15:10:27 +0100`, subject “Merge pull request #4446 from lightpanda-io/completion-followups”. This is newer than the draft's `6c7ed668` source check.

- [WebSocket.connect, current main](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/browser/webapi/net/WebSocket.zig#L235): the function contains `if (isBlockedPort(resolved_url))`, followed by `http_client.network.newConnection()`, `try conn.setURL(resolved_url);`, and `try http_client.trackConn(conn);`. The complete function has no URL/adblock check or `Transfer` construction.
- [HttpClient.isUrlBlocked](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/network/HttpClient.zig#L434) says: “Every reason a request is refused before it reaches the network: `--block-urls` patterns and the `--adblock-lists` filters both land here so that no call site can apply one without the other.” It checks the URL blocklist and adblocker. The HTTP pipeline calls it in `.after_intercept` at line 1132; `trackConn` at line 2101 adds the connection to curl's handles without doing this check.
- [Current CLI help](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/help.zon#L435) says adblock requests “are failed before they leave”; URL blocking says “Patterns are matched case-insensitively against the full URL and '*' is a wildcard.” These statements support the reported expectation, though they do not explicitly name WebSocket.
- [CDP handler](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/server/cdp/domains/network.zig#L230) takes `urlPatterns: []const HttpClient.BlockPattern` and calls `setBlockedUrlPatterns(params.urlPatterns)`. The [upstream test](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/server/cdp/domains/network.zig#L1327) supplies `.{ .urlPattern = "*://blocked.test/*", .block = true }`. The shared blocklist supports the draft's proposed common cause; it does not independently verify its earlier CDP execution.
- [Connection reset](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/network/http.zig#L547) installs `.opensocket_function, opensocketCallback` when `ip_filter` exists. [Network.newConnection](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/network/Network.zig#L206) passes `self.ip_filter` into connection initialization. This supports the claimed CIDR explanation, source-only.

Inference: the claimed bypass remains plausible on current main because WebSocket bypasses the specific stage implementing both URL blocking and adblock. Source inspection cannot establish the exact HTML output, successful handshake, or event timing asserted in the draft.

## Concrete draft changes, in priority order

1. **Supply the missing server.** Replace “Attach as `srv.py` (62 lines)” with the complete script or an actual attached file. Include commands creating `www/probe.html`, acquiring the tested binary, checking its version/checksum, starting both servers with log redirection and readiness checks, and stopping them. The server must make the cross-origin fetch readable in the unblocked control (for example, return a suitable `Access-Control-Allow-Origin` header); this cannot be checked from the prose description.
2. **Provide runnable variants or narrow the title.** The title includes “`Network.setBlockedURLs` / `--adblock-lists`”, but neither has runnable steps. For CDP, provide launch/attach/navigation steps and exact JSON, including `"urlPatterns":[{"urlPattern":"*127.0.0.2:18003*","block":true}]`, and record successful command acknowledgment. For adblock, supply the filter file bytes and full command. Otherwise title the report “`--block-urls` does not block WebSocket connections” and retain the others explicitly as earlier observations lacking a supplied reproducer.
3. **Match the summary to supplied evidence.** “A URL matched by `--block-urls` is refused for fetch and XHR” exceeds the displayed probe, which has fetch and WebSocket only. Remove “and XHR” or add its probe/output. The current broad title and summary make three mechanisms plus XHR appear independently reproducible when only one incomplete CLI example is provided.
4. **Distinguish rejection from any fetch error.** `catch(e){r.fetch='blocked'}` labels all failures as policy blocking, including CORS/network errors. Record the exception and include browser “blocked url” logs plus the destination-server log. Keep the already-described no-block control, with its actual command and raw output; it is needed to establish that cross-origin fetch works with this server.
5. **Update the main-branch evidence precisely.** Replace the old upstream bullet with: “Source inspected at current main `d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0` (2026-11-04): `WebSocket.connect` bypasses the HTTP pipeline's URL/adblock check; current main was not built or executed.” Link the functions above. Keep the tested binary identity separate.
6. **Avoid promising one exact error event.** “Both requests … are blocked: `{"fetch":"blocked","ws":"error"}`” unnecessarily requires an asynchronous WebSocket error rather than a constructor exception. State the essential expectation: “No request reaches the blocked server; the WebSocket cannot open or receive application data.” Record synchronous exceptions and timeout explicitly in the probe instead of leaving `ws` absent after the timer.
7. **Preserve limited impact and route.** Keep “`WebSocket.send` with an application payload was not tested” and other stated limits. The [upstream security policy](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/SECURITY.md#L9) says “Please **DO NOT** file a public issue, instead send your report privately to security@lightpanda.io.” Its private-report instruction is correctly quoted in the draft. No filing or contact occurred during this review.

The minimum acceptance improvement is the complete server plus one current runnable CLI control/blocked pair and their logs. The additional mechanisms can remain secondary until their exact reproduction steps are supplied.
