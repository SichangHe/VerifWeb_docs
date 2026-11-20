// vlm46 live4: model corrected against automerge 0.10.0 bloom.rs and sync.rs (see NOTES.md). FIXED model: Timeout step (clears sent_hashes and in_flight) + Edit guard (no queued change depends on a fresh local change).
// Automerge sync (commit 40063d6) two-peer protocol model + safety proof.
// Changes are ints; deps(c) < c; docs are dependency-closed sets; network = per-sender set of pending
// messages (receive may keep the message = duplicate, any pending message may be delivered = reorder,
// Drop removes = loss). Bloom filter = arbitrary superset of the true set (false positives allowed).
use vstd::prelude::*;
verus! {

pub struct Have { pub last_sync: ISet<int>, pub bloom: ISet<int> }
pub struct Msg { pub heads: ISet<int>, pub need: ISet<int>, pub have: Seq<Have>, pub changes: ISet<int>, pub sync_reset: bool }
pub struct Peer {
    pub doc: ISet<int>, pub queue: ISet<int>, pub shared_heads: ISet<int>, pub last_sent_heads: ISet<int>,
    pub their_heads: Option<ISet<int>>, pub their_have: Option<Seq<Have>>, pub their_need: Option<ISet<int>>,
    pub sent_hashes: ISet<int>, pub in_flight: bool, pub have_responded: bool, pub needs_reset: bool,
    pub caps: bool,   // their_capabilities is Some: we have received some message (every message of this version carries flags)
}
pub struct World { pub peers: Seq<Peer>, pub net: Seq<ISet<Msg>> }
pub type Deps = spec_fn(int) -> ISet<int>;

pub open spec fn wf(d: Deps, n: int) -> bool {
    n >= 0 && forall|c: int, x: int| #[trigger] d(c).contains(x) ==> 0 <= x && x < c
}
pub open spec fn closed(d: Deps, s: ISet<int>) -> bool {
    forall|c: int, x: int| s.contains(c) && #[trigger] d(c).contains(x) ==> s.contains(x)
}
pub open spec fn bounded(s: ISet<int>, n: int) -> bool {
    forall|c: int| #[trigger] s.contains(c) ==> 0 <= c && c < n
}
pub open spec fn heads(d: Deps, s: ISet<int>) -> ISet<int> {
    ISet::new(|c: int| s.contains(c) && !(exists|c2: int| s.contains(c2) && #[trigger] d(c2).contains(c)))
}
pub open spec fn reach(d: Deps, h: ISet<int>, k: nat) -> ISet<int> decreases k {
    if k == 0 { h } else {
        let r = reach(d, h, (k - 1) as nat);
        ISet::new(|x: int| r.contains(x) || exists|y: int| r.contains(y) && #[trigger] d(y).contains(x))
    }
}
pub open spec fn closure(d: Deps, n: int, h: ISet<int>) -> ISet<int> { reach(d, h, n as nat) }
pub open spec fn walk(d: Deps, s: ISet<int>, q: ISet<int>, start: ISet<int>, k: nat) -> ISet<int> decreases k {
    if k == 0 { start.difference(s) } else {
        let r = walk(d, s, q, start, (k - 1) as nat);
        ISet::new(|x: int| r.contains(x)
            || (exists|y: int| r.contains(y) && q.contains(y) && #[trigger] d(y).contains(x) && !s.contains(x)))
    }
}
// missing_deps_from
pub open spec fn missing(d: Deps, n: int, s: ISet<int>, q: ISet<int>, start: ISet<int>) -> ISet<int> {
    walk(d, s, q, start, n as nat).difference(q)
}
pub open spec fn opt_set(o: Option<ISet<int>>) -> ISet<int> { match o { Some(s) => s, None => ISet::empty() } }
pub open spec fn must_reset(p: Peer) -> bool {
    match p.their_have { Some(h) => h.len() > 0 && !h[0].last_sync.subset_of(p.doc), None => false }
}
pub open spec fn all_last_sync(h: Seq<Have>) -> ISet<int> {
    ISet::new(|x: int| exists|i: int| 0 <= i < h.len() && #[trigger] h[i].last_sync.contains(x))
}
// get_hashes_to_send (bloom hits are "peer has it"; bloom misses and all their dependents are sent; plus need we have)
pub open spec fn hts_core(d: Deps, n: int, s: ISet<int>, have: Seq<Have>, need2: ISet<int>) -> ISet<int> {
    if have.len() == 0 { need2 } else {
        let hs = s.difference(closure(d, n, all_last_sync(have)));
        let miss = ISet::new(|h: int| hs.contains(h) && forall|i: int| 0 <= i < have.len() ==> !(#[trigger] have[i].bloom.contains(h)));
        let sent = ISet::new(|h: int| hs.contains(h) && exists|m: int| miss.contains(m) && closure(d, n, ISet::empty().insert(h)).contains(m));
        need2.union(sent)
    }
}
// need hashes we do not hold are dropped here; the exact code path for them is `bad` below
pub open spec fn hashes_to_send(d: Deps, n: int, s: ISet<int>, have: Seq<Have>, need: ISet<int>) -> ISet<int> {
    hts_core(d, n, s, have, need.intersect(s))
}
pub open spec fn send_set(d: Deps, n: int, p: Peer) -> ISet<int> {
    match (p.their_have, p.their_need) {
        (Some(h), Some(nd)) => hashes_to_send(d, n, p.doc, h, nd).difference(p.sent_hashes),
        _ => ISet::empty(),
    }
}
// ---- sync.rs generate_sync_message, send side
pub open spec fn their_ok(p: Peer) -> bool { p.their_have is Some && p.their_need is Some }
// get_hashes_to_send(their_have, their_need) minus sent_hashes, need NOT intersected with our doc
pub open spec fn full_set(d: Deps, n: int, p: Peer) -> ISet<int> {
    match (p.their_have, p.their_need) {
        (Some(h), Some(nd)) => hts_core(d, n, p.doc, h, nd).difference(p.sent_hashes),
        _ => ISet::empty(),
    }
}
// State::send_doc: their_heads == Some([]) (&& supports_v2, implied: their_heads is Some only after a receive)
pub open spec fn sdoc(p: Peer) -> bool { p.their_heads == Some(ISet::<int>::empty()) }
// hashes.len() > self.change_graph.len() / 3  (integer division)
pub open spec fn big(d: Deps, n: int, p: Peer) -> bool { cnt(full_set(d, n, p), n as nat) > cnt(p.doc, n as nat) / 3 }
// get_changes_by_hashes(..).ok()? fails: some hash to send is not in the document
pub open spec fn bad(d: Deps, n: int, p: Peer) -> bool {
    their_ok(p) && !sdoc(p) && !big(d, n, p) && !full_set(d, n, p).subset_of(p.doc)
}
// the hashes of the message builder (= the changes of the message)
pub open spec fn chg(d: Deps, n: int, p: Peer) -> ISet<int> {
    if their_ok(p) && (sdoc(p) || big(d, n, p)) { p.doc } else { send_set(d, n, p) }
}
// generate_sync_message returns None via the heads_equal branch
pub open spec fn report_in_sync(d: Deps, n: int, p: Peer) -> bool {
    let oh = heads(d, p.doc);
    !must_reset(p) && !bad(d, n, p) && p.last_sent_heads == oh && p.have_responded && p.their_heads == Some(oh)
        && chg(d, n, p) == ISet::<int>::empty()
}
pub open spec fn gen(d: Deps, n: int, p: Peer, bloom: ISet<int>, fake: bool) -> (Peer, Option<Msg>) {
    let oh = heads(d, p.doc);
    let need = missing(d, n, p.doc, p.queue, opt_set(p.their_heads));
    let have = if need.subset_of(opt_set(p.their_heads)) { seq![Have { last_sync: p.shared_heads, bloom: bloom }] } else { Seq::empty() };
    if must_reset(p) {
        // Message::reset: have = [Have::default()], no SYNC_RESET flag
        (p, Some(Msg { heads: oh, need: ISet::empty(), have: seq![Have { last_sync: ISet::empty(), bloom: ISet::empty() }],
                       changes: ISet::empty(), sync_reset: false }))
    } else if bad(d, n, p) {
        (p, None)
    } else {
        let send = chg(d, n, p);
        if p.last_sent_heads == oh && p.have_responded
            && ((p.their_heads == Some(oh) && send == ISet::<int>::empty()) || p.in_flight) {
            (p, None)
        } else {
            let hts = if p.needs_reset && fake { ISet::empty() } else { oh };
            let p2 = Peer { last_sent_heads: oh, sent_hashes: p.sent_hashes.union(send), in_flight: true,
                            have_responded: true, needs_reset: false, ..p };
            (p2, Some(Msg { heads: hts, need: need, have: have, changes: send, sync_reset: p.needs_reset && !fake }))
        }
    }
}
// drain of the change queue: maximal dependency-closed extension using pool
pub open spec fn drain_ok(d: Deps, s: ISet<int>, pool: ISet<int>, s2: ISet<int>) -> bool {
    s.subset_of(s2) && s2.subset_of(s.union(pool)) && closed(d, s2)
        && forall|c: int| pool.contains(c) && !s2.contains(c) ==> !(d(c).subset_of(s2))
}
pub open spec fn recv(d: Deps, n: int, p: Peer, m: Msg, s2: ISet<int>) -> Peer {
    let before = heads(d, p.doc);
    let pool = p.queue.union(m.changes);
    let newheads = heads(d, s2);
    let sh1 = if m.changes != ISet::<int>::empty() { newheads.difference(before).union(p.shared_heads.intersect(newheads)) } else { p.shared_heads };
    let known = m.heads.intersect(s2);
    let sent0 = if m.sync_reset { ISet::<int>::empty() } else { p.sent_hashes };
    let sent1 = sent0.difference(closure(d, n, known));
    let lsh1 = if m.changes == ISet::<int>::empty() && m.heads == before { m.heads } else { p.last_sent_heads };
    let all_known = known == m.heads;
    let sh2 = if all_known { m.heads } else { sh1.union(known) };
    let wipe = all_known && m.heads == ISet::<int>::empty();
    Peer { doc: s2, queue: pool.difference(s2), shared_heads: sh2,
           last_sent_heads: if wipe { ISet::empty() } else { lsh1 },
           their_heads: Some(m.heads), their_have: Some(m.have), their_need: Some(m.need),
           sent_hashes: if wipe { ISet::empty() } else { sent1 },
           in_flight: false, have_responded: p.have_responded, needs_reset: p.needs_reset, caps: true }
}

pub enum Step {
    Edit { who: int, c: int },
    Gen { who: int, bloom: ISet<int>, fake: bool },
    Recv { who: int, m: Msg, s2: ISet<int>, keep: bool },
    Drop { who: int, m: Msg },
    SetReset { who: int },
    Timeout { who: int },
}
// vlm46 fix: the bloom is built from exactly H = get_hashes(shared_heads) = doc \ closure(shared_heads).
// bloom.rs: contains_hash returns false when num_entries == 0, i.e. when H is empty the filter has no false positives.
// When H is nonempty the filter holds all of H and may have false positives on anything.
pub open spec fn bloom_ok(d: Deps, n: int, p: Peer, bloom: ISet<int>) -> bool {
    let h = p.doc.difference(closure(d, n, p.shared_heads));
    h.subset_of(bloom) && (h == ISet::<int>::empty() ==> bloom == ISet::<int>::empty())
}
pub open spec fn guard(d: Deps, n: int, w: World, st: Step) -> bool {
    match st {
        Step::Edit { who, c } => {
            let p = w.peers[who];
            (who == 0 || who == 1) && 0 <= c && c < n && !p.doc.contains(c) && !p.queue.contains(c)
            && d(c).subset_of(p.doc)
            && (forall|y: int| #[trigger] p.queue.contains(y) ==> !d(y).contains(c))
        }
        Step::Gen { who, bloom, fake } => {
            let p = w.peers[who];
            (who == 0 || who == 1)
            && bloom_ok(d, n, p, bloom)
            && fake == !p.caps   // needs_reset path: SYNC_RESET flag if the peer supports it, else heads = []
        }
        Step::Recv { who, m, s2, keep } => {
            let p = w.peers[who];
            (who == 0 || who == 1) && w.net[1 - who].contains(m)
            && bounded(p.queue.union(m.changes), n) && drain_ok(d, p.doc, p.queue.union(m.changes), s2)
            && (m.changes == ISet::<int>::empty() ==> s2 == p.doc)
        }
        Step::Drop { who, m } => (who == 0 || who == 1) && w.net[who].contains(m),
        Step::SetReset { who } => who == 0 || who == 1,
        Step::Timeout { who } => who == 0 || who == 1,
    }
}
// THE FIX: on timeout, forget what we believe is in flight and what we believe was sent.
pub open spec fn tmo(p: Peer) -> Peer { Peer { sent_hashes: ISet::empty(), in_flight: false, ..p } }
// State::set_read_only(true) then set_read_only(false): the whole state is reset, only capabilities survive
pub open spec fn set_reset(p: Peer) -> Peer {
    Peer { doc: p.doc, queue: p.queue, shared_heads: ISet::empty(), last_sent_heads: ISet::empty(), their_heads: None,
           their_have: None, their_need: None, sent_hashes: ISet::empty(), in_flight: false, have_responded: false,
           needs_reset: true, caps: p.caps }
}
pub open spec fn apply(d: Deps, n: int, w: World, st: Step) -> World {
    match st {
        Step::Edit { who, c } => {
            let p = w.peers[who];
            World { peers: w.peers.update(who, Peer { doc: p.doc.insert(c), ..p }), net: w.net }
        }
        Step::Gen { who, bloom, fake } => {
            let p = w.peers[who];
            let r = gen(d, n, p, bloom, fake);
            World { peers: w.peers.update(who, r.0),
                    net: match r.1 { Some(m) => w.net.update(who, w.net[who].insert(m)), None => w.net } }
        }
        Step::Recv { who, m, s2, keep } => {
            let p = w.peers[who];
            World { peers: w.peers.update(who, recv(d, n, p, m, s2)),
                    net: if keep { w.net } else { w.net.update(1 - who, w.net[1 - who].remove(m)) } }
        }
        Step::Drop { who, m } => World { peers: w.peers, net: w.net.update(who, w.net[who].remove(m)) },
        Step::SetReset { who } => {
            let p = w.peers[who];
            World { peers: w.peers.update(who, set_reset(p)), net: w.net }
        }
        Step::Timeout { who } => {
            let p = w.peers[who];
            World { peers: w.peers.update(who, tmo(p)), net: w.net }
        }
    }
}
pub open spec fn next(d: Deps, n: int, w: World, st: Step, w2: World) -> bool {
    guard(d, n, w, st) && w2 == apply(d, n, w, st)
}
pub open spec fn init_peer() -> Peer {
    Peer { doc: ISet::empty(), queue: ISet::empty(), shared_heads: ISet::empty(), last_sent_heads: ISet::empty(),
           their_heads: None, their_have: Some(Seq::empty()), their_need: None, sent_hashes: ISet::empty(),
           in_flight: false, have_responded: false, needs_reset: false, caps: false }
}
pub open spec fn init(w: World) -> bool {
    w.peers == seq![init_peer(), init_peer()] && w.net == seq![ISet::<Msg>::empty(), ISet::<Msg>::empty()]
}
pub open spec fn reachable(d: Deps, n: int, w: World, k: nat) -> bool decreases k {
    if k == 0 { init(w) } else {
        exists|w0: World, st: Step| reachable(d, n, w0, (k - 1) as nat) && next(d, n, w0, st, w)
    }
}

// ---------- safety ----------
pub open spec fn peer_inv(d: Deps, n: int, w: World, i: int) -> bool {
    let p = w.peers[i];
    let o = w.peers[1 - i];
    closed(d, p.doc) && bounded(p.doc, n)
    && (forall|m: Msg| #[trigger] w.net[i].contains(m) ==> exists|t: ISet<int>|
          closed(d, t) && bounded(t, n) && t.subset_of(p.doc) && heads(d, t) == m.heads)
    && (match p.their_heads { None => true, Some(h) => exists|t: ISet<int>|
          closed(d, t) && bounded(t, n) && t.subset_of(o.doc) && heads(d, t) == h })
}
pub open spec fn inv(d: Deps, n: int, w: World) -> bool {
    w.peers.len() == 2 && w.net.len() == 2 && peer_inv(d, n, w, 0) && peer_inv(d, n, w, 1)
}

// heads determine a closed set
proof fn lemma_sub(d: Deps, n: int, s: ISet<int>, t: ISet<int>, c: int)
    requires wf(d, n), closed(d, s), closed(d, t), bounded(s, n), bounded(t, n), heads(d, s) == heads(d, t), s.contains(c),
    ensures t.contains(c),
    decreases n - c,
{
    if heads(d, s).contains(c) {
        assert(heads(d, t).contains(c));
    } else {
        let c2 = choose|c2: int| s.contains(c2) && #[trigger] d(c2).contains(c);
        assert(c < c2);
        lemma_sub(d, n, s, t, c2);
        assert(t.contains(c));
    }
}
pub proof fn lemma_heads_determine(d: Deps, n: int, s: ISet<int>, t: ISet<int>)
    requires wf(d, n), closed(d, s), closed(d, t), bounded(s, n), bounded(t, n), heads(d, s) == heads(d, t),
    ensures s == t,
{
    assert forall|c: int| s.contains(c) implies t.contains(c) by { lemma_sub(d, n, s, t, c); }
    assert forall|c: int| t.contains(c) implies s.contains(c) by { lemma_sub(d, n, t, s, c); }
    assert(s =~= t);
}

pub proof fn lemma_init(d: Deps, n: int, w: World)
    requires wf(d, n), init(w), ensures inv(d, n, w),
{
    assert(w.peers.len() == 2);
    assert(w.net[0] == ISet::<Msg>::empty());
    assert(w.net[1] == ISet::<Msg>::empty());
    let e = ISet::<int>::empty();
    assert(closed(d, e)); assert(bounded(e, n));
}

// gen keeps docs and only emits messages whose heads are the heads of a closed sub-doc
proof fn lemma_step(d: Deps, n: int, w: World, st: Step, w2: World)
    requires wf(d, n), inv(d, n, w), next(d, n, w, st, w2), ensures inv(d, n, w2),
{
    let e = ISet::<int>::empty();
    assert(closed(d, e) && bounded(e, n));
    match st {
        Step::Edit { who, c } => {
            let p = w.peers[who];
            let nd = p.doc.insert(c);
            assert(closed(d, nd)) by {
                assert forall|a: int, x: int| nd.contains(a) && #[trigger] d(a).contains(x) implies nd.contains(x) by {
                    if a == c { assert(d(c).subset_of(p.doc)); assert(p.doc.contains(x)); }
                }
            }
            assert(bounded(nd, n));
            assert(w2.peers.len() == 2 && w2.net == w.net);
            assert forall|i: int| 0 <= i < 2 implies peer_inv(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { Peer { doc: nd, ..p } } else { w.peers[i] });
            }
        }
        Step::Gen { who, bloom, fake } => {
            let p = w.peers[who];
            let r = gen(d, n, p, bloom, fake);
            assert(r.0.doc == p.doc);
            assert(w2.peers.len() == 2);
            assert forall|i: int| 0 <= i < 2 implies peer_inv(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { r.0 } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { r.0 } else { w.peers[1 - i] });
                if i == who {
                    if let Some(m) = r.1 {
                        assert(w2.net[i] == w.net[i].insert(m));
                        assert(m.heads == heads(d, p.doc) || m.heads == e || m.heads == heads(d, p.doc));
                        assert(heads(d, e) == e) by { assert(heads(d, e) =~= e); }
                    }
                    assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies exists|t: ISet<int>|
                        closed(d, t) && bounded(t, n) && t.subset_of(p.doc) && heads(d, t) == m2.heads by {
                        if w.net[i].contains(m2) { } else {
                            assert(Some(m2) == r.1);
                            if m2.heads == heads(d, p.doc) {
                                assert(p.doc.subset_of(p.doc));
                            } else {
                                assert(m2.heads == e);
                                assert(heads(d, e) == e) by { assert(heads(d, e) =~= e); }
                                assert(e.subset_of(p.doc));
                            }
                        }
                    }
                } else {
                    assert(w2.net[i] == w.net[i]);
                }
            }
        }
        Step::Recv { who, m, s2, keep } => {
            let p = w.peers[who];
            let q = 1 - who;
            let p2 = recv(d, n, p, m, s2);
            assert(p2.doc == s2);
            assert(bounded(s2, n)) by {
                assert forall|c: int| s2.contains(c) implies 0 <= c && c < n by {
                    assert(p.doc.contains(c) || p.queue.union(m.changes).contains(c));
                }
            }
            assert(w2.peers.len() == 2);
            assert forall|i: int| 0 <= i < 2 implies peer_inv(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { p2 } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { p2 } else { w.peers[1 - i] });
                if i == who {
                    assert(w2.net[i] == w.net[i]);
                    assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies exists|t: ISet<int>|
                        closed(d, t) && bounded(t, n) && t.subset_of(s2) && heads(d, t) == m2.heads by {
                        let t = choose|t: ISet<int>| closed(d, t) && bounded(t, n) && t.subset_of(p.doc) && heads(d, t) == m2.heads;
                        assert(t.subset_of(s2));
                    }
                    // their_heads of receiver
                    assert(w.net[q].contains(m));
                    assert(peer_inv(d, n, w, q));
                    let t = choose|t: ISet<int>| closed(d, t) && bounded(t, n) && t.subset_of(w.peers[q].doc) && heads(d, t) == m.heads;
                    assert(closed(d, t) && bounded(t, n) && t.subset_of(w.peers[q].doc) && heads(d, t) == m.heads);
                } else {
                    // other peer: its net and its their_heads (witness inside p.doc subset s2)
                    if keep { assert(w2.net[i] == w.net[i]); } else { assert(w2.net[i] == w.net[i].remove(m)); }
                    assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies w.net[i].contains(m2) by {}
                    match w.peers[i].their_heads {
                        None => {},
                        Some(h) => {
                            let t = choose|t: ISet<int>| closed(d, t) && bounded(t, n) && t.subset_of(p.doc) && heads(d, t) == h;
                            assert(t.subset_of(s2));
                        }
                    }
                }
            }
        }
        Step::Drop { who, m } => {
            assert(w2.peers == w.peers);
            assert forall|i: int| 0 <= i < 2 implies peer_inv(d, n, w2, i) by {
                assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies w.net[i].contains(m2) by {
                    if i == who { assert(w2.net[i] == w.net[i].remove(m)); } else { assert(w2.net[i] == w.net[i]); }
                }
            }
        }
        Step::SetReset { who } => {
            let p = w.peers[who];
            assert(w2.net == w.net);
            assert forall|i: int| 0 <= i < 2 implies peer_inv(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { set_reset(p) } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { set_reset(p) } else { w.peers[1 - i] });
            }
        }
        Step::Timeout { who } => {
            let p = w.peers[who];
            assert(w2.net == w.net);
            assert forall|i: int| 0 <= i < 2 implies peer_inv(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { tmo(p) } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { tmo(p) } else { w.peers[1 - i] });
            }
        }
    }
}

// every reachable world satisfies inv (any number of drops, duplicates, reorderings)
pub proof fn theorem_inv_reachable(d: Deps, n: int, w: World, k: nat)
    requires wf(d, n), reachable(d, n, w, k), ensures inv(d, n, w),
    decreases k,
{
    if k == 0 { lemma_init(d, n, w); } else {
        reveal_with_fuel(reachable, 2);
        assert(reachable(d, n, w, k) == (exists|w0: World, st: Step| reachable(d, n, w0, (k - 1) as nat) && next(d, n, w0, st, w)));
        assert(exists|w0: World, st: Step| #[trigger] reachable(d, n, w0, (k - 1) as nat) && #[trigger] next(d, n, w0, st, w));
        let (w0, st) = choose|w0: World, st: Step| #[trigger] reachable(d, n, w0, (k - 1) as nat) && #[trigger] next(d, n, w0, st, w);
        theorem_inv_reachable(d, n, w0, (k - 1) as nat);
        lemma_step(d, n, w0, st, w);
    }
}

// SAFETY: if both peers would answer None through the heads_equal branch, their change sets are identical.
pub proof fn theorem_safety(d: Deps, n: int, w: World, k: nat)
    requires wf(d, n), reachable(d, n, w, k),
        report_in_sync(d, n, w.peers[0]), report_in_sync(d, n, w.peers[1]),
    ensures w.peers[0].doc == w.peers[1].doc,
{
    theorem_inv_reachable(d, n, w, k);
    let a = w.peers[0]; let b = w.peers[1];
    let ta = choose|t: ISet<int>| closed(d, t) && bounded(t, n) && t.subset_of(b.doc) && heads(d, t) == heads(d, a.doc);
    let tb = choose|t: ISet<int>| closed(d, t) && bounded(t, n) && t.subset_of(a.doc) && heads(d, t) == heads(d, b.doc);
    lemma_heads_determine(d, n, a.doc, ta);
    lemma_heads_determine(d, n, b.doc, tb);
    assert(a.doc =~= b.doc);
}



// =====================================================================================
// Part 2: extra invariant (needed by liveness).  xinv holds in every reachable world.
// =====================================================================================
pub open spec fn xinv_p(d: Deps, n: int, w: World, i: int) -> bool {
    let p = w.peers[i];
    let o = w.peers[1 - i];
    bounded(p.queue, n) && p.queue.subset_of(o.doc)
    && (forall|c: int| #[trigger] p.queue.contains(c) ==> !p.doc.contains(c) && !d(c).subset_of(p.doc))
    && p.shared_heads.subset_of(o.doc)
    && (match p.their_have { Some(h) => forall|k: int| 0 <= k < h.len() ==> #[trigger] h[k].last_sync.subset_of(p.doc), None => true })
    && (forall|m: Msg| #[trigger] w.net[i].contains(m) ==>
          m.changes.subset_of(p.doc) && bounded(m.changes, n)
          && (forall|k: int| 0 <= k < m.have.len() ==> #[trigger] m.have[k].last_sync.subset_of(o.doc)))
}
pub open spec fn xinv0(d: Deps, n: int, w: World) -> bool {
    w.peers.len() == 2 && w.net.len() == 2 && xinv_p(d, n, w, 0) && xinv_p(d, n, w, 1)
}
// vlm46: need hashes are always held by the peer that is asked (so the `bad` branch of gen is unreachable)
pub open spec fn ninv_p(d: Deps, n: int, w: World, i: int) -> bool {
    let p = w.peers[i];
    let o = w.peers[1 - i];
    (match p.their_need { Some(nd) => nd.subset_of(p.doc), None => true })
    && (forall|m: Msg| #[trigger] w.net[i].contains(m) ==> m.need.subset_of(o.doc))
}
pub open spec fn xinv(d: Deps, n: int, w: World) -> bool {
    xinv0(d, n, w) && ninv_p(d, n, w, 0) && ninv_p(d, n, w, 1)
}
pub open spec fn sinv(d: Deps, n: int, w: World) -> bool { inv(d, n, w) && xinv(d, n, w) }

pub proof fn lemma_xinit(d: Deps, n: int, w: World)
    requires init(w), ensures xinv(d, n, w),
{
    assert(w.net[0] == ISet::<Msg>::empty());
    assert(w.net[1] == ISet::<Msg>::empty());
    assert(w.peers[0] == init_peer() && w.peers[1] == init_peer());
    lemma_xinit0(d, n, w);
}
pub proof fn lemma_xinit0(d: Deps, n: int, w: World)
    requires init(w), ensures xinv0(d, n, w),
{
    assert(w.net[0] == ISet::<Msg>::empty());
    assert(w.net[1] == ISet::<Msg>::empty());
    let e = ISet::<int>::empty();
    assert(bounded(e, n));
    assert(e.subset_of(e));
}

proof fn lemma_gen_props(d: Deps, n: int, p: Peer, bloom: ISet<int>, fake: bool)
    ensures
        gen(d, n, p, bloom, fake).0.doc == p.doc, gen(d, n, p, bloom, fake).0.queue == p.queue,
        gen(d, n, p, bloom, fake).0.shared_heads == p.shared_heads,
        gen(d, n, p, bloom, fake).0.their_have == p.their_have,
        gen(d, n, p, bloom, fake).0.their_need == p.their_need,
        gen(d, n, p, bloom, fake).0.their_heads == p.their_heads,
        gen(d, n, p, bloom, fake).0.caps == p.caps,
        gen(d, n, p, bloom, fake).1 is Some ==> ({
            let m = gen(d, n, p, bloom, fake).1.unwrap();
            m.changes.subset_of(p.doc)
            && (forall|k: int| 0 <= k < m.have.len() ==> #[trigger] m.have[k].last_sync.subset_of(p.shared_heads))
        }),
{
    lemma_send_subset(d, n, p);
    let r = gen(d, n, p, bloom, fake);
    if r.1 is Some {
        let m = r.1.unwrap();
        assert(m.changes.subset_of(p.doc));
        assert forall|k: int| 0 <= k < m.have.len() implies #[trigger] m.have[k].last_sync.subset_of(p.shared_heads) by {
            if must_reset(p) { assert(m.have[k].last_sync == ISet::<int>::empty()); }
            else { assert(m.have[k].last_sync == p.shared_heads); }
        }
    }
}
proof fn lemma_need_sub(d: Deps, n: int, p: Peer, od: ISet<int>)
    requires closed(d, od), p.queue.subset_of(od), opt_set(p.their_heads).subset_of(od),
    ensures missing(d, n, p.doc, p.queue, opt_set(p.their_heads)).subset_of(od),
{
    lemma_walk_sub(d, p.doc, p.queue, opt_set(p.their_heads), od, n as nat);
    assert forall|x: int| missing(d, n, p.doc, p.queue, opt_set(p.their_heads)).contains(x) implies od.contains(x) by {
        assert(walk(d, p.doc, p.queue, opt_set(p.their_heads), n as nat).contains(x));
    }
}
proof fn lemma_send_subset(d: Deps, n: int, p: Peer)
    ensures send_set(d, n, p).subset_of(p.doc), chg(d, n, p).subset_of(p.doc),
{
    match (p.their_have, p.their_need) {
        (Some(h), Some(nd)) => {
            let hts = hashes_to_send(d, n, p.doc, h, nd);
            assert(hts.subset_of(p.doc)) by {
                assert forall|x: int| hts.contains(x) implies p.doc.contains(x) by {}
            }
        }
        _ => {}
    }
}
proof fn sub_tr(a: ISet<int>, b: ISet<int>, c: ISet<int>)
    requires a.subset_of(b), b.subset_of(c), ensures a.subset_of(c),
{
    assert forall|x: int| a.contains(x) implies c.contains(x) by { assert(b.contains(x)); }
}
proof fn lemma_newheads(d: Deps, s: ISet<int>, s2: ISet<int>, c: int)
    requires s.subset_of(s2), heads(d, s2).contains(c), !heads(d, s).contains(c), ensures !s.contains(c),
{
    if s.contains(c) {
        assert(s2.contains(c));
        assert(!exists|c2: int| s2.contains(c2) && #[trigger] d(c2).contains(c));
        assert(heads(d, s).contains(c));
    }
}

pub proof fn lemma_xstep(d: Deps, n: int, w: World, st: Step, w2: World)
    requires wf(d, n), inv(d, n, w), xinv(d, n, w), next(d, n, w, st, w2), ensures xinv(d, n, w2),
{
    lemma_xstep0(d, n, w, st, w2);
    lemma_step(d, n, w, st, w2);
    assert(w2.peers.len() == 2 && w2.net.len() == 2);
    assert(peer_inv(d, n, w, 0) && peer_inv(d, n, w, 1) && xinv_p(d, n, w, 0) && xinv_p(d, n, w, 1));
    assert(ninv_p(d, n, w, 0) && ninv_p(d, n, w, 1));
    match st {
        Step::Edit { who, c } => {
            let p = w.peers[who];
            assert(w2.net == w.net);
            assert forall|i: int| 0 <= i < 2 implies ninv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { Peer { doc: p.doc.insert(c), ..p } } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { Peer { doc: p.doc.insert(c), ..p } } else { w.peers[1 - i] });
                assert forall|m: Msg| #[trigger] w2.net[i].contains(m) implies m.need.subset_of(w2.peers[1 - i].doc) by {
                    assert(w.net[i].contains(m));
                    sub_tr(m.need, w.peers[1 - i].doc, w2.peers[1 - i].doc);
                }
                match w.peers[i].their_need { Some(nd) => { sub_tr(nd, w.peers[i].doc, w2.peers[i].doc); }, None => {} }
            }
        }
        Step::Gen { who, bloom, fake } => {
            let p = w.peers[who];
            let r = gen(d, n, p, bloom, fake);
            lemma_gen_props(d, n, p, bloom, fake);
            let o = w.peers[1 - who];
            assert forall|i: int| 0 <= i < 2 implies ninv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { r.0 } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { r.0 } else { w.peers[1 - i] });
                assert forall|m: Msg| #[trigger] w2.net[i].contains(m) implies m.need.subset_of(w2.peers[1 - i].doc) by {
                    if i == who {
                        match r.1 {
                            Some(m0) => {
                                assert(w2.net[i] == w.net[i].insert(m0));
                                if m0 == m {
                                    if must_reset(p) { assert(m.need =~= ISet::<int>::empty()); }
                                    else {
                                        assert(m.need == missing(d, n, p.doc, p.queue, opt_set(p.their_heads)));
                                        let th = opt_set(p.their_heads);
                                        match p.their_heads {
                                            Some(h) => {
                                                let t = choose|t: ISet<int>| closed(d, t) && bounded(t, n) && t.subset_of(o.doc) && heads(d, t) == h;
                                                assert forall|x: int| h.contains(x) implies o.doc.contains(x) by {
                                                    assert(heads(d, t).contains(x)); assert(t.contains(x));
                                                }
                                            }
                                            None => {}
                                        }
                                        lemma_need_sub(d, n, p, o.doc);
                                    }
                                } else { assert(w.net[i].contains(m)); }
                            }
                            None => { assert(w2.net[i] == w.net[i]); }
                        }
                    } else { assert(w2.net[i] == w.net[i]); assert(w.net[i].contains(m)); }
                }
            }
        }
        Step::Recv { who, m, s2, keep } => {
            let p = w.peers[who];
            let q = 1 - who;
            let p2 = recv(d, n, p, m, s2);
            assert(w.net[q].contains(m));
            assert(m.need.subset_of(p.doc));
            assert(p.doc.subset_of(s2));
            assert forall|i: int| 0 <= i < 2 implies ninv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { p2 } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { p2 } else { w.peers[1 - i] });
                assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies m2.need.subset_of(w2.peers[1 - i].doc) by {
                    if i == who { assert(w2.net[i] == w.net[i]); assert(w.net[i].contains(m2)); }
                    else {
                        assert(w.net[i].contains(m2));
                        sub_tr(m2.need, p.doc, s2);
                    }
                }
                if i == who { sub_tr(m.need, p.doc, s2); }
            }
        }
        Step::Drop { who, m } => {
            assert(w2.peers == w.peers);
            assert forall|i: int| 0 <= i < 2 implies ninv_p(d, n, w2, i) by {
                assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies w.net[i].contains(m2) by {
                    if i == who { assert(w2.net[i] == w.net[i].remove(m)); } else { assert(w2.net[i] == w.net[i]); }
                }
            }
        }
        Step::SetReset { who } => {
            let p = w.peers[who];
            assert(w2.net == w.net);
            assert forall|i: int| 0 <= i < 2 implies ninv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { set_reset(p) } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { set_reset(p) } else { w.peers[1 - i] });
            }
        }
        Step::Timeout { who } => {
            let p = w.peers[who];
            assert(w2.net == w.net);
            assert forall|i: int| 0 <= i < 2 implies ninv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { tmo(p) } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { tmo(p) } else { w.peers[1 - i] });
            }
        }
    }
}
proof fn lemma_xstep0(d: Deps, n: int, w: World, st: Step, w2: World)
    requires wf(d, n), inv(d, n, w), xinv0(d, n, w), next(d, n, w, st, w2), ensures xinv0(d, n, w2),
{
    lemma_step(d, n, w, st, w2);
    assert(w2.peers.len() == 2 && w2.net.len() == 2);
    match st {
        Step::Edit { who, c } => {
            let p = w.peers[who];
            let nd = p.doc.insert(c);
            assert forall|i: int| 0 <= i < 2 implies xinv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { Peer { doc: nd, ..p } } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { Peer { doc: nd, ..p } } else { w.peers[1 - i] });
                assert(w2.net == w.net);
                let pi = w.peers[i]; let oi = w.peers[1 - i];
                assert(p.doc.subset_of(nd));
                assert(pi.queue.subset_of(oi.doc));
                assert(pi.shared_heads.subset_of(oi.doc));
                assert(w2.peers[i].queue == pi.queue && w2.peers[i].shared_heads == pi.shared_heads);
                assert(oi.doc.subset_of(w2.peers[1 - i].doc)) by {
                    if 1 - i == who { } else { assert(w2.peers[1 - i] == oi); }
                }
                sub_tr(pi.queue, oi.doc, w2.peers[1 - i].doc);
                sub_tr(pi.shared_heads, oi.doc, w2.peers[1 - i].doc);
                assert(pi.doc.subset_of(w2.peers[i].doc)) by { if i == who { } else { assert(w2.peers[i] == pi); } }
                match pi.their_have { Some(h) => {
                    assert forall|k: int| 0 <= k < h.len() implies #[trigger] h[k].last_sync.subset_of(w2.peers[i].doc) by {
                        sub_tr(h[k].last_sync, pi.doc, w2.peers[i].doc);
                    } }, None => {} }
                assert forall|y: int| #[trigger] w2.peers[i].queue.contains(y) implies !w2.peers[i].doc.contains(y) && !d(y).subset_of(w2.peers[i].doc) by {
                    if i == who {
                        assert(pi.queue.contains(y));
                        assert(!d(y).contains(c));
                        if d(y).subset_of(nd) {
                            assert forall|x: int| d(y).contains(x) implies p.doc.contains(x) by { assert(nd.contains(x)); assert(x != c); }
                        }
                    }
                }
                assert forall|m: Msg| #[trigger] w2.net[i].contains(m) implies
                    m.changes.subset_of(w2.peers[i].doc) && bounded(m.changes, n)
                    && (forall|k: int| 0 <= k < m.have.len() ==> #[trigger] m.have[k].last_sync.subset_of(w2.peers[1 - i].doc)) by {
                    assert(w.net[i].contains(m));
                    sub_tr(m.changes, pi.doc, w2.peers[i].doc);
                    assert forall|k: int| 0 <= k < m.have.len() implies #[trigger] m.have[k].last_sync.subset_of(w2.peers[1 - i].doc) by {
                        sub_tr(m.have[k].last_sync, oi.doc, w2.peers[1 - i].doc);
                    }
                }
            }
        }
        Step::Gen { who, bloom, fake } => {
            let p = w.peers[who];
            let r = gen(d, n, p, bloom, fake);
            lemma_gen_props(d, n, p, bloom, fake);
            assert forall|i: int| 0 <= i < 2 implies xinv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { r.0 } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { r.0 } else { w.peers[1 - i] });
                assert forall|m: Msg| #[trigger] w2.net[i].contains(m) implies
                    m.changes.subset_of(w2.peers[i].doc) && bounded(m.changes, n)
                    && (forall|k: int| 0 <= k < m.have.len() ==> #[trigger] m.have[k].last_sync.subset_of(w2.peers[1 - i].doc)) by {
                    if i == who {
                        match r.1 {
                            Some(m0) => {
                                assert(w2.net[i] == w.net[i].insert(m0));
                                if m0 == m {
                                    assert(m.changes.subset_of(p.doc));
                                    assert forall|x: int| m.changes.contains(x) implies 0 <= x && x < n by {
                                        assert(p.doc.contains(x));
                                    }
                                    assert forall|k: int| 0 <= k < m.have.len() implies #[trigger] m.have[k].last_sync.subset_of(w2.peers[1 - i].doc) by {
                                        assert(m.have[k].last_sync.subset_of(p.shared_heads));
                                    }
                                } else { assert(w.net[i].contains(m)); }
                            }
                            None => { assert(w2.net[i] == w.net[i]); }
                        }
                    } else { assert(w2.net[i] == w.net[i]); assert(w.net[i].contains(m)); }
                }
            }
        }
        Step::Recv { who, m, s2, keep } => {
            let p = w.peers[who];
            let q = 1 - who;
            let p2 = recv(d, n, p, m, s2);
            assert(w.net[q].contains(m));
            assert(m.changes.subset_of(w.peers[q].doc) && bounded(m.changes, n));
            assert(p.doc.subset_of(s2));
            let pool = p.queue.union(m.changes);
            assert(pool.subset_of(w.peers[q].doc)) by {
                assert forall|x: int| pool.contains(x) implies w.peers[q].doc.contains(x) by {
                    if p.queue.contains(x) { assert(p.queue.subset_of(w.peers[q].doc)); }
                }
            }
            let t = choose|t: ISet<int>| closed(d, t) && bounded(t, n) && t.subset_of(w.peers[q].doc) && heads(d, t) == m.heads;
            assert(m.heads.subset_of(w.peers[q].doc)) by {
                assert forall|x: int| m.heads.contains(x) implies w.peers[q].doc.contains(x) by {
                    assert(heads(d, t).contains(x)); assert(t.contains(x));
                }
            }
            assert(p2.shared_heads.subset_of(w.peers[q].doc)) by {
                let before = heads(d, p.doc);
                let newheads = heads(d, s2);
                let known = m.heads.intersect(s2);
                assert forall|x: int| p2.shared_heads.contains(x) implies w.peers[q].doc.contains(x) by {
                    if known == m.heads {
                        assert(p2.shared_heads == m.heads);
                    } else {
                        if m.changes != ISet::<int>::empty() {
                            if newheads.difference(before).contains(x) {
                                lemma_newheads(d, p.doc, s2, x);
                                assert(s2.contains(x));
                                assert(pool.contains(x));
                            }
                        }
                    }
                }
            }
            assert forall|i: int| 0 <= i < 2 implies xinv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { p2 } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { p2 } else { w.peers[1 - i] });
                if i == who {
                    assert(w2.net[i] == w.net[i]);
                    assert(p2.queue == pool.difference(s2));
                    assert forall|x: int| #[trigger] p2.queue.contains(x) implies 0 <= x && x < n by {
                        assert(bounded(pool, n)); assert(pool.contains(x));
                    }
                    assert forall|x: int| #[trigger] p2.queue.contains(x) implies !p2.doc.contains(x) && !d(x).subset_of(p2.doc) by {
                        assert(pool.contains(x) && !s2.contains(x));
                    }
                    assert(p2.queue.subset_of(w.peers[q].doc));
                    match p2.their_have { Some(h) => {
                        assert forall|k: int| 0 <= k < h.len() implies #[trigger] h[k].last_sync.subset_of(p2.doc) by {
                            assert(m.have[k].last_sync.subset_of(w.peers[who].doc));
                            assert(h == m.have);
                        } }, None => {} }
                    assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies
                        m2.changes.subset_of(p2.doc) && bounded(m2.changes, n)
                        && (forall|k: int| 0 <= k < m2.have.len() ==> #[trigger] m2.have[k].last_sync.subset_of(w2.peers[1 - i].doc)) by {
                        assert(w.net[i].contains(m2));
                    }
                } else {
                    assert forall|x: int| w2.peers[i].queue.contains(x) implies w2.peers[1 - i].doc.contains(x) by {
                        assert(w.peers[i].queue.subset_of(w.peers[1 - i].doc));
                    }
                    assert(w.peers[i].shared_heads.subset_of(s2));
                    assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies
                        m2.changes.subset_of(w2.peers[i].doc) && bounded(m2.changes, n)
                        && (forall|k: int| 0 <= k < m2.have.len() ==> #[trigger] m2.have[k].last_sync.subset_of(w2.peers[1 - i].doc)) by {
                        assert(w.net[i].contains(m2));
                        if keep { assert(w2.net[i] == w.net[i]); } else { assert(w2.net[i] == w.net[i].remove(m)); }
                        assert forall|k: int| 0 <= k < m2.have.len() implies #[trigger] m2.have[k].last_sync.subset_of(w2.peers[1 - i].doc) by {
                            assert(m2.have[k].last_sync.subset_of(w.peers[1 - i].doc));
                        }
                    }
                }
            }
        }
        Step::Drop { who, m } => {
            assert(w2.peers == w.peers);
            assert forall|i: int| 0 <= i < 2 implies xinv_p(d, n, w2, i) by {
                assert forall|m2: Msg| #[trigger] w2.net[i].contains(m2) implies w.net[i].contains(m2) by {
                    if i == who { assert(w2.net[i] == w.net[i].remove(m)); } else { assert(w2.net[i] == w.net[i]); }
                }
            }
        }
        Step::SetReset { who } => {
            let p = w.peers[who];
            assert(w2.net == w.net);
            assert forall|i: int| 0 <= i < 2 implies xinv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { set_reset(p) } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { set_reset(p) } else { w.peers[1 - i] });
            }
        }
        Step::Timeout { who } => {
            let p = w.peers[who];
            assert(w2.net == w.net);
            assert forall|i: int| 0 <= i < 2 implies xinv_p(d, n, w2, i) by {
                assert(w2.peers[i] == if i == who { tmo(p) } else { w.peers[i] });
                assert(w2.peers[1 - i] == if 1 - i == who { tmo(p) } else { w.peers[1 - i] });
            }
        }
    }
}

