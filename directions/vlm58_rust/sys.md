scope: non-web security-relevant Rust systems; 2 candidates ranked + 1 weak; searched Firecracker, rust-vmm, Rust Binder, sudo-rs only
(authored by agents unless marked 🧑)
not covered (no time, no evidence gathered): crosvm/Cloud Hypervisor own advisories, cargo/uv, libsignal, sequoia, youki, Windows kernel; Wasmtime already in vlm48 a.md
labels: [F]=fact, [I]=inference, [O]=opinion
caveat: WebFetch limits quotes to 125 chars, so quotes below are short; full text at URL

1 rust-vmm guest-memory + virtqueue layer (vm-memory, virtio-queue, vmm-sys-util) -- best candidate
 users
  [F] crates.io API (curl, 2026-11-19): vm-memory 10,316,564 total / 3,512,520 recent; virtio-queue 5,066,100 / 2,230,426 (recent); vmm-sys-util 15,312,553 / 4,390,969
  [F] https://github.com/firecracker-microvm/firecracker README: "efficiency of services like [AWS Lambda](https://aws.amazon.com/lambda/) and [AWS Fargate]"
  [F] rust-vmm crates are shared by Firecracker, crosvm, Cloud Hypervisor (rust-vmm README; not re-quoted)
 recurring failure class: guest-controlled value is validated once, or a bounds contract is assumed but not enforced, then used to index host-visible memory
  [F] Firecracker CVE-2026-5747, https://github.com/firecracker-microvm/firecracker/security/advisories/GHSA-776c-mpj7-jm3r
   "a root-privileged guest... modify virtio queue configuration registers after device activation"
   "Out-of-bounds writes up to 524,284 bytes beyond the virtio queues"
   CVSS v4 8.7 High; affected 1.13.0-1.14.3, 1.15.0
  [F] vm-memory CVE-2023-41051 / RUSTSEC-2023-0056, https://rustsec.org/advisories/RUSTSEC-2023-0056.html
   title: "Default functions in VolatileMemory trait lack bounds checks, potentially leading to out-of-bounds memory accesses"
   present from 0.1.0, fixed 0.12.2 (search-result summary; open page to quote more)
  [F] vmm-sys-util CVE-2023-50711 / GHSA-875g-mfp6-g7f9
   "FamStructWrapper::deserialize ... can lead to out of bounds memory accesses" (search summary: header length not checked against flexible array length)
  [F] Firecracker CVE-2026-122192, https://github.com/firecracker-microvm/firecracker/security/advisories/GHSA-48ww-rqpp-2mgm
   "can leave part of the guest memory range unmapped while Firecracker keeps running" (failed discard in balloon/virtio-mem, snapshot File backend)
   different sub-class: memory-mapping state machine, not bounds
 theorem (proposed)
  [I] for every guest-writable register/descriptor state reachable by any guest action sequence (incl. after activation, after snapshot restore), every host access made by the queue/memory layer lies inside the region granted to that device, or the call returns Err
  [I] formally: GuestMemory::get_slice(a,n) = Ok(s) implies s.len==n and [a,a+n) within a mapped region; queue iterators only ever call it with values derived from validated fields; validated fields are immutable (or revalidated) after activate()
  [I] second theorem: mapping state machine (mmap/discard/restore) never leaves a hole inside a live region; failure => abort
 why proof beats testing
  [I] 5747 was a time-of-check/time-of-use over guest actions after init; fuzzers rarely drive that ordering; a proof quantifies over all guest register write sequences
  [I] 41051 depends on every downstream impl of a trait obeying a doc comment; a proof obligation on the trait (a Verus spec) turns the comment into a checked contract
 tool: Verus (Rust, trait specs, ghost state for permissions); needs unsafe pointer/mmap model (Verus has raw-pointer permissions, vstd)
 closest prior work
  [F, from rust-vmm search result, not verified by me] virtio-queue README claims formal proofs of conformance of queue to the virtio spec (Kani); Firecracker also uses Kani (my memory [I])
  so "we verify virtqueue" is NOT new; to be new, must be: whole guest-memory+device-state invariant under post-activation guest writes, in Verus rather than bounded Kani, and snapshot/restore
  need to check what exactly Kani harnesses cover and their bounds (first thing to do)
  related [I, from memory]: VeriSMo (Verus, SVSM for confidential VMs), seL4/CertiKOS hypervisors; CompCert-style verified virtio drivers
  scholar queries: "verified virtio device emulation"; "formally verified virtqueue Kani"; "Verus hypervisor"; "verified VMM guest memory isolation"; "VeriSMo Verus"; "Firecracker formal verification"; "Kani Firecracker virtio proof"
 what changes for users
  [I] cloud providers running untrusted code (Lambda, Fargate, Kata) get a machine-checked claim that a device bug cannot write outside the guest grant; shrinks reliance on guest-escape bug bounties
 risk [O]: advisors may call this "AWS already does it (Kani)"; edge is weak unless Verus gives unbounded proofs plus post-activation/snapshot coverage. Also Firecracker is not a "hot" area but AWS has money

