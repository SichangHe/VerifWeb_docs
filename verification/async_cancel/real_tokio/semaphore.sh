#!/usr/bin/env bash
# Emit Tokio master MIR for the batch-semaphore checker and run the loom permit test.
# Usage: semaphore.sh SCRATCH EXPECTED_END   (SCRATCH is created; delete it afterwards)
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
    "--emit=mir=$scratch/tokio.mir" >"$scratch/mir.log" 2>&1
cat "$here/semaphore-loom.patch.rs" >>tokio/src/sync/tests/loom_semaphore_batch.rs
cat "$here/mpsc-loom.patch.rs" >>tokio/src/sync/tests/loom_mpsc.rs
set +e
CARGO_TARGET_DIR="$scratch/loomtarget" RUSTFLAGS="--cfg loom -C debug-assertions" LOOM_MAX_PREEMPTIONS=3 \
    run cargo test --lib --release --features full -- sync::tests::loom_semaphore_batch >"$scratch/loom.log" 2>&1
echo "loom exit: $?"
CARGO_TARGET_DIR="$scratch/loomtarget" RUSTFLAGS="--cfg loom -C debug-assertions" LOOM_MAX_PREEMPTIONS=3 \
    run cargo test --lib --release --features full -- sync::tests::loom_mpsc::close_after_repoll_recv_returns_none >"$scratch/mpsc.log" 2>&1
echo "mpsc loom exit: $?"
git checkout -q -- .
