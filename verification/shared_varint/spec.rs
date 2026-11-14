// Shared specification of the QUIC variable-length integer, RFC 9000 Section 16:
// "The QUIC variable-length integer encoding reserves the two most significant bits
// of the first byte to encode the base-2 logarithm of the integer encoding length in
// bytes. The integer value is encoded on the remaining bits, in network byte order."
// Used unchanged by every implementation proof in this directory.
use vstd::prelude::*;

verus! {

// ---- specification ----

/// big-endian (network byte order) value of a byte sequence
pub open spec fn be(s: Seq<u8>) -> nat decreases s.len() {
    if s.len() == 0 { 0 } else { be(s.drop_last()) * 256 + s.last() as nat }
}

/// encoding length in bytes selected by the two most significant bits of the first byte
pub open spec fn tag_len(first: u8) -> nat {
    let t = first >> 6u8;
    if t == 0 { 1 } else if t == 1 { 2 } else if t == 2 { 4 } else { 8 }
}

/// 2^(8 * len - 2): values representable in `len` bytes
pub open spec fn cap(len: nat) -> nat {
    if len == 1 { 0x40 } else if len == 2 { 0x4000 } else if len == 4 { 0x4000_0000 } else { 0x4000_0000_0000_0000 }
}

/// Decoding the front of `s`: None if `s` is too short, else (value, bytes consumed).
/// The value is the big-endian integer of the first `len` bytes with the top two bits removed.
pub open spec fn decode(s: Seq<u8>) -> Option<(nat, nat)> {
    if s.len() == 0 { None } else {
        let len = tag_len(s[0]);
        if s.len() < len { None } else { Some((be(s.take(len as int)) % cap(len), len)) }
    }
}

/// shortest length that can encode `v` (both implementations always emit this length)
pub open spec fn min_len(v: nat) -> nat {
    if v < 0x40 { 1 } else if v < 0x4000 { 2 } else if v < 0x4000_0000 { 4 } else { 8 }
}

pub open spec fn max_var_int() -> nat { 0x3fff_ffff_ffff_ffff }

// ---- trusted specifications of Rust std functions (shared trusted base) ----

pub assume_specification[ u16::from_be_bytes ](b: [u8; 2]) -> (r: u16)
    ensures r as nat == be(b@);
pub assume_specification[ u32::from_be_bytes ](b: [u8; 4]) -> (r: u32)
    ensures r as nat == be(b@);
pub assume_specification[ u64::from_be_bytes ](b: [u8; 8]) -> (r: u64)
    ensures r as nat == be(b@);
pub assume_specification[ u16::to_be_bytes ](v: u16) -> (r: [u8; 2])
    ensures be(r@) == v as nat;
pub assume_specification[ u32::to_be_bytes ](v: u32) -> (r: [u8; 4])
    ensures be(r@) == v as nat;
pub assume_specification[ u64::to_be_bytes ](v: u64) -> (r: [u8; 8])
    ensures be(r@) == v as nat;

#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExTryFromSliceError(std::array::TryFromSliceError);

pub assume_specification<'a, T: Copy, const N: usize>[ <[T; N] as std::convert::TryFrom<&'a [T]>>::try_from ](s: &[T]) -> (r: Result<[T; N], std::array::TryFromSliceError>)
    ensures s@.len() == N ==> (r matches Ok(a) && a@ == s@);


