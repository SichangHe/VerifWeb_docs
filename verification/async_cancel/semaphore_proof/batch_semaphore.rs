#![allow(unused_imports, dead_code, non_snake_case)]
#![cfg_attr(verus_keep_ghost, verifier::exec_allows_no_decreases_clause)]
use std::sync::Arc;
use std::task::{Context, Poll, Waker};
use vstd::atomic_ghost::*;
use vstd::invariant::*;
use vstd::prelude::*;
use vstd::rwlock::{RwLock, RwLockPredicate, WriteHandle};
use vstd::tokens::*;
use verus_state_machines_macros::tokenized_state_machine;

verus! {

global size_of usize == 8;

pub open spec fn MAXP() -> nat { 0x1fff_ffff_ffff_ffff } // usize::MAX >> 3 on 64-bit

pub ghost struct CounterG { pub permits: nat, pub closed: bool }

pub ghost struct LockG {
    pub queue: Seq<nat>,
    pub reg: Set<nat>,
    pub closed: bool,
    pub blocked: bool,
    pub popping: bool,
}

pub ghost struct WS { pub num: nat, pub state: nat }

pub ghost enum Own { Idle, Fast, Reg, Done }

pub ghost enum Key { W(nat), O(nat) }

pub open spec fn contrib(o: Own, w: WS) -> nat {
    match o {
        Own::Fast | Own::Reg => (w.num - w.state) as nat,
        _ => 0,
    }
}

pub open spec fn cmap(own: Map<nat, Own>, ws: Map<nat, WS>) -> Map<nat, nat> {
    Map::new(|k: nat| own.dom().contains(k), |k: nat| contrib(own[k], ws[k]))
}

pub open spec fn msum<K>(m: Map<K, nat>) -> nat
    decreases m.dom().len()
{
    if m.dom().finite() && m.dom().len() > 0 {
        let k = m.dom().choose();
        m[k] + msum(m.remove(k))
    } else {
        0
    }
}

pub proof fn lemma_msum_remove<K>(m: Map<K, nat>, k: K)
    requires m.dom().finite(), m.dom().contains(k),
    ensures msum(m) == m[k] + msum(m.remove(k)),
    decreases m.dom().len(),
{
    let c = m.dom().choose();
    assert(m.dom().len() > 0) by { vstd::set_lib::lemma_set_empty_equivalency_len(m.dom()); }
    if c != k {
        let mc = m.remove(c);
        let mk = m.remove(k);
        lemma_msum_remove(mc, k);
        lemma_msum_remove(mk, c);
        assert(mc.remove(k) =~= mk.remove(c));
    }
}

pub proof fn lemma_msum_insert<K>(m: Map<K, nat>, k: K, v: nat)
    requires m.dom().finite(),
    ensures
        m.dom().contains(k) ==> msum(m.insert(k, v)) + m[k] == msum(m) + v,
        !m.dom().contains(k) ==> msum(m.insert(k, v)) == msum(m) + v,
{
    let m2 = m.insert(k, v);
    lemma_msum_remove(m2, k);
    if m.dom().contains(k) {
        lemma_msum_remove(m, k);
        assert(m2.remove(k) =~= m.remove(k));
    } else {
        assert(m2.remove(k) =~= m);
    }
}

pub proof fn lemma_msum_ge<K>(m: Map<K, nat>, k: K)
    requires m.dom().finite(), m.dom().contains(k),
    ensures msum(m) >= m[k],
{
    lemma_msum_remove(m, k);
}

pub proof fn lemma_cmap_update(own: Map<nat, Own>, ws: Map<nat, WS>, k: nat, o: Own, w: WS)
    requires own.dom().contains(k),
    ensures cmap(own.insert(k, o), ws.insert(k, w)) =~= cmap(own, ws).insert(k, contrib(o, w)),
{
}

pub proof fn lemma_cmap_finite(own: Map<nat, Own>, ws: Map<nat, WS>)
    requires own.dom().finite(),
    ensures cmap(own, ws).dom() =~= own.dom(), cmap(own, ws).dom().finite(),
{
    assert(cmap(own, ws).dom() =~= own.dom());
}

tokenized_state_machine!{
    Sem {
        fields {
            // the permit counter (shifted out of the atomic word); token in the atomic
            #[sharding(variable)] pub counter: CounterG,
            // the wait list and closed flag; token inside the mutex
            #[sharding(variable)] pub lk: LockG,
            // each waiter's `state` atomic; token inside that atomic
            #[sharding(map)] pub ws: Map<nat, WS>,
            // each Acquire future's protocol phase; token held by the future
            #[sharding(map)] pub own: Map<nat, Own>,
            // each future's requested permits (duplicable)
            #[sharding(persistent_map)] pub nums: Map<nat, nat>,
            // permits held in a local variable of a running operation
            #[sharding(map)] pub fl: Map<Key, nat>,
            // permits handed to callers (SemaphorePermit etc.)
            #[sharding(count)] pub held: nat,
            // right to add brand-new permits, bounded by MAX_PERMITS
            #[sharding(count)] pub budget: nat,
            // ghost id allocator
            #[sharding(variable)] pub next_id: nat,
            // initial + added - forgotten
            #[sharding(not_tokenized)] pub total: nat,
            // whether `close` may ever be called (false for Mutex and RwLock, which never close)
            #[sharding(constant)] pub closable: bool,
        }

        pub open spec fn ledger(&self) -> nat {
            self.counter.permits + msum(cmap(self.own, self.ws)) + msum(self.fl) + self.held
        }

        #[invariant]
        pub fn inv_doms(&self) -> bool {
            &&& self.own.dom().finite()
            &&& self.fl.dom().finite()
            &&& forall|k: nat| #[trigger] self.own.dom().contains(k) ==> {
                &&& k < self.next_id
                &&& self.ws.dom().contains(k)
                &&& self.nums.dom().contains(k)
                &&& self.fl.dom().contains(Key::W(k))
            }
            &&& forall|k: nat| #[trigger] self.ws.dom().contains(k) ==> self.own.dom().contains(k)
            &&& forall|k: nat| #[trigger] self.nums.dom().contains(k) ==> self.own.dom().contains(k)
            &&& forall|k: nat| #[trigger] self.fl.dom().contains(Key::W(k)) ==> self.own.dom().contains(k)
            &&& forall|k: nat| #[trigger] self.fl.dom().contains(Key::O(k)) ==> k < self.next_id
        }

        #[invariant]
        pub fn inv_ws(&self) -> bool {
            forall|k: nat| #[trigger] self.own.dom().contains(k) ==> {
                &&& self.ws[k].state <= self.ws[k].num
                &&& self.ws[k].num <= MAXP()
                &&& self.nums[k] == self.ws[k].num
                &&& (self.own[k] == Own::Idle ==> self.ws[k].state == self.ws[k].num)
                &&& (self.own[k] == Own::Fast ==> self.ws[k].state == 0)
            }
        }

        /// Permit conservation.
        #[invariant]
        pub fn inv_ledger(&self) -> bool {
            &&& self.ledger() == self.total
            &&& self.total + self.budget <= MAXP()
        }

        #[invariant]
        pub fn inv_closed(&self) -> bool {
            &&& self.counter.closed == self.lk.closed
            &&& (!self.lk.closed && self.lk.queue.len() > 0 ==> self.lk.blocked)
            &&& (self.lk.blocked && !self.lk.closed ==> self.counter.permits == 0)
            &&& (!self.closable ==> !self.counter.closed)
        }

        #[invariant]
        pub fn inv_queue(&self) -> bool {
            &&& self.lk.queue.no_duplicates()
            &&& forall|i: int| 0 <= i < self.lk.queue.len() ==> {
                &&& self.own.dom().contains(#[trigger] self.lk.queue[i])
                &&& self.own[self.lk.queue[i]] == Own::Reg
                &&& (self.ws[self.lk.queue[i]].state > 0 || (self.lk.popping && i == self.lk.queue.len() - 1))
                &&& (!self.lk.closed ==> self.fl[Key::W(self.lk.queue[i])] == 0)
            }
            &&& forall|k: nat| #[trigger] self.lk.reg.contains(k) <==> (self.own.dom().contains(k) && self.own[k] == Own::Reg)
            &&& (self.lk.popping ==> self.lk.queue.len() > 0)
        }

        init!{
            initialize(n: nat, closable: bool) {
                require(n <= MAXP());
                init counter = CounterG { permits: n, closed: false };
                init lk = LockG { queue: Seq::empty(), reg: Set::empty(), closed: false, blocked: false, popping: false };
                init ws = Map::empty();
                init own = Map::empty();
                init nums = Map::empty();
                init fl = Map::empty();
                init held = 0;
                init budget = (MAXP() - n) as nat;
                init next_id = 0;
                init total = n;
                init closable = closable;
            }
        }

        transition!{
            new_waiter(num: nat) {
                require(num <= MAXP());
                update next_id = pre.next_id + 1;
                add own += [pre.next_id => Own::Idle];
                add ws += [pre.next_id => WS { num, state: num }];
                add nums (union)= [pre.next_id => num];
                add fl += [Key::W(pre.next_id) => 0];
            }
        }

        transition!{
            new_op() {
                update next_id = pre.next_id + 1;
                add fl += [Key::O(pre.next_id) => 0];
            }
        }

        // lock-free CAS that moves k permits from the counter into a local
        transition!{
            take(op: Key, k: nat) {
                require(!pre.counter.closed && k <= pre.counter.permits);
                update counter = CounterG { permits: (pre.counter.permits - k) as nat, closed: false };
                remove fl -= [op => let a];
                add fl += [op => a + k];
            }
        }

        // the same CAS performed with the wait-list lock held, emptying the counter
        transition!{
            take_block(op: Key, k: nat) {
                require(!pre.counter.closed && k == pre.counter.permits);
                update counter = CounterG { permits: 0, closed: false };
                update lk = LockG { blocked: true, ..pre.lk };
                remove fl -= [op => let a];
                add fl += [op => a + k];
            }
        }

        // poll_acquire fast path: `node.state.store(0)` after taking all permits
        transition!{
            fast_store(id: nat) {
                remove own -= [id => Own::Idle];
                add own += [id => Own::Fast];
                remove ws -= [id => let w];
                add ws += [id => WS { num: w.num, state: 0 }];
                remove fl -= [Key::W(id) => let a];
                require(a == w.num);
                add fl += [Key::W(id) => 0];
            }
        }

        // poll_acquire, first time under the lock: assign_permits on its own node; enqueue if not done
        transition!{
            reg_assign(id: nat, amt: nat) {
                require(!pre.lk.closed && !pre.lk.popping && pre.lk.blocked);
                remove own -= [id => Own::Idle];
                remove ws -= [id => let w];
                remove fl -= [Key::W(id) => let a];
                require(amt == if a <= w.state { a } else { w.state });
                add ws += [id => WS { num: w.num, state: (w.state - amt) as nat }];
                add fl += [Key::W(id) => (a - amt) as nat];
                add own += [id => if w.state - amt == 0 { Own::Fast } else { Own::Reg }];
                update lk = if w.state - amt == 0 { pre.lk } else {
                    LockG { reg: pre.lk.reg.insert(id), queue: Seq::empty().push(id) + pre.lk.queue, ..pre.lk }
                };
            }
        }

        // poll_acquire of a registered waiter, under the lock: assign_permits on its own node
        transition!{
            assign_own(id: nat, amt: nat) {
                require(!pre.lk.closed && !pre.lk.popping);
                remove own -= [id => Own::Reg];
                remove ws -= [id => let w];
                remove fl -= [Key::W(id) => let a];
                require(amt == if a <= w.state { a } else { w.state });
                add ws += [id => WS { num: w.num, state: (w.state - amt) as nat }];
                add fl += [Key::W(id) => (a - amt) as nat];
                add own += [id => if w.state - amt == 0 { Own::Fast } else { Own::Reg }];
                update lk = if w.state - amt == 0 { LockG { reg: pre.lk.reg.remove(id), ..pre.lk } } else { pre.lk };
            }
        }

        // add_permits_locked: assign_permits on queue.last()
        transition!{
            assign_q(op: Key, amt: nat) {
                require(pre.lk.queue.len() > 0 && !pre.lk.popping);
                remove ws -= [pre.lk.queue.last() => let w];
                remove fl -= [op => let a];
                require(amt == if a <= w.state { a } else { w.state });
                add ws += [pre.lk.queue.last() => WS { num: w.num, state: (w.state - amt) as nat }];
                add fl += [op => (a - amt) as nat];
                update lk = LockG { popping: w.state - amt == 0, ..pre.lk };
            }
        }

        // pop_back of the wait list (add_permits_locked and close)
        transition!{
            pop() {
                require(pre.lk.queue.len() > 0);
                update lk = LockG { queue: pre.lk.queue.drop_last(), popping: false, ..pre.lk };
            }
        }

        // Acquire::drop: queue.remove(node)
        transition!{
            unlink(i: int) {
                require(0 <= i < pre.lk.queue.len() && !pre.lk.popping);
                update lk = LockG { queue: pre.lk.queue.remove(i), ..pre.lk };
            }
        }

        // Acquire::drop: load the state of an unlinked waiter and take its permits
        transition!{
            retire(id: nat) {
                require(!pre.lk.queue.contains(id) && !pre.lk.popping);
                remove own -= [id => let o];
                require(o == Own::Reg || o == Own::Fast);
                have ws >= [id => let w];
                remove fl -= [Key::W(id) => let a];
                add own += [id => Own::Done];
                add fl += [Key::W(id) => a + (w.num - w.state) as nat];
                update lk = LockG { reg: pre.lk.reg.remove(id), ..pre.lk };
            }
        }

        // Acquire::drop of a future that is not queued
        transition!{
            retire_idle(id: nat) {
                remove own -= [id => Own::Idle];
                add own += [id => Own::Done];
            }
        }

        // Acquire::poll: `*queued = false` after Ready(Ok); permits go to the caller
        transition!{
            complete(id: nat) {
                remove own -= [id => Own::Fast];
                add own += [id => Own::Done];
                have nums >= [id => let n];
                add held += (n);
            }
        }

        // poll_acquire close path (candidate fix): return local permits to the counter
        transition!{
            give_back(op: Key, k: nat) {
                require(pre.lk.closed);
                remove fl -= [op => let a];
                require(k <= a);
                add fl += [op => (a - k) as nat];
                update counter = CounterG { permits: pre.counter.permits + k, ..pre.counter };
            }
        }

        // add_permits_locked: queue empty, put the rest into the counter
        transition!{
            release_rest(op: Key, k: nat) {
                require(pre.lk.queue.len() == 0 && !pre.lk.popping);
                remove fl -= [op => let a];
                require(k <= a);
                add fl += [op => (a - k) as nat];
                update counter = CounterG { permits: pre.counter.permits + k, ..pre.counter };
                update lk = LockG { blocked: false, ..pre.lk };
            }
        }

        transition!{
            close_bit() {
                require(pre.closable);
                update counter = CounterG { closed: true, ..pre.counter };
                update lk = LockG { closed: true, ..pre.lk };
            }
        }

        transition!{
            forget(k: nat) {
                require(k <= pre.counter.permits);
                update counter = CounterG { permits: (pre.counter.permits - k) as nat, ..pre.counter };
                update total = (pre.total - k) as nat;
            }
        }

        transition!{
            try_take(k: nat) {
                require(!pre.counter.closed && k <= pre.counter.permits);
                update counter = CounterG { permits: (pre.counter.permits - k) as nat, ..pre.counter };
                add held += (k);
            }
        }

        // release(k) of permits the caller holds
        transition!{
            begin_release(op: nat, k: nat) {
                remove held -= (k);
                remove fl -= [Key::O(op) => let a];
                add fl += [Key::O(op) => a + k];
            }
        }

        // a client object moves k permits it holds to another of its keyed tokens
        // (SemaphorePermit::merge/split, mpsc Permit::send into the message)
        transition!{
            transfer(from: Key, to: Key, a: nat, b: nat, k: nat) {
                require(from != to && k <= a && from is O && to is O);
                remove fl -= (Map::empty().insert(from, a).insert(to, b));
                add fl += (Map::empty().insert(from, (a - k) as nat).insert(to, b + k));
            }
        }

        // SemaphorePermit::forget: the permits leave circulation for good
        transition!{
            forget_held(op: Key, k: nat) {
                require(op is O);
                remove fl -= [op => let a];
                require(k <= a);
                add fl += [op => (a - k) as nat];
                update total = (pre.total - k) as nat;
            }
        }

        // release(k) of brand-new permits (Semaphore::add_permits)
        transition!{
            mint(op: nat, k: nat) {
                remove budget -= (k);
                remove fl -= [Key::O(op) => let a];
                add fl += [Key::O(op) => a + k];
                update total = pre.total + k;
            }
        }

        property!{
            counter_bound(op: Key) {
                have fl >= [op => let a];
                assert(pre.counter.permits + a <= MAXP()) by {
                    lemma_cmap_finite(pre.own, pre.ws);
                    lemma_msum_ge(pre.fl, op);
                };
            }
        }

        property!{
            fl_bound(op: Key) {
                have fl >= [op => let a];
                assert(a <= MAXP()) by {
                    lemma_cmap_finite(pre.own, pre.ws);
                    lemma_msum_ge(pre.fl, op);
                };
            }
        }

        property!{
            open_word() {
                assert(!pre.closable ==> !pre.counter.closed);
            }
        }

        property!{
            open_lk() {
                assert(!pre.closable ==> !pre.lk.closed);
            }
        }

        property!{
            closed_agree() {
                assert(pre.counter.closed == pre.lk.closed);
            }
        }

        property!{
            q_nodup() {
                assert(pre.lk.queue.no_duplicates());
            }
        }

        property!{
            ws_bound(id: nat) {
                have ws >= [id => let w];
                have nums >= [id => let n];
                assert(w.state <= w.num && w.num == n && n <= MAXP());
            }
        }

        property!{
            fast_zero(id: nat) {
                have own >= [id => Own::Fast];
                have ws >= [id => let w];
                assert(w.state == 0);
            }
        }

        property!{
            idle_full(id: nat) {
                have own >= [id => Own::Idle];
                have ws >= [id => let w];
                assert(w.state == w.num);
            }
        }

        // a registered waiter that is in the queue while open owes nothing locally
        property!{
            linked_no_local(id: nat) {
                have fl >= [Key::W(id) => let a];
                assert(pre.lk.queue.contains(id) && !pre.lk.closed ==> a == 0);
            }
        }

        #[inductive(initialize)]
        fn initialize_inductive(post: Self, n: nat, closable: bool) {
            assert(cmap(post.own, post.ws) =~= Map::empty());
            assert(msum(Map::<nat, nat>::empty()) == 0);
            assert(msum(Map::<Key, nat>::empty()) == 0);
        }

        #[inductive(new_waiter)]
        fn new_waiter_inductive(pre: Self, post: Self, num: nat) {
            let id = pre.next_id;
            lemma_msum_insert(pre.fl, Key::W(id), 0);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws).insert(id, 0));
            lemma_cmap_finite(pre.own, pre.ws);
            lemma_msum_insert(cmap(pre.own, pre.ws), id, 0);
            assert forall|i: int| 0 <= i < post.lk.queue.len() implies post.ws[post.lk.queue[i]] == pre.ws[pre.lk.queue[i]] by {
                assert(pre.own.dom().contains(pre.lk.queue[i]));
            }
        }

        #[inductive(new_op)]
        fn new_op_inductive(pre: Self, post: Self) {
            lemma_msum_insert(pre.fl, Key::O(pre.next_id), 0);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
        }

        #[inductive(take)]
        fn take_inductive(pre: Self, post: Self, op: Key, k: nat) {
            assert(post.fl =~= pre.fl.insert(op, pre.fl[op] + k));
            let a = pre.fl[op];
            lemma_msum_insert(pre.fl, op, a + k);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
            assert forall|i: int| 0 <= i < post.lk.queue.len() && !post.lk.closed implies
                post.fl[Key::W(post.lk.queue[i])] == 0 by {
                assert(pre.lk.blocked);
            }
        }

        #[inductive(take_block)]
        fn take_block_inductive(pre: Self, post: Self, op: Key, k: nat) {
            assert(post.fl =~= pre.fl.insert(op, pre.fl[op] + k));
            let a = pre.fl[op];
            lemma_msum_insert(pre.fl, op, a + k);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
            assert forall|i: int| 0 <= i < post.lk.queue.len() && !post.lk.closed implies
                post.fl[Key::W(post.lk.queue[i])] == 0 by {
                assert(pre.lk.blocked);
            }
        }

        #[inductive(fast_store)]
        fn fast_store_inductive(pre: Self, post: Self, id: nat) {
            assert(post.fl =~= pre.fl.insert(Key::W(id), 0));
            assert(post.own =~= pre.own.insert(id, Own::Fast));
            assert(post.ws =~= pre.ws.insert(id, WS { num: pre.ws[id].num, state: 0 }));
            let w = pre.ws[id];
            lemma_msum_insert(pre.fl, Key::W(id), 0);
            lemma_cmap_update(pre.own, pre.ws, id, Own::Fast, WS { num: w.num, state: 0 });
            lemma_cmap_finite(pre.own, pre.ws);
            lemma_msum_insert(cmap(pre.own, pre.ws), id, w.num);
            assert(!pre.lk.queue.contains(id));
            assert forall|i: int| 0 <= i < post.lk.queue.len() implies post.lk.queue[i] != id by {}
            assert forall|k: nat| post.own.dom().contains(k) && k != id implies post.own[k] == pre.own[k] by {}
        }

        #[inductive(reg_assign)]
        fn reg_assign_inductive(pre: Self, post: Self, id: nat, amt: nat) {
            let o2 = if pre.ws[id].state - amt == 0 { Own::Fast } else { Own::Reg };
            assert(post.fl =~= pre.fl.insert(Key::W(id), (pre.fl[Key::W(id)] - amt) as nat));
            assert(post.own =~= pre.own.insert(id, o2));
            assert(post.ws =~= pre.ws.insert(id, WS { num: pre.ws[id].num, state: (pre.ws[id].state - amt) as nat }));
            let w = pre.ws[id];
            let a = pre.fl[Key::W(id)];
            let nw = WS { num: w.num, state: (w.state - amt) as nat };
            let o = if w.state - amt == 0 { Own::Fast } else { Own::Reg };
            lemma_msum_insert(pre.fl, Key::W(id), (a - amt) as nat);
            lemma_cmap_update(pre.own, pre.ws, id, o, nw);
            lemma_cmap_finite(pre.own, pre.ws);
            lemma_msum_insert(cmap(pre.own, pre.ws), id, contrib(o, nw));
            assert(!pre.lk.queue.contains(id));
            assert(!pre.lk.reg.contains(id));
            if w.state - amt != 0 {
                let q = post.lk.queue;
                assert(q[0] == id);
                assert forall|i: int| 1 <= i < q.len() implies q[i] == pre.lk.queue[i - 1] by {}
                assert forall|i: int, j: int| 0 <= i < q.len() && 0 <= j < q.len() && i != j implies q[i] != q[j] by {
                    if i > 0 && j > 0 { assert(pre.lk.queue[i - 1] != pre.lk.queue[j - 1]); }
                    else if i == 0 { assert(pre.lk.queue[j - 1] != id); }
                    else { assert(pre.lk.queue[i - 1] != id); }
                }
                assert forall|i: int| 0 <= i < q.len() implies {
                    &&& post.own.dom().contains(#[trigger] q[i])
                    &&& post.own[q[i]] == Own::Reg
                    &&& (post.ws[q[i]].state > 0 || (post.lk.popping && i == q.len() - 1))
                    &&& (!post.lk.closed ==> post.fl[Key::W(q[i])] == 0)
                } by {
                    if i > 0 { assert(pre.lk.queue[i - 1] != id); }
                }
            } else {
                assert forall|i: int| 0 <= i < post.lk.queue.len() implies post.lk.queue[i] != id by {}
            }
        }

        #[inductive(assign_own)]
        fn assign_own_inductive(pre: Self, post: Self, id: nat, amt: nat) {
            let o2 = if pre.ws[id].state - amt == 0 { Own::Fast } else { Own::Reg };
            assert(post.fl =~= pre.fl.insert(Key::W(id), (pre.fl[Key::W(id)] - amt) as nat));
            assert(post.own =~= pre.own.insert(id, o2));
            assert(post.ws =~= pre.ws.insert(id, WS { num: pre.ws[id].num, state: (pre.ws[id].state - amt) as nat }));
            let w = pre.ws[id];
            let a = pre.fl[Key::W(id)];
            let nw = WS { num: w.num, state: (w.state - amt) as nat };
            let o = if w.state - amt == 0 { Own::Fast } else { Own::Reg };
            lemma_msum_insert(pre.fl, Key::W(id), (a - amt) as nat);
            lemma_cmap_update(pre.own, pre.ws, id, o, nw);
            lemma_cmap_finite(pre.own, pre.ws);
            lemma_msum_insert(cmap(pre.own, pre.ws), id, contrib(o, nw));
            if pre.lk.queue.contains(id) {
                let i = pre.lk.queue.index_of(id);
                assert(pre.lk.queue[i] == id);
                assert(a == 0);
                assert(w.state > 0);
            }
            assert forall|i: int| 0 <= i < post.lk.queue.len() && post.lk.queue[i] == id implies
                w.state - amt != 0 by {
                assert(pre.lk.queue.contains(id));
                let j = pre.lk.queue.index_of(id);
            }
        }

        #[inductive(assign_q)]
        fn assign_q_inductive(pre: Self, post: Self, op: Key, amt: nat) {
            assert(post.fl =~= pre.fl.insert(op, (pre.fl[op] - amt) as nat));
            assert(post.ws =~= pre.ws.insert(pre.lk.queue.last(), WS { num: pre.ws[pre.lk.queue.last()].num, state: (pre.ws[pre.lk.queue.last()].state - amt) as nat }));
            let id = pre.lk.queue.last();
            let last = pre.lk.queue.len() - 1;
            assert(pre.lk.queue[last] == id);
            let w = pre.ws[id];
            let a = pre.fl[op];
            let nw = WS { num: w.num, state: (w.state - amt) as nat };
            lemma_msum_insert(pre.fl, op, (a - amt) as nat);
            assert(pre.own[id] == Own::Reg);
            lemma_cmap_update(pre.own, pre.ws, id, Own::Reg, nw);
            assert(pre.own.insert(id, Own::Reg) =~= pre.own);
            lemma_cmap_finite(pre.own, pre.ws);
            lemma_msum_insert(cmap(pre.own, pre.ws), id, contrib(Own::Reg, nw));
            assert forall|i: int| 0 <= i < post.lk.queue.len() implies
                (post.ws[#[trigger] post.lk.queue[i]].state > 0 || (post.lk.popping && i == post.lk.queue.len() - 1)) by {
                if i != last { assert(pre.lk.queue[i] != id); }
            }
            assert forall|i: int| 0 <= i < post.lk.queue.len() && !post.lk.closed implies
                post.fl[Key::W(#[trigger] post.lk.queue[i])] == 0 by {
                if op == Key::W(pre.lk.queue[i]) { assert(a == 0); }
            }
        }

        #[inductive(pop)]
        fn pop_inductive(pre: Self, post: Self) {
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
            let q = post.lk.queue;
            assert forall|i: int| 0 <= i < q.len() implies q[i] == pre.lk.queue[i] by {}
            assert forall|i: int| 0 <= i < q.len() implies #[trigger] post.ws[q[i]].state > 0 by {
                assert(pre.lk.queue[i] == q[i]);
            }
        }

        #[inductive(unlink)]
        fn unlink_inductive(pre: Self, post: Self, i: int) {
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
            let q = post.lk.queue;
            assert forall|j: int| 0 <= j < q.len() implies #[trigger] q[j] == pre.lk.queue[if j < i { j } else { j + 1 }] by {}
            assert forall|j: int, k: int| 0 <= j < q.len() && 0 <= k < q.len() && j != k implies q[j] != q[k] by {
                let jj = if j < i { j } else { j + 1 };
                let kk = if k < i { k } else { k + 1 };
                assert(pre.lk.queue[jj] != pre.lk.queue[kk]);
            }
            assert forall|j: int| 0 <= j < q.len() implies post.ws[#[trigger] q[j]].state > 0 by {
                let jj = if j < i { j } else { j + 1 };
                assert(q[j] == pre.lk.queue[jj]);
            }
            assert forall|j: int| 0 <= j < q.len() implies post.own.dom().contains(#[trigger] q[j]) by {
                let jj = if j < i { j } else { j + 1 };
                assert(q[j] == pre.lk.queue[jj]);
            }
        }

        #[inductive(retire)]
        fn retire_inductive(pre: Self, post: Self, id: nat) {
            assert(post.fl =~= pre.fl.insert(Key::W(id), pre.fl[Key::W(id)] + (pre.ws[id].num - pre.ws[id].state) as nat));
            assert(post.own =~= pre.own.insert(id, Own::Done));
            let w = pre.ws[id];
            let a = pre.fl[Key::W(id)];
            let o = pre.own[id];
            lemma_msum_insert(pre.fl, Key::W(id), a + (w.num - w.state) as nat);
            lemma_cmap_update(pre.own, pre.ws, id, Own::Done, w);
            assert(pre.ws.insert(id, w) =~= pre.ws);
            lemma_cmap_finite(pre.own, pre.ws);
            lemma_msum_insert(cmap(pre.own, pre.ws), id, 0);
            assert forall|i: int| 0 <= i < post.lk.queue.len() implies post.lk.queue[i] != id by {}
        }

        #[inductive(retire_idle)]
        fn retire_idle_inductive(pre: Self, post: Self, id: nat) {
            assert(post.own =~= pre.own.insert(id, Own::Done));
            let w = pre.ws[id];
            lemma_cmap_update(pre.own, pre.ws, id, Own::Done, w);
            assert(pre.ws.insert(id, w) =~= pre.ws);
            lemma_cmap_finite(pre.own, pre.ws);
            lemma_msum_insert(cmap(pre.own, pre.ws), id, 0);
            assert(!pre.lk.queue.contains(id));
            assert forall|i: int| 0 <= i < post.lk.queue.len() implies post.lk.queue[i] != id by {}
        }

        #[inductive(complete)]
        fn complete_inductive(pre: Self, post: Self, id: nat) {
            assert(post.own =~= pre.own.insert(id, Own::Done));
            let w = pre.ws[id];
            lemma_cmap_update(pre.own, pre.ws, id, Own::Done, w);
            assert(pre.ws.insert(id, w) =~= pre.ws);
            lemma_cmap_finite(pre.own, pre.ws);
            lemma_msum_insert(cmap(pre.own, pre.ws), id, 0);
            assert(!pre.lk.queue.contains(id));
            assert forall|i: int| 0 <= i < post.lk.queue.len() implies post.lk.queue[i] != id by {}
        }

        #[inductive(give_back)]
        fn give_back_inductive(pre: Self, post: Self, op: Key, k: nat) {
            assert(post.fl =~= pre.fl.insert(op, (pre.fl[op] - k) as nat));
            let a = pre.fl[op];
            lemma_msum_insert(pre.fl, op, (a - k) as nat);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
        }

        #[inductive(release_rest)]
        fn release_rest_inductive(pre: Self, post: Self, op: Key, k: nat) {
            assert(post.fl =~= pre.fl.insert(op, (pre.fl[op] - k) as nat));
            let a = pre.fl[op];
            lemma_msum_insert(pre.fl, op, (a - k) as nat);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
        }

        #[inductive(close_bit)]
        fn close_bit_inductive(pre: Self, post: Self) { }

        #[inductive(forget)]
        fn forget_inductive(pre: Self, post: Self, k: nat) { }

        #[inductive(try_take)]
        fn try_take_inductive(pre: Self, post: Self, k: nat) { }

        #[inductive(begin_release)]
        fn begin_release_inductive(pre: Self, post: Self, op: nat, k: nat) {
            assert(post.fl =~= pre.fl.insert(Key::O(op), pre.fl[Key::O(op)] + k));
            let a = pre.fl[Key::O(op)];
            lemma_msum_insert(pre.fl, Key::O(op), a + k);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
        }

        #[inductive(transfer)]
        fn transfer_inductive(pre: Self, post: Self, from: Key, to: Key, a: nat, b: nat, k: nat) {
            let mp = Map::empty().insert(from, a).insert(to, b);
            assert(mp.dom().contains(from) && mp.dom().contains(to) && mp[from] == a && mp[to] == b);
            assert(mp.submap_of(pre.fl));
            assert(mp.dom().contains(from) ==> pre.fl.dom().contains(from));
            assert(pre.fl.dom().contains(from));
            assert(pre.fl[from] == a);
            assert(mp.dom().contains(to) ==> pre.fl.dom().contains(to));
            assert(pre.fl.dom().contains(to));
            assert(pre.fl[to] == b);
            let m1 = pre.fl.insert(from, (a - k) as nat);
            assert(m1.dom().contains(to) && m1[to] == b);
            assert(post.fl =~= m1.insert(to, b + k));
            lemma_msum_insert(pre.fl, from, (a - k) as nat);
            lemma_msum_insert(m1, to, b + k);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
        }

        #[inductive(forget_held)]
        fn forget_held_inductive(pre: Self, post: Self, op: Key, k: nat) {
            let a = pre.fl[op];
            assert(post.fl =~= pre.fl.insert(op, (a - k) as nat));
            lemma_msum_insert(pre.fl, op, (a - k) as nat);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
        }

        #[inductive(mint)]
        fn mint_inductive(pre: Self, post: Self, op: nat, k: nat) {
            assert(post.fl =~= pre.fl.insert(Key::O(op), pre.fl[Key::O(op)] + k));
            let a = pre.fl[Key::O(op)];
            lemma_msum_insert(pre.fl, Key::O(op), a + k);
            assert(cmap(post.own, post.ws) =~= cmap(pre.own, pre.ws));
        }
    }
}


