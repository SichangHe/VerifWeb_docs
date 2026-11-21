#![allow(unused_imports, dead_code, non_snake_case, unused_variables, unused_mut, unreachable_code)]
#![cfg_attr(verus_keep_ghost, verifier::exec_allows_no_decreases_clause)]
//! Tokio's clients of the batch semaphore (master fc0d151 + semaphore-close-fix.patch):
//! `Semaphore`/`SemaphorePermit`/`OwnedSemaphorePermit` (semaphore.rs), `Mutex` and its
//! guards (mutex.rs), `RwLock` and its guards (rwlock.rs, rwlock/*.rs), and bounded `mpsc`
//! (mpsc/bounded.rs, mpsc/chan.rs). Lines marked `// VERUS:` differ from the real source;
//! see CLIENTS_PROOF.md.
pub mod batch_semaphore;

// ======================================================================
// Ghost helpers shared by the clients (no runtime code).
// ======================================================================
pub mod common {
use std::task::{Context, Poll};
use vstd::prelude::*;
use crate::batch_semaphore as ll;
use vstd::tokens::*;

verus! {

/// `t` is a client's keyed token on semaphore `sem` that holds exactly `n` permits.
pub open spec fn holds(t: ll::Sem::fl, sem: &ll::Semaphore, n: nat) -> bool {
    &&& t.instance_id() == sem.inst@.id()
    &&& t.key() is O
    &&& t.value() == n
}

/// A finite map whose values are all 0 sums to 0.
pub proof fn lemma_msum_zero<K>(m: Map<K, nat>)
    requires m.dom().finite(), forall|k: K| m.dom().contains(k) ==> m[k] == 0,
    ensures ll::msum(m) == 0,
    decreases m.dom().len(),
{
    if m.dom().len() > 0 {
        let k = m.dom().choose();
        ll::lemma_msum_remove(m, k);
        lemma_msum_zero(m.remove(k));
    }
}

/// The Verus-checked step of the bounded-`mpsc` corollary, over the ledger state `s` of a
/// channel's semaphore (`bounded::Semaphore::wf`: `fixed`, `initial == bound`). Premises,
/// one per kind of token: the channel's list token (key `list_key`, `ListTx::key`; its
/// value is the number of messages in the list, `ListPred`) is 0; every other keyed token
/// (`Permit`s, running calls' locals) is 0; no queued future is owed permits; no `held`
/// permits are outstanding. Conclusion: the counter, which `is_idle` compares, equals `bound`.
pub proof fn lemma_channel_drained_is_idle(s: ll::Sem::State, list_key: nat, bound: nat)
    requires
        s.invariant(),
        s.fixed, s.initial == bound,
        s.fl.dom().contains(ll::Key::O(list_key)), s.fl[ll::Key::O(list_key)] == 0,
        forall|k: ll::Key| #[trigger] s.fl.dom().contains(k) && k != ll::Key::O(list_key) ==> s.fl[k] == 0,
        forall|id: nat| #[trigger] s.own.dom().contains(id) ==> ll::contrib(s.own[id], s.ws[id]) == 0,
        s.held == 0,
    ensures s.counter.permits == bound,
{
    ll::lemma_cmap_finite(s.own, s.ws);
    assert forall|k: ll::Key| s.fl.dom().contains(k) implies s.fl[k] == 0 by {
        if k == ll::Key::O(list_key) {} else {}
    }
    lemma_msum_zero(s.fl);
    lemma_msum_zero(ll::cmap(s.own, s.ws));
}

/// Ghost-only (no runtime code): a fresh keyed token holding the permits of `h`.
pub fn stash(sem: &ll::Semaphore, Tracked(h): Tracked<ll::Sem::held>) -> (r: Tracked<ll::Sem::fl>)
    requires sem.wf(), h.instance_id() == sem.inst@.id(),
    ensures holds(r@, sem, h.count()),
{
    let Tracked(t) = sem.new_op();
    let tracked t2 = sem.inst.borrow().begin_release(t.key()->O_0, h.count(), t, h);
    Tracked(t2)
}

/// Ghost-only: move `k` permits from keyed token `from` to keyed token `to`.
pub proof fn move_permits(tracked inst: &ll::Sem::Instance, tracked from: &mut ll::Sem::fl, tracked to: &mut ll::Sem::fl, k: nat)
    requires
        old(from).instance_id() == inst.id(), old(to).instance_id() == inst.id(),
        old(from).key() is O, old(to).key() is O,
        k <= old(from).value(),
    ensures
        from.instance_id() == inst.id(), from.key() == old(from).key(), from.value() == old(from).value() - k,
        to.instance_id() == inst.id(), to.key() == old(to).key(), to.value() == old(to).value() + k,
{
    from.unique(&*to);
    let tracked f = ll::take_fl(from);
    let tracked t = ll::take_fl(to);
    let fk = f.key(); let tk = t.key(); let a = f.value(); let b = t.value();
    let tracked mut m = vstd::tokens::MapToken::<ll::Key, nat, ll::Sem::fl>::empty(inst.id());
    m.insert(f);
    m.insert(t);
    assert(m.map() =~= Map::empty().insert(fk, a).insert(tk, b));
    let tracked mut m2 = inst.transfer(fk, tk, a, b, k, m);
    assert(m2.dom().contains(fk) && m2.dom().contains(tk));
    let tracked f2 = m2.remove(fk);
    let tracked t2 = m2.remove(tk);
    *from = f2;
    *to = t2;
}

/// `assert!(cond, ..)` on a caller's input: panics iff `cond` is false (trusted; unwinding is out of scope).
#[verifier::external_body]
pub fn check(b: bool)
    ensures b,
{
    assert!(b);
}

/// `unreachable!()`: Verus must prove that the call is never reached.
#[verifier::external_body]
pub fn unreachable_()
    requires false,
{
    unreachable!()
}

/// `debug_assert!(..)` whose condition the proof does not establish (trusted: no effect on permits).
#[verifier::external_body]
pub fn debug_assert_unproved(b: bool) {
    debug_assert!(b);
}

pub assume_specification<T>[ std::mem::forget::<T> ](_0: T);

} // verus!
}

// ======================================================================
// semaphore.rs
// ======================================================================
pub mod semaphore {
use std::sync::Arc;
use std::task::{Context, Poll};
use vstd::prelude::*;
use crate::batch_semaphore as ll; // low level implementation
use crate::batch_semaphore::{AcquireError, TryAcquireError};
use crate::common::*;

verus! {

pub struct Semaphore {
    pub ll_sem: ll::Semaphore,
}

pub struct SemaphorePermit<'a> {
    pub sem: &'a Semaphore,
    pub permits: usize,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}

pub struct OwnedSemaphorePermit {
    pub sem: Arc<Semaphore>,
    pub permits: usize,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}

impl Semaphore {
    pub open spec fn wf(&self) -> bool {
        self.ll_sem.wf() && self.ll_sem.inst@.closable() && !self.ll_sem.inst@.fixed()
    }
}

impl<'a> SemaphorePermit<'a> {
    pub open spec fn wf(&self) -> bool {
        self.sem.wf() && holds(self.tok@, &self.sem.ll_sem, self.permits as nat)
    }
}

impl OwnedSemaphorePermit {
    pub open spec fn wf(&self) -> bool {
        self.sem.wf() && holds(self.tok@, &self.sem.ll_sem, self.permits as nat)
    }
}

/// The future of `Semaphore::acquire_many` (`async fn`), written out by hand.
/// `inner` is the `.await`ed `ll::Acquire`; `done` is the returned state.
pub struct AcquireManyFuture<'a> {
    pub this: &'a Semaphore,
    pub n: u32,
    pub inner: Option<ll::Acquire<'a>>,
    pub done: bool,
}

impl<'a> AcquireManyFuture<'a> {
    pub open spec fn wf(&self) -> bool {
        &&& self.this.wf()
        &&& self.inner matches Some(a) ==> {
            &&& a.wf() && a.semaphore == &self.this.ll_sem && a.num_permits == self.n as usize
            &&& a.own@.value() != ll::Own::Done
        }
        &&& self.done ==> self.inner is None
    }
}

impl Semaphore {
    pub fn new(permits: usize) -> (r: (Self, Tracked<ll::Sem::budget>))
        requires permits <= ll::MAXP(),
        ensures r.0.wf(), r.1@.instance_id() == r.0.ll_sem.inst@.id(),
    {
        let (ll_sem, budget) = ll::Semaphore::new(permits, Ghost(true), Ghost(false)); // VERUS: `let ll_sem = ll::Semaphore::new(permits);` also returns the ghost budget; `close` may be called
        (Self { // VERUS: `Self {` returned with the ghost budget token alongside
            ll_sem,
        }, budget) // VERUS: (see above)
    }

    pub fn available_permits(&self) -> usize
        requires self.wf(),
    {
        self.ll_sem.available_permits()
    }

    /// `src` says where the permits come from: new permits (`Source::Mint`, the
    /// public use) or permits held by a `SemaphorePermit` (`Source::Stashed`, from its drop).
    pub fn add_permits(&self, n: usize, Tracked(op): Tracked<&mut ll::Sem::fl>, Tracked(src): Tracked<ll::Source>)
        requires
            self.wf(),
            old(op).instance_id() == self.ll_sem.inst@.id(), old(op).key() is O,
            match src {
                ll::Source::Held(h) => h.instance_id() == self.ll_sem.inst@.id() && h.count() == n && old(op).value() == 0,
                ll::Source::Mint(b) => b.instance_id() == self.ll_sem.inst@.id() && b.count() == n && old(op).value() == 0,
                ll::Source::Stashed => old(op).value() == n,
            },
        ensures
            op.instance_id() == old(op).instance_id(), op.key() == old(op).key(), op.value() == 0,
    {
        self.ll_sem.release(n, Tracked(op), Tracked(src));
    }

