use std::future::Future;

struct Guard<'a>(&'a mut bool);
impl Drop for Guard<'_> {
    fn drop(&mut self) {
        *self.0 = false;
    }
}

// 🧑 "the human requires proving the real code conforms to the spec, not only a model"
async fn guarded<F: Future<Output = ()>>(flag: &mut bool, future: F) {
    *flag = true;
    let _guard = Guard(flag);
    future.await;
}

fn main() {
    let mut flag = false;
    drop(guarded(&mut flag, std::future::pending::<()>()));
}
