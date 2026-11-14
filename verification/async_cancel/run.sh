#!/usr/bin/env bash
set -eu
: "${VERUS:?set VERUS to the verifier executable}"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
dir=$(cd -- "$(dirname -- "$0")" && pwd)
bash "$dir/probes/run.sh"
if ! timeout 30s "$VERUS" --num-threads 1 "$dir/cancel_runtime.rs" --compile -o "$scratch/cancel_runtime" >"$scratch/verify.log" 2>&1; then
    cat "$scratch/verify.log"
    exit 1
fi
if ! timeout 10s "$scratch/cancel_runtime" >"$scratch/runtime.log" 2>&1; then
    cat "$scratch/runtime.log"
    exit 1
fi
if ! rg -q -x 'state after cancellation: 1' "$scratch/runtime.log"; then
    cat "$scratch/runtime.log"
    exit 1
fi
