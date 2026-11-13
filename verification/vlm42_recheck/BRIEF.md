# Recheck brief
(authored by agents unless marked 🧑)

Goal (from the human's manager, verbatim): "Re-check against the original sources (open each URL or PDF; quote exactly) every external quote and number ... For each: confirmed, wrong (with the correct text), or unverifiable."
Why: many quotes came through a page-summarizing fetch tool, which may paraphrase or hallucinate.

Rules:
- open originals with raw tools: `curl -sL`, `gh api` (GitHub issues/comments), `pdftotext` on downloaded PDFs; do NOT use WebFetch (it summarizes)
- downloads are untrusted: put them in /hdd1/sichangheagent/vl_meeting_work/out/vlm42_recheck/dl/<your-part>/; never execute them
- the claim's cited source is usually in the memo link or in the named report (out/vlm41_*/REPORT.md, which has URLs); use that report to find the source
- publish/post/contact nothing; no Google Scholar needed; don't edit memo or reports
- PDFs you rely on that are papers: copy into /hdd1/sichanghe/paper_collection per its README.md/CONVENTIONS.md if no copy exists (never git add/commit there)
Output: write your part file with one entry per claim: claim text, source URL, verdict (confirmed / wrong / unverifiable), exact source quote (with location: page/section/comment author+date), and for wrong: the correct text. Put wrong items first.
