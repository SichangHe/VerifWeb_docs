(authored by agents unless marked 🧑)

My strongest matches are relational proofs for proxy request handling, resource/liveness proofs for HTTP/2 cancellation, and proof maintenance for certificate validation.

Live source retrieval failed because DNS was unavailable. The bug citations below were not freshly checked; novelty and closest-work judgments are provisional. Each proposed contribution is a research hypothesis, not a claim that existing methods cannot already handle it.

1. Relational verification of HTTP request boundaries  
   Prove: The proxy and backend agree where each forwarded request ends; after an early response, unread body bytes cannot become another request when the connection is reused.  
   Why proof: This relates two parsers and connection management across arbitrary byte streams, fragmentation, and early-exit paths.  
   FV contribution: Compositional stream-refinement proofs joining parsing, forwarding, discarding unread bodies, and connection reuse; parser correctness alone is insufficient.  
   System + bug: A small Pingora connection/request core. [CVE-2025-4366, 2025](https://blog.cloudflare.com/resolving-a-request-smuggling-vulnerability-in-pingora/) concerned request smuggling when a cache-hit path left request bodies unread; the proposed property covers early responses generally.  
   Tool: Verus for executable Rust and relevant parser code; start with one fixed proxy/backend parser pair.  
   Closest FV work: “EverParse: Verified Secure Zero-Copy Parsers for Authenticated Message Formats,” USENIX Security 2019; extend parsing guarantees to stateful interaction between components.

2. Resource and liveness proofs across HTTP/2 cancellation  
   Prove: During any interval of length t, backend task starts ≤ burst + rate × t, and live backend tasks ≤ B; resets cannot replenish rate credits. Admitted requests eventually finish under fair scheduling, responsive peers, and terminating backends.  
   Why proof: A reset can remove a stream while its backend task continues; finite load tests cannot cover every reset/completion interleaving or establish eventual completion.  
   FV contribution: Compose resource-credit invariants with progress proofs across cancellation and asynchronous cleanup, then refine them to Rust task ownership.  
   System + bug: An admission/cancellation component around Rust h2 or Pingora. [CVE-2023-44487, 2023](https://nvd.nist.gov/vuln/detail/CVE-2023-44487), HTTP/2 Rapid Reset, motivates accounting for work beyond active-stream counts; these bounds concern backend tasks, not all DDoS costs.  
   Tool: Verus, including temporal proofs; TLA+ for protocol exploration, with executor and backend assumptions explicit.  
   Closest FV work: “Amortised Resource Analysis with Separation Logic,” LMCS 2011; the proposed advance combines accounting with asynchronous cancellation and liveness.

3. Maintaining HTTPS certificate-validation proofs through policy changes  
   Prove: Old and new validators agree outside an approved policy change, such as retiring a signature algorithm; designated CA/key constraints remain true, and Rust code refines the new specification.  
   Why proof: Regression certificates cannot establish agreement across every other certificate chain, extension, and validation option.  
   FV contribution: Relational proofs between policy versions, with agents repairing implementation proofs while protected security invariants remain fixed; evaluate across actual release histories.  
   System + bug: Extend Verdict’s Rust/Verus validator. [CVE-2021-3450, 2021](https://nvd.nist.gov/vuln/detail/CVE-2021-3450) was an OpenSSL regression that bypassed CA checks under affected verification options; it is motivation, not a reported Verdict bug.  
   Tool: Verus and untrusted proof-writing agents; humans review permitted policy changes and protected invariants.  
   Closest FV work: “Towards Practical, End-to-End Formally Verified X.509 Certificate Validators with Verdict,” USENIX Security 2025; “Mostly Automated Proof Repair for Verified Libraries” (Sisyphus), PLDI 2023. Investigate evolving specifications as well as code.

4. Equivalence between URL checks and the HTTP client’s parsed destination  
   Prove: For every accepted URL, policy and transport use identical scheme/hostname/port values after serialization and reparsing; redirects restart this obligation. This concerns parsed destinations, not resolved IP addresses.  
   Why proof: Agreement must hold across all accepted encodings, delimiters, and normalization cases; differential fuzzing establishes it only for sampled inputs.  
   FV contribution: Compatibility certificates for independently updated parser/serializer pairs over a shared accepted URL subset, with new proof obligations generated when dependencies change.  
   System + bug: A verified adapter and relevant parser code for Rust url/reqwest-based webhook services. [CVE-2022-27780, 2022](https://curl.se/docs/CVE-2022-27780.html), curl’s “Percent-encoded path separator in URL host,” illustrates an interpretation failure.  
   Tool: Verus; preserve a typed destination through transport setup and prove the remaining serialization boundaries.  
   Closest FV lead: “An Expressive Model for the Web Infrastructure: Definition and Application to the BrowserID SSO System,” IEEE S&P 2014. This is a model-level comparison; the nearest implementation-verification competitor remains unconfirmed.

5. Credential noninterference across redirects  
   Prove: Holding public server responses fixed, changing a protected credential cannot change HTTP content sent outside that credential’s permitted destinations; compare requests before encryption, excluding timing side channels.  
   Why proof: This compares executions over arbitrary redirect chains, retries, and protocol/port transitions; isolated “header stripped” tests do not establish noninterference.  
   FV contribution: Compositional information-flow proofs across mutable header reconstruction and redirect state, supporting different permitted destinations for different credentials.  
   System + bug: A small Rust HTTP-client redirect/header component usable by Servo or reqwest consumers. [CVE-2022-27774, 2022](https://curl.se/docs/CVE-2022-27774.html), curl’s “Credential leak on redirect,” supplies concrete motivation.  
   Tool: Verus paired-execution proofs; Authorization credentials follow configured origins, while cookies follow their specified domain/path/security rules.  
   Closest FV lead: “Quark: A Browser Built for Security,” USENIX Security 2012, as a browser-isolation comparison; closest work specifically verifying redirect implementations needs checking.

6. Refinement and recovery proofs for per-domain certificate-issuance evidence  
   Prove: Every domain in a certificate request has its own valid authorization and current DNS CAA check permitting this issuer; after recovery, stable valid requests finish under fair retries and available dependencies.  
   Why proof: Concurrent multi-domain requests, retries, and crashes create unbounded histories; testing and bounded model checking cannot establish the complete safety-and-progress claim.  
   FV contribution: Refine a persistent evidence protocol into Rust, composing issuance safety with recovery liveness; mechanize applicable CA/Browser Forum requirements with human review of the prose-to-spec translation.  
   System + bug: A Rust component recording and recovering per-domain checks in an ACME certificate service. Let’s Encrypt’s [CAA rechecking incident, 2020](https://bugzilla.mozilla.org/show_bug.cgi?id=1619047) repeatedly checked one name instead of all names in affected requests; no CVE is claimed.  
   Tool: Verus for code and temporal reasoning; TLA+ for recovery design. DNS evidence and clock behavior require explicit contracts.  
   Closest FV work: “Anvil: Verifying Liveness of Cluster Management Controllers,” OSDI 2024, as an implementation-liveness method; an ACME-specific prior-work search and a prospective CA adopter are still needed.

7. Translation validation for gateway routing and authorization configurations  
   Prove: For every request, compiled routing/filter configurations choose the same backend and allow/deny decision as their reference semantics, including path normalization and middleware order.  
   Why proof: Equivalence quantifies over unbounded request paths and overlapping rules; replaying production traffic cannot establish it.  
   FV contribution: An untrusted configuration optimizer emits certificates checked by a small verified checker; the proof includes normalization and middleware effects, beyond route lookup alone.  
   System + bug: A proposed Pingora configuration loader compiling exact/prefix policies into routing tables; adopter unconfirmed. [CVE-2021-29492, 2021](https://nvd.nist.gov/vuln/detail/CVE-2021-29492) involved Envoy path interpretation and possible authorization bypass, which the reference semantics must explicitly exclude.  
   Tool: Lean or Verus for certificate checking and reference semantics; Verus for the Rust execution core.  
   Closest FV work: “NetKAT: Semantic Foundations for Networks,” POPL 2014. Application-layer normalization and middleware composition provide the proposed extension; keep the evaluation centered on deployed gateways to avoid becoming too PL-heavy.

8. Refinement from authenticated bytes to JWT authorization claims  
   Prove: Accepted claims come from the exact authenticated bytes, using an issuer-approved key/algorithm pair and required audience; ambiguous encodings cannot select weaker verification behavior.  
   Why proof: The guarantee crosses attacker-controlled syntax, key selection, algorithm dispatch, and claim interpretation; verifying the signature primitive covers only one layer.  
   FV contribution: Generate and check correspondence proofs showing that every implementation acceptance represents authenticated claims in the protocol model; initially support signed JWTs with configured keys and one algorithm.  
   System + bug: A small verified JWT-verification core for Rust web APIs. [CVE-2015-9235, 2015](https://nvd.nist.gov/vuln/detail/CVE-2015-9235) documents algorithm-confusion problems in node-jsonwebtoken; cryptographic primitive security remains assumed.  
   Tool: Verus plus Tamarin or ProVerif, with an explicit proved correspondence between executable and symbolic operations.  
   Closest FV work: “DY*: A Modular Symbolic Verification Framework for Executable Cryptographic Protocol Code,” EuroS&P 2021. The contribution must exceed building another verified token library.

9. Resource and termination proofs for recursive DNS used by web infrastructure  
   Prove: Each lookup triggers at most B outgoing DNS requests and returns an answer or error under fair local timers, despite referral cycles and adversarial replies; shared requests are charged to every dependent lookup.  
   Why proof: Replies dynamically construct the dependency graph; finite query corpora cannot cover every graph and concurrent request-sharing schedule.  
   FV contribution: Preserve per-lookup resource and progress guarantees through recursive expansion, retries, and shared work, with refinement to asynchronous Rust.  
   System + bug: A scheduling component in Hickory’s recursive resolver for web-fetch infrastructure. [CVE-2020-8616, 2020](https://kb.isc.org/docs/cve-2020-8616), associated with NXNSAttack, exposed excessive recursive fetches in BIND.  
   Tool: Verus for credits and ownership; temporal reasoning for completion through responses or timeouts.  
   Closest FV work: “GRoot: Proactive Verification of DNS Configurations,” SIGCOMM 2020; extend configuration reasoning to resolver execution. Its connection to the web is weaker than the other candidates’.

10. Compositional resource proofs for HTTP content decoding  
    Prove: Across all decoding stages, total emitted bytes ≤ O and peak buffer/state memory ≤ M, including during cancellation; the memory theorem assumes explicit bounds on each codec’s internal state.  
    Why proof: Limits checked separately per header or only on final output do not imply bounds across all intermediate decoding stages.  
    FV contribution: Resource contracts that compose through dynamically constructed decoder pipelines and survive codec additions; prove the Rust orchestration against explicit codec contracts.  
    System + bug: A bounded decoding adapter for Rust web clients/proxies. curl’s [CVE-2022-32206, 2022](https://curl.se/docs/CVE-2022-32206.html) and [CVE-2023-23916, 2023](https://curl.se/docs/CVE-2023-23916.html) concern HTTP-compression denial of service, including limits bypassed using multiple headers.  
    Tool: Verus for pipeline construction, shared budgets, and cleanup; this does not establish an unconditional CPU-time bound for unverified codecs.  
    Closest FV work: “Amortised Resource Analysis with Separation Logic,” LMCS 2011. The research contribution must be reusable composition and proof maintenance; a one-off counter fix would not qualify.

My ranking by FV-centrality × fit:

**1 proxy boundaries > 2 HTTP/2 cancellation > 3 certificate-policy updates > 5 redirect credentials > 4 URL agreement > 6 certificate issuance > 7 gateway configurations > 8 JWT verification > 10 decoding budgets > 9 DNS resolution**

The first three offer the clearest systems thesis. Redirect credentials is the strongest privacy option. Certificate issuance needs a CA partner; gateway configurations and JWT verification face substantial novelty questions; decoding budgets risk collapsing into engineering; DNS has the weakest web-specific fit.