# Jev score and error response shapes

Type: task
Status: resolved
Blocked by:

## Question

Call the Jev API with each question type (`choice`, `noul`, `score`), plus bad-key, malformed and timeout cases, and record the exact response and error shapes, latency, and the free-tier limits. Needs `OPENCODE_API_KEY` in the environment (the user exports it; it's never written to a file or logged). Carries over v1 ticket 05.

## Answer

Full write-up: `docs/research/jev-response-shapes.md`. Probed 2026-11-26 with 35 calls; key loaded from `.env` and never logged.

- A 200 response is `{model, answers:{id:{type,...}}, usage:{input_tokens, output_tokens, cost, opencode:{billing_source, list_cost, tokens}}}`. The only id is the `x-opencode-log-id` header.
- `choice` gives `{choice, confidence, probabilities}`, where confidence = p(top) − p(second). `noul` gives `{noul: P(yes)}`. `score` gives `{score, confidence, legend, probabilities}`; **score is the 0-based expected level index** (0..n-1) and the keys are `"0"`..`"n-1"`.
- Errors come in three shapes: gateway `{error:{type,message}}` (401 bad key, 402 paid models with no credits, 400 unknown model, 422 catch-all "Endpoint is unavailable" for a missing or invalid `questions`/`state`/criteria); upstream `{detail:{error_type,...}}` (400 bad question type, 400 `max_tokens_exceeded`); and an empty body (400 malformed JSON).
- The key only has access to `jev-1.13-free`. `jev-1.13` and `jev-1.14` return 402.
- The real input limit is about 32K tokens, not 64K. No rate-limit headers; no 429 seen.
- Latency p50 is about 1.2 s and max 3.4 s. Use a 5 s deadline with one retry.
- Not deterministic: probabilities jitter by ±0.02, but the decision stayed the same in 10/10 calls.

