# vlm_servo shared brief
(authored by agents unless marked 🧑)

Goal (from manager, quoting human): attempt feasibility of Verus verification on small real pieces of Servo (Rust browser engine) or related Rust browser crates; "pick 2-4 concrete components, actually try to verify a property, record what worked, what blocked, effort, and what the Verus checker reports per failed attempt". Human: "Be 8x more aggressive"; "You have 1 day".

Tools (working, verified):
- Verus: `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus FILE.rs` (version 0.2026.11.02, rustc 1.99.1 via rustup). Ignore the harmless `GLIBC_2.39 weak version` warning line.
- Smoke test: `/hdd1/sichangheagent/vl_meeting_work/tools/t/a.rs`.
- Verus guide: https://verus-lang.github.io/verus/guide/ ; vstd docs: https://verus-lang.github.io/verus/verusdoc/vstd/

Rules:
- work only under your dir `/hdd1/sichangheagent/vl_meeting_work/out/vlm_servo/<component>/`; never write to /ssd1/sichangheagent/email
- fetch real upstream source (crates.io tarball via `curl -sL https://crates.io/api/v1/crates/NAME/VERSION/download | tar xz`, or a shallow git clone) into `<component>/src_upstream/`; record exact version/commit
- port real code (as close to verbatim as possible) into a standalone Verus file; record every change you had to make to the original code and why
- prove at least one meaningful property (memory safety-adjacent: no overflow/panic/out-of-bounds; or functional correctness)
- keep a log of every failed verification attempt: the property/code, and the exact Verus error output (verbatim, trimmed), and what you changed next
- run commands with `timeout`

Output: `<component>/REPORT.md` with: component + upstream version, property(ies) attempted, result (proved / partial / blocked), verbatim per-failure Verus messages + what they told (or failed to tell) you, required code changes, unsupported Rust features hit, effort (wall-clock time, number of verify iterations, lines of spec/proof vs code), and the final `.rs` file(s) that verify with the command to rerun.
