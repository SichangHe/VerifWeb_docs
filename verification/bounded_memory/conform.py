"""Check that executable code in a Verus proof file equals upstream quinn code.
usage: python3 -I conform.py PROOF.rs UPSTREAM_datagrams.rs
Strips Verus-only syntax from the proof's UPSTREAM block (spec clauses, proof
blocks, named returns), strips comments/tracing from upstream, removes all
whitespace, then requires each upstream item to appear verbatim in the proof."""
import re, sys
def norm(t):
    t = re.sub(r'//[^\n]*', '', t)
    return re.sub(r'\s+', '', t)
def strip_verus(block):
    out, skip, pdepth = [], False, 0
    for l in block.split('\n'):
        s = l.strip()
        if pdepth or s.startswith('proof {'):
            pdepth += l.count('{') - l.count('}')
            continue
        if re.match(r'(requires|ensures|invariant|decreases)\b', s):
            skip = True
        if skip:
            if s == '{':
                skip = False
                out[-1] = out[-1].rstrip() + ' {'
            continue
        out.append(l)
    t = '\n'.join(out)
    t = re.sub(r'->\s*\(\w+:\s*([^\n]*?)\)\s*(\{|$)', r'-> \1 \2', t, flags=re.M)
    return t
def items(src):
    src = re.sub(r'^\s*(debug|trace)!\([^;]*\);\s*$', '', src, flags=re.M)
    names = ['pub(super) struct DatagramState', 'struct DatagramState', 'fn received', 'fn recv(',
             'struct DatagramBuffer', 'fn push_back', 'fn pop_front', 'fn memory_used', 'fn is_empty']
    res = {}
    for n in names:
        i = src.find(n, src.find('impl DatagramState') if n == 'fn recv(' else 0)
        if i < 0: continue
        j = src.rfind('\n', 0, i) + 1
        depth, k, started = 0, i, False
        while True:
            c = src[k]
            if c == '{': depth += 1; started = True
            elif c == '}': depth -= 1
            k += 1
            if started and depth == 0: break
        res[n] = src[j:k]
    return res
proof, up = open(sys.argv[1]).read(), open(sys.argv[2]).read()
block = proof[proof.index('\n// BEGIN UPSTREAM'):proof.index('\n// END UPSTREAM')]
ours = norm(strip_verus(block))
bad = 0
for n, t in items(up).items():
    if n == 'pub(super) struct DatagramState': continue
    ok = norm(t).replace('pub(super)', '').replace('#[derive(Default)]', '') in ours.replace('pub(super)', '')
    print(('OK  ' if ok else 'DIFF'), n); bad += not ok
sys.exit(1 if bad else 0)
