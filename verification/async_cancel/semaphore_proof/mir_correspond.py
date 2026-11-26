"""Compare the compiled MIR of real Tokio's batch semaphore with the MIR of the Verus copy.

Inputs
- REAL.mir: `rustc --emit=mir` of Tokio fc0d151 + semaphore-close-fix.patch (crate `tokio`, feature `sync`)
- VERUS.mir: `verus --compile --no-verify --emit=mir` of batch_semaphore.rs. Verus erases ghost code
  before code generation, so this is the executable code whose ghost-annotated source was verified
Both must come from the same rustc (Verus pins 1.91.0).

Method: symbolic execution of each covered function on both sides, over every path through its
control-flow graph, with each block visited at most BOUND times per path (loops unrolled). A path
yields a trace of events:
- atomic: op, target place, value arguments (memory orderings removed and listed separately)
- lock, unlock (real: guard dropped or moved; Verus: explicit `unlock`), list ops, waker ops
- call: covered functions and library calls, with symbolic arguments
- write: stores through references (e.g. `*queued = true`)
- branch: the symbolic condition and the arm taken; assert: a condition that must hold
- return: the symbolic return value
Values are terms over parameters and earlier events' results (`v3` = result of event 3).
References and dereferences are dropped from terms (place paths only), so `Pin<&mut Waiter>`,
`&Arc<Waiter>` and an inline `Waiter` name the same node. Drop flags and other locals that hold
constants along a path are evaluated, so their branches disappear.

The script prints, per function, whether the two trace sets are equal; otherwise the hunks
that differ. Known differences are whole-trace rewrites in KNOWN, each with a reason; any other
difference, or a KNOWN rule that no longer fires, makes the script exit 1.

Trusted stub mapping (STUBS below): which real library calls and which Verus stand-ins name the
same operation, e.g. real `UnsafeCell::with_mut(waker, closure at line 271)` = Verus
`WakerCell::take(waker)`. The stand-ins' behaviour is trusted as before; this script only
checks that the code calls them at the same places with the same arguments.

Usage: python3 -I mir_correspond.py REAL.mir VERUS.mir [--orderings] [--bound N] [--only FN]
"""
import difflib
import re
import sys

BOUND = 3

IMPL_R = r"^fn batch_semaphore::<impl at tokio/src/sync/batch_semaphore\.rs:\d+:\d+: \d+:\d+>::"
IMPL_V = r"^fn <impl at [^:>]*\.rs:\d+:\d+: \d+:\d+>::"
# name -> (real header regex, Verus header regex)
FUNCS = {
    "Semaphore::new": (r"new\(_1: usize\) -> batch_semaphore::Semaphore", r"new\(_1: usize, _2: vstd::prelude::Ghost<bool>"),
    "release": (r"release\(_1: &batch_semaphore::Semaphore", r"release\(_1: &Semaphore"),
    "close": (r"close\(_1: &batch_semaphore::Semaphore", r"close\(_1: &Semaphore"),
    "try_acquire": (r"try_acquire\(_1:", r"try_acquire\(_1:"),
    "add_permits_locked": (r"add_permits_locked\(_1:", r"add_permits_locked\(_1:"),
    "forget_permits": (r"forget_permits\(_1:", r"forget_permits\(_1:"),
    "poll_acquire": (r"poll_acquire\(_1:", r"poll_acquire\(_1:"),
    "Waiter::new": (r"new\(_1: usize\) -> batch_semaphore::Waiter", r"new\(_1: usize, _2: vstd::prelude::Tracked<Sem::Instance>"),
    "assign_permits": (r"assign_permits\(_1:", r"assign_permits\(_1:"),
    "Acquire::poll": (r"poll\(_1: Pin<&mut batch_semaphore::Acquire", r"poll\(_1: &mut Acquire"),
    "Acquire::new": (r"new\(_1: &batch_semaphore::Semaphore, _2: usize\) -> batch_semaphore::Acquire", r"new\(_1: &Semaphore, _2: usize\) -> Acquire"),
    "Acquire::drop": (r"drop\(_1: &mut batch_semaphore::Acquire", r"drop\(_1: &mut Acquire"),
}

