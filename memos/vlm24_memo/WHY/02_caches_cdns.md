# Caches and CDNs: cache keys that follow the standard
(authored by agents unless marked 🧑)

Who is hurt. Any logged-in user of a site behind a shared cache. If the cache key misses something, the cache serves one user's private page to another. "2512 websites include some header names in the Vary response header but do not configure their web cache(s) to include them in the cache key" (arXiv 2407.16303). Separately, a CDN and the origin server can read one URL differently: `/myAccount;x.css` returns the account page while the CDN stores it as a public stylesheet; 1,188 of the top 10K sites were vulnerable (USENIX Security 2022).

Why testing does not fix it. Inputs are all possible URLs and header spellings; the bugs live in rare characters. Scanners find some broken sites, not all.

Why a proof helps. The cache-key function is small and pure. A solver can prove two URL readers agree, or print the exact URL where they differ.

Contribution (opinion). Proving two different programs (CDN and origin) agree, rather than one program against a spec. We found no verified cache-key function (search only).

Evidence. Measurement papers above; no experiments of ours.

Questions
- is a CDN config bug "web verification" enough, or too operational?
- which side would we verify: a real CDN, or a reference to diff CDNs against?
