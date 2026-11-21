"""Check that the Verus copy keeps the real code of batch_semaphore.rs, and list what it adds.

Real side: each function in FUNCS of the real file (Tokio fc0d151 +
semaphore-close-fix.patch), with comments, blank lines and
`#[cfg(all(tokio_unstable, feature = "tracing"))]` items removed.
Verus side: the function of the same name in batch_semaphore.rs, with ghost
syntax erased (proof blocks, tracked/ghost lets, Tracked/Ghost arguments and
fields, loop invariants, open_atomic_invariant!) and
`atomic_with_ghost!(&x => op(args); ..)` turned back into `x.op(args)`.
Both sides drop memory-ordering arguments and normalise whitespace.

Two checks per function:
- kept: real lines found verbatim, in order, in the Verus function. The rest are
  printed as "changed" (informational).
- added: Verus executable lines not matched to a real line. Each must carry a
  `// VERUS:` marker (on the line, or on a comment-only line directly above it)
  or match an ALLOWED category below. Unexplained additions are printed as
  "UNEXPLAINED" and make the script exit 1.

Usage: python3 correspond.py REAL_batch_semaphore.rs   (exit 0 iff no unexplained added line)
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# name -> signature regex (after "fn "), so that the three `new`s are told apart
FUNCS = {
    "Semaphore::new": r"new\(permits",
    "release": r"release\b",
    "close": r"close\b",
    "try_acquire": r"try_acquire\b",
    "add_permits_locked": r"add_permits_locked\b",
    "forget_permits": r"forget_permits\b",
    "poll_acquire": r"poll_acquire\b",
    "Waiter::new": r"new\(\s*num_permits",
    "assign_permits": r"assign_permits\b",
    "poll": r"poll\(",
    "Acquire::new": r"new\(semaphore",
    "drop": r"drop\(&mut self\)",
}

# Added lines that need no per-line marker: (category, regex on the normalised line).
ALLOWED = [
    ("closing brackets", r"^[\]\)\}]+[,;]?$"),
    ("guard drop made explicit (Rust drops MutexGuard implicitly)",
     r"^(\w+\.)?unlock\(\);$|^if let Some\(g\) = lock \{$"),
    ("assert!/assert_eq! as runtime_assert (trusted to panic iff false)", r"^runtime_assert\(.*\);"),
    ("atomic call's result bound to `res` before the `match` (so the ghost step can see it)",
     r"^let res = [\w.]+\.compare_exchange(_weak)?\(.*\);$|^match res \{$"),
    ("lock(): returns (guard, ghost token); the guard is bound to a name where the real code uses `self.waiters.lock()` inline",
     r"^let (mut )?\w+ = self(\.semaphore)?\.waiters\.lock\(\);$"),
    ("ghost-only value plumbing (Tracked instance clone, erased at compile time)",
     r"^let tracked_inst = |tracked_inst"),
    ("match arms of a rewritten `?`/`let..else`/`ready!`/`break value` (block carries a VERUS marker)",
     r"^(Ok\(\(\)\) => \{\},|Err\(e\) => return Poll::Ready\(Err\(e\)\),|Some\(w\) => w,|None => break,"
     r"|Poll::Ready\(c\) => c,|Poll::Pending => return Poll::Pending,|Poll::Pending => Poll::Pending,"
     r"|Poll::Ready\(r\) => \{|Ok\(_\) => \{\},?|Err\(e\) => \{)$"),
]

MARK = "@@VERUS@@"

def norm(l):
    l = re.sub(r"//.*", "", l).strip()
    l = l.replace("Ordering::", "")
    l = re.sub(r",\s*(AcqRel|Acquire|Release|Relaxed)\s*,\s*(AcqRel|Acquire|Release|Relaxed)\)", ")", l)
    l = re.sub(r",\s*(AcqRel|Acquire|Release|Relaxed)\)", ")", l)
    l = re.sub(r"\((AcqRel|Acquire|Release|Relaxed)\)", "()", l)
    return re.sub(r"\s+", " ", l)

def body(src, name, sig, verus):
    m = re.search(r"\n\s*(pub(\(crate\))? )?(const )?fn " + sig, src)
    if m is None:
        raise SystemExit(f"{name}: not found")
    if verus:
        # skip requires/ensures: the body opens at the first line that is just "{"
        sig_end = re.search(r"\n\s*\{\s*\n", src[m.end():])
        i = src.index("{", m.end() + sig_end.start())
    else:
        i = src.index("{", balanced(src, src.index("(", m.start()), "(", ")"))
    return src[i:balanced(src, i)]

def balanced(s, i, open_="{", close="}"):
    """Index just past the bracket group that starts at s[i] == open_."""
    depth = 0
    for j in range(i, len(s)):
        depth += s[j] == open_; depth -= s[j] == close
        if depth == 0:
            return j + 1
    raise ValueError("unbalanced")

def erase_ghost(b):
    """Strip Verus-only syntax so that executable statements can be compared.

    `// VERUS:` comments become MARK so that they survive comment removal."""
    b = re.sub(r"//+\s*VERUS:.*", MARK, b)
    b = re.sub(r"//.*", "", b)
    # atomic_with_ghost!(&E => op(args); ...ghost...) -> E.op(args)
    while (m := re.search(r"atomic_with_ghost!\(\s*&", b)):
        end = balanced(b, m.end() - 2, "(", ")")
        inner = b[m.end():end - 1]
        target, rest = inner.split("=>", 1)
        call = rest.split(";", 1)[0].strip()
        b = b[:m.start()] + target.strip() + "." + call + b[end:]
    # ghost-only blocks
    while (m := re.search(r"\b(proof\s*\{|open_atomic_invariant!\()", b)):
        if m.group(1).startswith("proof"):
            e = balanced(b, m.end() - 1)
        else:
            e = balanced(b, m.end() - 1, "(", ")")
            e += b[e:].startswith(";")
        b = b[:m.start()] + b[e:]
    # loop invariants/ensures: "loop\n invariant ..\n {" -> "loop {"
    b = re.sub(r"\b(loop|while [^\n]*?)\s*\n\s*(invariant|invariant_except_break|ensures|decreases)\b.*?\n\s*\{",
               lambda m: m.group(1).rstrip() + " {", b, flags=re.S)
    b = re.sub(r"let (tracked|ghost) [^;]*;", "", b)
    b = re.sub(r"let \w+ = (Tracked|Ghost)\([^;]*\);", "", b)
    # ghost struct fields: `name: Tracked(..),`
    b = re.sub(r"(?m)^\s*\w+: (Tracked|Ghost)\(.*\),?\s*$", "", b)
    # Tracked(..)/Ghost(..) arguments
    while (m := re.search(r",?\s*\b(Tracked|Ghost)\(", b)):
        e = balanced(b, m.end() - 1, "(", ")")
        if not m.group(0).startswith(","):  # first argument: drop the following comma
            e += len(re.match(r"\s*,?\s*", b[e:]).group(0))
        b = b[:m.start()] + b[e:]
    b = re.sub(r"\blet \((mut )?(\w+)\) =", r"let \1\2 =", b)  # `let (g) =` left by erasure
    b = re.sub(r"(?m)^(\s*)\((\w+)\)\s*$", r"\1\2", b)  # `(s)` left by erasure
    b = b.replace(".w.", ".")  # MutexGuard field access: `waiters.w.closed` is `waiters.closed`
    return b

def real_lines(b):
    out, lines, k = [], b.splitlines(), 0
    while k < len(lines):
        l = lines[k]
        if re.search(r"#\[cfg\(all\(tokio_unstable", l):
            # skip the next item: lines until brackets balance and the item ends
            k += 1; depth = 0
            while k < len(lines):
                t = norm(lines[k])
                depth += sum(t.count(c) for c in "({[") - sum(t.count(c) for c in ")}]")
                k += 1
                if depth <= 0 and t.endswith((";", ",", "}")):
                    break
            continue
        if re.search(r"#\[cfg\(any\(not\(tokio_unstable", l):
            k += 1  # the attribute only; the item is compiled in
            continue
        n = norm(l)
        if n and n not in ("{", "}"):
            out.append(n)
        k += 1
    return out

def verus_lines(b):
    """(normalised line, marked) for each executable line of an erased body."""
    out, pending = [], False
    for l in erase_ghost(b).splitlines():
        marked = MARK in l
        n = norm(l.replace(MARK, ""))
        if not n:
            pending = pending or marked  # comment-only marker covers the next line
            continue
        if n not in ("{", "}"):
            out.append((n, marked or pending))
        pending = False
    return out

def allowed(l):
    for cat, rx in ALLOWED:
        if re.search(rx, l):
            return cat
    return None

def main():
    real = open(sys.argv[1]).read()
    ver = open(os.path.join(HERE, "batch_semaphore.rs")).read()
    tot_real = tot_kept = tot_added = tot_marked = tot_allowed = unexplained = 0
    cats = {}
    for f, sig in FUNCS.items():
        r = real_lines(body(real, f, sig, False))
        v = verus_lines(body(ver, f, sig, True))
        pos, missing, used = 0, [], set()
        for l in r:
            for k in range(pos, len(v)):
                if v[k][0] == l:
                    used.add(k); pos = k + 1
                    break
            else:
                missing.append(l)
        added = [(l, mk) for k, (l, mk) in enumerate(v) if k not in used]
        print(f"{f}: {len(r) - len(missing)}/{len(r)} real lines kept in order; {len(added)} lines added")
        for l in missing:
            print(f"    changed: {l}")
        for l, mk in added:
            if mk:
                tot_marked += 1
                print(f"    added (VERUS marker): {l}")
            elif (c := allowed(l)):
                tot_allowed += 1; cats[c] = cats.get(c, 0) + 1
                print(f"    added (allowed: {c}): {l}")
            else:
                unexplained += 1
                print(f"    added UNEXPLAINED: {l}")
        tot_real += len(r); tot_kept += len(r) - len(missing); tot_added += len(added)
    print(f"total: {tot_kept}/{tot_real} real lines kept verbatim in order; {tot_real - tot_kept} changed")
    print(f"added: {tot_added} ({tot_marked} marked, {tot_allowed} allowed, {unexplained} unexplained)")
    for c, n in cats.items():
        print(f"    allowed {n}: {c}")
    sys.exit(1 if unexplained else 0)

if __name__ == "__main__":
    main()