# Known differences, as rewrites of whole traces (events joined by " | "), applied before comparing:
# (function, side, regex, replacement, reason). Each rule must fire at least once, and after
# rewriting the trace sets must be equal. MIR_CORRESPOND.md argues why each is harmless.
KNOWN = [
    ("Semaphore::new", "verus",
     r"\| (mutex_new W.*?) \| (atomic_new .*?) \| return \(Semaphore \{ waiters: Mutex \{ rw: RW\((.*?)\) \}, (permits: .*) \}, GHOST\)$",
     r"| \2 | \1 | return Semaphore { waiters: Mutex(\3), \4 }",
     "constructor: the copy builds the wait-list mutex (a vstd RwLock in a Mutex struct) before the counter "
     "and also returns the ghost budget; same initial values; the object is not shared yet"),
    ("add_permits_locked", "real",
     r"\| (assert Eq\(_2, 0\) 1) \| (unlock _3) \| return _0$", r"| \2 | \1 | return _0",
     "rem == 0 on entry: real drops the guard at scope end after `assert_eq!(rem, 0)`; the copy unlocks just "
     "before that assert, which reads only a local"),
    ("Waiter::new", "real",
     r"\| lib Pointers::new \| return Waiter \{ (state: Atomic\(_1\), waker: WakerCell\(None\)), pointers: new1, _p: PhantomPinned \}$",
     r"| return Waiter { \1 }",
     "intrusive-list `pointers` and `PhantomPinned` fields are absent in the copy (trusted list spec)"),
    ("Acquire::poll", "verus",
     r"lib RestoreOnPending::made_progress _19", r"lib RestoreOnPending::made_progress poll_proceed1.Ready.0",
     "the trusted RestoreOnPending stand-in is zero-sized, so rustc omits the move out of `Ready(coop)`; "
     "the same call is made at the same point"),
]

# ---------------------------------------------------------------- MIR text


def functions(text):
    """Map header -> {block: [lines]} for every function."""
    out = {}
    for m in re.finditer(r"^fn ([^\n]*)\{\n(.*?)^\}\n", text, re.M | re.S):
        blocks = {}
        for b in re.finditer(r"^    (bb\d+)(?: \(cleanup\))?: \{\n(.*?)^    \}", m[2], re.M | re.S):
            blocks[b[1]] = [l.strip() for l in b[2].splitlines() if l.strip()]
        types = dict(re.findall(r"^\s*let (?:mut )?(_\d+): (.*);$", m[2], re.M))
        for a in split_top(m[1][m[1].index("(") + 1:m[1].rindex(") ->")]):
            k, _, t = a.partition(": ")
            types[k] = t
        blocks["types"] = types
        out["fn " + m[1]] = blocks
    return out


def inline_promoted(text):
    """Replace `const F::promoted[N]` by its value when the promoted body is `&const V`."""
    table = {}
    for m in re.finditer(r"^const ([^\n]*::promoted\[\d+\]): &\w+ = \{\n(.*?)^\}\n", text, re.M | re.S):
        v = re.search(r"_1 = const ([^;]+);\n\s*_0 = &_1;", m[2])
        km = re.search(r"([^:\s]+::promoted\[\d+\])$", m[1])
        if not km:
            continue
        key = km[1]
        if v and table.get(key, v[1]) == v[1]:
            table[key] = v[1]
        else:
            table[key] = None  # ambiguous or not a simple constant
    def sub(m):
        key = re.search(r"([^:\s]+::promoted\[\d+\])$", m[1])[1]
        return f"const {table[key]}" if table.get(key) else m[0]
    return re.sub(r"const ([\w:]*::promoted\[\d+\])", sub, text)


class PathEnd(Exception):
    """The path diverges (e.g. `expect` on a None known along this path)."""


def find(fns, impl, sig):
    hits = [h for h in fns if re.search(impl + sig, h)]
    if len(hits) != 1:
        raise SystemExit(f"{len(hits)} functions match {sig!r}")
    return hits[0], fns[hits[0]]


def split_top(s, sep=","):
    """Split at top-level separators (outside (), [], {}, <>), ignoring `->`."""
    out, depth, cur, i = [], 0, "", 0
    while i < len(s):
        c = s[i]
        if c in "([{<" and not (c == "<" and s[i - 1:i] == " " and s[i + 1:i + 2] == "="):
            depth += 1
        elif c in ")]}>" and not (c == ">" and s[i - 1:i] == "-"):
            depth -= 1
        if c == sep and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += c
        i += 1
    if cur.strip():
        out.append(cur.strip())
    return out


def strip_generics(s):
    """Remove `::<...>` and `<...>` generic argument lists (balanced)."""
    out, i = "", 0
    while i < len(s):
        if s[i] == "<" and (s[i - 1:i].isalnum() or s[i - 1:i] in (":", "_")):
            if out.endswith("::"):
                out = out[:-2]
            depth = 0
            while i < len(s):
                depth += s[i] == "<"
                depth -= s[i] == ">" and s[i - 1] != "-"
                i += 1
                if depth == 0:
                    break
            continue
        out += s[i]
        i += 1
    return out