// ======================================================================
// Bit-level facts about the permit word (`permits << 1 | CLOSED`).
// ======================================================================

pub proof fn lemma_word(v: usize)
    ensures v & 1 == v % 2, v >> 1 == v / 2, (v & 1 > 0) == (v % 2 == 1), (v & 1 == 1) == (v % 2 == 1),
{
    assert(v & 1 == v % 2) by (bit_vector);
    assert(v >> 1 == v / 2) by (bit_vector);
}

pub proof fn lemma_max()
    ensures Semaphore::MAX_PERMITS == MAXP(),
{
    assert(usize::MAX >> 3usize == 0x1fff_ffff_ffff_ffffusize) by (bit_vector);
}

pub proof fn lemma_shl1(x: usize)
    requires x <= 0x7fff_ffff_ffff_ffff,
    ensures x << 1 == x + x,
{
    assert(x <= 0x7fff_ffff_ffff_ffff ==> x << 1 == x + x) by (bit_vector);
}

pub proof fn lemma_or1(v: usize)
    ensures (v | 1) >> 1 == v >> 1, (v | 1) & 1 == 1,
{
    assert((v | 1) >> 1 == v >> 1) by (bit_vector);
    assert((v | 1) & 1 == 1) by (bit_vector);
}

pub proof fn lemma_or_low(n: usize, b: usize)
    requires n <= 0x7fff_ffff_ffff_ffff,
    ensures (n << 1) | (b & 1) == n + n + b % 2,
{
    assert(n <= 0x7fff_ffff_ffff_ffff ==> (n << 1) | (b & 1) == (n << 1) + (b & 1)) by (bit_vector);
    lemma_shl1(n);
    lemma_word(b);
}

