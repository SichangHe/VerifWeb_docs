# Where memory goes in Rust/Wasm web apps (measured)
(authored by agents unless marked 🧑)

Question: if an automatic, verified optimization shrank a Rust/Wasm app's own data structures, how much of a tab's memory could it save?

## Takeaways

- The browser dominates. With 1k todos, the app's whole Wasm linear memory is 9–12% of renderer memory. With 10k todos it is 24–35%.
- Even that Wasm memory is mostly framework state, not app data. Live Rust heap is 3.1–5.2 KB per todo. The todo itself is a string of about 45 bytes plus a few fields.
  - inference: the app's model data (todos) is ≲3% of live Wasm heap and ≲1% of renderer memory
- The biggest consumer is the DOM. Blink's GC heap grows by about 9–10 KB per todo, and it is the same for Rust and React.
  - each todo is 6–9 DOM nodes
- Allocator slack is real but bounded. Wasm memory exceeds live heap by 12–19 MB at 10k items (24–31% of Wasm memory). Linear memory never shrinks, so the peak persists.
- Rust/Wasm frameworks do not beat React here: at 10k todos their renderer memory is 189–205 MB versus React's 154 MB.
- Conclusion (opinion): optimizing app-level data structures alone could plausibly remove a few percent of tab memory. The bigger wins are:
  1. fewer DOM nodes, e.g. list virtualization: ~45% of renderer memory at 10k items is Blink GC
  2. smaller framework per-item state (reactive graph / vdom / closures): ~3–5 KB/item
  3. returning memory after peaks (allocator compaction or memory discard; Wasm cannot shrink linear memory today)

## Setup

- apps: the frameworks' own TodoMVC examples, built from git HEAD on 2026-11-20
  - Dioxus 0.8.0-alpha.3 `examples/01-app-demos/todomvc.rs`
    - built as a standalone crate with `dioxus` features `web` (no fullstack); `dx` CLI did not run here (glibc too old); the `asset!` stylesheet line was removed, CSS loaded via HTML instead
    - does not persist to localStorage
  - Leptos `examples/todomvc` (CSR); persists to localStorage
  - Yew 0.23 `examples/function_todomvc`; persists to localStorage
  - React 18 reference: my own minimal TodoMVC with the same DOM shape, `React.memo` per item, persists to localStorage
- build: `cargo build --release --target wasm32-unknown-unknown`, `wasm-bindgen --target web` (version matching each lockfile), no wasm-opt
- live-heap counter: a `#[global_allocator]` wrapper around the default allocator (`System` = dlmalloc) counting live/peak requested bytes, exported to JS ([code](measure_code/countalloc_lib.rs))
- workload: headless Google Chrome, fresh profile per run; JS types N todos (~45 chars each) into the new-todo input via synthetic input + Enter events ([harness](measure_code/measure.mjs))
- metrics after 3 forced GCs:
  - Wasm linear memory: `memory.buffer.byteLength`
  - JS heap: CDP `Performance.getMetrics` `JSHeapUsedSize`
  - DOM nodes: `Performance.getMetrics` `Nodes`
  - per-allocator breakdown: Chrome memory-infra dump (CDP `Tracing.requestMemoryDump`): `blink_gc` (DOM/layout objects), `malloc`, `v8`, `partition_alloc`, `cc`
  - renderer total: PSS from `/proc/PID/smaps_rollup`
- not measured: `performance.measureUserAgentSpecificMemory` (needs cross-origin isolation); heap snapshots
- runs: one per (app, N); no repetitions, so expect noise of a few MB

## Numbers

Units are MB (MiB). "Renderer" is renderer-process PSS. "Wasm" is linear memory size. "Live" is live Rust heap bytes.

Blank page (just an `<input>`): renderer 19.8, JS heap 1.0, Blink GC 0.9.
Other Chrome processes (browser, GPU, network, storage) total about 140 MB, independent of the app.

N = 0 (app loaded, empty list)
- Dioxus: renderer 25.6, Wasm 1.2 (live 0.02), JS 1.2
- Leptos: renderer 24.1, Wasm 1.1 (live 0.01), JS 1.2
- Yew: renderer 23.6, Wasm 1.1 (live 0.01), JS 1.1
- React: renderer 22.2, JS 1.4

N = 1,000
- Dioxus: renderer 65.3, Wasm 8.1 (live 5.0), JS 1.6, Blink GC 16.4, nodes 6.1k
- Leptos: renderer 58.7, Wasm 5.8 (live 3.6), JS 2.2, Blink GC 15.4, nodes 8.1k
- Yew: renderer 58.9, Wasm 5.2 (live 3.0), JS 1.7, Blink GC 16.2, nodes 9.1k
- React: renderer 53.7, JS 4.1, Blink GC 14.2, nodes 6.0k

N = 10,000
- Dioxus: renderer 200.2, Wasm 70.0 (live 50.8, peak 56.0), JS 3.4, Blink GC 88.2, nodes 60k
- Leptos: renderer 190.2, Wasm 50.6 (live 38.6, peak 40.6), JS 9.8, Blink GC 90.6, nodes 80k
- Yew: renderer 184.3, Wasm 44.8 (live 30.7, peak 34.8), JS 4.9, Blink GC 96.7, nodes 90k
- React: renderer 150.2, JS 23.0, Blink GC 87.5, nodes 60k

N = 30,000: React only, renderer 383.1, JS 64.8, Blink GC 255.3. The Rust apps did not finish within 45 min: adding todos one by one is superlinear for them (10k already took 4–17 min versus React's 3.6 min).

Raw JSON lines: `/hdd1/sichangheagent/vl_meeting_work/memmeasure/results.jsonl` (not committed).

## Caveats

- TodoMVC is tiny-data: its app state is a few strings, so it understates apps with large models, e.g. editors or data grids. In those apps, app data could be a larger share.
  - I don't know how large that share gets for real data-heavy Rust/Wasm apps; untested
- No wasm-opt and default allocator; `wee_alloc`-style or size-optimized builds may change slack but not the DOM side
- Desktop Linux headless Chrome; mobile Chrome may differ, e.g. GPU/`cc` memory
- Memory-infra categories overlap with PSS imperfectly. Wasm linear memory is not listed under any top-level allocator but is resident in PSS.

## Literature

- Yan et al., "Understanding the performance of WebAssembly applications", IMC 2021, https://dl.acm.org/doi/10.1145/3487552.3487827. Abstract, finding (4): "WebAssembly uses significantly more memory than its JavaScript counterparts."
- Qazi et al., "Mobile web browsing under memory pressure", ACM SIGCOMM CCR 2020, https://dl.acm.org/doi/abs/10.1145/3431832.3431837. Google Scholar snippet: "… memory footprint of Web browsing when loading Web pages … , Web servers precompute the JavaScript heap and the DOM tree for a page and when a mobile browser requests the page…"
- not read further: "Shiny Objects: Object-Centric Characterization of Chromium" (https://dl.acm.org/doi/abs/10.1145/3788102); "Webmedic: Disentangling the memory-functionality tension for the next billion mobile web users" (https://dl.acm.org/doi/abs/10.1145/3446382.3448652)