    pub fn forget_permits(&self, n: usize) -> (r: usize)
        requires self.wf(),
        ensures r <= n,
    {
        self.ll_sem.forget_permits(n)
    }

    /// VERUS: `async fn acquire_many(&self, n: u32)` returns its future; the body is in `AcquireManyFuture::poll`.
    pub fn acquire_many<'a>(&'a self, n: u32) -> (r: AcquireManyFuture<'a>)
        requires self.wf(),
        ensures r.wf(), !r.done, r.this == self, r.n == n,
    {
        AcquireManyFuture { this: self, n, inner: None, done: false }
    }

    pub fn try_acquire_many(&self, n: u32) -> (r: Result<SemaphorePermit<'_>, TryAcquireError>)
        requires self.wf(),
        ensures r matches Ok(p) ==> p.wf() && p.sem == self && p.permits == n as usize,
    {
        let tracked mut out = None;
        match self.ll_sem.try_acquire(n as usize, Tracked(&mut out)) {
            Ok(()) => Ok(SemaphorePermit {
                sem: self,
                permits: n as usize,
                tok: stash(&self.ll_sem, Tracked(out.tracked_unwrap())), // VERUS: ghost field
            }),
            Err(e) => Err(e),
        }
    }

    pub fn try_acquire_many_owned(self: Arc<Self>, n: u32) -> (r: Result<OwnedSemaphorePermit, TryAcquireError>)
        requires self.wf(),
        ensures r matches Ok(p) ==> p.wf() && p.sem == self && p.permits == n as usize,
    {
        let tracked mut out = None;
        match self.ll_sem.try_acquire(n as usize, Tracked(&mut out)) {
            Ok(()) => { // VERUS: block added for the ghost `tok` (`self` is moved into the permit)
                let tok = stash(&self.ll_sem, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
                Ok(OwnedSemaphorePermit { // VERUS: (see above)
                sem: self,
                permits: n as usize,
                tok, // VERUS: ghost field
            })},
            Err(e) => Err(e),
        }
    }

    pub fn close(&self)
        requires self.wf(),
    {
        self.ll_sem.close();
    }

    pub fn is_closed(&self) -> bool
        requires self.wf(),
    {
        self.ll_sem.is_closed()
    }
}

impl<'a> AcquireManyFuture<'a> {
    /// `self.ll_sem.acquire(n as usize).await?; Ok(SemaphorePermit { sem: self, permits: n as usize })`
    pub fn poll(&mut self, cx: &mut Context<'_>) -> (ret: Poll<Result<SemaphorePermit<'a>, AcquireError>>)
        requires old(self).wf(), !old(self).done,
        ensures
            self.wf(), self.this == old(self).this, self.n == old(self).n,
            ret is Ready <==> self.done,
            ret matches Poll::Ready(Ok(p)) ==> p.wf() && p.sem == self.this && p.permits == self.n as usize,
    {
        // VERUS: the `.await` is written out: create the `Acquire` on the first poll, poll it,
        // keep it while `Pending`, and drop it when `Ready` (end of the `.await?` statement).
        if self.inner.is_none() {
            self.inner = Some(self.this.ll_sem.acquire(self.n as usize)); // VERUS: `self.ll_sem.acquire(n as usize)` (see above)
        }
        let mut inner = self.inner.take().unwrap(); // VERUS: (see above)
        let tracked mut out = None;
        match inner.poll(cx, Tracked(&mut out)) { // VERUS: (see above)
            Poll::Pending => {
                self.inner = Some(inner); // VERUS: (see above)
                Poll::Pending
            },
            Poll::Ready(r) => {
                inner.drop(); // VERUS: Rust drops the `Acquire` at the end of the `.await?` statement
                self.done = true; // VERUS: (see above)
                match r { // VERUS: `?`
                    Ok(()) => {},
                    Err(e) => return Poll::Ready(Err(e)),
                }
                let tok = stash(&self.this.ll_sem, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
                Poll::Ready(Ok(SemaphorePermit { // VERUS: `Ok(SemaphorePermit {` returned from the `async fn`
                    sem: self.this, // VERUS: `sem: self,`
                    permits: self.n as usize, // VERUS: `permits: n as usize,`
                    tok, // VERUS: ghost field
                }))
            },
        }
    }

    /// Drop glue of the `async fn` future: in the suspended state it drops the `Acquire`.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.inner is None,
    {
        // VERUS: compiler-generated drop of the suspended `async fn` state
        if self.inner.is_some() {
            let mut inner = self.inner.take().unwrap(); // VERUS: (see above)
            inner.drop(); // VERUS: (see above)
        }
    }
}

impl<'a> SemaphorePermit<'a> {
    pub fn forget(self)
        requires self.wf(),
    {
        let mut this = self; // VERUS: `mut self` made a local `this` (Verus has no `mut self`)
        proof { forget_permits_ghost(this.sem.ll_sem.inst.borrow(), this.tok.borrow_mut(), this.permits as nat); }
        this.permits = 0; // VERUS: `self.permits = 0;` on the local
        this.drop(); // VERUS: Rust drops `self` here
    }

    pub fn merge(&mut self, other: Self)
        requires old(self).wf(), other.wf(),
        ensures self.wf(), self.sem == old(self).sem, self.permits == old(self).permits + other.permits,
    {
        let mut other = other; // VERUS: `mut other` parameter made a local
        check(ptr_eq(self.sem, other.sem)); // VERUS: `assert!(std::ptr::eq(..), "merging permits from different semaphore instances")` via trusted `check`
        proof {
            self.sem.ll_sem.inst.borrow().fl_bound(self.tok@.key(), self.tok.borrow());
            self.sem.ll_sem.inst.borrow().fl_bound(other.tok@.key(), other.tok.borrow());
        }
        self.permits = self
            .permits
            .checked_add(other.permits)
            .expect("number of permits overflowed");
        proof { move_permits(self.sem.ll_sem.inst.borrow(), other.tok.borrow_mut(), self.tok.borrow_mut(), other.permits as nat); }
        other.permits = 0;
        other.drop(); // VERUS: Rust drops `other` here
    }

    pub fn split(&mut self, n: usize) -> (r: Option<Self>)
        requires old(self).wf(),
        ensures
            self.wf(), self.sem == old(self).sem,
            r matches Some(p) ==> p.wf() && p.sem == self.sem && p.permits == n && self.permits == old(self).permits - n,
            r is None ==> self.permits == old(self).permits,
    {
        if n > self.permits {
            return None;
        }

        self.permits = self.permits - n; // VERUS: `self.permits -= n;` (Verus has no compound assignment to a field)

        let Tracked(mut tok) = self.sem.ll_sem.new_op(); // VERUS: ghost-only (no runtime code)
        proof { move_permits(self.sem.ll_sem.inst.borrow(), self.tok.borrow_mut(), &mut tok, n as nat); }
        Some(Self {
            sem: self.sem,
            permits: n,
            tok: Tracked(tok), // VERUS: ghost field
        })
    }

    pub fn num_permits(&self) -> usize {
        self.permits
    }

    /// `impl Drop for SemaphorePermit<'_>`. VERUS: verified as a method; Rust calls it once when the permit is dropped.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        self.sem.add_permits(self.permits, Tracked(self.tok.borrow_mut()), Tracked(ll::Source::Stashed));
    }
}

impl OwnedSemaphorePermit {
    pub fn forget(self)
        requires self.wf(),
    {
        let mut this = self; // VERUS: `mut self` made a local `this` (Verus has no `mut self`)
        proof { forget_permits_ghost(this.sem.ll_sem.inst.borrow(), this.tok.borrow_mut(), this.permits as nat); }
        this.permits = 0; // VERUS: `self.permits = 0;` on the local
        this.drop(); // VERUS: Rust drops `self` here
    }

    pub fn merge(&mut self, other: Self)
        requires old(self).wf(), other.wf(),
        ensures self.wf(), self.sem == old(self).sem, self.permits == old(self).permits + other.permits,
    {
        let mut other = other; // VERUS: `mut other` parameter made a local
        check(arc_ptr_eq(&self.sem, &other.sem)); // VERUS: `assert!(Arc::ptr_eq(..), "merging permits from different semaphore instances")` via trusted `check`
        proof {
            self.sem.ll_sem.inst.borrow().fl_bound(self.tok@.key(), self.tok.borrow());
            self.sem.ll_sem.inst.borrow().fl_bound(other.tok@.key(), other.tok.borrow());
        }
        self.permits = self
            .permits
            .checked_add(other.permits)
            .expect("number of permits overflowed");
        proof { move_permits(self.sem.ll_sem.inst.borrow(), other.tok.borrow_mut(), self.tok.borrow_mut(), other.permits as nat); }
        other.permits = 0;
        other.drop(); // VERUS: Rust drops `other` here
    }

    pub fn split(&mut self, n: usize) -> (r: Option<Self>)
        requires old(self).wf(),
        ensures
            self.wf(), self.sem == old(self).sem,
            r matches Some(p) ==> p.wf() && p.sem == self.sem && p.permits == n && self.permits == old(self).permits - n,
            r is None ==> self.permits == old(self).permits,
    {
        if n > self.permits {
            return None;
        }

        self.permits = self.permits - n; // VERUS: `self.permits -= n;` (Verus has no compound assignment to a field)

        let Tracked(mut tok) = self.sem.ll_sem.new_op(); // VERUS: ghost-only (no runtime code)
        proof { move_permits(self.sem.ll_sem.inst.borrow(), self.tok.borrow_mut(), &mut tok, n as nat); }
        Some(Self {
            sem: self.sem.clone(),
            permits: n,
            tok: Tracked(tok), // VERUS: ghost field
        })
    }

    /// `impl Drop for OwnedSemaphorePermit`. VERUS: verified as a method (see `SemaphorePermit::drop`).
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        self.sem.add_permits(self.permits, Tracked(self.tok.borrow_mut()), Tracked(ll::Source::Stashed));
    }
}

/// `std::ptr::eq` (trusted): equal addresses mean the same semaphore.
#[verifier::external_body]
pub fn ptr_eq(a: &Semaphore, b: &Semaphore) -> (r: bool)
    ensures r ==> a == b,
{
    std::ptr::eq(a, b)
}

/// `Arc::ptr_eq` (trusted).
#[verifier::external_body]
pub fn arc_ptr_eq(a: &Arc<Semaphore>, b: &Arc<Semaphore>) -> (r: bool)
    ensures r ==> a == b,
{
    Arc::ptr_eq(a, b)
}

/// Ghost: `forget` takes the permits out of circulation (the semaphore's total drops by `k`).
pub proof fn forget_permits_ghost(tracked inst: &ll::Sem::Instance, tracked t: &mut ll::Sem::fl, k: nat)
    requires old(t).instance_id() == inst.id(), old(t).key() is O, old(t).value() == k, !inst.fixed(),
    ensures t.instance_id() == inst.id(), t.key() == old(t).key(), t.value() == 0,
{
    let tracked f = ll::take_fl(t);
    *t = inst.forget_held(f.key(), k, f);
}

} // verus!
}

