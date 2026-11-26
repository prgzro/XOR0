---
Status: accepted
---

# NautilusTrader v2 is the engine; its order execution is gated on a spike

2026-11-26. We run backtests and SIGNAL_ONLY on NautilusTrader v2 (pinned `2.0.0rc9` until 2.0.0 final ships, Python 3.13). The main reason is that the same strategy code runs in backtest and live. We chose v2 over v1.231 because v1 is frozen and will only get security fixes for a short time after v2 ships. **PAPER execution through Nautilus is not committed yet.** It has to pass a spike first (`.scratch/kronos-jev/issues/09-nautilus-spike.md`). The reason is that open IB-adapter bugs affect restart reconciliation and IDEALPRO order rejects: #5598, #5428, #5350, #5619 and #5752. If the spike fails, Nautilus stays for backtesting only and orders go through a thin `ib_async` layer. Evidence: `docs/research/nautilustrader-ibkr.md`.

## Considered Options

- **Our own engine on `ib_async`:** simpler, but we would have to build backtest/live parity and reconciliation ourselves.
- **QuantConnect LEAN:** C#-first, and live trading on the hosted platform is paid.
- **Backtrader:** unmaintained since 2023.
- **vectorbt:** research only, with no live trading.
- **Nautilus v1.231:** runs on our Python 3.12, but is frozen.

## Consequences

- **Risk Gate:** it stays our own code, independent of Nautilus. It runs inside the strategy between Decision and order submission. Nautilus's RiskEngine has no hook for custom checks, so it is only a backstop (order size and rate limits). Its `HALTED` state is the kill switch.
- **Gateway:** Nautilus connects to our existing pinned gnzsnz IB Gateway (`127.0.0.1:4002`, its own client ID). It does not use its own `DockerizedIBGateway`. PAPER needs a separate read-write paper Gateway config. Live stays off.
- **Backtest data:** IBKR H1 BID and ASK bars, because mid bars model zero spread. XM history (bid only) is a cross-check only.
- **Backtest costs and fills:**
  - a custom IBKR fee model: FX `max(0.2 bp × notional, USD 2)`, gold commission configurable and unverified;
  - 1-tick seeded slippage;
  - trades where SL and TP are hit in the same bar are reported both ways.
