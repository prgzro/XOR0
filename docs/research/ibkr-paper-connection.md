# IBKR paper connection: headless IB Gateway

For `.scratch/kronos-jev/issues/05-ibkr-account-setup.md`. Builds on [ibkr-api-and-products.md](ibkr-api-and-products.md). Done 2026-11-26 and read-only throughout: no orders and no whatIf orders.

## TL;DR

- **Connected.** IB Gateway 10.50.1h with IBC 3.24.2 runs headless in Docker: paper mode only, read-only API, `127.0.0.1:4002` only, no VNC. `ib_async` 2.0.1 connects with `readonly=True`.
- **Login.** Paper login needed **no 2FA**. The first attempt stopped at IBKR's "Existing session detected" dialog, because the same username was logged in elsewhere. After the user logged out of the other sessions, the login went straight through.
- **Account.** It is `DU*******` (a paper account), INDIVIDUAL. NetLiquidation is 1,000,000.00 USD; the summary reports in USD, which implies the base currency is USD. Server time matched local UTC within 1 s.
- **FX.** All 11 pairs resolve on IDEALPRO. **minTick is half a pip** (5e-05; 0.005 for JPY pairs). Real-time quotes stream on paper with no subscription (`marketDataType=1`).
- **Gold.** Spot **XAUUSD resolves** (CMDTY/SMART, minTick 0.01, 1 oz) and has real-time quotes. MGC resolves on COMEX (12 contract months), but its market data is **not subscribed** (error 354; only delayed data is available).
- **History depth.** H1 MIDPOINT, BID and ASK start in **2005-03** for 10 pairs, 2007-11 for NZDUSD and 2010-06 for XAUUSD. A **1-year request for 1-hour bars works** (about 6,200 bars in 7-14 s), so 3 requests gave 3 years.
- **IBKR vs XM.** XM H1 closes sit a steady **~1.1 pip below** the IBKR midpoint (XM stores bid; the difference is about half the spread). Once that bias is removed, the median gap is 0.1 pip and the 90th percentile is 0.3 pip. XM server time is **EET/EEST with EU DST rules** (UTC+2 in winter, UTC+3 in summer).

## Versions

| Item | Version |
|---|---|
| Image | `ghcr.io/gnzsnz/ib-gateway:10.50.1h`. Its digest `sha256:4f2704a1ab2ebcd468ac6ca58e2b99d2c6c056b303a3f499b67fc80012ad5a10` equals `:stable` on 2026-11-26. `latest` is 10.53.1a. |
| IB Gateway / IBC | 10.50.1h / 3.24.2. API server version 178. |
| Python / ib_async | 3.12.3 / `ib_async==2.0.1` (plus `aeventkit==2.1.0`, `nest-asyncio==1.6.0`), in the scratchpad venv `ibgw/venv` |

## Compose file

Lives in the scratchpad at `ibgw/docker-compose.yml`. Credentials are interpolated from the repo `.env` (`IBKR_USERNAME` / `IBKR_PASSWORD`) through `--env-file` and are never written as literal values.

```yaml
# Start:
#   docker compose -p jevquant-ibgw --env-file /home/prgzro/Projects/XOR0/.env -f docker-compose.yml up -d
# Stop:
#   docker compose -p jevquant-ibgw --env-file /home/prgzro/Projects/XOR0/.env -f docker-compose.yml down
#   (or: docker stop jevquant-ibgw && docker rm jevquant-ibgw)
name: jevquant-ibgw
services:
  ib-gateway:
    image: ghcr.io/gnzsnz/ib-gateway:10.50.1h   # = stable channel on 2026-11-26
    container_name: jevquant-ibgw
    restart: "no"            # no auto-restart loop on a failed login (account-lockout guard)
    environment:
      TWS_USERID: ${IBKR_USERNAME:?IBKR_USERNAME missing}
      TWS_PASSWORD: ${IBKR_PASSWORD:?IBKR_PASSWORD missing}
      TRADING_MODE: paper
      READ_ONLY_API: "yes"
      TWS_ACCEPT_INCOMING: reject
      # EXISTING_SESSION_DETECTED_ACTION: manual   # image default; "primaryoverride" logs out other sessions
      RELOGIN_AFTER_TWOFA_TIMEOUT: "no"
      TWOFA_TIMEOUT_ACTION: exit
      AUTO_RESTART_TIME: "11:45 PM"
      TIME_ZONE: Etc/UTC
      TZ: Etc/UTC
    ports:
      - "127.0.0.1:4002:4004"   # paper API (socat relay -> internal 4002)
```

