# Sharing processes across tabs/tenants: deeper map + other directions
(authored by agents unless marked 🧑)

Labels: [F] fetched fact, [I] inference, [O] opinion. Quotes and URLs for every paper: `prior_work.md` (isolation) and `other_directions.md` (other web directions). Raw Scholar pages: `scholar/`, `other/`.

## Takeaway
- [O] best direction from the main thread: a per-tenant checker for JIT output, run before JIT code becomes executable (direction 2 of vlm9). Nobody we found does this, and it targets the exact gap Cloudflare names.
- [O] best other direction: measure what browser agents cost as a server workload, then design multi-tenancy for agent browsers. Nobody we found measures this, and it connects back to process sharing.
- [F] the first experiment shows the checker needs V8's pointer-compression/sandbox build. Without it, roughly a third of JIT memory accesses use raw 64-bit pointers that no static check can bound.

## Prior work (details in prior_work.md)
- [F] Icarus is real (SOSP 2024, https://dl.acm.org/doi/abs/10.1145/3694715.3695949): "a new framework for implementing JIT compilers that are automatically, formally verified to be safe"
  - [I] it verifies the compiler once and does not check each output; its goal is memory safety, not isolation between tenants
- [F] Mohabi is real (OSDI 2026, https://www.usenix.org/conference/osdi26/presentation/sharma): "Mohabi leverages software-based fault isolation (SFI) to ensure JavaScript engine bugs cannot affect the rest of the browser"; it costs about 25% on JetStream and Speedometer
  - [I] it walls off the whole engine from the browser, not one tab from another
- [F] groups working on this
  - UCSD/UT Austin/Stanford (Stefan, Shacham, Narayan, Garfinkel, Jhala): RLBox, VeriWasm, Swivel, WaVe, Icarus, Mohabi
  - Graz (Gruss, Schwarz, Schwarzl): Spectre on Workers, Dynamic Process Isolation
  - also MPI-SWS (ERIM), Rochester (Hodor), and Cloudflare in production
- [I] open gaps
  1. Spectre: Cloudflare 2026 leaked "up to 12 bit/s with a 99% accuracy" in production; "Detection cannot happen only after a script finishes"
  2. Cloudflare says code that can run arbitrary machine code "could disable memory protection keys". VeriWasm and LFI check one fixed sandbox of ahead-of-time code. We found no checker for many tenant cages inside one JIT.
     - only abstracts were searched, so check full texts before claiming novelty
  3. cost: Mohabi ~25%, Swivel's deterministic mode 3.3% to 240.2%; we found no work running many tenants in one engine with proofs at acceptable cost

## Other directions (details in other_directions.md)
- [F] prompt-injection defenses for browser agents are crowded: WASP (221 citations), BrowseSafe, ceLLMate, Prismata
- [O] worth considering
  1. cost of the browser as an agent runtime: per-session CPU, memory and latency, then multi-tenancy designed for agents
     - [I] no measurement paper found; it ties back to process sharing
  2. test HTTP-layer enforcement at crawl scale: ceLLMate assumes every side effect shows up as an HTTP request; check this on real sites using the group's web data
  3. measure AI-agent traffic and bot defenses passively: moderately crowded, and it needs a system on top to count as systems work
- [F] warning: "Site Isolation is Dead" (IEEE S&P 2026) argues agentic browsers break Site Isolation. Only its Scholar snippet was read, so read it before committing.

## Experiment: what would a JIT-output checker face? (`exp/`)
Setup: Node v22.21.1 (V8 with pointer compression off); 9 mixed workloads (`exp/work.js`); `--print-opt-code` output classified by `exp/ana.py`; 14 optimized functions, 2,217 instructions.
- [F] memory operands by base register
  - stack (rbp/rsp): 34%
  - r13, the isolate/roots register: 32%
  - raw heap pointers in other registers: 32%
  - r14, the cage base: 1%
- [F] no WRPKRU bytes found
- [F] 17 distinct call/jump targets, 244 total; 148 were not labeled as builtins (probably calls through r13 or registers)
- [I] what this means
  - with raw 64-bit pointers, a checker cannot prove an access stays in a tenant's region, so it needs pointer compression or the V8 sandbox (Chrome's default), where heap accesses are cage base + a 32-bit offset
  - r13-relative accesses reach per-isolate state, so a tenant switch must also swap or validate r13
  - the run hit only a few builtin targets, so a short list of allowed entry points looks plausible, but the 148 unlabeled calls must be resolved first
- next step [O]: rerun on a V8 build with pointer compression and sandbox (d8), and resolve the unlabeled calls
  - build only if `free -g` shows at least 60 GiB available

## Limits
- Scholar showed a CAPTCHA after about 12 fetches. It was not bypassed, so some cited-by pages are missing.
- PDF text extraction failed, so quotes come from abstracts, snippets and blogs.
- one small, non-representative workload