pub proof fn theorem_sinv_reachable(d: Deps, n: int, w: World, k: nat)
    requires wf(d, n), reachable(d, n, w, k), ensures sinv(d, n, w),
    decreases k,
{
    if k == 0 { lemma_init(d, n, w); lemma_xinit(d, n, w); } else {
        reveal_with_fuel(reachable, 2);
        assert(reachable(d, n, w, k) == (exists|w0: World, st: Step| reachable(d, n, w0, (k - 1) as nat) && next(d, n, w0, st, w)));
        assert(exists|w0: World, st: Step| #[trigger] reachable(d, n, w0, (k - 1) as nat) && #[trigger] next(d, n, w0, st, w));
        let (w0, st) = choose|w0: World, st: Step| #[trigger] reachable(d, n, w0, (k - 1) as nat) && #[trigger] next(d, n, w0, st, w);
        theorem_sinv_reachable(d, n, w0, (k - 1) as nat);
        lemma_step(d, n, w0, st, w);
        lemma_xstep(d, n, w0, st, w);
    }
}

// =====================================================================================
// Part 3: counting measure and step monotonicity (no edits)
// =====================================================================================
pub open spec fn cnt(s: ISet<int>, k: nat) -> nat decreases k {
    if k == 0 { 0 } else { cnt(s, (k - 1) as nat) + (if s.contains((k - 1) as int) { 1nat } else { 0nat }) }
}
proof fn cnt_mono(s: ISet<int>, t: ISet<int>, k: nat)
    requires s.subset_of(t), ensures cnt(s, k) <= cnt(t, k), decreases k,
{ if k > 0 { cnt_mono(s, t, (k - 1) as nat); } }
proof fn cnt_eq(s: ISet<int>, t: ISet<int>, k: nat)
    requires s.subset_of(t), cnt(s, k) == cnt(t, k),
    ensures forall|c: int| 0 <= c < k && t.contains(c) ==> s.contains(c), decreases k,
{
    if k > 0 {
        cnt_mono(s, t, (k - 1) as nat);
        cnt_eq(s, t, (k - 1) as nat);
        assert(s.contains((k - 1) as int) == t.contains((k - 1) as int));
    }
}

pub open spec fn gset(w: World, a: int) -> ISet<int> { w.peers[1 - a].doc.difference(w.peers[a].doc) }
pub open spec fn rset(w: World, a: int) -> ISet<int> { w.peers[1 - a].doc.difference(w.peers[a].doc.union(w.peers[a].queue)) }
pub open spec fn phi(n: int, w: World) -> nat {
    cnt(gset(w, 0), n as nat) + cnt(gset(w, 1), n as nat) + cnt(rset(w, 0), n as nat) + cnt(rset(w, 1), n as nat)
}
pub open spec fn rel_i(w: World, w2: World, i: int) -> bool {
    w.peers[i].doc.subset_of(w2.peers[i].doc)
    && w2.peers[i].doc.subset_of(w.peers[i].doc.union(w.peers[1 - i].doc))
    && gset(w2, i).subset_of(gset(w, i)) && rset(w2, i).subset_of(rset(w, i))
}
pub open spec fn rel(w: World, w2: World) -> bool { rel_i(w, w2, 0) && rel_i(w, w2, 1) }

pub proof fn lemma_rel_trans(w: World, w1: World, w2: World)
    requires w.peers.len() == 2, w1.peers.len() == 2, w2.peers.len() == 2, rel(w, w1), rel(w1, w2), ensures rel(w, w2),
{
    assert forall|i: int| 0 <= i < 2 implies rel_i(w, w2, i) by {
        assert(rel_i(w, w1, i) && rel_i(w1, w2, i) && rel_i(w, w1, 1 - i) && rel_i(w1, w2, 1 - i));
        assert forall|x: int| w.peers[i].doc.contains(x) implies w2.peers[i].doc.contains(x) by {
            assert(w1.peers[i].doc.contains(x));
        }
        assert forall|x: int| w2.peers[i].doc.contains(x) implies w.peers[i].doc.union(w.peers[1 - i].doc).contains(x) by {
            if !w1.peers[i].doc.contains(x) { assert(w1.peers[1 - i].doc.contains(x)); }
        }
        assert forall|x: int| gset(w2, i).contains(x) implies gset(w, i).contains(x) by { assert(gset(w1, i).contains(x)); }
        assert forall|x: int| rset(w2, i).contains(x) implies rset(w, i).contains(x) by { assert(rset(w1, i).contains(x)); }
    }
}
pub proof fn lemma_rel_refl(w: World)
    requires w.peers.len() == 2, ensures rel(w, w),
{
    assert forall|i: int| 0 <= i < 2 implies rel_i(w, w, i) by {
        assert forall|x: int| w.peers[i].doc.contains(x) implies w.peers[i].doc.union(w.peers[1 - i].doc).contains(x) by {}
    }
}
pub proof fn lemma_phi_le(n: int, w: World, w2: World)
    requires n >= 0, w.peers.len() == 2, w2.peers.len() == 2, rel(w, w2), ensures phi(n, w2) <= phi(n, w),
{
    cnt_mono(gset(w2, 0), gset(w, 0), n as nat); cnt_mono(gset(w2, 1), gset(w, 1), n as nat);
    cnt_mono(rset(w2, 0), rset(w, 0), n as nat); cnt_mono(rset(w2, 1), rset(w, 1), n as nat);
}

pub open spec fn passive_step(st: Step) -> bool { match st { Step::Edit { .. } => false, _ => true } }

pub proof fn lemma_rel_step(d: Deps, n: int, w: World, st: Step, w2: World)
    requires wf(d, n), inv(d, n, w), xinv(d, n, w), next(d, n, w, st, w2), passive_step(st), ensures rel(w, w2),
{
    lemma_xstep(d, n, w, st, w2);
    lemma_step(d, n, w, st, w2);
    assert(w2.peers.len() == 2);
    match st {
        Step::Recv { who, m, s2, keep } => {
            let p = w.peers[who];
            let q = 1 - who;
            let p2 = recv(d, n, p, m, s2);
            let pool = p.queue.union(m.changes);
            assert(w.net[q].contains(m));
            assert(pool.subset_of(w.peers[q].doc)) by {
                assert forall|x: int| pool.contains(x) implies w.peers[q].doc.contains(x) by {
                    if p.queue.contains(x) { assert(p.queue.subset_of(w.peers[q].doc)); }
                }
            }
            assert(w2.peers[who] == p2 && w2.peers[q] == w.peers[q]);
            assert forall|i: int| 0 <= i < 2 implies rel_i(w, w2, i) by {
                if i == who {
                    assert(p.doc.subset_of(s2) && s2.subset_of(p.doc.union(pool)));
                    assert forall|x: int| s2.contains(x) implies p.doc.union(w.peers[q].doc).contains(x) by {
                        if !p.doc.contains(x) { assert(pool.contains(x)); }
                    }
                    assert forall|x: int| gset(w2, i).contains(x) implies gset(w, i).contains(x) by {}
                    assert forall|x: int| rset(w2, i).contains(x) implies rset(w, i).contains(x) by {
                        assert(!p2.doc.contains(x) && !p2.queue.contains(x));
                        if p.queue.contains(x) { assert(pool.contains(x)); assert(s2.contains(x) || p2.queue.contains(x)); }
                    }
                } else {
                    assert forall|x: int| gset(w2, i).contains(x) implies gset(w, i).contains(x) by {
                        if !p.doc.contains(x) { assert(pool.contains(x)); }
                    }
                    assert forall|x: int| rset(w2, i).contains(x) implies rset(w, i).contains(x) by {
                        if !p.doc.contains(x) { assert(pool.contains(x)); }
                    }
                    assert forall|x: int| w.peers[i].doc.contains(x) implies w.peers[i].doc.union(w.peers[1 - i].doc).contains(x) by {}
                }
            }
        }
        Step::Gen { who, bloom, fake } => {
            let p = w.peers[who];
            lemma_gen_props(d, n, p, bloom, fake);
            let r = gen(d, n, p, bloom, fake);
            assert(w2.peers[who] == r.0);
            assert forall|i: int| 0 <= i < 2 implies rel_i(w, w2, i) by {
                assert(w2.peers[i].doc == w.peers[i].doc && w2.peers[i].queue == w.peers[i].queue);
                assert(w2.peers[1 - i].doc == w.peers[1 - i].doc && w2.peers[1 - i].queue == w.peers[1 - i].queue);
                assert forall|x: int| w.peers[i].doc.contains(x) implies w.peers[i].doc.union(w.peers[1 - i].doc).contains(x) by {}
                assert(gset(w2, i) == gset(w, i) && rset(w2, i) == rset(w, i));
                assert(gset(w2, i).subset_of(gset(w, i)) && rset(w2, i).subset_of(rset(w, i)));
            }
        }
        Step::Timeout { who } => {
            assert forall|i: int| 0 <= i < 2 implies rel_i(w, w2, i) by {
                assert(w2.peers[i].doc == w.peers[i].doc && w2.peers[i].queue == w.peers[i].queue);
                assert(w2.peers[1 - i].doc == w.peers[1 - i].doc && w2.peers[1 - i].queue == w.peers[1 - i].queue);
                assert forall|x: int| w.peers[i].doc.contains(x) implies w.peers[i].doc.union(w.peers[1 - i].doc).contains(x) by {}
                assert(gset(w2, i) == gset(w, i) && rset(w2, i) == rset(w, i));
                assert(gset(w2, i).subset_of(gset(w, i)) && rset(w2, i).subset_of(rset(w, i)));
            }
        }
        _ => {
            assert forall|i: int| 0 <= i < 2 implies rel_i(w, w2, i) by {
                assert(w2.peers[i].doc == w.peers[i].doc && w2.peers[i].queue == w.peers[i].queue);
                assert(w2.peers[1 - i].doc == w.peers[1 - i].doc && w2.peers[1 - i].queue == w.peers[1 - i].queue);
                assert forall|x: int| w.peers[i].doc.contains(x) implies w.peers[i].doc.union(w.peers[1 - i].doc).contains(x) by {}
                assert(gset(w2, i) == gset(w, i) && rset(w2, i) == rset(w, i));
                assert(gset(w2, i).subset_of(gset(w, i)) && rset(w2, i).subset_of(rset(w, i)));
            }
        }
    }
}

// =====================================================================================
// Part 4: lock-step rounds (a particular scheduler of the model; every round is 4-6 model steps)
//   Timeout A; Timeout B; Gen A; Gen B; then each generated message is either dropped (loss) or received.
// =====================================================================================
pub struct RP {
    pub ba: ISet<int>, pub fa: bool, pub bb: ISet<int>, pub fb: bool,
    pub s2a: ISet<int>, pub s2b: ISet<int>, pub lossa: bool, pub lossb: bool,
}
pub open spec fn rw1(d: Deps, n: int, w: World) -> World { apply(d, n, w, Step::Timeout { who: 0 }) }
pub open spec fn rw2(d: Deps, n: int, w: World) -> World { apply(d, n, rw1(d, n, w), Step::Timeout { who: 1 }) }
pub open spec fn rw3(d: Deps, n: int, w: World, rp: RP) -> World { apply(d, n, rw2(d, n, w), Step::Gen { who: 0, bloom: rp.ba, fake: rp.fa }) }
pub open spec fn rw4(d: Deps, n: int, w: World, rp: RP) -> World { apply(d, n, rw3(d, n, w, rp), Step::Gen { who: 1, bloom: rp.bb, fake: rp.fb }) }
pub open spec fn msg_a(d: Deps, n: int, w: World, rp: RP) -> Option<Msg> { gen(d, n, rw2(d, n, w).peers[0], rp.ba, rp.fa).1 }
pub open spec fn msg_b(d: Deps, n: int, w: World, rp: RP) -> Option<Msg> { gen(d, n, rw3(d, n, w, rp).peers[1], rp.bb, rp.fb).1 }
pub open spec fn st5(rp: RP, m: Msg) -> Step {
    if rp.lossa { Step::Drop { who: 0, m } } else { Step::Recv { who: 1, m, s2: rp.s2b, keep: false } }
}
pub open spec fn st6(rp: RP, m: Msg) -> Step {
    if rp.lossb { Step::Drop { who: 1, m } } else { Step::Recv { who: 0, m, s2: rp.s2a, keep: false } }
}
pub open spec fn rw5(d: Deps, n: int, w: World, rp: RP) -> World {
    match msg_a(d, n, w, rp) { Some(m) => apply(d, n, rw4(d, n, w, rp), st5(rp, m)), None => rw4(d, n, w, rp) }
}
pub open spec fn rw6(d: Deps, n: int, w: World, rp: RP) -> World {
    match msg_b(d, n, w, rp) { Some(m) => apply(d, n, rw5(d, n, w, rp), st6(rp, m)), None => rw5(d, n, w, rp) }
}
pub open spec fn rvalid(d: Deps, n: int, w: World, rp: RP) -> bool {
    guard(d, n, w, Step::Timeout { who: 0 })
    && guard(d, n, rw1(d, n, w), Step::Timeout { who: 1 })
    && guard(d, n, rw2(d, n, w), Step::Gen { who: 0, bloom: rp.ba, fake: rp.fa })
    && guard(d, n, rw3(d, n, w, rp), Step::Gen { who: 1, bloom: rp.bb, fake: rp.fb })
    && (match msg_a(d, n, w, rp) { Some(m) => guard(d, n, rw4(d, n, w, rp), st5(rp, m)), None => true })
    && (match msg_b(d, n, w, rp) { Some(m) => guard(d, n, rw5(d, n, w, rp), st6(rp, m)), None => true })
}
pub open spec fn good(rp: RP) -> bool { !rp.lossa && !rp.lossb }

proof fn lemma_one(d: Deps, n: int, w: World, st: Step, w2: World)
    requires wf(d, n), sinv(d, n, w), next(d, n, w, st, w2), passive_step(st), ensures sinv(d, n, w2), rel(w, w2),
{
    lemma_step(d, n, w, st, w2); lemma_xstep(d, n, w, st, w2); lemma_rel_step(d, n, w, st, w2);
}

pub proof fn lemma_round(d: Deps, n: int, w: World, rp: RP)
    requires wf(d, n), sinv(d, n, w), rvalid(d, n, w, rp),
    ensures sinv(d, n, rw6(d, n, w, rp)), rel(w, rw6(d, n, w, rp)),
{
    let w1 = rw1(d, n, w); let w2 = rw2(d, n, w); let w3 = rw3(d, n, w, rp); let w4 = rw4(d, n, w, rp);
    let w5 = rw5(d, n, w, rp); let w6 = rw6(d, n, w, rp);
    lemma_one(d, n, w, Step::Timeout { who: 0 }, w1);
    lemma_one(d, n, w1, Step::Timeout { who: 1 }, w2);
    lemma_one(d, n, w2, Step::Gen { who: 0, bloom: rp.ba, fake: rp.fa }, w3);
    lemma_one(d, n, w3, Step::Gen { who: 1, bloom: rp.bb, fake: rp.fb }, w4);
    lemma_rel_trans(w, w1, w2); lemma_rel_trans(w, w2, w3); lemma_rel_trans(w, w3, w4);
    match msg_a(d, n, w, rp) {
        Some(m) => { lemma_one(d, n, w4, st5(rp, m), w5); lemma_rel_trans(w, w4, w5); }
        None => { lemma_rel_refl(w4); lemma_rel_trans(w, w4, w5); }
    }
    match msg_b(d, n, w, rp) {
        Some(m) => { lemma_one(d, n, w5, st6(rp, m), w6); lemma_rel_trans(w, w5, w6); }
        None => { lemma_rel_refl(w5); lemma_rel_trans(w, w5, w6); }
    }
}

// peer-level view of a round
pub open spec fn tga(d: Deps, n: int, w: World, rp: RP) -> (Peer, Option<Msg>) { gen(d, n, tmo(w.peers[0]), rp.ba, rp.fa) }
pub open spec fn tgb(d: Deps, n: int, w: World, rp: RP) -> (Peer, Option<Msg>) { gen(d, n, tmo(w.peers[1]), rp.bb, rp.fb) }
pub open spec fn fin_b(d: Deps, n: int, w: World, rp: RP) -> Peer {
    match tga(d, n, w, rp).1 {
        Some(m) => if rp.lossa { tgb(d, n, w, rp).0 } else { recv(d, n, tgb(d, n, w, rp).0, m, rp.s2b) },
        None => tgb(d, n, w, rp).0,
    }
}
pub open spec fn fin_a(d: Deps, n: int, w: World, rp: RP) -> Peer {
    match tgb(d, n, w, rp).1 {
        Some(m) => if rp.lossb { tga(d, n, w, rp).0 } else { recv(d, n, tga(d, n, w, rp).0, m, rp.s2a) },
        None => tga(d, n, w, rp).0,
    }
}
pub proof fn lemma_round_peers(d: Deps, n: int, w: World, rp: RP)
    requires wf(d, n), sinv(d, n, w), rvalid(d, n, w, rp),
    ensures rw6(d, n, w, rp).peers.len() == 2, rw6(d, n, w, rp).peers[0] == fin_a(d, n, w, rp), rw6(d, n, w, rp).peers[1] == fin_b(d, n, w, rp),
{
    let w1 = rw1(d, n, w); let w2 = rw2(d, n, w); let w3 = rw3(d, n, w, rp); let w4 = rw4(d, n, w, rp);
    let w5 = rw5(d, n, w, rp); let w6 = rw6(d, n, w, rp);
    assert(w.peers.len() == 2);
    assert(w1.peers == w.peers.update(0, tmo(w.peers[0])));
    assert(w2.peers == w1.peers.update(1, tmo(w.peers[1])));
    assert(w2.peers[0] == tmo(w.peers[0]) && w2.peers[1] == tmo(w.peers[1]));
    assert(w2.net == w.net);
    let ga = tga(d, n, w, rp);
    assert(w3.peers == w2.peers.update(0, ga.0));
    assert(w3.peers[1] == tmo(w.peers[1]));
    let gb = tgb(d, n, w, rp);
    assert(w4.peers == w3.peers.update(1, gb.0));
    assert(w4.peers[0] == ga.0 && w4.peers[1] == gb.0 && w4.peers.len() == 2);
    match msg_a(d, n, w, rp) {
        Some(m) => {
            if rp.lossa { assert(w5.peers == w4.peers); }
            else { assert(w5.peers == w4.peers.update(1, recv(d, n, w4.peers[1], m, rp.s2b))); }
        }
        None => {}
    }
    assert(w5.peers.len() == 2);
    assert(w5.peers[0] == ga.0);
    match msg_b(d, n, w, rp) {
        Some(m) => {
            if rp.lossb { assert(w6.peers == w5.peers); }
            else { assert(w6.peers == w5.peers.update(0, recv(d, n, w5.peers[0], m, rp.s2a))); }
        }
        None => {}
    }
}

// =====================================================================================
// Part 5: one round, facts about the sender's message and the receiver's resulting state
// =====================================================================================
proof fn lemma_head_out(d: Deps, n: int, sb: ISet<int>, sa: ISet<int>, c: int)
    requires wf(d, n), closed(d, sa), bounded(sb, n), sb.contains(c), !sa.contains(c),
    ensures exists|h: int| heads(d, sb).contains(h) && !sa.contains(h),
    decreases n - c,
{
    if !heads(d, sb).contains(c) {
        let c2 = choose|c2: int| sb.contains(c2) && #[trigger] d(c2).contains(c);
        assert(!sa.contains(c2)) by { if sa.contains(c2) { assert(sa.contains(c)); } }
        assert(c < c2);
        lemma_head_out(d, n, sb, sa, c2);
    }
}
proof fn lemma_heads_ne(d: Deps, n: int, sa: ISet<int>, sb: ISet<int>)
    requires wf(d, n), closed(d, sa), closed(d, sb), bounded(sa, n), bounded(sb, n), !sb.subset_of(sa),
    ensures heads(d, sb) != heads(d, sa),
{
    if heads(d, sb) == heads(d, sa) {
        lemma_heads_determine(d, n, sa, sb);
        assert(sb.subset_of(sa));
    }
}
proof fn lemma_not_known(d: Deps, n: int, w: World, a: int)
    requires wf(d, n), sinv(d, n, w), 0 <= a < 2, !w.peers[1 - a].doc.subset_of(w.peers[a].doc),
    ensures w.peers[1 - a].their_heads != Some(heads(d, w.peers[1 - a].doc)),
{
    let b = 1 - a;
    assert(peer_inv(d, n, w, b));
    if w.peers[b].their_heads == Some(heads(d, w.peers[b].doc)) {
        let t = choose|t: ISet<int>| closed(d, t) && bounded(t, n) && t.subset_of(w.peers[a].doc) && heads(d, t) == heads(d, w.peers[b].doc);
        lemma_heads_determine(d, n, w.peers[b].doc, t);
        assert(w.peers[b].doc.subset_of(w.peers[a].doc));
    }
}
proof fn lemma_no_reset(d: Deps, n: int, w: World, i: int)
    requires sinv(d, n, w), 0 <= i < 2, ensures !must_reset(w.peers[i]),
{
    assert(xinv_p(d, n, w, i));
    match w.peers[i].their_have {
        Some(h) => { if h.len() > 0 { assert(h[0].last_sync.subset_of(w.peers[i].doc)); } }
        None => {}
    }
}
proof fn lemma_not_bad(d: Deps, n: int, p: Peer)
    requires match p.their_need { Some(nd) => nd.subset_of(p.doc), None => true },
    ensures !bad(d, n, p),
{
    if their_ok(p) && !sdoc(p) && !big(d, n, p) {
        let h = p.their_have.unwrap(); let nd = p.their_need.unwrap();
        assert(full_set(d, n, p).subset_of(p.doc)) by {
            assert forall|x: int| full_set(d, n, p).contains(x) implies p.doc.contains(x) by {
                assert(hts_core(d, n, p.doc, h, nd).contains(x));
            }
        }
    }
}
proof fn lemma_gen_ns(d: Deps, n: int, p: Peer, bloom: ISet<int>, fake: bool)
    requires !must_reset(p), !bad(d, n, p), !p.in_flight, p.their_heads != Some(heads(d, p.doc)),
    ensures
        gen(d, n, p, bloom, fake).1 is Some,
        ({ let m = gen(d, n, p, bloom, fake).1.unwrap();
           m.heads == (if p.needs_reset && fake { ISet::<int>::empty() } else { heads(d, p.doc) })
           && m.need == missing(d, n, p.doc, p.queue, opt_set(p.their_heads))
           && m.changes == chg(d, n, p) && m.sync_reset == (p.needs_reset && !fake) }),
        gen(d, n, p, bloom, fake).0.needs_reset == false,
        gen(d, n, p, bloom, fake).0.their_heads == p.their_heads,
{}

// ---- walk / missing
proof fn lemma_walk_notin(d: Deps, s: ISet<int>, q: ISet<int>, st: ISet<int>, k: nat, x: int)
    requires walk(d, s, q, st, k).contains(x), ensures !s.contains(x), decreases k,
{
    if k > 0 {
        if walk(d, s, q, st, (k - 1) as nat).contains(x) { lemma_walk_notin(d, s, q, st, (k - 1) as nat, x); }
    }
}
proof fn lemma_walk_sub(d: Deps, s: ISet<int>, q: ISet<int>, st: ISet<int>, t: ISet<int>, k: nat)
    requires closed(d, t), st.subset_of(t), ensures walk(d, s, q, st, k).subset_of(t), decreases k,
{
    if k > 0 {
        lemma_walk_sub(d, s, q, st, t, (k - 1) as nat);
        let r = walk(d, s, q, st, (k - 1) as nat);
        assert forall|x: int| walk(d, s, q, st, k).contains(x) implies t.contains(x) by {
            if !r.contains(x) {
                let y = choose|y: int| r.contains(y) && q.contains(y) && #[trigger] d(y).contains(x) && !s.contains(x);
                assert(t.contains(y));
            }
        }
    }
}
proof fn lemma_walk_mono(d: Deps, s: ISet<int>, q: ISet<int>, st: ISet<int>, k1: nat, k2: nat)
    requires k1 <= k2, ensures walk(d, s, q, st, k1).subset_of(walk(d, s, q, st, k2)), decreases k2,
{
    if k1 < k2 {
        lemma_walk_mono(d, s, q, st, k1, (k2 - 1) as nat);
        let r = walk(d, s, q, st, (k2 - 1) as nat);
        assert forall|x: int| walk(d, s, q, st, k1).contains(x) implies walk(d, s, q, st, k2).contains(x) by {
            assert(r.contains(x));
        }
    }
}
proof fn lemma_chain(d: Deps, n: int, s: ISet<int>, q: ISet<int>, st: ISet<int>, y: int, k: nat)
    requires wf(d, n), 0 <= y, walk(d, s, q, st, k).contains(y), k + y + 1 <= n,
        forall|c: int| #[trigger] q.contains(c) ==> !d(c).subset_of(s),
    ensures exists|x: int| walk(d, s, q, st, n as nat).contains(x) && !q.contains(x),
    decreases y,
{
    if !q.contains(y) {
        lemma_walk_mono(d, s, q, st, k, n as nat);
        assert(walk(d, s, q, st, n as nat).contains(y));
    } else {
        assert(!d(y).subset_of(s));
        let z = choose|z: int| d(y).contains(z) && !s.contains(z);
        assert(0 <= z && z < y);
        let r = walk(d, s, q, st, k);
        assert(walk(d, s, q, st, (k + 1) as nat).contains(z)) by { assert(r.contains(y) && q.contains(y) && d(y).contains(z) && !s.contains(z)); }
        lemma_chain(d, n, s, q, st, z, (k + 1) as nat);
    }
}
proof fn lemma_exists_missing(d: Deps, n: int, sa: ISet<int>, qa: ISet<int>, sb: ISet<int>)
    requires wf(d, n), closed(d, sa), closed(d, sb), bounded(sb, n), !sb.subset_of(sa),
        forall|c: int| #[trigger] qa.contains(c) ==> !d(c).subset_of(sa),
    ensures exists|x: int| missing(d, n, sa, qa, heads(d, sb)).contains(x) && sb.contains(x) && !sa.contains(x) && !qa.contains(x),
{
    let c = choose|c: int| sb.contains(c) && !sa.contains(c);
    lemma_head_out(d, n, sb, sa, c);
    let h = choose|h: int| heads(d, sb).contains(h) && !sa.contains(h);
    assert(sb.contains(h));
    assert(walk(d, sa, qa, heads(d, sb), 0).contains(h));
    lemma_chain(d, n, sa, qa, heads(d, sb), h, 0);
    let x = choose|x: int| walk(d, sa, qa, heads(d, sb), n as nat).contains(x) && !qa.contains(x);
    lemma_walk_sub(d, sa, qa, heads(d, sb), sb, n as nat);
    lemma_walk_notin(d, sa, qa, heads(d, sb), n as nat, x);
    assert(heads(d, sb).subset_of(sb));
}

// ---- round facts
pub open spec fn tg(d: Deps, n: int, w: World, rp: RP, c: int) -> (Peer, Option<Msg>) { if c == 0 { tga(d, n, w, rp) } else { tgb(d, n, w, rp) } }
pub open spec fn fin(d: Deps, n: int, w: World, rp: RP, c: int) -> Peer { if c == 0 { fin_a(d, n, w, rp) } else { fin_b(d, n, w, rp) } }
pub open spec fn flag(rp: RP, c: int) -> bool { if c == 0 { rp.fa } else { rp.fb } }

proof fn lemma_rw4(d: Deps, n: int, w: World, rp: RP)
    requires wf(d, n), sinv(d, n, w),
    ensures rw4(d, n, w, rp).peers.len() == 2, rw4(d, n, w, rp).peers[0] == tga(d, n, w, rp).0, rw4(d, n, w, rp).peers[1] == tgb(d, n, w, rp).0,
{
    let w1 = rw1(d, n, w); let w2 = rw2(d, n, w); let w3 = rw3(d, n, w, rp);
    assert(w2.peers[0] == tmo(w.peers[0]) && w2.peers[1] == tmo(w.peers[1]));
    assert(w3.peers == w2.peers.update(0, tga(d, n, w, rp).0));
    assert(w3.peers[1] == tmo(w.peers[1]));
}

pub proof fn lemma_msg_of(d: Deps, n: int, w: World, rp: RP, c: int)
    requires wf(d, n), sinv(d, n, w), rvalid(d, n, w, rp), good(rp), 0 <= c < 2,
        w.peers[c].their_heads != Some(heads(d, w.peers[c].doc)),
    ensures
        tg(d, n, w, rp, c).1 is Some,
        ({ let m = tg(d, n, w, rp, c).1.unwrap();
           let pc = w.peers[c];
           let fo = fin(d, n, w, rp, 1 - c);
           m.heads == (if pc.needs_reset && flag(rp, c) { ISet::<int>::empty() } else { heads(d, pc.doc) })
           && m.need == missing(d, n, pc.doc, pc.queue, opt_set(pc.their_heads))
           && m.changes == chg(d, n, tmo(pc))
           && fo.their_heads == Some(m.heads) && fo.their_need == Some(m.need) && fo.their_have == Some(m.have)
           && (forall|x: int| m.changes.contains(x) ==> fo.doc.contains(x) || fo.queue.contains(x)) }),
        fin(d, n, w, rp, c).needs_reset == false,
{
    lemma_no_reset(d, n, w, c);
    let pc = w.peers[c];
    let t = tmo(pc);
    assert(!must_reset(t));
    assert(xinv_p(d, n, w, c));
    lemma_not_bad(d, n, t);
    lemma_gen_ns(d, n, t, if c == 0 { rp.ba } else { rp.bb }, flag(rp, c));
    lemma_gen_props(d, n, t, if c == 0 { rp.ba } else { rp.bb }, flag(rp, c));
    lemma_rw4(d, n, w, rp);
    let g = tg(d, n, w, rp, c);
    let m = g.1.unwrap();
    let o = 1 - c;
    assert(w.peers.len() == 2);
    // the receiver's drain guard
    if c == 0 {
        assert(msg_a(d, n, w, rp) == g.1);
        assert(rw5(d, n, w, rp).peers.len() == 2 || true);
        assert(guard(d, n, rw4(d, n, w, rp), st5(rp, m)));
        let go = tgb(d, n, w, rp).0;
        assert(go.doc == w.peers[1].doc && go.queue == w.peers[1].queue);
        assert(drain_ok(d, go.doc, go.queue.union(m.changes), rp.s2b));
        let r = recv(d, n, go, m, rp.s2b);
        assert(fin_b(d, n, w, rp) == r);
        assert forall|x: int| m.changes.contains(x) implies r.doc.contains(x) || r.queue.contains(x) by {
            assert(go.queue.union(m.changes).contains(x));
        }
    } else {
        assert(msg_b(d, n, w, rp) == g.1);
        assert(guard(d, n, rw5(d, n, w, rp), st6(rp, m)));
        let go = tga(d, n, w, rp).0;
        // rw5 peer 0 is go (peer 0 untouched by a message to peer 1)
        let w4 = rw4(d, n, w, rp);
        let w5 = rw5(d, n, w, rp);
        match msg_a(d, n, w, rp) {
            Some(m0) => {
                if rp.lossa { assert(w5.peers == w4.peers); }
                else { assert(w5.peers == w4.peers.update(1, recv(d, n, w4.peers[1], m0, rp.s2b))); }
            }
            None => {}
        }
        assert(w5.peers[0] == go);
        assert(go.doc == w.peers[0].doc && go.queue == w.peers[0].queue);
        assert(drain_ok(d, go.doc, go.queue.union(m.changes), rp.s2a));
        let r = recv(d, n, go, m, rp.s2a);
        assert(fin_a(d, n, w, rp) == r);
        assert forall|x: int| m.changes.contains(x) implies r.doc.contains(x) || r.queue.contains(x) by {
            assert(go.queue.union(m.changes).contains(x));
        }
    }
}

// =====================================================================================
// Part 6: four good rounds strictly decrease phi unless the docs are equal
// =====================================================================================
proof fn lemma_const(d: Deps, n: int, w: World, w2: World)
    requires wf(d, n), sinv(d, n, w), sinv(d, n, w2), rel(w, w2), phi(n, w2) == phi(n, w),
    ensures forall|i: int| 0 <= i < 2 ==> (w2.peers[i].doc == w.peers[i].doc && w2.peers[i].queue == w.peers[i].queue
        && gset(w2, i) == gset(w, i) && rset(w2, i) == rset(w, i)),
{
    cnt_mono(gset(w2, 0), gset(w, 0), n as nat); cnt_mono(gset(w2, 1), gset(w, 1), n as nat);
    cnt_mono(rset(w2, 0), rset(w, 0), n as nat); cnt_mono(rset(w2, 1), rset(w, 1), n as nat);
    assert(inv(d, n, w) && inv(d, n, w2));
    assert forall|i: int| 0 <= i < 2 implies (w2.peers[i].doc == w.peers[i].doc
        && gset(w2, i) == gset(w, i) && rset(w2, i) == rset(w, i)) by {
        assert(peer_inv(d, n, w, 0) && peer_inv(d, n, w, 1) && peer_inv(d, n, w2, 0) && peer_inv(d, n, w2, 1));
        assert(rel_i(w, w2, i));
        cnt_eq(gset(w2, i), gset(w, i), n as nat);
        cnt_eq(rset(w2, i), rset(w, i), n as nat);
        assert(gset(w2, i) =~= gset(w, i)) by {
            assert forall|x: int| gset(w, i).contains(x) implies gset(w2, i).contains(x) by {
                assert(w.peers[1 - i].doc.contains(x));
                assert(bounded(w.peers[1 - i].doc, n));
            }
        }
        assert(rset(w2, i) =~= rset(w, i)) by {
            assert forall|x: int| rset(w, i).contains(x) implies rset(w2, i).contains(x) by {
                assert(w.peers[1 - i].doc.contains(x));
                assert(bounded(w.peers[1 - i].doc, n));
            }
        }
        // docs: elements gained by doc_i would leave gset
        assert forall|x: int| w2.peers[i].doc.contains(x) implies w.peers[i].doc.contains(x) by {
            if !w.peers[i].doc.contains(x) {
                assert(w.peers[1 - i].doc.contains(x));
                assert(gset(w, i).contains(x));
                assert(gset(w2, i).contains(x));
            }
        }
        assert(w2.peers[i].doc =~= w.peers[i].doc);
    }
    assert forall|i: int| 0 <= i < 2 implies w2.peers[i].queue == w.peers[i].queue by {
        assert(xinv_p(d, n, w, i) && xinv_p(d, n, w2, i));
        assert(w2.peers[i].doc == w.peers[i].doc && w2.peers[1 - i].doc == w.peers[1 - i].doc);
        assert(w2.peers[i].queue =~= w.peers[i].queue) by {
            assert forall|x: int| w2.peers[i].queue.contains(x) implies w.peers[i].queue.contains(x) by {
                assert(w2.peers[1 - i].doc.contains(x) && !w2.peers[i].doc.contains(x));
                assert(gset(w, i).contains(x));
                assert(!rset(w2, i).contains(x));
                assert(!rset(w, i).contains(x));
            }
            assert forall|x: int| w.peers[i].queue.contains(x) implies w2.peers[i].queue.contains(x) by {
                assert(w.peers[1 - i].doc.contains(x) && !w.peers[i].doc.contains(x));
                assert(gset(w2, i).contains(x));
                assert(!rset(w, i).contains(x));
                assert(!rset(w2, i).contains(x));
            }
        }
    }
}

proof fn lemma_send_has_need(d: Deps, n: int, s: ISet<int>, have: Seq<Have>, need: ISet<int>, x: int)
    requires need.contains(x), s.contains(x), ensures hashes_to_send(d, n, s, have, need).contains(x),
{}

proof fn lemma_peer_is_fin(d: Deps, n: int, w: World, rp: RP, c: int)
    requires wf(d, n), sinv(d, n, w), rvalid(d, n, w, rp), 0 <= c < 2,
    ensures rw6(d, n, w, rp).peers[c] == fin(d, n, w, rp, c),
{ lemma_round_peers(d, n, w, rp); }

pub open spec fn rnd_pre(d: Deps, n: int, w: World, rp: RP, a: int) -> bool {
    wf(d, n) && 0 <= a < 2 && sinv(d, n, w) && rvalid(d, n, w, rp) && good(rp)
    && !w.peers[1 - a].doc.subset_of(w.peers[a].doc)
}
proof fn lemma_s_flag(d: Deps, n: int, w: World, rp: RP, a: int)
    requires rnd_pre(d, n, w, rp, a), ensures rw6(d, n, w, rp).peers[1 - a].needs_reset == false,
{
    lemma_not_known(d, n, w, a);
    lemma_msg_of(d, n, w, rp, 1 - a);
    lemma_peer_is_fin(d, n, w, rp, 1 - a);
}
proof fn lemma_s_heads(d: Deps, n: int, w: World, rp: RP, a: int)
    requires rnd_pre(d, n, w, rp, a), w.peers[1 - a].needs_reset == false,
    ensures rw6(d, n, w, rp).peers[a].their_heads == Some(heads(d, w.peers[1 - a].doc)),
{
    lemma_not_known(d, n, w, a);
    lemma_msg_of(d, n, w, rp, 1 - a);
    lemma_peer_is_fin(d, n, w, rp, a);
}
proof fn lemma_s_need(d: Deps, n: int, w: World, rp: RP, a: int)
    requires rnd_pre(d, n, w, rp, a), w.peers[a].their_heads == Some(heads(d, w.peers[1 - a].doc)),
    ensures rw6(d, n, w, rp).peers[1 - a].their_need
        == Some(missing(d, n, w.peers[a].doc, w.peers[a].queue, heads(d, w.peers[1 - a].doc))),
        rw6(d, n, w, rp).peers[1 - a].their_have is Some,
{
    let b = 1 - a;
    assert(peer_inv(d, n, w, 0) && peer_inv(d, n, w, 1));
    lemma_heads_ne(d, n, w.peers[a].doc, w.peers[b].doc);
    lemma_msg_of(d, n, w, rp, a);
    lemma_peer_is_fin(d, n, w, rp, b);
}
proof fn lemma_s_send(d: Deps, n: int, w: World, rp: RP, a: int, x: int)
    requires rnd_pre(d, n, w, rp, a), w.peers[1 - a].doc.contains(x), w.peers[1 - a].their_have is Some,
        (match w.peers[1 - a].their_need { Some(nd) => nd.contains(x), None => false }),
    ensures rw6(d, n, w, rp).peers[a].doc.contains(x) || rw6(d, n, w, rp).peers[a].queue.contains(x),
{
    let b = 1 - a;
    lemma_not_known(d, n, w, a);
    lemma_msg_of(d, n, w, rp, b);
    lemma_peer_is_fin(d, n, w, rp, a);
    let pb = w.peers[b];
    let t = tmo(pb);
    match (pb.their_have, pb.their_need) {
        (Some(h), Some(nd)) => {
            lemma_send_has_need(d, n, pb.doc, h, nd, x);
            assert(t.sent_hashes == ISet::<int>::empty());
            assert(t.their_have == pb.their_have && t.their_need == pb.their_need && t.doc == pb.doc);
            assert(hashes_to_send(d, n, t.doc, h, nd).contains(x));
            assert(send_set(d, n, t).contains(x));
            assert(chg(d, n, t).contains(x));
        }
        _ => { assert(false); }
    }
}

#[verifier::spinoff_prover]
#[verifier::rlimit(60)]
pub proof fn lemma_window(d: Deps, n: int, w0: World, rp0: RP, rp1: RP, rp2: RP, rp3: RP, a: int)
    requires wf(d, n), 0 <= a < 2, sinv(d, n, w0),
        rvalid(d, n, w0, rp0), good(rp0),
        rvalid(d, n, rw6(d, n, w0, rp0), rp1), good(rp1),
        rvalid(d, n, rw6(d, n, rw6(d, n, w0, rp0), rp1), rp2), good(rp2),
        rvalid(d, n, rw6(d, n, rw6(d, n, rw6(d, n, w0, rp0), rp1), rp2), rp3), good(rp3),
        !w0.peers[1 - a].doc.subset_of(w0.peers[a].doc),
    ensures phi(n, rw6(d, n, rw6(d, n, rw6(d, n, rw6(d, n, w0, rp0), rp1), rp2), rp3)) < phi(n, w0),
{
    let b = 1 - a;
    let w1 = rw6(d, n, w0, rp0); let w2 = rw6(d, n, w1, rp1); let w3 = rw6(d, n, w2, rp2); let w4 = rw6(d, n, w3, rp3);
    lemma_round(d, n, w0, rp0); lemma_round(d, n, w1, rp1); lemma_round(d, n, w2, rp2); lemma_round(d, n, w3, rp3);
    assert(w0.peers.len() == 2 && w1.peers.len() == 2 && w2.peers.len() == 2 && w3.peers.len() == 2 && w4.peers.len() == 2);
    lemma_phi_le(n, w0, w1); lemma_phi_le(n, w1, w2); lemma_phi_le(n, w2, w3); lemma_phi_le(n, w3, w4);
    if phi(n, w4) >= phi(n, w0) {
        lemma_const(d, n, w0, w1); lemma_const(d, n, w1, w2); lemma_const(d, n, w2, w3); lemma_const(d, n, w3, w4);
        let da = w0.peers[a].doc; let db = w0.peers[b].doc; let qa = w0.peers[a].queue;
        assert(w1.peers[a].doc == da && w2.peers[a].doc == da && w3.peers[a].doc == da && w4.peers[a].doc == da);
        assert(w1.peers[b].doc == db && w2.peers[b].doc == db && w3.peers[b].doc == db && w4.peers[b].doc == db);
        assert(w1.peers[a].queue == qa && w2.peers[a].queue == qa && w3.peers[a].queue == qa);
        lemma_s_flag(d, n, w0, rp0, a);
        lemma_s_heads(d, n, w1, rp1, a);
        assert(inv(d, n, w2) && xinv(d, n, w2));
        assert(peer_inv(d, n, w0, 0) && peer_inv(d, n, w0, 1) && inv(d, n, w0));
        assert(peer_inv(d, n, w2, 0) && peer_inv(d, n, w2, 1));
        assert(xinv_p(d, n, w2, a));
        lemma_exists_missing(d, n, da, qa, db);
        let x = choose|x: int| missing(d, n, da, qa, heads(d, db)).contains(x) && db.contains(x) && !da.contains(x) && !qa.contains(x);
        lemma_s_need(d, n, w2, rp2, a);
        lemma_s_send(d, n, w3, rp3, a, x);
        assert(rset(w3, a).contains(x));
        assert(rset(w4, a) == rset(w3, a));
    }
}

// =====================================================================================
// Part 7: rounds are enabled (a drain always exists), so the liveness theorem is not vacuous
// =====================================================================================
pub open spec fn in_drain(d: Deps, s: ISet<int>, pool: ISet<int>, c: int) -> bool decreases (if c < 0 { 0int } else { c + 1 }) {
    if s.contains(c) { true } else if c < 0 || !pool.contains(c) { false } else {
        forall|x: int| #[trigger] d(c).contains(x) ==> (0 <= x && x < c && in_drain(d, s, pool, x))
    }
}
pub open spec fn drain_set(d: Deps, s: ISet<int>, pool: ISet<int>) -> ISet<int> { ISet::new(|c: int| in_drain(d, s, pool, c)) }

pub proof fn lemma_drain_exists(d: Deps, n: int, s: ISet<int>, pool: ISet<int>)
    requires wf(d, n), closed(d, s), bounded(s, n), bounded(pool, n),
    ensures drain_ok(d, s, pool, drain_set(d, s, pool)),
{
    let s2 = drain_set(d, s, pool);
    assert(s.subset_of(s2)) by { assert forall|c: int| s.contains(c) implies s2.contains(c) by { reveal_with_fuel(in_drain, 2); } }
    assert(s2.subset_of(s.union(pool))) by {
        assert forall|c: int| s2.contains(c) implies s.union(pool).contains(c) by { reveal_with_fuel(in_drain, 2); }
    }
    assert(closed(d, s2)) by {
        assert forall|c: int, x: int| s2.contains(c) && #[trigger] d(c).contains(x) implies s2.contains(x) by {
            reveal_with_fuel(in_drain, 2);
            if s.contains(c) { assert(s.contains(x)); }
        }
    }
    assert forall|c: int| pool.contains(c) && !s2.contains(c) implies !(d(c).subset_of(s2)) by {
        reveal_with_fuel(in_drain, 2);
        if d(c).subset_of(s2) {
            assert forall|x: int| #[trigger] d(c).contains(x) implies (0 <= x && x < c && in_drain(d, s, pool, x)) by {
                assert(s2.contains(x));
            }
            assert(in_drain(d, s, pool, c));
        }
    }
}

