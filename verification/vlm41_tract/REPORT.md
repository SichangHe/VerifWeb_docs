# vlm41_tract: can Verus prove things about real Rust CRDT sync code?
(authored by agents unless marked 🧑)

Short answer: yes for the leaf pieces, at low cost. Doing the Automerge Bloom filter took about 1 hour of agent time, and Verus found a remote-triggerable panic on the first run. The property in the memo ("in sync ⇒ identical; eventual delivery ⇒ in sync") is still far off. It lives in the protocol state machine (sync.rs, about 300 lines of logic over HashSet/HashMap and the change graph), not in any one function. I did not attempt it.

Target: Automerge, rust/automerge/src/sync{.rs,/bloom.rs,/state.rs}, commit 40063d6 (shallow clone in src/automerge).
Why Automerge: its sync code is self-contained (bloom.rs is 160 lines; the sync.rs logic is about 300 lines), with no async and no unsafe. Yrs is the more widely used product (see out/vlm41_crdtuse/REPORT.md, a sibling worker's finding I did not re-check). But its state-vector sync is wired into a larger encoder/decoder and transaction layer, so it is a worse first probe. Loro was not examined.

What was proved (verus/bloom1.rs: "20 verified, 0 errors", 0 assume)
- get_probes, set_bit, get_bit, add_hash, contains_hash, from_hashes: no panic or overflow, given a well-formedness precondition wf(): 0 < bits.len() <= 2^28.
- No false negatives: for every h in hashes, from_hashes(hashes).contains_hash(h) == true, proved end to end through the exec code.
- What this means for sync: a sender never sends again a change that the peer's filter already listed. It does not give convergence. Convergence depends on how false positives are handled, which happens in sync.rs (need/heads re-requests), and that is not proved.

What Verus found (verus/bloom0.rs, the real code without specs)
- Division by zero. In get_probes, modulo = 8 * bits.len(), so modulo is 0 when bits is empty. contains_hash guards only num_entries == 0. BloomFilter::parse takes num_entries and num_bits_per_entry from the wire, and bits_capacity(num_entries=1, num_bits_per_entry=0) = 0.
  - Inference from reading the code, not run: a peer can send a sync message whose `have` contains last_sync=[] and a bloom with num_entries=1, bits_per_entry=0. When the receiver next calls generate_sync_message on a non-empty doc, the path is get_hashes_to_send → contains_hash → `% 0`, and the receiver panics. That is a remote denial of service on any peer that accepts sync messages. Not reproduced: the task rules forbid building the crate.
- u32 overflow in `x + y` and in `8 * bits.len() as u32`. These need a filter of at least 256 MiB, so they are only theoretical. Debug builds panic; release builds wrap.

Changes made to the copied code, and why
1. u32::from_le_bytes → explicit shifts: Verus does not support it. Same value.
2. Added the precondition wf() (bits non-empty, ≤ 2^28 bytes): this is the guard the real code lacks. Without it, the proof fails exactly at the bug above.
3. Vec::with_capacity → Vec::new, and `for _ in 1..n` → while loops: to attach loop invariants.
4. get_mut → index + set: same semantics.
5. A generic ExactSizeIterator<Borrow<ChangeHash>> argument → &Vec<ChangeHash>: generics with traits are awkward to specify in Verus.
6. bits_capacity f64 ceil → integer ceil: Verus has no floats. Same result for the value 10·n/8.
Parsing (leb128) was not copied; the inputs it can produce are taken from reading the code.

What I could not do, and the blockers
- get_hashes_to_send (the have/need computation) and the sync state machine: they rely on std HashSet/HashMap (Verus models these only partly) and on the change graph (a larger module). They also need a spec for the "document" (a set of changes closed under dependencies), which the code never states. Termination and "in sync ⇒ identical" are properties of two State objects plus a network model. That requires writing a protocol model, i.e. the "what the algorithm is supposed to be" spec Ramesh mentioned, before any code proof.
- Sync-loop bugs (#772, #1284) and the Loro issues were not modeled, so I cannot say whether my model reproduces them. The Bloom layer alone cannot explain a loop.
- None of the anticipated blockers (async, unsafe, crate size) appeared in the piece I proved. Hashing was abstracted as given bytes (no SHA proof needed).

Estimate (my guess, low confidence)
- Bloom + have/need computation over an abstract change DAG: 1–2 more agent-days.
- An abstract protocol model in Verus (two peers, lossy reordering network) proving "in sync ⇒ same change set" and convergence under fairness: about 1–2 person-weeks. Connecting that model to the real sync.rs code by refinement: several more weeks. The main cost is writing the spec, not tool limits.

Rerun: timeout 600 /hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus /hdd1/sichangheagent/vl_meeting_work/out/vlm41_tract/verus/bloom1.rs
(The binary prints a harmless GLIBC_2.39 warning; z3 per out/vlm_servo/SUMMARY.md.)
