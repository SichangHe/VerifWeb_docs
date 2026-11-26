#!/usr/bin/env bash
# MIR correspondence between real Tokio's batch semaphore and the Verus copy, its mutation check,
# and Tokio's batch-semaphore loom tests with every atomic of batch_semaphore.rs weakened to Relaxed.
# Usage: semaphore_mir.sh SCRATCH EXPECTED_END VERUS   (SCRATCH is created; delete it afterwards)
set -eu
scratch=$1
end=$2
verus=$3
here=$(cd -- "$(dirname -- "$0")" && pwd)
proof="$here/../semaphore_proof"
rev=fc0d151753b5fb10125ecef2d48f29b192c9abcf
run() {  # cpu-run LOW, waiting while it answers 3 (no capacity yet)
    while :; do
        set +e
        cpu-run LOW -c 4 -m 16G -t 4096 -o vl_async_study -e "$end" -- "$@"
        r=$?
        set -e
        [ "$r" -ne 3 ] && return "$r"
        sleep 60
    done
}
mkdir -p "$scratch/mir"
[ -d "$scratch/src" ] || git clone -q https://github.com/tokio-rs/tokio.git "$scratch/src"
git -C "$scratch/src" checkout -q -f --detach "$rev"
git -C "$scratch/src" apply "$here/semaphore-close-fix.patch"
# builds real.mir and verus.mir (rustc 1.91.0, the toolchain Verus pins), compares, runs the mutations
python3 -I "$proof/mutate_mir.py" "$verus" "$scratch/src" "$scratch/mir" "$end"
python3 -I "$proof/mir_correspond.py" "$scratch/mir/real.mir" "$scratch/mir/verus.mir" --orderings
# every Ordering in batch_semaphore.rs -> Relaxed (17 sites), plus our loom permit test
f="$scratch/src/tokio/src/sync/batch_semaphore.rs"
sed -E -i -e 's/\(Acquire\)/(Relaxed)/g' -e 's/, Release\)/, Relaxed)/g' -e 's/AcqRel, Acquire\)/Relaxed, Relaxed)/g' \
    -e 's/^(\s*)(AcqRel|Acquire),$/\1Relaxed,/' "$f"
echo "orderings left in batch_semaphore.rs (outside comments): $(grep -vE '^\s*//' "$f" | grep -cE '\b(AcqRel|Release)\b|\(Acquire\)|Acquire,$')"
cat "$here/semaphore-loom.patch.rs" >>"$scratch/src/tokio/src/sync/tests/loom_semaphore_batch.rs"
cd "$scratch/src"
set +e
CARGO_TARGET_DIR="$scratch/loomtarget" RUSTFLAGS="--cfg loom -C debug-assertions" LOOM_MAX_PREEMPTIONS=3 \
    run cargo test --lib --release --features full -- sync::tests::loom_semaphore_batch >"$scratch/loom-relaxed.log" 2>&1
echo "relaxed loom exit: $?"
set -e
grep -E "^test |test result" "$scratch/loom-relaxed.log" || true
git checkout -q -- .
