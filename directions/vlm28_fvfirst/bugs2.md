# bug citation verification (fetched via WebFetch, 2026-11-09)
(authored by agents unless marked 🧑)

1. pingora issue 910 (h2 RST_STREAM zombie streams)
exists: yes
year: 2026 (opened Jun 13 2026, closed Aug 25 2026 "Fixed with b79ce4f")
key sentences:
- "a downstream `RST_STREAM` is not acknowledged by pingora if it arrives while the proxy is blocked writing the request body to the upstream"
- "Each such stream becomes a "zombie": closed at the protocol level, but still pinning its share of the shared downstream connection window."
- "the RST_STREAM frees the stream slot (max_concurrent_streams) but not the window credit."
title (verbatim): "H2→H2 proxy: downstream RST_STREAM is not observed while the upstream request-body write is blocked, pinning connection-window credit indefinitely"

2. quinn GHSA-hmxj-32vh-65vr (unbounded retire_cids)
exists: yes
year: 2026 (dated Aug 17 2026)
key sentences:
- "There are **two** code paths that push into this queue, and only **one** of them is bounded"
- "The 'this CID was already retired' path (`Err(InsertError::Retired)`) pushes **`frame.sequence` with no cap and no de-duplication**."
- "A peer that has completed the QUIC handshake can drive the second path arbitrarily many times, growing `pending.retire_cids` without bound."
title (verbatim): "quinn-proto: unbounded pending.retire_cids growth via already-retired NEW_CONNECTION_ID frames (remote memory-exhaustion DoS)"
notes: affects quinn-proto <= 0.11.16, fixed in 0.11.17, severity Moderate (CWE-770), no CVE listed. PoC reached 505 entries vs 50 cap on the other path (reporter's claim).

3. CVE-2025-30355 (Matrix Synapse state resolution)
exists: NOT VERIFIED
reason: NVD fetch returned only the NVD homepage ("NVD - Home"), no CVE entry. No year, no description, no "exploited in the wild" text confirmed.
next step: retry NVD via API (services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2025-30355) or check CISA KEV catalog.

4. servo/ipc-channel lost messages or fd exhaustion
exists: yes (issue titles only, no bodies fetched)
candidates:
- #450 (2026): "try_recv_timeout loses messages on Windows". Message loss, Windows only.
- #281 (2021): "IpcReceiver hang, forking leaks file descriptors, problem/discussion". fd leak on fork.
- #461 (2026): "Windows: receiver leaks one handle per received shm region / channel end". Windows handles, not Unix fds.
- #395 (2025): "Panic when sending more than 64 file descriptors on unix systems". Fd-passing limit, not exhaustion.
no exact match for "lost messages on Unix" or "fd exhaustion from the library".

5. curl CVE-2022-27774 (credential leak on redirect)
exists: yes
year: 2022 (advisory dated Apr 27 2022)
key sentences:
- "This "same host check" has been flawed all since it was introduced."
- "It does not work on cross protocol redirects and it does not consider different port numbers to be separate hosts."
- "This leads to curl leaking credentials to other servers when it follows redirects from auth protected HTTP(S) URLs…"
notes: affected 4.9 through 7.82.0, fixed in 7.83.0, severity Medium, reporter Harry Sintonen.

6. mozilla bugzilla 1619047 (Let's Encrypt CAA rechecking)
exists: yes
year: 2020 (incident 2020-02-29 UTC)
status: RESOLVED FIXED
key sentences:
- "On 2020-02-29 UTC, Let's Encrypt found a bug in our CAA code."
- "when a certificate request contained N domain names that needed CAA rechecking, Boulder would pick one domain name and check it N times."
- "We confirmed the bug at 2020-02-29 03:08 UTC, and halted issuance at 03:10."
notes: loop-variable reference bug in Go, about 3,048,289 valid certs affected, fixed 05:22 UTC same day. Related bug 1619179 covers incomplete revocation.
