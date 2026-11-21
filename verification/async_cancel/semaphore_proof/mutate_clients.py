"""Apply one known-bad change to clients.rs (or batch_semaphore.rs) and check that Verus rejects it for the expected reason.

As in mutate.py: a mutation passes only if every Verus error is of the expected
kind (postcondition/precondition/invariant at the end of an `open_atomic_invariant!` block), in the expected file and function, at the
expected clause (the text at the column Verus reports), and at least one error
is at the required clause.
Usage: python3 mutate_clients.py VERUS   (exit 0 iff the original verifies and every mutation fails as expected)
"""
import os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ("clients.rs", "batch_semaphore.rs")
SRC = {f: open(os.path.join(HERE, f)).read() for f in FILES}

def in_fn(header, a, b):
    """Replace the first `a` after the first `header` (a line that starts the function) by `b`."""
    def f(s):
        i = s.index(header)
        j = s.index(a, i)
        return s[:j] + b + s[j + len(a):]
    return f

def seq(*fs):
    def f(s):
        for g in fs:
            s = g(s)
        return s
    return f

RECV = "    pub fn recv(&mut self, cx: &mut Context<'_>, Tracked(op)"
PERMIT_SEND = "    pub fn send(self, value: T, Tracked(op): Tracked<&mut ll::Sem::fl>)"
PERMIT_DROP = "        let semaphore = self.chan.semaphore();\n\n        // Add the permit back to the semaphore"
TRY_SEND = "    pub fn try_send(&self, message: T, Tracked(op)"
WG_SKIP = "    fn skip_drop(self) -> (r: WriteInner<'a>)"
WG_DROP = "    /// `impl Drop for RwLockWriteGuard<'a, T>`."
SP_FORGET = "impl<'a> SemaphorePermit<'a> {\n    pub fn forget(self)"
SP_MERGE = "    pub fn merge(&mut self, other: Self)"  # first: SemaphorePermit
SP_SPLIT_HDR = "    pub fn split(&mut self, n: usize)"  # first: SemaphorePermit
RAW_POP = "    pub fn pop(&mut self, tx: &RawTx<T>, Tracked(len)"
RAW_POP_VALUE = "r matches Some(Read::Value(_)) ==> old(len).len() >= 1 && len.len() == old(len).len() - 1,"
RAW_CHANNEL = "pub fn raw_channel<T>()"

def master_no_close_fix(s):
    i = s.index("            if acquired > 0 {\n                let tracked mut tf = take_fl(fl);")
    end = "                proof { *fl = tf; }\n            }\n"
    j = s.index(end, i) + len(end)
    return s[:i] + s[j:]

# name -> (file, mutation)
MUTATIONS = {
    # mpsc: recv takes a value but does not return its slot permit (the channel can never become idle again)
    "mpsc_recv_no_add_permit": ("clients.rs", in_fn(RECV, "                self.inner.semaphore.add_permit(Tracked(op));\n", "")),
    # mpsc: a dropped Permit does not return its slot
    "mpsc_permit_drop_no_release": ("clients.rs", in_fn(PERMIT_DROP, "        semaphore.add_permit(Tracked(self.tok.borrow_mut()));\n", "")),
    # mpsc: Permit::send runs the Permit's drop after enqueueing (the effect of #8559, here without a panic)
    "mpsc_permit_send_then_drop": ("clients.rs", seq(
        in_fn(PERMIT_SEND, "        std::mem::forget(this); // VERUS: `mem::forget(self);`\n", ""),
        in_fn(PERMIT_SEND, "        chan.send(value, Tracked(op));\n", "        chan.send(value, Tracked(op));\n        this.drop();\n"))),
    # mpsc: try_send acquires a slot but does not enqueue the message
    "mpsc_try_send_no_push": ("clients.rs", in_fn(TRY_SEND, "        self.chan.send(message, Tracked(op));\n", "")),
    # the close-path leak: batch_semaphore.rs without semaphore-close-fix.patch, checked with all clients
    "master_no_close_fix": ("batch_semaphore.rs", master_no_close_fix),
    # RwLockWriteGuard::downgrade also runs the write guard's drop (#2941, fixed by #2957)
    "rwlock_downgrade_drops_write_guard": ("clients.rs", in_fn(WG_SKIP,
        "        let me = self; // VERUS: `mem::ManuallyDrop::new(self)`: the guard's drop is not run (no call to `drop` follows)\n",
        "        let mut me = self;\n        me.drop();\n")),
    # RwLockWriteGuard's drop returns one permit instead of all it holds
    "rwlock_write_drop_releases_one": ("clients.rs", in_fn(WG_DROP, "self.s.release(self.permits_acquired as usize,", "self.s.release(1,")),
    # SemaphorePermit::forget without `permits = 0`: the drop then returns the forgotten permits
    "semaphore_forget_keeps_count": ("clients.rs", in_fn(SP_FORGET, "        this.permits = 0; // VERUS: `self.permits = 0;` on the local\n", "")),
    # SemaphorePermit::merge without `other.permits = 0`: other's drop returns the merged permits again
    "semaphore_merge_no_zero_other": ("clients.rs", in_fn(SP_MERGE, "        other.permits = 0;\n", "")),
    # SemaphorePermit::split without subtracting: both permits own the split-off permits
    "semaphore_split_no_subtract": ("clients.rs", in_fn(SP_SPLIT_HDR,
        "        self.permits = self.permits - n; // VERUS: `self.permits -= n;` (Verus has no compound assignment to a field)\n", "")),
    # mpsc list: a popped value stays in the list (count not decremented), so it can be popped again (double pop)
    "mpsc_list_double_pop": ("clients.rs", in_fn(RAW_POP, RAW_POP_VALUE,
        "r matches Some(Read::Value(_)) ==> old(len).len() >= 1 && len.len() == old(len).len(),")),
    # mpsc list: pop may return a value from an empty list (a pop with no push)
    "mpsc_list_pop_without_push": ("clients.rs", in_fn(RAW_POP, RAW_POP_VALUE,
        "r matches Some(Read::Value(_)) ==> (old(len).len() == 0 && len.len() == 0) || (old(len).len() >= 1 && len.len() == old(len).len() - 1),")),
    # mpsc list: a new list already holds a value that no one pushed
    "mpsc_list_starts_nonempty": ("clients.rs", in_fn(RAW_CHANNEL, "r.2@.len() == 0,", "r.2@.len() == 1,")),
}