// ======================================================================
// Trusted environment (no effect on permits). Each item is a stand-in for
// Tokio or std code that the proof does not cover; see SEMAPHORE_PROOF.md.
// ======================================================================

#[verifier::external_type_specification]
pub struct ExPoll<T>(Poll<T>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExContext<'a>(Context<'a>);

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExWaker(Waker);

pub assume_specification<T>[ std::mem::drop::<T> ](_0: T);

pub assume_specification<T>[ Poll::<T>::is_ready ](p: &Poll<T>) -> (r: bool)
    ensures r == (*p is Ready);

/// `assert!`/`assert_eq!` in the real code: Verus must prove the condition.
#[verifier::external_body]
pub fn runtime_assert(b: bool)
    requires b,
{
    assert!(b);
}

/// `std::cmp::min` on usize.
#[verifier::external_body]
pub fn min(a: usize, b: usize) -> (r: usize)
    ensures r == if a <= b { a } else { b },
{
    std::cmp::min(a, b)
}

/// `UnsafeCell<Option<Waker>>` in `Waiter`; accessed only with the wait-list lock held.
#[verifier::external_body]
pub struct WakerCell {
    inner: std::cell::UnsafeCell<Option<Waker>>,
}

impl WakerCell {
    #[verifier::external_body]
    pub fn new() -> Self {
        WakerCell { inner: std::cell::UnsafeCell::new(None) }
    }

