#!/usr/bin/env bash
# Reproduce: fixed quinn code verifies, pre-fix code fails, both match upstream text.
set -eu
: "${VERUS:?set VERUS to the verifier executable}"
dir=$(cd -- "$(dirname -- "$0")" && pwd)
scratch=$(mktemp -d); trap 'rm -rf "$scratch"' EXIT
git clone -q https://github.com/quinn-rs/quinn "$scratch/quinn"
git -C "$scratch/quinn" show c7b46a969cd315398b504792e9e9af6a15a7dcc6:quinn-proto/src/connection/datagrams.rs >"$scratch/up_fixed.rs"
git -C "$scratch/quinn" show a3109c34^:quinn-proto/src/connection/datagrams.rs >"$scratch/up_buggy.rs"
python3 -I "$dir/conform.py" "$dir/fixed.rs" "$scratch/up_fixed.rs"
python3 -I "$dir/conform.py" "$dir/buggy.rs" "$scratch/up_buggy.rs"
timeout 300 "$VERUS" --num-threads 1 "$dir/fixed.rs" 2>&1 | grep -q 'verification results:: 19 verified, 0 errors'
echo "fixed: 19 verified, 0 errors"
if timeout 300 "$VERUS" --num-threads 1 "$dir/buggy.rs" >"$scratch/b.log" 2>&1; then echo "buggy unexpectedly verified"; exit 1; fi
grep -q 'verification results:: 18 verified, 1 errors' "$scratch/b.log"
grep -A3 'postcondition not satisfied' "$scratch/b.log" | grep -q 'window.is_some() && old(self).incoming.mem() <= window.unwrap()'
echo "buggy: fails exactly the memory-bound postcondition"