# name -> (kind, file, function, required clause, other clauses allowed in the same function)
EXPECTED = {
    "mpsc_recv_no_add_permit": ("postcondition", "clients.rs", "recv", "holds(*op, &self.inner.semaphore.semaphore, 0)", []),
    "mpsc_permit_drop_no_release": ("postcondition", "clients.rs", "drop", "self.tok@.value() == 0", []),
    "mpsc_permit_send_then_drop": ("precondition", "clients.rs", "send", "this.drop()", []),
    "mpsc_try_send_no_push": ("postcondition", "clients.rs", "try_send", "holds(*op, &self.chan.inner.semaphore.semaphore, 0)", []),
    "master_no_close_fix": ("postcondition", "batch_semaphore.rs", "poll_acquire", "fl.value() == 0", []),
    "rwlock_downgrade_drops_write_guard": ("postcondition", "clients.rs", "skip_drop", "r.wf()", []),
    "rwlock_write_drop_releases_one": ("precondition", "clients.rs", "drop", "self.s.release(1,", []),
    "semaphore_forget_keeps_count": ("precondition", "clients.rs", "forget", "this.drop()", []),
    "semaphore_merge_no_zero_other": ("precondition", "clients.rs", "merge", "other.drop()", []),
    "semaphore_split_no_subtract": ("postcondition", "clients.rs", "split", "self.wf()", ["Some(p) ==> p.wf()"]),
    "mpsc_list_double_pop": ("invariant", "clients.rs", "pop", "open_atomic_invariant!(tx.inv.borrow()", []),
    "mpsc_list_pop_without_push": ("precondition", "clients.rs", "pop", "move_permits(tx.sem_inst.borrow(), &mut tok, op, 1)", []),
    "mpsc_list_starts_nonempty": ("precondition", "clients.rs", "list_channel", "AtomicInvariant::new(", []),
}

def verify(texts, verus):
    """(exit code, results line, [(kind, file, function, text at the reported column)])"""
    with tempfile.TemporaryDirectory() as d:
        for f, t in texts.items():
            open(os.path.join(d, f), "w").write(t)
        r = subprocess.run([verus, "--crate-type=lib", "--triggers-mode", "silent", "clients.rs"],
                           capture_output=True, text=True, cwd=d)
        out = r.stdout + r.stderr
    m = re.search(r"verification results:: (\d+) verified, (\d+) errors", out)
    res = m.group(0) if m else (out.strip().splitlines()[-1] if out.strip() else "no output")
    errs = []
    for em in re.finditer(r"^error: (?:(\w+) not satisfied|Cannot show (invariant) holds at end of block)\n\s*--> ([\w.]+):(\d+):(\d+)", out, re.M):
        f, ln, col = em.group(3), int(em.group(4)), int(em.group(5))
        lines = texts[f].splitlines()
        fn = next((fm.group(1) for k in range(ln - 1, -1, -1)
                   if (fm := re.search(r"\bfn (\w+)", lines[k]))), "?")
        errs.append((em.group(1) or em.group(2), f, fn, lines[ln - 1][col - 1:]))
    other = len(re.findall(r"^error", out, re.M)) - len(errs) - len(re.findall(r"^error: aborting", out, re.M))
    if other:
        errs.append(("other", "?", "?", "unparsed error"))
    return r.returncode, res, errs

def as_expected(name, errs):
    kind, file, fn, req, extra = EXPECTED[name]
    def match(e, clause):
        return e[0] == kind and e[1] == file and e[2] == fn and e[3].startswith(clause)
    return (any(match(e, req) for e in errs)
            and all(any(match(e, c) for c in [req] + extra) for e in errs))

def main():
    verus = sys.argv[1]
    code, res, _ = verify(SRC, verus)
    print(f"original: exit {code}: {res}")
    ok = code == 0
    for name, (f, mut) in MUTATIONS.items():
        texts = dict(SRC)
        texts[f] = mut(SRC[f])
        assert texts[f] != SRC[f], name
        code, res, errs = verify(texts, verus)
        good = code != 0 and as_expected(name, errs)
        ok &= good
        print(f"{name}: exit {code}: {res} ({'rejected as expected' if good else 'NOT AS EXPECTED'})")
        for k, fl, fn, t in errs:
            print(f"    {k} in {fl} {fn}: {t.strip()[:70]}")
    sys.exit(0 if ok else 1)

main()