// ======================================================================
// mutex.rs (the protected data `c: UnsafeCell<T>`, `Deref`, and the closures
// and data pointers of `map` are omitted: they do not touch permits)
// ======================================================================
pub mod mutex {
use std::sync::Arc;
use std::task::{Context, Poll};
use vstd::prelude::*;
use crate::batch_semaphore as semaphore;
use crate::common::*;

verus! {

pub struct Mutex {
    pub s: semaphore::Semaphore,
}

pub struct MutexGuard<'a> {
    pub lock: &'a Mutex,
    pub tok: Tracked<semaphore::Sem::fl>, // VERUS: ghost field
}

pub struct OwnedMutexGuard {
    pub lock: Arc<Mutex>,
    pub tok: Tracked<semaphore::Sem::fl>, // VERUS: ghost field
}

pub struct MappedMutexGuard<'a> {
    pub s: &'a semaphore::Semaphore,
    pub tok: Tracked<semaphore::Sem::fl>, // VERUS: ghost field
}

pub struct MutexGuardInner<'a> {
    pub lock: &'a Mutex,
    pub tok: Tracked<semaphore::Sem::fl>, // VERUS: ghost field
}

pub struct TryLockError(pub ());

impl Mutex {
    /// The semaphore was created with `close` disabled, and Mutex never closes it.
    pub open spec fn wf(&self) -> bool {
        self.s.wf() && !self.s.inst@.closable()
    }
}

impl<'a> MutexGuard<'a> {
    pub open spec fn wf(&self) -> bool { self.lock.wf() && holds(self.tok@, &self.lock.s, 1) }
}
impl OwnedMutexGuard {
    pub open spec fn wf(&self) -> bool { self.lock.wf() && holds(self.tok@, &self.lock.s, 1) }
}
impl<'a> MappedMutexGuard<'a> {
    pub open spec fn wf(&self) -> bool { self.s.wf() && holds(self.tok@, self.s, 1) }
}
impl<'a> MutexGuardInner<'a> {
    pub open spec fn wf(&self) -> bool { self.lock.wf() && holds(self.tok@, &self.lock.s, 1) }
}

/// The future of `Mutex::lock` (an `async fn` awaiting the `async` block that awaits
/// `Mutex::acquire`, an `async fn` awaiting `self.s.acquire(1)`), flattened by hand.
pub struct LockFuture<'a> {
    pub this: &'a Mutex,
    pub inner: Option<semaphore::Acquire<'a>>,
    pub done: bool,
}

impl<'a> LockFuture<'a> {
    pub open spec fn wf(&self) -> bool {
        &&& self.this.wf()
        &&& self.inner matches Some(a) ==> {
            &&& a.wf() && a.semaphore == &self.this.s && a.num_permits == 1
            &&& a.own@.value() != semaphore::Own::Done
        }
        &&& self.done ==> self.inner is None
    }
}

impl Mutex {
    pub fn new() -> (r: Self)
        ensures r.wf(),
    {
        let (s, _budget) = semaphore::Semaphore::new(1, Ghost(false), Ghost(false)); // VERUS: `let s = semaphore::Semaphore::new(1);`; the semaphore is created with `close` disabled; the ghost budget is dropped (Mutex never adds permits)

        Self {
            s,
        }
    }

