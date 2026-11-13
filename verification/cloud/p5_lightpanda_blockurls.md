# p5_lightpanda_blockurls — does Lightpanda `--block-urls` block WebSocket, redirects, fetch/XHR?

(authored by agents)

## Answer

`--block-urls` blocks fetch, XHR, every redirect I tried, document navigations, iframes and scripts. It does **not** block WebSocket connections.

- **Fetch and XHR:** blocked (observed). The blocked origin's server received zero requests.
- **Redirects:** blocked (observed). Covers 301/302/307/308 used by fetch, XHR, the top-level document, iframes and `<script>`, plus meta-refresh and `location.href` navigations. The check runs again on every redirect hop.
- **WebSocket:** not blocked (observed). The upgrade reached the blocked server, the handshake completed (101), and page JS got the server's message. This held for every pattern I tried, including one aimed at `ws://` URLs (`ws://127.0.0.1:8002/*`). The same bypass happens with CDP `Network.setBlockedURLs` and with `--adblock-lists`.
- **Why (from source):** `new WebSocket()` opens its own libcurl connection and registers it with the HTTP client directly. It never enters the request pipeline, which is the only place the URL blocklist and adblock filters are checked.
- **What does work for WebSocket:** IP-level blocking (`--block-cidrs`, and by the same mechanism `--block-private-networks`). It is installed on every curl connection, WebSocket ones included. Observed: the WebSocket to `127.0.0.2:8003` failed and the server got nothing.

No upstream report was filed, as instructed.

## Setup (facts)

- Binary: `https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux`, downloaded 2026-11-04.
  - sha256 `e7ed89bddaadf3da70d2e6092b498181d66a45fcd07353302c0c2724f668e16e`
  - `lightpanda version` printed `1.1.0-nightly.11647+b8e234a77`
- Source: `git clone https://github.com/lightpanda-io/browser`, checked out at `b8e234a77259283ff2653d5cc5900249d1d2cea9` ("Merge pull request #4436 from lightpanda-io/orderfile-regen", 2026-11-04). This is the commit embedded in the binary's version string. Every line number below refers to it.
- Servers: `tools/srv.py`, a raw-socket Python HTTP+WebSocket server that logs every request line and completes RFC 6455 handshakes. Three instances:
  - `127.0.0.1:8001`: allowed origin. Serves the probe pages and `/redir?code=N&to=URL`.
  - `127.0.0.1:8002`: the blocked origin.
  - `127.0.0.2:8003`: blocked origin for the CIDR test.
- Probe page: `www/probe.html`, loaded from 8001. It calls:
  - fetch and XHR, directly to 8002
  - fetch and XHR through `8001/redir` with 301/302/307/308 to 8002
  - `new WebSocket(...)` with `ws://127.0.0.1:8002/ws_direct`, with `http://127.0.0.1:8002/ws_http_scheme` (spec maps http→ws), and with an upper-case path
  - one allowed control fetch to 8001
- Other pages: `subres.html` (scripts, imgs and iframes, direct and via redirect), `meta.html` (meta refresh), `nav2.html` (sync `location.href`).
- The harness is in `/tmp/claude-0/-home-user/4bdcf092-6cae-540a-b27e-17319deea21c/scratchpad/{tools,www}`.

How to read the WebSocket result strings: `open message:hello-from-8002 error close:1006` means the connection opened, the blocked server's message arrived, and then my server dropped TCP without a close frame. The `error` and `close:1006` come from that drop, not from blocking.

## Experiments (commands and outputs, verbatim, trimmed only where marked)

### E0: baseline, no blocking

```
$ lightpanda fetch --wait-until done --wait-ms 20000 --dump-selector "#out" --dump html http://127.0.0.1:8001/probe.html
 "fetch_direct": "ok status=200 url=http://127.0.0.1:8002/fetch_direct body=secret-from-8002/fetch_direct",
 "xhr_direct": "load status=200 url=http://127.0.0.1:8002/xhr_direct body=secret-from-8002/xhr_direct",
 "fetch_redir_302": "ok status=200 url=http://127.0.0.1:8002/fetch_redir_302 body=secret-from-8002/fetch_redir_302",
 [... all redirect cases likewise ok ...]
 "ws_direct": "open message:hello-from-8002 error close:1006 (timeout)",
```

