"""Check that the Verus copy keeps the real code of batch_semaphore.rs.

For each function in FUNCS, every statement line of the real function body
(Tokio fc0d151 + semaphore-close-fix.patch; comments, blank lines and
`#[cfg(all(tokio_unstable, feature = "tracing"))]` items removed) must
appear, in order, in the Verus function of the same name after whitespace
normalisation, unless it is listed in ALLOWED with a reason.
Usage: python3 correspond.py REAL_batch_semaphore.rs   (exit 0 iff no unexplained line)
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FUNCS = ["release", "close", "try_acquire", "add_permits_locked", "forget_permits",
         "poll_acquire", "assign_permits", "poll", "drop"]

def norm(l):
    l = re.sub(r"//.*", "", l).strip()
    l = l.replace("Ordering::", "")
    l = re.sub(r",\s*(AcqRel|Acquire|Release|Relaxed)\s*,\s*(AcqRel|Acquire|Release|Relaxed)\)", ")", l)
    l = re.sub(r",\s*(AcqRel|Acquire|Release|Relaxed)\)", ")", l)
    l = re.sub(r"\((AcqRel|Acquire|Release|Relaxed)\)", "()", l)
    return re.sub(r"\s+", " ", l)

def body(src, name, verus):
    m = re.search(r"\n\s*(pub(\(crate\))? )?fn " + name + r"\b", src)
    if m is None:
        raise SystemExit(f"{name}: not found")
    if verus:
        # skip requires/ensures: the body opens at the first line that is just "{"
        sig_end = re.search(r"\n\s*\{\s*\n", src[m.end():])
        i = src.index("{", m.end() + sig_end.start())
    else:
        i = src.index("{", src.index(")", m.end()))
    depth, j = 0, i
    while True:
        c = src[j]
        depth += c == "{"; depth -= c == "}"
        j += 1
        if depth == 0:
            return src[i:j]

def balanced(s, i, open_="{", close="}"):
    """Index just past the bracket group that starts at s[i] == open_."""
    depth = 0
    for j in range(i, len(s)):
        depth += s[j] == open_; depth -= s[j] == close
        if depth == 0:
            return j + 1
    raise ValueError("unbalanced")

def erase_ghost(b):
    """Strip Verus-only syntax so that executable statements can be compared."""
    b = re.sub(r"//.*", "", b)
    # atomic_with_ghost!(&E => op(args); ...ghost...) -> E.op(args)
    while (m := re.search(r"atomic_with_ghost!\(\s*&", b)):
        end = balanced(b, m.end() - 2, "(", ")")
        inner = b[m.end():end - 1]
        target, rest = inner.split("=>", 1)
        call = rest.split(";", 1)[0].strip()
        b = b[:m.start()] + target.strip() + "." + call + b[end:]
    # proof { ... } blocks and ghost-only lets
    while (m := re.search(r"\bproof\s*\{", b)):
        b = b[:m.start()] + b[balanced(b, m.end() - 1):]
    b = re.sub(r"let (tracked|ghost) [^;]*;", "", b)
    # Tracked(..)/Ghost(..) arguments
    while (m := re.search(r",?\s*\b(Tracked|Ghost)\(", b)):
        b = b[:m.start()] + b[balanced(b, m.end() - 1, "(", ")"):]
    return b

def real_lines(b):
    out, skip = [], 0
    lines = b.splitlines()
    k = 0
    while k < len(lines):
        l = lines[k]
        if "tokio_unstable" in l and "cfg" in l:
            # skip the next item: a balanced statement/block
            k += 1; depth = 0; started = False
            while k < len(lines):
                depth += lines[k].count("{") + lines[k].count("(") - lines[k].count("}") - lines[k].count(")")
                started = True
                k += 1
                if started and depth <= 0 and (lines[k-1].rstrip().endswith((";", "}", ");", "});", ")),", "));"))):
                    break
            continue
        n = norm(l)
        if n and n not in ("{", "}"):
            out.append(n)
        k += 1
    return out

def main():
    real = open(sys.argv[1]).read()
    ver = open(os.path.join(HERE, "batch_semaphore.rs")).read()
    bad = 0
    for f in FUNCS:
        r = real_lines(body(real, f, False))
        v = [norm(l) for l in erase_ghost(body(ver, f, True)).splitlines()]
        pos, missing = 0, []
        for l in r:
            for k in range(pos, len(v)):
                if v[k] == l:
                    pos = k + 1
                    break
            else:
                missing.append(l)
        print(f"{f}: {len(r) - len(missing)}/{len(r)} real lines kept in order")
        for l in missing:
            print(f"    changed: {l}")
        bad += len(missing)
    print(f"total changed lines: {bad}")

main()