def short(path):
    """Last path segment: `std::sync::atomic::AtomicUsize::load` -> `AtomicUsize::load`."""
    p = strip_generics(path)
    p = re.sub(r"<impl [^>]*>::", "", p)
    m = re.fullmatch(r"<(.*) as (.*)>::(\w+)", p)
    if m:
        return short(m[1]) + "::" + m[3]
    parts = [x for x in p.split("::") if x]
    return "::".join(parts[-2:])


def norm_const(c):
    c = c.strip()
    if "Tracked" in c or "Ghost" in c or "PhantomData" in c:
        return "GHOST"
    m = re.fullmatch(r"(\d+)_?(usize|u\d+|i\d+|isize)?", c)
    if m:
        return m[1]
    if c in ("true", "false"):
        return "1" if c == "true" else "0"
    if c.startswith('"'):
        return c
    if c.startswith("ZeroSized: {closure@"):
        m = re.search(r"\{closure@([^:]+):(\d+)", c)
        return f"closure@{m[2]}" if "vstd" not in m[1] else "GHOST"
    return ctor_norm(c)


def ctor_norm(t):
    """Normalise constructor/const paths: drop generics and module paths."""
    t = strip_generics(t)
    t = re.sub(r"\b(?:\w+::)+(\w+)", r"\1", t)
    return t


def atom(t):
    return re.fullmatch(r"[\w.#@]+", t) is not None


def ctor_parts(v):
    """`Some(x)` -> ('Some', ['x']); `(a, b)` -> ('', ['a','b']); else None."""
    m = re.fullmatch(r"(\w*)\((.*)\)", v)
    if not m:
        return None
    if m[1] and (m[1][0].islower() or m[1] in ("Add", "Sub", "Shl", "Shr", "BitAnd", "BitOr", "Gt", "Ge",
                                               "Lt", "Le", "Eq", "Ne", "Not", "Mul", "Div", "Rem")):
        return None
    return m[1], split_top(m[2])


DISC = {"None": 0, "Some": 1, "Ok": 0, "Err": 1, "Ready": 0, "Pending": 1, "Continue": 0, "Break": 1,
        "Closed": 0, "NoPermits": 1}

# ---------------------------------------------------------------- stubs


ATOMIC_OPS = "load|store|fetch_add|fetch_sub|fetch_or|fetch_and|fetch_xor|swap|compare_exchange|compare_exchange_weak"
WAKER_CLOSURES = {"271": "waker_take", "361": "waker_take", "557": "waker_register"}  # real lines of the closures
IDENTITY = re.compile(r"(Deref::deref|DerefMut::deref_mut|From::from|get_unchecked_mut|Pin::as_mut|"
                      r"NonNull::from|NonNull::as_mut|NonNull::as_ref|NonNull::new_unchecked|"
                      r"Pin::into_inner_unchecked|Arc::clone|Arc::deref|Arc::new)$")
GHOST_CALL = re.compile(r"assume_new_fallback|get_variant_field|is_variant")
COVERED = {"poll_acquire", "assign_permits", "add_permits_locked", "release", "Waiter::new", "Acquire::project"}


