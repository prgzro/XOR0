# XOR0: JEV QUANT

AI-assisted trading service: Kronos forecasts + Jev decision API + independent risk gate, executing on Interactive Brokers (Python). The master plan is `JEV_QUANT_MASTER_PLAN.md` (v2). The v1 SQ9/MT4 plan and its research are archived (`docs/archive/`, `docs/research/`).

- `indcators/` (spelled that way on purpose) holds the original AbuHamzah SQ9 indicators. Never rename, modify or delete them.
- Never enable live trading (default PAPER on the IBKR paper account). Never commit secrets (`.env` is gitignored).

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix), recorded as a `Status:` line. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