    /// `waker.with_mut(|waker| (*waker).take())`
    #[verifier::external_body]
    pub fn take(&self) -> Option<Waker> {
        unsafe { (*self.inner.get()).take() }
    }

    /// The `node.waker.with_mut(..)` block of `poll_acquire`; returns `old_waker`.
    #[verifier::external_body]
    pub fn register(&self, cx: &mut Context<'_>) -> Option<Waker> {
        let waker = unsafe { &mut *self.inner.get() };
        if waker.as_ref().is_none_or(|w| !w.will_wake(cx.waker())) {
            waker.replace(cx.waker().clone())
        } else {
            None
        }
    }
}

/// `crate::util::WakeList`.
#[verifier::external_body]
pub struct WakeList {
    v: Vec<Waker>,
}

impl WakeList {
    #[verifier::external_body]
    pub fn new() -> Self { WakeList { v: Vec::new() } }
    #[verifier::external_body]
    pub fn can_push(&self) -> bool { self.v.len() < 32 }
    #[verifier::external_body]
    pub fn push(&mut self, w: Waker) { self.v.push(w) }
    #[verifier::external_body]
    pub fn wake_all(&mut self) { for w in self.v.drain(..) { w.wake() } }
}

/// `crate::task::coop::RestoreOnPending` and `poll_proceed`: may return Pending at any poll.
#[verifier::external_body]
pub struct RestoreOnPending {
    x: (),
}

impl RestoreOnPending {
    #[verifier::external_body]
    pub fn made_progress(&self) {}
}

#[verifier::external_body]
pub fn poll_proceed(cx: &mut Context<'_>) -> Poll<RestoreOnPending> {
    Poll::Ready(RestoreOnPending { x: () })
}

// ----------------------------------------------------------------------
// Intrusive `LinkedList<Waiter>`: trusted specification over a sequence.
// Nodes are identified by their ghost id; Tokio identifies them by address.
// ----------------------------------------------------------------------

pub open spec fn ids(s: Seq<Arc<Waiter>>) -> Seq<nat> {
    s.map_values(|w: Arc<Waiter>| w.id@)
}

#[verifier::external_body]
pub struct LinkedList {
    v: std::collections::VecDeque<Arc<Waiter>>,
}

impl LinkedList {
    pub uninterp spec fn view(&self) -> Seq<Arc<Waiter>>;

    #[verifier::external_body]
    pub fn new() -> (r: Self)
        ensures r@ == Seq::<Arc<Waiter>>::empty(),
    {
        LinkedList { v: std::collections::VecDeque::new() }
    }

    #[verifier::external_body]
    pub fn push_front(&mut self, w: Arc<Waiter>)
        ensures self@ == Seq::empty().push(w) + old(self)@,
    {
        self.v.push_front(w)
    }

    #[verifier::external_body]
    pub fn last(&self) -> (r: Option<&Arc<Waiter>>)
        ensures
            self@.len() == 0 ==> r is None,
            self@.len() > 0 ==> (r matches Some(w) && *w == self@.last()),
    {
        self.v.back()
    }

    #[verifier::external_body]
    pub fn pop_back(&mut self) -> (r: Option<Arc<Waiter>>)
        ensures
            old(self)@.len() == 0 ==> r is None && self@ == old(self)@,
            old(self)@.len() > 0 ==> r == Some(old(self)@.last()) && self@ == old(self)@.drop_last(),
    {
        self.v.pop_back()
    }

    /// `queue.remove(NonNull::from(node))`
    #[verifier::external_body]
    pub fn remove(&mut self, node: &Arc<Waiter>) -> (r: Option<Arc<Waiter>>)
        ensures
            !ids(old(self)@).contains(node.id@) ==> r is None && self@ == old(self)@,
            ids(old(self)@).contains(node.id@) && ids(old(self)@).no_duplicates() ==>
                r is Some && self@ == old(self)@.remove(ids(old(self)@).index_of(node.id@)),
    {
        let i = self.v.iter().position(|w| Arc::ptr_eq(w, node))?;
        self.v.remove(i)
    }
}

// ----------------------------------------------------------------------
// `loom::sync::Mutex<Waitlist>`, built on vstd's verified RwLock (write mode).
// The guard must be released explicitly; Rust releases it on drop.
// ----------------------------------------------------------------------

pub struct Waitlist {
    pub queue: LinkedList,
    pub closed: bool,
}

pub struct LockVal {
    pub w: Waitlist,
    pub tok: Tracked<Sem::lk>,
}

/// The wait-list invariant except `!popping`.
pub open spec fn wl_inv(inst_id: InstanceId, w: &Waitlist, t: Sem::lk) -> bool {
    &&& t.instance_id() == inst_id
    &&& ids(w.queue@) == t.value().queue
    &&& w.closed == t.value().closed
    &&& forall|i: int| 0 <= i < w.queue@.len() ==> {
        &&& (#[trigger] w.queue@[i]).wf()
        &&& w.queue@[i].inst@.id() == inst_id
    }
}

pub ghost struct LockPred {
    pub inst_id: InstanceId,
}

impl RwLockPredicate<LockVal> for LockPred {
    open spec fn inv(self, v: LockVal) -> bool {
        wl_inv(self.inst_id, &v.w, v.tok@) && !v.tok@.value().popping
    }
}

pub struct Mutex {
    pub rw: RwLock<LockVal, LockPred>,
}

pub struct MutexGuard<'a> {
    pub w: Waitlist,
    pub h: WriteHandle<'a, LockVal, LockPred>,
}

impl Mutex {
    pub open spec fn pred(&self) -> LockPred {
        self.rw.pred()
    }

