# Web formal-verification targets shaped like FV's industrial successes
(authored by agents unless marked 🧑)

## 0. What we are looking for
- advisors' ask (Nov 3 meeting, as relayed by the manager): formal verification targets in the web context, drawn from real breakage, bite-sized, with a differentiator
- human correction (verbatim): "I think we were saying more broadly to look at things that we should formally verify that are related to the web."
- human preference (verbatim): "I do like having something to do with privacy, cash, cookie and so on that are kind of niche"

## 1. The shape of a successful FV target
Source: survey.md (14 industrial cases, quotes and URLs there). Summary [inference from those cases]:
- a precise spec already exists: the policy language (AWS Zelkova), RFC/NIST crypto (s2n, HACL*, Fiat-Crypto), C semantics (CompCert)
  - Zelkova: "The property to be verified is specified in the policy language itself, eliminating the need for a different specification or formalism for properties." (Backes et al., FMCAD 2018, https://cdn.amazon.science/56/3c/7d75bca84c56b9b1ed1999beec0c/semantic-based-automated-reasoning-for-aws-access-policies-using-smt.pdf)
- the checked thing is a small decision function: a policy, a config, a field operation, a parser
- tests cannot cover the inputs, so "for all inputs" is the product
  - Tiros: "allows users to gain assurance about the security of their networks that would be impossible through testing." (CAV 2019, https://d1.awsstatic.com/whitepapers/Security/Reachability_Analysis_for_AWS-based_Networks.pdf)
- a wrong answer is costly: security boundary, outage, legal exposure
- the proof is paid once and reused, or re-run in CI
  - s2n: "In one year of code changes only three manual updates to the proof were required." (CAV 2018, http://www0.cs.ucl.ac.uk/staff/b.cook/CAV18_s2n.pdf)

Implication [opinion]: good web targets are small pure decision functions that sit between a standard and a privacy or security outcome: "may this cookie be set", "is this cached response reusable", "does this byte string mean consent".

## 2. Ideas
Ordered by fit to the shape × the human's privacy/cache/cookie taste [opinion]. Quotes and Scholar notes come from candidates.md; Scholar was checked from first-page snippets only, so "none seen" is not proof that none exists.

### 2.1 Cache reuse must respect `Vary`
- thing: HTTP caches (CDNs, proxies) store a response and reuse it for later requests. The response header `Vary: Cookie, Accept-Language` says "reuse only if these request headers match", so the cache key must include them.
- breakage: "2512 websites include some header names in the Vary response header but do not configure their web cache(s) to include them in the cache key." (https://arxiv.org/html/2407.16303)
  - consequence: one user's personalized or logged-in page can be served to another user
- property: a cache serves a stored response for request R only if every header named in Vary matches under RFC 9111's rules (case, order, whitespace, repeated fields, `Vary: *`, absent vs empty)
- why FV: the key function is small and pure, but the inputs (header combinations and spellings) are unbounded; a proof covers all of them
- unusual: caches are treated as performance plumbing, but a cache-key bug is a privacy leak between users
- prior: Scholar shows only old cache-navigation models ("Formal models for web navigations with session control and browser cache", 2004) and conformance testing; no verified key function seen
- first step: write RFC 9111 "match" in Lean, prove a reference implementation equal to it, then diff nginx/Varnish/Squid against it on generated headers

### 2.2 IAB TCF consent strings decode correctly
- thing: in the EU, a "consent string" (base64 bits) records which ad vendors a user agreed to. Consent popups encode it, and every ad company decodes it before using personal data.
- breakage: iabtcf-es issue #142: "according to spec, we need to have 733 bits that indicate if vendors have consent or not. but we only have 28 bits." Maintainer: "That string is either invalidly encoded or truncated in some way." (https://github.com/InteractiveAdvertisingBureau/iabtcf-es/issues/142)
- property: decode(encode(x)) = x for every valid x, every malformed string is rejected, and vendor v gets "consent" only if v's bit is set
- why FV: bit-level format with range encoding and optional segments; a parser that silently pads or guesses turns "no" into "yes"
- unusual: the error is a legal one (GDPR), not a crash; prior work measures compliance instead of proving the codec
- prior: Scholar shows only compliance measurement (e.g. "Johnny can't revoke consent either"); no proofs seen
- first step: verified core-segment decoder in Verus or Lean with a round-trip proof; fuzz the official libraries against it

### 2.3 Cookie `Domain` vs the Public Suffix List
- thing: a site can scope a cookie to a parent domain (`Domain=example.co.uk`). The browser must refuse public suffixes like `co.uk`, which come from a ~10k-rule list with wildcards and exceptions.
- breakage: crawlberg #762: "In HTTP mode, crawlberg stores a cookie whose `Domain` is a public suffix when that suffix is not in a short fixed list." ... "It then sends that cookie to every other site under the same suffix. Chrome rejects the same cookie." (https://github.com/xberg-io/crawlberg/issues/762)
  - caveat: small project; browsers also disagree ("IE apparently misunderstands wildcard rules", IETF http-state 2015, https://mailarchive.ietf.org/arch/msg/http-state/TPAIg769WRpZsQVkKOCFpQNqFmE/)
- property: for every host and every list, accept/reject equals the RFC 6265bis + publicsuffix.org algorithm, and an accepted cookie never matches a host outside its registrable domain
- why FV: the list changes weekly and wildcard/exception interplay is combinatorial; tests cover only listed examples
- unusual: the PSL underpins cookies, CORS-like "site" checks and partitioning, yet is treated as data, not logic
- prior: the Quark browser verified cookie domain logic against an abstract suffix predicate ("current domain suffixes build on the notion of a public suffix", Jang, Tatlock, Lerner, USENIX Sec 2012), not the real PSL algorithm
- first step: verify a PSL matcher (longest match, `*`, `!`) equal to a naive spec over all label sequences

### 2.4 Bounce-tracking deletion fires exactly when it should
- thing: trackers bounce you through their domain during a redirect to set a cookie. Browsers now delete storage of sites seen only as redirect hops without user interaction for 45 days.
- breakage: the spec itself lists open holes: "TODO: Consider if we should do anything when the clock is moved forward or backward." and "TODO: Verify that using domain-match catches all cookies for the registrable domain." (https://privacycg.github.io/nav-tracking-mitigations/)
- property: a site is purged iff it bounced, the grace period passed and no user activation occurred, for any interleaving of clock changes, activations and navigations; the purge covers all of that site's state
- why FV: timers × events × clock jumps form a temporal state space that tests sample poorly; a model checker explores all orders
- unusual: privacy defenses are rarely specified as timed state machines
- prior: none seen (Scholar returned only unrelated aviation-tracking papers)
- first step: timed-automaton model of the spec; check the clock-skew TODO

### 2.5 Ad-blocker rule compilation preserves meaning
- thing: Chrome's Manifest V3 forces ad/tracker blockers to compile filter-list rules (e.g. `$removeparam=utm_source` strips a tracking URL parameter) into Chrome's declarative rule format.
- breakage: AdGuard #3615: "A valid named `$removeparam` rule fails before the request when the target is the first query item." and "the final address bar looks sanitized in both cases even though the first-position value has already left the browser." (https://github.com/AdguardTeam/AdguardBrowserExtension/issues/3615)
- property: the compiled rule matches a URL iff the source rule does, under filter syntax (`^`, `*`, `|`), and exceptions cancel exactly their targets
- why FV: this is a compiler; translation validation is the CompCert-shaped answer, and the failure is silent (the URL bar looks clean)
- unusual: filter lists are studied empirically, never as a compiler-correctness problem
- prior: Scholar shows filter-list measurement (Chen, Snyder et al.), no verification
- first step: prove translation correct for a 3-operator pattern language, then extend to `$removeparam`

### 2.6 Attribution Reporting budget filter
- thing: Chrome's Attribution Reporting API lets advertisers count conversions with noise added. A per-source budget caps how much any one source contributes, and the privacy guarantee depends on that cap.
- breakage: Chrome's own authors: "neither ARA nor PAA has been backed by a rigorous DP proof" (arXiv 2412.16916, https://arxiv.org/html/2412.16916v1)
- property: for any sequence of triggers, each source's total contribution never exceeds the budget, and clamping happens before noise
- why FV: the differential-privacy theorem holds only if the budget filter code is right; that filter is a small state machine with a precise invariant
- unusual: DP proofs exist on paper; checking the code that the paper's theorem assumes is the missing link
- prior: paper proof only (arXiv above); no machine-checked proof seen
- first step: verify the budget-filter rules in Chromium's attribution storage against the invariant, with the DP theorem left as a hypothesis

### 2.7 Storage Access API: three answers to one question agree
- thing: an embedded iframe (e.g. a comment widget) asks permission to use its normal cookies. The browser answers through `hasStorageAccess()`, the `requestStorageAccess()` promise, and the actual cookie jar.
- breakage: WebKit 193277: "despite hasStorageAccess() returning true, and the promise requestStorageAccess() resolving." ... "An iframe (siteB) is still unable to set and get cookies." (https://bugs.webkit.org/show_bug.cgi?id=193277)
  - closed as invalid (a prior first-party visit was required); the three views still disagreed in practice
- property: `hasStorageAccess()` is true iff the frame's cookie access is actually unpartitioned; grants survive exactly the navigations the spec lists
- why FV: small state (grant, user activation, sandbox flags, navigation kind); model checking covers all combinations
- unusual: proves API consistency, not secrecy
- prior: Scholar shows only empirical work ("Exploiting the Shared Storage API", CCS 2025); no formal model seen
- first step: ~6-variable state model; prove the three views agree

### 2.8 HTTP/1.1 message framing (request smuggling)
- thing: when a proxy and a server disagree on where one HTTP request ends (`Content-Length` vs `Transfer-Encoding`), an attacker hides a second request inside the first.
- breakage: HDiff found "an attack that exploits a semantic gap in parsing more than one Content-Length or Transfer-Encoding header field" and "we discovered 14 vulnerabilities" (DSN 2022, https://www.jianjunchen.com/p/hdiff.dsn22.pdf; quote from a search summary, not yet re-checked)
- property: the parser's framing equals RFC 9112's, or the message is rejected; then any two verified components agree on every byte stream
- why FV: differential fuzzing (HDiff, HTTP Garden) keeps finding new cases; a proof closes the class
- unusual [opinion]: least unusual here; included because the human asked for broad web targets and it fits the shape best
- prior: only fuzzing seen (HTTP Garden, https://arxiv.org/pdf/2405.17737)
- first step: verified framing function; compare with one proxy

## 3. Gaps
- Chromium tracker pages need login; CHIPS and cache-partition bugs were dropped for that reason (candidates.md A2, B2)
- Scholar checks: first-page snippets only; 2.8 had no dedicated query
- weaker candidates left out: Surrogate-Control precedence (evidence only from a fork's issue tracker), Topics, Protected Audience k-anonymity, Privacy Pass (already Tamarin-analyzed, https://eprint.iacr.org/2025/2022), IDNA, HTTP Range