class Path:
    def __init__(self, side):
        self.side = side
        self.env, self.mem, self.ev, self.orderings = {}, {}, [], []
        self.visits, self.counts, self.params = {}, {}, set()

    def copy(self):
        p = Path(self.side)
        p.env, p.mem, p.ev, p.orderings = dict(self.env), dict(self.mem), list(self.ev), list(self.orderings)
        p.visits, p.counts, p.params = dict(self.visits), dict(self.counts), self.params
        return p

    def deref_locals(self, v):
        """Event arguments: a reference to a local is shown as the local's value."""
        return re.sub(r"@(_\d+)", lambda m: self.env.get(m[1], m[1]), v)

    # ------------------------------------------------ places and operands

    def place(self, s, addr=False):
        s = s.strip()
        if re.fullmatch(r"_\d+", s):
            if addr and s not in self.params:
                return "@" + s  # reference to a local: kept as a location so writes through it land
            return self.env.get(s, s)
        m = re.fullmatch(r"\(\*(.*)\)", s)
        if m:
            k = self.place(m[1])
            if k.startswith("@"):
                return k if addr else self.env.get(k[1:], k[1:])
            return k if addr else self.mem.get(k, k)
        if s.startswith("(") and s.endswith(")"):
            inner = s[1:-1]
            parts = split_top(inner, ":")
            if len(parts) >= 2:
                base_field, ty = parts[0], ":".join(parts[1:])
                base, field = base_field.rsplit(".", 1)
                if re.search(r"PAtomicUsize|^\s*Waitlist\s*$", ty) and self.side == "verus":
                    return self.place(base, addr)  # vstd atomic wrapper; MutexGuard.w is the guarded Waitlist
                mb = re.fullmatch(r"\((.*) as (\w+)\)", base)
                if mb:
                    v = self.place(mb[1])
                    cp = ctor_parts(v)
                    if cp and cp[0] == mb[2]:
                        return cp[1][int(field)]
                    if v.startswith("branch(") and mb[2] == "Break":
                        return v[len("branch("):-1]
                    return f"{v}.{mb[2]}.{field}"
                v = self.place(base, addr=True) if self.is_deref_place(base) else self.place(base)
                if v.startswith("@"):
                    v = self.env.get(v[1:], v[1:])
                cp = ctor_parts(v)
                if cp is not None and cp[0] == "" and not self.is_deref_place(base):
                    return cp[1][int(field)]
                k = f"{v}.{field}"
                return k if addr else self.mem.get(k, k)
        raise ValueError(f"place {s!r}")

    @staticmethod
    def is_deref_place(s):
        return s.strip().startswith("(*")

    def operand(self, s):
        s = s.strip()
        for pre in ("copy ", "move ", "deref_copy "):
            if s.startswith(pre):
                return self.place(s[len(pre):])
        if s.startswith("const "):
            return norm_const(s[6:])
        return self.rvalue(s)

    def rvalue(self, s):
        s = s.strip()
        if s.startswith("&raw const ") or s.startswith("&raw mut "):
            return self.place(s.split(" ", 2)[2], addr=True)
        if s.startswith("&mut "):
            return self.place(s[5:], addr=True)
        if s.startswith("&"):
            return self.place(s[1:], addr=True)
        if s.startswith(("copy ", "move ", "const ", "deref_copy ")):
            return self.operand(s)
        m = re.fullmatch(r"discriminant\((.*)\)", s)
        if m:
            v = self.place(m[1])
            cp = ctor_parts(v)
            if cp and cp[0] in DISC:
                return str(DISC[cp[0]])
            if v in DISC:
                return str(DISC[v])
            if v.startswith("branch("):
                v = v[len("branch("):-1]
            return f"disc({v})"
        m = re.fullmatch(r"(\w+)WithOverflow\((.*)\)", s)
        if m:
            a = [self.operand(x) for x in split_top(m[2])]
            return f"({m[1]}({', '.join(a)}), ovf)"
        m = re.fullmatch(r"(Add|Sub|Mul|Div|Rem|Shl|Shr|BitAnd|BitOr|BitXor|Gt|Ge|Lt|Le|Eq|Ne)\((.*)\)", s)
        if m:
            a = [self.operand(x) for x in split_top(m[2])]
            return fold(m[1], a)
        m = re.fullmatch(r"Not\((.*)\)", s)
        if m:
            a = self.operand(m[1])
            return {"0": "1", "1": "0"}.get(a, f"Not({a})")
        m = re.fullmatch(r"(.*) as (\w+) \(\w+\)", s)
        if m:
            return self.operand(m[1])
        if s.startswith("std::sync::atomic::Ordering::"):
            return "Ordering::" + s.rsplit("::", 1)[1]
        if s.startswith("(") and s.endswith(")"):
            return "(" + ", ".join(self.operand(x) for x in split_top(s[1:-1])) + ")"
        m = re.fullmatch(r"\[(.*)\]", s)
        if m:
            return "[" + ", ".join(self.operand(x) for x in split_top(m[1])) + "]"
        m = re.fullmatch(r"\{closure@[^:]+:(\d+):[^}]*\}(?: \{ (.*) \})?", s)
        if m:
            caps = []
            for f in split_top(m[2] or ""):
                k, v = f.split(": ", 1)
                v = v.strip()
                caps.append(f"{k}={self.place(v[5:], addr=True) if v.startswith('&mut ') else self.operand(v)}")
            return f"closure@{m[1]}[{';'.join(caps)}]"
        m = re.fullmatch(r"([\w:<>'&, \[\]]+?) \{ (.*) \}", s)  # struct aggregate
        if m:
            fields = []
            for f in split_top(m[2]):
                k, v = f.split(": ", 1)
                v = self.operand(v)
                if not v.startswith("GHOST"):
                    fields.append(f"{k}: {v}")
            return f"{ctor_norm(m[1])} {{ {', '.join(fields)} }}"
        m = re.fullmatch(r"([\w:<>'&, \[\]()]+?)::(\w+)(?:\((.*)\))?", s)  # enum aggregate
        if m:
            name = m[2]
            if m[3] is None:
                return name
            return f"{name}({', '.join(self.operand(x) for x in split_top(m[3]))})"
        m = re.fullmatch(r"(\w+)\((.*)\)", s)  # tuple-struct aggregate, e.g. AcquireError(..)
        if m:
            return f"{m[1]}({', '.join(self.operand(x) for x in split_top(m[2]))})"
        raise ValueError(f"rvalue {s!r}")

    # ------------------------------------------------ writes

    def write(self, dest, val):
        dest = dest.strip()
        if re.fullmatch(r"_\d+", dest):
            self.env[dest] = val
            return
        k = self.place(dest, addr=True)
        if k.startswith("@"):
            self.env[k[1:]] = val
            return
        self.mem[k] = val
        root = k.split(".")[0]
        if root in self.params or re.fullmatch(r"lock\d+", root):
            self.event(("write", k, val))  # through a parameter or the guarded wait list

    def event(self, e):
        """Record an event; its result is named by kind and per-kind count, so that an extra
        event on one side does not rename every later value."""
        e = tuple(self.deref_locals(x) if isinstance(x, str) else x for x in e)
        self.ev.append(e)
        key = e[0] if e[0] not in ("atomic", "list", "waker", "lib", "call") else e[1]
        key = re.sub(r"\W", "_", key.split("::")[-1])
        self.counts[key] = self.counts.get(key, 0) + 1
        return f"{key}{self.counts[key]}"

    # ------------------------------------------------ calls

    def call(self, callee, args):
        """Return the symbolic result of a call (and record its event)."""
        name = short(callee)
        raw = callee
        if GHOST_CALL.search(raw):
            return "GHOST"
        vals = [self.deref_locals(self.operand(a)) for a in args]
        real = self.side == "real"
        if IDENTITY.search(name) or re.search(r"as (std::ops::)?(Deref|DerefMut)>::deref(_mut)?$|as From<", raw):
            return vals[0]
        m = re.fullmatch(rf"(?:std::sync::atomic::AtomicUsize|vstd::atomic::PAtomicUsize)::({ATOMIC_OPS})", raw)
        if m:
            target = vals[0]
            rest = [v for v in vals[1:] if not v.startswith("GHOST")]
            ords = [v for v in rest if v.startswith("Ordering::")]
            rest = [v for v in rest if not v.startswith("Ordering::")]
            r = self.event(("atomic", m[1], target, *rest))
            if real:
                self.orderings.append((m[1], target, ords))
            if m[1].startswith("compare_exchange"):
                return f"cas({r})"
            return r
        if re.search(r"AtomicUsize(::<.*>)?::new$", raw):
            v = [x for x in vals if not x.startswith("GHOST")]
            self.event(("atomic_new", *v))
            return f"Atomic({', '.join(v)})"
        if re.search(r"Mutex(::<.*>)?::lock$", raw):
            g = self.event(("lock", vals[0]))
            return g if real else f"({g}, GHOST)"
        if raw.endswith("MutexGuard::<'_>::unlock") or re.search(r"mem::drop::<std::sync::MutexGuard", raw):
            self.event(("unlock", vals[0]))
            return "()"
        if re.search(r"Mutex(::<.*>)?::new$", raw):
            self.event(("mutex_new", vals[0]))
            return f"Mutex({vals[0]})"
        if re.search(r"rwlock::RwLock(::<.*>)?::new$", raw):  # Verus: Mutex { rw: RwLock::new(LockVal{w,..}) }
            inner = re.sub(r"^LockVal \{ w: (.*?)(, tok: .*)? \}$", r"\1", vals[0])
            self.event(("mutex_new", inner))
            return f"RW({inner})"
        m = re.search(r"LinkedList(?:::<[^>]*(?:<[^>]*>)?[^>]*>)?::(push_front|pop_back|last|remove|new)$", raw)
        if m:
            if m[1] == "new":
                return "LinkedList::new()"
            r = self.event(("list", m[1], vals[0], *vals[1:]))
            return f"L({r})"
        if raw.endswith("UnsafeCell::<Option<Waker>>::with_mut") or re.search(r"unsafe_cell::UnsafeCell::<.*>::with_mut", raw):
            clo = re.search(r"closure@tokio/src/sync/batch_semaphore\.rs:(\d+)", raw)
            op = WAKER_CLOSURES.get(clo[1] if clo else "", "waker_with_mut?")
            extra = ["_2"] if op == "waker_register" else []
            r = self.event(("waker", op, vals[0], *extra))
            ow = re.search(r"old_waker=(@_\d+)", self.operand(args[1]))
            if ow:  # the real closure stores the old waker through its capture; Verus returns it
                self.env[ow[1][1:]] = r
            return r
        if name in ("WakerCell::take", "WakerCell::register"):
            op = "waker_take" if name.endswith("take") else "waker_register"
            return self.event(("waker", op, *vals))
        if name in ("WakerCell::new",) or (real and re.search(r"UnsafeCell::<Option<Waker>>::new$|unsafe_cell::UnsafeCell::<.*>::new$", raw)):
            return "WakerCell(None)"
        if name == "AcquireError::closed":
            return "AcquireError(())"
        if name == "trace_leaf" and real:
            return "Ready(())"
        if name == "Try::branch" or re.search(r"as Try>::branch$", raw):
            v = vals[0]
            cp = ctor_parts(v)
            if cp and cp[0] == "Ok":
                return f"Continue({cp[1][0]})"
            if cp and cp[0] == "Err":
                return f"Break(Err({cp[1][0]}))"
            return f"branch({v})"
        if re.search(r"as FromResidual<.*>>::from_residual$", raw):
            return f"Ready({vals[0]})"
        if re.fullmatch(r"(Option::)?(is_none|is_some|expect|unwrap|take)", name.split("::")[-1]) and \
                re.search(r"Option(::<.*>)?::(is_none|is_some|expect|unwrap|take)$", raw):
            op = name.split("::")[-1]
            v = vals[0]
            if op == "take":
                raw0 = self.place(re.sub(r"^(copy|move) ", "", args[0].strip()))
                cur = self.env.get(raw0[1:], raw0) if raw0.startswith("@") else self.mem.get(raw0, raw0)
                self.write_ref(args[0], "None")
                return cur
            cp = ctor_parts(v)
            known = cp is not None and cp[0] == "Some" or v == "None"
            if known:
                if op == "is_none":
                    return "1" if v == "None" else "0"
                if op == "is_some":
                    return "0" if v == "None" else "1"
                if v != "None":
                    return cp[1][0]
                self.event(("panic", op))
                raise PathEnd()
        if re.search(r"Option(::<.*>)?::unwrap_or_else(::<.*>)?$", raw):
            v, clo = vals
            cp = ctor_parts(v)
            if cp and cp[0] == "Some":
                return cp[1][0]
            if v == "None" and clo.startswith("closure@339"):  # real closure `|| self.waiters.lock()`
                return self.event(("lock", "_1.0"))
            raise ValueError(f"unwrap_or_else on {v} with {clo}")
        if name.split("::")[-1] in ("new_display", "new_v1"):
            return "fmt"
        covered = name in COVERED or (name.split("::")[-1] in COVERED and name.split("::")[0] in ("Semaphore", "Waiter"))
        kind = "call" if covered else "lib"
        vals = [v for v in vals if not v.startswith("GHOST")]
        if name.endswith("::project") and real:
            s = vals[0]
            return f"({s}.0, {s}.1, {s}.2, {s}.3)"
        if name == "cmp::min":
            name = "min"  # the copy's trusted `min` wraps std::cmp::min
        return self.event((kind, name, *vals))

    def write_ref(self, arg, val):
        a = arg.strip()
        for pre in ("copy ", "move "):
            if a.startswith(pre):
                a = a[len(pre):]
        k = self.place(a)
        if k.startswith("@"):
            self.env[k[1:]] = val
        else:
            self.mem[k] = val