    pub fn lock(&self) -> (r: (MutexGuard<'_>, Tracked<Sem::lk>))
        ensures
            r.0.h.rwlock() == self.rw,
            wl_inv(self.pred().inst_id, &r.0.w, r.1@),
            !r.1@.value().popping,
    {
        let (v, h) = self.rw.acquire_write();
        let LockVal { w, tok } = v;
        (MutexGuard { w, h }, tok)
    }
}

impl<'a> MutexGuard<'a> {
    pub fn unlock(self, Tracked(t): Tracked<Sem::lk>)
        requires
            wl_inv(self.h.rwlock().pred().inst_id, &self.w, t),
            !t.value().popping,
    {
        let MutexGuard { w, h } = self;
        h.release_write(LockVal { w, tok: Tracked(t) });
    }
}

// ----------------------------------------------------------------------
// ghost helpers
// ----------------------------------------------------------------------

pub proof fn lemma_ids_remove(s: Seq<Arc<Waiter>>, i: int)
    requires 0 <= i < s.len(),
    ensures ids(s.remove(i)) =~= ids(s).remove(i),
{
    assert forall|j: int| 0 <= j < s.len() - 1 implies ids(s.remove(i))[j] == ids(s).remove(i)[j] by {
        assert(s.remove(i)[j] == s[if j < i { j } else { j + 1 }]);
    }
}

pub proof fn lemma_remove_nodup(q: Seq<nat>, i: int)
    requires 0 <= i < q.len(), q.no_duplicates(),
    ensures !q.remove(i).contains(q[i]),
{
    assert forall|j: int| 0 <= j < q.len() - 1 implies q.remove(i)[j] != q[i] by {
        assert(q.remove(i)[j] == q[if j < i { j } else { j + 1 }]);
    }
}

pub proof fn take_fl(tracked r: &mut Sem::fl) -> (tracked t: Sem::fl)
    ensures t == *old(r),
{
    let tracked mut a = Sem::fl::arbitrary();
    vstd::modes::tracked_swap(r, &mut a);
    a
}

pub proof fn take_own(tracked r: &mut Sem::own) -> (tracked t: Sem::own)
    ensures t == *old(r),
{
    let tracked mut a = Sem::own::arbitrary();
    vstd::modes::tracked_swap(r, &mut a);
    a
}

pub struct AllocPred;

impl InvariantPredicate<InstanceId, Sem::next_id> for AllocPred {
    open spec fn inv(k: InstanceId, t: Sem::next_id) -> bool {
        t.instance_id() == k
    }
}

pub open spec fn ALLOC_NS() -> int { 77 }

/// Where the permits of `release(added)` come from.
pub tracked enum Source {
    /// permits previously obtained from this semaphore
    Held(Sem::held),
    /// brand-new permits (`Semaphore::add_permits`)
    Mint(Sem::budget),
    /// permits already held in the `op` token itself (a client's keyed token)
    Stashed,
}

// ======================================================================
// batch_semaphore.rs (Tokio master fc0d151 + semaphore-close-fix.patch)
// Lines marked `// VERUS:` differ from the real source; see SEMAPHORE_PROOF.md.
// ======================================================================

pub struct AcquireError(());

pub enum TryAcquireError {
    Closed,
    NoPermits,
}

struct_with_invariants!{
    pub struct Waiter {
        pub state: AtomicUsize<_, Sem::ws, _>,
        pub waker: WakerCell,
        // VERUS: `pointers: linked_list::Pointers<Waiter>` is replaced by the trusted list; ghost fields added
        pub inst: Tracked<Sem::Instance>,
        pub id: Ghost<nat>,
    }

    pub open spec fn wf(&self) -> bool {
        invariant on state with (inst, id) is (v: usize, g: Sem::ws) {
            &&& g.instance_id() == inst@.id()
            &&& g.key() == id@
            &&& g.value().state == v as nat
        }
    }
}

struct_with_invariants!{
    pub struct Semaphore {
        pub waiters: Mutex,
        pub permits: AtomicUsize<_, Sem::counter, _>,
        // VERUS: ghost fields
        pub inst: Tracked<Sem::Instance>,
        pub alloc: Tracked<AtomicInvariant<InstanceId, Sem::next_id, AllocPred>>,
    }

    pub open spec fn wf(&self) -> bool {
        predicate {
            &&& self.waiters.pred() == LockPred { inst_id: self.inst@.id() }
            &&& self.alloc@.constant() == self.inst@.id()
            &&& self.alloc@.namespace() == ALLOC_NS()
        }

        invariant on permits with (inst) is (v: usize, g: Sem::counter) {
            &&& g.instance_id() == inst@.id()
            &&& v as int == g.value().permits + g.value().permits + if g.value().closed { 1int } else { 0int }
        }
    }
}

pub struct Acquire<'a> {
    pub node: Arc<Waiter>, // VERUS: `node: Waiter` (pinned, intrusive)
    pub semaphore: &'a Semaphore,
    pub num_permits: usize,
    pub queued: bool,
    // VERUS: ghost fields
    pub own: Tracked<Sem::own>,
    pub fl: Tracked<Sem::fl>,
    pub nt: Tracked<Sem::nums>,
}

impl<'a> Acquire<'a> {
    pub open spec fn id(&self) -> nat { self.node.id@ }

    pub open spec fn wf(&self) -> bool {
        let iid = self.semaphore.inst@.id();
        &&& self.semaphore.wf()
        &&& self.node.wf()
        &&& self.node.inst@.id() == iid
        &&& self.own@.instance_id() == iid && self.own@.key() == self.id()
        &&& self.fl@.instance_id() == iid && self.fl@.key() == Key::W(self.id()) && self.fl@.value() == 0
        &&& self.nt@.instance_id() == iid && self.nt@.key() == self.id() && self.nt@.value() == self.num_permits as nat
        &&& self.num_permits <= MAXP()
        &&& self.queued == (self.own@.value() == Own::Fast || self.own@.value() == Own::Reg)
    }
}

impl Semaphore {
    pub const MAX_PERMITS: usize = usize::MAX >> 3;
    pub const CLOSED: usize = 1;
    pub const PERMIT_SHIFT: usize = 1;

    pub fn new(permits: usize, Ghost(closable): Ghost<bool>) -> (r: (Self, Tracked<Sem::budget>))
        requires permits <= MAXP(),
        ensures r.0.wf(), r.1@.instance_id() == r.0.inst@.id(), r.1@.count() == MAXP() - permits,
            r.0.inst@.closable() == closable,
    {
        proof { lemma_max(); }
        runtime_assert(permits <= Self::MAX_PERMITS);
        let tracked (Tracked(inst), Tracked(counter), Tracked(lk), Tracked(_ws), Tracked(_own), Tracked(_nums),
            Tracked(_fl), Tracked(_held), Tracked(budget), Tracked(next_id)) = Sem::Instance::initialize(permits as nat, closable);
        proof { lemma_shl1(permits); }
        let w = Waitlist { queue: LinkedList::new(), closed: false }; // VERUS: `Mutex::new(Waitlist {..})` built in steps: the Waitlist, then a vstd RwLock holding it with the ghost token
        let ghost pred = LockPred { inst_id: inst.id() };
        proof { assert(ids(w.queue@) =~= Seq::<nat>::empty()); }
        let rw = RwLock::new(LockVal { w, tok: Tracked(lk) }, Ghost(pred)); // VERUS: (see above)
        let tracked alloc = AtomicInvariant::new(inst.id(), next_id, ALLOC_NS());
        let tracked_inst = Tracked(inst.clone());
        let s = Self { // VERUS: `Self { .. }` bound to `s` so the ghost budget token can be returned alongside
            permits: AtomicUsize::new(Ghost(tracked_inst), permits << Self::PERMIT_SHIFT, Tracked(counter)),
            waiters: Mutex { rw }, // VERUS: `Mutex::new(..)`: vstd RwLock wrapper (see above)
            inst: Tracked(inst),
            alloc: Tracked(alloc),
        };
        (s, Tracked(budget)) // VERUS: returns the semaphore with the ghost budget token
    }

    pub fn available_permits(&self) -> usize
        requires self.wf(),
    {
        let v = atomic_with_ghost!(&self.permits => load(); ghost g => {});
        v >> Self::PERMIT_SHIFT
    }

    /// VERUS: ghost-only helper: a fresh operation id (no runtime code).
    pub fn new_op(&self) -> (r: Tracked<Sem::fl>)
        requires self.wf(),
        ensures r@.instance_id() == self.inst@.id(), r@.key() is O, r@.value() == 0,
    {
        let tracked mut t;
        open_atomic_invariant!(self.alloc.borrow() => nid => {
            proof { t = self.inst.borrow().new_op(&mut nid); }
        });
        Tracked(t)
    }

    pub fn release(&self, added: usize, Tracked(op): Tracked<&mut Sem::fl>, Tracked(src): Tracked<Source>)
        requires
            self.wf(),
            old(op).instance_id() == self.inst@.id(), old(op).key() is O,
            match src {
                Source::Held(h) => h.instance_id() == self.inst@.id() && h.count() == added && old(op).value() == 0,
                Source::Mint(b) => b.instance_id() == self.inst@.id() && b.count() == added && old(op).value() == 0,
                Source::Stashed => old(op).value() == added,
            },
        ensures
            op.instance_id() == old(op).instance_id(), op.key() == old(op).key(), op.value() == 0,
    {
        if added == 0 {
            return;
        }
        // Assign permits to the wait queue
        let (g, Tracked(lk)) = self.waiters.lock();
        proof {
            let tracked f = take_fl(op);
            let tracked f2 = match src {
                Source::Held(h) => self.inst.borrow().begin_release(f.key()->O_0, added as nat, f, h),
                Source::Mint(b) => self.inst.borrow().mint(f.key()->O_0, added as nat, f, b),
                Source::Stashed => f,
            };
            *op = f2;
        }
        self.add_permits_locked(added, g, Tracked(lk), Tracked(op)); // VERUS: `self.add_permits_locked(added, self.waiters.lock())` with the guard bound above
    }

