#!/usr/bin/env bash
# Current Hyper master: run the #4040 regression, emit crate MIR, run the unwind-gap harness.
# Usage: master.sh SCRATCH EXPECTED_END   (SCRATCH is created; delete it afterwards)
# Output: SCRATCH/hyper-master.mir, SCRATCH/{test,mir,gap}.log, summary on stdout
set -eu
scratch=$1
end=$2
here=$(cd -- "$(dirname -- "$0")" && pwd)
rev=21da6a59db9a90631302e7b173c106b723b9065f
mkdir -p "$scratch"
[ -d "$scratch/src" ] || git clone -q https://github.com/hyperium/hyper.git "$scratch/src"
git -C "$scratch/src" checkout -q -f --detach "$rev"
cd "$scratch/src"
run() { cpu-run LOW -c 4 -m 16G -t 4096 -o vl_async_study -e "$end" -- "$@"; }
export CARGO_BUILD_JOBS=4
set +e
CARGO_TARGET_DIR="$scratch/target" run cargo test --features full --test client -- \
    conn::h2_pipe_task_cancelled_on_response_future_drop --exact >"$scratch/test.log" 2>&1
echo "regression exit: $?"
CARGO_TARGET_DIR="$scratch/target" run env RUSTC_BOOTSTRAP=1 cargo rustc --lib --features client,http2 -- \
    "--emit=mir=$scratch/hyper-master.mir" >"$scratch/mir.log" 2>&1
echo "mir exit: $?"
cp "$here/h2_unwind_gap.rs" tests/h2_unwind_gap.rs
CARGO_TARGET_DIR="$scratch/gaptarget" RUSTFLAGS='--cfg hyper_unstable_tracing' run \
    cargo test --features full,tracing --test h2_unwind_gap -- --test-threads=1 --nocapture >"$scratch/gap.log" 2>&1
echo "unwind gap exit: $?"
rm -f tests/h2_unwind_gap.rs