pub proof fn lemma_round_exists(d: Deps, n: int, w: World)
    requires wf(d, n), sinv(d, n, w),
    ensures exists|rp: RP| rvalid(d, n, w, rp) && good(rp),
{
    assert(inv(d, n, w) && xinv(d, n, w));
    assert(peer_inv(d, n, w, 0) && peer_inv(d, n, w, 1) && xinv_p(d, n, w, 0) && xinv_p(d, n, w, 1));
    let e = ISet::<int>::empty();
    let rp0 = RP { ba: w.peers[0].doc.difference(closure(d, n, w.peers[0].shared_heads)), fa: !w.peers[0].caps, bb: w.peers[1].doc.difference(closure(d, n, w.peers[1].shared_heads)), fb: !w.peers[1].caps, s2a: e, s2b: e, lossa: false, lossb: false };
    let w1 = rw1(d, n, w); let w2 = rw2(d, n, w); let w3 = rw3(d, n, w, rp0); let w4 = rw4(d, n, w, rp0);
    assert(w2.peers[0] == tmo(w.peers[0]) && w2.peers[1] == tmo(w.peers[1]) && w2.peers.len() == 2);
    lemma_gen_props(d, n, tmo(w.peers[0]), rp0.ba, rp0.fa);
    lemma_gen_props(d, n, tmo(w.peers[1]), rp0.bb, rp0.fb);
    lemma_rw4(d, n, w, rp0);
    let ga = tga(d, n, w, rp0); let gb = tgb(d, n, w, rp0);
    assert(w4.peers[0].doc == w.peers[0].doc && w4.peers[0].queue == w.peers[0].queue);
    assert(w4.peers[1].doc == w.peers[1].doc && w4.peers[1].queue == w.peers[1].queue);
    // s2 for B receiving A's message, s2 for A receiving B's message
    let s2b = match ga.1 {
        Some(m) => if m.changes == e { w.peers[1].doc } else { drain_set(d, w.peers[1].doc, w.peers[1].queue.union(m.changes)) },
        None => e };
    let s2a = match gb.1 {
        Some(m) => if m.changes == e { w.peers[0].doc } else { drain_set(d, w.peers[0].doc, w.peers[0].queue.union(m.changes)) },
        None => e };
    let rp = RP { s2a: s2a, s2b: s2b, ..rp0 };
    assert(rw3(d, n, w, rp) == w3 && rw4(d, n, w, rp) == w4);
    assert(msg_a(d, n, w, rp) == ga.1 && msg_b(d, n, w, rp) == gb.1);
    // recv guard facts
    match ga.1 {
        Some(m) => {
            assert(w4.net[0].contains(m)) by { assert(w4.net[0] == w3.net[0]); assert(w3.net[0] == w2.net[0].insert(m)); }
            let p = w.peers[1];
            assert(bounded(p.queue.union(m.changes), n)) by {
                assert forall|x: int| p.queue.union(m.changes).contains(x) implies 0 <= x && x < n by {
                    if !p.queue.contains(x) { assert(m.changes.subset_of(w.peers[0].doc)); assert(w.peers[0].doc.contains(x)); }
                }
            }
            if m.changes == e {
                assert(drain_ok(d, p.doc, p.queue.union(m.changes), p.doc)) by {
                    assert(p.queue.union(e) =~= p.queue);
                    assert forall|c: int| p.queue.contains(c) && !p.doc.contains(c) implies !(d(c).subset_of(p.doc)) by {}
                }
            } else { lemma_drain_exists(d, n, p.doc, p.queue.union(m.changes)); }
        }
        None => {}
    }
    let w5 = rw5(d, n, w, rp);
    match gb.1 {
        Some(m) => {
            let p = w.peers[0];
            match ga.1 {
                Some(m0) => { assert(w5.net[1] == w4.net[1]); }
                None => {}
            }
            assert(w4.net[1].contains(m)) by { assert(w4.net[1] == w3.net[1].insert(m)); }
            assert(w5.net[1].contains(m));
            assert(w5.peers.len() == 2);
            assert(w5.peers[0] == w4.peers[0]);
            assert(bounded(p.queue.union(m.changes), n)) by {
                assert forall|x: int| p.queue.union(m.changes).contains(x) implies 0 <= x && x < n by {
                    if !p.queue.contains(x) { assert(m.changes.subset_of(w.peers[1].doc)); assert(w.peers[1].doc.contains(x)); }
                }
            }
            if m.changes == e {
                assert(drain_ok(d, p.doc, p.queue.union(m.changes), p.doc)) by {
                    assert(p.queue.union(e) =~= p.queue);
                    assert forall|c: int| p.queue.contains(c) && !p.doc.contains(c) implies !(d(c).subset_of(p.doc)) by {}
                }
            } else { lemma_drain_exists(d, n, p.doc, p.queue.union(m.changes)); }
        }
        None => {}
    }
    assert(rvalid(d, n, w, rp) && good(rp));
}