    #[verifier::loop_isolation(false)]
    pub fn close(&self)
        requires self.wf(), self.inst@.closable(),
    {
        let (mut waiters, Tracked(mut lk)) = self.waiters.lock();
        atomic_with_ghost!(&self.permits => fetch_or(Self::CLOSED);
            update prev -> next;
            ghost g => {
                lemma_or1(prev);
                lemma_word(prev);
                lemma_word(next);
                self.inst.borrow().close_bit(&mut g, &mut lk);
            });
        waiters.w.closed = true;

        let mut wakers = WakeList::new();
        loop
            invariant
                self.wf(),
                waiters.h.rwlock() == self.waiters.rw,
                wl_inv(self.inst@.id(), &waiters.w, lk),
                !lk.value().popping,
        {
            // VERUS: `while wakers.can_push() { let Some(..) else { break } }` written as `loop { if !can_push { break } match .. }`
            loop
                invariant
                    self.wf(),
                    waiters.h.rwlock() == self.waiters.rw,
                    wl_inv(self.inst@.id(), &waiters.w, lk),
                    !lk.value().popping,
            {
                if !wakers.can_push() { // VERUS: (see above)
                    break;
                }
                // VERUS: `let Some(mut waiter) = .. else { break; }` written as a match
                let waiter = match waiters.w.queue.pop_back() {
                    Some(w) => w,
                    None => break,
                };
                proof {
                    self.inst.borrow().pop(&mut lk);
                    assert(ids(waiters.w.queue@) =~= lk.value().queue);
                }
                let waker = waiter.waker.take(); // VERUS: `unsafe { waiter.as_mut().waker.with_mut(|waker| (*waker).take()) }` via trusted WakerCell::take
                if let Some(waker) = waker { // VERUS: `if let Some(waker) = <expr>` with <expr> bound above
                    wakers.push(waker);
                }
            }
            let is_empty = wakers.can_push();
            waiters.unlock(Tracked(lk)); // drop(waiters)
            wakers.wake_all();
            if is_empty {
                return;
            }
            let (w2, Tracked(lk2)) = self.waiters.lock();
            waiters = w2; // VERUS: `waiters = self.waiters.lock()` with the ghost token bound separately
            proof { lk = lk2; }
        }
    }

    pub fn is_closed(&self) -> bool
        requires self.wf(),
    {
        let v = atomic_with_ghost!(&self.permits => load(); ghost g => {});
        v & Self::CLOSED == Self::CLOSED
    }

    #[verifier::loop_isolation(false)]
    pub fn try_acquire(&self, num_permits: usize, Tracked(out): Tracked<&mut Option<Sem::held>>) -> (r: Result<(), TryAcquireError>)
        requires self.wf(), num_permits <= MAXP(), *old(out) is None,
        ensures
            r is Ok ==> (*out matches Some(h) && h.instance_id() == self.inst@.id() && h.count() == num_permits),
            r is Err ==> *out is None,
            r matches Err(TryAcquireError::Closed) ==> self.inst@.closable(),
    {
        proof { lemma_max(); }
        runtime_assert(num_permits <= Self::MAX_PERMITS);
        proof { lemma_shl1(num_permits); }
        let ghost orig = num_permits;
        let num_permits = num_permits << Self::PERMIT_SHIFT;
        let mut curr = atomic_with_ghost!(&self.permits => load(); ghost g => { self.inst.borrow().open_word(&g); });
        loop
            invariant self.wf(), *out is None, num_permits as int == 2 * (num_permits / 2), num_permits / 2 <= MAXP(), num_permits / 2 == orig,
                !self.inst@.closable() ==> curr % 2 == 0,
        {
            proof { lemma_word(curr); }
            // Has the semaphore closed?
            if curr & Self::CLOSED == Self::CLOSED {
                return Err(TryAcquireError::Closed);
            }
            // Are there enough permits remaining?
            if curr < num_permits {
                return Err(TryAcquireError::NoPermits);
            }
            let next = curr - num_permits;
            let res = atomic_with_ghost!(&self.permits => compare_exchange(curr, next);
                update prv -> nxt;
                returning res;
                ghost g => {
                    self.inst.borrow().open_word(&g);
                    if res is Ok {
                        let tracked h = self.inst.borrow().try_take((num_permits / 2) as nat, &mut g);
                        *out = Some(h);
                    }
                });
            match res {
                Ok(_) => {
                    return Ok(());
                },
                Err(actual) => curr = actual,
            }
        }
    }