def fold(op, a):
    if all(re.fullmatch(r"\d+", x) for x in a):
        x, y = int(a[0]), int(a[1])
        r = {"Add": x + y, "Sub": x - y, "Shl": x << y, "Shr": x >> y, "BitAnd": x & y, "BitOr": x | y,
             "Gt": int(x > y), "Ge": int(x >= y), "Lt": int(x < y), "Le": int(x <= y), "Eq": int(x == y),
             "Ne": int(x != y)}.get(op)
        if r is not None:
            return str(r)
    return f"{op}({', '.join(a)})"

# ---------------------------------------------------------------- exploration


CALL_TAIL = re.compile(r"\) -> (\[(?:return|success)[^\]]*\]|unwind [\w()]+|bb\d+);$")


class _CallRe:
    """Split `DEST = CALLEE(ARGS) -> TARGET;` with balanced brackets."""

    def match(self, line):
        t = CALL_TAIL.search(line)
        if not t:
            return None
        end = t.start()  # index of the closing ')'
        depth = 0
        for i in range(end, -1, -1):
            depth += line[i] == ")"
            depth -= line[i] == "("
            if depth == 0:
                break
        head, args = line[:i], line[i + 1:end]
        m = re.fullmatch(r"(?:(_\d+|\(.*?\)) = )?(.+)", head)
        if not m or not m[2] or m[2] in ("switchInt", "drop", "assert"):
            return None
        return (None, m[1], m[2], args)


