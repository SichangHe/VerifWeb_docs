# vlm48_amnet: automerge sync stalls over an emulated network, with real samod peers
(authored by agents unless marked 🧑)

Short answer. Fact: two real samod Repos, joined by an in-memory link that drops or reorders chosen frames, reach the #772 stall (lost change-carrying message; both first messages lost). Both stalls disappear with the `on_timeout` fix. Fact: the no-loss Bloom + reordering stuck state of the bare crate is NOT reached in samod (it recovers without the fix); samod regenerates after every received message. Rates are below.

Fork: `/hdd1/sichangheagent/vl_meeting_work/out/vlm47_amcode/alexjg--samod`, new local branch `vl-net-tests` (from `vl-verus`), commit `ff3ff7c`, pushed to https://github.com/SichangHe/alexjg--samod/tree/vl-net-tests (fork only; nothing filed upstream).

## What was built
- Fix in samod (opt-in, default off): `RepoBuilder::with_sync_timeout(Duration)`. Hub tick (100 ms) counts; every N ticks the hub sends `SyncTimeout` to every doc actor; the actor calls `sync_state.on_timeout()` on each connection, then the normal generate loop runs. Files: `samod-core/src/actors/hub/state.rs`, `.../document/{document_actor,peer_doc_connection,actor_input}.rs`, `messages/hub_to_doc_msg.rs`, `samod/src/{builder,lib}.rs`. It fires on a fixed period, not "a reply is overdue" per connection (inference: cheaper to build; costs chatter only when out of sync, since generate returns None when in sync).
- `Cargo.toml` has `[patch.crates-io] automerge = { path = "../automerge--automerge/rust/automerge" }`; `cargo tree -p samod -i automerge` shows `automerge v0.12.0 (.../automerge--automerge/rust/automerge)`.
- `samod/tests/netem.rs`: relay between two Repos. Per sync/request frame, a policy returns Deliver, Drop, Delay(d) (reorders) or Hold (test releases it later). Handshake frames always pass. Frames are identified by the CBOR bytes `type`=`sync`/`request`.
- `samod/tests/net_stall.rs`: tests and sweeps. Setup per run: A creates a doc, B finds it over a clean link, both disconnect (fresh `State` on reconnect), A and B each make one edit, reconnect over the emulated link. Stall = heads not equal and complete within 3 s (tests) / 4 s (sweeps).

## Commands and outputs
Tests (debug): `cargo test -p samod --offline --features tokio --test net_stall -- --nocapture`

    test lost_change_message_stalls_without_fix_and_recovers_with_fix ... ok
    test both_first_messages_lost ... ok
    test bloom_false_positive_with_reordering_no_loss_is_masked_by_eager_generation ... ok
    test result: ok. 4 passed; 0 failed; 2 ignored

Each test runs the scenario twice in one test: without timeout it asserts the stall, with `with_sync_timeout(100ms)` it asserts convergence. "Fails before the fix" = the no-fix half of each test passes only if the stall happens; before the fix hook existed the file does not compile (`with_sync_timeout`), and with the hook off the convergence assertion would fail. I did not run a separate "revert the hook" build (not done).

How the stall is reached (selective drop). Single-drop exploration (`explore_single_drop`, no fix): frames per direction counted from 0; each direction exchanges #0 (179 B), #1 (301 B, carries the changes), #2 (241 B).

    drop AtoB #0: converged=true      drop BtoA #0: converged=true
    drop AtoB #1: converged=false     drop BtoA #1: converged=false
    drop AtoB #2: converged=true      drop BtoA #2: converged=true
    drop AtoB #3: converged=true      drop BtoA #3: converged=true

- #772 case 1: drop one change-carrying frame (A->B #1) and the docs never converge. Fact (link log, no fix): afterwards the peers do not go silent; they ping-pong 238 B / 233 B frames forever ("6301 frames" in 3 s) with nothing new. With fix, 97-101 frames until convergence. This livelock (receiver keeps asking, sender keeps answering without the changes) differs from "silent"; I did not check whether that matches the report in #772 exactly.
- #772 case 2: drop A->B #0 and B->A #0. Without fix: stall (asserted). With fix: converges. The silent-forever claim is not separately measured (I assert only non-convergence).
- Bloom / no-loss (`bloom_run`): schedule = hold B->A #0 until after #1, hold A->B #1 (ack, heads=[c0]) until after A's next message; A's two edits are searched so c1 is a false positive of B's Bloom filter and c2 a miss (3 to 88 candidate edits). Link log:

      BtoA #0 sync 177B -> Hold      AtoB #0 sync 176B -> Deliver
      BtoA #1 sync 298B -> Deliver   AtoB #1 sync 202B -> Hold
      AtoB #2 sync 299B -> Deliver   BtoA #2 sync 200B -> Deliver
      AtoB #3 sync 332B -> Deliver   BtoA #3 sync 202B -> Deliver

  Fact: converges without the fix. Reason (read from `rust/automerge/src/sync.rs` 252-257 and 401, plus the log): B's receive of A->B #2 clears `in_flight`, and samod generates immediately, so B sends `need=[c1]` (BtoA #2) and A replies with c1 (AtoB #3). In the bare-crate trace B does not generate between the two receives. Inference: eager generate-after-receive masks this stuck state in samod for all two-peer schedules; not proved, only the schedules below were tried.

