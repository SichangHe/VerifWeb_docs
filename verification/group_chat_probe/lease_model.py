# Explicit-state model of matrix-sdk-common cross_process_lock.rs (commit b93751e).
# Time unit = EXTEND_LEASE_EVERY_MS = 50 ms; LEASE = 500 ms = 10 units.
# Each process: guards held (bool), renew task alive (bool), known generation, dirty flag,
# and a cached-view generation (the store generation its in-memory state reflects).
# Any process may be suspended for any number of ticks (OS suspension); time keeps advancing.
from collections import deque
LEASE, TMAX = 10, 40
def try_lock(st, p, dur):
    holder, exp, gen, now = st['holder'], st['exp'], st['gen'], st['now']
    if holder is None: return dict(st, holder=p, exp=now+dur, gen=1), 1
    if holder == p or exp < now:
        g = gen if holder == p else gen + 1
        return dict(st, holder=p, exp=now+dur, gen=g), g
    return st, None
def freeze(s): return tuple(sorted((k, tuple(sorted(v.items())) if isinstance(v, dict) else v) for k, v in s.items()))
P0 = dict(guard=False, renew=False, kgen=0, dirty=False, view=0)
init = dict(holder=None, exp=0, gen=0, now=0, A=dict(P0), B=dict(P0))
def succ(s):
    out = []
    # time passes (any process may be suspended meanwhile)
    if s['now'] < TMAX: out.append(('tick', dict(s, now=s['now']+1)))
    for p in 'AB':
        me = s[p]
        if not me['guard']:  # try_lock_once with no holders
            st, g = try_lock(s, p, LEASE)
            if g is not None:
                dirty = me['dirty'] or (me['kgen'] not in (0, g))
                # caller reloads its view when dirty/first acquire (crypto: on_lock_newly_acquired)
                st = dict(st); st[p] = dict(me, guard=True, renew=True, kgen=g, dirty=False, view=st['gen'])
                out.append((p+':acquire', st))
        else:
            # critical-section write: protected state changes; bump a data version = store gen marker
            if me['view'] != s['gen'] and not me['dirty']:
                out.append((p+':STALE_WRITE', s))  # acting on stale cache while lock says clean
            if me['renew']:  # renew step (generation result ignored, as in the code)
                st, g = try_lock(s, p, LEASE)
                st = dict(st); st[p] = dict(me, renew=g is not None)
                out.append((p+':renew', st))
            st = dict(s); st[p] = dict(me, guard=False)  # drop all guards
            if me['renew']:
                st2, _ = try_lock(st, p, 0); st = dict(st2); st[p] = dict(me, guard=False, renew=False)
            out.append((p+':release', st))
    return out
seen = {freeze(init)}; q = deque([(init, [])])
while q:
    s, tr = q.popleft()
    for lab, t in succ(s):
        if 'STALE' in lab:
            print('violation:', ' -> '.join(tr + [lab])); raise SystemExit
        f = freeze(t)
        if f not in seen: seen.add(f); q.append((t, tr + [lab]))
print('no violation,', len(seen), 'states')
