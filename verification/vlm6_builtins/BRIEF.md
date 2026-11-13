# vlm6_builtins brief
(authored by agents unless marked 🧑)

Manager's task (verbatim): "Scale up the approach that found the Boa at() bug (/hdd1/sichangheagent/vl_meeting_work/out/poke_esmeta/REPORT.md): hunt for more integer-conversion/overflow edge-case bugs in Boa builtins (and optionally another Rust JS engine) by hand-transcribing ECMA-262 algorithms (ToIntegerOrInfinity, clamping, relative indices) into Verus specs or z3 checks for 10+ builtins that take numeric index/length arguments, then confirming any proof failure with a concrete JS repro on Boa main 329e897; check test262 coverage and Boa issues for each."
Constraints (verbatim): "memory guard: no builds/heavy runs when `free -g` available < 60 GiB; do NOT file upstream or contact anyone; never write in /ssd1/sichangheagent/email"

Resources
- prior work: /hdd1/sichangheagent/vl_meeting_work/out/poke_esmeta/REPORT.md, work/builtins.rs (Verus spec+port example)
- Boa source @329e897: /hdd1/sichangheagent/vl_meeting_work/out/vfy_at/src/boa (read-only; do not build)
- Boa release CLI @329e897: /hdd1/sichangheagent/vl_meeting_work/out/poke_esmeta/work/boa_bin/bin/boa FILE.js
- ECMA-262 spec: /hdd1/sichangheagent/vl_meeting_work/out/vfy_at/src/ecma.html
- test262: /hdd1/sichangheagent/vl_meeting_work/out/vfy_at/src/test262
- Verus: /tmp/vd/verus FILE.rs ; z3: ~/.local/bin/z3
- Boa issues: `gh issue list -R boa-dev/boa --search ... --state all` (read only)
- known already: String.prototype.at(-1e300) crash (do not re-report)

Output: write YOUR_DIR/RESULT.md (per builtin: spec checked / Verus-or-z3 result / JS repro + Boa output vs expected / test262 coverage of the edge / related Boa issue) plus the spec/proof files. Distinguish confirmed (repro on real Boa) vs proof-only.