// =====================================================================================
// Part 8: LIVENESS under fair-lossy rounds
//   A run is an infinite sequence of rounds starting from any reachable world (after the last local edit).
//   Fair-lossy (our formalization): for every m there are 4 consecutive loss-free rounds at some k >= m.
//   Conclusion: from some round on, the two docs are identical (and stay so).
// =====================================================================================
pub open spec fn run_ok(d: Deps, n: int, ws: spec_fn(nat) -> World, rps: spec_fn(nat) -> RP) -> bool {
    forall|k: nat| #![trigger rps(k)] rvalid(d, n, ws(k), rps(k)) && ws((k + 1) as nat) == rw6(d, n, ws(k), rps(k))
}
pub open spec fn win4(rps: spec_fn(nat) -> RP, m: nat) -> bool {
    exists|k: nat| #![trigger rps(k)] k >= m && good(rps(k)) && good(rps((k + 1) as nat))
        && good(rps((k + 2) as nat)) && good(rps((k + 3) as nat))
}
pub open spec fn fair_lossy(rps: spec_fn(nat) -> RP) -> bool { forall|m: nat| #[trigger] win4(rps, m) }

proof fn lemma_run_at(d: Deps, n: int, ws: spec_fn(nat) -> World, rps: spec_fn(nat) -> RP, k: nat)
    requires run_ok(d, n, ws, rps),
    ensures rvalid(d, n, ws(k), rps(k)), ws((k + 1) as nat) == rw6(d, n, ws(k), rps(k)),
{}
proof fn lemma_run_sinv(d: Deps, n: int, ws: spec_fn(nat) -> World, rps: spec_fn(nat) -> RP, k: nat)
    requires wf(d, n), sinv(d, n, ws(0)), run_ok(d, n, ws, rps), ensures sinv(d, n, ws(k)), decreases k,
{
    if k > 0 {
        lemma_run_sinv(d, n, ws, rps, (k - 1) as nat);
        lemma_run_at(d, n, ws, rps, (k - 1) as nat);
        lemma_round(d, n, ws((k - 1) as nat), rps((k - 1) as nat));
    }
}
proof fn lemma_run_mono(d: Deps, n: int, ws: spec_fn(nat) -> World, rps: spec_fn(nat) -> RP, i: nat, j: nat)
    requires wf(d, n), n >= 0, sinv(d, n, ws(0)), run_ok(d, n, ws, rps), i <= j,
    ensures phi(n, ws(j)) <= phi(n, ws(i)), decreases j - i,
{
    if i < j {
        lemma_run_mono(d, n, ws, rps, i, (j - 1) as nat);
        lemma_run_sinv(d, n, ws, rps, (j - 1) as nat);
        lemma_run_at(d, n, ws, rps, (j - 1) as nat);
        lemma_round(d, n, ws((j - 1) as nat), rps((j - 1) as nat));
        lemma_phi_le(n, ws((j - 1) as nat), ws(j));
    }
}
proof fn cnt_pos(s: ISet<int>, k: nat)
    requires cnt(s, k) > 0, ensures exists|c: int| 0 <= c < k && s.contains(c), decreases k,
{ if k > 0 { if cnt(s, (k - 1) as nat) > 0 { cnt_pos(s, (k - 1) as nat); } } }

// phi == 0 means identical docs
proof fn lemma_phi_zero(d: Deps, n: int, w: World)
    requires wf(d, n), sinv(d, n, w), phi(n, w) == 0, ensures w.peers[0].doc == w.peers[1].doc,
{
    assert(inv(d, n, w));
    assert(peer_inv(d, n, w, 0) && peer_inv(d, n, w, 1));
    assert(cnt(gset(w, 0), n as nat) == 0 && cnt(gset(w, 1), n as nat) == 0);
    assert forall|x: int| w.peers[1].doc.contains(x) implies w.peers[0].doc.contains(x) by {
        if !w.peers[0].doc.contains(x) { assert(gset(w, 0).contains(x)); cnt_mono(ISet::<int>::empty().insert(x), gset(w, 0), n as nat); lemma_cnt_single(x, n as nat); }
    }
    assert forall|x: int| w.peers[0].doc.contains(x) implies w.peers[1].doc.contains(x) by {
        if !w.peers[1].doc.contains(x) { assert(gset(w, 1).contains(x)); cnt_mono(ISet::<int>::empty().insert(x), gset(w, 1), n as nat); lemma_cnt_single(x, n as nat); }
    }
    assert(w.peers[0].doc =~= w.peers[1].doc);
}
proof fn lemma_cnt_single(x: int, k: nat)
    requires 0 <= x < k, ensures cnt(ISet::<int>::empty().insert(x), k) == 1, decreases k,
{
    let s = ISet::<int>::empty().insert(x);
    if k > 0 {
        if x < k - 1 { lemma_cnt_single(x, (k - 1) as nat); assert(!s.contains((k - 1) as int)); }
        else { lemma_cnt_zero_below(x, (k - 1) as nat); assert(s.contains((k - 1) as int)); }
    }
}
proof fn lemma_cnt_zero_below(x: int, k: nat)
    requires k <= x, ensures cnt(ISet::<int>::empty().insert(x), k) == 0, decreases k,
{ if k > 0 { lemma_cnt_zero_below(x, (k - 1) as nat); } }

proof fn lemma_live_from(d: Deps, n: int, ws: spec_fn(nat) -> World, rps: spec_fn(nat) -> RP, v: nat, m: nat)
    requires wf(d, n), n >= 0, sinv(d, n, ws(0)), run_ok(d, n, ws, rps), fair_lossy(rps), phi(n, ws(m)) <= v,
    ensures exists|K: nat| #![trigger ws(K)] K >= m && ws(K).peers[0].doc == ws(K).peers[1].doc,
    decreases v,
{
    assert(win4(rps, m));
    let k = choose|k: nat| #![trigger rps(k)] k >= m && good(rps(k)) && good(rps((k + 1) as nat)) && good(rps((k + 2) as nat)) && good(rps((k + 3) as nat));
    lemma_run_mono(d, n, ws, rps, m, k);
    lemma_run_sinv(d, n, ws, rps, k);
    if phi(n, ws(k)) == 0 {
        lemma_phi_zero(d, n, ws(k));
    } else {
        let w0 = ws(k);
        assert(phi(n, w0) > 0);
        // some direction has a gap
        let a = if cnt(gset(w0, 0), n as nat) > 0 { 0int } else { 1int };
        if cnt(gset(w0, 0), n as nat) == 0 && cnt(gset(w0, 1), n as nat) == 0 {
            // R sets are subsets of G sets, so their counts are 0 too
            cnt_mono(rset(w0, 0), gset(w0, 0), n as nat); cnt_mono(rset(w0, 1), gset(w0, 1), n as nat);
            assert(false);
        }
        assert(cnt(gset(w0, a), n as nat) > 0);
        cnt_pos(gset(w0, a), n as nat);
        assert(!w0.peers[1 - a].doc.subset_of(w0.peers[a].doc));
        lemma_run_at(d, n, ws, rps, k);
        lemma_run_at(d, n, ws, rps, (k + 1) as nat);
        lemma_run_at(d, n, ws, rps, (k + 2) as nat);
        lemma_run_at(d, n, ws, rps, (k + 3) as nat);
        lemma_window(d, n, w0, rps(k), rps((k + 1) as nat), rps((k + 2) as nat), rps((k + 3) as nat), a);
        lemma_live_from(d, n, ws, rps, (v - 1) as nat, (k + 4) as nat);
    }
}

// THEOREM (liveness): any fair-lossy run from a world satisfying sinv reaches identical docs.
pub proof fn theorem_liveness(d: Deps, n: int, ws: spec_fn(nat) -> World, rps: spec_fn(nat) -> RP)
    requires wf(d, n), sinv(d, n, ws(0)), run_ok(d, n, ws, rps), fair_lossy(rps),
    ensures exists|K: nat| #![trigger ws(K)] ws(K).peers[0].doc == ws(K).peers[1].doc,
{
    lemma_live_from(d, n, ws, rps, phi(n, ws(0)), 0);
}

// docs stay identical once identical (so "eventually equal" is "eventually always equal")
pub proof fn theorem_stays_equal(d: Deps, n: int, ws: spec_fn(nat) -> World, rps: spec_fn(nat) -> RP, i: nat, j: nat)
    requires wf(d, n), sinv(d, n, ws(0)), run_ok(d, n, ws, rps), i <= j, ws(i).peers[0].doc == ws(i).peers[1].doc,
    ensures ws(j).peers[0].doc == ws(j).peers[1].doc, decreases j - i,
{
    if i < j {
        theorem_stays_equal(d, n, ws, rps, i, (j - 1) as nat);
        let w = ws((j - 1) as nat);
        lemma_run_sinv(d, n, ws, rps, (j - 1) as nat);
        lemma_run_at(d, n, ws, rps, (j - 1) as nat);
        lemma_round(d, n, w, rps((j - 1) as nat));
        let w2 = ws(j);
        assert(rel(w, w2));
        assert(rel_i(w, w2, 0) && rel_i(w, w2, 1));
        assert(w.peers[0].doc.union(w.peers[1].doc) =~= w.peers[0].doc);
        assert(w2.peers[0].doc =~= w2.peers[1].doc) by {
            assert forall|x: int| w2.peers[0].doc.contains(x) implies w2.peers[1].doc.contains(x) by {
                assert(w.peers[0].doc.union(w.peers[1].doc).contains(x));
                assert(w.peers[1].doc.contains(x));
            }
            assert forall|x: int| w2.peers[1].doc.contains(x) implies w2.peers[0].doc.contains(x) by {
                assert(w.peers[1].doc.union(w.peers[0].doc).contains(x));
                assert(w.peers[0].doc.contains(x));
            }
        }
    }
}

// Every round is a sequence of model steps (so a run of rounds is an execution of the model).
pub proof fn lemma_round_is_model_steps(d: Deps, n: int, w: World, rp: RP)
    requires rvalid(d, n, w, rp),
    ensures
        next(d, n, w, Step::Timeout { who: 0 }, rw1(d, n, w)),
        next(d, n, rw1(d, n, w), Step::Timeout { who: 1 }, rw2(d, n, w)),
        next(d, n, rw2(d, n, w), Step::Gen { who: 0, bloom: rp.ba, fake: rp.fa }, rw3(d, n, w, rp)),
        next(d, n, rw3(d, n, w, rp), Step::Gen { who: 1, bloom: rp.bb, fake: rp.fb }, rw4(d, n, w, rp)),
        (match msg_a(d, n, w, rp) { Some(m) => next(d, n, rw4(d, n, w, rp), st5(rp, m), rw5(d, n, w, rp)), None => true }),
        (match msg_b(d, n, w, rp) { Some(m) => next(d, n, rw5(d, n, w, rp), st6(rp, m), rw6(d, n, w, rp)), None => true }),
{}

// Liveness from any world reachable by the fixed model (including worlds stuck under the original protocol).
pub proof fn theorem_liveness_reachable(d: Deps, n: int, w: World, k: nat, ws: spec_fn(nat) -> World, rps: spec_fn(nat) -> RP)
    requires wf(d, n), reachable(d, n, w, k), ws(0) == w, run_ok(d, n, ws, rps), fair_lossy(rps),
    ensures exists|K: nat| #![trigger ws(K)] ws(K).peers[0].doc == ws(K).peers[1].doc,
{
    theorem_sinv_reachable(d, n, w, k);
    theorem_liveness(d, n, ws, rps);
}

// =====================================================================================
// Part 9: executable refinement of the patch.  EState mirrors the fields of sync::State that the model uses
// (types simplified: hashes are u64, sets are Vec).  on_timeout is the body of the proposed State::on_timeout.
// =====================================================================================
pub struct EHave { pub last_sync: Vec<u64>, pub bloom: Vec<u64> }
pub struct EState {
    pub shared_heads: Vec<u64>, pub last_sent_heads: Vec<u64>,
    pub their_heads: Option<Vec<u64>>, pub their_need: Option<Vec<u64>>, pub their_have: Option<Vec<EHave>>,
    pub sent_hashes: Vec<u64>, pub in_flight: bool, pub have_responded: bool, pub needs_reset: bool, pub caps: bool,
}
pub open spec fn vset(v: Seq<u64>) -> ISet<int> { ISet::new(|x: int| exists|i: int| 0 <= i < v.len() && v[i] as int == x) }
pub open spec fn abs_have(h: EHave) -> Have { Have { last_sync: vset(h.last_sync@), bloom: vset(h.bloom@) } }
pub open spec fn abs_opt(o: Option<Vec<u64>>) -> Option<ISet<int>> { match o { Some(v) => Some(vset(v@)), None => None } }
// abstraction: the doc and the change queue live in the Automerge document, not in State
pub open spec fn abs(s: EState, doc: ISet<int>, queue: ISet<int>) -> Peer {
    Peer {
        doc: doc, queue: queue, shared_heads: vset(s.shared_heads@), last_sent_heads: vset(s.last_sent_heads@),
        their_heads: abs_opt(s.their_heads), their_need: abs_opt(s.their_need),
        their_have: match s.their_have { Some(v) => Some(Seq::new(v@.len(), |i: int| abs_have(v@[i]))), None => None },
        sent_hashes: vset(s.sent_hashes@), in_flight: s.in_flight, have_responded: s.have_responded, needs_reset: s.needs_reset, caps: s.caps,
    }
}
impl EState {
    // proposed:  pub fn on_timeout(&mut self) { self.sent_hashes.clear(); self.in_flight = false; }
    pub fn on_timeout(&mut self)
        ensures
            forall|doc: ISet<int>, queue: ISet<int>| abs(*final(self), doc, queue) == tmo(abs(*old(self), doc, queue)),
            final(self).shared_heads == old(self).shared_heads, final(self).last_sent_heads == old(self).last_sent_heads,
            final(self).their_heads == old(self).their_heads, final(self).their_need == old(self).their_need,
            final(self).their_have == old(self).their_have, final(self).have_responded == old(self).have_responded,
            final(self).needs_reset == old(self).needs_reset, final(self).caps == old(self).caps,
            final(self).sent_hashes@.len() == 0, final(self).in_flight == false,
    {
        self.sent_hashes.clear();
        self.in_flight = false;
        proof {
            assert forall|doc: ISet<int>, queue: ISet<int>| abs(*final(self), doc, queue) == tmo(abs(*old(self), doc, queue)) by {
                assert(vset(self.sent_hashes@) =~= ISet::<int>::empty());
            }
        }
    }
}

fn main() {}

// =====================================================================================
// Part 10 (vlm45_amproof): general runs.  A block is either a lock-step round (as above) or ONE arbitrary
// model step other than Edit: deliver any pending (stale, reordered) message, deliver-and-keep (duplicate),
// Drop, Gen, Timeout, SetReset, by either peer, in any order.  Fairness: infinitely often, 4 consecutive
// blocks are loss-free rounds.  Conclusion: docs become identical and stay identical.
// =====================================================================================
pub open spec fn blk_ok(d: Deps, n: int, w: World, isr: bool, rp: RP, st: Step, w2: World) -> bool {
    if isr { rvalid(d, n, w, rp) && w2 == rw6(d, n, w, rp) } else { next(d, n, w, st, w2) && passive_step(st) }
}
pub open spec fn grun_ok(d: Deps, n: int, ws: spec_fn(nat) -> World, isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, sts: spec_fn(nat) -> Step) -> bool {
    forall|k: nat| #![trigger rps(k)] blk_ok(d, n, ws(k), isr(k), rps(k), sts(k), ws((k + 1) as nat))
}
pub open spec fn gr(isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, k: nat) -> bool { isr(k) && good(rps(k)) }
pub open spec fn gwin4(isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, m: nat) -> bool {
    exists|k: nat| #![trigger rps(k)] k >= m && gr(isr, rps, k) && gr(isr, rps, (k + 1) as nat)
        && gr(isr, rps, (k + 2) as nat) && gr(isr, rps, (k + 3) as nat)
}
pub open spec fn gfair(isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP) -> bool { forall|m: nat| #[trigger] gwin4(isr, rps, m) }

proof fn lemma_grun_at(d: Deps, n: int, ws: spec_fn(nat) -> World, isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, sts: spec_fn(nat) -> Step, k: nat)
    requires grun_ok(d, n, ws, isr, rps, sts),
    ensures blk_ok(d, n, ws(k), isr(k), rps(k), sts(k), ws((k + 1) as nat)),
{ let _ = rps(k); }
proof fn lemma_blk(d: Deps, n: int, w: World, isr: bool, rp: RP, st: Step, w2: World)
    requires wf(d, n), sinv(d, n, w), blk_ok(d, n, w, isr, rp, st, w2),
    ensures sinv(d, n, w2), rel(w, w2),
{
    if isr { lemma_round(d, n, w, rp); } else { lemma_one(d, n, w, st, w2); }
}
proof fn lemma_grun_sinv(d: Deps, n: int, ws: spec_fn(nat) -> World, isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, sts: spec_fn(nat) -> Step, k: nat)
    requires wf(d, n), sinv(d, n, ws(0)), grun_ok(d, n, ws, isr, rps, sts), ensures sinv(d, n, ws(k)), decreases k,
{
    if k > 0 {
        let j = (k - 1) as nat;
        lemma_grun_sinv(d, n, ws, isr, rps, sts, j);
        lemma_grun_at(d, n, ws, isr, rps, sts, j);
        lemma_blk(d, n, ws(j), isr(j), rps(j), sts(j), ws(k));
    }
}
proof fn lemma_grun_rel(d: Deps, n: int, ws: spec_fn(nat) -> World, isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, sts: spec_fn(nat) -> Step, i: nat, j: nat)
    requires wf(d, n), sinv(d, n, ws(0)), grun_ok(d, n, ws, isr, rps, sts), i <= j,
    ensures rel(ws(i), ws(j)), ws(i).peers.len() == 2, ws(j).peers.len() == 2, decreases j - i,
{
    lemma_grun_sinv(d, n, ws, isr, rps, sts, i);
    lemma_grun_sinv(d, n, ws, isr, rps, sts, j);
    assert(inv(d, n, ws(i)) && inv(d, n, ws(j)));
    if i < j {
        let p = (j - 1) as nat;
        lemma_grun_rel(d, n, ws, isr, rps, sts, i, p);
        lemma_grun_sinv(d, n, ws, isr, rps, sts, p);
        lemma_grun_at(d, n, ws, isr, rps, sts, p);
        lemma_blk(d, n, ws(p), isr(p), rps(p), sts(p), ws(j));
        lemma_rel_trans(ws(i), ws(p), ws(j));
    } else { lemma_rel_refl(ws(i)); }
}
proof fn lemma_glive_from(d: Deps, n: int, ws: spec_fn(nat) -> World, isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, sts: spec_fn(nat) -> Step, v: nat, m: nat)
    requires wf(d, n), n >= 0, sinv(d, n, ws(0)), grun_ok(d, n, ws, isr, rps, sts), gfair(isr, rps), phi(n, ws(m)) <= v,
    ensures exists|K: nat| #![trigger ws(K)] K >= m && ws(K).peers[0].doc == ws(K).peers[1].doc,
    decreases v,
{
    assert(gwin4(isr, rps, m));
    let k = choose|k: nat| #![trigger rps(k)] k >= m && gr(isr, rps, k) && gr(isr, rps, (k + 1) as nat) && gr(isr, rps, (k + 2) as nat) && gr(isr, rps, (k + 3) as nat);
    lemma_grun_rel(d, n, ws, isr, rps, sts, m, k);
    lemma_phi_le(n, ws(m), ws(k));
    lemma_grun_sinv(d, n, ws, isr, rps, sts, k);
    if phi(n, ws(k)) == 0 {
        lemma_phi_zero(d, n, ws(k));
    } else {
        let w0 = ws(k);
        let a = if cnt(gset(w0, 0), n as nat) > 0 { 0int } else { 1int };
        if cnt(gset(w0, 0), n as nat) == 0 && cnt(gset(w0, 1), n as nat) == 0 {
            cnt_mono(rset(w0, 0), gset(w0, 0), n as nat); cnt_mono(rset(w0, 1), gset(w0, 1), n as nat);
            assert(false);
        }
        cnt_pos(gset(w0, a), n as nat);
        assert(!w0.peers[1 - a].doc.subset_of(w0.peers[a].doc));
        lemma_grun_at(d, n, ws, isr, rps, sts, k);
        lemma_grun_at(d, n, ws, isr, rps, sts, (k + 1) as nat);
        lemma_grun_at(d, n, ws, isr, rps, sts, (k + 2) as nat);
        lemma_grun_at(d, n, ws, isr, rps, sts, (k + 3) as nat);
        lemma_window(d, n, w0, rps(k), rps((k + 1) as nat), rps((k + 2) as nat), rps((k + 3) as nat), a);
        lemma_glive_from(d, n, ws, isr, rps, sts, (v - 1) as nat, (k + 4) as nat);
    }
}
// THEOREM (general liveness)
pub proof fn theorem_gliveness(d: Deps, n: int, w: World, k0: nat, ws: spec_fn(nat) -> World, isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, sts: spec_fn(nat) -> Step)
    requires wf(d, n), reachable(d, n, w, k0), ws(0) == w, grun_ok(d, n, ws, isr, rps, sts), gfair(isr, rps),
    ensures exists|K: nat| #![trigger ws(K)] ws(K).peers[0].doc == ws(K).peers[1].doc,
{
    theorem_sinv_reachable(d, n, w, k0);
    lemma_glive_from(d, n, ws, isr, rps, sts, phi(n, ws(0)), 0);
}
// THEOREM (general stability): once equal, docs stay equal under any blocks.
pub proof fn theorem_gstays_equal(d: Deps, n: int, ws: spec_fn(nat) -> World, isr: spec_fn(nat) -> bool, rps: spec_fn(nat) -> RP, sts: spec_fn(nat) -> Step, i: nat, j: nat)
    requires wf(d, n), sinv(d, n, ws(0)), grun_ok(d, n, ws, isr, rps, sts), i <= j, ws(i).peers[0].doc == ws(i).peers[1].doc,
    ensures ws(j).peers[0].doc == ws(j).peers[1].doc,
{
    lemma_grun_rel(d, n, ws, isr, rps, sts, i, j);
    let w = ws(i); let w2 = ws(j);
    assert(rel_i(w, w2, 0) && rel_i(w, w2, 1));
    assert(w2.peers[0].doc =~= w2.peers[1].doc) by {
        assert forall|x: int| w2.peers[0].doc.contains(x) implies w2.peers[1].doc.contains(x) by {
            assert(w.peers[0].doc.union(w.peers[1].doc).contains(x)); assert(w.peers[1].doc.contains(x));
        }
        assert forall|x: int| w2.peers[1].doc.contains(x) implies w2.peers[0].doc.contains(x) by {
            assert(w.peers[1].doc.union(w.peers[0].doc).contains(x)); assert(w.peers[0].doc.contains(x));
        }
    }
}
// Not vacuous: a stale delivery between rounds is a legal block (any guard-satisfying non-Edit step is).
pub proof fn lemma_block_exists(d: Deps, n: int, w: World, st: Step)
    requires guard(d, n, w, st), passive_step(st),
    ensures blk_ok(d, n, w, false, arbitrary(), st, apply(d, n, w, st)),
{}


// =====================================================================================
// Part 11 (vlm46_amfollow, corrected model): COUNTEREXAMPLE to liveness under per-message fairness.
// n = 2 changes (0 and 1), no dependencies.  A run (no Edit after step 7, no Drop) in which every message ever
// sent is delivered over and over, both peers time out and generate over and over, and the documents differ
// forever (A = {0,1}, B = {1}).
// Why the bloom fix does not kill it: B's doc is NOT empty, so B's bloom may have a false positive on 0.
// B's shared_heads is reset to {} by a stale message from A (heads {}), so B's filter is built from {1}, not from nothing.
// The stale message m0 is A's very first message (sent when A was empty); it is re-delivered to B every cycle after ma.
// =====================================================================================
pub open spec fn dd() -> Deps { |c: int| ISet::<int>::empty() }
pub open spec fn es() -> ISet<int> { ISet::<int>::empty() }
pub open spec fn zs() -> ISet<int> { ISet::<int>::empty().insert(0) }
pub open spec fn os() -> ISet<int> { ISet::<int>::empty().insert(1) }
pub open spec fn bs() -> ISet<int> { ISet::<int>::empty().insert(0).insert(1) }
pub open spec fn hE() -> Have { Have { last_sync: es(), bloom: es() } }      // from A while A is empty: empty filter (forced by the fix)
pub open spec fn hB() -> Have { Have { last_sync: es(), bloom: bs() } }      // from B: filter built from {1}, false positive on 0
pub open spec fn hA() -> Have { Have { last_sync: os(), bloom: zs() } }      // from A: filter built from {0}
pub open spec fn m0() -> Msg { Msg { heads: es(), need: es(), have: seq![hE()], changes: es(), sync_reset: false } }
pub open spec fn mb() -> Msg { Msg { heads: os(), need: es(), have: seq![hB()], changes: os(), sync_reset: false } }
pub open spec fn ma() -> Msg { Msg { heads: bs(), need: es(), have: seq![hA()], changes: es(), sync_reset: false } }
pub open spec fn pp(doc: ISet<int>, sh: ISet<int>, lsh: ISet<int>, th: Option<ISet<int>>, thv: Option<Seq<Have>>, tn: Option<ISet<int>>,
                    sent: ISet<int>, inf: bool, hr: bool, caps: bool) -> Peer {
    Peer { doc: doc, queue: es(), shared_heads: sh, last_sent_heads: lsh, their_heads: th, their_have: thv, their_need: tn,
           sent_hashes: sent, in_flight: inf, have_responded: hr, needs_reset: false, caps: caps }
}
pub open spec fn emp_have() -> Option<Seq<Have>> { Some(Seq::<Have>::empty()) }
pub open spec fn ne() -> ISet<Msg> { ISet::<Msg>::empty() }
pub open spec fn n1(a: Msg) -> ISet<Msg> { ISet::<Msg>::empty().insert(a) }
pub open spec fn n2() -> ISet<Msg> { ISet::<Msg>::empty().insert(m0()).insert(ma()) }
pub open spec fn wld(a: Peer, b: Peer, n0: ISet<Msg>, n1: ISet<Msg>) -> World { World { peers: seq![a, b], net: seq![n0, n1] } }
// peers
pub open spec fn aA1() -> Peer { pp(es(), es(), es(), None, emp_have(), None, es(), true, true, false) }      // after A's first generate
pub open spec fn aA5() -> Peer { pp(os(), os(), es(), Some(os()), Some(seq![hB()]), Some(es()), es(), false, true, true) }
pub open spec fn aA6() -> Peer { pp(bs(), os(), es(), Some(os()), Some(seq![hB()]), Some(es()), es(), false, true, true) }
pub open spec fn aC() -> Peer { pp(bs(), os(), bs(), Some(os()), Some(seq![hB()]), Some(es()), es(), true, true, true) }    // just generated
pub open spec fn aD() -> Peer { pp(bs(), os(), bs(), Some(os()), Some(seq![hB()]), Some(es()), es(), false, true, true) }   // just received mb
pub open spec fn bB2() -> Peer { Peer { doc: os(), ..init_peer() } }
pub open spec fn bB3() -> Peer { pp(os(), es(), es(), Some(es()), Some(seq![hE()]), Some(es()), es(), false, false, true) }
pub open spec fn bC() -> Peer { pp(os(), es(), os(), Some(es()), Some(seq![hE()]), Some(es()), os(), true, true, true) }       // just generated
pub open spec fn bM1() -> Peer { pp(os(), os(), os(), Some(bs()), Some(seq![hA()]), Some(es()), es(), false, true, true) }    // just received ma
pub open spec fn bM2() -> Peer { pp(os(), es(), es(), Some(es()), Some(seq![hE()]), Some(es()), es(), false, true, true) }    // then received m0
// worlds: prefix w0..w7, cycle worlds
pub open spec fn w0() -> World { wld(init_peer(), init_peer(), ne(), ne()) }
pub open spec fn w1() -> World { wld(aA1(), init_peer(), n1(m0()), ne()) }
pub open spec fn w2() -> World { wld(aA1(), bB2(), n1(m0()), ne()) }
pub open spec fn w3() -> World { wld(aA1(), bB3(), n1(m0()), ne()) }
pub open spec fn w4() -> World { wld(aA1(), bC(), n1(m0()), n1(mb())) }
pub open spec fn w5() -> World { wld(aA5(), bC(), n1(m0()), n1(mb())) }
pub open spec fn w6() -> World { wld(aA6(), bC(), n1(m0()), n1(mb())) }
pub open spec fn c0() -> World { wld(aC(), bC(), n2(), n1(mb())) }
pub open spec fn c1() -> World { wld(aC(), bM1(), n2(), n1(mb())) }
pub open spec fn c2() -> World { wld(aC(), bM2(), n2(), n1(mb())) }
pub open spec fn c5() -> World { wld(aD(), bC(), n2(), n1(mb())) }
// steps
pub open spec fn cyc_step(t: int) -> Step {
    if t == 0 { Step::Recv { who: 1, m: ma(), s2: os(), keep: true } }
    else if t == 1 { Step::Recv { who: 1, m: m0(), s2: os(), keep: true } }
    else if t == 2 { Step::Timeout { who: 1 } }
    else if t == 3 { Step::Gen { who: 1, bloom: bs(), fake: false } }
    else if t == 4 { Step::Recv { who: 0, m: mb(), s2: bs(), keep: true } }
    else if t == 5 { Step::Timeout { who: 0 } }
    else { Step::Gen { who: 0, bloom: zs(), fake: false } }
}
pub open spec fn cyc_world(t: int) -> World {
    if t == 0 || t == 4 { c0() } else if t == 1 { c1() } else if t == 2 || t == 3 { c2() } else { c5() }
}
pub open spec fn stp(i: nat) -> Step {
    if i == 0 { Step::Gen { who: 0, bloom: es(), fake: true } }
    else if i == 1 { Step::Edit { who: 1, c: 1 } }
    else if i == 2 { Step::Recv { who: 1, m: m0(), s2: os(), keep: true } }
    else if i == 3 { Step::Gen { who: 1, bloom: bs(), fake: false } }
    else if i == 4 { Step::Recv { who: 0, m: mb(), s2: os(), keep: true } }
    else if i == 5 { Step::Edit { who: 0, c: 0 } }
    else if i == 6 { Step::Gen { who: 0, bloom: zs(), fake: false } }
    else { cyc_step(((i - 7) % 7) as int) }
}
pub open spec fn wd(i: nat) -> World {
    if i == 0 { w0() } else if i == 1 { w1() } else if i == 2 { w2() } else if i == 3 { w3() } else if i == 4 { w4() }
    else if i == 5 { w5() } else if i == 6 { w6() } else { cyc_world(((i - 7) % 7) as int) }
}

proof fn lem_reach(h: ISet<int>, k: nat)
    ensures reach(dd(), h, k) == h, decreases k,
{
    if k > 0 {
        lem_reach(h, (k - 1) as nat);
        let r = reach(dd(), h, (k - 1) as nat);
        assert(reach(dd(), h, k) =~= h) by {
            assert forall|x: int| reach(dd(), h, k).contains(x) == h.contains(x) by {
                if reach(dd(), h, k).contains(x) && !h.contains(x) { assert(r.contains(x) || exists|y: int| r.contains(y) && #[trigger] dd()(y).contains(x)); }
            }
        }
    }
}
proof fn lem_walk(s: ISet<int>, q: ISet<int>, st: ISet<int>, k: nat)
    ensures walk(dd(), s, q, st, k) == st.difference(s), decreases k,
{
    if k > 0 {
        lem_walk(s, q, st, (k - 1) as nat);
        assert(walk(dd(), s, q, st, k) =~= st.difference(s));
    }
}
proof fn lem_cnt0(k: nat)
    ensures cnt(es(), k) == 0, decreases k,
{ if k > 0 { lem_cnt0((k - 1) as nat); } }
proof fn lem_basic()
    ensures
        forall|s: ISet<int>| #[trigger] heads(dd(), s) == s,
        forall|h: ISet<int>| #[trigger] closure(dd(), 2, h) == h,
        forall|s: ISet<int>, q: ISet<int>, st: ISet<int>| #[trigger] missing(dd(), 2, s, q, st) == st.difference(s).difference(q),
        closed(dd(), es()) && closed(dd(), os()) && closed(dd(), bs()) && closed(dd(), zs()),
        bounded(es(), 2) && bounded(os(), 2) && bounded(bs(), 2) && bounded(zs(), 2),
        wf(dd(), 2), cnt(es(), 2) == 0,
{
    assert forall|s: ISet<int>| #[trigger] heads(dd(), s) == s by {
        assert(heads(dd(), s) =~= s);
    }
    assert forall|h: ISet<int>| #[trigger] closure(dd(), 2, h) == h by { lem_reach(h, 2); }
    assert forall|s: ISet<int>, q: ISet<int>, st: ISet<int>| #[trigger] missing(dd(), 2, s, q, st) == st.difference(s).difference(q) by {
        lem_walk(s, q, st, 2);
        assert(missing(dd(), 2, s, q, st) =~= st.difference(s).difference(q));
    }
    lem_cnt0(2);
    assert(bounded(os(), 2)); assert(bounded(bs(), 2)); assert(bounded(zs(), 2));
}
proof fn lem_sets()
    ensures
        es().union(es()) == es(), es().difference(os()) == es(), es().difference(es()) == es(), os().difference(os()) == es(),
        os().difference(es()) == os(), bs().difference(bs()) == es(), bs().difference(os()) == zs(), os().union(es()) == os(),
        es().union(os()) == os(), os().union(os()) == os(), bs().union(os()) == bs(), os().intersect(os()) == os(),
        bs().intersect(os()) == os(), os().intersect(bs()) == os(), bs().intersect(bs()) == bs(), es().intersect(os()) == es(),
        es().intersect(es()) == es(), os().intersect(es()) == es(), bs().difference(es()) == bs(), es().intersect(bs()) == es(),
        os().difference(bs()) == es(), es().union(bs()) == bs(), bs().intersect(es()) == es(), zs().union(es()) == zs(),
        es().intersect(zs()) == es(), bs().difference(zs()) == os(), os().insert(0) == bs(), es().insert(1) == os(),
        bs().insert(0) == bs(), es().insert(0) == zs(), os().contains(1), !os().contains(0), bs().contains(0), bs().contains(1),
        zs().contains(0), !es().contains(0), !es().contains(1),
{
    assert(es().union(es()) =~= es()); assert(es().difference(os()) =~= es()); assert(es().difference(es()) =~= es());
    assert(os().difference(os()) =~= es()); assert(os().difference(es()) =~= os()); assert(bs().difference(bs()) =~= es());
    assert(bs().difference(os()) =~= zs()); assert(os().union(es()) =~= os()); assert(es().union(os()) =~= os());
    assert(os().union(os()) =~= os()); assert(bs().union(os()) =~= bs()); assert(os().intersect(os()) =~= os());
    assert(bs().intersect(os()) =~= os()); assert(os().intersect(bs()) =~= os()); assert(bs().intersect(bs()) =~= bs());
    assert(es().intersect(os()) =~= es()); assert(es().intersect(es()) =~= es()); assert(os().intersect(es()) =~= es());
    assert(bs().difference(es()) =~= bs()); assert(es().intersect(bs()) =~= es()); assert(os().difference(bs()) =~= es());
    assert(es().union(bs()) =~= bs()); assert(bs().intersect(es()) =~= es()); assert(zs().union(es()) =~= zs());
    assert(es().intersect(zs()) =~= es()); assert(bs().difference(zs()) =~= os());
    assert(os().insert(0) =~= bs()); assert(es().insert(1) =~= os()); assert(bs().insert(0) =~= bs()); assert(es().insert(0) =~= zs());
}
// hashes_to_send core with one Have: need2 plus everything outside last_sync and outside the bloom
proof fn lem_hts1(s: ISet<int>, ls: ISet<int>, bl: ISet<int>, need2: ISet<int>)
    ensures hts_core(dd(), 2, s, seq![Have { last_sync: ls, bloom: bl }], need2) =~= need2.union(s.difference(ls).difference(bl)),
{
    lem_basic();
    let h = seq![Have { last_sync: ls, bloom: bl }];
    assert(h.len() == 1 && h[0].last_sync == ls && h[0].bloom == bl);
    assert(all_last_sync(h) =~= ls) by {
        assert forall|x: int| all_last_sync(h).contains(x) == ls.contains(x) by {
            if ls.contains(x) { assert(0 <= 0 < h.len() && h[0].last_sync.contains(x)); }
        }
    }
    let hs = s.difference(closure(dd(), 2, all_last_sync(h)));
    assert(hs =~= s.difference(ls));
    let miss = ISet::new(|x: int| hs.contains(x) && forall|i: int| 0 <= i < h.len() ==> !(#[trigger] h[i].bloom.contains(x)));
    assert(miss =~= s.difference(ls).difference(bl)) by {
        assert forall|x: int| miss.contains(x) == s.difference(ls).difference(bl).contains(x) by {
            if s.difference(ls).difference(bl).contains(x) {
                assert(hs.contains(x));
                assert forall|i: int| 0 <= i < h.len() implies !(#[trigger] h[i].bloom.contains(x)) by { assert(i == 0); }
            }
        }
    }
    let sent = ISet::new(|x: int| hs.contains(x) && exists|m: int| miss.contains(m) && closure(dd(), 2, ISet::empty().insert(x)).contains(m));
    assert forall|x: int| sent.contains(x) == miss.contains(x) by {
        assert(closure(dd(), 2, ISet::empty().insert(x)) =~= ISet::empty().insert(x));
        if miss.contains(x) { assert(hs.contains(x) && closure(dd(), 2, ISet::empty().insert(x)).contains(x)); }
        if sent.contains(x) { let m = choose|m: int| miss.contains(m) && closure(dd(), 2, ISet::empty().insert(x)).contains(m); assert(m == x); }
    }
    assert(sent =~= miss);
    assert(hts_core(dd(), 2, s, h, need2) =~= need2.union(s.difference(ls).difference(bl)));
}

// ---- peer-level facts (one lemma per distinct generate / receive) ----
proof fn gen_first(p: Peer)
    requires p == init_peer(),
    ensures gen(dd(), 2, p, es(), true) == (aA1(), Some(m0())),
{
    lem_basic(); lem_sets();
    assert(missing(dd(), 2, p.doc, p.queue, opt_set(p.their_heads)) == es());
    assert(!must_reset(p));
    assert(!their_ok(p));
    assert(!bad(dd(), 2, p));
    assert(send_set(dd(), 2, p) =~= es());
    assert(chg(dd(), 2, p) =~= es());
    assert(seq![Have { last_sync: es(), bloom: es() }] =~= seq![hE()]);
    assert(gen(dd(), 2, p, es(), true).0 =~= aA1());
    assert(gen(dd(), 2, p, es(), true).1 == Some(m0()));
}
proof fn gen_b(p: Peer)
    requires p.doc == os(), p.queue == es(), p.shared_heads == es(), p.last_sent_heads == es(), p.their_heads == Some(es()),
        p.their_have == Some(seq![hE()]), p.their_need == Some(es()), p.sent_hashes == es(), p.needs_reset == false, p.caps == true,
    ensures gen(dd(), 2, p, bs(), false) == (pp(os(), es(), os(), Some(es()), Some(seq![hE()]), Some(es()), os(), true, true, true), Some(mb())),
{
    lem_basic(); lem_sets();
    assert(missing(dd(), 2, p.doc, p.queue, opt_set(p.their_heads)) == es());
    assert(!must_reset(p));
    assert(sdoc(p));
    assert(!bad(dd(), 2, p));
    assert(chg(dd(), 2, p) == os());
    assert(heads(dd(), p.doc) == os());
    assert(p.last_sent_heads != os()) by { assert(os().contains(1)); assert(!es().contains(1)); }
    assert(seq![Have { last_sync: es(), bloom: bs() }] =~= seq![hB()]);
    assert(es().union(os()) =~= os());
    assert(gen(dd(), 2, p, bs(), false).0 =~= pp(os(), es(), os(), Some(es()), Some(seq![hE()]), Some(es()), os(), true, true, true));
    assert(gen(dd(), 2, p, bs(), false).1 == Some(mb()));
}
proof fn gen_a(p: Peer)
    requires p.doc == bs(), p.queue == es(), p.shared_heads == os(), p.their_heads == Some(os()), p.their_have == Some(seq![hB()]),
        p.their_need == Some(es()), p.sent_hashes == es(), p.in_flight == false, p.have_responded == true, p.needs_reset == false,
        p.caps == true, p.last_sent_heads == es() || p.last_sent_heads == bs(),
    ensures gen(dd(), 2, p, zs(), false) == (aC(), Some(ma())),
{
    lem_basic(); lem_sets();
    assert(missing(dd(), 2, p.doc, p.queue, opt_set(p.their_heads)) == es());
    assert(!must_reset(p));
    assert(!sdoc(p)) by { assert(os().contains(1)); assert(!es().contains(1)); }
    lem_hts1(bs(), es(), bs(), es());
    let h = seq![hB()];
    assert(hts_core(dd(), 2, p.doc, h, es()) =~= es());
    assert(es().intersect(p.doc) =~= es());
    assert(full_set(dd(), 2, p) =~= es());
    assert(send_set(dd(), 2, p) =~= es());
    assert(!big(dd(), 2, p));
    assert(!bad(dd(), 2, p));
    assert(chg(dd(), 2, p) =~= es());
    assert(heads(dd(), p.doc) == bs());
    assert(p.their_heads != Some(bs())) by { assert(os().contains(1) && !os().contains(0)); assert(bs().contains(0)); }
    assert(p.last_sent_heads == es() || p.last_sent_heads == bs());
    assert(seq![Have { last_sync: os(), bloom: zs() }] =~= seq![hA()]);
    assert(p.sent_hashes.union(es()) =~= es());
    assert(gen(dd(), 2, p, zs(), false).0 =~= aC());
    assert(gen(dd(), 2, p, zs(), false).1 == Some(ma()));
}
proof fn recv_guard(p: Peer, m: Msg, s2: ISet<int>)
    requires p.queue == es(), closed(dd(), p.doc), s2 == p.doc.union(m.changes), m.changes == es() || m.changes == os(), bounded(p.doc, 2),
    ensures bounded(p.queue.union(m.changes), 2), drain_ok(dd(), p.doc, p.queue.union(m.changes), s2), (m.changes == es() ==> s2 == p.doc),
{
    lem_basic(); lem_sets();
    assert(p.queue.union(m.changes) =~= m.changes);
    assert(bounded(m.changes, 2));
    assert(closed(dd(), s2)) by { assert(closed(dd(), s2)); }
    assert forall|c: int| m.changes.contains(c) && !s2.contains(c) implies !(dd()(c).subset_of(s2)) by { assert(s2.contains(c)); }
    if m.changes == es() { assert(p.doc.union(es()) =~= p.doc); }
}
proof fn recv_ma(p: Peer)
    requires p == bC(), ensures recv(dd(), 2, p, ma(), os()) == bM1(),
{
    lem_basic(); lem_sets();
    assert(os().intersect(os()) =~= os());
    assert(bs().intersect(os()) =~= os());
    assert(os().difference(closure(dd(), 2, os())) =~= es());
    assert(es().union(os()) =~= os());
    assert(recv(dd(), 2, p, ma(), os()) =~= bM1());
}
proof fn recv_m0(p: Peer)
    requires p.doc == os(), p.queue == es(), p.needs_reset == false, p.shared_heads == es() || p.shared_heads == os(),
    ensures recv(dd(), 2, p, m0(), os()) == pp(os(), es(), es(), Some(es()), Some(seq![hE()]), Some(es()), es(), false, p.have_responded, true),
        recv(dd(), 2, p, m0(), os()).have_responded == p.have_responded,
{
    lem_basic(); lem_sets();
    assert(es().intersect(os()) =~= es());
    assert(p.queue.union(es()) =~= es());
    assert(es().difference(os()) =~= es());
    assert(recv(dd(), 2, p, m0(), os()) =~= pp(os(), es(), es(), Some(es()), Some(seq![hE()]), Some(es()), es(), false, p.have_responded, true));
}
proof fn recv_mb_a(p: Peer)
    requires p == aA1(), ensures recv(dd(), 2, p, mb(), os()) == aA5(),
{
    lem_basic(); lem_sets();
    assert(os().intersect(os()) =~= os());
    assert(os().difference(es()) =~= os());
    assert(es().intersect(os()) =~= es());
    assert(os().union(es()) =~= os());
    assert(es().union(os()) =~= os());
    assert(es().difference(closure(dd(), 2, os())) =~= es());
    assert(recv(dd(), 2, p, mb(), os()) =~= aA5());
}
proof fn recv_mb_c(p: Peer)
    requires p == aC(), ensures recv(dd(), 2, p, mb(), bs()) == aD(),
{
    lem_basic(); lem_sets();
    assert(os().intersect(bs()) =~= os());
    assert(bs().difference(bs()) =~= es());
    assert(os().intersect(bs()) =~= os());
    assert(bs().intersect(bs()) =~= bs());
    assert(es().union(os()) =~= os());
    assert(es().difference(closure(dd(), 2, os())) =~= es());
    assert(bs().difference(bs()).union(os().intersect(bs())) =~= os());
    assert(recv(dd(), 2, p, mb(), bs()) =~= aD());
}
proof fn tmo_same(p: Peer)
    requires p.sent_hashes == es(), p.in_flight == false, ensures tmo(p) == p,
{ assert(tmo(p) =~= p); }

// ---- one lemma per step of the run ----
proof fn s0() ensures guard(dd(), 2, w0(), stp(0)), apply(dd(), 2, w0(), stp(0)) == w1() {
    lem_basic(); lem_sets(); gen_first(init_peer());
    assert(init_peer().doc.difference(closure(dd(), 2, init_peer().shared_heads)) =~= es());
    assert(apply(dd(), 2, w0(), stp(0)).peers =~= w1().peers);
    assert(apply(dd(), 2, w0(), stp(0)).net =~= w1().net);
}
proof fn s1() ensures guard(dd(), 2, w1(), stp(1)), apply(dd(), 2, w1(), stp(1)) == w2() {
    lem_basic(); lem_sets();
    assert(apply(dd(), 2, w1(), stp(1)).peers =~= w2().peers);
    assert(apply(dd(), 2, w1(), stp(1)).net =~= w2().net);
}
proof fn s2() ensures guard(dd(), 2, w2(), stp(2)), apply(dd(), 2, w2(), stp(2)) == w3() {
    lem_basic(); lem_sets();
    let p = w2().peers[1];
    recv_m0(p); recv_guard(p, m0(), os());
    assert(w2().net[0].contains(m0()));
    assert(apply(dd(), 2, w2(), stp(2)).peers =~= w3().peers);
    assert(apply(dd(), 2, w2(), stp(2)).net =~= w3().net);
}
proof fn s3() ensures guard(dd(), 2, w3(), stp(3)), apply(dd(), 2, w3(), stp(3)) == w4() {
    lem_basic(); lem_sets();
    let p = w3().peers[1];
    gen_b(p);
    assert(p.doc.difference(closure(dd(), 2, p.shared_heads)) =~= os());
    assert(apply(dd(), 2, w3(), stp(3)).peers =~= w4().peers);
    assert(apply(dd(), 2, w3(), stp(3)).net =~= w4().net);
}
proof fn s4() ensures guard(dd(), 2, w4(), stp(4)), apply(dd(), 2, w4(), stp(4)) == w5() {
    lem_basic(); lem_sets();
    let p = w4().peers[0];
    recv_mb_a(p);
    assert(p.queue.union(mb().changes) =~= os());
    assert(drain_ok(dd(), p.doc, p.queue.union(mb().changes), os())) by {
        assert(p.queue.union(mb().changes) =~= os());
        assert forall|c: int| os().contains(c) && !os().contains(c) implies !(dd()(c).subset_of(os())) by {}
    }
    assert(bounded(p.queue.union(mb().changes), 2));
    assert(w4().net[1].contains(mb()));
    assert(apply(dd(), 2, w4(), stp(4)).peers =~= w5().peers);
    assert(apply(dd(), 2, w4(), stp(4)).net =~= w5().net);
}
proof fn s5() ensures guard(dd(), 2, w5(), stp(5)), apply(dd(), 2, w5(), stp(5)) == w6() {
    lem_basic(); lem_sets();
    assert(apply(dd(), 2, w5(), stp(5)).peers =~= w6().peers);
    assert(apply(dd(), 2, w5(), stp(5)).net =~= w6().net);
}
proof fn gen_a_step(w: World, w2: World)
    requires (w == w6() && w2 == c0()) || (w == c5() && w2 == c0()),
    ensures guard(dd(), 2, w, Step::Gen { who: 0, bloom: zs(), fake: false }),
        apply(dd(), 2, w, Step::Gen { who: 0, bloom: zs(), fake: false }) == w2,
{
    lem_basic(); lem_sets();
    let p = w.peers[0];
    gen_a(p);
    assert(p.doc.difference(closure(dd(), 2, p.shared_heads)) =~= zs());
    let st = Step::Gen { who: 0, bloom: zs(), fake: false };
    assert(apply(dd(), 2, w, st).peers =~= w2.peers);
    assert(apply(dd(), 2, w, st).net =~= w2.net) by { assert(w.net[0].insert(ma()) =~= n2()); }
}
proof fn s6() ensures guard(dd(), 2, w6(), stp(6)), apply(dd(), 2, w6(), stp(6)) == c0() { gen_a_step(w6(), c0()); }
proof fn c_recv_ma() ensures guard(dd(), 2, c0(), cyc_step(0)), apply(dd(), 2, c0(), cyc_step(0)) == c1() {
    lem_basic(); lem_sets();
    let p = c0().peers[1];
    recv_ma(p); recv_guard(p, ma(), os());
    assert(c0().net[0].contains(ma()));
    assert(apply(dd(), 2, c0(), cyc_step(0)).peers =~= c1().peers);
    assert(apply(dd(), 2, c0(), cyc_step(0)).net =~= c1().net);
}
proof fn c_recv_m0() ensures guard(dd(), 2, c1(), cyc_step(1)), apply(dd(), 2, c1(), cyc_step(1)) == c2() {
    lem_basic(); lem_sets();
    let p = c1().peers[1];
    recv_m0(p); recv_guard(p, m0(), os());
    assert(c1().net[0].contains(m0()));
    assert(apply(dd(), 2, c1(), cyc_step(1)).peers =~= c2().peers);
    assert(apply(dd(), 2, c1(), cyc_step(1)).net =~= c2().net);
}
proof fn c_tmo_b() ensures guard(dd(), 2, c2(), cyc_step(2)), apply(dd(), 2, c2(), cyc_step(2)) == c2() {
    tmo_same(bM2());
    assert(apply(dd(), 2, c2(), cyc_step(2)).peers =~= c2().peers);
}
proof fn c_gen_b() ensures guard(dd(), 2, c2(), cyc_step(3)), apply(dd(), 2, c2(), cyc_step(3)) == c0() {
    lem_basic(); lem_sets();
    let p = c2().peers[1];
    gen_b(p);
    assert(p.doc.difference(closure(dd(), 2, p.shared_heads)) =~= os());
    assert(apply(dd(), 2, c2(), cyc_step(3)).peers =~= c0().peers);
    assert(apply(dd(), 2, c2(), cyc_step(3)).net =~= c0().net) by { assert(c2().net[1].insert(mb()) =~= n1(mb())); }
}
proof fn c_recv_mb() ensures guard(dd(), 2, c0(), cyc_step(4)), apply(dd(), 2, c0(), cyc_step(4)) == c5() {
    lem_basic(); lem_sets();
    let p = c0().peers[0];
    recv_mb_c(p); recv_guard(p, mb(), bs());
    assert(c0().net[1].contains(mb()));
    assert(bs().union(os()) =~= bs());
    assert(apply(dd(), 2, c0(), cyc_step(4)).peers =~= c5().peers);
    assert(apply(dd(), 2, c0(), cyc_step(4)).net =~= c5().net);
}
proof fn c_tmo_a() ensures guard(dd(), 2, c5(), cyc_step(5)), apply(dd(), 2, c5(), cyc_step(5)) == c5() {
    tmo_same(aD());
    assert(apply(dd(), 2, c5(), cyc_step(5)).peers =~= c5().peers);
}
proof fn c_gen_a() ensures guard(dd(), 2, c5(), cyc_step(6)), apply(dd(), 2, c5(), cyc_step(6)) == c0() { gen_a_step(c5(), c0()); }

pub proof fn lem_step(i: nat)
    ensures guard(dd(), 2, wd(i), stp(i)), apply(dd(), 2, wd(i), stp(i)) == wd((i + 1) as nat),
{
    if i == 0 { s0(); } else if i == 1 { s1(); } else if i == 2 { s2(); } else if i == 3 { s3(); }
    else if i == 4 { s4(); } else if i == 5 { s5(); } else if i == 6 { s6(); }
    else {
        let t = ((i - 7) % 7) as int;
        if t == 0 { c_recv_ma(); } else if t == 1 { c_recv_m0(); } else if t == 2 { c_tmo_b(); }
        else if t == 3 { c_gen_b(); } else if t == 4 { c_recv_mb(); } else if t == 5 { c_tmo_a(); } else { c_gen_a(); }
        assert(((i + 1 - 7) % 7) as int == (t + 1) % 7);
    }
}

// ---- fairness notions (stated for a flat run: ws(k) --sts(k)--> ws(k+1)) ----
pub open spec fn delivers(st: Step, s: int, m: Msg) -> bool {
    match st { Step::Recv { who, m: mm, .. } => who == 1 - s && mm == m, _ => false }
}
pub open spec fn is_tmo(st: Step, w: int) -> bool { match st { Step::Timeout { who } => who == w, _ => false } }
pub open spec fn is_gen(st: Step, w: int) -> bool { match st { Step::Gen { who, .. } => who == w, _ => false } }
pub open spec fn is_edit(st: Step) -> bool { match st { Step::Edit { .. } => true, _ => false } }
// MSG_FAIR: every message that is in a sender's network at time k is delivered (received at least once) at some time j >= k.
pub open spec fn in_net(w: World, s: int, m: Msg) -> bool { w.net[s].contains(m) }
pub open spec fn msg_fair(ws: spec_fn(nat) -> World, sts: spec_fn(nat) -> Step) -> bool {
    forall|k: nat, s: int, m: Msg| (s == 0 || s == 1) && #[trigger] in_net(ws(k), s, m) ==> exists|j: nat| j >= k && #[trigger] delivers(sts(j), s, m)
}
// ACT_FAIR: each peer times out and generates at some time j >= k, for every k.
pub open spec fn tmo_after(sts: spec_fn(nat) -> Step, w: int, k: nat) -> bool { exists|j: nat| j >= k && #[trigger] is_tmo(sts(j), w) }
pub open spec fn gen_after(sts: spec_fn(nat) -> Step, w: int, k: nat) -> bool { exists|j: nat| j >= k && #[trigger] is_gen(sts(j), w) }
pub open spec fn act_fair(sts: spec_fn(nat) -> Step) -> bool {
    forall|k: nat, w: int| (w == 0 || w == 1) ==> (#[trigger] tmo_after(sts, w, k) && gen_after(sts, w, k))
}
pub open spec fn flat_run_ok(d: Deps, n: int, ws: spec_fn(nat) -> World, sts: spec_fn(nat) -> Step) -> bool {
    forall|k: nat| #[trigger] next(d, n, ws(k), sts(k), ws((k + 1) as nat))
}

proof fn lem_exists_j(k: nat, r: nat) -> (j: nat)
    requires r < 7, ensures j >= k && j % 7 == r,
{
    let j = (k + ((r + 7 - (k % 7)) % 7)) as nat;
    assert(j >= k && j % 7 == r) by (nonlinear_arith) requires r < 7, j == k + ((r + 7 - (k % 7)) % 7) {}
    j
}
proof fn lem_reach_wd(i: nat)
    requires i <= 7, ensures reachable(dd(), 2, wd(i), i), decreases i,
{
    if i == 0 {
        assert(wd(0).peers =~= seq![init_peer(), init_peer()]); assert(wd(0).net =~= seq![ISet::<Msg>::empty(), ISet::<Msg>::empty()]);
    } else {
        lem_reach_wd((i - 1) as nat); lem_step((i - 1) as nat);
        assert(next(dd(), 2, wd((i - 1) as nat), stp((i - 1) as nat), wd(i)));
    }
}
// in every cycle world: A = {0,1}, B = {1}, A's network is {m0, ma}, B's is {mb}
proof fn lem_shape(i: nat)
    requires i >= 7,
    ensures wd(i).peers[0].doc == bs(), wd(i).peers[1].doc == os(), wd(i).net[0] == n2(), wd(i).net[1] == n1(mb()),
{}
// THE COUNTEREXAMPLE
pub proof fn theorem_no_liveness_under_message_fairness()
    ensures exists|ws: spec_fn(nat) -> World, sts: spec_fn(nat) -> Step|
        wf(dd(), 2) && reachable(dd(), 2, ws(0), 7) && flat_run_ok(dd(), 2, ws, sts)
        && (forall|k: nat| !is_edit(#[trigger] sts(k))) && msg_fair(ws, sts) && act_fair(sts)
        && (forall|k: nat| #[trigger] ws(k).peers[0].doc != ws(k).peers[1].doc),
{
    lem_basic(); lem_sets();
    let ws = |k: nat| wd((k + 7) as nat);
    let sts = |k: nat| stp((k + 7) as nat);
    lem_reach_wd(7);
    assert forall|k: nat| #[trigger] next(dd(), 2, ws(k), sts(k), ws((k + 1) as nat)) by { lem_step((k + 7) as nat); }
    assert forall|k: nat| !is_edit(#[trigger] sts(k)) by { }
    assert forall|k: nat| #[trigger] ws(k).peers[0].doc != ws(k).peers[1].doc by {
        lem_shape((k + 7) as nat); assert(bs().contains(0) && !os().contains(0));
    }
    assert forall|k: nat, s: int, m: Msg| (s == 0 || s == 1) && #[trigger] in_net(ws(k), s, m) implies exists|j: nat| j >= k && #[trigger] delivers(sts(j), s, m) by {
        lem_shape((k + 7) as nat);
        if s == 1 {
            assert(m == mb());
            let j = lem_exists_j(k, 4);
            assert(sts(j) == cyc_step(4)); assert(delivers(sts(j), s, m));
        } else {
            assert(m == m0() || m == ma());
            if m == ma() {
                let j = lem_exists_j(k, 0);
                assert(sts(j) == cyc_step(0)); assert(delivers(sts(j), s, m));
            } else {
                let j = lem_exists_j(k, 1);
                assert(sts(j) == cyc_step(1)); assert(delivers(sts(j), s, m));
            }
        }
    }
    assert forall|k: nat, w: int| (w == 0 || w == 1) implies (#[trigger] tmo_after(sts, w, k) && gen_after(sts, w, k)) by {
        let rt: nat = if w == 0 { 5 } else { 2 };
        let rg: nat = if w == 0 { 6 } else { 3 };
        let j1 = lem_exists_j(k, rt);
        let j2 = lem_exists_j(k, rg);
        assert(sts(j1) == cyc_step(rt as int)); assert(sts(j2) == cyc_step(rg as int));
        assert(is_tmo(sts(j1), w)); assert(is_gen(sts(j2), w));
        assert(tmo_after(sts, w, k)); assert(gen_after(sts, w, k));
    }
    assert(msg_fair(ws, sts)); assert(act_fair(sts));
}
}
