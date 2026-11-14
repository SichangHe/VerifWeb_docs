# Build and check paired MIR
(authored by agents unless marked 🧑)

purpose
- prevent the stale emitted-crate selection observed in [source mutation checks](SOURCE_MUTATIONS.md)
- one Cargo invocation writes crate MIR to an explicit fresh filename and coroutine MIR to a fresh dump directory
- require one nonempty get-resume/drop pair and nonempty crate MIR before invoking the combined checker
- temporary MIR is removed on completion; caller's build cache remains reusable
- trusted build workflow, not source authentication or a whole-function proof
  - inherits the [conditional check](../CONDITIONAL_CHECK.md)'s assumptions
  - caller supplies the intended checkout and its Cargo.lock

run
- use the [pinned checkout and toolchain](README.md)
- from the repository root, set CHECKOUT, CACHE, VERUS and EXPECTED_END
- run the entire wrapper under the resource limits

```sh
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
cpu-run LOW -c 2 -o vl_async_study.md -e "$EXPECTED_END" -- \
  systemd-run --user --scope -p MemoryMax=16G -p TasksMax=512 -- \
  uv run --no-project python -m verification.async_cancel.real_pingora.build_check \
  "$CHECKOUT" "$CACHE" "$VERUS"
```

failure behavior
- compilation, missing/ambiguous/empty MIR, checker failure and timeout return nonzero
- compiler timeout is ten minutes; checker timeout is two minutes
- `cpu-run` exit 3 means the LOW budget is full

validation
- executed the pinned Pingora source and existing Verus through this wrapper
  - compilation and combined check returned zero
  - fresh MIR was deleted afterward; the original study artifacts were unchanged

validation
- pinned source compiled through this wrapper on 2026-11-14 UTC
- the combined checker returned `conditional lookup-outcome/Pending cleanup chain passed; see CONDITIONAL_CHECK.md`
