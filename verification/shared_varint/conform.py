"""Check that executable code in a Verus proof file equals upstream code.
usage: python3 -I conform.py PROOF.rs UPSTREAM.rs ITEM_PREFIX...
Strips Verus-only lines from the proof's BEGIN/END UPSTREAM blocks (spec clauses,
proof blocks, ghost lets, verifier attributes, named returns), removes comments and
whitespace, then requires each named upstream item (fn or macro) to appear verbatim."""
import re, sys
def norm(t):
    return re.sub(r'\s+', '', re.sub(r'//[^\n]*', '', t))
def strip_verus(block):
    out, skip, pdepth = [], False, 0
    for l in block.split('\n'):
        s = l.strip()
        if pdepth or s.startswith('proof {'):
            pdepth += l.count('{') - l.count('}'); continue
        if s.startswith('let ghost ') or s.startswith('#[verifier::'): continue
        if re.match(r'(requires|ensures|invariant|decreases)\b', s): skip = True
        if skip:
            if s == '{': skip = False; out[-1] = out[-1].rstrip() + ' {'
            continue
        out.append(l)
    t = '\n'.join(out)
    return re.sub(r'->\s*\(\w+:\s*([^\n]*?)\)\s*(\{|$)', r'-> \1 \2', t, flags=re.M)
def item(src, prefix):
    i = src.find(prefix)
    if i < 0: sys.exit('missing upstream item ' + prefix)
    j, depth, k, started = src.rfind('\n', 0, i) + 1, 0, i, False
    while not (started and depth == 0):
        c = src[k]; k += 1
        if c == '{': depth += 1; started = True
        elif c == '}': depth -= 1
    return src[j:k]
proof, up = open(sys.argv[1]).read(), open(sys.argv[2]).read()
blocks = re.findall(r'\n// BEGIN UPSTREAM[^\n]*\n(.*?)\n// END UPSTREAM', proof, flags=re.S)
ours = norm(strip_verus('\n'.join(blocks)))
bad = 0
for n in sys.argv[3:]:
    ok = norm(item(up, n)) in ours
    print(('OK  ' if ok else 'DIFF'), n); bad += not ok
sys.exit(1 if bad else 0)
