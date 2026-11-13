# Weird web verification targets, PL / algebra lens (gen_pl)
(authored by agent; nothing published. Prior-work notes are from memory, NOT searched this run: [unchecked].)

Method [O]: ask of each web mechanism "is this secretly a semilattice, a monotone map, an idempotent normalizer, a round trip, or a refinement between two specs?" Specs state the algorithm; almost none state the algebraic law, so no one machine-checks it.

1. Stacked CSPs form a meet-semilattice
- thing: browsers enforce every Content-Security-Policy header/meta present; the spec says "all must pass".
- theorem: allowed(P1 ∧ P2) ⊆ allowed(P1), order-independent, idempotent; adding any policy never permits a load that was blocked. Test nonce/'strict-dynamic'/hash interplay for breaks.
- why unusual: CSP is verified as a policy language, not as an algebra of combinations.
- prior [unchecked]: CSP formal models (Calzavara et al.), none on combination laws.
- step: Lean model of source-list matching with nonce and strict-dynamic; prove monotonicity or get a counterexample.

2. Response tainting only moves up a lattice across redirects
- thing: Fetch spec response types basic < cors < opaque (and opaqueredirect), with redirects, service workers, cache in between.
- theorem: along any redirect/service-worker chain, taint never decreases; information visible to the page is a function of the final taint.
- why unusual: Fetch is read as prose; the lattice is implicit in a mutable field.
- prior [unchecked]: WebSpec (Coq) models parts of this; no lattice lemma known to me.
- step: encode Fetch main-fetch + redirect loop (limit 20) with taint; prove monotone and terminating.

3. Streaming parse equals whole-buffer parse (chunking invariance)
- thing: browsers parse HTML/sniff MIME while bytes arrive in arbitrary network chunks.
- theorem: for every split of input into chunks, tokenizer(+tree builder) output equals parse of the concatenation; MIME sniff depends only on the first 1445 bytes.
- why unusual: the spec is written for whole input; refinement to streaming is assumed.
- prior [unchecked]: chunk-boundary bugs seen in html5ever/parse5-style parsers; no proof known.
- step: prove it for the tokenizer's character-reference and "--!>" states in a small Lean/Verus tokenizer.

4. Byte-range cache merging is a CRDT
- thing: video/PDF/media caches store 206 Partial Content pieces from many requests.
- theorem: merge of interval-sets is commutative, associative, idempotent; reassembled bytes equal the origin body iff validators (ETag/Last-Modified) agree; a mixed-validator merge is rejected.
- why unusual: range handling is a bug source, but viewed as plumbing, not as a join.
- prior [unchecked]: RFC 9110 text only.
- step: Dafny interval-set with validator check; prove the three laws plus content equality.

5. Hostname normalization is idempotent (IDNA / UTS46 + URL serialize-parse)
- thing: the WHATWG host parser runs UTS46 mapping, punycode, NFC.
- theorem: parse(serialize(parse(x))) = parse(x) for all x, and toUnicode∘toASCII is stable on its image; list the inputs where it fails.
- why unusual: URL work checks "matches the test suite", not the round-trip law (differs from item 7 of the taken list, which is conformance).
- prior [unchecked]: Unicode security notes on IDNA mapping changes.
- step: restrict to the ASCII + a few mapped codepoints; prove with a table-driven Lean model, extend the table.

6. CSS cascade: !important reverses layer order
- thing: @layer, origin, specificity, source order; for !important the layer order is inverted.
- theorem: cascade winner is a total, deterministic order; reordering stylesheet links changes the winner only within equal layer/specificity; important-flip is an order-reversing involution.
- why unusual: CSS is never a verification target; this is a compare function with a twist.
- prior [unchecked]: formal CSS work (e.g. Coq CSS formalizations) predates layers.
- step: model the sort key as a lexicographic tuple in Lean; prove totality and the involution.

7. ES module evaluation order is a topological order, with cycles and top-level await
- thing: module graph evaluation (async modules, cycles) in the ECMAScript spec.
- theorem: each module runs after all its non-cyclic dependencies finish; order is unique given the graph; evaluation terminates and runs each module exactly once.
- why unusual: spec algorithm had known subtle fixes; no mechanized statement of the ordering law.
- prior [unchecked]: ESMeta executes the spec; no theorem I know of.
- step: model the algorithm (InnerModuleEvaluation) on graphs of <= 6 nodes; bounded check, then Lean proof.

8. robots.txt: adding a rule never widens access
- thing: RFC 9309 longest-match, ties favour Allow, Google's open-source parser, others differ.
- theorem: access decision is independent of rule order; adding a Disallow never turns a denied URL into allowed; crawlers' parsers agree with the RFC on all (rule set, path) pairs.
- why unusual: crawler ethics, not correctness, is the usual framing; fits your web-measurement tools (DeGenTWeb crawling).
- prior [unchecked]: Google's parser + fuzz tests; no proof.
- step: Lean model of the matcher with `*` and `$`; prove order independence; differentially test against 3 parsers.

9. JS printer/parser round trip (minifiers, bundlers)
- thing: minifiers print ASTs back to text; ASI, regex-vs-division, `a+ +b`, `a++ +b`.
- theorem: parse(print(ast)) = ast for a fragment containing these ambiguities; print(parse(s)) is an idempotent normal form.
- why unusual: tools are tested on corpora; the round trip is the property that breaks real sites silently.
- prior [unchecked]: verified JS printers are rare (CompCert-style work targets C; JSCert covers semantics, not printing).
- step: tiny expression+statement grammar with ASI in Lean; prove the round trip with minimal parentheses/space insertion.

10. Header field combining is lossless only for list-typed fields
- thing: proxies merge duplicate headers by joining with commas (RFC 9110); Set-Cookie, and some others, break.
- theorem: for a typed table of fields, split(join(hs)) = hs iff the field's grammar is list-based; any proxy that folds a non-list field changes meaning (refines to a smuggling/cookie-merge bug).
- why unusual: framing smuggling is studied; the type distinction behind the combining rule is not stated as a refinement.
- prior [unchecked]: HTTP Garden discrepancies are observational.
- step: Lean model with a field-type table (Set-Cookie, Cache-Control, Content-Length); prove the iff, then find which CDNs violate it.

Ranking [O], weirdness x feasibility: 1, 4, 8 (easy, clean laws); 2, 3 (deeper); 6, 7, 9 (most original, more modelling work).