CALL_RE = _CallRe()


def terminator_succ(line):
    """For a call terminator: normal successor or None if it diverges."""
    m = re.search(r"-> \[return: (bb\d+)", line)  # a bare `-> bbN` is an unwind-only (diverging) call
    return m[1] if m else None


def diverges(blocks, b, depth=0):
    if depth > 20:
        return False
    last = blocks[b][-1]
    if last.startswith("goto -> "):
        return diverges(blocks, last[8:].rstrip(";"), depth + 1)
    if last in ("return;", "unreachable;") or last.startswith(("switchInt", "drop(", "assert(")):
        return last == "unreachable;"
    m = CALL_RE.match(last)
    if m:
        s = terminator_succ(last)
        return s is None or diverges(blocks, s, depth + 1)
    return False


def explore(blocks, side, params, bound):
    """All bounded paths; returns list of (events, orderings)."""
    types = blocks.pop("types", {}) if "types" in blocks else {}
    explore.types = types
    start = Path(side)
    for p, v in params.items():
        start.env[p] = v
    start.params = set(params)
    out, stack = [], [(start, "bb0")]
    while stack:
        p, b = stack.pop()
        p.visits[b] = p.visits.get(b, 0) + 1
        if p.visits[b] > bound:
            continue
        lines = blocks[b]
        for line in lines[:-1]:
            if line.startswith(("StorageLive", "StorageDead", "FakeRead", "PlaceMention", "AscribeUserType",
                                "Retag", "Coverage", "ConstEvalCounter", "Nop", "Deinit")):
                continue
            m = re.fullmatch(r"(.+?) = (.*);", line)
            if not m:
                m2 = re.fullmatch(r"discriminant\((.*)\) = (\d+);", line)
                if m2:
                    continue
                raise ValueError(f"{side} {b}: statement {line!r}")
            p.write(m[1], p.rvalue(m[2]))
        last = lines[-1]
        if last == "return;":
            p.event(("return", p.env.get("_0", "_0")))
            out.append((tuple(p.ev), tuple(p.orderings)))
            continue
        if last in ("unreachable;", "resume;"):
            continue
        if last.startswith("goto -> "):
            stack.append((p, last[8:].rstrip(";")))
            continue
        if last.startswith("assert("):
            stack.append((p, re.search(r"success: (bb\d+)", last)[1]))
            continue
        if last.startswith("drop("):
            m = re.match(r"drop\((.*?)\) -> \[return: (bb\d+)", last)
            v = p.place(m[1])
            if "MutexGuard" in explore.types.get(m[1], "") and v != "None":
                g = re.sub(r"^Some\((.*)\)$", r"\1", v)
                p.event(("unlock", g) if side == "real" else ("guard_dropped_without_unlock", g))
            stack.append((p, m[2]))
            continue
        if last.startswith("switchInt("):
            m = re.fullmatch(r"switchInt\((.*?)\) -> \[(.*)\];", last)
            cond = p.operand(m[1])
            arms = [a.split(": ") for a in split_top(m[2])]
            explicit = [a for a, _ in arms if a != "otherwise"]
            live = [(a, t) for a, t in arms if not (blocks[t][-1] == "unreachable;" and len(blocks[t]) == 1)]
            if re.fullmatch(r"\d+", cond):
                tgt = next((t for a, t in arms if a == cond), None) or next(t for a, t in arms if a == "otherwise")
                stack.append((p, tgt))
                continue
            def label(a):
                if a != "otherwise":
                    return a
                if explicit == ["0"]:
                    return "1"
                if explicit == ["1"]:
                    return "0"
                rest = {"0", "1"} - set(explicit)
                return rest.pop() if len(rest) == 1 and cond.startswith("disc(") else "not" + "/".join(explicit)
            c, flip = cond, False
            while c.startswith("Not(") and c.endswith(")"):
                c, flip = c[4:-1], not flip
            def lab(a):
                l = label(a)
                return {"0": "1", "1": "0"}.get(l, l) if flip else l
            div = [(a, t) for a, t in live if diverges(blocks, t)]
            if div and len(div) < len(live):
                for a, t in live:
                    if (a, t) not in div:
                        q = p.copy()
                        q.event(("assert", c, lab(a)))
                        stack.append((q, t))
                continue
            for a, t in live:
                q = p.copy()
                q.event(("branch", c, lab(a)))
                stack.append((q, t))
            continue
        m = CALL_RE.match(last)
        if m:
            _, dest, callee, args = m
            nxt = terminator_succ(last)
            if nxt is None:
                p.event(("panic", short(callee)))
                continue
            if callee == "runtime_assert" and side == "verus":
                c = p.operand(args)
                flip = False
                while c.startswith("Not(") and c.endswith(")"):
                    c, flip = c[4:-1], not flip
                if not re.fullmatch(r"\d+", c):  # a constant assertion is folded away by rustc on the real side
                    p.event(("assert", c, "0" if flip else "1"))
                if dest:
                    p.write(dest, "()")
                stack.append((p, nxt))
                continue
            try:
                r = p.call(callee, split_top(args))
            except PathEnd:
                continue
            if dest:
                p.write(dest, r)
            stack.append((p, nxt))
            continue
        raise ValueError(f"{side} {b}: terminator {last!r}")
    return out


