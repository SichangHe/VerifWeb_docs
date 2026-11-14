use std::future::Future;
#[allow(unused_imports)]
use vstd::prelude::*;
pub trait F<T> { fn f(x: &T) -> impl Future + Send; }
struct E;
struct S;
impl F<E> for S { async fn f(_x: &E) {} }
fn main() {}