Sweeps (release build, one core via cpu-run LOW; raw files `sweep_plain.txt`, `sweep_bloom.txt`, `bloom_fp_rate.txt`). Command:

    SWEEP_N=500 SWEEP_PAR=25 SWEEP_CFG="0,0;0,0.5;0.02,0;0.05,0;0.1,0;0.2,0;0.1,0.5" cpu-run LOW -c 1 -o vlm46_amfollow.md -e 15min -- $BIN sweep --ignored --nocapture

Random policy per frame: drop with prob `loss`; else with prob `reorder` delay by 5-59 ms; else deliver. Scenario "plain" (both edit). 500 runs per row, stalled = not converged after 4 s:

    loss  reorder  no fix            with fix (100 ms)
    0     0        0/500             0/500
    0     0.5      0/500             0/500
    0.02  0        17/500 (3.4%)     0/500
    0.05  0        54/500 (10.8%)    0/500
    0.1   0        109/500 (21.8%)   0/500
    0.2   0        194/500 (38.8%)   0/500
    0.1   0.5      102/500 (20.4%)   0/500

Fact: reorder alone (50% of frames delayed, no loss) never stalls in 500 runs; every stall needs a lost frame.

Scenario "bloom" (B has a new change; A makes the FP+miss edit pair at a random 0-80 ms after connect; 300 runs per row):

    loss  reorder  no fix            with fix
    0     0        0/300             0/300
    0     0.5      0/300             0/300
    0     1        0/300             0/300
    0.05  0        37/300 (12.3%)    0/300
    0.1   0.5      68/300 (22.7%)    0/300

Fact: with no loss, forced false positive, 0 stalls in 900 runs. With loss the rate matches plain loss (about one drop of the change-carrying frame suffices); I did not show that the Bloom false positive adds stalls beyond plain loss.

How often the false positive arises (`bloom_false_positive_rate`, random hashes vs filters of n random entries, 2,000,000 trials each; filter built by `BloomFilter::from_hashes`):

    entries=1 rate=0.01077   entries=2 rate=0.01683   entries=3 rate=0.01422   entries=4 rate=0.01620
    entries=6 rate=0.00954   entries=8 rate=0.01195   entries=16 rate=0.01010

Fact: about 1% per new change (spread between rows is sampling noise from only 20,000 filters per row; theory for 10 bits/entry, 7 probes is about 0.8%). In the sweeps a FP edit was found after a median of 51-62 candidate edits (about 1.7%, the same order). So a FP is rare per change but not negligible; the full no-loss stuck state additionally needs the reorderings, which samod's eager generation defeats.

## Facts vs inferences, unknowns
- Fact: #772 loss stalls reproduce over a real samod stack; selective drops of one frame suffice; the timeout hook (100 ms period) left 0 stalls in 3,100 lossy runs (plain 2,500 + bloom 600; tables above), against 574 stalls in the same 3,100 without it (plain 476/2,500, bloom 105/600).
- Fact: no-loss reordering stall not reproduced in samod. I don't know whether another schedule (more peers, three-way topology, policy-pending buffering in samod, multi-doc) reaches it.
- Inference: real networks use TCP/WebSocket (reliable, in-order); drops and reorders in these tests are not possible there without a disconnect, and a disconnect makes a fresh `State`. So these stalls matter only for lossy transports (the abstract link here), not samod over TCP. I did not test mid-connection frame loss on a TCP path.
- I don't know the stall rates for per-message loss at other timeouts; only 100 ms tested. Deadline 4 s caps what counts as stalled (late convergence under heavy loss counted as stalled for the no-fix rows only if > 4 s; fix rows converged).
- Caveats: the first sweep attempt for Bloom reported 500/500 stalls; cause was my checker (it compared heads to the pre-merge heads); fixed in `wait_converged`, plain-scenario rows were re-run after the fix. Livelock without fix burns CPU (6000 frames/3 s per run).
- Not done: separate "before fix" build; samod tests other than the new ones were run once and pass (`cargo test -p samod -p samod-core --features samod/tokio`; I read the first 40 output lines, all ok, rest not inspected).
