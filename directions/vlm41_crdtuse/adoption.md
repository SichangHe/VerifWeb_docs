# Who actually uses Rust CRDT/sync code in widely used products

(authored by agents unless marked 🧑)

Conventions: [F] fact (quoted, sourced), [I] inference, [O] opinion, [?] I don't know. All web use was read-only. Numbers fetched 2026-11-10 from crates.io API, npm downloads API (last 30 days: 2026-10-11..2026-11-09), pypistats (last month). Quotes are verbatim; "(2026)" etc. is the year of the source or of the data fetch.

## 1. Takeaway

- [I] Widest-used products with a CRDT: Yjs-based (Tiptap, Gitbook, Evernote, Proton Docs, Linear, JupyterLab...). That code is JavaScript, not Rust.
- [I] Rust CRDT code that really runs in a known product: (a) Yrs in AppFlowy, (b) Yrs through pycrdt in JupyterLab real-time collaboration, (c) y-octo (a Rust Yjs-compatible engine, not Yrs) in AFFiNE, (d) Automerge's Rust core via WASM in every npm Automerge app, (e) Loro's Rust core via WASM/native in Loro apps.
- [I] Strongest Rust-and-widely-used candidate: JupyterLab/Jupyter (Yrs via pycrdt), then AFFiNE and AppFlowy (both large open-source Rust+TS apps with real user bug reports). Automerge and Loro have named users but all small or unclear; Loro's flagship named user (marimo) just removed Loro (see 3.3).
- [?] I could not verify scale (active users) of any of these products. The number of products using each library is small relative to Yjs-in-JS.

## 2. Which part is Rust, which is JS

### Automerge
- [F] Rust core compiled to WASM, JS wrapper. automerge README (2026): "This repository also contains the core Rust library which is compiled to WebAssembly and exposed in JavaScript" and "This project is formed of a core Rust implementation which is exposed via FFI in javascript+WASM, C, and soon other languages." https://github.com/automerge/automerge
- [F] npm package: "Javascript implementation of automerge, backed by @automerge/automerge-wasm" (package.json description of @automerge/automerge 3.5.0, 2026; it ships dist/automerge.wasm). https://github.com/automerge/automerge/blob/main/javascript/package.json
- [I] So every JS Automerge app runs the Rust code in a WASM sandbox. The sync protocol and merge logic are Rust; automerge-repo (networking/storage, 174k npm dl/month) is TypeScript.
- [F] Rust-native users: crates `samod`, `automerge_repo`, `autosurgeon`, `ethersync`, `peermerge` (crates.io reverse deps, 2026). I do not know of a widely used product among them.

### Loro
- [F] README (2026): "You can now use it in Rust, JS (via WASM), and Swift." https://github.com/loro-dev/loro
- [F] npm `loro-crdt` 1.17.1 has `"main": "nodejs/index.js"`, `"module": "bundler/index.js"` and no dependencies (registry.npmjs.org/loro-crdt/latest, 2026). [I] This is the WASM build of the Rust crate (consistent with README; I did not inspect the .wasm file).
- [F] Python `loro` package is a native extension: marimo PR #11625 (2026): "it makes Loro, a native extension, a dependency of every client and server." https://github.com/marimo-team/marimo/pull/11625

### Yjs / Yrs / y-octo
- [F] Yjs is pure JavaScript (npm yjs 13.6.33, description "Shared Editing Library", sole dep lib0). [I] The Yjs README has no sentence "written in JS", but the package is JS.
- [F] Yrs is Rust: y-crdt README (2026): "**yrs** (read: _wires_) is a core Rust library, a foundation stone for other projects." and "**ywasm** is a wrapper around _yrs_ that targets WebAssembly and JavaScript API." and "to maintain behavior and binary protocol compatibility with Yjs". https://github.com/y-crdt/y-crdt
- [F] Bindings built on Yrs: "pycrdt - Python bindings.", "yrb - Ruby bindings.", "ydotnet - .NET/C# bindings.", "yswift - Swift bindings.", "ykt - Kotlin bindings." (same README).
- [F] Servers: Tiptap's Hocuspocus is a Node (Yjs) server; Yrs servers include yrs-warp and Jamsocket's y-sweet (Rust). Yjs README (2026) lists "y-sweet, ypy-websocket, yrs-warp and Hocuspocus" as alternative backends. https://github.com/yjs/yjs
- [F] y-octo is a separate Rust implementation, not Yrs: AFFiNE README (2026): "y-octo is a native, high-performance, thread-safe YJS CRDT implementation, serving as the core engine enabling the AFFiNE Client/Server to achieve "local-first" functionality." https://github.com/toeverything/AFFiNE ; same README also: "yjs - Fundamental support of CRDTs for our implementation on state management and data sync on web." [I] So AFFiNE uses both: Yjs JS in the web client, Rust y-octo elsewhere. AFFiNE Cargo.toml has `y-octo = "0.1.1"`.

