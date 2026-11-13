# Capture-recapture estimate of direction count
(authored by agents unless marked 🧑)

Bottom line: 75 distinct clusters observed. The estimated total is about 80 to 90. Treat this as a lower bound: the method assumes things these samplers violate.

Data (scripts/estimate.py, raw output estimate_raw.txt):
- Clusters hit per capture: browsersec 34, jsrt 21, pc 28, pl 34, gpt 45, gemini 26, prior work (W) 29.
- The six samplers hit 74 clusters. Adding prior work gives 75: one cluster, prototype integrity (TARGETS 11), appears only in prior work.
- Frequency counts, six samplers: f1=19, f2=21, f3=18, f4=9, f5=5, f6=2.

Estimates:
- Pairwise Chapman across the six samplers (15 pairs): median 66.7, range 54.7 to 91.3. Lincoln-Petersen gives nearly the same numbers.
- Pairwise Chapman with prior work as one of the pair (6 pairs): median 57.3, range 49.8 to 75.7.
- Chao1, six samplers: 81.2.
- Chao1 with prior work as a seventh capture: 81.9 (f1=17, f2=18).

Why the pairwise numbers are wrong:
- The median pairwise estimate (67) is below the 74 clusters actually observed. That is the signature of positive dependence: samplers that share a prompt and a meeting transcript find the same "obvious" directions (JIT, isolation, URL parser, runtime-state). This inflates overlap and deflates the estimate.
- The two-sample estimators assume equal catchability for every direction. That fails here: the four Claude samplers had assigned lenses, and the lens shifts which clusters each one finds.

Why Chao1 is also low:
- Chao1 is a lower-bound estimator even under heterogeneity. f1 of about f2 means the tail is still open.
- Clustering granularity sets the count. Merging or splitting clusters (e.g. treating the Lightpanda sub-items as several clusters) moves the total by ±10.

Assumptions:
- Closed population: the set of possible directions is fixed during sampling.
- Same prompt for all samplers.
- Prior work was produced earlier, by a different process. It is therefore the most independent capture.
- A cluster counts as caught by prior work if prior work at least partially covers it.

Inference: further samplers with the same prompt would add mostly singletons in the long tail, such as niche browser subsystems. A different prompt or a human would be needed to find directions outside the shared frame.