def params_of(header, side=None):
    ps = re.findall(r"(_\d+): ", header.split(") ->")[0])
    return {p: p for p in ps}


def show(e):
    return " ".join(str(x) for x in e)


def rewrite(name, side, traces, fired):
    out = set()
    for t in traces:
        text = " | ".join(show(e) for e in t)
        for i, (fn, sd, rx, rep, _) in enumerate(KNOWN):
            if fn == name and sd == side:
                new = re.sub(rx, rep, text)
                if new != text:
                    fired.add(i)
                    text = new
        out.add(text)
    return out


def compare(name, real_paths, verus_paths):
    fired = set()
    R = rewrite(name, "real", {ev for ev, _ in real_paths}, fired)
    V = rewrite(name, "verus", {ev for ev, _ in verus_paths}, fired)
    unused = [i for i, k in enumerate(KNOWN) if k[0] == name and i not in fired]
    only_r, only_v = sorted(R - V, key=len), sorted(V - R, key=len)
    diffs = []
    for a_side, b_side, flip in ((only_r, only_v, False), (only_v, only_r, True)):
        for t in a_side:
            ts = t.split(" | ")
            best = max(b_side or [""], key=lambda u: difflib.SequenceMatcher(None, ts, u.split(" | ")).ratio())
            bs = best.split(" | ") if best else []
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ts, bs).get_opcodes():
                if op != "equal":
                    d = (ts[i1:i2], bs[j1:j2])
                    d = (d[1], d[0]) if flip else d
                    if d not in diffs:
                        diffs.append(d)
    return len(R), len(V), len(R & V), diffs, unused, sorted(fired)