Because of the `:?` guards, `down` also needs `--env-file`, or you can use `docker stop`/`docker rm` by name. IBC confirmed "Read-Only API checkbox is already set to: true" and "Auto restart time set to 11:45 PM".

## Login notes

- **Attempt 1 (03:51 UTC).** IBC got past the password step, then IBKR raised "Existing session detected" ("User must choose whether to continue with this session"). The image default `ExistingSessionDetectedAction=manual` leaves that dialog for a human, so I stopped the container after 3 minutes.
- **Attempt 2 (04:16 UTC).** This was after the user logged out of all other sessions. Login completed and the configuration dialog was titled "(Simulated Trading)". No 2FA prompt appeared.
- **Lesson.** Any other login for the same username (TWS, Client Portal, IBKR Mobile) blocks or kills the Gateway session. A dedicated paper username avoids that.

## Results

### Account and connection

| Check | Result |
|---|---|
| Account | `DU*******` (paper), AccountType INDIVIDUAL |
| NetLiquidation / TotalCash / AvailableFunds | 1,000,000.00 USD each. BuyingPower is 4,000,000.00 USD. |
| Base currency | USD (inferred: `accountSummary` reports in base currency). `reqAccountUpdates` hung under `ib_async` with `readonly=True`, so the explicit `Currency` tag was not read. |
| Server time | 2026-11-26 04:17:00 UTC against local 04:17:01 UTC |

### Contracts (`reqContractDetails`)

| Instrument | Local symbol / exchange | minTick | minSize = sizeIncrement | Market rule | Hours (US/Eastern) |
|---|---|---|---|---|---|
| EURUSD, GBPUSD, USDCHF, AUDUSD, USDCAD, EURGBP, EURCHF | `EUR.USD` etc. / IDEALPRO | 0.00005 | 0.01 | 3188 | 17:15 to 17:00 the next day |
| USDJPY, EURJPY, GBPJPY | `USD.JPY` etc. / IDEALPRO | 0.005 | 1 | 145 | 17:15 to 17:00 |
| NZDUSD | `NZD.USD` / IDEALPRO | 0.00005 | 1 | 239 | 13:15 to 13:00 (as reported; check it) |
| XAUUSD | `XAUUSD` CMDTY / SMART | 0.01 | 1 (oz) | 87 | 18:00 to 17:00. The 2026-11-26 session closes at 14:15 (holiday). |
| MGC | `MGCZ6` (expires 2026-12-29), `MGCG7` … / COMEX, multiplier 10 | 0.1 | 1 | 65 | 18:00 to 17:00. Closes early at 14:30 on 2026-11-26. |

Notes:
- The minTick is 0.00005 rather than the 0.0001 that ticket 03 assumed. Market rule 3188 may give finer ticks at some price levels, so read it at runtime.
- The minSize of 0.01 is the API size increment. The IDEALPRO 25k minimum is still enforced through odd-lot routing.
- XAUUSD resolving means the account is eligible for London spot gold. The project should use XAUUSD rather than MGC.

### Earliest data (`reqHeadTimeStamp`, useRTH=False, UTC)

| Instrument | MIDPOINT | BID | ASK |
|---|---|---|---|
| EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, EURGBP, EURJPY, GBPJPY, EURCHF | 2005-03-09 04:30 | same | same |
| NZDUSD | 2007-11-01 21:15 | same | same |
| XAUUSD | 2010-06-08 21:15 | same | same |
| MGC (front, MGCZ6) | 2024-12-30 23:00 | same | same (TRADES is the same too) |

