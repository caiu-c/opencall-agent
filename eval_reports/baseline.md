# RAG evaluation report

- Generated: 2026-04-20T20:48:27+00:00
- Rows evaluated: 30
- Retrieval recall (must_cite ∩ retrieved): 28.3%
- Anchor coverage (must_contain): 52.2%
- Latency p50 / p95: 10.19s / 15.86s
- Refusal false-negatives: 0

## By category

| Category | N | Recall | Anchors |
|----------|---|--------|---------|
| faq | 6 | 50.0% | 77.8% |
| politica | 13 | 11.5% | 41.0% |
| produto | 2 | 75.0% | 83.3% |
| regulatorio | 5 | 10.0% | 33.3% |
| transcricao | 4 | 50.0% | 58.3% |

## Per-row

| id | cat | recall | anchors | latency |
|----|-----|--------|---------|---------|
| q01 | politica | 0.0% | 50.0% | 8.24s |
| q02 | faq | 50.0% | 100.0% | 15.86s |
| q03 | politica | 0.0% | 66.7% | 11.90s |
| q04 | politica | 0.0% | 50.0% | 8.60s |
| q05 | faq | 50.0% | 100.0% | 12.49s |
| q06 | faq | 100.0% | 100.0% | 16.79s |
| q07 | faq | 50.0% | 0.0% | 13.91s |
| q08 | politica | 0.0% | 0.0% | 3.99s |
| q09 | politica | 50.0% | 66.7% | 10.54s |
| q10 | politica | 0.0% | 0.0% | 8.81s |
| q11 | faq | 0.0% | 66.7% | 8.95s |
| q12 | politica | 50.0% | 100.0% | 14.71s |
| q13 | regulatorio | 0.0% | 50.0% | 10.98s |
| q14 | politica | 0.0% | 0.0% | 1.69s |
| q15 | regulatorio | 0.0% | 0.0% | 1.45s |
| q16 | produto | 100.0% | 66.7% | 12.26s |
| q17 | politica | 50.0% | 100.0% | 11.77s |
| q18 | politica | 0.0% | 0.0% | 8.65s |
| q19 | politica | 0.0% | 0.0% | 8.79s |
| q20 | regulatorio | 0.0% | 50.0% | 8.00s |
| q21 | politica | 0.0% | 0.0% | 10.19s |
| q22 | faq | 50.0% | 100.0% | 13.41s |
| q23 | politica | 0.0% | 100.0% | 9.16s |
| q24 | produto | 50.0% | 100.0% | 8.57s |
| q25 | regulatorio | 0.0% | 0.0% | 8.70s |
| q26 | transcricao | 50.0% | 100.0% | 11.01s |
| q27 | transcricao | 50.0% | 50.0% | 11.55s |
| q28 | transcricao | 66.7% | 33.3% | 6.85s |
| q29 | transcricao | 33.3% | 50.0% | 12.48s |
| q30 | regulatorio | 50.0% | 66.7% | 9.48s |