def main(argv):
    global BOUND
    args = list(argv[1:])
    show_ord = "--orderings" in args
    if show_ord:
        args.remove("--orderings")
    only = None
    if "--only" in args:
        i = args.index("--only"); only = args[i + 1]; del args[i:i + 2]
    if "--bound" in args:
        i = args.index("--bound"); BOUND = int(args[i + 1]); del args[i:i + 2]
    real_fns = functions(inline_promoted(open(args[0]).read()))
    verus_fns = functions(inline_promoted(open(args[1]).read()))
    bad = 0
    all_ord = []
    for name, (rs, vs) in FUNCS.items():
        if only and name != only:
            continue
        rh, rb = find(real_fns, IMPL_R, rs)
        vh, vb = find(verus_fns, IMPL_V, vs)
        rp = explore(rb, "real", params_of(rh, "real"), BOUND)
        vp = explore(vb, "verus", params_of(vh, "verus"), BOUND)
        for _, o in rp:
            for x in o:
                if (name,) + x[:2] + (tuple(x[2]),) not in all_ord:
                    all_ord.append((name,) + x[:2] + (tuple(x[2]),))
        nr, nv, both, diffs, unused, fired = compare(name, rp, vp)
        status = "DIFFERS" if diffs else "equal" + (f" after known rewrite(s) {fired}" if fired else "")
        print(f"{name}: real {len(rp)} paths, verus {len(vp)} paths, {nr}/{nv} distinct traces, {both} shared: {status}")
        for r, v in diffs:
            print("  real : " + (" | ".join(r) or "-"))
            print("  verus: " + (" | ".join(v) or "-"))
        for i in unused:
            print(f"  known rewrite {i} did not apply (stale entry)")
        bad += bool(diffs or unused)
    if show_ord:
        print("\nreal atomic operations and their orderings:")
        for fn, op, target, ords in all_ord:
            print(f"  {fn}: {op} {target} {', '.join(o.removeprefix('Ordering::') for o in ords)}")
    print(f"result: {'all covered functions agree up to known differences' if not bad else f'{bad} function(s) with unexplained differences'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
