# JEV QUANT v2 (Kronos + Jev + IBKR): wayfinder map

Label: `wayfinder:map`

## Destination

A buildable spec for Phases 0–6 of `JEV_QUANT_MASTER_PLAN.md` (v2): Kronos forecasts → Candidates → Jev Decision → Risk Gate → IBKR (SIGNAL_ONLY / PAPER / guarded LIVE), with backtest and Jev replay. No decision left open, and the Kronos edge test passed, ready for `/to-spec`.

## Notes

- Plan: `JEV_QUANT_MASTER_PLAN.md` (v2). Vocabulary: `GLOSSARY.md` (**Forecast**, **Candidate**, **Decision**, **Risk Gate**). Jev reference: `docs/reference/jev-opencode-zen-guide.md`.
- Standing decisions (user, 2026-11-26):
  - Universe: FX majors and crosses plus gold on IBKR.
  - Signals on H1, 400-bar lookback, 24-bar horizon.
  - Kronos samples many paths, a mechanical rule makes the Candidate, Jev approves or rejects, and the Risk Gate is authoritative.
  - Zero-shot edge test before any build.
  - One Python service; no MT4, MQL4 or Node.
  - Modes: SIGNAL_ONLY, then PAPER (IBKR paper account), then guarded LIVE. The default is PAPER, and LIVE is never enabled by the agent.
- Account (user, 2026-11-26): IBKR **paper**, USD 1,000,000, 1% risk per trade for tests; user resident in Egypt, so spot XAUUSD is expected to be available. Test credentials and the Jev key are in `.env` (gitignored). The user reports that 2FA is needed for web logins but not for their installed desktop client.
- Hardware: GTX 1650 4 GB, 16 cores, 23 GB RAM.
- Existing data: XM H1 history 2020-02 → 2026-11 for all 12 symbols in `~/.wine-jevquant/drive_c/JevQuantMT4/history/XMGlobal-Demo 2/*.hst` (read copies only). Cost and edge-test methodology to reuse: `docs/research/edge-revalidation.md`.
- The MT4 isolation rule from v1 still applies if MT4 is ever touched again: never run anything inside `~/.wine`.
- Edge test universe (user, 2026-11-26): **the 7 FX majors only**. Gold follows as a separate test once the majors pass. The crosses are not in the Edge test.
- User goal (2026-11-26): **2–6% a month**. It is reported as a target check in the Edge test and never used as an objective to tune for. The quant skills in `.claude/skills/` (lookahead, reproducibility, research log, deflated metrics, Monte Carlo, authenticity audit) are part of the Edge test.
- Skills: `grilling` + `domain-modeling` for grilling tickets, `research` for research tickets. Research outputs go to `docs/research/<slug>.md`.

## Decisions so far

- [v1 SQ9 map (closed)](../jev-quant/map.md): SQ9 levels showed no edge, so the destination was redrawn to Kronos + Jev on IBKR.
- [Kronos training data and cutoff](issues/01-kronos-training-cutoff.md): treat **every bar before 2025-07-01 as possibly seen in training** (paper data runs to June 2024; weights were uploaded 2025-06-30, and it's unconfirmed whether they match the paper). FX H1 *was* in pretraining (1,023 pairs, 5m–W, from 2020); gold probably wasn't. The paper has no FX trading result, and FX forecast correlation is only ≈0.02–0.05. User reports to check: forecasts drift back to the window mean, and dropout stays on unless the model is put in eval mode. [write-up](../../docs/research/kronos-training-data.md)
- [IBKR API, products and costs for FX + gold](issues/03-ibkr-api-and-products.md): IB Gateway runs in Docker (`gnzsnz/ib-gateway-docker` + IBC, pin the tag) with paper port 4002; it needs a manual 2FA login once a week. The library is `ib_async` 2.0.1, with `bracketOrder()`. IDEALPRO min is USD 25k; smaller orders go to IDEAL and fill ~1–2 bp worse. Commission is 0.20 bp with a USD 2 minimum. Spot XAUUSD isn't offered to US/CA/AU/HK/JP residents (alternative: MGC futures, 10 oz, needs rolling). FX history is MIDPOINT/BID/ASK only, at 60 requests per 10 min. Prices came from search snippets because the IBKR pages blocked fetches, so verify them before using them as constants. [write-up](../../docs/research/ibkr-api-and-products.md)
- [Jev score and error response shapes](issues/04-jev-response-shapes.md): `choice` → `{choice, confidence (top minus second probability), probabilities}`; `noul` → P(yes); `score` is **0-based** (5 levels give 0–4) plus a legend and probabilities. There's no request id in the body (only the `x-opencode-log-id` header). Errors come in 3 body shapes (`error{type,message}`, `detail{error_type}`, an empty body), and bad requests return a vague 422, so validate before sending. The key works only for **jev-1.13-free** (the others return 402). Real input limit ≈32K tokens. p50 1.2 s, max 3.4 s, so use a 5 s deadline and one retry. Probabilities vary ±0.02 between calls, but the decision was stable 10/10. [write-up](../../docs/research/jev-response-shapes.md)
- [Kronos install and speed on this machine](issues/02-kronos-on-this-machine.md): **Kronos-small, N = 30, at 8.6 Forecasts/s** on the GTX 1650 (12-symbol cycle 1.4 s; full Edge test ≈1.7 days). Base is 3.6/s, which is over the 3-day budget. The vendor loop was 68× slower, averaged the paths and left dropout on. Our KV-cached sampler is bit-identical and independent of batching. Kronos reverts to the window mean even on a random walk. [write-up](../../docs/research/kronos-install-speed.md)
- [IBKR paper account access](issues/05-ibkr-account-setup.md): IB Gateway `ghcr.io/gnzsnz/ib-gateway:10.50.1h` (paper, read-only, 127.0.0.1:4002) logs in with **no 2FA**, but only while no other session uses the username. The paper account holds USD 1M. All 11 FX pairs resolve on IDEALPRO with free real-time quotes (EURUSD spread 0.3 pip). **Spot XAUUSD is available**; MGC has no data subscription. History goes back to 2005 (NZDUSD 2007, XAUUSD 2010). XM closes sit 1.1 pip below the IBKR mid (bid vs mid), with a 0.1-pip median gap after removing that offset. XM server time is UTC+2/+3 (EU DST). Open: a dedicated API username, and the weekly re-authentication. [write-up](../../docs/research/ibkr-paper-connection.md)

## Not yet specified

- **Candidate and SL/TP rule details beyond the edge test:** for example, re-forecast cadence on an open position, and exits other than SL/TP.
- **Jev snapshot content and thresholds:** these become sharp once the Jev response shapes are known and the edge test shows which Forecast features matter.
- **Risk Gate defaults across correlated FX:** exposure grouping and limits.
- **Runtime and operations:** process supervision, IB Gateway lifecycle and daily restarts, GPU memory, scheduling at bar close.
- **Journal schema and analytics cut.**
- **Fine-tuning Kronos:** only if the zero-shot test fails, as a separate pre-registered experiment.

## Out of scope

- SQ9 levels, the V2 indicator and MT4/XM execution (v1, archived).
- Phase 7 operations and the decision to go LIVE.
- Training Kronos-large or anything that doesn't fit this machine.
