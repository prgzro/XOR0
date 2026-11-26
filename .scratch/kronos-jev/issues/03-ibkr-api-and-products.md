# IBKR API, products and costs for FX + gold

Type: research
Status: resolved
Blocked by:

## Question

From IBKR's primary docs, find:
- how a Linux Python service connects: IB Gateway (headless or Docker, daily restart, 2FA), the TWS API vs `ib_async`, and the paper-account port;
- IDEALPRO FX minimum and odd-lot sizes, increments and commissions;
- how gold can be traded: spot XAUUSD (who is eligible) vs MGC/GC futures, with contract specs and commissions;
- historical H1 data depth and pacing limits;
- bracket orders (entry plus SL/TP) and margin.

Output: the facts the Risk Gate and execution need, with sources.

## Answer

Full write-up with citations: [`docs/research/ibkr-api-and-products.md`](../../../docs/research/ibkr-api-and-products.md).

- **Connection.** Run IB Gateway headless in `gnzsnz/ib-gateway-docker` (IB Gateway + IBC). Use port 4002 for paper and 4001 for live. TWS uses 7497 and 7496. Set `AUTO_RESTART_TIME` for the daily restart. A manual 2FA login is needed once a week, after Sunday 01:00 ET. Use `ib_async` v2.0.1 (Python ≥3.10). It throttles to 45 requests/s and has a `bracketOrder()` helper. Pin the Docker image tag, because the README announces a breaking IBC to ibcontroller switch no earlier than 2027-01-10.
- **IDEALPRO.** The minimum is USD 25k equivalent and the maximum about USD 7M. Smaller orders are odd lots routed to IDEAL at 1-3 ticks / about 1-2 bp worse. Quantity is in base-currency units, with no lots. Read the tick size from `minTick`. The commission is 0.20 bp of trade value with a USD 2.00 minimum per order (Tier I).
- **Gold.** XAUUSD (CMDTY, 1 oz, 1.5 bp with a USD 2 minimum) is for non-US residents only. Residents of the US, Canada, Australia, Hong Kong and Japan, and IB Singapore clients, are excluded. US residents can use USGOLD or MGC. MGC is 10 oz with a $1 tick, costs USD 0.25 per contract plus about USD 0.70 in exchange fees, is physically delivered, and must be rolled before IBKR's close-out deadline.
- **History.** FX supports MIDPOINT, BID, ASK and BID_ASK, but not TRADES. Pacing allows at most 60 requests in 10 minutes, no identical request within 15 s, and fewer than 6 requests per contract in 2 s. BID_ASK counts double. There is no published depth, so use `reqHeadTimeStamp`.
- **Orders and margin.** Brackets are a parent plus children, with `transmit=False` on every leg except the last. A stop may be simulated. FX margin is about 2% (50:1) per an old IBKR document, so check it at runtime with `whatIfOrder`.
- **Market data.** FX data is free. CME futures need a paid subscription.
- **Caveat.** interactivebrokers.com and cmegroup.com blocked direct fetches, so many IBKR figures come from search extracts and are tagged [snippet]. Check them live before relying on them.
