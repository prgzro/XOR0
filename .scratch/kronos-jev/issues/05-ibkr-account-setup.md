# IBKR paper account access

Type: task
Status: resolved
Blocked by: 03

## Question

HITL. Does the user have an IBKR account with a paper-trading login? Once ticket 03 shows how to connect, give the user a precise checklist: enable the paper account, install and log in to IB Gateway, enable the API, set the port and read-only first. Then verify a read-only connection (account summary, an EURUSD H1 history request) from this machine. Credentials stay in `.env` or Gateway only.

## Answer

Resolved 2026-11-26, read-only, no orders. Headless IB Gateway 10.50.1h with IBC 3.24.2 (`gnzsnz/ib-gateway`, pinned equal to stable) runs in paper mode with a read-only API on 127.0.0.1:4002 (container `jevquant-ibgw`). `ib_async` 2.0.1 connects with `readonly=True`.

- **Login:** no 2FA was needed for paper. It works only when no other session of the same username is logged in. The first attempt hit "Existing session detected"; after the user logged out elsewhere it went straight through.
- **Account:** `DU…` paper account, NetLiquidation 1,000,000 USD (base USD, inferred).
- **FX:** all 11 pairs resolve on IDEALPRO with minTick 0.00005 (JPY pairs 0.005) and stream real-time quotes for free.
- **Gold:** XAUUSD spot resolves with real-time quotes. MGC resolves, but its data is not subscribed.
- **History:** H1 history goes back to 2005 for most pairs. A 1-year request returns about 6,200 H1 bars, and EURUSD H1 MIDPOINT was pulled for 3 years.
- **IBKR vs XM:** XM closes sit a steady 1.1 pip below the IBKR mid (bid against mid). After removing that bias the median gap is 0.1 pip. XM time is EET/EEST with EU DST rules.

Details: [docs/research/ibkr-paper-connection.md](../../../docs/research/ibkr-paper-connection.md).
