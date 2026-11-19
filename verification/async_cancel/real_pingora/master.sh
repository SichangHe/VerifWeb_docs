#!/usr/bin/env bash
# Current Pingora master: run PR #1037's cancellation regression (test only) and
# emit crate MIR plus coroutine dumps for check_pingora.py and unwind_mir.py.
# Usage: master.sh SCRATCH EXPECTED_END   (SCRATCH is created; delete it afterwards)
# Output: SCRATCH/master/{crate.mir,dump/}, SCRATCH/test.log
set -eu
scratch=$1
end=$2
here=$(cd -- "$(dirname -- "$0")" && pwd)
rev=3f87e92c982ee27c714506e16ae362776faea4aa
mkdir -p "$scratch"
[ -d "$scratch/src" ] || git clone -q https://github.com/cloudflare/pingora.git "$scratch/src"
git -C "$scratch/src" checkout -q -f --detach "$rev"
cd "$scratch/src"
export CARGO_TARGET_DIR="$scratch/target" CARGO_BUILD_JOBS=4
run() { cpu-run LOW -c 4 -m 16G -t 4096 -o vl_async_study -e "$end" -- "$@"; }
rm -rf "$scratch/master"; mkdir -p "$scratch/master"
run env RUSTC_BOOTSTRAP=1 cargo rustc -p pingora-memory-cache --lib -- \
    "--emit=mir=$scratch/master/crate.mir" -Zdump-mir=coroutine \
    "-Zdump-mir-dir=$scratch/master/dump" >"$scratch/mir.log" 2>&1
echo "mir exit: $?"
git apply "$here/base-regression.patch"
set +e
run cargo test -p pingora-memory-cache --lib \
    read_through::tests::test_cancelled_writer_does_not_block_later_readers -- --exact >"$scratch/test.log" 2>&1
echo "regression exit: $?"
git checkout -q -- .
