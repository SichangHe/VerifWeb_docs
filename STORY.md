# VL top-level story
(authored by agents unless marked 🧑)

Approved by the human on 2026-11-12: 🧑 "This sounds good. Note it". The wording below was written by an agent (vl_meeting_work.md).

Motivating story: web apps now keep the same state in many places at once: tabs, devices, collaborators' editors, identity providers. The protocols that keep those copies in agreement fail silently. Documents stop syncing, and you stay logged out in one tab but not another. Nobody notices until users complain.

Top-level story: verify that the real Rust implementations of these protocols both agree and finish (convergence and liveness), not just models of the algorithms.
