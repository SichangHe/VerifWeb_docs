"""Apply one known-bad change to batch_semaphore.rs and check that Verus rejects it for the expected reason.

A mutation passes only if Verus reports exactly one error, of the expected kind
(postcondition/precondition), at the expected failing clause (a snippet that
Verus prints under "failed this postcondition"/"failed precondition"), in the
expected function.
Usage: python3 mutate.py VERUS   (exit 0 iff the original verifies and every mutation fails as expected)
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
    "drop_no_return": rep("        if acquired_permits > 0 {\n            self.semaphore.add_permits_locked(acquired_permits, waiters, Tracked(lk), Tracked(&mut tf));\n        } else { // VERUS: guard drop made explicit: Rust drops `waiters` when `acquired_permits == 0`\n            waiters.unlock(Tracked(lk)); // VERUS: Rust drops `waiters`\n        }",
                          "        waiters.unlock(Tracked(lk));"),
    # drop does not unlink the waiter
    "drop_no_remove": lambda s: rep(re.search(r"        let removed = waiters.w.queue.remove\(&self.node\);.*\n", s).group(0), "")(
                                rep("                self.semaphore.inst.borrow().unlink(i, &mut lk);\n", "")(s)),
    # queued cleared even on Pending
    "poll_clear_on_pending": rep("        if result.is_ready() {\n            self.queued = false;",
                                 "        self.queued = false;\n        if result.is_ready() {"),
}

# name -> (kind, function, required clause, other clauses allowed to fail in the same function).
# A clause is matched at the column Verus reports: the failing postcondition, or the called
# function for a failed precondition.
EXPECTED = {
    "master_no_close_fix": ("postcondition", "poll_acquire", "fl.value() == 0", []),
    "pre8542_fast_path": ("postcondition", "poll_acquire", "fl.value() == 0",
                          ["Poll::Ready(Ok(_)) ==> own.value() == Own::Fast"]),
    "drop_no_return": ("postcondition", "drop", "self.fl@.value() == 0", []),
    "drop_no_remove": ("precondition", "drop", "self.semaphore.inst.borrow().retire(", []),
    "poll_clear_on_pending": ("postcondition", "poll", "self.wf()", []),
}

def verify(text, verus):
    """(exit code, results line, [(kind, function, text at the reported column)])"""
    lines = text.splitlines()
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.rs"); open(p, "w").write(text)
        r = subprocess.run([verus, "--crate-type=lib", "--triggers-mode", "silent", p], capture_output=True, text=True)
        out = r.stdout + r.stderr
    m = re.search(r"verification results:: (\d+) verified, (\d+) errors", out)
    res = m.group(0) if m else (out.strip().splitlines()[-1] if out.strip() else "no output")
    errs = []
    for em in re.finditer(r"^error: (\w+) not satisfied\n\s*--> [^\n]*m\.rs:(\d+):(\d+)", out, re.M):
        ln, col = int(em.group(2)), int(em.group(3))
        fn = next((fm.group(1) for k in range(ln - 1, -1, -1)
                   if (fm := re.search(r"\bfn (\w+)", lines[k]))), "?")
        errs.append((em.group(1), fn, lines[ln - 1][col - 1:]))
    other = len(re.findall(r"^error", out, re.M)) - len(errs) - len(re.findall(r"^error: aborting", out, re.M))
    if other:
        errs.append(("other", "?", "unparsed error"))
    return r.returncode, res, errs

def as_expected(name, errs):
    kind, fn, req, extra = EXPECTED[name]
    def match(e, clause):
        return e[0] == kind and e[1] == fn and e[2].startswith(clause)
    return (any(match(e, req) for e in errs)
            and all(any(match(e, c) for c in [req] + extra) for e in errs))

def main():
    verus = sys.argv[1]
    code, res, _ = verify(SRC, verus)
    print(f"original: exit {code}: {res}")
    ok = code == 0
    for name, f in MUTATIONS.items():
        code, res, errs = verify(f(SRC), verus)
        good = code != 0 and as_expected(name, errs)
        ok &= good
        print(f"{name}: exit {code}: {res} ({'rejected as expected' if good else 'NOT AS EXPECTED'})")
        for k, fn, t in errs:
            print(f"    {k} in {fn}: {t.strip()[:70]}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
