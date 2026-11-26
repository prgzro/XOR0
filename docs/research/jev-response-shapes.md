# Jev response and error shapes (research)

Ticket: `.scratch/kronos-jev/issues/04-jev-response-shapes.md`. Gathered 2026-11-26 against `POST https://opencode.ai/inference/systemone/v1/systemone`, with the user's test key. Builds on `docs/reference/jev-opencode-zen-guide.md`.

Probe script and raw responses (session scratchpad, not in the repo; headers saved, key never written): `/tmp/claude-1000/-home-prgzro-Projects-XOR0/205c3630-a6e9-485f-b79e-e22a252b80f3/scratchpad/jev-probe/` (`probe.py`, one `<case>.json` per call). 35 calls in total. No 429 was seen.

The `state` sent was a made-up EURUSD H1 snapshot as a JSON object: last bars, ATR14, SQ9 levels, a Kronos-style forecast (`p_up` 0.66, median move 0.85 ATR, quantiles q10..q90 in ATR) and a candidate LONG with entry, SL and TP.

## TL;DR

- **Success shape:** `{ model, answers: { <questionId>: {...} }, usage: {...} }`. Every answer repeats its `type`. Probabilities come rounded to 2 decimals.
- **`score` (not documented before):** `{ type:"score", score, confidence, legend, probabilities }`. **`score` is the expected 0-based level index** (`Σ i·p_i`), so with 5 levels it runs 0..4, not 1..5. `legend` and `probabilities` are keyed by the strings `"0"`..`"n-1"`.
- **`choice`:** `confidence` = top probability minus second probability (0.89/0.11 gives 0.78). It is not the top probability.
- **`noul`:** a single number from 0 to 1, P(YES).
- **Errors have three different body shapes** and a malformed JSON body returns **400 with an empty body**. Missing or invalid `questions`/`state` gives **422 `server_error` "Endpoint is unavailable"**, not a validation message.
- **Access:** the key works for `jev-1.13-free` only. `jev-1.13` and `jev-1.14` return **402 Insufficient balance** (pay-as-you-go credits).
- **Real input limit is about 32K tokens, not 64K.** 30,050 input tokens worked. About 37K tokens returned 400 `max_tokens_exceeded`.
- **Latency:** p50 about 1.2 s, max 3.4 s over 10 identical calls. The server's own `server-timing` reports only 36–117 ms.
- **Not deterministic, but stable:** the same request gives the same pick and jitter of ±0.02 on the probabilities.
- **No rate-limit headers** come back (no `x-ratelimit-*`, no `retry-after`).

## Success response

Top level (HTTP 200, `Content-Type: application/json`):

```
{
  model:   string                     // echoes the request, e.g. "jev-1.13-free"
  answers: { [questionId]: Answer }   // one entry per question key sent, in the same order
  usage: {
    input_tokens:  int                // 1071 for the 3-question snapshot
    output_tokens: int                // depends on the questions: score 17, noul 23, choice 39, all three 72
    cost: number                      // 0 on the free tier
    opencode: {
      billing_source: "free"
      list_cost: number               // 0
      tokens: { input:int, output:int, reasoning:0, cache_read:0, cache_write_5m:0, cache_write_1h:0 }
    }
  }
}
```

The body has no response id. The only id is the `x-opencode-log-id` header (a UUIDv7). Log it for support.

### `choice`

Request: `criteria: { APPROVE_LONG: "...", NO_TRADE: "..." }`.

```
{
  type: "choice",
  choice: string,                          // one of the criteria keys
  confidence: number [0,1],                // = p(top) - p(second)
  probabilities: { [criteriaKey]: number } // all keys present, sum ≈ 1 (rounded to 2dp)
}
```

Observed: `{"type":"choice","choice":"APPROVE_LONG","confidence":0.78,"probabilities":{"APPROVE_LONG":0.89,"NO_TRADE":0.11}}`

### `noul`

Request: no `criteria`.

```
{ type: "noul", noul: number [0,1] }   // P(YES). No confidence field.
```

Observed: `{"type":"noul","noul":0.21}` for "critical risk?".

### `score`

Request: `criteria: ["1 - Very poor: no edge", ..., "5 - Excellent: strong edge, well-placed SL/TP"]` (array, 5 levels).

```
{
  type: "score",
  score: number [0, n-1],                // expected level index, Σ i·p_i (0-based)
  confidence: number [0,1],              // the formula is not clear (0.79–0.82 here)
  legend: { "0": criteria[0], ..., "n-1": criteria[n-1] },   // echoes the request array
  probabilities: { "0": p0, ..., "n-1": p(n-1) }             // sum ≈ 1
}
```

Observed: `score 2.99`, `probabilities {"0":0,"1":0.02,"2":0.08,"3":0.79,"4":0.11}`. The most likely level is index 3 = "4 - Good". To get the 1..5 label scale, use `score + 1`, or take the argmax of `probabilities`.

### Combined vs single

The three questions in one request gave the same answers as each question sent alone, within the jitter (choice 0.89 vs 0.91, noul 0.21 vs 0.20, score 2.99 vs 3.01). One combined call costs 1071 input tokens. Three separate calls cost 936 + 895 + 946. **Batch the questions into one call.**

`state` sent as a JSON string instead of an object gave the same answers (noul 0.24 vs about 0.20).

## Errors

