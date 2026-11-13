# Review: lightpanda_blockurls_websocket.md
(authored by agent)

Verdict: FIX FIRST (minor). Core claim reproduced; no overstatement of substance.

## Re-run (own dir, draft text only; srv.py copied from cx_bugs, probe.html pasted from draft)
Binary vlm_runtime/lightpanda/bin/lightpanda: version 1.1.0-nightly.11647+b8e234a77, sha256 e7ed89bd... matches draft.
- baseline: {"fetch":"secret-from-18003/f","ws":"hello-from-18003"}  OK
- --block-urls '*127.0.0.2:18003*': {"fetch":"blocked","ws":"hello-from-18003"}; 18003 log shows "GET /ws upgrade=True origin=http://127.0.0.1:18001" + "ws handshake completed (101 sent)". OK
- --block-urls 'ws://127.0.0.2:18003/*': fetch passes, ws passes. OK
- --block-cidrs 127.0.0.2/32: {"fetch":"blocked","ws":"error"}. OK
- --adblock-lists (file containing `127.0.0.2:18003`): fetch blocked, ws data. OK
- CDP setBlockedURLs: not rerun by me; relies on cx_bugs/lightpanda/cdp.log (prior reviewer ran it). 
- --block-private-networks: I ran it; page itself (127.0.0.1) is blocked -> SelectorNotFound, uninformative. Draft correctly says not executed.
Source quotes (HttpClient.zig isUrlBlocked/after_intercept, WebSocket.zig isBlockedPort->newConnection->setURL->trackConn) verified at b8e234a77.

## Duplicates
gh search (issues+PRs, all states): "websocket block", "block-urls", "setBlockedURLs", "websocket bypass", "adblock websocket": no existing report. Related only: PR #3004 (closed, original block-urls), #3116 (adblocker, merged), #1971 (ip filter, closed). Upstream main now 6c7ed668 (2026-11-04); its WebSocket.zig still only has isBlockedPort -> newConnection (no blocklist check). Draft pinned to b8e234a77.

## Findings
1. [MED] Channel: SECURITY.md says verbatim "Please **DO NOT** file a public issue, instead send your report privately to security@lightpanda.io." Draft handles this correctly but is written as a public issue (Title/Version/Expected/Actual). Repo has GitHub private advisories enabled (security-advisories API responds; GHSA exists), so private route exists. Recommend: human decides; if treated as security, send same text to security@; otherwise default to public. Low severity (needs attacker page JS plus operator relying on block-urls as boundary); a public issue is defensible but the call is the human's.
2. [LOW] Template: confirmed none (.github has only actions/, workflows/; no ISSUE_TEMPLATE, no root template). Draft claim correct.
3. [LOW] Version staleness: tested on b8e234a77, main is newer. Before filing, say "still present on main 6c7ed66 by source inspection" or rebuild and rerun. Source-check on main only grep-level by me.
4. [LOW] srv.py comment says usage `<port> <docroot>` but draft passes a 3rd host arg (works; code reads argv[3]). Draft says "62 lines; paste inline" - a 62-line paste into an issue is heavy; and "Local copy: /hdd1/..." is a local path that leaks into the issue body if copied. Strip it. Also `python3 -I srv.py` with `$PWD/www` fine.
5. [LOW] Repro needs 127.0.0.2 loopback (Linux only; macOS lacks it). State this.
6. [LOW] "Impact" says "application data comes back": true only for server-sent frame (observed). Draft already notes send not tested. Acceptable. "Anyone using ... can be bypassed" -> fine but phrase "page JS" is correct.
7. [LOW] "Evidence trail" section marked not for issue body; ensure it is removed (internal paths, REVIEW.md refs, mentions of prior agent review) before filing.
8. [INFO] "Likely cause" line numbers are "around"; fine. Say lines refer to b8e234a77.
9. [INFO] Tone: neutral, no embarrassing claims; "Whether this is intended behavior" unknown is honest. Adblock claim: CDP/adblock items are "confirmed" by prior reviewer; I reproduced adblock myself, not CDP.

## Must-do before filing
Choose channel (finding 1); remove local paths + Evidence trail + "DRAFT/Status" header; optionally rerun on current main.
