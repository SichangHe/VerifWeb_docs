<!-- (authored by agents unless marked 🧑) DRAFT, not published -->
## Web things worth formally verifying: where we are

**We are looking for parts of the web where a machine-checked proof fixes a real, recurring harm, and where our group has an edge.** On Nov 3 the ask was "Verification targets that you can think of in the web context. Because we have lots of data, we have lots of experience", with a warning: "you need to have some differentiator ... Otherwise ... 3 months later, somebody else put it on the archive already." The advice was to "pick bite-sized problems and make slow headway." By "formally verify" I mean proving with a tool that code meets a precise rule for every input, not just tested ones.

**The pattern we look for is a small rule-checking function between a precise standard and a security or privacy outcome.** Proofs paid off in industry where a precise spec already existed, the checked code was small, tests could not cover the inputs, and a wrong answer was costly (e.g. AWS access policies, TLS in s2n). On the web, the recurring failure is two parties that must agree on a rule but do not: a CDN (a caching server in front of a site) and the site's own server (the origin) reading a URL differently, or a consent banner and an ad vendor holding different answers. Measurement shows disagreement happened; a proof shows it cannot.

### Eight directions, strongest "why" first

**Agent browsers leak logins because their URL, cookie and redirect rules are wrong.** Agent browsers are browsers driven by AI agents; they run many users' sessions in one process to save cost. Lightpanda, one such browser, published 9 rule bugs in 6 months, one leaking login headers across sites. All 9 sit in a small core every request passes through, so a verified core could rule them out without verifying the JavaScript engine.

**Shared caches serve one user's logged-in page to another.** 2,512 sites let a response vary by some request header but leave that header out of the cache's lookup key (arXiv 2024); a URL like `/myAccount;x.css` made CDNs cache private pages on 1,188 top sites (USENIX Security 2022). The fix would be proving the cache key follows the HTTP caching standard, and that CDN and origin read URLs the same way.

**Proxies and servers disagree on where an HTTP request ends, letting attackers smuggle requests.** Fuzzing (feeding programs odd inputs automatically) found 122 parser disagreements (HTTP Garden 2024) and keeps finding more after fixes. A proof would close the class; it is also the most crowded direction.

**Revoked cookie consent often stays "yes".** 22 of 281 sites kept a positive consent after users revoked it, and on 101 sites vendors were never told (PoPETs 2025). The bug depends on the order of clicks and vendor reads, which a model checker (a tool that tries every ordering) covers fully and crawlers do not.

**Web archives still replay 9% of pages wrongly after FidEx (NSDI 2026); archives rewrite page JavaScript to replay it.** A checker proved correct once could certify each rewrite for the page's actual state. Our archive data is the edge here.

**Third-party page scripts change built-in objects and send form data away.** In our tests 46 of 120 library versions changed built-in prototypes, and 11 of 139 pages sent the typed email to another site before submit. A check at load time of one narrow property per script is the shape, much as Linux checks small programs before running them in the kernel (eBPF).

**Sharing one process across tabs or customers (tenants) saves memory but trusts the JavaScript engine to keep them apart.** The vm2 sandbox escape (CVE-2023-29017) is the failure. Rather than verify an engine, a checker could confirm each piece of compiled code stays in its tenant's memory.

**JavaScript engines diverge from the language spec.** Proof attempts found real bugs (below), but whole engines are far too big to verify; our current view is that this is evidence the method works, not a project.

### Directions we discussed in more detail

**Agent browsers and Lightpanda's rule bugs.** The 9 rule bugs cover URL origin (an `@` in the path faked the origin), cookies sent cross-site despite SameSite (the setting that limits cross-site cookies), login headers kept across redirects, and unauthenticated control ports. Closest prior work is Quark (2012), a verified browser core with one process per tab.
> **[Sichang's view: TODO]**

**Sharing processes across tabs or tenants: must the JS engine be verified?** The evidence so far says no: what must hold is a short list of boundary rules (separate memory per tenant, compiled code stays in its region), and Spectre (attacks that leak data through CPU timing) is outside any proof anyway. Cloudflare Workers already share processes, assuming attackers cannot run arbitrary machine code.
> **[Sichang's view: TODO]**

**Servo as a base.** Servo is a 578k-line Rust browser prototype whose JS engine is SpiderMonkey (C++). Rust proof tools reach only small parts of it, so the plan that follows (an opinion) is a small verified core that treats Servo as untrusted.
> **[Sichang's view: TODO]**

**On-the-fly verification of page JS.** Checking code right before it runs is established (proof-carrying code, where code ships with a proof the host checks), and was tried for page JS around 2009-2012. Whole real pages are out of reach: median 2.7 MB of JS per site in our sample, and 62 of 97 sites use eval-like code (code built and run at runtime). Narrow privacy properties per script look feasible.
> **[Sichang's view: TODO]**

**Caches, consent and cookies.** These fit the proof pattern best: small functions, precise standards, measured harm. We have no experiments of our own here, and "no formal prior work" comes from searches, not a full review.
> **[Sichang's view: TODO]**

### Real bugs found by attempting proofs (private, unreported)

**Proof attempts found about a dozen real bugs in Rust web components (JS engines Boa and Nova, rust-url, Servo, Wasmtime) and in Lightpanda; none is reported yet.** They include a memory bug in the garbage collector of the Boa JS engine, Boa running callbacks in the wrong order on 4,171 of 9,430 test programs, and rust-url failing 69 of 896 standard tests. Most of our proofs cover small hand-written models, not the real code.

### Next step

**Next I will settle my view on each direction, then pick 2-3.** Open questions for you: which directions have a differentiator others cannot copy, and is "a proof on a small model plus real bugs found" publishable, or must the proof cover real code?
