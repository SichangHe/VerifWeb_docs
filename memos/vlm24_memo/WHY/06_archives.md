# Archives and replay: JS rewrites keep page behavior
(authored by agents unless marked 🧑)

Who is hurt. Users and researchers of web archives, and now AI agent benchmarks that run on archived pages. Archives rewrite each page's JavaScript so it replays offline; wrong rewrites silently break pages. FidEx "reduced the fraction of archived pages which violate fidelity from 15% to 9%" (NSDI 2026), so 9% still fail.

Why testing does not fix it. FidEx finds errors by comparing a crawl run with a replay run. That needs both runs and finds errors after the fact.

Why a proof helps. A checker proved correct once could certify each rewrite for the page's actual state, without a paired run. This matches the advisor remark: "for the given state, what is the behavior".

Contribution (opinion). Checking each rewrite against its input (translation validation) exists for JIT compilers, not for archive rewriting (search only).

Fit (opinion). Strongest group fit: Harsha's archive data is something others lack.

I don't know whether most failing rewrites fit one small model; getters and dynamic dispatch may make them uncheckable. A two-week classification of FidEx failures would tell.

Questions
- is the archive team's failure data available?
