# Scoping: agent-oriented git merge
(authored by agents unless marked 🧑)

Written 2026-11-24 by vlm62_agentgit.md, from three subagent searches (web, arXiv, vendor docs). Raw notes, with more items and links: kept only in `/tmp/vlm62/{semantic,vcs,agents}.md` (not committed).

Source caveats:
- quotes below are verbatim as returned by fetch or search tools
- items marked (snippet) came from a search-result excerpt and were not re-checked on the page
- Google Scholar was queried only once, so Scholar-only work may be missing
- "nobody does X" statements are inferences from a short search, not proofs of absence

## 🧑 The request (Zulip, Nov 24, verbatim, research part only)

🧑 "The natural next step. If we do a research project on auto merge team type. And so on, is to overtake it. And first, produce a auto Git merge. That resolves conflict, but also. It sucks, and. Can be improved or replaced in several manners. First. Git is slow. Git push and Git pull takes a long time. So, are the merge procedures. That would be fine for humans. Operating on Git, but. We need to optimize for agents, and find out what does not fit agents. Second, get the slide diff naively. Re in reality, what we need is semantic diff. In writing, that would be which words changed in this part. Addition, deletion, substitution, and then. That would be another thing that Git doesn't have, which is. Moving things around. For example, I moved a function to another file. But other parts of the files remain intact. Git just shows huge diffs. With no indication of a move, and. Renaming also should be identified, and so on. I'm not sure these should be implemented into the system or. Storage, or only when we are trying to. Look at them or resolve them. Finally, maybe it's an idea to. Have Git work like a synchronized database. For the most part, although. It would then be, like logs, and. One would need to obtain a. Right, and exclusive lock on each branch to write to it, and then others will be. Told that they may still read, but reads may be stale. And. Once anyone goes offline, they would. Automatically be. Given, essentially, a new branch that's local to them. Of course, you you can still read commits with no problem because. Once you commit, it's immutable. Anyway, that's some ideas for the research part, and there are probably some prior work like. source graph or something."

(Transcribed speech. "get the slide diff" presumably means "git's line diff"; "Right, and exclusive lock" presumably means "write, exclusive lock".)

## Short answer

- Each of the three sub-ideas has close prior work. No system found combines them, and no system found serves agents as its main users.
- Sub-idea 1 ("git is slow"):
  - measured fact: git is slow only at monorepo scale
  - inference: for agents, the bigger costs are per-agent working copies and conflicts found late, at merge time
- Sub-idea 2 (semantic diff):
  - fact: view-time tools exist
  - inference: what is missing is move/rename facts recorded in history and used by the merge
- Sub-idea 3 (branch locks plus automatic offline branching):
  - fact: each piece exists in some system
  - inference: no documented system found combines them
- Inference: the best fit for formal verification is sub-idea 3's lock/lease protocol. Its safety and liveness are close to our Automerge sync liveness proofs.

## 1. "Git is slow" and what does not fit agents

Fact: git's cost grows with file count and history size.
- Microsoft, "Announcing GVFS", 2017, https://devblogs.microsoft.com/devops/announcing-gvfs-git-virtual-file-system/ :
  - "the Windows codebase has over 3.5 million files and is over 270 GB in size."
  - "when you run "git checkout" and it takes up to 3 hours, or even a simple "git status" takes almost 10 minutes to run."
  - "That's assuming you can get past the "git clone", which takes 12+ hours."
- GitHub, "Improve Git monorepo performance with a file system monitor", 2022, https://github.blog/engineering/infrastructure/improve-git-monorepo-performance-with-a-file-system-monitor/ : "when FSMonitor is not present, the commands took from 17 to 85 seconds. However, when FSMonitor was enabled the commands took less than 1 second."
- Local measurement, this host, git 2.34.1, one noisy run each, on a blob-less partial clone of rust-lang/rust (64,892 files):
  - clone: 51 s
  - `git status`: 0.16-0.38 s
  - no-op `git fetch`: 0.26-0.33 s
  - trivial `git merge`: 0.11 s
- Inference: at ordinary repo sizes, git operations take far less time than one LLM call. The human's "Git push and Git pull takes a long time" holds at monorepo scale or under heavy load.

Fact: the strongest evidence that git fits agents badly comes from an industry report.
- Pragmatic Engineer, "Anthropic builds its own source control system", Oct 22, 2026, https://blog.pragmaticengineer.com/the-pulse-anthropic-builds-its-own-source-control-system/ :
  - "The bottleneck, now, is all of the developer infrastructure built for human scale: source control, builds, and CI."
  - "as of September, we merged over 30,000 per day."
  - "25 million git checkouts per day, just for CI!"
  - "All ~3,000 staff extensively use parallel Claude agents – typically 10-15 per engineer"
  - "Design decisions to accommodate offline clients mean inefficient checkouts and more data transferred than necessary."

Fact: today's agent tools isolate each agent in its own git worktree, branch, or VM.
- OpenAI Codex docs, https://learn.chatgpt.com/docs/environments/git-worktrees :
  - "Git only allows a branch to be checked out in one place at a time."
  - "Worktrees can take up a lot of disk space."
