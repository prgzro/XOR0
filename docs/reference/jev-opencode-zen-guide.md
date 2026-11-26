# Jev on OpenCode Zen: Setup & Usage Guide

> Source: the user's Anytype note of the same name, written 2026-11-25, tested against `jev-1.13-free`. Copied here as the integration reference for the Jev bridge.

## What Jev is

Jev is a decision model made by TypeSafe (System One). It is not a chat or coding model:

- You give it some text (or a JSON object, or images) and one or more typed questions.
- It returns structured answers with probabilities, not written prose.
- It does not look anything up. It judges only from the text and what it already knows.
- It is not usable as an agent model in the OpenCode CLI. Call it over HTTP.

| Model ID | Price (per 1M tokens) | Context |
| --- | --- | --- |
| `jev-1.13-free` | Free | 64K |
| `jev-1.13` | $0.042 input, $0 output | 64K |
| `jev-1.14` | $0.042 input, $0 output | 64K |

Inputs: text, PNG, JPEG. No tools, no reasoning, no temperature controls.

## Requirements

- OpenCode Zen API key (`oc_sk_...`) in `OPENCODE_API_KEY`. Never in code or commits.
- Node.js 18+ (built-in `fetch`, no npm packages).

## The API

```
POST https://opencode.ai/inference/systemone/v1/systemone
Authorization: Bearer <OPENCODE_API_KEY>
Content-Type: application/json
```

Request:

```json
{
  "model": "jev-1.13-free",
  "state": "I was charged twice. Please refund the duplicate.",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": { "billing": "Charges and refunds", "support": "Other requests" }
    },
    "requestsRefund": { "type": "noul", "instructions": "Is the customer requesting money back?" }
  }
}
```

- `state`: the text to judge. It can also be a JSON object.
- `questions`: any number of named questions; each key becomes a key in `answers`.

| Type (wire name) | What it does | `criteria` |
| --- | --- | --- |
| `choice` | Picks one option | Object `{ option: "description" }`, 1–255 options |
| `noul` | Yes/no; returns probability of YES (0–1). Called `boolean` in the AI SDK. | none |
| `score` | Rates the text on a scale | Array of level descriptions, 1–10 levels |

Response:

```json
{
  "model": "jev-1.13-free",
  "answers": {
    "department": {
      "type": "choice",
      "choice": "billing",
      "confidence": 1,
      "probabilities": { "billing": 1, "support": 0 }
    },
    "requestsRefund": { "type": "noul", "noul": 0.98 }
  },
  "usage": {
    "input_tokens": 334, "output_tokens": 51, "cost": 0,
    "opencode": { "billing_source": "free" }
  }
}
```

**Not documented:** the response shape of a `score` answer, and the error-body shapes for 401/429/5xx.

## curl

```bash
curl -s -X POST https://opencode.ai/inference/systemone/v1/systemone \
  -H "Authorization: Bearer $OPENCODE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"jev-1.13-free","state":"The sky is green.","questions":{"answer":{"type":"noul","instructions":"Is this statement true?"}}}'
```

## Reference client (decide.mjs)

```js
const API_URL = 'https://opencode.ai/inference/systemone/v1/systemone';
const MODEL = 'jev-1.13-free';

export async function decide(state, questions, { apiKey = process.env.OPENCODE_API_KEY, model = MODEL } = {}) {
  if (!apiKey) throw new Error('Set OPENCODE_API_KEY');
  // The wire format calls boolean questions "noul".
  const wireQuestions = Object.fromEntries(
    Object.entries(questions).map(([id, q]) => [id, q.type === 'boolean' ? { ...q, type: 'noul' } : q]),
  );
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}`, 'content-type': 'application/json' },
    body: JSON.stringify({ model, state, questions: wireQuestions }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`Jev ${res.status}: ${JSON.stringify(body)}`);
  return body.answers;
}
```

Score example (request side):

```js
urgency: { type: 'score', instructions: 'How urgent is this?', criteria: ['Not urgent', 'Somewhat urgent', 'Very urgent'] }
```

## Tested results

| Text | Question | Result |
| --- | --- | --- |
| "I was charged twice. Please refund the duplicate." | department | billing, 100% |
| same | requests refund? | 0.98 |
| "My app crashes every time I open settings" | department | support, 100% |
| same | requests refund? | 0.04 |
| "The sky is green." | Is this statement true? | 7% yes |
| "I love this product, works great!" | sentiment | positive, 100% |

All calls billed `"billing_source": "free"`, cost $0.

## AI SDK alternative (untested)

`npm i ai @ai-sdk/typesafe-ai`; `createTypeSafeAi({ baseURL: 'https://opencode.ai/inference/systemone/v1' })` (the provider appends `/systemone`). Supports `providerOptions.typesafe.longContext: true` (262K context, slower, less accurate) and PNG/JPEG inputs.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| HTTP 404 | URL must end in `/systemone/v1/systemone`. |
| `jev-1.13-free` missing from `opencode models` | Expected: it's a decision model; the CLI doesn't list it. |

## Provenance

- `https://opencode.ai/zen/v1/models` lists Jev with `"type": "decision"`, `"recommended_api": "systemone"`.
- `@ai-sdk/typesafe-ai` source: requests go to `<baseURL>/systemone`; boolean questions are sent as `"noul"`.
