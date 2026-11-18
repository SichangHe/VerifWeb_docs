#!/usr/bin/env bash
# Run Hyper's #4040 regression on both sides of fix 5b17a69 and emit crate MIR.
# Usage: build.sh SCRATCH EXPECTED_END   (SCRATCH is created; delete it afterwards)
set -eu
scratch=$1
end=$2
here=$(cd -- "$(dirname -- "$0")" && pwd)
fixed=5b17a69ebcf969471c1a19b25ed2cb81299d1be6
parent=7211ec25eff2ea6ee783817fee2a221d4eb2ed03
mkdir -p "$scratch"
[ -d "$scratch/src" ] || git clone -q https://github.com/hyperium/hyper.git "$scratch/src"
export CARGO_TARGET_DIR="$scratch/target" CARGO_BUILD_JOBS=4
run() {
    cpu-run LOW -c 4 -m 16G -t 4096 -o vl_async_study -e "$end" -- "$@"
}
test_name=conn::h2_pipe_task_cancelled_on_response_future_drop
for side in fixed parent; do
    rev=${!side}
    git -C "$scratch/src" checkout -q -f --detach "$rev"
    if [ "$side" = parent ]; then
        git -C "$scratch/src" apply "$here/base-regression.patch"
    fi
    cd "$scratch/src"
    [ -f "$scratch/Cargo.lock" ] && cp "$scratch/Cargo.lock" Cargo.lock
    set +e
    run cargo test --features full --test client -- "$test_name" --exact \
        >"$scratch/test-$side.log" 2>&1
    echo "$side regression exit: $?" | tee -a "$scratch/summary.log"
    set -e
    [ -f "$scratch/Cargo.lock" ] || cp Cargo.lock "$scratch/Cargo.lock"
    git checkout -q -- tests/client.rs
    run env RUSTC_BOOTSTRAP=1 cargo rustc --lib --features client,http2 -- \
        "--emit=mir=$scratch/hyper-$side.mir" >"$scratch/mir-$side.log" 2>&1
    echo "$side mir: $(wc -c <"$scratch/hyper-$side.mir") bytes" | tee -a "$scratch/summary.log"
done
