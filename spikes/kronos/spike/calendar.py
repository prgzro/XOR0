"""Generated future H1 bar times (no calendar data, so no leakage)."""

import pandas as pd

NY = "America/New_York"


def future_bar_times(last_open: pd.Timestamp, horizon: int, session: str = "fx") -> pd.DatetimeIndex:
    """Next `horizon` IBKR H1 bar-open times after `last_open` (UTC in, UTC out).

    Fixed rule in New York time, no holiday calendar, so the future calendar never leaks in.
    Used identically in backtest and live.
    - "fx" (IDEALPRO): bars on the hour, except the session-open bar at 17:15 (after the
      17:00-17:15 break); no bars from Friday 17:00 until Sunday 17:15.
    - "gold" (XAUUSD): bars on the hour, no 17:00 bar (17:00-18:00 break); no bars from
      Friday 17:00 until Sunday 18:00.
    """
    t = last_open.tz_convert(NY).floor("h")
    out = []
    while len(out) < horizon:
        t = t + pd.Timedelta(hours=1)
        wd, hr = t.weekday(), t.hour
        if (wd == 4 and hr >= 17) or wd == 5 or (wd == 6 and hr < 17):
            continue
        if hr == 17:
            if session == "gold":
                continue
            t = t + pd.Timedelta(minutes=15)
            out.append(t)
            t = t - pd.Timedelta(minutes=15)
            continue
        out.append(t)
    return pd.DatetimeIndex(out).tz_convert("UTC")
