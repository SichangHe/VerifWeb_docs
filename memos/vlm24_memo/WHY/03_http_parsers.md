# HTTP parsers: proxy and server agree where a request ends
(authored by agents unless marked 🧑)

Who is hurt. Sites behind proxies and CDNs. If a proxy and a server split the same bytes into different requests, an attacker hides a second request inside the first ("request smuggling") and can hijack other users' requests.

Why testing does not fix it. Differential fuzzing keeps finding new cases: HTTP Garden found "122 unique parsing discrepancies" (2024); a 2025 follow-up reported 17 vulnerabilities and 9 CVEs. Vendors' fixes after HTTP Garden were themselves incomplete. Patching one case at a time does not show none remain.

Why a proof helps. "Every hop splits the stream the same way, for every byte stream" closes the whole class.

Contribution (opinion). Proving that forwarding preserves meaning across two parsers. Verified single parsers exist (EverParse); a two-parser proof we did not find.

Opinion. This fits proofs best but is the least novel and least connected to our group's data.

Questions
- is a well-known problem with a cleaner proof worth it, or too crowded?