The head timestamp does not prove that H1 bars are complete back to 2005. The EURUSD pull below only went back to 2023-11.

### EURUSD H1 MIDPOINT pull

| Request | Bars | Range (UTC) | Time |
|---|---|---|---|
| `1 Y`, end = now | 6,192 | 2025-11-26 22:15 to 2026-11-26 04:00 | 7.3 s |
| `1 Y`, end = previous first bar | 6,209 | 2024-11-26 22:15 to 2025-11-26 21:00 | 8.2 s |
| `1 Y`, walking back again | 6,210 | 2023-11-27 22:15 to 2024-11-26 21:00 | 14.1 s |

That is 18,611 unique bars from 3 requests, with no pacing errors. 769 bars carry a **:15 timestamp**, the 22:15/21:15 UTC session-open bar after IDEALPRO's 17:00-17:15 ET break. IBKR's H1 grid is aligned to the session, not to the clock hour, at that point. Data saved to `ibgw/out/eurusd_h1.csv` in the scratchpad.

### IBKR MIDPOINT vs XM H1 close (EURUSD)

XM `EURUSD60.hst` (read from a copy) is HST v401 with 42,033 bars, from 2020-02-21 16:00 to 2026-11-26 03:00 server time. Bars were matched with XM time = UTC + Europe/Athens offset (EET/EEST). Fitting per DST transition week confirms **EU rules**. In 2025, +2 still fitted for 09-29 March (US DST had already started) and +3 fitted from 31 March. +2 fitted 26 Oct to 1 Nov (before the US change).

| Window | n | Median abs. diff | p90 | p99 | Max | Mean (XM − IBKR) | After removing bias: median / p90 |
|---|---|---|---|---|---|---|---|
| 1 month, 2026-10-26 to 11-25 | 528 | 1.1 pip | 1.3 | 2.9 | 13.0 | **−1.14 pip** | 0.14 / 0.34 pip |
| 3 years, 2023-11 to 2026-11 | 17,801 | 1.1 pip | 1.3 | 3.0 | 13.1 | −1.10 pip | 0.10 / 0.30 pip |

The two feeds agree closely. The steady −1.1 pip is bid against mid. Expect XM-calibrated levels to sit about 1 pip below IBKR mid.

### Market data (`reqMktData` snapshot)

| Instrument | Result |
|---|---|
| EURUSD | Real-time (`marketDataType=1`): bid 1.09601, ask 1.09604, a 0.3 pip spread |
| XAUUSD | Real-time: bid 3583.34, ask 3583.80 |
| MGC | Error 354, "Requested market data is not subscribed … Delayed market data is available" |

## Re-run (scratchpad `ibgw/`)

```
docker compose -p jevquant-ibgw --env-file /home/prgzro/Projects/XOR0/.env -f docker-compose.yml up -d
venv/bin/python -I scripts/probe.py out/probe.json               # clientId 17, readonly
venv/bin/python -I scripts/history.py out/eurusd_h1.csv "1 Y" 3  # clientId 18, 16 s between requests
venv/bin/python -I scripts/compare.py EURUSD60.hst out/eurusd_h1.csv
```

## Open issues

- The Gateway session dies whenever the user logs in elsewhere with the same username. Decide between a dedicated paper username and accepting the clash.
- Weekly re-authentication: paper needed no 2FA today. Watch the first Sunday restart.
- `restart: "no"` is deliberate. Move to `unless-stopped` once logins are stable.
- Base currency was inferred, not read (the `reqAccountUpdates` hang). Read it with `accountSummary` tags or the Client Portal.
- The NZDUSD trading hours (13:15-13:00 ET) look odd. Re-check them.
- Confirm that H1 bars before 2023-11 are actually complete, not just present at the head timestamp.
- The image moves from IBC to "ibcontroller" no earlier than 2027-01-10. Keep the tag pinned.