2 Rust Binder in Linux kernel (drivers/android/binder/*.rs) -- interesting, narrow
 users
  [F] merged in v6.18-rc1 (search-result summary: "Rust Binder was merged into Linux v6.18-rc1"); Binder is the IPC of every Android device [I: general knowledge, no quote fetched]
  need a sourced device count (Android active devices) -- not collected
 recurring failure class: unsafe intrusive-list / lock / refcount invariants that safe Rust does not check
  [F] CVE-2025-68260 (first Rust CVE in kernel), https://ratatoskr.run/linux-cve-announce/2025/12/8046848
   unsafe call assumed a NodeDeath is "never inserted into the death list of any node other than its owner"
   "this leads to memory corruption of the prev/next pointers"
   fixed 6.18.1; introduced 6.18 (eafedbc7c050)
  [F] CVE-2025-71181: deadlock in rust_shrink_free_page(), caused by a list_lru locking change not accounted for in forward-port (search summary, unverified text)
  [F] CVE-2026-64466: leak from refcount cycle; "clear the freeze listener when a node is removed" (search summary, unverified text)
  [F] C Binder UAF CVE-2026-64468 shows same domain failing in C (not Rust; context only)
 theorem (proposed)
  [I] every unsafe list::remove in Binder is called with the list's lock held and the element in that list (membership + lock-ownership invariant); node release never leaves a death in a list not under its lock
  [I] liveness: no lock-order cycle, so no deadlock
 why proof beats testing: [I] races are rare schedules; syzkaller/KCSAN sees only explored interleavings
 tool: Verus has verified linked lists/concurrency (e.g. via tracked permissions) [I]; kernel Rust uses its own `kernel::list` abstraction, so the unit to verify is that abstraction + its Binder users
 closest prior work: scholar queries "verified intrusive linked list Rust Verus"; "Rust for Linux verification Verus"; "Binder formal verification"; "RustBelt intrusive list"; "Atmosphere verified OS Verus"
 what changes for users: [I] Android vendors could ship Rust Binder without a stream of kernel-crash CVEs; value is small today (bugs are DoS/crash, 3 CVEs in months)
 risk [O]: (a) likely seen as "single bugs"; (b) the real contribution would be a verified list abstraction in kernel, which Rust-for-Linux folks may or may not accept; (c) no sourced user count yet

3 sudo-rs -- weak, listed to document rejection
  users: Ubuntu 25.10 ships it [F, search summary of Phoronix: "Ubuntu 25.10 is also seeing a stable release update"]; no download number gathered
  failures [F, all Low/Medium]: CVE-2025-46717 (existence of files in inaccessible folders via sudo --list), CVE-2025-46718 (enumerate others' privileges), CVE-2025-64170 (password keystrokes echoed after timeout), CVE-2025-64517 (timestamp recorded invoking user's UID instead of authenticated-as UID)
  [O] reject: bugs are policy/logic leaks, not a memory-safety class; a "verified sudoers semantics" is plausible but is a Rust port of C sudo (human: ports don't count) and overlaps the "permission checks" area the human called too hot

recommendation [O]: pursue 1, after checking Kani coverage; 2 only as a sub-case of "verified unsafe abstractions for kernel Rust"