### diamond-types
- [F] crates.io: diamond-types 55,401 total / 25,360 recent downloads, 1 reverse dependency (`codemp`, 855 dl) (2026). [I] It is not used by any known widely used product. [?] I did not search for npm/WASM users beyond `diamond-types-node` (504 npm dl/month).

## 3. Who uses what (named products)

### 3.1 Download counts (2026-11-10)
- [F] crates.io: yrs 4,744,697 total / 2,373,262 recent (84 reverse deps); loro 1,152,056 / 670,110 (29 reverse deps); automerge 834,509 / 340,143 (43 reverse deps); diamond-types 55,401 / 25,360 (1); y-octo 73,894 / 36,368.
- [I] Caveat: part of yrs counts are from its own workspace crates (top reverse dep `yrs-kvstore` 1.2M); crates.io downloads include CI and mirrors. `loro-crdt` is not a crate name (the crate is `loro`).
- [F] npm last 30 days: yjs 52,977,710; y-prosemirror 11,256,436; @tiptap/extension-collaboration 14,739,161; @hocuspocus/server 6,293,819; y-websocket 4,655,906; loro-crdt 811,540; @automerge/automerge 370,089; @automerge/automerge-repo 174,101; yrs (npm, unrelated name) 1,115.
- [F] PyPI last month: pycrdt 2,381,662; jupyter-server-ydoc 815,532; pycrdt-websocket 622,256; jupyter-collaboration 177,449; loro 2,504,763; y-py 713,064; automerge 11,085.
- [I] Yjs (JS) is about 100x the Automerge and Loro npm counts. Rust-backed code reached by PyPI (pycrdt, loro) is in the millions per month. [?] Why PyPI `loro` is 2.5M/month I don't know (CI? agent tools? marimo?) — do not treat as user count.
- [F] GitHub "dependents" pages could not be scraped (no counts returned). [?] unknown.

### 3.2 Yjs / Yrs
- [F] Yjs README "Who is using Yjs" (2026) lists, among others: AFFiNE, Cargo, Gitbook, Evernote (starred), JupyterLab, AWS SageMaker, linear, NextCloud, Proton Docs, Appflowy ("Appflowy - They use Yrs"), Multi.app ("They are using Yrs."). https://github.com/yjs/yjs . [I] This is a self-reported list by the maintainer; I did not verify each entry. Most are JS-only.
- [F] AppFlowy runs Yrs: AppFlowy-Collab Cargo.toml has `yrs = { version = "0.25", features = ["sync"] }` (2026); AppFlowy README: "a single codebase written in Flutter and Rust supporting multiple platforms". https://github.com/AppFlowy-IO/AppFlowy-Collab , https://github.com/AppFlowy-IO/AppFlowy . Also an AppFlowy logo is in y-crdt's sponsors.
- [F] JupyterLab collaboration runs Yrs via Python: jupyter_ydoc pyproject.toml (2026): `"pycrdt >=0.14.0,<0.15.0"`; pycrdt README: "CRDTs based on [Yrs]". https://github.com/jupyter-server/jupyter_ydoc , https://github.com/y-crdt/pycrdt . Server-side only; the browser uses Yjs JS. [I] This is likely the largest Rust-backed deployment: pycrdt 2.4M PyPI downloads/month. [?] Many are non-collab installs/dependency pulls, so I don't know active collaborative users.
- [F] Evernote/Gitbook/Linear/Proton: listed as Yjs users only; [?] I don't know their server language. Nothing found saying they use Yrs.

