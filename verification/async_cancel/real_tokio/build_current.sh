#!/usr/bin/env bash
# Emit crate MIR for current Tokio master and run Tokio's loom Notify tests plus ours.
# Usage: build_current.sh SCRATCH EXPECTED_END   (SCRATCH is created; delete it afterwards)
set -eu
scratch=$1
end=$2
here=$(cd -- "$(dirname -- "$0")" && pwd)
rev=fc0d151753b5fb10125ecef2d48f29b192c9abcf
mkdir -p "$scratch"
[ -d "$scratch/src" ] || git clone -q https://github.com/tokio-rs/tokio.git "$scratch/src"
git -C "$scratch/src" checkout -q -f --detach "$rev"
run() { cpu-run LOW -c 4 -m 16G -t 4096 -o vl_async_study -e "$end" -- "$@"; }
cd "$scratch/src"
CARGO_TARGET_DIR="$scratch/target" run env RUSTC_BOOTSTRAP=1 cargo rustc -p tokio --lib --features sync -- \
    "--emit=mir=$scratch/tokio-master.mir" >"$scratch/mir.log" 2>&1
git apply "$here/current-loom.patch"
set +e
CARGO_TARGET_DIR="$scratch/loomtarget" RUSTFLAGS="--cfg loom -C debug-assertions" LOOM_MAX_PREEMPTIONS=2 \
    run cargo test --lib --release --features full -- sync::tests::loom_notify >"$scratch/loom.log" 2>&1
echo "loom exit: $?"
git checkout -q -- .