    pub fn acquire(&self, num_permits: usize) -> (r: Acquire<'_>)
        requires self.wf(), num_permits <= MAXP(),
        ensures r.wf(), r.semaphore == self, r.num_permits == num_permits, r.own@.value() == Own::Idle,
    {
        Acquire::new(self, num_permits)
    }

    #[verifier::loop_isolation(false)]
    fn add_permits_locked(&self, rem: usize, waiters: MutexGuard<'_>, Tracked(lk): Tracked<Sem::lk>,
        Tracked(fl): Tracked<&mut Sem::fl>)
        requires
            self.wf(),
            waiters.h.rwlock() == self.waiters.rw,
            wl_inv(self.inst@.id(), &waiters.w, lk),
            !lk.value().popping,
            old(fl).instance_id() == self.inst@.id(),
            old(fl).value() == rem,
        ensures
            fl.instance_id() == old(fl).instance_id(), fl.key() == old(fl).key(), fl.value() == 0,
    {
        let mut rem = rem; // VERUS: `mut rem` parameter made a local (Verus has no `mut` parameters)
        let mut wakers = WakeList::new();
        // VERUS: `let mut lock = Some(waiters);` with the ghost token alongside
        let mut lock = Some(waiters);
        let tracked mut lkt = Some(lk);
        let mut is_empty = false;
        // VERUS: loop invariants added
        while rem > 0
            invariant
                self.wf(),
                lock.is_some() == lkt.is_some(),
                lock matches Some(g) ==> g.h.rwlock() == self.waiters.rw && wl_inv(self.inst@.id(), &g.w, lkt->0) && !lkt->0.value().popping,
                fl.instance_id() == self.inst@.id(), fl.key() == old(fl).key(), fl.value() == rem,
                is_empty ==> rem == 0,
        {
            // VERUS: `lock.take().unwrap_or_else(|| self.waiters.lock())` without a closure
            let (mut waiters, Tracked(mut lk)) = match lock.take() {
                Some(g) => (g, Tracked(lkt.tracked_take())), // VERUS: `lock.take().unwrap_or_else(|| self.waiters.lock())` written as a match
                None => self.waiters.lock(), // VERUS: (see above)
            };
            // VERUS: `'inner: while wakers.can_push()` written as `loop { if !can_push { break } .. }`
            'inner: loop
                invariant
                    self.wf(),
                    waiters.h.rwlock() == self.waiters.rw,
                    wl_inv(self.inst@.id(), &waiters.w, lk),
                    !lk.value().popping,
                    fl.instance_id() == self.inst@.id(), fl.key() == old(fl).key(), fl.value() == rem,
                    is_empty ==> waiters.w.queue@.len() == 0,
                    lock is None,
            {
                if !wakers.can_push() { // VERUS: (see above)
                    break; // VERUS: (see above)
                }
                // Was the waiter assigned enough permits to wake it?
                let _assigned = match waiters.w.queue.last() {
                    Some(waiter) => {
                        proof {
                            let i = waiters.w.queue@.len() - 1;
                            assert(waiters.w.queue@[i].wf());
                            assert(ids(waiters.w.queue@)[i] == waiter.id@);
                        }
                        let tracked mut dummy = Sem::own::arbitrary();
                        let (should_remove, assigned) = waiter.assign_permits(&mut rem, Ghost(false),
                            Tracked(&mut lk), Tracked(&mut *fl), Tracked(&mut dummy), Tracked(self.inst.borrow()));
                        if !should_remove {
                            break 'inner;
                        }
                        assigned
                    },
                    None => {
                        is_empty = true;
                        // If we assigned permits to all the waiters in the queue, and there are
                        // still permits left over, assign them back to the semaphore.
                        break 'inner;
                    },
                };
                let waiter = waiters.w.queue.pop_back().unwrap(); // VERUS: `let mut waiter` (no `as_mut()` on Arc)
                proof {
                    self.inst.borrow().pop(&mut lk);
                    assert(ids(waiters.w.queue@) =~= lk.value().queue);
                }
                let waker = waiter.waker.take(); // VERUS: `unsafe { waiter.as_mut().waker.with_mut(|waker| (*waker).take()) }` via trusted WakerCell::take
                if let Some(waker) = waker { // VERUS: `if let Some(waker) = <expr>` with <expr> bound above
                    wakers.push(waker);
                }
            }

            if rem > 0 && is_empty {
                let permits = rem;
                proof { lemma_max(); self.inst.borrow().fl_bound(fl.key(), &*fl); }
                runtime_assert(permits <= Self::MAX_PERMITS);
                let tracked mut tf = take_fl(fl);
                let prev = atomic_with_ghost!(&self.permits => fetch_add(rem << Self::PERMIT_SHIFT);
                    update prev -> next;
                    ghost g => {
                        self.inst.borrow().counter_bound(tf.key(), &g, &tf);
                        lemma_shl1(rem);
                        tf = self.inst.borrow().release_rest(tf.key(), rem as nat, &mut g, &mut lk, tf);
                    });
                proof { *fl = tf; lemma_word(prev); }
                let prev = prev >> Self::PERMIT_SHIFT;
                runtime_assert(prev + permits <= Self::MAX_PERMITS);
                rem = 0;
            }

            waiters.unlock(Tracked(lk)); // drop(waiters); // release the lock
            wakers.wake_all();
        }
        // VERUS: Rust drops an unused `lock` here
        if let Some(g) = lock {
            g.unlock(Tracked(lkt.tracked_unwrap()));
        }
        runtime_assert(rem == 0);
    }

    #[verifier::loop_isolation(false)]
    pub fn forget_permits(&self, n: usize) -> (r: usize)
        requires self.wf(),
        ensures r <= n,
    {
        if n == 0 {
            return 0;
        }
        let mut curr_bits = atomic_with_ghost!(&self.permits => load(); ghost g => {});
        loop
            invariant self.wf(),
        {
            proof { lemma_word(curr_bits); }
            let curr = curr_bits >> Self::PERMIT_SHIFT;
            let new = curr.saturating_sub(n);
            proof { lemma_or_low(new, curr_bits); }
            let res = atomic_with_ghost!(&self.permits => compare_exchange_weak(curr_bits, (new << Self::PERMIT_SHIFT) | (curr_bits & Self::CLOSED));
                update prv -> nxt;
                returning res;
                ghost g => {
                    if res is Ok {
                        // the returned `min(curr, n)` is the amount removed from the ledger
                        assert(curr - new == if curr < n { curr } else { n });
                        self.inst.borrow().forget((curr - new) as nat, &mut g);
                    }
                });
            match res {
                Ok(_) => return min(curr, n), // VERUS: `std::cmp::min` via trusted `min`
                Err(actual) => curr_bits = actual,
            };
        }
    }

    fn poll_acquire(
        &self,
        cx: &mut Context<'_>,
        num_permits: usize,
        node: &Arc<Waiter>, // VERUS: `node: Pin<&mut Waiter>`
        queued: &mut bool,
        Tracked(own): Tracked<&mut Sem::own>,
        Tracked(fl): Tracked<&mut Sem::fl>,
        Tracked(nt): Tracked<&Sem::nums>,
    ) -> (ret: Poll<Result<(), AcquireError>>)
        requires
            self.wf(),
            node.wf(),
            node.inst@.id() == self.inst@.id(),
            old(own).instance_id() == self.inst@.id(), old(own).key() == node.id@,
            old(own).value() != Own::Done,
            old(fl).instance_id() == self.inst@.id(), old(fl).key() == Key::W(node.id@), old(fl).value() == 0,
            nt.instance_id() == self.inst@.id(), nt.key() == node.id@, nt.value() == num_permits as nat,
            num_permits <= MAXP(),
            *old(queued) == (old(own).value() == Own::Fast || old(own).value() == Own::Reg),
        ensures
            own.instance_id() == old(own).instance_id(), own.key() == old(own).key(),
            fl.instance_id() == old(fl).instance_id(), fl.key() == old(fl).key(), fl.value() == 0,
            own.value() != Own::Done,
            *queued == (own.value() == Own::Fast || own.value() == Own::Reg),
            ret matches Poll::Ready(Ok(_)) ==> own.value() == Own::Fast,
            ret matches Poll::Ready(Err(_)) ==> self.inst@.closable(),
    {
        let id = Ghost(node.id@);
        let mut acquired: usize = 0; // VERUS: `let mut acquired = 0;` with the type written out

        let needed = if *queued {
            let s = atomic_with_ghost!(&node.state => load();
                ghost g => { self.inst.borrow().ws_bound(id@, &g, nt); }); // VERUS: `node.state.load(Acquire) << Self::PERMIT_SHIFT` with the load bound to `s` (ghost step); `s` is used on the next line
            proof { lemma_shl1(s); }
            s << Self::PERMIT_SHIFT // VERUS: (see above)
        } else {
            proof { lemma_shl1(num_permits); }
            num_permits << Self::PERMIT_SHIFT
        };

        let mut lock: Option<MutexGuard<'_>> = None; // VERUS: `let mut lock = None;` with the type written out
        let tracked mut lkt: Option<Sem::lk> = None;
        let ghost mut blk = false;
        // First, try to take the requested number of permits from the
        // semaphore.
        let mut curr = atomic_with_ghost!(&self.permits => load(); ghost g => { self.inst.borrow().open_word(&g); });
        // VERUS: `let mut waiters = loop { .. break value .. }` written with an Option
        let mut out: Option<MutexGuard<'_>> = None;
        // VERUS: `let mut waiters = loop {` (break value via `out`)
        loop
            invariant_except_break
                acquired == 0,
                out is None,
                lock.is_some() == lkt.is_some(),
                lock matches Some(g) ==> g.h.rwlock() == self.waiters.rw && wl_inv(self.inst@.id(), &g.w, lkt->0) && !lkt->0.value().popping,
            invariant
                self.wf(), node.wf(), node.inst@.id() == self.inst@.id(), id@ == node.id@,
                old(own).key() == node.id@, old(own).instance_id() == self.inst@.id(),
                old(fl).key() == Key::W(node.id@), old(fl).instance_id() == self.inst@.id(),
                needed as int == 2 * (needed / 2), needed / 2 <= MAXP(),
                !*queued ==> needed / 2 == num_permits,
                own.instance_id() == self.inst@.id(), own.key() == id@, own.value() != Own::Done,
                own.value() == old(own).value(), *queued == *old(queued),
                *queued == (own.value() == Own::Fast || own.value() == Own::Reg),
                fl.instance_id() == self.inst@.id(), fl.key() == Key::W(id@), fl.value() == acquired,
                nt.instance_id() == self.inst@.id(), nt.key() == id@, nt.value() == num_permits as nat,
                blk ==> lkt is Some && lkt->0.value().blocked && !lkt->0.value().closed,
                !self.inst@.closable() ==> curr % 2 == 0,
            ensures
                out matches Some(g) && lkt matches Some(t) && g.h.rwlock() == self.waiters.rw && wl_inv(self.inst@.id(), &g.w, t) && !t.value().popping,
                fl.value() == acquired,
                own.value() == Own::Idle ==> blk,
                acquired <= MAXP(),
        {
            proof { lemma_word(curr); }
            // Has the semaphore closed?
            if curr & Self::CLOSED > 0 {
                // VERUS: Rust drops `lock` on return
                if let Some(g) = lock {
                    g.unlock(Tracked(lkt.tracked_unwrap()));
                }
                return Poll::Ready(Err(AcquireError(()))); // VERUS: `AcquireError::closed()` inlined as the constructor
            }

            let mut remaining = 0;
            let total = curr.checked_add(acquired).expect("number of permits must not overflow"); // VERUS: `curr.checked_add(acquired).expect(..)` on one line (rustfmt split it)
            let (next, acq) = if total >= needed {
                let next = curr - (needed - acquired);
                (next, needed >> Self::PERMIT_SHIFT)
            } else {
                remaining = (needed - acquired) - curr;
                (0, curr >> Self::PERMIT_SHIFT)
            };
            proof { lemma_word(needed); }

            if remaining > 0 && lock.is_none() {
                // No permits were immediately available, so this permit will
                // (probably) need to wait. We'll need to acquire a lock on the
                // wait queue before continuing. We need to do this _before_ the
                // CAS that sets the new value of the semaphore's `permits`
                // counter. Otherwise, if we subtract the permits and then
                // acquire the lock, we might miss additional permits being
                // added while waiting for the lock.
                let (g, Tracked(t)) = self.waiters.lock();
                lock = Some(g); // VERUS: `lock = Some(self.waiters.lock());` with the guard bound above
                proof { lkt = Some(t); }
            }

            let tracked mut tf = take_fl(fl);
            let res = atomic_with_ghost!(&self.permits => compare_exchange(curr, next);
                update prv -> nxt;
                returning res;
                ghost g => {
                    self.inst.borrow().open_word(&g);
                    if res is Ok {
                        if remaining > 0 {
                            let tracked mut t = lkt.tracked_take();
                            self.inst.borrow().closed_agree(&g, &t);
                            self.inst.borrow().counter_bound(tf.key(), &g, &tf);
                            tf = self.inst.borrow().take_block(tf.key(), acq as nat, &mut g, &mut t, tf);
                            lkt = Some(t);
                        } else {
                            tf = self.inst.borrow().take(tf.key(), acq as nat, &mut g, tf);
                        }
                    }
                });
            proof { *fl = tf; }
            match res {
                Ok(_) => {
                    acquired += acq;
                    if remaining == 0 {
                        if !*queued {
                            // The waiter now holds all of its permits. Record
                            // this in its state and set `queued`, so that
                            // `Acquire::drop` returns the permits if the
                            // future is dropped before it completes, e.g.
                            // because the tracing subscriber panics below.
                            let tracked mut tf = take_fl(fl);
                            let tracked mut to = take_own(own);
                            atomic_with_ghost!(&node.state => store(0);
                                update prev -> next;
                                ghost g => {
                                    self.inst.borrow().ws_bound(id@, &g, nt);
                                    let tracked (Tracked(w2), Tracked(o2), Tracked(f2)) = self.inst.borrow().fast_store(id@, g, to, tf);
                                    to = o2; g = w2; tf = f2;
                                });
                            proof { *fl = tf; *own = to; }
                            *queued = true;
                            // VERUS: Rust drops `lock` on return
                            if let Some(g) = lock {
                                g.unlock(Tracked(lkt.tracked_unwrap()));
                            }
                            return Poll::Ready(Ok(()));
                        } else if lock.is_none() {
                            let (g, Tracked(t)) = self.waiters.lock();
                            out = Some(g); // VERUS: `break self.waiters.lock();` via `out`
                            proof { lkt = Some(t); }
                            break; // VERUS: (see above)
                        }
                    }
                    out = Some(lock.expect("lock must be acquired before waiting")); // VERUS: `break lock.expect(..);` via `out`
                    proof { if remaining > 0 { blk = true; } }
                    break; // VERUS: (see above)
                },
                Err(actual) => curr = actual,
            }
        }
        let mut waiters = out.unwrap(); // VERUS: end of `let mut waiters = loop {..};` (break value via `out`)
        let tracked mut lk = lkt.tracked_unwrap();
        proof { self.inst.borrow().open_lk(&lk); }

        if waiters.w.closed {
            if acquired > 0 {
                let tracked mut tf = take_fl(fl);
                atomic_with_ghost!(&self.permits => fetch_add(acquired << Self::PERMIT_SHIFT);
                    update prev -> next;
                    ghost g => {
                        self.inst.borrow().counter_bound(tf.key(), &g, &tf);
                        lemma_shl1(acquired);
                        tf = self.inst.borrow().give_back(tf.key(), acquired as nat, &mut g, &lk, tf);
                    });
                proof { *fl = tf; }
            }
            waiters.unlock(Tracked(lk)); // VERUS: Rust drops `waiters` on return
            return Poll::Ready(Err(AcquireError(()))); // VERUS: `AcquireError::closed()` inlined as the constructor
        }

        // The waiter is about to be assigned permits or linked into the wait
        // queue, so `Acquire::drop` must clean up after it from now on.
        let was_queued = *queued;
        *queued = true;

        let (should_remove, _assigned) = node.assign_permits(&mut acquired, Ghost(true),
            Tracked(&mut lk), Tracked(&mut *fl), Tracked(&mut *own), Tracked(self.inst.borrow()));

        if should_remove {
            self.add_permits_locked(acquired, waiters, Tracked(lk), Tracked(fl));
            return Poll::Ready(Ok(()));
        }

        runtime_assert(acquired == 0); // assert_eq!(acquired, 0);

        // Otherwise, register the waker & enqueue the node.
        let old_waker = node.waker.register(cx); // VERUS: `node.waker.with_mut(|waker| { .. will_wake .. replace .. })` via trusted WakerCell::register

        // If the waiter is not already in the wait queue, enqueue it.
        if !was_queued {
            waiters.w.queue.push_front(node.clone()); // VERUS: `Pin::into_inner_unchecked`/`NonNull` node replaced by `Arc` clone
            proof { assert(ids(waiters.w.queue@) =~= lk.value().queue); }
        }
        waiters.unlock(Tracked(lk)); // drop(waiters);
        drop(old_waker);

        Poll::Pending
    }
}

impl Waiter {
    fn new(num_permits: usize, Tracked(inst): Tracked<Sem::Instance>, Ghost(id): Ghost<nat>,
        Tracked(ws): Tracked<Sem::ws>) -> (r: Self)
        requires ws.instance_id() == inst.id(), ws.key() == id, ws.value().state == num_permits as nat,
        ensures r.wf(), r.inst@ == inst, r.id@ == id,
    {
        let tracked_inst = Tracked(inst);
        Waiter {
            waker: WakerCell::new(), // VERUS: `UnsafeCell::new(None)` via trusted WakerCell; `pointers` and `_p: PhantomPinned` removed
            state: AtomicUsize::new(Ghost((tracked_inst, Ghost(id))), num_permits, Tracked(ws)),
            inst: tracked_inst,
            id: Ghost(id),
        }
    }

