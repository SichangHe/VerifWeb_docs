#!/usr/bin/env python3
"""Explicit-state BFS model of whatwg/html#12861 (WPT same-document-nav-cross-document-nav, test 1).

Spec: html.spec.whatwg.org/multipage/browsing-the-web.html (fetched 2026-11-13).
Threads: S = iframe event loop running the test script; Q = traversable's session history
traversal queue; P = navigate's "In parallel" steps for the cross-document navigation.
Property (liveness, checked as deadlock/terminal-state): every terminal state has load fired.
"""
from collections import deque

# state: (pc_S, pc_Q, pc_P, ongoing, queue(tuple), load_fired, canceled_note)
INIT = ("frag", "idle", "none", None, (), False, "")

def step(s):
    S, Q, P, ong, q, load, note = s
    out = []
    # --- S: script: location.hash = "#1"
    if S == "frag":
        # navigate: url equals active entry URL excluding fragments, fragment non-null
        #   -> "Navigate to a fragment ... Return."  (ongoing navigation NOT set on this path)
        # navigate to a fragment: "Append the following session history synchronous navigation
        #   steps ... Finalize a same-document navigation"
        out.append(("S: navigate->navigate to a fragment; append finalize to traversal queue",
                    ("search_19", Q, P, ong, q + ("finalize",), load, note)))
    # --- S: script: location.search = "?2"  -> navigate, cross-document path
    if S == "search_19":
        # navigate: 'If navigable's ongoing navigation is "traversal": ... canceled ... Return.'
        if ong == "traversal":
            out.append(("S: navigate step 'ongoing is traversal' -> Return (nav2 dropped)",
                        ("done", Q, P, ong, q, load, "nav2 canceled at traversal check")))
        else:
            # navigate: "Set the ongoing navigation for navigable to navigationId."
            # then "In parallel, run these steps"
            out.append(("S: navigate 'Set the ongoing navigation to navigationId(nav2)'; start in-parallel",
                        ("done", Q, "check", "nav2", q, load, note)))
    # --- P: navigate in-parallel steps
    if P == "check":
        # "If unloadPromptCanceled is not 'continue', or navigable's ongoing navigation is no
        #  longer navigationId: ... Abort these steps."
        if ong != "nav2":
            out.append(("P: navigate in-parallel 'ongoing navigation is no longer navigationId' -> Abort",
                        (S, Q, "aborted", ong, q, load, note + " nav2 aborted in-parallel")))
        else:
            # abstraction: fetch + create/load document; later checks of ongoing navigation
            # (e.g. populate/finalize-cross-document) are collapsed here -> JUDGMENT
            out.append(("P: fetch ok -> (cross-document finalize) -> iframe load event fires",
                        (S, Q, "loaded", None, q, True, note)))
    # --- Q: session history traversal queue
    if Q == "idle" and q:
        # finalize a same-document navigation: "If targetNavigable's active session history entry
        #  is not targetEntry, then return." -- nav2 has not committed, so active entry is still
        #  the #1 entry -> proceed; ... "Apply the push/replace history step" -> apply the history step
        # apply the history step: for each changing navigable (update-only):
        #   'Set navigable's ongoing navigation to "traversal".'   (issue: step 8.4)
        out.append(("Q: finalize same-doc nav -> apply the history step: ongoing := \"traversal\"",
                    (S, "applying", P, "traversal", q[1:], load, note)))
    if Q == "applying":
        # apply the history step waits for change jobs / queued tasks, then for update-only:
        #   "This is a same-document navigation ... Set navigable's ongoing navigation to null."
        #   (issue: step 14.10.1)
        out.append(("Q: apply the history step (same-document branch): ongoing := null",
                    (S, "idle", P, None, q, load, note)))
    return out

def bfs():
    seen = {INIT: None}
    dq = deque([INIT])
    bad = []
    while dq:
        s = dq.popleft()
        succ = step(s)
        if not succ and not s[5]:
            bad.append(s)
        for lbl, t in succ:
            if t not in seen:
                seen[t] = (s, lbl)
                dq.append(t)
    print(f"states={len(seen)} bad_terminal={len(bad)}")
    for b in bad:
        trace, x = [], b
        while seen[x] is not None:
            p, lbl = seen[x]; trace.append(lbl); x = p
        print("\nBAD terminal (no load ever):", b[6].strip())
        for i, l in enumerate(reversed(trace), 1):
            print(f"  {i}. {l}")

if __name__ == "__main__":
    bfs()
