# part_res3: "Breadth first" paragraph of msg_1110_results.txt
(authored by agents unless marked 🧑)
Raw curl copies and text extracts: dl/res3/. All checked against the original pages.

## WRONG / overstated
1. "the bad updates passed validation" (about Cloudflare, Google Cloud, Azure, CrowdStrike together). Verdict: wrong as a blanket claim.
 - CrowdStrike, confirmed: https://www.crowdstrike.com/en-us/blog/falcon-content-update-preliminary-post-incident-report/ "Due to a bug in the Content Validator, one of the two Template Instances passed validation despite containing problematic content data."
 - Azure, partly: https://azure.status.microsoft/en-us/status/history/?trackingId=YKYN-BWZ "the configuration passed through the protection safeguard" (it passed the config protection/health check because the crash was asynchronous; the PIR also says "This defect escaped detection due to a gap in our pre-production validation").
 - Google Cloud, not validation: https://status.cloud.google.com/incidents/ow5i3PPK96RduMcb1SsW "it did not have appropriate error handling nor was it feature flag protected." No validator is mentioned.
 - Cloudflare 18 Nov: no "validation" statement found; page says the file "doubled in size" and the software had a size limit.
 Correct text: "CrowdStrike's bad update passed its validator; Azure's passed the protection/health gate; Google's had no flag protection; Cloudflare's size limit was exceeded."
2. Jepsen NATS "lost 679,153 of 1,367,069" needs context, number itself right. The loss was in the file-corruption test, not a plain crash (see below). Verdict: number confirmed, framing incomplete.

## CONFIRMED
- Cloudflare 18 Nov 2025, https://blog.cloudflare.com/18-november-2025-outage/ : "Today was Cloudflare's worst outage since 2019." Panic text: "thread fl2_worker_thread panicked: called Result::unwrap() on an Err value". Cause: "a change to one of our database systems' permissions" producing a doubled "feature file". (Config file = feature file, ok.)
- FL2 is Rust: https://blog.cloudflare.com/5-december-2025-outage/ "our new FL2 proxy, which is written in Rust".
- Google Cloud 12 Jun 2025: "Incident began at 2025-06-12 10:51 and ended at 2025-06-12 18:18 (all times are US/Pacific)"; "the null pointer caused the binary to crash"; "This occurred globally given each regional deployment."
- Azure Front Door 29 Oct 2025: "Between 15:41 UTC on 29 October and 00:05 UTC on 30 October 2025 ... connection timeout errors"; crash "during asynchronous processing within the data plane service".
- CrowdStrike 2024: "On Friday, July 19, 2024 at 04:09 UTC, as part of regular operations, CrowdStrike released a content configuration update"; reverted 05:27 UTC.
- AWS us-east-1, https://aws.amazon.com/message/101925/ : "the first Enactor (which had been unusually delayed) applied its much older plan to the regional DDB endpoint, overwriting the newer plan." Start/end: "started at 11:48 PM PDT on October 19 and ended at 2:20 PM PDT on October 20" = 14 h 32 min, so ~14.5 h correct. (Quote with ellipsis "applied its much older plan ... overwriting the newer plan" is faithful: omitted words are "to the regional DDB endpoint,".)
- Jepsen NATS, https://jepsen.io/analyses/nats-2.12.1 : "file corruption in this test run caused NATS to lose 679,153 acknowledged writes out of 1,367,069 total". Run dated Nov 2025 in the logs.
- etcd 2022, https://github.com/etcd-io/etcd/blob/main/Documentation/postmortems/v3.5-data-inconsistency.md (dated 2022-04-20): "Code refactor in v3.5.0 resulted in consistent index not being saved atomically."; "This operation is required to be atomic". Memo wording "non-atomic apply" fits.
- Browsers: https://cloud.google.com/blog/topics/threat-intelligence/2025-zero-day-review "Browsers accounted for less than 10% of 2025 zero-day exploitation".

## UNVERIFIABLE
- "AWS's own TLA+ program didn't cover it": the AWS page never mentions TLA+; this is an absence claim, the memo's own report labels it INFERENCE. Cannot be confirmed from a source.