    #[verifier::loop_isolation(false)]
    fn assign_permits(&self, n: &mut usize, Ghost(by_owner): Ghost<bool>,
        Tracked(lk): Tracked<&mut Sem::lk>, Tracked(fl): Tracked<&mut Sem::fl>,
        Tracked(own): Tracked<&mut Sem::own>, Tracked(inst): Tracked<&Sem::Instance>) -> (r: (bool, usize))
        requires
            self.wf(), self.inst@.id() == inst.id(),
            old(lk).instance_id() == inst.id(), !old(lk).value().popping,
            old(fl).instance_id() == inst.id(), old(fl).value() == *old(n),
            by_owner ==> {
                &&& old(own).instance_id() == inst.id() && old(own).key() == self.id@
                &&& old(fl).key() == Key::W(self.id@)
                &&& !old(lk).value().closed
                &&& (old(own).value() == Own::Idle ==> old(lk).value().blocked)
                &&& (old(own).value() == Own::Idle || old(own).value() == Own::Fast || old(own).value() == Own::Reg)
            },
            !by_owner ==> old(lk).value().queue.len() > 0 && old(lk).value().queue.last() == self.id@,
        ensures
            fl.instance_id() == old(fl).instance_id(), fl.key() == old(fl).key(), fl.value() == *n,
            *n == *old(n) - r.1,
            lk.instance_id() == old(lk).instance_id(),
            lk.value().closed == old(lk).value().closed,
            !r.0 ==> *n == 0,
            by_owner ==> {
                &&& own.instance_id() == old(own).instance_id() && own.key() == old(own).key()
                &&& (r.0 ==> own.value() == Own::Fast && lk.value().queue == old(lk).value().queue && !lk.value().popping)
                &&& (!r.0 ==> own.value() == Own::Reg && !lk.value().popping)
                &&& (!r.0 && old(own).value() == Own::Idle ==> lk.value().queue == Seq::empty().push(self.id@) + old(lk).value().queue)
                &&& (!(!r.0 && old(own).value() == Own::Idle) ==> lk.value().queue == old(lk).value().queue)
            },
            !by_owner ==> {
                &&& lk.value().queue == old(lk).value().queue
                &&& lk.value().popping == r.0
                &&& *own == *old(own)
            },
    {
        let mut curr = atomic_with_ghost!(&self.state => load(); ghost g => {});
        loop
            invariant
                self.wf(), self.inst@.id() == inst.id(),
                lk == old(lk), fl == old(fl), own == old(own), *n == *old(n),
        {
            let assign = min(curr, *n); // VERUS: `cmp::min` via trusted `min`
            let next = curr - assign;
            let tracked mut tf = take_fl(fl);
            let tracked mut to = take_own(own);
            let res = atomic_with_ghost!(&self.state => compare_exchange(curr, next);
                update prv -> nxt;
                returning res;
                ghost g => {
                    if res is Ok {
                        if !by_owner {
                            let tracked (Tracked(w2), Tracked(f2)) = inst.assign_q(tf.key(), assign as nat, lk, g, tf);
                            g = w2; tf = f2;
                        } else if to.value() == Own::Idle {
                            let tracked (Tracked(w2), Tracked(o2), Tracked(f2)) = inst.reg_assign(self.id@, assign as nat, lk, g, to, tf);
                            to = o2; g = w2; tf = f2;
                        } else if to.value() == Own::Reg {
                            let tracked (Tracked(w2), Tracked(o2), Tracked(f2)) = inst.assign_own(self.id@, assign as nat, lk, g, to, tf);
                            to = o2; g = w2; tf = f2;
                        } else {
                            inst.fast_zero(self.id@, &g, &to);
                        }
                    }
                });
            proof { *fl = tf; *own = to; }
            match res {
                Ok(_) => {
                    *n -= assign;
                    return (next == 0, assign);
                },
                Err(actual) => curr = actual,
            }
        }
    }
}

impl<'a> Acquire<'a> {
    pub fn poll(&mut self, cx: &mut Context<'_>, Tracked(out): Tracked<&mut Option<Sem::held>>) -> (ret: Poll<Result<(), AcquireError>>)
        requires
            old(self).wf(), old(self).own@.value() != Own::Done, *old(out) is None,
        ensures
            self.wf(), self.id() == old(self).id(), self.semaphore == old(self).semaphore,
            self.num_permits == old(self).num_permits,
            ret matches Poll::Ready(Ok(_)) ==> {
                &&& self.own@.value() == Own::Done
                &&& *out matches Some(h) && h.instance_id() == self.semaphore.inst@.id() && h.count() == self.num_permits
            },
            !(ret matches Poll::Ready(Ok(_))) ==> self.own@.value() != Own::Done && *out is None,
            ret matches Poll::Ready(Err(_)) ==> self.semaphore.inst@.closable(),
    {
        // ready!(crate::trace::trace_leaf(cx));   VERUS: taskdump-only, returns Ready

        // VERUS: `let (node, semaphore, needed, queued) = self.project();` inlined as field accesses
        let result = match self.semaphore.poll_acquire(cx, self.num_permits, &self.node, &mut self.queued,
            Tracked(self.own.borrow_mut()), Tracked(self.fl.borrow_mut()), Tracked(self.nt.borrow())) {
            Poll::Pending => Poll::Pending,
            Poll::Ready(r) => {
                // VERUS: `r?;`
                match r {
                    Ok(()) => {},
                    Err(e) => return Poll::Ready(Err(e)),
                }
                // VERUS: `ready!(..)` expanded
                let coop = match poll_proceed(cx) {
                    Poll::Ready(c) => c,
                    Poll::Pending => return Poll::Pending,
                };
                coop.made_progress();
                Poll::Ready(Ok(()))
            },
        };

        // The permits are handed to the caller once the future completes, so
        // `Acquire::drop` must no longer return them. Clear `queued` only after
        // the last tracing event, so that the permits are still returned if
        // the subscriber panics.
        if result.is_ready() {
            self.queued = false; // VERUS: `*queued = false` with `project()` inlined
            proof {
                let tracked to = take_own(self.own.borrow_mut());
                let tracked (Tracked(o2), Tracked(h)) = self.semaphore.inst.borrow().complete(self.node.id@, to, self.nt.borrow());
                *self.own.borrow_mut() = o2;
                *out = Some(h);
            }
        }

        result
    }

    fn new(semaphore: &'a Semaphore, num_permits: usize) -> (r: Self)
        requires semaphore.wf(), num_permits <= MAXP(),
        ensures r.wf(), r.semaphore == semaphore, r.num_permits == num_permits, r.own@.value() == Own::Idle,
    {
        proof { lemma_max(); }
        runtime_assert(num_permits <= Semaphore::MAX_PERMITS);
        let tracked mut own;
        let tracked mut ws;
        let tracked mut nt;
        let tracked mut fl;
        let ghost mut id: nat;
        open_atomic_invariant!(semaphore.alloc.borrow() => nid => {
            proof {
                id = nid.value();
                let tracked (Tracked(w), Tracked(o), Tracked(n), Tracked(f)) = semaphore.inst.borrow().new_waiter(num_permits as nat, &mut nid);
                own = o; ws = w; nt = n; fl = f;
            }
        });
        Acquire { // VERUS: `return Self { .. }` (the non-tracing cfg branch)
            node: Arc::new(Waiter::new(num_permits, Tracked(semaphore.inst.borrow().clone()), Ghost(id), Tracked(ws))), // VERUS: `Waiter::new(num_permits)` boxed in `Arc` (intrusive node replaced by Arc)
            semaphore,
            num_permits,
            queued: false,
            own: Tracked(own),
            fl: Tracked(fl),
            nt: Tracked(nt),
        }
    }

    /// `impl Drop for Acquire<'_>`. VERUS: verified as a method; Rust calls it once when the future is dropped.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures
            self.own@.instance_id() == old(self).own@.instance_id(), self.own@.key() == old(self).own@.key(),
            self.own@.value() == Own::Done,
            self.fl@.instance_id() == old(self).fl@.instance_id(), self.fl@.key() == old(self).fl@.key(),
            self.fl@.value() == 0,
    {
        // If the future is completed, there is no node in the wait list, so we
        // can skip acquiring the lock.
        if !self.queued {
            proof {
                if self.own@.value() == Own::Idle {
                    let tracked to = take_own(self.own.borrow_mut());
                    *self.own.borrow_mut() = self.semaphore.inst.borrow().retire_idle(self.node.id@, to);
                }
            }
            return;
        }

        // This is where we ensure safety. The future is being dropped,
        // which means we must ensure that the waiter entry is no longer stored
        // in the linked list.
        let (mut waiters, Tracked(mut lk)) = self.semaphore.waiters.lock();

        // remove the entry from the list
        let ghost oldq = waiters.w.queue@;
        proof { self.semaphore.inst.borrow().q_nodup(&lk); }
        let removed = waiters.w.queue.remove(&self.node); // VERUS: `unsafe { waiters.queue.remove(NonNull::from(&mut self.node)) }` on the trusted list
        proof {
            if lk.value().queue.contains(self.node.id@) {
                let i = lk.value().queue.index_of(self.node.id@);
                lemma_ids_remove(oldq, i);
                lemma_remove_nodup(lk.value().queue, i);
                self.semaphore.inst.borrow().unlink(i, &mut lk);
            }
            assert(ids(waiters.w.queue@) =~= lk.value().queue);
            assert forall|j: int| 0 <= j < waiters.w.queue@.len() implies
                (#[trigger] waiters.w.queue@[j]).wf() && waiters.w.queue@[j].inst@.id() == self.semaphore.inst@.id() by {
                if lk.value().queue.len() < oldq.len() {
                    let i = ids(oldq).index_of(self.node.id@);
                    assert(waiters.w.queue@[j] == oldq[if j < i { j } else { j + 1 }]);
                }
            }
        }

        let tracked mut to = take_own(self.own.borrow_mut());
        let tracked mut tf = take_fl(self.fl.borrow_mut());
        let st = atomic_with_ghost!(&self.node.state => load();
            ghost g => {
                self.semaphore.inst.borrow().ws_bound(self.node.id@, &g, self.nt.borrow());
                let tracked (Tracked(o2), Tracked(f2)) = self.semaphore.inst.borrow().retire(self.node.id@, &mut lk, &g, to, tf);
                to = o2; tf = f2;
            }); // VERUS: `self.node.state.load(Acquire)` bound to `st` (ghost step)
        let acquired_permits = self.num_permits - st; // VERUS: (see above)
        proof { *self.own.borrow_mut() = to; }
        if acquired_permits > 0 {
            self.semaphore.add_permits_locked(acquired_permits, waiters, Tracked(lk), Tracked(&mut tf));
        } else { // VERUS: guard drop made explicit: Rust drops `waiters` when `acquired_permits == 0`
            waiters.unlock(Tracked(lk)); // VERUS: Rust drops `waiters`
        }
        proof { *self.fl.borrow_mut() = tf; }
    }
}

} // verus!
