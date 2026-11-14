use vstd::prelude::*;
verus! {
trait Service { async fn one() -> (r: u64) ensures r == 1; }
struct Server;
impl Service for Server { async fn one() -> u64 { 1 } }
async fn caller() { let r = Server::one().await; assert(r == 1); }
}
fn main() {}
