# Privacy and consent: a "no" stays "no"
(authored by agents unless marked 🧑)

Who is hurt. EU users who reject or revoke cookie consent. Sites store the choice in a "consent string" passed to ad vendors. "we analyzed 281 websites ... and found 22 websites that store a positive consent despite user's revocation", and on 101 sites vendors "are not informed of revocation" (PoPETs 2025). After users click reject, "72.8% of the websites that were TCF compliant claimed legitimate interest" instead (WWW 2024).

Why measurement does not fix it. The bug depends on the order of clicks and vendor reads, which crawlers rarely hit. Also, the standard itself defines no revocation path: "TCF v2.2 does not specify any URL parameters to be used for this".

Why a proof helps. A model checker tries every order of clicks and reads. Writing the model forces the spec gap into the open.

Contribution (opinion). The first formal model of consent protocols (none found, search only); harm is legal (GDPR), not crashes.

Evidence. Papers above; we ran nothing.

Questions
- is consent "web systems" enough, or too policy flavored?
- is finding a spec gap a result, or must we verify a real banner's code?