The 8002 log shows every request, including `GET /ws_direct upgrade=True` and `ws handshake completed (101 sent)`. This shows the harness reaches 8002 for every kind of request.

### E1: `--block-urls '*127.0.0.1:8002*'` (scheme-agnostic pattern)

```
$ lightpanda fetch --block-urls '*127.0.0.1:8002*' --wait-until done --wait-ms 20000 --dump-selector '#out' --dump html http://127.0.0.1:8001/probe.html
 "fetch_direct": "threw TypeError: fetch error",
 "xhr_direct": "error status=0",
 "fetch_redir_301": "threw TypeError: fetch error",
 "xhr_redir_301": "error status=0",
 "fetch_redir_302": "threw TypeError: fetch error",
 "xhr_redir_302": "error status=0",
 "fetch_redir_307": "threw TypeError: fetch error",
 "xhr_redir_307": "error status=0",
 "fetch_redir_308": "threw TypeError: fetch error",
 "xhr_redir_308": "error status=0",
 "ws_direct": "open message:hello-from-8002 error close:1006",
 "ws_http_scheme": "open message:hello-from-8002 error close:1006",
 "ws_upper_case_host": "open message:hello-from-8002 error close:1006",
 "fetch_control_allowed": "ok status=200 url=http://127.0.0.1:8001/control body=secret-from-8001/control",
--- 8002 server log
[8002 06:33:44] GET /ws_direct upgrade=True origin=http://127.0.0.1:8001
[8002 06:33:44] ws handshake completed (101 sent)
[8002 06:33:45] GET /ws_http_scheme upgrade=True origin=http://127.0.0.1:8001
[8002 06:33:45] ws handshake completed (101 sent)
[8002 06:33:46] GET /WS_UPPER upgrade=True origin=http://127.0.0.1:8001
[8002 06:33:46] ws handshake completed (101 sent)
```

With `--log-level info`, Lightpanda's own log shows the redirect target being blocked: the second hop is checked, not the first URL.

```
$scope=http $level=info $msg="blocked url" url=http://127.0.0.1:8002/fetch_redir_301
$scope=http $level=info $msg="request error" $page=1 source=fetch url="http://127.0.0.1:8001/redir?code=301&to=http%3A%2F%2F127.0.0.1%3A8002%2Ffetch_redir_301" status=0 err=UrlBlocked
```

For WebSocket it logs a successful connection instead:

```
$scope=websocket $level=info $msg="connected" url=ws://127.0.0.1:8002/ws_direct
$scope=websocket $level=info $msg="disconnected" $page=1 url=ws://127.0.0.1:8002/ws_direct reason=closed
```

### E2: `--block-urls 'http://127.0.0.1:8002/*'`

Same output as E1: HTTP blocked, all three WebSockets connected and the server logged their handshakes.

### E3: `--block-urls 'ws://127.0.0.1:8002/*'` (pattern written for the WS URL)

All fetch and XHR cases succeed, which is expected because the pattern does not match `http://` URLs. All three WebSockets still connect, and the 8002 log shows `GET /ws_direct upgrade=True` and `ws handshake completed (101 sent)`. So pattern choice is not the cause: WebSocket URLs are never checked.

### E4: document navigations and subresources

```
$ lightpanda fetch --log-level info --block-urls '*127.0.0.1:8002*' --json --dump html "http://127.0.0.1:8001/redir?code=302&to=http%3A%2F%2F127.0.0.1%3A8002%2Fdoc_redir"
exit=1
{"url":"http://127.0.0.1:8001/redir?code=302&to=...doc_redir","http_status":0,...,"content":"...<h1>Navigation failed</h1><p>Reason: UrlBlocked</p>...","error":"UrlBlocked",...}
$scope=http $level=info $msg="blocked url" url=http://127.0.0.1:8002/doc_redir
```

- Direct navigation to `http://127.0.0.1:8002/doc_direct`: `"error":"UrlBlocked"`, exit 1.
- `meta.html` (meta refresh to 8002) and `nav2.html` (sync `location.href=` to 8002): both end with `"error":"UrlBlocked"` and `msg="blocked url" $page=2 url=http://127.0.0.1:8002/...`.
- `subres.html` with `--load-resources iframe --with-frames`: direct and redirected scripts and iframes all log `blocked url`. Each iframe shows `Navigation failed ... Reason: UrlBlocked`.
- The 8002 log stayed empty for every run in E4.
- Not evidence about blocking:
  - images: Lightpanda does not load them by default (`page_status.skipped.image`)
  - iframes: skipped unless `--load-resources iframe` is given (`"resource skipped" ... resource=iframe hint="enable via --load-resources iframe"`)
  - `nav.html` (`location.href` inside `setTimeout`): `fetch` exited after `"schedule navigation"` without running the navigation, so it is inconclusive