### 3.3 Loro
- [F] Loro's homepage "Who's Using Loro" (source: loro-dev/loro-docs components/landing/CustomerWall.tsx, 2026) shows: Latch.bio, Marimo, Dora, Subset, Roomy, Nema, AX Semantics, and further entries (I read the first seven). https://github.com/loro-dev/loro-docs/blob/main/components/landing/CustomerWall.tsx (loro.dev itself returned 403 to my fetch.)
- [F] Search-engine summary of loro.dev quotes (secondary, not read directly): "We use Loro as the document representation for our web-based computational notebook software..."; "After extensive research, we made a big early technology bet on Loro... 10/10 experience to date." (Subset). I could not confirm who the first quote's author is: search results attributed it to marimo in one and Latch.bio in another. [?]
- [F] Marimo REMOVED Loro on 2026-11-04. PR #11625 "Remove experimental real-time collaboration" (merged 2026-11-04): "Real-time collaboration also never left experimental. It has known problems around reconnecting, reloading and file watching (#7582, #5800, #11530), and it makes Loro, a native extension, a dependency of every client and server." And: "a CRDT was a reasonable way to keep that state in sync between browsers ... Concurrent editing is handled by the host, cell by cell, so a second mechanism for syncing cell text between browsers is additional complexity with little benefit." https://github.com/marimo-team/marimo/pull/11625 [I] Loro's best-known named user dropped it a week before this report; it was behind an experimental flag (`rtc_v2`) all along.
- [F] Lody (Loro's own team): "toward the end of 2025, we started building lody.ai on top of Loro" (loro.dev/blog/crdt-is-not-enough, via search snippet; I did not open the page). Not an independent adopter.
- [F] Latch.bio shared data: Loro 1.0 post: "Thanks to latch.bio for sharing the document data." (loro.dev/blog/v1.0, via search snippet).
- [F] Velt (2026) comparison says Loro is "in active production use at companies including Latch.bio and Marimo.io" yet rates "Proven scale" "Early (newer engine)" (via search snippet; vendor with own product, [O] low weight). https://velt.dev/blog/best-crdt-libraries-real-time-data-sync
- [?] No Loro user with a large public user base found. I found no engineering blog by Latch.bio, Subset or Macro about Loro.

### 3.4 Automerge
- [F] automerge.org (2026): "support contracts and feature development funding from users like GoodNotes and Bowtie"; "open source sponsorship from partners like Fly.io and Prisma"; "Built for Javascript and Rust, with ports or bindings for Swift, Python, C, Java, and more." https://automerge.org/
- [I] GoodNotes is a large iPad note app (my background knowledge), but the page says only "support contracts"; [?] I do not know whether Goodnotes ships Automerge in the app, in which language, or on what part.
- [F] A Notion engineer on HN (2023, quoted via search snippet, not opened): "I believe Yjs is more actively deployed in production since the Automerge implementation was so far behind performance wise until now." https://news.ycombinator.com/item?id=38197600
- [F] Rust-side users in crates reverse deps: samod, automerge_repo, autosurgeon (4.5k dl), ethersync (364 dl). [?] no known widely used product.

### 3.5 diamond-types
- [?] No product found. Only reverse dep `codemp` (855 dl).

## 4. Real-world sync/divergence bugs in products (not in vlm29 bugs.md)
All are user-filed issues; root causes are NOT established unless stated. I did not check which are CRDT-library bugs vs app bugs.

### AppFlowy (Yrs, Rust)
- #8455 (2026-01-26, open) "[Bug] Sync is unreliable and leads to data loss": "Several times I have found that checklist items have been lost between sessions on my two devices ... it had synced with my desktop version creating a situation where I had nothing to revert back to and an incorrect sync with missing data." Version 0.11.0. Team reply: "We haven't received similar bug reports since our syncing protocol revamp." https://github.com/AppFlowy-IO/AppFlowy/issues/8455
- #9032 (2026-09-20, open) "Data is not synced from another device", data loss in record's page: user gets error "Data is not synced from another device"; "I created a page inside one of the records, but the info I added kept disappearing." v0.14.3; still occurs on 0.14.5. https://github.com/AppFlowy-IO/AppFlowy/issues/9032
- #8992 (2026-09-05, closed) "Mobile <-> Web Cloud Sync Completely Broken - Redis OOM Error" (title only read). https://github.com/AppFlowy-IO/AppFlowy/issues/8992
- #5139 (2024-04-15, open) "[FR] Manual sync conflict resolution" (title only). https://github.com/AppFlowy-IO/AppFlowy/issues/5139

### AFFiNE (Yjs JS + y-octo Rust)
- #14846 (2026-04-17, closed) "no user prompt when sync fails leading to data loss": "The document appears as it was this morning, before I typed anything." A commenter: "silently failed, no UI warning ... I loaded the same URL from another browser and it saved about 70% of the content." with console "An error occurred while Y.doc ... transacting". v0.26.6, self-hosted. https://github.com/toeverything/AFFiNE/issues/14846
- #15497 (2026-08-19, closed) "LOST A WEEK OF DATA" on app.affine.pro: "all changes made over the past week have been lost". Maintainer darkskygit blamed browser storage: "the browser may clear data saved in the browser under certain circumstances". [I] Cause unestablished; not shown to be a CRDT bug. https://github.com/toeverything/AFFiNE/issues/15497
- #13741 (2025-10-13, open) "[Bug]: lost workspaces" (title only). https://github.com/toeverything/AFFiNE/issues/13741

### JupyterLab collaboration (Yrs via pycrdt)
- #597 (2026-06-15, open) "A client can be stuck with a stale version of an old cell version after a no-op-store restart": repro "Open an existing notebook in both A and B ... Disconnect the browser client B ... Change a cell from A ... Shut down the server ... Delete Ydoc ... Reconnect both ... See client B does not get updated cell content"; "a regression introduced by #571 (before which we would see content duplication instead)". https://github.com/jupyterlab/jupyter-collaboration/issues/597 [I] Classic stale-client-after-server-state-loss divergence.
- #219 (2023-12-02, open) "Data loss as notebook does not get saved": "Unfortunately, under some circumstances, and without apparent warnings severe data loss occurs." (v2.0.0a4). https://github.com/jupyterlab/jupyter-collaboration/issues/219
- #214 (2023-11-13, closed) "Incompatible with Jupytext plugin (notebook corruption)". https://github.com/jupyterlab/jupyter-collaboration/issues/214
- #240/#243 (2024, open) "Improve out-of-band change detection" (file changed on disk vs the Ydoc; titles only). #486 (2025, open) "Read-only mode of timeline slider results in data loss" (title only).

### marimo (Loro)
- #11530 (2026-10-28, closed) "rtc_v2: a reloaded tab is registered as an interactor but told it can edit, so every run returns 403": "The session's only consumer can then never run a cell, and nothing in the UI says why." Session-handling bug, not a merge bug. https://github.com/marimo-team/marimo/issues/11530
- #7582 (2025-12-22, open) "RTC not working when session goes to sleep": "I can't edit a cell. This happens when I switch between windows after a period of inactivity." (marimo 0.18.4). https://github.com/marimo-team/marimo/issues/7582
- #5800 (2025-07-29, open) "marimo --watch doesn't work when experimental RTC is enabled": log "RTC: Closing websocket - no session found for file key". https://github.com/marimo-team/marimo/issues/5800

### Tiptap Hocuspocus (Yjs JS)
- [F] Hocuspocus 4 on HN (2026, via search summary, not opened): "document updates are now processed sequentially per connection through an internal queue, which fixes a correctness bug where async hooks could cause CRDT updates to apply out of order under load." https://news.ycombinator.com/item?id=48208834 [?] I did not verify the exact wording; open it before citing.

## 5. Not done / gaps
- [?] Did not verify AppFlowy/AFFiNE active-user counts, Goodnotes's Automerge use, any Notion/Figma/Linear implementation detail (Notion/Figma/Linear not shown to use Rust CRDTs).
- [?] Did not read loro.dev/blog pages, HN threads, or Velt/PkgPulse pages directly (blocked or only via search snippets); items marked "via search snippet" need re-checking.
- [?] Did not examine .wasm contents to prove loro-crdt is Rust-built. [I] by README.