/// Stand-in for std's `TryInto` on slice-to-array conversion. Importing it shadows the
/// prelude trait, so upstream `slice.try_into()` calls resolve here. Reason: vstd gives
/// std's blanket `try_into` no usable contract for arrays, and the orphan rule forbids adding one.
pub trait TryInto<A>: Sized {
    spec fn spec_ok(self, r: Result<A, std::array::TryFromSliceError>) -> bool;
    fn try_into(self) -> (r: Result<A, std::array::TryFromSliceError>) ensures Self::spec_ok(self, r);
}
impl<'a, T: Copy, const N: usize> TryInto<[T; N]> for &'a [T] {
    open spec fn spec_ok(self, r: Result<[T; N], std::array::TryFromSliceError>) -> bool {
        self@.len() == N ==> (r is Ok && r->Ok_0@ == self@)
    }
    fn try_into(self) -> (r: Result<[T; N], std::array::TryFromSliceError>)
    { <[T; N] as std::convert::TryFrom<&'a [T]>>::try_from(self) }
}

pub assume_specification<T: std::fmt::Display>[ core::panicking::unreachable_display ](x: &T) -> !
    requires false;

// ---- shared lemmas ----

/// splitting off the first byte: be(s) = s[0] * 256^(n-1) + be(rest)
pub proof fn lemma_be_first(s: Seq<u8>)
    requires s.len() >= 1,
    ensures be(s) == s[0] as nat * pow256((s.len() - 1) as nat) + be(s.drop_first()),
    decreases s.len()
{
    if s.len() == 1 {
        assert(s.drop_last().len() == 0);
        assert(s.drop_first().len() == 0);
        assert(be(s.drop_first()) == 0);
        assert(be(s.drop_last()) == 0);
        assert(be(s) == s.last() as nat);
        assert(pow256(0) == 1);
    } else {
        let t = s.drop_last();
        lemma_be_first(t);
        assert(t.drop_first() =~= s.drop_first().drop_last());
        assert(s.drop_first().last() == s.last());
        let n = (s.len() - 2) as nat;
        let p = pow256(n);
        assert(pow256(n + 1) == 256 * p);
        let a = s[0] as nat; let u = be(t.drop_first()); let l = s.last() as nat;
        assert(t[0] == s[0]);
        assert(t.len() - 1 == n);
        assert(be(t) == a * p + u);
        assert(be(s) == be(t) * 256 + l);
        assert(be(s.drop_first()) == be(s.drop_first().drop_last()) * 256 + l);
        assert(be(s.drop_first()) == u * 256 + l);
        assert((a * p + u) * 256 + l == a * (256 * p) + (u * 256 + l)) by (nonlinear_arith);
    }
}

pub open spec fn pow256(n: nat) -> nat decreases n { if n == 0 { 1 } else { 256 * pow256((n - 1) as nat) } }

/// two sequences with equal contents have equal be
pub proof fn lemma_be_ext(a: Seq<u8>, b: Seq<u8>) requires a =~= b ensures be(a) == be(b) {}

/// removing the top two bits of the first byte takes the value modulo cap:
/// be(s) % (64 * 256^(n-1)) == (s[0] % 64) * 256^(n-1) + be(rest)
pub proof fn lemma_be_mod_first(s: Seq<u8>)
    requires s.len() >= 1,
    ensures ({ let m = pow256((s.len() - 1) as nat);
        be(s) % (64 * m) == (s[0] as nat % 64) * m + be(s.drop_first()) }),
{
    let m = pow256((s.len() - 1) as nat);
    lemma_be_first(s);
    lemma_be_lt_pow(s.drop_first());
    lemma_pow256_pos((s.len() - 1) as nat);
    let a = s[0] as nat; let r = be(s.drop_first());
    let q = a / 64; let b = a % 64;
    assert(a == 64 * q + b && b < 64);
    assert(a * m + r == q * (64 * m) + (b * m + r)) by (nonlinear_arith) requires a == 64 * q + b;
    assert(64 * m > 0);
    assert(b * m + r < 64 * m) by (nonlinear_arith) requires b < 64, r < m;
    vstd::arithmetic::div_mod::lemma_fundamental_div_mod_converse(
        (a * m + r) as int, (64 * m) as int, q as int, (b * m + r) as int);
}

pub proof fn lemma_pow256_pos(n: nat) ensures pow256(n) > 0 decreases n { if n > 0 { lemma_pow256_pos((n - 1) as nat); } }

pub proof fn lemma_be_lt_pow(s: Seq<u8>) ensures be(s) < pow256(s.len()) decreases s.len() {
    if s.len() > 0 {
        lemma_be_lt_pow(s.drop_last());
        let n = (s.len() - 1) as nat;
        let p = pow256(n); let b = be(s.drop_last()); let l = s.last() as nat;
        assert(b * 256 + l < 256 * p) by (nonlinear_arith) requires b < p, l < 256;
    }
}

/// tag value (top two bits) for each encoding length
pub open spec fn tag_of(len: nat) -> nat { if len == 1 { 0 } else if len == 2 { 1 } else if len == 4 { 2 } else { 3 } }

/// Encoding direction, shared: `len` bytes whose big-endian value is tag * cap + x decode to x.
pub proof fn lemma_encoded(b: Seq<u8>, x: nat, len: nat)
    requires len == 1 || len == 2 || len == 4 || len == 8, b.len() == len, x < cap(len),
        be(b) == tag_of(len) * cap(len) + x,
    ensures decode(b) == Some((x, len)),
{
    reveal_with_fuel(pow256, 8);
    lemma_be_first(b);
    lemma_be_lt_pow(b.drop_first());
    let m = pow256((len - 1) as nat);
    let b0 = b[0];
    let r = be(b.drop_first());
    let t = tag_of(len);
    assert(cap(len) == 64 * m);
    // b0 * m + r == t * 64 * m + x with r < m and x < 64m  ==>  b0 / 64 == t
    assert(t * 64 <= b0 && b0 < t * 64 + 64) by (nonlinear_arith)
        requires b0 as nat * m + r == t * (64 * m) + x, r < m, x < 64 * m, m > 0, r >= 0;
    assert(b0 >> 6u8 == b0 / 64) by (bit_vector);
    assert(b.take(len as int) =~= b);
    vstd::arithmetic::div_mod::lemma_fundamental_div_mod_converse(be(b) as int, cap(len) as int, t as int, x as int);
}

} // verus!
