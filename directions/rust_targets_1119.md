# Widely used Rust targets for a verified, principled fix (after Nov 19 meeting)
(authored by agents unless marked 🧑)

Asked by Ramesh (Nov 19, L467): "Is there a widely used Rust-based software that may or may not be web-related? ... Or some networking software, anything like that." and (L490-493) "not so much ... bugs and bug finding ... but sort of what a principled fix to all of this might be".
Evidence (users with sources, bug quotes with links, theorems): vlm58_rust/net.md and vlm58_rust/sys.md. Prior work (9 Google Scholar queries with as_ylo=2022, no CAPTCHA): vlm58_rust/scholar.md. The ranking is OPINION. Verus is the assumed tool. Snippets in scholar.md are Scholar excerpts; papers were not read in full except arXiv 2610.09198.

## 1. rust-vmm guest memory and virtqueue (shared by Firecracker, crosvm, Cloud Hypervisor)
- users: AWS Lambda/Fargate run on Firecracker; rust-vmm crate downloads in sys.md
- failure class (FACT): values controlled by the guest are checked once or only by convention; CVE-2023-41051 (vm-memory), CVE-2023-50711 (vmm-sys-util), Firecracker CVE-2026-5747
- theorem: for any sequence of guest writes, no host memory access leaves the region granted to the device
- prior work (FACT): the virtio-queue README claims Kani proofs, but only 2 are enabled, both `unwind(0)` on a single-region stub; `verify_add_used` is disabled (vm-virtio issue #373). Related work: VeriSMo (Verus, OSDI'24), Kani on Firecracker (ICSE-SEIP'22), MicroVMM (not read)
- new: unbounded proofs over multi-region memory, guest writes after activation, and snapshot/restore
- for users: a guest-to-host escape through this layer is ruled out, not only tested. This is the security angle Calvin asked for.

## 2. Verified multi-threaded (work-stealing) async runtime
- users: tokio has 1.22B crates.io downloads; nearly every Rust network service runs on it
- prior work (FACT): Lion (SOSP'26, Verus) verifies a single-threaded runtime compatible with Tokio. It says "Extending the verification to cover cross-thread work-stealing ... is a challenging direction for future work".
- prior work (FACT): arXiv 2610.09198 (ESOP'27) checks liveness of runtime components; its model "cannot handle tokio's fairness mechanism"
- prior work (FACT): verified work-stealing deques exist without a runtime (BWoS OSDI'23; Chase-Lev in separation logic; a verified OCaml 5 scheduler, PACMPL'26)
- risks: Lion reports that most confirmed Tokio liveness bugs are in single-threaded logic (FACT), so this fix ends only a minority of the observed bugs. Verus support for weak-memory atomics is unknown (ASSUMPTION).
- matches the advisors' path (Nov 19): runtime first, then verified networking libraries on top

## 3. Memory bounds for QUIC/HTTP2 state machines (quinn-proto 444M downloads, h2 997M)
- failure class: a hostile peer makes the endpoint use unbounded memory (bug quotes reused from vlm48_dirs/a.md and not re-checked)
- theorem: endpoint memory ≤ f(configured limits), whatever the peer sends
- prior work: the Scholar search was shallow; it found testing and bug-finding papers only (e.g. NDSS'26)
- overlaps "bounded memory vs hostile peer", which the human called "worth exploring"

## Weaker or rejected
- Hickory DNS parsing and DNSSEC: arXiv 2512.11431 "Proving DNSSEC Correctness" is close; the resolver deployment count is unsourced
- cancellation safety (Pingora, hyper): the only prior work found tests by injecting cancellations (Joshi et al. 2026); no proof-based work found; the theorem is not yet sharp
- Rust Binder (Linux kernel): mostly crashes; user count unsourced; better framed as a verified intrusive-list abstraction
- sudo-rs: a port of C sudo and a permission-check tool; both are rejection categories the human already set
- boringtun (small), ntpd-rs (no bug class found), linkerd2-proxy (its issue tracker is disabled, so no bug evidence)

## Not covered
- crosvm/Cloud Hypervisor advisories, cargo/uv, libsignal, sequoia-pgp, youki, Windows kernel Rust
- Scholar queries not run: EverParse DNS, Iris/RustBelt on tokio, Kani on s2n-quic, IVy on QUIC
