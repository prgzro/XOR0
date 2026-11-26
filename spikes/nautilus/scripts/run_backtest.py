"""Step 1: run the EURUSD H1 backtest twice on the IBKR catalog and compare.

uv run python scripts/run_backtest.py [seed=42] [sl_pips=30] [tp_pips=45]
"""

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from spike.backtest import run_backtest


def digest(fills) -> str:
    return hashlib.sha256(repr(fills).encode()).hexdigest()[:16]


def main(seed: int, sl_pips: int, tp_pips: int) -> None:
    catalog = ROOT / "data" / "catalog"
    print(f"seed {seed}, SL {sl_pips} pips, TP {tp_pips} pips")
    a = run_backtest(catalog, seed, sl_pips, tp_pips)
    b = run_backtest(catalog, seed, sl_pips, tp_pips)
    approved = sum(v.approved for _, v in a.verdicts)
    print(f"verdicts: {len(a.verdicts)} ({approved} approved, {len(a.verdicts) - approved} rejected)")
    print(f"fills: {len(a.fills)}  closed trades: {len(a.trades)}")
    print(f"commission: {a.total_commission_usd} USD")
    print(f"run A: balance {a.final_balance}  fills sha {digest(a.fills)}")
    print(f"run B: balance {b.final_balance}  fills sha {digest(b.fills)}")
    print("IDENTICAL" if (a.fills, a.final_balance) == (b.fills, b.final_balance) else "DIFFERENT")
    sl_first = sum(h.pnl_sl_first for h in a.same_bar)
    tp_first = sum(h.pnl_tp_first for h in a.same_bar)
    print(
        f"same-bar SL+TP trades: {len(a.same_bar)} of {len(a.trades)}; "
        f"gross P&L if SL first {sl_first} USD, if TP first {tp_first} USD"
    )
    for h in a.same_bar:
        t = h.trade
        print(f"  {t.side} entry {t.entry_px} sl {t.sl} tp {t.tp} bar_ts {h.bar_ts}")


if __name__ == "__main__":
    args = [int(x) for x in sys.argv[1:]] + [42, 30, 45][len(sys.argv) - 1 :]
    main(*args[:3])