| Case | HTTP | Body |
| --- | --- | --- |
| Fake key (`oc_fake_...`) | 401 | `{"error":{"type":"authentication_error","message":"Invalid credential"}}` |
| Empty bearer | 401 | same as the fake key |
| Malformed JSON (truncated) | 400 | **empty body**, no `Content-Type` |
| `questions` missing | 422 | `{"error":{"type":"server_error","message":"Upstream request failed: Endpoint is unavailable."}}` |
| `questions: {}` | 422 | same as `questions` missing |
| `state` missing | 422 | same as `questions` missing |
| `score` with object criteria | 422 | same as `questions` missing |
| `choice` with no criteria | 422 | same as `questions` missing |
| Unknown model `jev-9.99-nope` | 400 | `{"error":{"type":"server_error","message":"Upstream request failed: Model is unavailable."}}` |
| Unknown question type `ranking` | 400 | `{"detail":{"error_type":"api_usage_error","message":"Invalid request."}}` |
| Too many tokens (about 37K and up; 1.1 MB also tried) | 400 | `{"detail":{"error_type":"max_tokens_exceeded"}}` (no message) |
| `jev-1.13` / `jev-1.14` with no credits | 402 | `{"error":{"type":"invalid_request_error","message":"Insufficient balance. This request is pay-as-you-go, billed to OpenCode Models credits. Top up at https://opencode.ai/console/wrk_[REDACTED]/billing?credits=1. ..."}}` |
| 429 / 5xx | not seen | Expect the gateway shape `{error:{type,message}}` |

There are three error body shapes:

1. Gateway: `{ error: { type: string, message: string } }`. Seen with 401, 402, 400 (model) and 422.
2. Upstream (System One): `{ detail: { error_type: string, message?: string } }`. Seen with 400.
3. Empty body. Seen with 400 for unparsable JSON.

Notes:
- 422 "Endpoint is unavailable" is the gateway's catch-all for a schema-invalid body. It says nothing about what is wrong, so validate on the client before sending.
- The 1.1 MB payload took 56 s to come back, mostly upload time. Cap the payload size on the client.
- A 2 s client timeout never fired (that call took 1.1 s). A 300 ms read timeout aborted cleanly with no partial body. Python's urllib timeout counts per socket operation, which is why the abort came at about 1.2 s total. In Node, use `AbortSignal.timeout(ms)` as a hard total deadline.

## Headers

Every response has `x-opencode-log-id` (UUIDv7) and `server-timing: gateway;dur=..., upstream;dur=..., total;dur=...`. Responses that reached the model also have `x-zen-model`, plus `Cf-Placement` and `CF-RAY`. There are **no rate-limit headers** of any kind, so free-tier limits can't be read ahead of time. Handle 429 on the client with backoff. The 402 and 401 responses have no `upstream` part in `server-timing`, because they are rejected at the gateway.

## Latency (10 identical 3-question calls, jev-1.13-free, client in EU)

| Metric | Client wall time | `server-timing total` |
| --- | --- | --- |
| min | 893 ms | 36 ms |
| p50 | 1,209 ms | 61 ms |
| mean | 1,688 ms | 68 ms |
| max | 3,385 ms | 117 ms |

Sorted client times: 893, 937, 1055, 1143, 1158, 1259, 1797, 2397, 2860, 3385 ms. Each call used a new TLS connection (`Connection: close`). Most of the time is network, TLS and edge queueing, not the model. Bigger inputs are slower: 20K tokens took 3.5 s, 30K took 3.2 s. **A 5 s deadline with one retry is a safe default** for an H1 decision.

## Determinism

The same request sent 10 times was **not bit-identical, but the decision was stable**:

- choice: APPROVE_LONG 10/10. p(APPROVE_LONG) ranged 0.89–0.92, confidence 0.78–0.84.
- noul: 0.19–0.21.
- score: 2.99–3.06, argmax level 3 every time.

There is no seed or temperature control. Treat about ±0.03 as noise. Don't set thresholds that a 0.02 wobble can flip, for example require `p ≥ 0.60`, not `p > 0.50` on the margin. Log the raw probabilities so you can tell a real flip from jitter.

## Validation checklist for the `jev` module

Before sending:
- [ ] `model` is in an allow-list; default `jev-1.13-free`. A paid model returns 402 until there are credits.
- [ ] `state` is present and not empty (object or string).
- [ ] `questions` has at least one entry. Each `type` is in {`choice`,`noul`,`score`} (map `boolean` to `noul`), and `instructions` is a non-empty string.
- [ ] `choice.criteria` is an object with 1–255 keys. `score.criteria` is an array of 1–10 strings. `noul` has no criteria.
- [ ] The serialized body is under a byte cap (about 60 KB, which keeps it under about 25K tokens) to stay well below the ~32K-token limit.
- [ ] `AbortSignal.timeout(5000)` is set, with at most one retry on network error, timeout, 429 or 5xx (exponential backoff with jitter). Don't retry on 400, 401, 402 or 422.

Parsing the response:
- [ ] Read the body as text first. An empty body or non-JSON body is an error, using the HTTP status.
- [ ] Non-2xx: get the message from `body.error.message`, or `body.detail.message`, or `body.detail.error_type`, or the status text. Log `x-opencode-log-id`.
- [ ] 200: `answers` is an object and has **exactly** the question ids that were sent.
- [ ] Each answer's `type` matches the type requested.
- [ ] `choice`: `choice` is one of the criteria keys, `probabilities` has every key, each value is in [0,1], they sum to 1 ± 0.03, and `confidence` is in [0,1].
- [ ] `noul`: `noul` is a finite number in [0,1].
- [ ] `score`: `probabilities` has keys `"0"`..`"n-1"` for the n criteria sent, values in [0,1], sum to 1 ± 0.03. `score` is in [0, n-1]. Convert to 1-based (`score + 1`) in one place only, and keep the argmax level too.
- [ ] Record `usage.input_tokens`, `usage.cost` and `usage.opencode.billing_source`. Alert if `billing_source != "free"` or `cost > 0` happens when you didn't expect it.
- [ ] Any validation failure counts as **NO_TRADE**. Fail closed and never default to an approve.
