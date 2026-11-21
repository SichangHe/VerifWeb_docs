// Usage: node measure.mjs APP N  -> prints one JSON line of memory metrics after adding N todos.
import puppeteer from "puppeteer-core";
import fs from "fs";
const [app, nStr] = process.argv.slice(2), n = +nStr;
const browser = await puppeteer.launch({
  executablePath: "/usr/bin/google-chrome", headless: true, protocolTimeout: 2700000,
  args: ["--no-sandbox", "--renderer-process-limit=1", "--js-flags=--expose-gc"],
});
const page = await browser.newPage();
const cdp = await page.createCDPSession();
await cdp.send("Performance.enable");
await page.goto(`http://127.0.0.1:${process.env.PORT}/${app}/index.html`);
await page.waitForFunction("window.__ready === true", { timeout: 60000 });
await page.waitForSelector("input.new-todo", { timeout: 60000 });
const t0 = Date.now();
await page.evaluate(async (n) => {
  const input = document.querySelector("input.new-todo");
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
  const key = (type) => {
    const e = new KeyboardEvent(type, { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true });
    if (e.keyCode !== 13) Object.defineProperty(e, "keyCode", { get: () => 13 });
    input.dispatchEvent(e);
  };
  for (let i = 0; i < n; i++) {
    setValue.call(input, `todo item number ${i} with some realistic text`);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0)); // let async frameworks see the draft
    key("keydown"); key("keypress"); key("keyup");
    if (i % 50 === 49) await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));
  }
  await new Promise((r) => setTimeout(r, 500));
}, n);
const fillMs = Date.now() - t0;
for (let i = 0; i < 3; i++) await cdp.send("HeapProfiler.collectGarbage");
await new Promise((r) => setTimeout(r, 1000));
const page_ = await page.evaluate(() => ({
  n_li: document.querySelectorAll("li").length,
  wasm_mem: window.__wasm?.memory?.buffer.byteLength ?? 0,
  heap_live: window.__m?.heap_live_bytes?.() ?? 0,
  heap_peak: window.__m?.heap_peak_bytes?.() ?? 0,
  n_allocs: window.__m?.heap_n_live_allocs?.() ?? 0,
  ls_bytes: Object.keys(localStorage).reduce((s, k) => s + 2 * (k.length + localStorage.getItem(k).length), 0),
}));
const perf = Object.fromEntries((await cdp.send("Performance.getMetrics")).metrics.map((m) => [m.name, m.value]));
// Chrome memory-infra dump: per-process allocator totals (V8, Blink GC, PartitionAlloc, malloc, ...).
const bcdp = await browser.target().createCDPSession();
const chunks = [];
bcdp.on("Tracing.dataCollected", (e) => chunks.push(...e.value));
const done = new Promise((r) => bcdp.once("Tracing.tracingComplete", r));
await bcdp.send("Tracing.start", { traceConfig: { includedCategories: ["disabled-by-default-memory-infra"], memoryDumpConfig: { triggers: [] } } });
await bcdp.send("Tracing.requestMemoryDump", { levelOfDetail: "detailed" });
await bcdp.send("Tracing.end");
await done;
const procInfo = (await bcdp.send("SystemInfo.getProcessInfo")).processInfo;
const pidType = Object.fromEntries(procInfo.map((p) => [p.id, p.type]));
const pss = (pid) => { try { return +/Pss:\s+(\d+)/.exec(fs.readFileSync(`/proc/${pid}/smaps_rollup`, "utf8"))[1] * 1024; } catch { return null; } };
const procs = {};
for (const ev of chunks.filter((e) => e.ph === "v" && e.args?.dumps)) {
  const alloc = ev.args.dumps.allocators || {};
  const top = {};
  for (const [name, d] of Object.entries(alloc)) {
    if (name.includes("/")) continue;
    if (d.attrs?.size) top[name] = parseInt(d.attrs.size.value, 16);
  }
  const type = pidType[ev.pid] ?? "browser";
  procs[`${type}:${ev.pid}`] = { pss: pss(ev.pid), top,
    v8_detail: Object.fromEntries(Object.entries(alloc).filter(([k, d]) => /^v8\/main\/heap\/[a-z_]+$/.test(k) && d.attrs?.size).map(([k, d]) => [k.split("/").pop(), parseInt(d.attrs.size.value, 16)])),
    blink: Object.fromEntries(Object.entries(alloc).filter(([k, d]) => /^(blink_gc\/main\/heap|partition_alloc\/partitions)\/[A-Za-z_]+$/.test(k) && d.attrs?.size).map(([k, d]) => [k, parseInt(d.attrs.size.value, 16)])) };
}
console.log(JSON.stringify({ app, n, fillMs, ...page_, JSHeapUsedSize: perf.JSHeapUsedSize, JSHeapTotalSize: perf.JSHeapTotalSize, Nodes: perf.Nodes, procs }));
await browser.close();
