"""Check that clients.rs keeps the real code of Tokio's batch-semaphore clients, and list what it adds.

Same method and checks as correspond.py (whose normalisation and ghost erasure
this script reuses), applied to the client functions in ENTRIES. An entry maps
one or more real functions (their bodies concatenated in the listed order) to
one Verus function; an `async fn` maps to the `poll` of its hand-written future.
Real side additionally drops `#[cfg(not(all(tokio_unstable, ..)))]` and
`#[allow(..)]` attribute lines (the item under them is compiled in).

Usage: python3 correspond_clients.py TOKIO_SRC_SYNC_DIR   (exit 0 iff no unexplained added line)
TOKIO_SRC_SYNC_DIR is tokio/src/sync of fc0d151 + semaphore-close-fix.patch.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from correspond import norm, balanced, real_lines, verus_lines, allowed

# (label, [(real file, impl regex, fn regex), ...], (Verus module regex, impl regex, fn regex))
S, M, R, Q = "semaphore.rs", "mutex.rs", "rwlock.rs", "mpsc/"
ENTRIES = [
    ("semaphore: Semaphore::new", [(S, r"impl Semaphore \{", r"new\(permits")], ("semaphore", r"impl Semaphore \{", r"new\(permits")),
    ("semaphore: available_permits", [(S, r"impl Semaphore \{", r"available_permits\b")], ("semaphore", r"impl Semaphore \{", r"available_permits\b")),
    ("semaphore: add_permits", [(S, r"impl Semaphore \{", r"add_permits\b")], ("semaphore", r"impl Semaphore \{", r"add_permits\b")),
    ("semaphore: forget_permits", [(S, r"impl Semaphore \{", r"forget_permits\b")], ("semaphore", r"impl Semaphore \{", r"forget_permits\b")),
    ("semaphore: acquire_many (async)", [(S, r"impl Semaphore \{", r"acquire_many\(")], ("semaphore", r"impl<'a> AcquireManyFuture<'a> \{\s*pub fn", r"poll\(")),
    ("semaphore: try_acquire_many", [(S, r"impl Semaphore \{", r"try_acquire_many\(")], ("semaphore", r"impl Semaphore \{", r"try_acquire_many\(")),
    ("semaphore: try_acquire_many_owned", [(S, r"impl Semaphore \{", r"try_acquire_many_owned\(")], ("semaphore", r"impl Semaphore \{", r"try_acquire_many_owned\(")),
    ("semaphore: close", [(S, r"impl Semaphore \{", r"close\(")], ("semaphore", r"impl Semaphore \{", r"close\(")),
    ("semaphore: is_closed", [(S, r"impl Semaphore \{", r"is_closed\(")], ("semaphore", r"impl Semaphore \{", r"is_closed\(")),
    ("semaphore: SemaphorePermit::forget", [(S, r"impl<'a> SemaphorePermit<'a> \{", r"forget\(")], ("semaphore", r"impl<'a> SemaphorePermit<'a> \{\n    pub fn forget", r"forget\(")),
    ("semaphore: SemaphorePermit::merge", [(S, r"impl<'a> SemaphorePermit<'a> \{", r"merge\(")], ("semaphore", r"impl<'a> SemaphorePermit<'a> \{\n    pub fn forget", r"merge\(")),
    ("semaphore: SemaphorePermit::split", [(S, r"impl<'a> SemaphorePermit<'a> \{", r"split\(")], ("semaphore", r"impl<'a> SemaphorePermit<'a> \{\n    pub fn forget", r"split\(")),
    ("semaphore: SemaphorePermit drop", [(S, r"impl Drop for SemaphorePermit<'_> \{", r"drop\(")], ("semaphore", r"impl<'a> SemaphorePermit<'a> \{\n    pub fn forget", r"drop\(&mut self\)")),
    ("semaphore: OwnedSemaphorePermit::forget", [(S, r"impl OwnedSemaphorePermit \{", r"forget\(")], ("semaphore", r"impl OwnedSemaphorePermit \{\n    pub fn forget", r"forget\(")),
    ("semaphore: OwnedSemaphorePermit::merge", [(S, r"impl OwnedSemaphorePermit \{", r"merge\(")], ("semaphore", r"impl OwnedSemaphorePermit \{\n    pub fn forget", r"merge\(")),
    ("semaphore: OwnedSemaphorePermit::split", [(S, r"impl OwnedSemaphorePermit \{", r"split\(")], ("semaphore", r"impl OwnedSemaphorePermit \{\n    pub fn forget", r"split\(")),
    ("semaphore: OwnedSemaphorePermit drop", [(S, r"impl Drop for OwnedSemaphorePermit \{", r"drop\(")], ("semaphore", r"impl OwnedSemaphorePermit \{\n    pub fn forget", r"drop\(&mut self\)")),

    ("mutex: Mutex::new", [(M, r"impl<T: \?Sized> Mutex<T> \{", r"new\(t")], ("mutex", r"impl Mutex \{\n    pub fn new", r"new\(")),
    ("mutex: lock + acquire (async)", [(M, r"impl<T: \?Sized> Mutex<T> \{", r"acquire\(&self\)"), (M, r"impl<T: \?Sized> Mutex<T> \{", r"lock\(&self\)")], ("mutex", r"impl<'a> LockFuture<'a> \{\n    pub fn poll", r"poll\(")),
    ("mutex: try_lock", [(M, r"impl<T: \?Sized> Mutex<T> \{", r"try_lock\(")], ("mutex", r"impl Mutex \{\n    pub fn new", r"try_lock\(")),
    ("mutex: try_lock_owned", [(M, r"impl<T: \?Sized> Mutex<T> \{", r"try_lock_owned\(")], ("mutex", r"impl Mutex \{\n    pub fn new", r"try_lock_owned\(")),
    ("mutex: MutexGuard::skip_drop", [(M, r"impl<'a, T: \?Sized> MutexGuard<'a, T> \{", r"skip_drop\(")], ("mutex", r"impl<'a> MutexGuard<'a> \{\n    fn skip_drop", r"skip_drop\(")),
    ("mutex: MutexGuard::map", [(M, r"impl<'a, T: \?Sized> MutexGuard<'a, T> \{", r"map<")], ("mutex", r"impl<'a> MutexGuard<'a> \{\n    fn skip_drop", r"map\(")),
    ("mutex: MutexGuard drop", [(M, r"impl<T: \?Sized> Drop for MutexGuard<'_, T> \{", r"drop\(")], ("mutex", r"impl<'a> MutexGuard<'a> \{\n    fn skip_drop", r"drop\(&mut self\)")),
    ("mutex: OwnedMutexGuard drop", [(M, r"impl<T: \?Sized> Drop for OwnedMutexGuard<T> \{", r"drop\(")], ("mutex", r"impl OwnedMutexGuard \{\s*pub fn", r"drop\(&mut self\)")),
    ("mutex: MappedMutexGuard drop", [(M, r"impl<'a, T: \?Sized> Drop for MappedMutexGuard<'a, T> \{", r"drop\(")], ("mutex", r"impl<'a> MappedMutexGuard<'a> \{\s*pub fn", r"drop\(&mut self\)")),

    ("rwlock: RwLock::new", [(R, r"impl<T: \?Sized> RwLock<T> \{", r"new\(value")], ("rwlock", r"impl RwLock \{\n    pub fn new", r"new\(")),
    ("rwlock: with_max_readers", [(R, r"impl<T: \?Sized> RwLock<T> \{", r"with_max_readers\(")], ("rwlock", r"impl RwLock \{\n    pub fn new", r"with_max_readers\(")),
    ("rwlock: read + write (async)", [(R, r"impl<T: \?Sized> RwLock<T> \{", r"read\(&self\)"), (R, r"impl<T: \?Sized> RwLock<T> \{", r"write\(&self\)")], ("rwlock", r"impl<'a> RwFuture<'a> \{\n    pub fn poll", r"poll\(")),
    ("rwlock: try_read", [(R, r"impl<T: \?Sized> RwLock<T> \{", r"try_read\(")], ("rwlock", r"impl RwLock \{\n    pub fn new", r"try_read\(")),
    ("rwlock: try_write", [(R, r"impl<T: \?Sized> RwLock<T> \{", r"try_write\(")], ("rwlock", r"impl RwLock \{\n    pub fn new", r"try_write\(")),
    ("rwlock: RwLockReadGuard drop", [("rwlock/read_guard.rs", r"impl<'a, T: \?Sized> Drop for RwLockReadGuard", r"drop\(")], ("rwlock", r"impl<'a> RwLockReadGuard<'a> \{\s*pub fn", r"drop\(")),
    ("rwlock: RwLockWriteGuard::skip_drop", [("rwlock/write_guard.rs", r"impl<'a, T: \?Sized> RwLockWriteGuard<'a, T> \{", r"skip_drop\(")], ("rwlock", r"impl<'a> RwLockWriteGuard<'a> \{\n    fn skip_drop", r"skip_drop\(")),
    ("rwlock: RwLockWriteGuard::downgrade", [("rwlock/write_guard.rs", r"impl<'a, T: \?Sized> RwLockWriteGuard<'a, T> \{", r"downgrade\(self")], ("rwlock", r"impl<'a> RwLockWriteGuard<'a> \{\n    fn skip_drop", r"downgrade\(")),
    ("rwlock: RwLockWriteGuard drop", [("rwlock/write_guard.rs", r"impl<'a, T: \?Sized> Drop for RwLockWriteGuard", r"drop\(")], ("rwlock", r"impl<'a> RwLockWriteGuard<'a> \{\n    fn skip_drop", r"drop\(&mut self\)")),
    ("rwlock: OwnedRwLockReadGuard drop", [("rwlock/owned_read_guard.rs", r"Drop for OwnedRwLockReadGuard", r"drop\(")], ("rwlock", r"impl OwnedRwLockReadGuard \{\s*pub fn", r"drop\(")),
    ("rwlock: OwnedRwLockWriteGuard::skip_drop", [("rwlock/owned_write_guard.rs", r"impl<T: \?Sized> OwnedRwLockWriteGuard<T> \{", r"skip_drop\(")], ("rwlock", r"impl OwnedRwLockWriteGuard \{\n    fn skip_drop", r"skip_drop\(")),
    ("rwlock: OwnedRwLockWriteGuard::downgrade", [("rwlock/owned_write_guard.rs", r"impl<T: \?Sized> OwnedRwLockWriteGuard<T> \{", r"downgrade\(self")], ("rwlock", r"impl OwnedRwLockWriteGuard \{\n    fn skip_drop", r"downgrade\(")),
    ("rwlock: OwnedRwLockWriteGuard drop", [("rwlock/owned_write_guard.rs", r"Drop for OwnedRwLockWriteGuard", r"drop\(")], ("rwlock", r"impl OwnedRwLockWriteGuard \{\n    fn skip_drop", r"drop\(&mut self\)")),

    ("mpsc: chan::Semaphore::add_permit", [(Q + "chan.rs", r"impl Semaphore for bounded::Semaphore \{", r"add_permit\(")], ("chan", r"impl Semaphore \{", r"add_permit\(")),
    ("mpsc: chan::Semaphore::is_idle", [(Q + "chan.rs", r"impl Semaphore for bounded::Semaphore \{", r"is_idle\(")], ("chan", r"impl Semaphore \{", r"is_idle\(")),
    ("mpsc: chan::Semaphore::close", [(Q + "chan.rs", r"impl Semaphore for bounded::Semaphore \{", r"close\(")], ("chan", r"impl Semaphore \{", r"close\(")),
    ("mpsc: chan::Semaphore::is_closed", [(Q + "chan.rs", r"impl Semaphore for bounded::Semaphore \{", r"is_closed\(")], ("chan", r"impl Semaphore \{", r"is_closed\(")),
    ("mpsc: chan::channel", [(Q + "chan.rs", r"", r"channel<T, S: Semaphore>\(semaphore"), (Q + "chan.rs", r"", r"channel_from_list<")], ("chan", r"", r"channel<T>\(")),
    ("mpsc: Tx::semaphore", [(Q + "chan.rs", r"impl<T, S> Tx<T, S> \{", r"semaphore\(")], ("chan", r"impl<T> Tx<T> \{\n    pub fn semaphore", r"semaphore\(")),
    ("mpsc: Tx::send + Chan::send", [(Q + "chan.rs", r"impl<T, S> Tx<T, S> \{", r"send\("), (Q + "chan.rs", r"impl<T, S> Chan<T, S> \{", r"send\(")], ("chan", r"impl<T> Tx<T> \{\n    pub fn semaphore", r"send\(")),
    ("mpsc: Tx::wake_rx", [(Q + "chan.rs", r"impl<T, S> Tx<T, S> \{", r"wake_rx\(")], ("chan", r"impl<T> Tx<T> \{\n    pub fn semaphore", r"wake_rx\(")),
    ("mpsc: Rx::close", [(Q + "chan.rs", r"impl<T, S: Semaphore> Rx<T, S> \{", r"close\(")], ("chan", r"impl<T> Rx<T> \{\n    pub fn close", r"close\(")),
    ("mpsc: Rx::recv", [(Q + "chan.rs", r"impl<T, S: Semaphore> Rx<T, S> \{", r"recv\(")], ("chan", r"impl<T> Rx<T> \{\n    pub fn close", r"recv\(")),
    ("mpsc: Rx drop (Guard::drain)", [(Q + "chan.rs", r"impl<'a, T, S: Semaphore> Guard<'a, T, S> \{", r"drain\(")], ("chan", r"impl<T> Rx<T> \{\n    pub fn close", r"drain\(")),
    ("mpsc: Rx drop", [(Q + "chan.rs", r"impl<T, S: Semaphore> Drop for Rx<T, S> \{", r"drop\(")], ("chan", r"impl<T> Rx<T> \{\n    pub fn close", r"drop\(")),
    ("mpsc: channel", [(Q + "bounded.rs", r"", r"channel<T>\(buffer")], ("bounded", r"", r"channel<T>\(buffer")),
    ("mpsc: Sender::max_capacity", [(Q + "bounded.rs", r"impl<T> Sender<T> \{", r"max_capacity\(")], ("bounded", r"impl<T> Sender<T> \{\n    pub fn max_capacity", r"max_capacity\(")),
    ("mpsc: reserve + reserve_inner (async)", [(Q + "bounded.rs", r"impl<T> Sender<T> \{", r"reserve_inner\("), (Q + "bounded.rs", r"impl<T> Sender<T> \{", r"reserve\(&self\)")], ("bounded", r"impl<'a, T> ReserveFuture<'a, T> \{\n    pub fn poll", r"poll\(")),
    ("mpsc: WakeReceiverOnDrop drop", [(Q + "bounded.rs", r"impl<T> Drop for WakeReceiverOnDrop", r"drop\(")], ("bounded", r"impl<'a, T> WakeReceiverOnDrop<'a, T> \{", r"drop\(")),
    ("mpsc: Sender::send (async)", [(Q + "bounded.rs", r"impl<T> Sender<T> \{", r"send\(&self, value: T\)")], ("bounded", r"impl<'a, T> SendFuture<'a, T> \{\s*pub fn", r"poll\(")),
    ("mpsc: Sender::try_send", [(Q + "bounded.rs", r"impl<T> Sender<T> \{", r"try_send\(")], ("bounded", r"impl<T> Sender<T> \{\n    pub fn max_capacity", r"try_send\(")),
    ("mpsc: Permit::send", [(Q + "bounded.rs", r"impl<T> Permit<'_, T> \{", r"send\(self")], ("bounded", r"impl<'a, T> Permit<'a, T> \{\s*pub fn", r"send\(self")),
    ("mpsc: Permit drop", [(Q + "bounded.rs", r"impl<T> Drop for Permit<'_, T> \{", r"drop\(")], ("bounded", r"impl<'a, T> Permit<'a, T> \{\s*pub fn", r"drop\(")),
    ("mpsc: Receiver::close", [(Q + "bounded.rs", r"impl<T> Receiver<T> \{", r"close\(")], ("bounded", r"impl<T> Receiver<T> \{\n    pub fn close", r"close\(")),
]

# Added lines specific to the clients that need no per-line marker.
ALLOWED_CLIENTS = [
    ("`Poll::Pending` arm that keeps the inner future (`.await` written out; block carries a VERUS marker)",
     r"^(Poll::Pending => \{|Poll::Pending|Poll::Ready\(r\) => \{)$"),
    ("match arms of a rewritten `?`/`unwrap_or_else` (block carries a VERUS marker)",
     r"^(Ok\(\(\)\) => \{\},|Err\(e\) => return Poll::Ready\(Err\(e\)\),)$"),
    ("`else` branch of a rewritten `if` (the `if` carries a VERUS marker)", r"^\} else \{$"),
]

def find_fn(src, start_rx, fn_rx):
    m0 = re.search(start_rx, src) if start_rx else None
    if start_rx and m0 is None:
        raise SystemExit(f"not found: {start_rx}")
    pos = m0.start() if m0 else 0
    m = re.compile(r"\n\s*(pub(\([\w:]+\))? )?(const )?(async )?fn " + fn_rx).search(src, pos)
    if m is None:
        raise SystemExit(f"not found: fn {fn_rx} after {start_rx}")
    return m

def mask(src):
    """Blank out `//` comments (same length) so that brackets in comments do not count."""
    return re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), src)

def real_body(src, impl_rx, fn_rx):
    ms = mask(src)
    m = find_fn(ms, impl_rx, fn_rx)
    i = ms.index("{", balanced(ms, ms.index("(", m.start()), "(", ")"))
    return src[i:balanced(ms, i)]

def verus_body(src, mod_rx, impl_rx, fn_rx):
    mm = re.search(r"\npub mod " + mod_rx + r" \{", src)
    if mm is None:
        raise SystemExit(f"module not found: {mod_rx}")
    orig = src[mm.start():]
    sub = mask(orig)
    m = find_fn(sub, impl_rx, fn_rx)
    after = balanced(sub, sub.index("(", m.start()), "(", ")")
    first = sub.index("{", after)
    if re.search(r"\b(requires|ensures)\b", sub[after:first]):
        first = after + re.search(r"\n\s*\{\s*\n", sub[after:]).start()
        first = sub.index("{", first)
    return orig[first:balanced(sub, first)]

def clean_real(lines):
    """Drop compiled-in cfg/allow attribute lines, and expand `macro_rules! NAME { () => { BODY }; }`
    at each `NAME!();` (as rustc does), removing the definition."""
    lines = [l for l in lines
             if not l.startswith("#[cfg(not(all(tokio_unstable") and not l.startswith("#[allow(")]
    out, k = [], 0
    macros = {}
    while k < len(lines):
        m = re.match(r"macro_rules! (\w+) \{$", lines[k])
        if m and lines[k + 1] == "() => {":
            j = k + 2
            body = []
            while lines[j] != "};":  # real_lines() already dropped lone `{`/`}` lines
                body.append(lines[j]); j += 1
            k = j + 1
            macros[m.group(1)] = body
            continue
        m = re.match(r"(\w+)!\(\);$", lines[k])
        if m and m.group(1) in macros:
            out += macros[m.group(1)]
        else:
            out.append(lines[k])
        k += 1
    return out

def allowed_client(l):
    for cat, rx in ALLOWED_CLIENTS:
        if re.search(rx, l):
            return cat
    return allowed(l)

def main():
    sync = sys.argv[1]
    ver = open(os.path.join(HERE, "clients.rs")).read()
    srcs = {}
    tot_real = tot_kept = tot_added = tot_marked = tot_allowed = unexplained = 0
    cats = {}
    for label, reals, (mod_rx, impl_rx, fn_rx) in ENTRIES:
        r = []
        for f, irx, frx in reals:
            if f not in srcs:
                srcs[f] = open(os.path.join(sync, f)).read()
            r += clean_real(real_lines(real_body(srcs[f], irx, frx)))
        v = verus_lines(verus_body(ver, mod_rx, impl_rx, fn_rx))
        pos, missing, used = 0, [], set()
        for l in r:
            for k in range(pos, len(v)):
                if v[k][0] == l:
                    used.add(k); pos = k + 1
                    break
            else:
                missing.append(l)
        added = [(l, mk) for k, (l, mk) in enumerate(v) if k not in used]
        print(f"{label}: {len(r) - len(missing)}/{len(r)} real lines kept in order; {len(added)} lines added")
        for l in missing:
            print(f"    changed: {l}")
        for l, mk in added:
            if mk:
                tot_marked += 1
                print(f"    added (VERUS marker): {l}")
            elif (c := allowed_client(l)):
                tot_allowed += 1; cats[c] = cats.get(c, 0) + 1
                print(f"    added (allowed: {c}): {l}")
            else:
                unexplained += 1
                print(f"    added UNEXPLAINED: {l}")
        tot_real += len(r); tot_kept += len(r) - len(missing); tot_added += len(added)
    print(f"total: {tot_kept}/{tot_real} real lines kept verbatim in order; {tot_real - tot_kept} changed ({len(ENTRIES)} entries)")
    print(f"added: {tot_added} ({tot_marked} marked, {tot_allowed} allowed, {unexplained} unexplained)")
    for c, n in cats.items():
        print(f"    allowed {n}: {c}")
    sys.exit(1 if unexplained else 0)

if __name__ == "__main__":
    main()
