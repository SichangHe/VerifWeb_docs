# VL top-level story
(authored by agents unless marked 🧑)

Approved by the human on 2026-11-12: 🧑 "This sounds good. Note it". The wording below was written by an agent (vl_meeting_work.md).

Motivating story: web apps now keep the same state in many places at once: tabs, devices, collaborators' editors, identity providers. The protocols that keep those copies in agreement fail silently. Documents stop syncing, and you stay logged out in one tab but not another. Nobody notices until users complain.

Top-level story: verify that the real Rust implementations of these protocols both agree and finish (convergence and liveness), not just models of the algorithms.

## Care with "formally verified" claims
🧑 Human, Nov 18, verbatim: "we need to be more careful when we claim that we formally verify type V. We need to look at what prior work has done, and so on."
- context: the human asked whether synced editors such as Google Docs already use formally verified protocols. Answer from the papers read so far: proofs exist for models (Gomes 2017 RGA; OT algorithms) and for real code of simple CRDTs (Nieto 2022, safety only). None was found for the real code of a deployed editor. Literature notes: literature/walkthrough.md
