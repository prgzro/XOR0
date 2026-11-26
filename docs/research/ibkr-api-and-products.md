# IBKR API, products and costs for FX and gold

Research for `.scratch/kronos-jev/issues/03-ibkr-api-and-products.md`. Researched 2026-11-26.

**Source access note.** Every `interactivebrokers.com` page (pricing, FAQ, IBKR Campus and the new `/docs/tws-api/` docs) and `cmegroup.com` returned HTTP 403 or timed out when fetched directly. Facts from those pages come from search-engine extracts of the official page, not a full read, and are tagged **[snippet]**. Facts from pages read in full (the legacy TWS API docs at `interactivebrokers.github.io`, ibkrguides.com, and GitHub source and READMEs) carry no tag. **[UNVERIFIED]** marks anything no primary source confirmed. Re-check every **[snippet]** price, margin or size against the live page before it becomes a Risk Gate constant.

## TL;DR

- **Connection.** Run IB Gateway headless in Docker (`gnzsnz/ib-gateway-docker`, which bundles IBC), with `TRADING_MODE=paper`. Use API port **4002** for paper and **4001** for live. TWS uses 7497 for paper and 7496 for live. Set `AUTO_RESTART_TIME` for the daily restart. Plan on **one manual 2FA login a week**, because tokens reset Sunday 01:00 ET. Use **`ib_async`** (v2.0.1, Python ≥3.10, BSD-2) rather than the raw `ibapi`. It has a built-in `bracketOrder()` helper and throttles itself to 45 requests/s.
- **FX sizing.** The IDEALPRO minimum is **USD 25,000 equivalent** (EUR 20,000) per order. The standard maximum is about USD 7M. Smaller orders are **odd lots**: IBKR routes them automatically to IDEAL and fills them **1-3 ticks / about 1-2 bp worse** than the IDEALPRO quote. Quantity is in units of the base currency, and IBKR has no lot concept. Read the price tick from `ContractDetails.minTick` instead of hard-coding it.
- **FX commissions (IBKR Pro).** **0.20 bp × trade value, minimum USD 2.00 per order** at Tier I (up to USD 1B a month). The rate falls to 0.15, 0.10 and 0.08 bp at higher tiers. The USD 2.00 minimum dominates below about USD 100k notional, so it is the number the Risk Gate's cost model should use.
- **Gold.** London spot **XAUUSD** (`secType=CMDTY`, `SMART`, 1 oz units, $0.001 tick, 1.5 bp with a USD 2 minimum) is for **non-US residents only**. It is also closed to residents of Canada, Australia, Hong Kong and Japan, and to IB Singapore clients. US residents get **USGOLD** instead, or COMEX futures. **MGC** (E-micro, 10 oz, $0.10 tick = $1.00) costs USD 0.25 a contract in commission plus about USD 0.70 in exchange fees. **GC** is 100 oz. Both futures are physically delivered, and IBKR liquidates them before its close-out deadline, so the system must roll them.
- **History.** FX supports `MIDPOINT`, `BID`, `ASK` and `BID_ASK`, but **not `TRADES`**. No fixed FX depth is published, so call `reqHeadTimeStamp` once per pair. Pacing allows no more than 60 requests in 10 minutes, no identical request within 15 s, fewer than 6 requests a contract in 2 s, and at most 50 open requests. `BID_ASK` counts twice.
- **Orders.** Brackets are a parent plus two children with `parentId` set. Every leg has `transmit=False` except the last. A stop on IDEALPRO may be **simulated** by IBKR, which affects fill guarantees.
- **Margin.** An old IBKR document gives **2% (50:1)** for USD pairs. IBKR's Forex CFD page gives 3.33%/5% retail minimums for CFDs. The current spot-FX house margin is not confirmed, so read `whatIfOrder` and the account values at runtime.
- **Market data.** FX needs **no paid subscription**. CME/COMEX futures need a paid real-time subscription (price unverified). Without one, data is delayed.

## 1. Connecting a Linux Python service

### IB Gateway vs TWS

