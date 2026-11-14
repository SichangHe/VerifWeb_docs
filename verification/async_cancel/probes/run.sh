#!/usr/bin/env bash
set -eu
: "${VERUS:?set VERUS to the verifier executable}"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
dir=$(cd -- "$(dirname -- "$0")" && pwd)
failed=0
for name in basic cross_module cross_module_create mut_ref custom_future async_block async_trait false_ensures open_invariant no_lifetime no_lifetime_flag drop_cleanup drop_opens; do
    expected=0
    diagnostic='verification results::'
    source_name=$name
    extra=()
    case "$name" in
        cross_module_create)
            expected=${EXPECT_CROSS_MODULE_CREATE_EXIT:-1}
            if [ "$expected" -ne 0 ]; then diagnostic='could not find function Fun(Path(vstd,'; fi;;
        no_lifetime_flag) source_name=no_lifetime; extra=(--no-lifetime);;
        drop_opens) expected=1; diagnostic='a `Drop` implementation must be marked `opens_invariants none`';;
        async_block) expected=1; diagnostic='Verus does not currently support coroutine types';;
        async_trait) expected=1; diagnostic='Verus does not currently support `impl Trait` types in trait definitions';;
        false_ensures) expected=1; diagnostic='postcondition not satisfied';;
        open_invariant) expected=1; diagnostic='callee may open invariants disallowed at call-site';;
    esac
    status=0
    timeout 30s "$VERUS" --num-threads 1 "${extra[@]}" "$dir/$source_name.rs" >"$scratch/$name.log" 2>&1 || status=$?
    if [ "$status" -ne "$expected" ] || ! rg -q -F "$diagnostic" "$scratch/$name.log"; then
        printf 'unexpected result: %s (exit %s; expected %s)\n' "$name" "$status" "$expected"
        cat "$scratch/$name.log"
        failed=1
    fi
done
exit "$failed"
