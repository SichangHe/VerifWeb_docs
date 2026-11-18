#!/usr/bin/env bash
# Run Tokio #3652's regression on both sides of fix f7c181c and emit crate MIR.
# Usage: build.sh SCRATCH EXPECTED_END   (SCRATCH is created; delete it afterwards)
set -eu
scratch=$1
end=$2
here=$(cd -- "$(dirname -- "$0")" && pwd)
fixed=f7c181c2c49ee28d7cb0773f5cdb4bec35b5a89b
parent=fee76ea7d5e1f24a155d3fcd319aa2893a095c4f
mkdir -p "$scratch"
[ -d "$scratch/src" ] || git clone -q https://github.com/tokio-rs/tokio.git "$scratch/src"
# Tokio 1.4 trips a lint that newer rustc denies by default; lints do not change code.
export CARGO_TARGET_DIR="$scratch/target" CARGO_BUILD_JOBS=4 RUSTFLAGS="--cap-lints=warn"
run() {
    cpu-run LOW -c 4 -m 16G -t 4096 -o vl_async_study -e "$end" -- "$@"
}
test_name=notify_one_after_dropped_all
for side in fixed parent; do
    rev=${!side}
    git -C "$scratch/src" checkout -q -f --detach "$rev"
    if [ "$side" = parent ]; then
        git -C "$scratch/src" apply "$here/base-regression.patch"
    fi
    cd "$scratch/src"
    [ -f "$scratch/Cargo.lock" ] && cp "$scratch/Cargo.lock" Cargo.lock
    set +e
    run cargo test -p tokio --features full --test sync_notify -- "$test_name" --exact \
        >"$scratch/test-$side.log" 2>&1
    echo "$side regression exit: $?" | tee -a "$scratch/summary.log"
    set -e
    [ -f "$scratch/Cargo.lock" ] || cp Cargo.lock "$scratch/Cargo.lock"
    git checkout -q -- tokio/tests/sync_notify.rs
    run env RUSTC_BOOTSTRAP=1 cargo rustc -p tokio --lib --features sync -- \
        "--emit=mir=$scratch/tokio-$side.mir" >"$scratch/mir-$side.log" 2>&1
    echo "$side mir: $(wc -c <"$scratch/tokio-$side.mir") bytes" | tee -a "$scratch/summary.log"
done