    /// VERUS: `async fn lock(&self)` returns its future; the body is in `LockFuture::poll`.
    pub fn lock<'a>(&'a self) -> (r: LockFuture<'a>)
        requires self.wf(),
        ensures r.wf(), !r.done, r.this == self,
    {
        LockFuture { this: self, inner: None, done: false }
    }

    pub fn try_lock(&self) -> (r: Result<MutexGuard<'_>, TryLockError>)
        requires self.wf(),
        ensures r matches Ok(g) ==> g.wf() && g.lock == self,
    {
        let tracked mut out = None;
        match self.s.try_acquire(1, Tracked(&mut out)) {
            Ok(()) => {
                let tok = stash(&self.s, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
                let guard = MutexGuard {
                    lock: self,
                    tok, // VERUS: ghost field
                };

                Ok(guard)
            }
            Err(_) => Err(TryLockError(())),
        }
    }

    pub fn try_lock_owned(self: Arc<Self>) -> (r: Result<OwnedMutexGuard, TryLockError>)
        requires self.wf(),
        ensures r matches Ok(g) ==> g.wf() && g.lock == self,
    {
        let tracked mut out = None;
        match self.s.try_acquire(1, Tracked(&mut out)) {
            Ok(()) => {
                let tok = stash(&self.s, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
                let guard = OwnedMutexGuard {
                    lock: self,
                    tok, // VERUS: ghost field
                };

                Ok(guard)
            }
            Err(_) => Err(TryLockError(())),
        }
    }
}

impl<'a> LockFuture<'a> {
    pub fn poll(&mut self, cx: &mut Context<'_>) -> (ret: Poll<MutexGuard<'a>>)
        requires old(self).wf(), !old(self).done,
        ensures
            self.wf(), self.this == old(self).this,
            ret is Ready <==> self.done,
            ret matches Poll::Ready(g) ==> g.wf() && g.lock == self.this,
    {
        // VERUS: the `.await`s are written out as in `AcquireManyFuture::poll`
        if self.inner.is_none() {
            self.inner = Some(self.this.s.acquire(1)); // VERUS: `self.s.acquire(1)` (see above)
        }
        let mut inner = self.inner.take().unwrap(); // VERUS: (see above)
        let tracked mut out = None;
        match inner.poll(cx, Tracked(&mut out)) { // VERUS: (see above)
            Poll::Pending => {
                self.inner = Some(inner); // VERUS: (see above)
                Poll::Pending
            },
            Poll::Ready(r) => {
                inner.drop(); // VERUS: Rust drops the `Acquire` at the end of the statement
                self.done = true; // VERUS: (see above)
                match r { // VERUS: `.unwrap_or_else(|_| { unreachable!() })` written as a match
                    Ok(()) => {},
                    Err(_) => unreachable_(), // VERUS: `unreachable!()`; Verus proves it is not reached (the semaphore is never closed)
                }
                let tok = stash(&self.this.s, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
                Poll::Ready(MutexGuard { // VERUS: `MutexGuard {` returned from the `async` block
                    lock: self.this, // VERUS: `lock: self,`
                    tok, // VERUS: ghost field
                })
            },
        }
    }

    /// Drop glue of the suspended future: drops the `Acquire`.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.inner is None,
    {
        // VERUS: compiler-generated drop of the suspended `async` state
        if self.inner.is_some() {
            let mut inner = self.inner.take().unwrap(); // VERUS: (see above)
            inner.drop(); // VERUS: (see above)
        }
    }
}

impl<'a> MutexGuard<'a> {
    fn skip_drop(self) -> (r: MutexGuardInner<'a>)
        requires self.wf(),
        ensures r.wf(), r.lock == self.lock,
    {
        let me = self; // VERUS: `mem::ManuallyDrop::new(self)`: the guard's drop is not run (no call to `drop` follows)
        MutexGuardInner {
            lock: me.lock,
            tok: me.tok, // VERUS: ghost field
        }
    }

    /// VERUS: `map(this, f)` without the closure and data pointer.
    pub fn map(this: Self) -> (r: MappedMutexGuard<'a>)
        requires this.wf(),
        ensures r.wf(), r.s == &this.lock.s,
    {
        let inner = this.skip_drop();
        MappedMutexGuard {
            s: &inner.lock.s,
            tok: inner.tok, // VERUS: ghost field
        }
    }

    /// `impl Drop for MutexGuard<'_, T>`. VERUS: verified as a method; Rust calls it once when the guard is dropped.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        self.lock.s.release(1, Tracked(self.tok.borrow_mut()), Tracked(semaphore::Source::Stashed));
    }
}

impl OwnedMutexGuard {
    /// `impl Drop for OwnedMutexGuard<T>`. VERUS: verified as a method.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        self.lock.s.release(1, Tracked(self.tok.borrow_mut()), Tracked(semaphore::Source::Stashed));
    }
}

impl<'a> MappedMutexGuard<'a> {
    /// `impl Drop for MappedMutexGuard<'a, T>`. VERUS: verified as a method.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        self.s.release(1, Tracked(self.tok.borrow_mut()), Tracked(semaphore::Source::Stashed));
    }
}

} // verus!
}

// ======================================================================
// rwlock.rs and rwlock/{read_guard,write_guard,owned_read_guard,owned_write_guard}.rs
// (data pointers, `PhantomData` markers and `map` closures omitted)
// ======================================================================
pub mod rwlock {
use std::sync::Arc;
use std::task::{Context, Poll};
use vstd::prelude::*;
use crate::batch_semaphore::{Semaphore, TryAcquireError};
use crate::batch_semaphore as ll;
use crate::common::*;
pub use crate::mutex::TryLockError;

verus! {

pub const MAX_READS: u32 = u32::MAX >> 3;

pub struct RwLock {
    // maximum number of concurrent readers
    pub mr: u32,
    //semaphore to coordinate read and write access to T
    pub s: Semaphore,
}

impl RwLock {
    pub open spec fn wf(&self) -> bool {
        &&& self.s.wf() && !self.s.inst@.closable()
        &&& 1 <= self.mr
    }
}

pub struct RwLockReadGuard<'a> {
    pub s: &'a Semaphore,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}

pub struct RwLockWriteGuard<'a> {
    pub permits_acquired: u32,
    pub s: &'a Semaphore,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}

pub struct OwnedRwLockReadGuard {
    pub lock: Arc<RwLock>,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}

pub struct OwnedRwLockWriteGuard {
    pub permits_acquired: u32,
    pub lock: Arc<RwLock>,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}

impl<'a> RwLockReadGuard<'a> {
    pub open spec fn wf(&self) -> bool { self.s.wf() && holds(self.tok@, self.s, 1) }
}
impl<'a> RwLockWriteGuard<'a> {
    pub open spec fn wf(&self) -> bool {
        self.s.wf() && self.permits_acquired >= 1 && holds(self.tok@, self.s, self.permits_acquired as nat)
    }
}
impl OwnedRwLockReadGuard {
    pub open spec fn wf(&self) -> bool { self.lock.wf() && holds(self.tok@, &self.lock.s, 1) }
}
impl OwnedRwLockWriteGuard {
    pub open spec fn wf(&self) -> bool {
        self.lock.wf() && self.permits_acquired >= 1 && holds(self.tok@, &self.lock.s, self.permits_acquired as nat)
    }
}

/// `rwlock/write_guard.rs` `Inner`
pub struct WriteInner<'a> {
    pub permits_acquired: u32,
    pub s: &'a Semaphore,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}
impl<'a> WriteInner<'a> {
    pub open spec fn wf(&self) -> bool {
        self.s.wf() && self.permits_acquired >= 1 && holds(self.tok@, self.s, self.permits_acquired as nat)
    }
}

/// `rwlock/owned_write_guard.rs` `Inner`
pub struct OwnedWriteInner {
    pub permits_acquired: u32,
    pub lock: Arc<RwLock>,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}
impl OwnedWriteInner {
    pub open spec fn wf(&self) -> bool {
        self.lock.wf() && self.permits_acquired >= 1 && holds(self.tok@, &self.lock.s, self.permits_acquired as nat)
    }
}

/// The futures of `RwLock::read` (`want = 1`) and `RwLock::write` (`want = mr`),
/// flattened by hand as in `mutex::LockFuture`.
pub struct RwFuture<'a> {
    pub this: &'a RwLock,
    pub write: bool,
    pub inner: Option<ll::Acquire<'a>>,
    pub done: bool,
}

impl<'a> RwFuture<'a> {
    pub open spec fn want(&self) -> usize { if self.write { self.this.mr as usize } else { 1 } }

    pub open spec fn wf(&self) -> bool {
        &&& self.this.wf()
        &&& self.inner matches Some(a) ==> {
            &&& a.wf() && a.semaphore == &self.this.s && a.num_permits == self.want()
            &&& a.own@.value() != ll::Own::Done
        }
        &&& self.done ==> self.inner is None
    }
}

/// What `RwFuture::poll` returns: the read or the write guard.
pub enum RwGuard<'a> {
    Read(RwLockReadGuard<'a>),
    Write(RwLockWriteGuard<'a>),
}

impl RwLock {
    pub fn new() -> (r: RwLock)
        ensures r.wf(),
    {
        proof { assert(u32::MAX >> 3u32 == 0x1fff_ffffu32) by (bit_vector); }
        let (s, _budget) = Semaphore::new(MAX_READS as usize, Ghost(false), Ghost(false)); // VERUS: `let s = Semaphore::new(MAX_READS as usize);`; `close` disabled; ghost budget dropped

        RwLock {
            mr: MAX_READS,
            s,
        }
    }

    pub fn with_max_readers(max_reads: u32) -> (r: RwLock)
        ensures r.wf(), r.mr == max_reads,
    {
        check(max_reads != 0); // VERUS: `assert_ne!(max_reads, 0, "a RwLock may not be created with 0 readers");` via trusted `check`
        check(max_reads <= MAX_READS); // VERUS: `assert!(max_reads <= MAX_READS, "..")` via trusted `check`
        let (s, _budget) = Semaphore::new(max_reads as usize, Ghost(false), Ghost(false)); // VERUS: `let s = Semaphore::new(max_reads as usize);`; `close` disabled; ghost budget dropped
        RwLock {
            mr: max_reads,
            s,
        }
    }

    /// VERUS: `async fn read(&self)` returns its future; the body is in `RwFuture::poll`.
    pub fn read<'a>(&'a self) -> (r: RwFuture<'a>)
        requires self.wf(),
        ensures r.wf(), !r.done, r.this == self, !r.write,
    {
        RwFuture { this: self, write: false, inner: None, done: false }
    }

    /// VERUS: `async fn write(&self)` returns its future; the body is in `RwFuture::poll`.
    pub fn write<'a>(&'a self) -> (r: RwFuture<'a>)
        requires self.wf(),
        ensures r.wf(), !r.done, r.this == self, r.write,
    {
        RwFuture { this: self, write: true, inner: None, done: false }
    }

    pub fn try_read(&self) -> (r: Result<RwLockReadGuard<'_>, TryLockError>)
        requires self.wf(),
        ensures r matches Ok(g) ==> g.wf() && g.s == &self.s,
    {
        let tracked mut out = None;
        match self.s.try_acquire(1, Tracked(&mut out)) {
            Ok(permit) => permit,
            Err(TryAcquireError::NoPermits) => return Err(TryLockError(())),
            Err(TryAcquireError::Closed) => unreachable_(), // VERUS: `unreachable!()`; Verus proves it is not reached
        }

        let tok = stash(&self.s, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
        let guard = RwLockReadGuard {
            s: &self.s,
            tok, // VERUS: ghost field
        };

        Ok(guard)
    }

    pub fn try_write(&self) -> (r: Result<RwLockWriteGuard<'_>, TryLockError>)
        requires self.wf(),
        ensures r matches Ok(g) ==> g.wf() && g.s == &self.s && g.permits_acquired == self.mr,
    {
        ll::runtime_assert(self.mr != 0); // VERUS: `debug_assert_ne!(self.mr, 0);` as runtime_assert (Verus proves it)
        let tracked mut out = None;
        match self.s.try_acquire(self.mr as usize, Tracked(&mut out)) {
            Ok(permit) => permit,
            Err(TryAcquireError::NoPermits) => return Err(TryLockError(())),
            Err(TryAcquireError::Closed) => unreachable_(), // VERUS: `unreachable!()`; Verus proves it is not reached
        }

        let tok = stash(&self.s, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
        let guard = RwLockWriteGuard {
            permits_acquired: self.mr,
            s: &self.s,
            tok, // VERUS: ghost field
        };

        Ok(guard)
    }
}

impl<'a> RwFuture<'a> {
    pub fn poll(&mut self, cx: &mut Context<'_>) -> (ret: Poll<RwGuard<'a>>)
        requires old(self).wf(), !old(self).done,
        ensures
            self.wf(), self.this == old(self).this, self.write == old(self).write,
            ret is Ready <==> self.done,
            ret matches Poll::Ready(RwGuard::Read(g)) ==> !self.write && g.wf() && g.s == &self.this.s,
            ret matches Poll::Ready(RwGuard::Write(g)) ==> self.write && g.wf() && g.s == &self.this.s && g.permits_acquired == self.this.mr,
    {
        // VERUS: the `.await` is written out as in `AcquireManyFuture::poll`
        if self.inner.is_none() {
            if self.write { // VERUS: `write`: `debug_assert_ne!(self.mr, 0); self.s.acquire(self.mr as usize)`; `read`: `self.s.acquire(1)`
                ll::runtime_assert(self.this.mr != 0); // VERUS: (see above)
                self.inner = Some(self.this.s.acquire(self.this.mr as usize)); // VERUS: (see above)
            } else { // VERUS: (see above)
                self.inner = Some(self.this.s.acquire(1)); // VERUS: (see above)
            }
        }
        let mut inner = self.inner.take().unwrap(); // VERUS: (see above)
        let tracked mut out = None;
        match inner.poll(cx, Tracked(&mut out)) { // VERUS: (see above)
            Poll::Pending => {
                self.inner = Some(inner); // VERUS: (see above)
                Poll::Pending
            },
            Poll::Ready(r) => {
                inner.drop(); // VERUS: Rust drops the `Acquire` at the end of the statement
                self.done = true; // VERUS: (see above)
                match r { // VERUS: `.unwrap_or_else(|_| { unreachable!() })` written as a match
                    Ok(()) => {},
                    Err(_) => unreachable_(), // VERUS: `unreachable!()`; Verus proves it is not reached
                }
                let tok = stash(&self.this.s, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
                if self.write { // VERUS: `write` returns `RwLockWriteGuard { .. }`, `read` returns `RwLockReadGuard { .. }`
                    Poll::Ready(RwGuard::Write(RwLockWriteGuard { // VERUS: (see above)
                        permits_acquired: self.this.mr, // VERUS: `permits_acquired: self.mr,`
                        s: &self.this.s, // VERUS: `s: &self.s,`
                        tok, // VERUS: ghost field
                    }))
                } else { // VERUS: (see above)
                    Poll::Ready(RwGuard::Read(RwLockReadGuard { // VERUS: (see above)
                        s: &self.this.s, // VERUS: `s: &self.s,`
                        tok, // VERUS: ghost field
                    }))
                }
            },
        }
    }

    /// Drop glue of the suspended future: drops the `Acquire`.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.inner is None,
    {
        // VERUS: compiler-generated drop of the suspended `async` state
        if self.inner.is_some() {
            let mut inner = self.inner.take().unwrap(); // VERUS: (see above)
            inner.drop(); // VERUS: (see above)
        }
    }
}

impl<'a> RwLockReadGuard<'a> {
    /// `impl Drop for RwLockReadGuard<'a, T>`. VERUS: verified as a method; Rust calls it once when the guard is dropped.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        self.s.release(1, Tracked(self.tok.borrow_mut()), Tracked(ll::Source::Stashed));
    }
}

impl<'a> RwLockWriteGuard<'a> {
    fn skip_drop(self) -> (r: WriteInner<'a>)
        requires self.wf(),
        ensures r.wf(), r.s == self.s, r.permits_acquired == self.permits_acquired,
    {
        let me = self; // VERUS: `mem::ManuallyDrop::new(self)`: the guard's drop is not run (no call to `drop` follows)
        WriteInner { // VERUS: `Inner {`
            permits_acquired: me.permits_acquired,
            s: me.s,
            tok: me.tok, // VERUS: ghost field
        }
    }

    /// `op` is this call's ghost local (Sem `fl` token, at 0 on entry and on return).
    pub fn downgrade(self, Tracked(op): Tracked<&mut ll::Sem::fl>) -> (r: RwLockReadGuard<'a>)
        requires self.wf(), holds(*old(op), self.s, 0),
        ensures r.wf(), r.s == self.s, op.key() == old(op).key(), holds(*op, self.s, 0),
    {
        let this = self.skip_drop();
        let Tracked(mut tok) = this.s.new_op(); // VERUS: ghost-only (no runtime code)
        let mut this = this; // VERUS: ghost-only rebinding so the ghost field can be moved
        proof {
            move_permits(this.s.inst.borrow(), this.tok.borrow_mut(), op, this.permits_acquired as nat);
            move_permits(this.s.inst.borrow(), op, &mut tok, 1);
        }
        let guard = RwLockReadGuard {
            s: this.s,
            tok: Tracked(tok), // VERUS: ghost field
        };

        // Release all but one of the permits held by the write guard
        let to_release = (this.permits_acquired - 1) as usize;
        this.s.release(to_release, Tracked(op), Tracked(ll::Source::Stashed));

        guard
    }

    /// `impl Drop for RwLockWriteGuard<'a, T>`. VERUS: verified as a method.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures
            self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
            self.s == old(self).s, self.permits_acquired == old(self).permits_acquired,
    {
        self.s.release(self.permits_acquired as usize, Tracked(self.tok.borrow_mut()), Tracked(ll::Source::Stashed));
    }
}

impl OwnedRwLockReadGuard {
    /// `impl Drop for OwnedRwLockReadGuard<T, U>`. VERUS: verified as a method.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        self.lock.s.release(1, Tracked(self.tok.borrow_mut()), Tracked(ll::Source::Stashed));
    }
}

impl OwnedRwLockWriteGuard {
    fn skip_drop(self) -> (r: OwnedWriteInner)
        requires self.wf(),
        ensures r.wf(), r.lock == self.lock, r.permits_acquired == self.permits_acquired,
    {
        let me = self; // VERUS: `mem::ManuallyDrop::new(self)`: the guard's drop is not run (no call to `drop` follows)
        OwnedWriteInner { // VERUS: `unsafe { Inner {`
            permits_acquired: me.permits_acquired,
            lock: me.lock, // VERUS: `lock: ptr::read(&me.lock),`
            tok: me.tok, // VERUS: ghost field
        }
    }

    /// `op` is this call's ghost local (at 0 on entry and on return).
    pub fn downgrade(self, Tracked(op): Tracked<&mut ll::Sem::fl>) -> (r: OwnedRwLockReadGuard)
        requires self.wf(), holds(*old(op), &self.lock.s, 0),
        ensures r.wf(), r.lock == self.lock, op.key() == old(op).key(), holds(*op, &self.lock.s, 0),
    {
        let this = self.skip_drop();
        let Tracked(mut tok) = this.lock.s.new_op(); // VERUS: ghost-only (no runtime code)
        let mut this = this; // VERUS: ghost-only rebinding so the ghost field can be moved
        proof {
            move_permits(this.lock.s.inst.borrow(), this.tok.borrow_mut(), op, this.permits_acquired as nat);
            move_permits(this.lock.s.inst.borrow(), op, &mut tok, 1);
        }
        let guard = OwnedRwLockReadGuard {
            lock: this.lock,
            tok: Tracked(tok), // VERUS: ghost field
        };

        // Release all but one of the permits held by the write guard
        let to_release = (this.permits_acquired - 1) as usize;
        guard.lock.s.release(to_release, Tracked(op), Tracked(ll::Source::Stashed));

        guard
    }

    /// `impl Drop for OwnedRwLockWriteGuard<T>`. VERUS: verified as a method.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        self.lock.s.release(self.permits_acquired as usize, Tracked(self.tok.borrow_mut()), Tracked(ll::Source::Stashed));
    }
}

} // verus!
}

// ======================================================================
// bounded mpsc: mpsc/bounded.rs and mpsc/chan.rs (chan.rs with `S` fixed to
// `bounded::Semaphore`; the `chan::Semaphore` trait methods are inherent methods)
// ======================================================================
pub mod mpsc {
use std::sync::Arc;
use vstd::invariant::*;
use std::task::{Context, Poll};
use std::task::Poll::{Pending, Ready};
use vstd::prelude::*;
use crate::batch_semaphore::{self as semaphore, TryAcquireError};
use crate::batch_semaphore as ll;
use crate::common::*;

verus! {

// ----------------------------------------------------------------------
// The lock-free block list (`list::Tx`/`list::Rx`). Trusted: only `RawTx`/`RawRx`,
// whose spec is about the list alone: a ghost `ListLen` counts the values in the
// list; `push` adds 1; a `pop` that returns a value needs the count >= 1 and
// subtracts 1. Verified: `ListTx`/`ListRx`, which keep one keyed ledger token per
// channel (the list token) in an atomic invariant with value = count, and move
// exactly one permit per message through the `transfer` transition.
// `AtomicWaker` and `Notify` are trusted not to touch permits.
// ----------------------------------------------------------------------

/// Ghost (no runtime data): the number of values in list `id()`. Trusted; no constructor.
#[verifier::external_body]
pub struct ListLen { v: () }

impl ListLen {
    pub uninterp spec fn id(&self) -> nat;
    pub uninterp spec fn len(&self) -> nat;
}

#[verifier::external_body]
#[verifier::reject_recursive_types(T)]
pub struct RawTx<T> { v: std::marker::PhantomData<T> }

#[verifier::external_body]
#[verifier::reject_recursive_types(T)]
pub struct RawRx<T> { v: std::marker::PhantomData<T> }

pub enum Read<T> {
    Value(T),
    Closed,
}

impl<T> RawTx<T> {
    pub uninterp spec fn id(&self) -> nat;

    /// `list::Tx::push` (trusted, linearizable).
    #[verifier::external_body]
    #[verifier::atomic]
    pub fn push(&self, value: T, Tracked(len): Tracked<&mut ListLen>)
        requires old(len).id() == self.id(),
        ensures len.id() == old(len).id(), len.len() == old(len).len() + 1,
        opens_invariants none
        no_unwind
    {
        unimplemented!()
    }
}

impl<T> RawRx<T> {
    pub uninterp spec fn id(&self) -> nat;

    /// `list::Rx::pop` (trusted, linearizable).
    #[verifier::external_body]
    #[verifier::atomic]
    pub fn pop(&mut self, tx: &RawTx<T>, Tracked(len): Tracked<&mut ListLen>) -> (r: Option<Read<T>>)
        requires old(self).id() == tx.id(), old(len).id() == tx.id(),
        ensures
            self.id() == old(self).id(), len.id() == old(len).id(),
            r matches Some(Read::Value(_)) ==> old(len).len() >= 1 && len.len() == old(len).len() - 1,
            !(r matches Some(Read::Value(_))) ==> len.len() == old(len).len(),
        opens_invariants none
        no_unwind
    {
        unimplemented!()
    }
}

/// `list::channel()` (trusted): an empty list.
#[verifier::external_body]
pub fn raw_channel<T>() -> (r: (RawTx<T>, RawRx<T>, Tracked<ListLen>))
    ensures r.1.id() == r.0.id(), r.2@.id() == r.0.id(), r.2@.len() == 0,
{
    unimplemented!()
}

pub open spec fn LIST_NS() -> int { 78 }

/// The list invariant, keyed by (semaphore instance, list id, list token key):
/// the list token holds exactly one permit per value in the list.
pub struct ListPred;

impl InvariantPredicate<(InstanceId, nat, nat), (ListLen, ll::Sem::fl)> for ListPred {
    open spec fn inv(k: (InstanceId, nat, nat), v: (ListLen, ll::Sem::fl)) -> bool {
        &&& v.0.id() == k.1
        &&& v.1.instance_id() == k.0 && v.1.key() == ll::Key::O(k.2)
        &&& v.1.value() == v.0.len()
    }
}

#[verifier::reject_recursive_types(T)]
pub struct ListTx<T> {
    pub raw: RawTx<T>,
    pub sem_inst: Tracked<ll::Sem::Instance>,
    pub inv: Tracked<AtomicInvariant<(InstanceId, nat, nat), (ListLen, ll::Sem::fl), ListPred>>,
}

#[verifier::reject_recursive_types(T)]
pub struct ListRx<T> {
    pub raw: RawRx<T>,
}

impl<T> ListTx<T> {
    /// The semaphore instance whose permits the messages carry.
    pub open spec fn inst(&self) -> InstanceId { self.inv@.constant().0 }
    /// The key of this channel's list token: `Key::O(key())`.
    pub open spec fn key(&self) -> nat { self.inv@.constant().2 }

    pub open spec fn wf(&self) -> bool {
        &&& self.inv@.namespace() == LIST_NS()
        &&& self.inv@.constant().1 == self.raw.id()
        &&& self.sem_inst@.id() == self.inst()
    }

    /// Move one permit from `op` into the list token, with the message.
    pub fn push(&self, value: T, Tracked(op): Tracked<&mut ll::Sem::fl>)
        requires self.wf(), old(op).instance_id() == self.inst(), old(op).key() is O, old(op).value() >= 1,
        ensures op.instance_id() == old(op).instance_id(), op.key() == old(op).key(), op.value() == old(op).value() - 1,
    {
        open_atomic_invariant!(self.inv.borrow() => g => {
            let tracked (mut len, mut tok) = g;
            self.raw.push(value, Tracked(&mut len));
            proof {
                move_permits(self.sem_inst.borrow(), op, &mut tok, 1);
                g = (len, tok);
            }
        });
    }
}

impl<T> ListRx<T> {
    /// Pop a message; a value's permit moves from the list token into `op`.
    pub fn pop(&mut self, tx: &ListTx<T>, Tracked(op): Tracked<&mut ll::Sem::fl>) -> (r: Option<Read<T>>)
        requires tx.wf(), old(self).raw.id() == tx.raw.id(), old(op).instance_id() == tx.inst(), old(op).key() is O,
        ensures
            self.raw.id() == old(self).raw.id(),
            op.instance_id() == old(op).instance_id(), op.key() == old(op).key(),
            op.value() == old(op).value() + if r matches Some(Read::Value(_)) { 1nat } else { 0nat },
    {
        let r;
        open_atomic_invariant!(tx.inv.borrow() => g => {
            let tracked (mut len, mut tok) = g;
            r = self.raw.pop(&tx.raw, Tracked(&mut len));
            proof {
                if r matches Some(Read::Value(_)) {
                    move_permits(tx.sem_inst.borrow(), &mut tok, op, 1);
                }
                g = (len, tok);
            }
        });
        r
    }
}

/// `list::channel()`: an empty list and a fresh list token (value 0) on `sem`.
pub fn list_channel<T>(sem: &ll::Semaphore) -> (r: (ListTx<T>, ListRx<T>))
    requires sem.wf(),
    ensures r.0.wf(), r.0.inst() == sem.inst@.id(), r.1.raw.id() == r.0.raw.id(),
{
    let (raw_tx, raw_rx, Tracked(len)) = raw_channel();
    let Tracked(tok) = sem.new_op();
    let tracked inv = AtomicInvariant::new((sem.inst@.id(), raw_tx.id(), tok.key()->O_0), (len, tok), LIST_NS());
    let tracked si = sem.inst.borrow().clone();
    (ListTx { raw: raw_tx, sem_inst: Tracked(si), inv: Tracked(inv) }, ListRx { raw: raw_rx })
}

#[verifier::external_body]
pub struct AtomicWaker { v: () }

impl AtomicWaker {
    #[verifier::external_body]
    pub fn new() -> Self { AtomicWaker { v: () } }
    #[verifier::external_body]
    pub fn wake(&self) {}
    /// `register_by_ref(cx.waker())`
    #[verifier::external_body]
    pub fn register_by_ref(&self, cx: &mut Context<'_>) {}
    #[verifier::external_body]
    pub fn take_waker(&self) {}
}

#[verifier::external_body]
pub struct Notify { v: () }

impl Notify {
    #[verifier::external_body]
    pub fn new() -> Self { Notify { v: () } }
    #[verifier::external_body]
    pub fn notify_waiters(&self) {}
}

pub struct SendError<T>(pub T);

pub enum TrySendError<T> {
    Full(T),
    Closed(T),
}

} // verus!

pub mod chan {
use std::sync::Arc;
use std::task::{Context, Poll};
use std::task::Poll::{Pending, Ready};
use vstd::prelude::*;
use crate::batch_semaphore::{self as semaphore, TryAcquireError};
use crate::batch_semaphore as ll;
use crate::common::*;
use super::*;
use super::bounded::Semaphore;

verus! {

// ----------------------------------------------------------------------
// chan.rs `impl Semaphore for bounded::Semaphore`
// ----------------------------------------------------------------------

impl Semaphore {
    pub open spec fn wf(&self) -> bool {
        &&& self.semaphore.wf() && self.semaphore.inst@.closable()
        &&& self.semaphore.inst@.fixed() && self.semaphore.inst@.initial() == self.bound // total = bound
        &&& 1 <= self.bound <= ll::MAXP()
    }

    pub open spec fn id(&self) -> InstanceId { self.semaphore.inst@.id() }

    /// `fn add_permit(&self)`; `op` holds the permit being returned.
    pub fn add_permit(&self, Tracked(op): Tracked<&mut ll::Sem::fl>)
        requires self.wf(), holds(*old(op), &self.semaphore, 1),
        ensures op.key() == old(op).key(), holds(*op, &self.semaphore, 0),
    {
        self.semaphore.release(1, Tracked(op), Tracked(ll::Source::Stashed));
    }

    pub fn is_idle(&self) -> bool
        requires self.wf(),
    {
        self.semaphore.available_permits() == self.bound
    }

    pub fn close(&self)
        requires self.wf(),
    {
        self.semaphore.close();
    }

    pub fn is_closed(&self) -> bool
        requires self.wf(),
    {
        self.semaphore.is_closed()
    }
}

// ----------------------------------------------------------------------
// chan.rs
// ----------------------------------------------------------------------

#[verifier::reject_recursive_types(T)]
pub struct Chan<T> {
    pub tx: ListTx<T>, // VERUS: `CachePadded<list::Tx<T>>`
    pub rx_waker: AtomicWaker, // VERUS: `CachePadded<AtomicWaker>`
    pub notify_rx_closed: Notify,
    pub semaphore: Semaphore,
    // VERUS: `tx_count`, `tx_weak_count` omitted (no permits); `rx_fields` moved into `Rx` (only `Rx` accesses it)
}

#[verifier::reject_recursive_types(T)]
pub struct RxFields<T> {
    pub list: ListRx<T>,
    pub rx_closed: bool,
}

#[verifier::reject_recursive_types(T)]
pub struct Tx<T> {
    pub inner: Arc<Chan<T>>,
}

#[verifier::reject_recursive_types(T)]
pub struct Rx<T> {
    pub inner: Arc<Chan<T>>,
    pub rx_fields: RxFields<T>, // VERUS: `inner.rx_fields: UnsafeCell<RxFields<T>>`, accessed only by `Rx`
}

impl<T> Chan<T> {
    pub open spec fn wf(&self) -> bool {
        self.semaphore.wf() && self.tx.wf() && self.tx.inst() == self.semaphore.id()
    }
}

impl<T> Tx<T> {
    pub open spec fn wf(&self) -> bool { self.inner.wf() }
}

impl<T> Rx<T> {
    pub open spec fn wf(&self) -> bool { self.inner.wf() && self.rx_fields.list.raw.id() == self.inner.tx.raw.id() }
}

pub fn channel<T>(semaphore: Semaphore) -> (r: (Tx<T>, Rx<T>))
    requires semaphore.wf(),
    ensures r.0.wf(), r.1.wf(), r.0.inner == r.1.inner, !r.1.rx_fields.rx_closed, r.0.inner.semaphore == semaphore,
{
    let (tx, rx) = list_channel(&semaphore.semaphore); // VERUS: `list::channel()`, plus the channel's list token on `semaphore`
    // VERUS: `channel_from_list(tx, rx, semaphore)` inlined
    let chan = Arc::new(Chan {
        notify_rx_closed: Notify::new(),
        tx, // VERUS: `tx: CachePadded::new(tx),`
        semaphore,
        rx_waker: AtomicWaker::new(), // VERUS: `rx_waker: CachePadded::new(AtomicWaker::new()),`
    });

    (Tx { inner: chan.clone() }, Rx { inner: chan, rx_fields: RxFields { list: rx, rx_closed: false } }) // VERUS: `(Tx::new(chan.clone()), Rx::new(chan))` with `rx_fields` in `Rx`
}

impl<T> Tx<T> {
    pub fn semaphore(&self) -> (r: &Semaphore)
        ensures r == &self.inner.semaphore,
    {
        &self.inner.semaphore
    }

    /// Send a message and notify the receiver. `op` holds the message's permit.
    pub fn send(&self, value: T, Tracked(op): Tracked<&mut ll::Sem::fl>)
        requires self.wf(), holds(*old(op), &self.inner.semaphore.semaphore, 1),
        ensures op.key() == old(op).key(), holds(*op, &self.inner.semaphore.semaphore, 0),
    {
        // VERUS: `self.inner.send(value)` with `Chan::send` inlined:
        // Push the value
        self.inner.tx.push(value, Tracked(op)); // VERUS: `self.tx.push(value);`

        // Notify the rx task
        self.inner.rx_waker.wake(); // VERUS: `self.rx_waker.wake();`
    }

    /// Wake the receive half
    pub fn wake_rx(&self) {
        self.inner.rx_waker.wake();
    }
}

impl<T> Rx<T> {
    pub fn close(&mut self)
        requires old(self).wf(),
        ensures self.wf(), self.rx_fields.rx_closed, self.inner == old(self).inner,
    {
        // VERUS: `self.inner.rx_fields.with_mut(|rx_fields_ptr| { .. })` inlined; its `return` leaves only the closure
        if self.rx_fields.rx_closed {
        } else { // VERUS: (see above)
            self.rx_fields.rx_closed = true; // VERUS: `rx_fields.rx_closed = true;`
        }

        self.inner.semaphore.close();
        self.inner.notify_rx_closed.notify_waiters();
    }

    /// Receive the next value. `op` is this call's ghost local (at 0 on entry and on return).
    pub fn recv(&mut self, cx: &mut Context<'_>, Tracked(op): Tracked<&mut ll::Sem::fl>) -> (r: Poll<Option<T>>)
        requires old(self).wf(), holds(*old(op), &old(self).inner.semaphore.semaphore, 0),
        ensures
            self.wf(), self.inner == old(self).inner, self.rx_fields.rx_closed == old(self).rx_fields.rx_closed,
            op.key() == old(op).key(), holds(*op, &self.inner.semaphore.semaphore, 0),
    {
        // ready!(crate::trace::trace_leaf(cx));   VERUS: taskdump-only, returns Ready

        // Keep track of task budget
        let coop = match ll::poll_proceed(cx) { // VERUS: `ready!(..)` expanded
            Poll::Ready(c) => c,
            Poll::Pending => return Poll::Pending,
        };

        // VERUS: `self.inner.rx_fields.with_mut(|rx_fields_ptr| { .. })` inlined; both uses of
        // `macro_rules! try_recv` expanded by hand (correspond_clients.py expands the real macro the same way)
        match self.rx_fields.list.pop(&self.inner.tx, Tracked(op)) { // VERUS: `match rx_fields.list.pop(&self.inner.tx) {`
            Some(Read::Value(value)) => {
                self.inner.semaphore.add_permit(Tracked(op));
                coop.made_progress();
                return Ready(Some(value));
            }
            Some(Read::Closed) => {
                // A channel is closed when all tx handles are
                // dropped. Dropping a tx handle releases memory,
                // which ensures that if dropping the tx handle is
                // visible, then all messages sent are also visible.
                debug_assert_unproved(self.inner.semaphore.is_idle()); // VERUS: `debug_assert!(self.inner.semaphore.is_idle());` (not proved; see CLIENTS_PROOF.md)
                coop.made_progress();
                return Ready(None);
            }
            None => {} // fall through
        }

        self.inner.rx_waker.register_by_ref(cx); // VERUS: `register_by_ref(cx.waker())`

        // It is possible that a value was pushed between attempting to read
        // and registering the task, so we have to check the channel a
        // second time here.
        match self.rx_fields.list.pop(&self.inner.tx, Tracked(op)) { // VERUS: `match rx_fields.list.pop(&self.inner.tx) {`
            Some(Read::Value(value)) => {
                self.inner.semaphore.add_permit(Tracked(op));
                coop.made_progress();
                return Ready(Some(value));
            }
            Some(Read::Closed) => {
                // A channel is closed when all tx handles are
                // dropped. Dropping a tx handle releases memory,
                // which ensures that if dropping the tx handle is
                // visible, then all messages sent are also visible.
                debug_assert_unproved(self.inner.semaphore.is_idle()); // VERUS: `debug_assert!(self.inner.semaphore.is_idle());` (not proved; see CLIENTS_PROOF.md)
                coop.made_progress();
                return Ready(None);
            }
            None => {} // fall through
        }

        if self.rx_fields.rx_closed && self.inner.semaphore.is_idle() { // VERUS: `rx_fields.rx_closed` is `self.rx_fields.rx_closed`
            coop.made_progress();
            Ready(None)
        } else {
            Pending
        }
    }

    /// `Guard::drain` of `impl Drop for Rx`: pops every value, returning its permit.
    pub fn drain(&mut self, Tracked(op): Tracked<&mut ll::Sem::fl>)
        requires old(self).wf(), holds(*old(op), &old(self).inner.semaphore.semaphore, 0),
        ensures
            self.wf(), self.inner == old(self).inner, self.rx_fields.rx_closed == old(self).rx_fields.rx_closed,
            op.key() == old(op).key(), holds(*op, &self.inner.semaphore.semaphore, 0),
    {
        // call T's destructor.
        // VERUS: `while let Some(Value(_)) = self.list.pop(self.tx) { .. }` written as `loop { match .. }`
        loop
            invariant
                self.wf(), self.inner == old(self).inner, self.rx_fields.rx_closed == old(self).rx_fields.rx_closed,
                op.key() == old(op).key(), holds(*op, &self.inner.semaphore.semaphore, 0),
        {
            match self.rx_fields.list.pop(&self.inner.tx, Tracked(op)) { // VERUS: (see above)
                Some(Read::Value(_)) => { // VERUS: (see above)
                    self.inner.semaphore.add_permit(Tracked(op)); // VERUS: `self.sem.add_permit();`
                },
                _ => break, // VERUS: (see above)
            }
        }
    }

    /// `impl Drop for Rx<T, S>`. VERUS: verified as a method; the `Guard` whose drop
    /// drains again is written as a second `drain` call.
    pub fn drop(&mut self, Tracked(op): Tracked<&mut ll::Sem::fl>)
        requires old(self).wf(), holds(*old(op), &old(self).inner.semaphore.semaphore, 0),
        ensures op.key() == old(op).key(), holds(*op, &self.inner.semaphore.semaphore, 0),
    {
        self.close();

        // When Rx is dropped, there is nothing for a task to poll anymore.
        // This means we can drop our waker to potentially free up resources.
        // Do so before draining the channel where panics may occur.
        self.inner.rx_waker.take_waker(); // VERUS: real line; the in-order check pairs `Guard::drop`'s `self.drain();` with the call below, so it lists this line as added

        self.drain(Tracked(op)); // VERUS: `guard.drain();`
        self.drain(Tracked(op)); // VERUS: `Guard::drop` runs `drain` again
    }
}

} // verus!
}

pub mod bounded {
use std::sync::Arc;
use std::task::{Context, Poll};
use std::task::Poll::{Pending, Ready};
use vstd::prelude::*;
use crate::batch_semaphore::{self as semaphore, TryAcquireError};
use crate::batch_semaphore as ll;
use crate::common::*;
use super::*;
use super::chan;
use super::chan::{Tx, Rx};

verus! {

/// Channel semaphore is a tuple of the semaphore implementation and a `usize`
/// representing the channel bound.
pub struct Semaphore {
    pub semaphore: semaphore::Semaphore,
    pub bound: usize,
}

// ----------------------------------------------------------------------
// bounded.rs
// ----------------------------------------------------------------------

#[verifier::reject_recursive_types(T)]
pub struct Sender<T> {
    pub chan: Tx<T>,
}

#[verifier::reject_recursive_types(T)]
pub struct Receiver<T> {
    /// The channel receiver.
    pub chan: Rx<T>,
}

#[verifier::reject_recursive_types(T)]
pub struct Permit<'a, T> {
    pub chan: &'a Tx<T>,
    pub tok: Tracked<ll::Sem::fl>, // VERUS: ghost field
}

impl<T> Sender<T> {
    pub open spec fn wf(&self) -> bool { self.chan.wf() }
}

impl<T> Receiver<T> {
    pub open spec fn wf(&self) -> bool { self.chan.wf() }
}

impl<'a, T> Permit<'a, T> {
    pub open spec fn wf(&self) -> bool {
        self.chan.wf() && holds(self.tok@, &self.chan.inner.semaphore.semaphore, 1)
    }
}

#[verifier::reject_recursive_types(T)]
pub struct WakeReceiverOnDrop<'a, T> {
    pub chan: &'a Tx<T>,
}

impl<'a, T> WakeReceiverOnDrop<'a, T> {
    pub fn drop(&mut self)
        requires old(self).chan.wf(),
    {
        let semaphore = self.chan.semaphore();
        if semaphore.is_closed() && semaphore.is_idle() {
            self.chan.wake_rx();
        }
    }
}

pub fn channel<T>(buffer: usize) -> (r: (Sender<T>, Receiver<T>))
    requires buffer <= ll::MAXP(), // VERUS: client obligation; a larger `buffer` panics in `semaphore::Semaphore::new`
    ensures r.0.wf(), r.1.wf(), r.0.chan.inner == r.1.chan.inner, !r.1.chan.rx_fields.rx_closed, r.0.chan.inner.semaphore.bound == buffer,
{
    check(buffer > 0); // VERUS: `assert!(buffer > 0, "mpsc bounded channel requires buffer > 0");` via trusted `check`
    let (sem, _budget) = semaphore::Semaphore::new(buffer, Ghost(true), Ghost(true)); // VERUS: `semaphore::Semaphore::new(buffer)` bound first; `close` allowed; `fixed`: total stays `buffer`
    let semaphore = Semaphore {
        semaphore: sem, // VERUS: `semaphore: semaphore::Semaphore::new(buffer),` (bound above)
        bound: buffer,
    };
    let (tx, rx) = chan::channel(semaphore);

    let tx = Sender { chan: tx }; // VERUS: `Sender::new(tx)` inlined
    let rx = Receiver { chan: rx }; // VERUS: `Receiver::new(rx)` inlined

    (tx, rx)
}

/// The future of `Sender::reserve` (`async fn` awaiting `reserve_inner(1)`, an `async fn`
/// awaiting `self.chan.semaphore().semaphore.acquire(n)`), flattened by hand.
#[verifier::reject_recursive_types(T)]
pub struct ReserveFuture<'a, T> {
    pub this: &'a Sender<T>,
    pub guard: Option<WakeReceiverOnDrop<'a, T>>,
    pub inner: Option<ll::Acquire<'a>>,
    pub done: bool,
}

impl<'a, T> ReserveFuture<'a, T> {
    pub open spec fn wf(&self) -> bool {
        &&& self.this.wf()
        &&& self.inner matches Some(a) ==> {
            &&& a.wf() && a.semaphore == &self.this.chan.inner.semaphore.semaphore && a.num_permits == 1
            &&& a.own@.value() != ll::Own::Done
        }
        &&& self.guard matches Some(g) ==> g.chan == &self.this.chan
        &&& (self.inner is Some <==> self.guard is Some)
        &&& self.done ==> self.inner is None && self.guard is None
    }
}

/// The future of `Sender::send` (`async fn` awaiting `self.reserve()`), flattened by hand.
#[verifier::reject_recursive_types(T)]
pub struct SendFuture<'a, T> {
    pub this: &'a Sender<T>,
    pub value: Option<T>,
    pub reserve: Option<ReserveFuture<'a, T>>,
    pub done: bool,
}

impl<'a, T> SendFuture<'a, T> {
    pub open spec fn wf(&self) -> bool {
        &&& self.this.wf()
        &&& self.reserve matches Some(r) ==> r.wf() && r.this == self.this && !r.done
        &&& !self.done ==> self.value is Some
        &&& self.done ==> self.reserve is None
    }
}

impl<T> Sender<T> {
    pub fn max_capacity(&self) -> usize {
        self.chan.semaphore().bound
    }

    /// VERUS: `async fn reserve(&self)` returns its future; the body is in `ReserveFuture::poll`.
    pub fn reserve<'a>(&'a self) -> (r: ReserveFuture<'a, T>)
        requires self.wf(),
        ensures r.wf(), r.this == self, !r.done, r.inner is None,
    {
        ReserveFuture { this: self, guard: None, inner: None, done: false }
    }

    /// VERUS: `async fn send(&self, value: T)` returns its future; the body is in `SendFuture::poll`.
    pub fn send<'a>(&'a self, value: T) -> (r: SendFuture<'a, T>)
        requires self.wf(),
        ensures r.wf(), r.this == self, !r.done,
    {
        SendFuture { this: self, value: Some(value), reserve: None, done: false }
    }

    /// `op` is this call's ghost local (at 0 on entry and on return).
    pub fn try_send(&self, message: T, Tracked(op): Tracked<&mut ll::Sem::fl>) -> (r: Result<(), TrySendError<T>>)
        requires self.wf(), holds(*old(op), &self.chan.inner.semaphore.semaphore, 0),
        ensures op.key() == old(op).key(), holds(*op, &self.chan.inner.semaphore.semaphore, 0),
    {
        let tracked mut out = None;
        match self.chan.semaphore().semaphore.try_acquire(1, Tracked(&mut out)) {
            Ok(()) => {}
            Err(TryAcquireError::Closed) => return Err(TrySendError::Closed(message)),
            Err(TryAcquireError::NoPermits) => return Err(TrySendError::Full(message)),
        }
        proof {
            let tracked f = ll::take_fl(op);
            *op = self.chan.inner.semaphore.semaphore.inst.borrow().begin_release(f.key()->O_0, 1, f, out.tracked_unwrap());
        }

        // Send the message
        self.chan.send(message, Tracked(op));
        Ok(())
    }
}

impl<'a, T> ReserveFuture<'a, T> {
    pub fn poll(&mut self, cx: &mut Context<'_>) -> (ret: Poll<Result<Permit<'a, T>, SendError<()>>>)
        requires old(self).wf(), !old(self).done,
        ensures
            self.wf(), self.this == old(self).this,
            ret is Ready <==> self.done,
            ret matches Poll::Ready(Ok(p)) ==> p.wf() && p.chan == &self.this.chan,
    {
        if self.inner.is_none() { // VERUS: first poll of the `async fn` (see `AcquireManyFuture::poll`)
            // crate::trace::async_trace_leaf().await;   VERUS: taskdump-only, returns Ready
            if 1 > self.this.max_capacity() { // VERUS: `if n > self.max_capacity() {` with `n = 1`
                self.done = true; // VERUS: the `async fn` returns
                return Poll::Ready(Err(SendError(()))); // VERUS: `return Err(SendError(()));`
            }
            self.guard = Some(WakeReceiverOnDrop { chan: &self.this.chan }); // VERUS: `let guard = WakeReceiverOnDrop { chan: &self.chan };`
            self.inner = Some(self.this.chan.semaphore().semaphore.acquire(1)); // VERUS: `self.chan.semaphore().semaphore.acquire(n)`, `.await` written out as in `AcquireManyFuture::poll`
        }
        let mut inner = self.inner.take().unwrap(); // VERUS: (see above)
        let tracked mut out = None;
        match inner.poll(cx, Tracked(&mut out)) { // VERUS: (see above)
            Poll::Pending => {
                self.inner = Some(inner); // VERUS: (see above)
                Poll::Pending
            },
            Poll::Ready(result) => { // VERUS: `let result = ..await;`
                inner.drop(); // VERUS: Rust drops the `Acquire` at the end of the statement
                self.done = true; // VERUS: (see above)
                let mut guard = self.guard.take().unwrap(); // VERUS: the `guard` local
                match result {
                    Ok(()) => {
                        std::mem::forget(guard);
                        let tok = stash(&self.this.chan.inner.semaphore.semaphore, Tracked(out.tracked_unwrap())); // VERUS: ghost-only (no runtime code)
                        Poll::Ready(Ok(Permit { chan: &self.this.chan, tok })) // VERUS: `Ok(())`, then `reserve`'s `Ok(Permit { chan: &self.chan })`
                    }
                    Err(_) => { // VERUS: block for the explicit drop of `guard`
                        guard.drop(); // VERUS: Rust drops `guard` on return
                        Poll::Ready(Err(SendError(()))) // VERUS: `Err(SendError(()))`, propagated by `reserve`'s `?`
                    }
                }
            },
        }
    }

    /// Drop glue of the suspended future: Rust drops `result`'s future (the
    /// `Acquire`) first, then `guard` (reverse declaration order).
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.inner is None,
    {
        // VERUS: compiler-generated drop of the suspended `async` state
        if self.inner.is_some() {
            let mut inner = self.inner.take().unwrap(); // VERUS: (see above)
            inner.drop(); // VERUS: (see above)
        }
        if self.guard.is_some() { // VERUS: (see above)
            let mut guard = self.guard.take().unwrap(); // VERUS: (see above)
            guard.drop(); // VERUS: (see above)
        }
    }
}

impl<'a, T> SendFuture<'a, T> {
    /// `op` is this call's ghost local (at 0 on entry and on return).
    pub fn poll(&mut self, cx: &mut Context<'_>, Tracked(op): Tracked<&mut ll::Sem::fl>) -> (ret: Poll<Result<(), SendError<T>>>)
        requires old(self).wf(), !old(self).done, holds(*old(op), &old(self).this.chan.inner.semaphore.semaphore, 0),
        ensures
            self.wf(), self.this == old(self).this,
            ret is Ready <==> self.done,
            op.key() == old(op).key(), holds(*op, &self.this.chan.inner.semaphore.semaphore, 0),
    {
        if self.reserve.is_none() { // VERUS: first poll of the `async fn` (see `AcquireManyFuture::poll`)
            self.reserve = Some(self.this.reserve()); // VERUS: `self.reserve().await`, written out as in `AcquireManyFuture::poll`
        }
        let mut reserve = self.reserve.take().unwrap(); // VERUS: (see above)
        match reserve.poll(cx) { // VERUS: (see above)
            Poll::Pending => {
                self.reserve = Some(reserve); // VERUS: (see above)
                Poll::Pending
            },
            Poll::Ready(r) => {
                reserve.drop(); // VERUS: Rust drops the finished `reserve` future
                self.done = true; // VERUS: (see above)
                let value = self.value.take().unwrap(); // VERUS: the `value` argument of the `async fn`
                match r { // VERUS: `match self.reserve().await {`
                    Ok(permit) => {
                        permit.send(value, Tracked(op));
                        Poll::Ready(Ok(())) // VERUS: `Ok(())`
                    }
                    Err(_) => Poll::Ready(Err(SendError(value))), // VERUS: `Err(_) => Err(SendError(value)),` returned from the `async fn`
                }
            },
        }
    }

    /// Drop glue: in the suspended state, drops the `reserve` future (and `value`).
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.reserve is None,
    {
        // VERUS: compiler-generated drop of the suspended `async` state
        if self.reserve.is_some() {
            let mut reserve = self.reserve.take().unwrap(); // VERUS: (see above)
            reserve.drop(); // VERUS: (see above)
        }
    }
}

impl<'a, T> Permit<'a, T> {
    /// `op` is this call's ghost local (at 0 on entry and on return).
    pub fn send(self, value: T, Tracked(op): Tracked<&mut ll::Sem::fl>)
        requires self.wf(), holds(*old(op), &self.chan.inner.semaphore.semaphore, 0),
        ensures op.key() == old(op).key(), holds(*op, &self.chan.inner.semaphore.semaphore, 0),
    {
        let mut this = self; // VERUS: `self` bound mutably so that its ghost field can be moved

        let chan = this.chan; // VERUS: `let chan = self.chan;`
        proof { move_permits(chan.inner.semaphore.semaphore.inst.borrow(), this.tok.borrow_mut(), op, 1); }

        // Avoid the drop logic
        std::mem::forget(this); // VERUS: `mem::forget(self);`

        chan.send(value, Tracked(op));
    }

    /// `impl Drop for Permit<'_, T>`. VERUS: verified as a method; Rust calls it once when the permit is dropped.
    pub fn drop(&mut self)
        requires old(self).wf(),
        ensures self.tok@.key() == old(self).tok@.key(), self.tok@.value() == 0,
    {
        let semaphore = self.chan.semaphore();

        // Add the permit back to the semaphore
        semaphore.add_permit(Tracked(self.tok.borrow_mut()));

        // If this is the last sender for this channel, wake the receiver so
        // that it can be notified that the channel is closed.
        if semaphore.is_closed() && semaphore.is_idle() {
            self.chan.wake_rx();
        }
    }
}

impl<T> Receiver<T> {
    pub fn close(&mut self)
        requires old(self).wf(),
        ensures self.wf(), self.chan.rx_fields.rx_closed, self.chan.inner == old(self).chan.inner,
    {
        self.chan.close();
    }
}

} // verus!
}
}
