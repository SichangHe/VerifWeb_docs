# Page scripts: third-party code behaves
(authored by agents unless marked 🧑)

Who is hurt. Users typing passwords or cards on pages that load third-party scripts (card skimmers), and sites broken by libraries that change built-in objects (prototype pollution, e.g. lodash CVE-2019-10744).

Our evidence. 46 of 120 library versions we tested polluted built-in prototypes; 63 of 95 real sites changed a built-in after loading; 11 of 139 pages sent the typed email to another site before submit (often hashed); 0 of 68 leaked passwords.

Why existing practice does not fix it. Static analyzers do not scale soundly to real pages: 62 of 97 sites in our corpus use eval-like dynamic code, and parsing alone takes a median 309 ms per site.

Why a proof helps. A load-time check of one narrow property ("this script never reads password fields"), cached per script, with fallback when the check fails. Like Linux's eBPF verifier, for page JS. This is the advisors' "on-the-fly verification".

Contribution (opinion). Load-time checks were done in 2009-2012 (Chugh et al.); new would be proofs for the current page state, at modern scale.

Opinion. Feasible for narrow privacy properties; not for deciding process sharing.

Questions
- is a measurement paper ("how much page JS is checkable") an acceptable first step?
