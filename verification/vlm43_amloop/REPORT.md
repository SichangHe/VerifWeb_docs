# vlm43_amloop: the automerge sync loop on the real crate
(authored by agents unless marked 🧑)

Short answer: reproduced. With the published crate automerge 0.10.0, losing one message makes two peers fail to converge, in both ways the vlm42 model predicted. The fix from the vlm43_amlive model (on timeout, clear `sent_hashes` and `in_flight`) makes both cases converge. Resetting the whole sync State, the remedy the maintainers document, also works.

## Setup (fact)
- Own Cargo project repro/ depending on `automerge = "=0.10.0"`; nothing from upstream was built or run. Crate source unpacked in crate_src/ for reading only.
- Each round: both peers call `generate_sync_message`; messages go into my own queues; a drop predicate may lose a message; then each peer receives its queue. Bounded at 40 rounds. Output: run_output.txt.

## Results (fact, from run_output.txt)
- lost change (issue #772 setup: diverged docs, A's message carrying its change is dropped), no fix: "NOT CONVERGED after 40 rounds: 42 msgs sent, 1 dropped, silent for last 0 rounds, heads equal=false". The peers keep exchanging messages forever.
- both first messages lost, no fix: "NOT CONVERGED after 40 rounds: 2 msgs sent, 2 dropped, silent for last 39 rounds, heads equal=false". Both peers go silent forever (the in_flight deadlock).
- timeout fix (every 5 rounds, a peer whose last-received `their_heads` differ from its own heads clears `sent_hashes` and sets `in_flight = false`): lost change "CONVERGED after 7 rounds"; both lost "CONVERGED after 8 rounds".
- `State::new()` reset under the same trigger: converges in 8 rounds in both.
- Caveat: the timeout trigger is my choice. It uses only local state, but its period is arbitrary, and I tested only these two scenarios.

## Code lines (crate 0.10.0)
- Cause of the loop, https://docs.rs/crate/automerge/0.10.0/source/src/sync.rs#212 : `.filter(|hash| !sync_state.sent_hashes.contains(hash))`
- Cause of the deadlock, sync.rs lines 236-238: `if sync_state.in_flight { return None; }`, inside `if heads_unchanged && sync_state.have_responded`; `in_flight = true` at line 275, cleared only on receive at line 379.
- Both fields are public (src/sync/state.rs lines 45, 54), so the fix can be applied by callers without patching the crate.

## Issues (quotes)
- https://github.com/automerge/automerge/issues/772 (open, 2023-10-17), author's text: "the receiver keeps asking for the changes that were in the dropped message and the sender keeps not sending them because it thinks it has already sent them". Member ept: "I think it would be preferable to add a sequence number to messages, and reject non-consecutive sequence numbers."
- https://github.com/automerge/automerge/issues/1284 (open, 2026-02-13), collaborator alexjg: "The sync protocol requires a reliable in-order stream, I.e. you need to reset the sync state if there could have been a dropped message."

## Interpretation
- Inference: this is documented, intended behavior rather than a hidden bug; the timeout fix is a lighter form of the documented reset (it keeps shared_heads and their_heads). Whether that saving matters in practice: I don't know.
- Nothing was posted. No papers relied on.