- IB Gateway is the lighter application and uses about 40% fewer resources than TWS. It accepts socket API connections by default, while TWS does not until you enable them. ([TWS API: Initial setup](https://interactivebrokers.github.io/tws-api/initial_setup.html))
- Read-Only API is enabled by default. "Information about orders is not available to the API when read-only mode is enabled." It must be turned off before the service can place orders. ([Initial setup](https://interactivebrokers.github.io/tws-api/initial_setup.html)) IBC's `ReadOnlyApi=yes|no` and the Docker `READ_ONLY_API` variable set it. ([IBC config.ini](https://github.com/IbcAlpha/IBC/blob/master/resources/config.ini), [ib-gateway-docker README](https://github.com/gnzsnz/ib-gateway-docker))
- One TWS or Gateway session accepts **up to 32 client applications**, told apart by `clientId`. Reusing a `clientId` that is already connected causes a connection failure. ([TWS API: Connection](https://interactivebrokers.github.io/tws-api/connection.html))

### Ports

| App | Live | Paper | Source |
|---|---|---|---|
| TWS | 7496 | 7497 | [Initial setup](https://interactivebrokers.github.io/tws-api/initial_setup.html) |
| IB Gateway | 4001 | 4002 | [ib-gateway-docker README](https://github.com/gnzsnz/ib-gateway-docker): container ports 4003/4004 relay through socat to internal 4001/4002, and the sample compose maps them back to `127.0.0.1:4001` and `127.0.0.1:4002` |

`ib_async`'s README says "Default ports are 7497 (TWS) and 4001 (Gateway)". 4001 is the Gateway **live** port, so set the port to 4002 explicitly for paper. ([ib_async](https://github.com/ib-api-reloaded/ib_async))

### Daily restart, weekly 2FA, IBC

- "Both TWS and IBGW were designed to be restarted daily." Auto-restart (version 974 and later) avoids a daily re-login. Credentials must be entered again after the weekend server reset. ([Initial setup](https://interactivebrokers.github.io/tws-api/initial_setup.html))
- IBKR: "This procedure will require manual authentication once a week." Security tokens reset each **Sunday 01:00 ET**. Auto-restart fails if the host is asleep or powered off at the restart time. ([ibkrguides: Auto-restart considerations](https://www.ibkrguides.com/traderworkstation/auto-restart-considerations.htm))
- **IBC** (latest 3.24.2, released 2026-08-21) fills in the login, clicks through dialogs, and offers `AutoRestartTime`, `ClosedownAt` (a tidy shutdown on Friday) and `ColdRestartTime` (a full shutdown and new login on Sunday after 01:00 ET). It handles 2FA through IBKR Mobile alerts but **cannot approve the alert itself**. `ReloginAfterSecondFactorAuthenticationTimeout=yes` makes it retry after the roughly 3-minute timeout. ([IBC user guide](https://github.com/IbcAlpha/IBC/blob/master/userguide.md), [IBC config.ini](https://github.com/IbcAlpha/IBC/blob/master/resources/config.ini), [releases](https://github.com/IbcAlpha/IBC/releases))
- **gnzsnz/ib-gateway-docker** bundles IB Gateway, IBC, Xvfb, x11vnc and socat. The `stable` channel is Gateway 10.50.1h and `latest` is 10.53.1a, both with IBC 3.24.2. Its environment variables are `TWS_USERID`, `TWS_PASSWORD`, `TRADING_MODE` (defaults to `paper`, and `both` runs live and paper together), `READ_ONLY_API`, `TWS_ACCEPT_INCOMING`, `AUTO_RESTART_TIME` ("does not require daily 2FA validation"), `TWS_COLD_RESTART`, `TWOFA_TIMEOUT_ACTION` (use `restart` together with `AUTO_RESTART_TIME`), `RELOGIN_AFTER_TWOFA_TIMEOUT` and `TIME_ZONE`. VNC on 5900 starts only if `VNC_SERVER_PASSWORD` is set. **Warning:** the README says the image is moving from IBC to "ibcontroller" no earlier than 2027-01-10, and that the change breaks existing compose and env files. **Pin an exact version tag.** ([README](https://github.com/gnzsnz/ib-gateway-docker), [docker-compose.yml](https://github.com/gnzsnz/ib-gateway-docker/blob/master/docker-compose.yml))
- Whether a **paper** login needs 2FA: **[UNVERIFIED]**. IBC's guide does not say. Keep the credentials in `.env`, which is gitignored.

### TWS API (`ibapi`) vs `ib_async`

- `ib_async` is the successor to `ib_insync`. Its original author died in early 2024. It is maintained by Matt Stancliff, needs Python ≥3.10, is BSD-2-Clause, and is built on asyncio and eventkit. Latest release is **v2.0.1 (2025-06-22)**. ([repo](https://github.com/ib-api-reloaded/ib_async), [releases](https://github.com/ib-api-reloaded/ib_async/releases))
- Its client throttles to `MaxRequests = 45` per `RequestsInterval = 1` s and emits `throttleStart` and `throttleEnd` events. ([ib_async/client.py](https://github.com/ib-api-reloaded/ib_async/blob/main/ib_async/client.py)) IBKR's own message-rate limit, commonly quoted as 50 messages/s, was **[UNVERIFIED]** on the pages read.
- `IB.bracketOrder(action, quantity, limitPrice, takeProfitPrice, stopLossPrice)` builds the three-leg bracket with the transmit flags already set. ([ib_async/ib.py](https://github.com/ib-api-reloaded/ib_async/blob/main/ib_async/ib.py))
- Recommendation: use `ib_async`. The raw `ibapi` callback threading model would have to be wrapped by hand anyway.

### Contract definitions

- FX: `Symbol="EUR", SecType="CASH", Currency="GBP", Exchange="IDEALPRO"`. In `ib_async` this is `Forex('EURGBP')`. ([Basic contracts](https://interactivebrokers.github.io/tws-api/basic_contracts.html), [ib_async](https://github.com/ib-api-reloaded/ib_async))
- Spot gold: `Symbol="XAUUSD", SecType="CMDTY", Exchange="SMART", Currency="USD"`. ([Basic contracts](https://interactivebrokers.github.io/tws-api/basic_contracts.html))
- Futures: `SecType="FUT"` with `LastTradeDateOrContractMonth`. ([Basic contracts](https://interactivebrokers.github.io/tws-api/basic_contracts.html)) For MGC and GC the exchange is `COMEX` **[UNVERIFIED; resolve with `reqContractDetails`]**.

## 2. IDEALPRO FX: sizes, increments, hours, commissions

- **Minimum:** "a minimum size of USD 25,000, or equivalent, is imposed on all IdealPro orders." ([FAQ: What does the IdealPro minimum mean?](https://www.interactivebrokers.com/support/faq/content/idealpro-minimum-mean-65996956) **[snippet]**) The order-size table gives a minimum of USD 25,000 / EUR 20,000 and a maximum of USD 7,000,000. The EUR maximum appears as both 6M and 5M on the same page. ([Spot Currency Min/Max Order Sizes](https://www.interactivebrokers.com/en/trading/forexOrderSize.php) **[snippet]**) Larger orders need the Large-Size Order Facility, which requires a written request. ([FAQ](https://www.interactivebrokers.com/support/faq/content/idealpro-large-size-order-facility-1163260418) **[snippet]**)
- **Odd lots:** orders below the minimum "will be automatically rerouted to a small order venue" (IDEAL). Marketable odd lots fill "only slightly inferior (1-3 ticks)", or about "1-2 basis points" outside the IDEALPRO quote. Odd-lot limit orders are not shown on IDEALPRO and may take longer to fill. ([FAQ: Odd lot FX transactions](https://www.interactivebrokers.com/support/faq/content/odd-lot-fx-transactions-1163260635), [IBKB node/1459](https://ibkb.interactivebrokers.com/node/1459) **[snippet]**)
- **Quantity:** "forex order quantity is by default defined in terms of units of the first currency of the pair. The concept of Forex lots does not apply." ([FAQ: Is there a minimum order size?](https://www.interactivebrokers.com/support/faq/content/there-minimum-order-size-27293079) **[snippet]**) The quantity increment below 25k (for example, whether 1 unit is allowed) is **[UNVERIFIED]**. Test it on paper.
- **Price increment:** IBKR's examples use 0.0001 for EUR.USD and 0.01 for USD.JPY. Half-pip precision (0.00005) is **[UNVERIFIED]**. Use `ContractDetails.minTick` and the market rules at runtime, which the API docs recommend. ([TWS API: minimum price increment](https://www.interactivebrokers.com/docs/tws-api/doc/orders/minimum-price-increment) **[snippet]**)
- **Hours:** IDEALPRO currencies trade Sunday-Friday 17:15-17:00 ET, which implies a 15-minute daily break. ([Products and Exchanges](https://investors.interactivebrokers.com/en/index.php?f=1604&p=global) **[snippet]**)
- **Commissions (IBKR Pro):** **0.20 bp × trade value** for monthly volume up to USD 1B, then 0.15, 0.10 and 0.08 bp. The **minimum per order** is USD 2.00 at Tier I, 1.50 at Tier II, 1.25 at Tier III and 1.00 at Tier IV. Commissions are computed on trade value and charged in the account's base currency. ([Commissions Spot Currencies](https://www.interactivebrokers.com/en/pricing/commissions-spot-currencies.php) **[snippet]**) An older IBKR PDF shows a USD 2.50 minimum, which is stale. Fixed pricing for FX and IBKR Lite FX terms are **[UNVERIFIED]**.
- **Implication for the cost model:** a round trip below about USD 100k notional costs **USD 4.00** in commission, before the odd-lot penalty. On a 25k EURUSD trade that is about 1.6 bp, or 0.16 pip, of commission alone.

## 3. Gold

### London spot XAUUSD

- Eligibility: "London Spot Gold (symbol XAUUSD) & Silver (symbol XAGUSD) are available to most customers who are not residents of the U.S., Canada, Australia, Hong Kong or Japan, and are also not available to customers of IB Singapore." ([IBKR Campus: Trading Spot Gold and Silver](https://www.interactivebrokers.com/campus/trading-lessons/trading-spot-gold-and-silver-using-ibkrs-tws/) **[snippet]**) Permissions are set as "Global" for London metals in the Client Portal. The account also needs the Commodities segment, which is off by default for securities-only accounts. **[snippet]**, same page.
- US residents get **USGOLD** (US Spot Gold) instead. It is not available in Arizona, Montana, New Hampshire or Rhode Island, and the account must meet the futures financial requirements. ([US Spot Gold](https://www.interactivebrokers.com/en/trading/products-metals.php), [Eligibility FAQ](https://www.interactivebrokers.com/support/faq/content/eligibility-requirements-obtaining-us-spot-154832301) **[snippet]**)
- Units are 1 troy oz and the minimum order is 1 oz. The minimum price increment is $0.001. (Campus lesson **[snippet]**)
- Commissions: **1.5 bp** on trade value up to USD 500k, 1.0 bp from 500k to 1M, and 0.7 bp above 1M, with a **USD 2.00 minimum** at Tier 1. Exchange and regulatory fees are included. ([Commissions Metals](https://www.interactivebrokers.com/en/pricing/commissions-metals.php) **[snippet]**) IB UK says a 1% supplementary financing fee applies to shorts from 1 May 2026. ([IB UK metals](https://www.interactivebrokers.co.uk/en/index.php?f=41426) **[snippet]**)
- Margin (IB UK page): 6.25% initial and 5% maintenance. Retail CFDs have a 5% regulatory minimum. Margin varies by jurisdiction. ([IB UK Metals Margin](https://www.interactivebrokers.co.uk/en/trading/margin-metals.php), [Metals CFDs FAQ](https://www.ibkrguides.com/kb/article-3642.htm) **[snippet]**)
- IDEALPRO Metals trading starts at 18:00 ET, separately from FX. ([Products and Exchanges](https://investors.interactivebrokers.com/en/index.php?f=1604&p=global) **[snippet]**)

### COMEX futures

| | MGC (E-micro Gold) | GC (Gold) |
|---|---|---|
| Size | 10 troy oz | 100 troy oz |
| Tick | $0.10/oz = **$1.00** | $0.10/oz = $10.00 **[UNVERIFIED, from the 10× size]** |
| Months | Feb/Apr/Jun/Aug/Oct/Dec within 24 months | **[UNVERIFIED]** |
| Last trade | 3rd-last business day of the contract month | **[UNVERIFIED]** |
| Settlement | Physical, by ACE (10% of a 100 oz bar) | Physical |
| Hours | Sunday 17:00 to Friday 16:00 CT, 60-minute daily break at 16:00 CT | same **[UNVERIFIED]** |

Sources for MGC: [CME Gold Product Overview](https://www.cmegroup.com/education/lessons/product-gold), [CME Micro Metals](https://www.cmegroup.com/markets/microsuite/metals.html), [CME Ch.120 rule](https://www.cmegroup.com/market-regulation/files/13-252_ExG.pdf) **[snippet]**.

- **Commissions:** the IBKR Pro tiered rate for MGC is USD 0.25, 0.20, 0.15 or 0.10 a contract, at monthly volumes of ≤1,000, ≤10,000, ≤20,000 and above. The fixed rate is USD 0.25. ([Commissions Futures](https://www.interactivebrokers.com/en/pricing/commissions-futures.php) **[snippet]**) The COMEX exchange-fee recovery for MGC is **USD 0.70** for non-members. ([COMEX fees](https://www.interactivebrokers.com/en/accounts/fees/COMEX.php) **[snippet]**) For GC, the general US futures rate is USD 0.85 fixed or USD 0.25-0.85 tiered. A GC-specific row and its exchange fee are **[UNVERIFIED]**.
- **Margin:** CME switched gold margins to a percentage of notional in January 2026 ([CME clearing advisory 26-019](https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2026/01/chadv26-019.pdf) **[snippet]**). Current MGC and GC figures are **[UNVERIFIED]**. Read them from `whatIfOrder` or the [IBKR futures margin page](https://www.interactivebrokers.com/en/trading/margin-futures-fops.php).
- **Rollover:** IBKR generally does not allow delivery, except on certain currency and metals futures. It may liquidate a position without notice after the contract's published **Close-Out Deadline**. COMEX precious-metals delivery has to be requested about one month before the last trading day. ([Futures Close Out](https://www.interactivebrokers.com/en/trading/futures-close-out.php), [COMEX precious metals](https://www.ibkrguides.com/clientportal/comexpreciousmetals.htm) **[snippet]**) The execution layer needs a roll calendar that runs ahead of IBKR's deadline.
- **Choice:** a non-US paper account can use XAUUSD, which has the same order model as FX. A US resident has to use MGC: a 10 oz contract is about USD 40k notional at current prices (**[UNVERIFIED]** price), it needs rolls, and it needs a CME data subscription.

## 4. Historical data (H1)

- `whatToShow` for Forex: **MIDPOINT, BID, ASK, BID_ASK** and SCHEDULE. **TRADES is not available.** Bar sizes include 1 hour, and `keepUpToDate=True` (with an empty end date) streams bar updates. ([Historical bars](https://interactivebrokers.github.io/tws-api/historical_bars.html))
- Step sizes: the legacy table tops out at "1 Y | 1 day - 1 month", and "1 M | 30 mins - 1 month" means a 1-hour bar fits in a 1 M request. ([Historical limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)) The newer docs say the hard limits for bars of 1 minute and up have been lifted, though large requests can still throttle. ([Max Duration Per Bar Size](https://www.interactivebrokers.com/docs/tws-api/doc/market-data-historical/historical-bars/max-duration-per-bar-size) **[snippet]**) Safe plan: request H1 in 1 M chunks and walk `endDateTime` backwards.
- **Pacing:** a violation is any of identical requests within 15 s, 6 or more requests for the same contract, exchange and tick type within 2 s, or more than 60 requests in 10 minutes. No more than 50 requests may be open at once. **BID_ASK counts twice.** ([Historical limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)) Backfilling 12 instruments × N months therefore takes about 10 minutes per 60 chunks.
- **Depth:** IBKR publishes no FX-specific depth. `reqHeadTimeStamp(contract, "MIDPOINT", ...)` returns the earliest available point. It counts as an open historical request and should be cancelled afterwards. ([Earliest data point](https://www.interactivebrokers.com/docs/tws-api/doc/market-data-historical/finding-the-earliest-available-data-point/receiving-the-earliest-data-point) **[snippet]**) Actual H1 depth per pair is **[UNVERIFIED]**. Measure it on the paper account.
- Expired futures: historical data for expired contracts is limited, so MGC/GC backtests need a continuous series built from other sources **[UNVERIFIED limit]**.

## 5. Bracket orders (entry + SL/TP)

- Pattern: the parent has `transmit=False`. The take-profit child has `parentId=parent.orderId` and `transmit=False`. The stop-loss child has `parentId` set and `transmit=True`, which sends the whole group. "The parent and children orders will need this attribute set to false to prevent accidental executions." ([Bracket orders](https://interactivebrokers.github.io/tws-api/bracket_order.html)) `ib_async.IB.bracketOrder()` does this, with the entry as a `LimitOrder`. ([ib.py](https://github.com/ib-api-reloaded/ib_async/blob/main/ib_async/ib.py)) For a market entry, build the parent by hand with the same flags.
- Child orders become active only after the parent fills. When one child fills the other is cancelled. ([IBKR Bracket Orders](https://www.interactivebrokers.com/docs/general/order-types/complex-orders/bracket-orders) **[snippet]**; the legacy API page does not mention OCA.)
- IBKR "may simulate certain order types on its books" where the venue lacks them, and simulated stops depend on IBKR's market data. ([Order Types](https://www.interactivebrokers.com/en/trading/ordertypes.php) **[snippet]**) Whether IDEALPRO stops are native or simulated is **[UNVERIFIED]**. Either way, a stop is not guaranteed a price, so the Risk Gate should budget for slippage.
- Trailing stops are supported for Forex. **[snippet]**, same page.

## 6. Margin and leverage (FX)

- An older IBKR margin document gives USD at **2% initial (50:1)**. Regulatory rates apply where they exceed IBKR's house rates. ([IBKR margin PDF](https://www.interactivebrokers.com/download/commSegComp/CME_PDF_20160218.pdf) **[snippet]**, dated 2016)
- Forex **CFDs** start at 2.5% for majors, with retail regulatory minimums of 3.33% or 5% depending on the pair. ([Forex CFDs FAQ](https://www.interactivebrokers.com/support/faq/content/forex-cfds-facts-q-1163260128) **[snippet]**) Not applicable to US residents (**[UNVERIFIED]**).
- Cash Forex trading needs a margin account and Forex trading permissions. ([Margin Rates](https://www.interactivebrokers.com/en/trading/margin-rates.php) **[snippet]**)
- Current spot-FX margin per pair is **[UNVERIFIED]**. The Risk Gate should call `ib.whatIfOrder(contract, order)` before each order and read `InitMarginReq`, `MaintMarginReq`, `ExcessLiquidity` and `Cushion` from the account values, instead of using constants.

## 7. Market data subscriptions

- "Forex and Cryptocurrencies do not require any additional market data subscriptions." ([IBKR API: Market data subscriptions](https://www.interactivebrokers.com/campus/ibkr-api-page/market-data-subscriptions/) **[snippet]**)
- CME and COMEX futures need a paid real-time subscription. Without one, data is delayed where available. Non-Professional status is cheaper, fees are not pro-rated, and subscriptions are managed in the Client Portal. ([Market Data Pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php) **[snippet]**) The exact COMEX non-professional fee is **[UNVERIFIED]**.
- Whether a paper account shares the live account's subscriptions is **[UNVERIFIED]** here.

## 8. Checklist for the Risk Gate and execution layer

1. Connect to Gateway on 4002 (paper) with a fixed `clientId`. Turn Read-Only off for the trading client. Reconnect with backoff around the daily restart. Alert on the Sunday 2FA.
2. Resolve contracts once with `reqContractDetails`, then cache `minTick`, market rules, trading hours and (for futures) expiry.
3. Size: round to an allowed quantity. Flag orders under USD 25k equivalent as odd lots, add about 2 bp of slippage, and cap at about USD 7M.
4. Cost model: `max(0.20bp × notional, USD 2.00)` per FX side, `max(1.5bp × notional, USD 2.00)` per XAUUSD side, and USD 0.25 + about 0.70 per MGC contract per side.
5. Run a margin pre-check with `whatIfOrder` and enforce an `ExcessLiquidity` floor.
6. Send orders as brackets only, using the parent/child transmit pattern. Reconcile with `openOrders` and `positions` on reconnect.
7. Pace history requests to at most 60 per 10 minutes. Use MIDPOINT for signals and BID/ASK for spread estimates.
8. Futures: keep a roll calendar that runs before IBKR's Close-Out Deadline.
9. Hours: skip FX from 17:00 to 17:15 ET and over weekends, and treat gold (from 18:00 ET) separately.
