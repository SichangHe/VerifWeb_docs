#!/usr/bin/env bash
# Emit crate MIR and coroutine dumps of pingora-memory-cache for fixed PR #1037
# and its parent (the buggy production code), for unwind_mir.py.
# Usage: build_unwind.sh SCRATCH EXPECTED_END   (SCRATCH is created; delete it afterwards)
# Output: SCRATCH/{fixed,parent}/{crate.mir,dump/}
set -eu
scratch=$1
end=$2
fixed=b2aeef4875823ffa75b638ba586ed491a1fc851e
parent=4487f7b2ab50f159e4a2cf4f6a6b813f61bb6e19
mkdir -p "$scratch"
if [ ! -d "$scratch/src" ]; then
    git clone -q https://github.com/cloudflare/pingora.git "$scratch/src"
    git -C "$scratch/src" fetch -q origin pull/1037/head
fi
export CARGO_TARGET_DIR="$scratch/target" CARGO_BUILD_JOBS=4 RUSTC_BOOTSTRAP=1
run() {
    cpu-run LOW -c 4 -m 16G -t 4096 -o vl_async_study -e "$end" -- "$@"
}
for side in fixed parent; do
    rev=${!side}
    git -C "$scratch/src" checkout -q -f --detach "$rev"
    cd "$scratch/src"
    [ -f "$scratch/Cargo.lock" ] && cp "$scratch/Cargo.lock" Cargo.lock
    rm -rf "$scratch/$side"
    mkdir -p "$scratch/$side"
    run cargo rustc -p pingora-memory-cache --lib -- \
        "--emit=mir=$scratch/$side/crate.mir" -Zdump-mir=coroutine \
        "-Zdump-mir-dir=$scratch/$side/dump" >"$scratch/$side.log" 2>&1
    [ -f "$scratch/Cargo.lock" ] || cp Cargo.lock "$scratch/Cargo.lock"
    echo "$side: $(wc -c <"$scratch/$side/crate.mir") bytes crate MIR"
done