- Cursor 2.0 changelog (snippet): "Run up to eight agents in parallel on a single prompt. This uses git worktrees or remote machines to prevent file conflicts."
- Dagger container-use README, https://github.com/dagger/container-use : "Each agent gets a fresh container in its own git branch - run multiple agents without conflicts".
- GitButler, https://blog.gitbutler.com/parallel-claude-code : "you need to bootstrap each of the worktrees (`npm install`, build artifacts, etc)" ; "now you have created the fun new ability to create merge conflicts with _yourself_."

Fact: per-agent isolation pushes conflicts to merge time.
- STORM, Liu et al., arXiv 2605.20563, 2026:
  - "Isolation prevents interference during editing but pushes all conflict resolution to the merge step"
  - "21.7% of first-round tasks overlap another's file scope"
  - the authors call their conflict figures "proxy measurements"
- AgenticFlict, Ogenrwot & Businge, arXiv 2604.03551, 2026: "yielding a conflict rate of 27.67%". This measures agent pull requests against their base branch, not agents against each other.

Inference: what fits agents badly.
- each agent needs a full working copy, including setup such as `npm install`
- a branch can be checked out in only one place
- conflicts are found late, at merge time
- conflict markers and interactive flows assume a human in an editor
- full-history clones are wasted on short-lived agents

Closest prior work for this sub-idea:
- Scalar, partial clone, and sparse checkout (Microsoft/GitHub, now in Git)
- Sapling/EdenFS (Meta)
- Jujutsu (jj)
  - stores conflicts in commits
  - has a lock-free operation log
- GitButler (multiple branches in one working directory)

Open:
- no measurement found of agent-against-agent conflict rates on shared repos
- no published design found of a VCS built for many concurrent agents
  - Anthropic's system is not public

Evaluation:
- run N parallel coding agents on a benchmark repo (e.g. SWE-bench-style tasks split across agents)
- compare git worktrees, jj, and the prototype on:
  - wall time and disk use
  - conflicts and broken merges
  - human interventions

## 2. Semantic diff: words, moves, renames

Fact: git detects whole-file renames by similarity at diff or merge time. Its move highlighting is for display only.
- git-merge docs, https://git-scm.com/docs/merge-strategies : ort "can detect and handle merges involving renames. It does not make use of detected copies."
- git-diff docs, https://git-scm.com/docs/git-diff : `--color-moved`: "Moved lines of code are colored differently."
- `--word-diff` "operates by taking the same line-by-line diff that is produced without the option and computing word-by-word changes within each hunk."

Fact: structural tools find moves, but at view or merge time and per language.
- GumTree (Falleri et al., ASE 2014; ICSE 2024), https://github.com/GumTreeDiff/gumtree : "it can detect moved or renamed elements in addition of deleted and inserted code." It only diffs; it does not merge.
- difftastic, https://github.com/Wilfred/difftastic :
  - "Difftastic always considers order to be important"
  - "AST merging is a hard problem that difftastic does not address."
- Mergiraf, https://mergiraf.org/conflicts.html :
  - "Mergiraf can detect that a particular section of source code has been moved in one revision and has been modified by the other revision."
  - the docs found do not state whether this works across files
- Spork (Larsén et al., IEEE TSE 2023), Java only. Its README: "If you're looking for a production ready tool for AST-based GIT merge, we recommend mergiraf."
- IntelliMerge (Shen et al., OOPSLA 2019) and RefMerge (Ellis, Nadi, Dig, arXiv 2112.10370), refactoring-aware merge, Java only:
  - RefMerge: "RefMerge resolves or reduces conflicts in 497 (25%) merge scenarios"
  - RefMerge: "RefMerge introduces conflicts when inverting move-related refactorings."
- Schesch et al., "Evaluation of Version Control Merge Tools", ASE 2024, https://arxiv.org/abs/2410.09934 : "The results differ significantly from previous claims".

Fact: LLM merge resolution is weak so far.
- Merge-Bench, Schesch & Ernst, arXiv 2605.25890, 2026: "The best models correctly resolve less than 60% of merge conflicts."

On the human's open question ("into the system or. Storage, or only when we are trying to. Look at them"):
- fact: every tool found infers moves at view or merge time, from snapshots
- fact: patch-based systems store changes, not snapshots
  - Pijul's manual, https://pijul.org/manual/why_pijul.html : "formally-correct version of Darcs' theory of changes and a new algorithm for merging changes"
  - Pijul's changes are line-level, with no move operation
- fact: CRDT editors give every character a stable identity, so a move or rename could be recorded once and replayed in merges
  - Eg-walker, Gentle & Kleppmann, EuroSys 2025, https://arxiv.org/abs/2409.14252 : "Compared to OT, merging long-running branches is orders of magnitude faster."
- opinion: a hybrid looks best
  - the agent declares its move or rename, since agents know their own intent
  - storage records it as a change with stable identity
  - view-time inference covers human edits
  - the human should judge this trade-off

Open:
- no system found records cross-file move or rename facts in history and uses them in merge
- no move-aware three-way merge found for prose

