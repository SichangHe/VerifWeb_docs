"""Check that mir_correspond.py catches a moved or changed atomic operation, on either side.

Each mutation changes one side (the Verus copy, or the real Tokio file), rebuilds that side's
MIR, and runs the comparison against the unchanged other side. It passes only if exactly the
expected function differs and every other function still agrees. The ordering-only mutation
is the exception: the comparison ignores orderings by design, so it must still agree, and the
ordering listing must show the change.

Usage: python3 -I mutate_mir.py VERUS TOKIO_SRC SCRATCH END
  TOKIO_SRC: a Tokio checkout at fc0d151 with semaphore-close-fix.patch applied (restored on exit)
  SCRATCH:   empty directory for MIR files; END: cpu-run end time
Heavy steps (Verus, cargo) run under `cpu-run LOW`; exit 0 iff every mutation is caught as expected.
"""
import contextlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mir_correspond as mc  # noqa: E402

COPY = open(os.path.join(HERE, "batch_semaphore.rs")).read()


def rep(a, b):
    def f(s):
        assert s.count(a) == 1, a
        return s.replace(a, b)
    return f


def move_before(block, anchor, new):
    """Delete `block`, insert `new` just before `anchor`."""
    def f(s):
        assert s.count(block) == 1 and s.count(anchor) == 1, (block, anchor)
        s = s.replace(block, "")
        return s.replace(anchor, new + anchor)
    return f


DROP_LOAD = """        let st = atomic_with_ghost!(&self.node.state => load();
            ghost g => {
                self.semaphore.inst.borrow().ws_bound(self.node.id@, &g, self.nt.borrow());
                let tracked (Tracked(o2), Tracked(f2)) = self.semaphore.inst.borrow().retire(self.node.id@, &mut lk, &g, to, tf);
                to = o2; tf = f2;
            }); // VERUS: `self.node.state.load(Acquire)` bound to `st` (ghost step)
"""

# name -> (side, change, expected differing function or None for "must still agree")
MUTATIONS = {
    # the close fix's give-back runs even when nothing was acquired: atomic moved out of its branch
    "verus_close_fix_unguarded": ("verus", rep(
        "            if acquired > 0 {\n                let tracked mut tf = take_fl(fl);\n                atomic_with_ghost!(&self.permits => fetch_add(acquired",
        "            if true {\n                let tracked mut tf = take_fl(fl);\n                atomic_with_ghost!(&self.permits => fetch_add(acquired"),
        "poll_acquire"),
    # remainder returned without the shift: changed atomic argument
    "verus_fetch_add_unshifted": ("verus", rep(
        "fetch_add(rem << Self::PERMIT_SHIFT);", "fetch_add(rem);"), "add_permits_locked"),
    # close toggles the bit with fetch_xor instead of setting it with fetch_or: changed atomic operation
    "verus_close_fetch_xor": ("verus", rep(
        "atomic_with_ghost!(&self.permits => fetch_or(Self::CLOSED);",
        "atomic_with_ghost!(&self.permits => fetch_xor(Self::CLOSED);"), "close"),
    # drop reads its waiter state before taking the lock: atomic moved across lock and list op
    "verus_drop_load_before_lock": ("verus", move_before(
        DROP_LOAD, "        let (mut waiters, Tracked(mut lk)) = self.semaphore.waiters.lock();\n\n        // remove the entry",
        "        let st = atomic_with_ghost!(&self.node.state => load(); ghost g => {});\n"), "Acquire::drop"),
    # real master: no close fix
    "real_master_no_close_fix": ("real", rep(
        "            if acquired > 0 {\n                self.permits.fetch_add(acquired << Self::PERMIT_SHIFT, Release);\n            }\n", ""),
        "poll_acquire"),
    # real drop reads the state before locking and unlinking (moved atomic)
    "real_drop_load_before_lock": ("real", move_before(
        "        let acquired_permits = self.num_permits - self.node.state.load(Acquire);\n",
        "        let mut waiters = self.semaphore.waiters.lock();\n\n        // remove the entry from the list\n        let node = NonNull::from(&mut self.node);",
        "        let acquired_permits = self.num_permits - self.node.state.load(Acquire);\n"), "Acquire::drop"),
    # ordering only: not compared by design, must still agree; shown by --orderings
    "real_release_relaxed": ("real", rep(
        "let prev = self.permits.fetch_add(rem << Self::PERMIT_SHIFT, Release);",
        "let prev = self.permits.fetch_add(rem << Self::PERMIT_SHIFT, Relaxed);"), None),
}


def run(end, cmd, cwd=None, log=None):
    """Run under cpu-run LOW, retrying while the scheduler says wait (exit 3)."""
    while True:
        r = subprocess.run(["cpu-run", "LOW", "-c", "4", "-m", "16G", "-t", "4096", "-o", "vl_async_study",
                            "-e", end, "--"] + cmd, cwd=cwd, capture_output=True, text=True)
        if r.returncode != 3:
            break
        time.sleep(30)
    if log:
        open(log, "w").write(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(cmd)}\n{r.stderr[-2000:]}")


def verus_mir(verus, text, scratch, end, tag):
    src = os.path.join(scratch, f"{tag}.rs")
    open(src, "w").write(text)
    out = os.path.join(scratch, f"{tag}.mir")
    run(end, [verus, "--crate-type=lib", src, "--compile", "--no-verify", "--emit=mir", "-o", out], cwd=scratch)
    return out


def real_mir(tokio, scratch, end, tag):
    out = os.path.join(scratch, f"{tag}.mir")
    run(end, ["env", "RUSTC_BOOTSTRAP=1", f"CARGO_TARGET_DIR={scratch}/target", "cargo", "+1.91.0", "rustc", "-p", "tokio",
              "--lib", "--features", "sync", "--", f"--emit=mir={out}"], cwd=tokio)
    return out


def compare(real, verus, orderings=False):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mc.main(["mir_correspond.py", real, verus] + (["--orderings"] if orderings else []))
    out = buf.getvalue()
    differ = re.findall(r"^(\S+): .*: DIFFERS$", out, re.M)
    return code, differ, out


def main(argv):
    verus, tokio, scratch, end = argv[1:5]
    real_file = os.path.join(tokio, "tokio/src/sync/batch_semaphore.rs")
    real_src = open(real_file).read()
    base_real = real_mir(tokio, scratch, end, "real")
    base_verus = verus_mir(verus, COPY, scratch, end, "verus")
    code, differ, out = compare(base_real, base_verus, orderings=True)
    print(f"original: exit {code}, differing: {differ or 'none'}")
    base_ord = out.split("real atomic operations")[1]
    ok = code == 0
    try:
        for name, (side, change, expect) in MUTATIONS.items():
            if side == "verus":
                r, v = base_real, verus_mir(verus, change(COPY), scratch, end, name)
            else:
                open(real_file, "w").write(change(real_src))
                try:
                    r, v = real_mir(tokio, scratch, end, name), base_verus
                finally:
                    open(real_file, "w").write(real_src)
            code, differ, out = compare(r, v, orderings=True)
            if expect is None:
                ordering_changed = out.split("real atomic operations")[1] != base_ord
                good = code == 0 and not differ and ordering_changed
                verdict = "still agrees; ordering listing changed" if good else "UNEXPECTED"
            else:
                good = code == 1 and differ == [expect]
                verdict = f"caught in {expect}" if good else "UNEXPECTED"
            print(f"{name}: exit {code}, differing: {differ or 'none'} ({verdict})")
            if not good:
                print(out)
            ok &= good
    finally:
        open(real_file, "w").write(real_src)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
