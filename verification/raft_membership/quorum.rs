// (authored by agents)
// Verus proof of the quorum logic openraft uses to decide membership changes.
// Source: crate quorum-set 0.6.0 (openraft main 7628ad40 depends on it):
//   src/quorum/quorum_set_impl.rs          BTreeSet::is_quorum, Vec<BTreeSet>::is_quorum
//   src/quorum/quorum_intersection_impl.rs BTreeSet/Vec intersects_with
// BTreeSet<u64> is represented by Vec<u64> without duplicates; `contains` stands in for
// BTreeSet membership / `any(|c| c == id)`.
use vstd::prelude::*;
use vstd::set_lib::*;

verus! {

broadcast use vstd::seq_lib::group_seq_properties, vstd::set_lib::group_set_lib_default;

pub open spec fn st(v: Seq<u64>) -> Set<u64> { v.to_set() }

// Spec: q is a majority of config c.
pub open spec fn maj(c: Set<u64>, q: Set<u64>) -> bool { 2 * c.intersect(q).len() > c.len() }

// Spec: q is a quorum of a joint config: nonempty, majority of every part.
pub open spec fn joint_quorum(cs: Seq<Set<u64>>, q: Set<u64>) -> bool {
    cs.len() > 0 && forall|i: int| 0 <= i < cs.len() ==> maj(#[trigger] cs[i], q)
}

// Spec: every quorum of a meets every quorum of b.
pub open spec fn always_intersect(a: Seq<Set<u64>>, b: Seq<Set<u64>>) -> bool {
    forall|qa: Set<u64>, qb: Set<u64>| joint_quorum(a, qa) && joint_quorum(b, qb)
        ==> exists|x: u64| qa.contains(x) && qb.contains(x)
}

pub open spec fn sets(v: Seq<Vec<u64>>) -> Seq<Set<u64>> { v.map_values(|c: Vec<u64>| st(c@)) }

fn contains(v: &Vec<u64>, x: u64) -> (r: bool)
    ensures r == st(v@).contains(x)
{
    let mut i = 0;
    while i < v.len()
        invariant 0 <= i <= v.len(), forall|j: int| 0 <= j < i ==> v@[j] != x,
        decreases v.len() - i
    {
        if v[i] == x { assert(v@.contains(x)); return true; }
        i += 1;
    }
    proof { if v@.contains(x) { let j = choose|j: int| 0 <= j < v@.len() && v@[j] == x; } }
    false
}

proof fn lemma_prefix_push(v: Seq<u64>, i: int)
    requires 0 <= i < v.len(), v.no_duplicates()
    ensures st(v.subrange(0, i + 1)) == st(v.subrange(0, i)).insert(v[i]),
            !st(v.subrange(0, i)).contains(v[i])

{
    assert(v.subrange(0, i + 1) == v.subrange(0, i).push(v[i]));
    v.subrange(0, i).lemma_push_to_set_commute(v[i]);
    if st(v.subrange(0, i)).contains(v[i]) {
        let j = choose|j: int| 0 <= j < i && v.subrange(0, i)[j] == v[i];
        assert(v[j] == v[i]);
    }
}

// a.difference(b).count() if keep_in == false; a.intersection(b).count() if keep_in == true
fn count_filter(a: &Vec<u64>, b: &Vec<u64>, keep_in: bool) -> (r: usize)
    requires a@.no_duplicates()
    ensures keep_in ==> r == st(a@).intersect(st(b@)).len(),
            !keep_in ==> r == st(a@).difference(st(b@)).len(),
            r <= a@.len()
{
    let mut count: usize = 0;
    let mut i = 0;
    assert(st(a@.subrange(0, 0)) =~= Set::empty());
    assert(st(a@.subrange(0, 0)).intersect(st(b@)) =~= Set::<u64>::empty());
    assert(st(a@.subrange(0, 0)).difference(st(b@)) =~= Set::<u64>::empty());
    while i < a.len()
        invariant 0 <= i <= a.len(), a@.no_duplicates(), count <= i,
            keep_in ==> count == st(a@.subrange(0, i as int)).intersect(st(b@)).len(),
            !keep_in ==> count == st(a@.subrange(0, i as int)).difference(st(b@)).len(),
        decreases a.len() - i
    {
        let x = a[i];
        let inb = contains(b, x);
        proof {
            lemma_prefix_push(a@, i as int);
            let p = st(a@.subrange(0, i as int));
            let bs = st(b@);
            if inb {
                assert(p.insert(x).intersect(bs) =~= p.intersect(bs).insert(x));
                assert(p.insert(x).difference(bs) =~= p.difference(bs));
            } else {
                assert(p.insert(x).intersect(bs) =~= p.intersect(bs));
                assert(p.insert(x).difference(bs) =~= p.difference(bs).insert(x));
            }
        }
        if inb == keep_in { count += 1; }
        i += 1;
    }
    assert(a@.subrange(0, a@.len() as int) == a@);
    count
}

// quorum_set_impl.rs: impl QuorumSet for BTreeSet<ID>, is_quorum (verbatim loop body)
fn btree_is_quorum(config: &Vec<u64>, ids: &Vec<u64>) -> (r: bool)
    requires config@.no_duplicates(), config@.len() < usize::MAX / 4
    ensures r == maj(st(config@), st(ids@))
{
    let mut count: usize = 0;
    let limit = config.len();
    let mut i = 0;
    assert(st(config@.subrange(0, 0)) =~= Set::empty());
    assert(st(config@.subrange(0, 0)).intersect(st(ids@)) =~= Set::<u64>::empty());
    proof { config@.unique_seq_to_set(); }
    while i < config.len()
        invariant 0 <= i <= config.len(), config@.no_duplicates(), limit == config@.len(),
            limit == st(config@).len(), limit < usize::MAX / 4,
            count == 2 * st(config@.subrange(0, i as int)).intersect(st(ids@)).len(),
            count <= limit,
        decreases config.len() - i
    {
        let id = config[i];
        proof {
            lemma_prefix_push(config@, i as int);
            let p = st(config@.subrange(0, i as int));
            if st(ids@).contains(id) {
                assert(p.insert(id).intersect(st(ids@)) =~= p.intersect(st(ids@)).insert(id));
            } else {
                assert(p.insert(id).intersect(st(ids@)) =~= p.intersect(st(ids@)));
            }
            lemma_len_subset(st(config@.subrange(0, i as int + 1)).intersect(st(ids@)), p.insert(id));
            lemma_len_subset(p.insert(id), st(config@));
        }
        if contains(ids, id) {
            count += 2;
            if count > limit {
                proof {
                    lemma_len_subset(st(config@.subrange(0, i as int + 1)).intersect(st(ids@)),
                                     st(config@).intersect(st(ids@)));
                }
                return true;
            }
        }
        i += 1;
    }
    assert(config@.subrange(0, config@.len() as int) == config@);
    false
}

// quorum_set_impl.rs: impl QuorumSet for Vec<BTreeSet<ID>>, is_quorum
fn vec_is_quorum(configs: &Vec<Vec<u64>>, ids: &Vec<u64>) -> (r: bool)
    requires forall|i: int| 0 <= i < configs@.len() ==> (#[trigger] configs@[i])@.no_duplicates()
                 && configs@[i]@.len() < usize::MAX / 4
    ensures r == joint_quorum(sets(configs@), st(ids@))
{
    if configs.len() == 0 { return false; }
    let mut i = 0;
    while i < configs.len()
        invariant 0 <= i <= configs.len(), configs@.len() > 0,
            forall|k: int| 0 <= k < configs@.len() ==> (#[trigger] configs@[k])@.no_duplicates()
                 && configs@[k]@.len() < usize::MAX / 4,
            forall|j: int| 0 <= j < i ==> maj(#[trigger] sets(configs@)[j], st(ids@)),
        decreases configs.len() - i
    {
        if !btree_is_quorum(&configs[i], ids) { assert(!maj(sets(configs@)[i as int], st(ids@))); return false; }
        i += 1;
    }
    true
}

// Core arithmetic lemma behind BTreeSet::intersects_with returning Some(true).
proof fn lemma_btree_intersect(a: Set<u64>, b: Set<u64>, qa: Set<u64>, qb: Set<u64>)
    requires maj(a, qa), maj(b, qb),
        ({ let ma = a.len() / 2 + 1; let mb = b.len() / 2 + 1;
           let os = a.difference(b).len(); let oo = b.difference(a).len();
           let ns = if ma >= os { ma - os } else { 0 };
           let no = if mb >= oo { mb - oo } else { 0 };
           ns + no > a.intersect(b).len() })
    ensures exists|x: u64| qa.contains(x) && qb.contains(x)
{
    let s = a.intersect(b);
    let xa = a.intersect(qa); let xb = b.intersect(qb);
    let sa = xa.intersect(b); let sb = xb.intersect(a);
    // xa ⊆ (a - b) ∪ sa
    assert(xa =~= xa.difference(b).union(sa));
    lemma_len_union(xa.difference(b), sa);
    lemma_len_subset(xa.difference(b), a.difference(b));
    assert(xb =~= xb.difference(a).union(sb));
    lemma_len_union(xb.difference(a), sb);
    lemma_len_subset(xb.difference(a), b.difference(a));
    // sa, sb ⊆ s
    lemma_len_union(sa, sb);
    lemma_len_subset(sa.union(sb), s);
    lemma_len_intersect(sa, sb);
    if !(exists|x: u64| qa.contains(x) && qb.contains(x)) {
        assert(sa.intersect(sb) =~= Set::empty());
        // |sa ∪ sb| = |sa| + |sb|
        assert(sa.union(sb).len() + sa.intersect(sb).len() == sa.len() + sb.len()) by {
            lemma_set_intersect_union_lens(sa, sb);
        }
        assert(false);
    }
}

// quorum_intersection_impl.rs: impl QuorumIntersection<BTreeSet> for BTreeSet
fn btree_intersects_with(a: &Vec<u64>, b: &Vec<u64>) -> (r: Option<bool>)
    requires a@.no_duplicates(), b@.no_duplicates(), a@.len() < usize::MAX / 4, b@.len() < usize::MAX / 4
    ensures r == Some(true) ==> always_intersect(seq![st(a@)], seq![st(b@)]),
            r.is_some()
{
    proof { a@.unique_seq_to_set(); b@.unique_seq_to_set(); }
    let majority_self = a.len() / 2 + 1;
    let majority_other = b.len() / 2 + 1;
    let only_self = count_filter(a, b, false);
    let only_other = count_filter(b, a, false);
    let shared = count_filter(a, b, true);
    let need_self = majority_self.saturating_sub(only_self);
    let need_other = majority_other.saturating_sub(only_other);
    let r = need_self + need_other > shared;
    if r {
        assert forall|qa: Set<u64>, qb: Set<u64>| true
            && joint_quorum(seq![st(a@)], qa) && joint_quorum(seq![st(b@)], qb)
            implies exists|x: u64| qa.contains(x) && qb.contains(x) by {
            assert(seq![st(a@)][0] == st(a@));
            assert(seq![st(b@)][0] == st(b@));
            lemma_btree_intersect(st(a@), st(b@), qa, qb);
        }
    }
    Some(r)
}

// A joint quorum of `cs` is a majority of each part.
proof fn lemma_joint_part(cs: Seq<Set<u64>>, q: Set<u64>, i: int)
    requires joint_quorum(cs, q), 0 <= i < cs.len()
    ensures joint_quorum(seq![cs[i]], q)
{ assert(seq![cs[i]][0] == cs[i]); }

// quorum_intersection_impl.rs: impl QuorumIntersection<Vec<BTreeSet>> for Vec<BTreeSet>
fn vec_intersects_with(a: &Vec<Vec<u64>>, b: &Vec<Vec<u64>>) -> (r: Option<bool>)
    requires
        forall|i: int| 0 <= i < a@.len() ==> (#[trigger] a@[i])@.no_duplicates() && a@[i]@.len() < usize::MAX / 4,
        forall|i: int| 0 <= i < b@.len() ==> (#[trigger] b@[i])@.no_duplicates() && b@[i]@.len() < usize::MAX / 4,
    ensures r == Some(true) ==> always_intersect(sets(a@), sets(b@))
{
    let either_is_empty = a.len() == 0 || b.len() == 0;
    if either_is_empty {
        return Some(true); // vacuous: an empty joint config has no quorum (vec_is_quorum)
    }
    let both_uniform = a.len() == 1 && b.len() == 1;
    if both_uniform {
        let r = btree_intersects_with(&a[0], &b[0]);
        proof {
            assert(sets(a@) =~= seq![st(a@[0]@)]);
            assert(sets(b@) =~= seq![st(b@[0]@)]);
        }
        return r;
    }
    let mut i = 0;
    while i < a.len()
        invariant 0 <= i <= a.len(),
            forall|k: int| 0 <= k < a@.len() ==> (#[trigger] a@[k])@.no_duplicates() && a@[k]@.len() < usize::MAX / 4,
            forall|k: int| 0 <= k < b@.len() ==> (#[trigger] b@[k])@.no_duplicates() && b@[k]@.len() < usize::MAX / 4,
        decreases a.len() - i
    {
        let mut j = 0;
        while j < b.len()
            invariant 0 <= i < a.len(), 0 <= j <= b.len(),
                forall|k: int| 0 <= k < a@.len() ==> (#[trigger] a@[k])@.no_duplicates() && a@[k]@.len() < usize::MAX / 4,
                forall|k: int| 0 <= k < b@.len() ==> (#[trigger] b@[k])@.no_duplicates() && b@[k]@.len() < usize::MAX / 4,
            decreases b.len() - j
        {
            let intersects = btree_intersects_with(&a[i], &b[j]);
            if intersects == Some(true) {
                proof {
                    let sa = sets(a@); let sb = sets(b@);
                    assert(sa[i as int] == st(a@[i as int]@));
                    assert(sb[j as int] == st(b@[j as int]@));
                    assert forall|qa: Set<u64>, qb: Set<u64>| true
                        && joint_quorum(sa, qa) && joint_quorum(sb, qb)
                        implies exists|x: u64| qa.contains(x) && qb.contains(x) by {
                        lemma_joint_part(sa, qa, i as int);
                        lemma_joint_part(sb, qb, j as int);
                    }
                }
                return Some(true);
            }
            j += 1;
        }
        i += 1;
    }
    None
}

// Sanity: the spec is not vacuous (a 3-node majority exists).
proof fn sanity() {
    let c = set![1u64, 2, 3];
    let q = set![1u64, 2];
    assert(c.intersect(q) =~= q);
    assert(maj(c, q));
}

fn main() {}

} // verus!
