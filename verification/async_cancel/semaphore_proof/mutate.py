"""Apply one known-bad change to batch_semaphore.rs and check that Verus rejects it.

Usage: python3 mutate.py VERUS   (exit 0 iff the original verifies and every mutation fails)
"""
import os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "batch_semaphore.rs")).read()

def cut(start, end):
    """Remove the text from the first `start` through the following `end` (inclusive)."""
    def f(s):
        i = s.index(start); j = s.index(end, i) + len(end)
        return s[:i] + s[j:]
    return f

def rep(a, b):
    def f(s):
        assert a in s, a
        return s.replace(a, b, 1)
    return f

MUTATIONS = {
    # master fc0d151 without semaphore-close-fix.patch
    "master_no_close_fix": cut("            if acquired > 0 {\n                let tracked mut tf = take_fl(fl);",
                               "                proof { *fl = tf; }\n            }\n"),
    # #8542's parent with master's coop order: fast path neither records state nor sets queued
    "pre8542_fast_path": cut("                            let tracked mut tf = take_fl(fl);\n                            let tracked mut to = take_own(own);\n                            atomic_with_ghost!(&node.state => store(0);",
                             "                            *queued = true;\n"),
    # drop does not return assigned permits
    "drop_no_return": rep("        if acquired_permits > 0 {\n            self.semaphore.add_permits_locked(acquired_permits, waiters, Tracked(lk), Tracked(&mut tf));\n        } else {\n            waiters.unlock(Tracked(lk)); // VERUS: Rust drops `waiters`\n        }",
                          "        waiters.unlock(Tracked(lk));"),
    # drop does not unlink the waiter
    "drop_no_remove": lambda s: rep("        let removed = waiters.w.queue.remove(&self.node);\n", "")(
                                rep("                self.semaphore.inst.borrow().unlink(i, &mut lk);\n", "")(s)),
    # queued cleared even on Pending
    "poll_clear_on_pending": rep("        if result.is_ready() {\n            self.queued = false;",
                                 "        self.queued = false;\n        if result.is_ready() {"),
}

def verify(text, verus):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.rs"); open(p, "w").write(text)
        r = subprocess.run([verus, "--crate-type=lib", p], capture_output=True, text=True)
        out = r.stdout + r.stderr
        m = re.search(r"verification results:: (\d+) verified, (\d+) errors", out)
        return r.returncode, (m.group(0) if m else out.strip().splitlines()[-1] if out.strip() else "no output")

def main():
    verus = sys.argv[1]
    code, res = verify(SRC, verus)
    print(f"original: exit {code}: {res}")
    ok = code == 0
    for name, f in MUTATIONS.items():
        code, res = verify(f(SRC), verus)
        print(f"{name}: exit {code}: {res} ({'rejected' if code else 'ACCEPTED'})")
        ok &= code != 0
    sys.exit(0 if ok else 1)

main()
