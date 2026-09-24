# Recommendation Engine — 50-Persona Test Suite

**Run:** Sep 24 2026, 22:05 UTC | **Target:** api.inferenceindexer.ai /v1/recommend (SSR)
**Score: 724/800 (90%)** — 37 PASS / 9 WEAK / 4 FAIL
**Latency:** median 78ms, p90 95ms, max 784ms (cached path)
**Re-run:** `engine_harness.py` (see /engine-harness/) — re-run after any engine change.

## What is graded (16 per persona)
1. PARSE — parser extracts the constraint tuple the persona intends
2. ANSWER — correct answer type (ranked models / provider list / per-provider compare)
3. COMPLIANCE — every returned result verifiably satisfies every constraint
4. SANITY — ranks contiguous 1..n, AA scores present, `why` strings present

## FAILS (4) — all one root cause family: parser gaps
| ID | Request | Root cause |
|---|---|---|
| RA03 | "...200k-token knowledge base" | Parser: "200k-token" before the word "context" — regex needs `Nk token` (not only `Nk context`) |
| LC03 | "1M token context" | Parser: no "1M" (million) support; only Nk |
| BV02 | "classify 5 million rows... cheapest" | Nothing parsed: "5 million" read as volume, no budget; fail-loud triggered correctly but persona needs volume synonym -> use_case=volume |
| ST01 | "MVP chatbot. Cheapest..." | Nothing parsed: "chatbot" not mapped; fail-loud correct but a synonym for chatbot->support and cheapest->(no budget) is needed |

Note: BV02 + ST01 fail-loud IS the designed behaviour (never guess). The gap is synonyms, not safety.

## WEAKS (9) — mostly persona-expectation vs parser philosophy
| ID | Issue | Verdict |
|---|---|---|
| CO02, CO06, SU04, LC01, AG01 | "PR review bot"/"unit tests"/"customer emails"/"chatbot" — job description but no literal coding/support keyword | PARTIAL-BY-DESIGN: keyword parser. Fix = add trade synonyms (PR review->coding, unit tests->coding, customer emails->support, briefs->summarization) |
| EX05 | "document parsing above AA 25" -> parsed aa_min only, use_case missing | Add "parsing"->extraction synonym |
| PR04, EU04 | "medical records ZDR"/"European infrastructure AA 30" routed to provider list (no price/model signal) | DEBATABLE: provider list IS a decent answer; expected models ranking. Router heuristic could pass price-signal context |
| PR06 | "German enterprise... AA 40" -> parsed EU only, missed AA 40 | Parser: "AA 40" needs the plain `AA N` pattern (exists) — check ordering; minor |

## Key insight
No compliance failures anywhere: every returned result satisfied every constraint.
All failures are parse/synonym gaps, and the fail-loud path worked correctly (never guessed).

## Priority fixes (est. 2h total)
1. Context regex: support `Nk-token`, `N million tokens`, `1M` (fixes RA03, LC03)
2. Synonyms: chatbot->support, PR review/unit tests/code migration->coding (already), briefs->summarization, parsing->extraction, classify rows->volume (fixes BV02, ST01, EX05, AG01)
3. Router: keep provider-list routing when NO price signal, but pass budget through when present (PR04/EU04 stay as-is — defensible)
