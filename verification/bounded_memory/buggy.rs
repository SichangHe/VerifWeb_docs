#![feature(allocator_api)]
// Verus proof: quinn-proto incoming DATAGRAM buffer stays within the configured window.
// Executable code between `// BEGIN UPSTREAM (buggy: parent of a3109c34, RUSTSEC-2026-0342)` and `// END UPSTREAM` is quinn main
// c7b46a969cd315398b504792e9e9af6a15a7dcc6 quinn-proto/src/connection/datagrams.rs,
// with only Verus annotation lines added and tracing macros removed (checked by check.sh).
use vstd::prelude::*;

verus! {
mod connection { pub mod datagrams {
use std::collections::VecDeque;
use vstd::prelude::*;
use vstd::layout::size_of as spec_size_of;

// ---- trusted stand-ins for external types (not upstream code) ----
pub struct Bytes { pub v: Vec<u8> }
impl Bytes {
    pub fn len(&self) -> (r: usize) ensures r == self.v.len() { self.v.len() }
}
pub assume_specification<T, A: std::alloc::Allocator>[std::collections::VecDeque::<T, A>::is_empty](q: &std::collections::VecDeque<T, A>) -> (r: bool)
    ensures r == (q@.len() == 0);
pub struct Datagram { pub data: Bytes }
pub struct TransportError;
#[allow(non_snake_case)]
impl TransportError {
    pub fn PROTOCOL_VIOLATION(_r: &'static str) -> Self { TransportError }
}

// ---- specification ----
pub open spec fn S() -> int { spec_size_of::<Datagram>() as int }

pub open spec fn sum_lens(s: Seq<Datagram>) -> int decreases s.len() {
    if s.len() == 0 { 0 } else { s[0].data.v.len() + sum_lens(s.drop_first()) }
}

proof fn lemma_sum_push(s: Seq<Datagram>, x: Datagram)
    ensures sum_lens(s.push(x)) == sum_lens(s) + x.data.v.len()
    decreases s.len()
{
    if s.len() > 0 {
        assert(s.push(x).drop_first() =~= s.drop_first().push(x));
        lemma_sum_push(s.drop_first(), x);
    } else {
        assert(s.push(x).drop_first() =~= s);
    }
}

proof fn lemma_sum_nonneg(s: Seq<Datagram>)
    ensures sum_lens(s) >= 0
    decreases s.len()
{
    if s.len() > 0 { lemma_sum_nonneg(s.drop_first()); }
}

impl DatagramBuffer {
    /// counter equals the sum it summarizes
    pub closed spec fn wf(&self) -> bool {
        self.payload_bytes == sum_lens(self.queue@)
    }
    /// memory this buffer accounts for, in mathematical integers (no saturation)
    proof fn lemma_empty(&self)
        requires self.wf(), self.qlen() == 0,
        ensures self.mem() == 0,
    {
        reveal_with_fuel(sum_lens, 1);
        assert(self.queue@.len() * S() == 0) by (nonlinear_arith) requires self.queue@.len() == 0;
    }
    pub closed spec fn qlen(&self) -> nat { self.queue@.len() }
    pub closed spec fn mem(&self) -> int {
        self.payload_bytes + self.queue@.len() * S()
    }
}

// BEGIN UPSTREAM (buggy: parent of a3109c34, RUSTSEC-2026-0342)
pub struct DatagramState {
    pub(super) incoming: DatagramBuffer,
    pub(super) outgoing: DatagramBuffer,
    pub(super) send_blocked: bool,
}

impl DatagramState {
    pub(super) fn received(
        &mut self,
        datagram: Datagram,
        window: &Option<usize>,
    ) -> (r: Result<bool, TransportError>)
        requires
            old(self).incoming.wf(),
            // environment: Rust objects are at most isize::MAX bytes
            datagram.data.v.len() <= isize::MAX,
            S() <= isize::MAX,
            old(self).incoming.mem() + datagram.data.v.len() + S() <= usize::MAX,
        ensures
            final(self).incoming.wf(),
            // THEOREM: if the old state fit the window, so does the new one
            window.is_some() && old(self).incoming.mem() <= window.unwrap()
                ==> final(self).incoming.mem() <= window.unwrap(),
    {
        let window = match window {
            None => {
                return Err(TransportError::PROTOCOL_VIOLATION(
                    "unexpected DATAGRAM frame",
                ));
            }
            Some(x) => *x,
        };

        if datagram.data.len() > window {
            return Err(TransportError::PROTOCOL_VIOLATION("oversized datagram"));
        }

        let was_empty = self.incoming.is_empty();
        while datagram.data.len() + self.incoming.payload_bytes > window
            invariant
                self.incoming.wf(),
                self.incoming.mem() <= old(self).incoming.mem(),
                datagram.data.v.len() <= window,
                datagram.data.v.len() <= isize::MAX,
                S() <= isize::MAX,
                old(self).incoming.mem() + datagram.data.v.len() + S() <= usize::MAX,
            decreases self.incoming.qlen()
        {
            proof { if self.incoming.qlen() == 0 { self.incoming.lemma_empty(); } }
            self.recv();
        }

        self.incoming.push_back(datagram);
        Ok(was_empty)
    }

    pub(super) fn recv(&mut self) -> (r: Option<Bytes>)
        requires old(self).incoming.wf(),
        ensures
            final(self).incoming.wf(),
            old(self).incoming.qlen() > 0 ==> final(self).incoming.qlen() == old(self).incoming.qlen() - 1,
            old(self).incoming.qlen() == 0 ==> final(self).incoming.qlen() == 0,
            final(self).incoming.mem() <= old(self).incoming.mem(),
    {
        let x = self.incoming.pop_front()?.data;
        Some(x)
    }
}

pub struct DatagramBuffer {
    queue: VecDeque<Datagram>,
    payload_bytes: usize,
}

impl DatagramBuffer {
    fn push_back(&mut self, datagram: Datagram)
        requires
            old(self).wf(),
            old(self).mem() + datagram.data.v.len() + S() <= usize::MAX,
        ensures
            final(self).wf(),
            final(self).mem() == old(self).mem() + datagram.data.v.len() + S(),
    {
        proof {
            lemma_sum_nonneg(self.queue@);
            lemma_sum_push(self.queue@, datagram);
            assert(self.queue@.len() * S() >= 0) by (nonlinear_arith) requires S() >= 0;
            assert((self.queue@.len() + 1) * S() == self.queue@.len() * S() + S()) by (nonlinear_arith);
        }
        self.payload_bytes += datagram.data.len();
        self.queue.push_back(datagram);
    }

    fn pop_front(&mut self) -> (r: Option<Datagram>)
        requires old(self).wf(),
        ensures
            final(self).wf(),
            old(self).queue@.len() > 0 ==> final(self).queue@ == old(self).queue@.drop_first(),
            old(self).queue@.len() == 0 ==> final(self).queue@ == old(self).queue@ && r.is_none(),
            final(self).mem() <= old(self).mem(),
    {
        proof { if self.queue@.len() > 0 { lemma_sum_nonneg(self.queue@.drop_first()); } }
        let datagram = self.queue.pop_front()?;
        proof { assert(old(self).queue@.drop_first() =~= self.queue@); }
        self.payload_bytes -= datagram.data.len();
        proof {
            assert((self.queue@.len() + 1) * S() == self.queue@.len() * S() + S()) by (nonlinear_arith);
        }
        Some(datagram)
    }

    fn memory_used(&self) -> (r: usize)
        requires self.wf(), self.mem() <= usize::MAX,
        ensures r == self.mem(),
    {
        proof {
            lemma_sum_nonneg(self.queue@);
            assert(self.queue@.len() * S() >= 0) by (nonlinear_arith) requires S() >= 0;
        }
        self.payload_bytes
            .saturating_add(self.queue.len() * size_of::<Datagram>())
    }

    pub(super) fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }
}
// END UPSTREAM
} }

fn main() {}
} // verus!