Evaluation:
- replay real histories that contain refactorings (RefactoringMiner can label them)
- measure conflicts and correct merges against git ort, Mergiraf, and IntelliMerge
- for prose, replay paper revision histories

## 3. Git as a synchronized database with per-branch locks

The human's design, restated:
- to write a branch, a writer must hold its exclusive lock
- readers may read while the lock is held, but their reads may be stale
- a peer that goes offline automatically gets its own local branch
- commits are immutable, so reading them is always safe

Fact: each piece exists somewhere, but no system found combines them.
- per-file server locks:
  - Git LFS, https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-lock.adoc : "Sets the given file path as "locked" against the Git LFS server, with the intention of blocking attempts by other users to update the given path."
  - Perforce exclusive open: "global exclusive lock on the file when they open it for edit". Taking the lock needs the server to be online.
- one-at-a-time merges into a branch: GitHub merge queue, "merge queue will ensure the pull request's changes pass all required status checks when applied to the latest version of the target branch and any pull requests already in the queue."
- diverge freely and merge later:
  - jj, https://docs.jj-vcs.dev/ : "it allows lock-free concurrency -- you can run concurrent `jj` commands without corrupting the repo, even if you run the commands on different machines"
  - Ink & Switch Upwelling, https://www.inkandswitch.com/upwelling/ : "supports work on private drafts that can be shared and merged only when their authors are ready."
- databases with git semantics:
  - Dolt: "Writes to a branch do not effect another branch until a merge."
  - TerminusDB
- small 2026 agent-tooling projects with per-branch leases: e.g. https://github.com/itsHabib/workbench/pull/350 , where a blocked writer "gets sent to a worktree of its own". Not peer-reviewed; code not read.

Inference: the new part is the protocol, not the storage.
- a lock is a lease with a timeout, and a fencing token protects the branch head
  - "fencing token" means a number that rises with each new lock holder, so the server rejects writes from an old holder
- if a lease expires, its holder's work turns into a local branch, to be merged later (possibly with sub-idea 2's merge)
- git already has a compare-and-swap on refs (`--force-with-lease`)
  - "compare-and-swap": update the branch only if it still points where the writer last saw it
  - so a prototype could sit on top of git

Open:
- a precise spec of these guarantees, e.g.:
  - one writer per branch
  - stale reads are bounded
  - no lost commits
  - every offline branch is eventually merged or surfaced
- a measurement of whether locking beats optimistic merge for agents

Evaluation:
- simulate N agents with injected disconnections
- measure throughput, lock wait, and work lost or reconciled
- compare against branch-per-agent with a merge queue

## Connection to VerifWeb and formal verification

Fact: our current work (STORY.md, `verification/vlm4x_am*`) proves sync liveness for the real Rust code of Automerge, in Verus.

Fact: nothing found formally verifies the merge or sync protocol of a production VCS.
- the closest work:
  - Gomes et al. 2017 (Isabelle proofs of CRDT models)
  - SafeMerge (Sousa, Dillig, Lahiri, OOPSLA 2018), which checks individual program merges
  - Mimram & Di Giusto 2013 (category theory of patches, on paper)
  - Camp (Darcs in Coq, experimental)
- survey arXiv 1405.3496 (2014): "the lack of formal analysis is visible especially in the area of merging algorithms." (snippet)

Opinion: fit for formal verification, per part.
- sub-idea 3 (lease, fencing, and offline-branch protocol): strong fit
  - safety: at most one writer per branch, and no acknowledged commit is lost
  - liveness: every offline branch is eventually reconciled or surfaced
  - this is the same style as our Automerge sync liveness proofs
- sub-idea 2's merge: partial fit
  - convergence and "the move is preserved" can be specified for a small move-aware CRDT
  - this overlaps `directions/verified_merge_lib.md`
  - semantic correctness of code merges is not a fit
- sub-idea 1 (speed and agent fit): mostly systems measurement, not verification

## Summary for the human

Git itself is fast at ordinary repo sizes: on rust-lang/rust, status, fetch, and merge each took under half a second here. It becomes slow only at monorepo scale, where Microsoft reported hours for checkout. What fits agents badly is the workflow around git: every agent needs its own full checkout, a branch can be checked out in only one place, and conflicts surface only at merge time. Anthropic reportedly moved its monorepo off git for exactly these reasons, at 30,000 merges and 25 million CI checkouts per day. For semantic diff, many tools find moves and renames when someone views or merges (GumTree, Mergiraf, IntelliMerge). None found records them in history, and the refactoring-aware merges work only on Java. My opinion is to let agents declare their moves and store them as changes with stable identity, as CRDTs do; whether that is worth it is your call. Your lock-per-branch idea has parts in Git LFS, Perforce, merge queues, jj, and Dolt, but no system found combines exclusive branch leases, stale reads, and automatic offline branches. That lease protocol is the most natural target for verification, since its safety and liveness resemble our Automerge sync proofs. No production VCS merge or sync protocol appears to be formally verified. Main gaps in this scan: Scholar was barely used, and some quotes came from search snippets.
