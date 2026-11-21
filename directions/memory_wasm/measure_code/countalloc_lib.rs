//! Counts live and peak heap bytes requested from the global allocator.
//! Single-threaded wasm, so relaxed atomics suffice.
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicUsize, Ordering::Relaxed};
use wasm_bindgen::prelude::wasm_bindgen;

pub struct Counting;
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static N_LIVE: AtomicUsize = AtomicUsize::new(0);

fn add(n: usize) {
    let live = LIVE.fetch_add(n, Relaxed) + n;
    PEAK.fetch_max(live, Relaxed);
}

unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        let p = System.alloc(l);
        if !p.is_null() {
            add(l.size());
            N_LIVE.fetch_add(1, Relaxed);
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        System.dealloc(p, l);
        LIVE.fetch_sub(l.size(), Relaxed);
        N_LIVE.fetch_sub(1, Relaxed);
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, new_size: usize) -> *mut u8 {
        let q = System.realloc(p, l, new_size);
        if !q.is_null() {
            LIVE.fetch_sub(l.size(), Relaxed);
            add(new_size);
        }
        q
    }
}

#[wasm_bindgen]
pub fn heap_live_bytes() -> usize { LIVE.load(Relaxed) }
#[wasm_bindgen]
pub fn heap_peak_bytes() -> usize { PEAK.load(Relaxed) }
#[wasm_bindgen]
pub fn heap_n_live_allocs() -> usize { N_LIVE.load(Relaxed) }
