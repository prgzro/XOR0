"""Catalog preparation.

IBKR FX history (BID/ASK/MIDPOINT) carries volume 0. Nautilus v2 builds its L1
book from bar volume, so zero-volume bars leave the venue with no market and every
order is rejected "No market for ...". FX top-of-book depth is not in the data
anyway; give each bar a large synthetic volume so fills are limited by price only.
"""

from nautilus_trader.model import Bar, Quantity

SYNTHETIC_VOLUME = 1_000_000_000  # units of base currency per bar


def with_synthetic_volume(bars, size_precision: int) -> list:
    volume = Quantity(SYNTHETIC_VOLUME, size_precision)
    return [Bar(b.bar_type, b.open, b.high, b.low, b.close, volume, b.ts_event, b.ts_init) for b in bars]