### E5: CDP `serve` mode

```
$ lightpanda serve --host 127.0.0.1 --port 9222 --block-urls '*127.0.0.1:8002*' &  ;  node tools/cdp_probe.mjs ws://127.0.0.1:9222/ http://127.0.0.1:8001/probe.html
event Network.loadingFailed {"requestId":"REQ-0000000002","timestamp":343,"type":"Ping","errorText":"UrlBlocked","canceled":false,"blockedReason":"inspector"}
[... one per blocked fetch/XHR ...]
 "ws_direct": "open message:hello-from-8002 error close:1006",
--- 8002 server log
[8002 06:35:35] GET /ws_direct upgrade=True origin=http://127.0.0.1:8001
[8002 06:35:35] ws handshake completed (101 sent)
```

- With no CLI flag, using `Network.setBlockedURLs {"urlPatterns":[{"urlPattern":"*127.0.0.1:8002*","block":true}]}` gives the same split: HTTP blocked, WebSocket connected, 8002 logged three handshakes.
- Side observation 1 (fact): the legacy form `{"urls":[...]}` is rejected with `{"code":-31998,"message":"MissingField"}`. Only `urlPatterns` is accepted (see S6).
- Side observation 2 (fact): fetch and XHR failures are reported with `"type":"Ping"`. My belief, not checked: that resource-type label is wrong.

### E6: `--adblock-lists` with a plain filter list (`fetch_direct`, `ws_direct`)

```
 "fetch_direct": "threw TypeError: fetch error",
 "ws_direct": "open message:hello-from-8002 error close:1006",
$scope=http $level=info $msg="blocked url" $page=1 url=http://127.0.0.1:8002/fetch_direct
--- 8002 log
[8002 06:36:11] GET /ws_direct upgrade=True origin=http://127.0.0.1:8001
```

### E7: IP-level blocking catches WebSocket

```
$ lightpanda fetch --log-level info --block-cidrs 127.0.0.2/32 --wait-until done --wait-ms 20000 --dump-selector '#out' --dump html http://127.0.0.1:8001/probe_cidr.html
 "fetch_direct": "threw TypeError: fetch error",
 [... all redirect cases fail ...]
 "ws_direct": "error close:1006",
 "ws_http_scheme": "error close:1006",
 "ws_upper_case_host": "error close:1006",
 "fetch_control_allowed": "ok status=200 ...",
--- 8003 server log
(empty)
```

`probe_cidr.html` is `probe.html` with the target changed to `127.0.0.2:8003`.

## Source explanation (quotes from commit b8e234a7)

S1. The blocklist is checked in one place, a stage of `HttpClient.pipeline`. `src/network/HttpClient.zig:1115-1118`:

```zig
        .after_intercept => {
            if (self.isUrlBlocked(transfer)) {
                log.info(.http, "blocked url", .{ .url = transfer.req.url });
                return transfer.failAsync(error.UrlBlocked);
```

S2. That one check covers both `--block-urls` and adblock, and it is keyed on the request URL. `HttpClient.zig:435-443`:

```zig
/// Every reason a request is refused before it reaches the network:
/// `--block-urls` patterns and the `--adblock-lists` filters both land here
/// so that no call site can apply one without the other.
fn isUrlBlocked(self: *const Client, transfer: *const Transfer) bool {
    const req = &transfer.req;
    if (req.internal) return false;
    if (self.url_blocklist) |*blocklist| {
        if (blocklist.isBlocked(req.url)) return true;
    }
```

S3. Why redirects are blocked: libcurl auto-follow is off for page transfers, and each 3xx re-enters the full pipeline with the new URL.

- `HttpClient.zig:3836`: `try conn.setFollowLocation(false);`
- `HttpClient.zig:2048-2057`:

```zig
// Follow a materialized redirect response: point the transfer at the
// redirect target and restart the whole pipeline (.redirect == .start),
// rechecking the cache/robot/ratelimit/...
fn followRedirect(self: *Client, transfer: *Transfer, location: []const u8) !void {
    try transfer.handleRedirect(location);
    ...
    try self.pipeline(transfer, .redirect);
}
```

