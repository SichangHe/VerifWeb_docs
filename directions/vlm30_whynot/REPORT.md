# Why has it not been done? CDN purge and TLS revocation
(authored by agents unless marked 🧑)

Question (🧑, verbatim): "If this is an interesting and. Actually, useful and doable thing. Why has it not been done? I think the same thing applies for. C A. For the. SSL. Or TLS, as it's now called. Right,"

Search scope: 6 Google Scholar queries (since 2016; raw results in `raw/s1.txt`–`raw/s6.txt`), plus primary industry sources fetched directly. "Not found" below means not found in this search, not proof that the work doesn't exist.

## Verdicts

1. CDN purge across edge and shield tiers. I found no formal model or proof of CDN purge anywhere, academic or industry. TLA+ is common for neighbouring problems: hardware cache coherence, serverless cache coherence, and Cosmos DB consistency. The closest industry work (Meta's TAO) measures consistency in production rather than proving it. My inference is that it hasn't been done for three reasons. CDN code and purge protocols are proprietary. The tiered-cache semantics aren't even publicly documented (Fastly's docs don't describe purge plus shielding). TTLs bound staleness anyway, so a stale object is rarely a crisis. A proof would add something only if a customer needs a hard "purge X means nobody sees X after time T" guarantee, for example for legal takedowns. That depends on the purge protocol plus failure handling, and it can't be checked from outside.

2. TLS certificate revocation. Here the industry has decided the mechanism itself is not worth perfecting. Browsers soft-fail, which means they accept the certificate when the revocation check can't complete. Langley (Google, 2014) called online checking "useless". Let's Encrypt turned off OCSP in 2025 over privacy. The CA/Browser Forum (2025) is shrinking certificate lifetimes to 47 days by 2029 precisely because revocation "do[es] not adequately protect relying parties". Formal work exists only for alternative or niche PKIs (Tamarin/ProVerif models of DTKI, LocalPKI, V2X, identity-based revocation), not for the deployed CRL/OCSP/CRLite system. Opinion: a proof that a revocation protocol is correct adds little when the real failures are policy choices (soft-fail, CAs that don't revoke) and not protocol bugs. Expiry is what actually bounds the risk.

Common thread (inference): in both cases there is a cheap fallback that bounds staleness without coordination (TTL or certificate expiry), so a proof of the coordinated path has low marginal value. The parallel the human drew holds. The difference is that TLS has already publicly chosen the fallback, while CDNs still sell instant purge as a feature.

## Evidence: CDN purge

- Scholar "formal verification CDN cache invalidation purge" (s1) and "content delivery network model checking OR TLA+ cache consistency" (s5) returned no CDN purge model. The hits are application-level invalidation (Cachematic, ACM/SPEC 2019), a CRDT web cache (2024), and CDN security fuzzing (ReqsMiner, NDSS 2024).
- TLA+ is used for adjacent caches (s2):
  - Zhu et al. 2021: "Our TLA + model allows for the number of processors…"
  - Concord (HPCA 2025, serverless software caches): "With TLA+, we first specify all the states and possible actions"
  - Hackett et al. ICSE-SEIP 2023, "Understanding inconsistency in Azure Cosmos DB with TLA+"
  - CausalMesh, "A Formally Verified Causally Consistent Distributed Cache" (title only seen, s5)
- Meta, "Cache made consistent" (2022), https://engineering.fb.com/2022/06/08/core-infra/cache-made-consistent/
  - result: "from 99.9999 percent (six nines) to 99.99999999 percent (10 nines)"
  - method is a black-box checker: "Polaris interacts with a stateful service as a client and assumes no knowledge of the service internals."
  - no TLA+ or formal methods mentioned. CDNs appear only as an easy case: "A static cache has a very simple cache model (e.g., a simplified CDN fits this model)."
- AWS, "Use of Formal Methods at Amazon Web Services" (Newcombe et al., 2014 tech report; CACM 2015), https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf
  - "So far we have used TLA+ on 10 large complex real-world systems."
  - the table lists S3, DynamoDB, EBS and a lock manager. CloudFront and caching are absent from the extracted text.
- Fastly purge docs, https://www.fastly.com/documentation/guides/concepts/edge-state/cache/purging/ (current)
  - semantics: "although it may still exist on disk, it won't be used to satisfy requests"
  - soft purge: "they'll be served the stale object and then the updated object will be retrieved from origin"
  - neither this page nor the shielding page states a propagation-time guarantee or how purge interacts with shields. Not found.

## Evidence: TLS revocation

- Langley, "Revocation checking and Chrome's CRL" (2014), https://www.imperialviolet.org/2014/04/19/revchecking.html
  - "So soft-fail is the only viable answer but it has a problem: it's completely useless."
  - "In short, it doesn't work and you are no more secure by switching it on."
- Let's Encrypt, "Ending OCSP Support in 2025" (2024-12-05), https://letsencrypt.org/2024/12/05/ending-ocsp/
  - "We plan to end support for OCSP primarily because it represents a considerable risk to privacy on the Internet."
  - "Must Staple has failed to get wide browser support after many years."
  - OCSP responders off on "August 6, 2025"
- CA/Browser Forum Ballot SC-081v3 (2025), https://cabforum.org/2025/04/11/ballot-sc081v3-introduce-schedule-of-reducing-validity-and-data-reuse-periods/
  - "Eventual reduction of maximum validity period from 398 days to 47 days", "starting in March 2026 and concluding in March 2029"
  - CRLs and OCSP "do not adequately protect relying parties at the current scale of the internet"
  - validity periods enforced by relying parties "are incredibly reliable"
  - "Not every potentially problematic certificate is revoked, let alone revoked in a timely manner."
- Measurement and engineering literature, but no formal verification of the deployed system (s3, s4):
  - CRLite (IEEE S&P 2017)
  - Let's Revoke (NDSS 2020)
  - Clubcards (S&P 2025): "over 900 million … certificates and over 8 million revoked certificates"
  - "Revocation speedrun" (2023): "35% can be made to accept a revoked certificate through the use of OCSP"
  - Kwon et al., ACM Computing Surveys 2026 (survey)
- Formal models exist only for alternative or niche designs (s6):
  - DTKI (Computer Journal 2016)
  - Khan et al. 2018: "The default adversary model used in Tamarin is a Dolev-Yao …"
  - LocalPKI ("formally proven alternative to PKIX")
  - "Formal verification of revocation approaches in identity-based cryptography"
  - V2X credential management
- Debnath 2025 thesis, a formally-guaranteed X.509 chain validator: notes "Mozilla's CRLite [134] being the only one deployed in practice" (revocation is context there, not something they verify)

## Gaps
- Not checked: Cloudflare or Fastly engineering posts on internal formal methods for purge. Also the AWS CACM HTML page (it returned 403; I used the 2014 PDF instead).
