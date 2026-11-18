#!/usr/bin/env bash
# Run the unwind-gap harness (h2_unwind_gap.rs) against Hyper fix 5b17a69.
# Usage: unwind_gap.sh SCRATCH EXPECTED_END   (SCRATCH is created; delete it afterwards)
set -eu
scratch=$1
end=$2
here=$(cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$scratch"
[ -d "$scratch/src" ] || git clone -q https://github.com/hyperium/hyper.git "$scratch/src"
git -C "$scratch/src" checkout -q -f --detach 5b17a69ebcf969471c1a19b25ed2cb81299d1be6
cp "$here/h2_unwind_gap.rs" "$scratch/src/tests/h2_unwind_gap.rs"
cd "$scratch/src"
export CARGO_TARGET_DIR="$scratch/target" CARGO_BUILD_JOBS=4 RUSTFLAGS='--cfg hyper_unstable_tracing'
cpu-run LOW -c 4 -m 16G -t 4096 -o vl_async_study -e "$end" -- \
    cargo test --features full,tracing --test h2_unwind_gap -- --test-threads=1 --nocapture