S4. Why WebSocket is not blocked: `WebSocket.connect` builds a curl handle itself and calls `trackConn`. It never creates a `Transfer` and never calls `pipeline`, so neither `isUrlBlocked` nor `blocksUrl` is reached. Its only pre-connect check is the port blocklist. `src/browser/webapi/net/WebSocket.zig:235-296` (excerpt):

```zig
fn connect(self: *WebSocket, protocols: []const []const u8) !void {
    ...
    if (isBlockedPort(resolved_url)) {
        return error.BlockedPort;
    }

    const conn = http_client.network.newConnection() orelse {
        return error.NoFreeConnection;
    };
    ...
    try conn.setURL(resolved_url);
    ...
    conn.transport = .{ .websocket = self };
    try http_client.trackConn(conn);
```

Fact: `grep -rn "blocksUrl\|isUrlBlocked\|url_blocklist" src` outside `HttpClient.zig`/`UrlBlocklist.zig` finds only `src/browser/tools/search.zig`. Nothing under `webapi/net/WebSocket.zig` matches.

S5. Why `--block-cidrs` does catch WebSocket: the IP filter is a curl opensocket callback that `http.Connection.init` installs on every connection. `Network.newConnection`, the call WebSocket uses, passes it in: `src/network/Network.zig:221`: `conn.* = http.Connection.init(self.certificates, self.config, self.ip_filter) catch {`.

- `src/network/http.zig:234-235`:

```zig
/// Opensocket callback: blocks connections to private/internal IP ranges
/// before TCP SYN, regardless of request origin (JS, HTML resources, redirects, etc.).
```

- `http.zig:548-551`:

```zig
        // IP filter: block private/internal network addresses
        if (ip_filter) |filter| {
            try libcurl.curl_easy_setopt(self._easy, .opensocket_function, opensocketCallback);
```

S6. CDP `Network.setBlockedURLs` uses the same list, so it inherits the gap. It takes only `urlPatterns`. `src/server/cdp/domains/network.zig:227-233`:

```zig
fn setBlockedURLs(cmd: *CDP.Command) !void {
    const params = (try cmd.params(struct {
        urlPatterns: []const HttpClient.BlockPattern,
    })) orelse return error.InvalidParams;
    ...
    try bc.cdp.browser.http_client.setBlockedUrlPatterns(params.urlPatterns);
```

S7. How patterns match. Help text (`lightpanda help fetch`): "Patterns are matched case-insensitively against the full URL and '*' is a wildcard." `src/network/UrlBlocklist.zig` lowercases each pattern once and compares it to each lowercased URL character, with `*` backtracking. Patterns match the full URL including the scheme, so `http://host/*` cannot match `ws://host/...` even in principle. By S4 that does not matter: WebSocket URLs are never checked.

## Interpretation (beliefs and inferences, not tested)

- Inference: an agent harness using `--block-urls` or `Network.setBlockedURLs` as an egress allow/deny boundary is bypassable. Any page script can open `new WebSocket("ws(s)://blocked-host/...")` and send or receive data. E1–E3 show both directions (the upgrade request goes out with `Origin`, the message comes back).
- Belief: the gap is an omission, not a design choice. Evidence: S2's comment says "no call site can apply one without the other", and S5's comment presents the IP filter as covering every request origin. Neither comment mentions WebSocket.
- Mitigation that works today (fact, E7): `--block-cidrs` / `--block-private-networks`. These filter by resolved IP, so they cannot express "block this hostname on a shared CDN".
- Untested, likely affected by S4 (belief): `wss://`, WebSocket from Workers (`net/websocket_worker.html` exists in tests), and a WebSocket upgrade that receives a 3xx.
- For the Verus/verification agenda (opinion): this is a compact, checkable property. "Every outbound connection is preceded by `isUrlBlocked(url) == false`" could be stated as a spec over the connection-creating API (`Network.newConnection`/`trackConn`). The bug is exactly a second path to that API that skips the guard.

## Limitations

- Loopback only and plain HTTP/WS; no TLS.
- One nightly build, one x86_64 Linux machine.
- The WS server closes TCP after 1 s without a close frame, which explains the `error close:1006` events.
