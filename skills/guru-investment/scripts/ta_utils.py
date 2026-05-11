"""
Technical analysis utilities for guru-investment skill.

Inputs: list of daily OHLCV dicts, e.g.:
    [{"date": "20260410", "close": 93000, "open": ..., "high": ..., "low": ..., "volume": ...}, ...]
(sorted ascending by date)

Outputs: MA, Stage, VCP contractions, volume patterns.

Usage:
    from ta_utils import analyze
    result = analyze(bars)
    print(result["ma50"], result["stage"], result["vcp"])
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional


def sma(values: List[float], period: int) -> Optional[float]:
    """Simple moving average of last `period` values."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def moving_averages(closes: List[float]) -> Dict[str, Optional[float]]:
    """Compute MA50, MA150, MA200, and MA200 from 1 month ago."""
    return {
        "ma50": sma(closes, 50),
        "ma150": sma(closes, 150),
        "ma200": sma(closes, 200),
        "ma200_1m_ago": sma(closes[:-20], 200) if len(closes) >= 220 else None,
    }


def minervini_trend_template(close: float, mas: Dict[str, Optional[float]]) -> Dict[str, bool]:
    """Check Minervini's 8-point Trend Template."""
    ma50, ma150, ma200, ma200_prev = mas["ma50"], mas["ma150"], mas["ma200"], mas["ma200_1m_ago"]
    checks = {}
    if None in (ma150, ma200):
        return {"insufficient_data": True}
    checks["price_above_ma150_ma200"] = close > ma150 and close > ma200
    checks["ma150_above_ma200"] = ma150 > ma200
    checks["ma200_rising"] = ma200_prev is not None and ma200 > ma200_prev
    if ma50 is not None:
        checks["ma50_above_ma150_ma200"] = ma50 > ma150 and ma50 > ma200
        checks["price_above_ma50"] = close > ma50
    return checks


def stage_analysis(close: float, mas: Dict[str, Optional[float]]) -> str:
    """Classify Minervini Stage 1/2/3/4."""
    ma50, ma150, ma200, ma200_prev = mas["ma50"], mas["ma150"], mas["ma200"], mas["ma200_1m_ago"]
    if None in (ma50, ma150, ma200):
        return "insufficient_data"
    rising_200 = ma200_prev is not None and ma200 > ma200_prev
    if ma50 > ma150 > ma200 and rising_200 and close > ma50:
        return "Stage 2 (uptrend)"
    if ma200 > ma150 > ma50 and not rising_200:
        return "Stage 4 (downtrend)"
    if abs(ma50 - ma200) / ma200 < 0.03:
        return "Stage 1 or 3 (consolidation/top)"
    return "Transitional"


def find_swings(bars: List[Dict], window: int = 3) -> Dict[str, List]:
    """Find swing highs/lows with a symmetric window."""
    highs, lows = [], []
    for i in range(window, len(bars) - window):
        h, l = bars[i]["high"], bars[i]["low"]
        if all(h >= bars[j]["high"] for j in range(i - window, i + window + 1) if j != i):
            highs.append({"idx": i, "date": bars[i]["date"], "price": h})
        if all(l <= bars[j]["low"] for j in range(i - window, i + window + 1) if j != i):
            lows.append({"idx": i, "date": bars[i]["date"], "price": l})
    return {"highs": highs, "lows": lows}


def compute_contractions(bars: List[Dict], lookback: int = 60, window: int = 3) -> List[Dict]:
    """Identify high->low contractions in recent bars."""
    recent = bars[-lookback:] if len(bars) > lookback else bars
    sw = find_swings(recent, window)
    points = [{"type": "H", **h} for h in sw["highs"]] + [{"type": "L", **l} for l in sw["lows"]]
    points.sort(key=lambda x: x["idx"])
    contractions, last_high = [], None
    for p in points:
        if p["type"] == "H":
            last_high = p
        elif p["type"] == "L" and last_high:
            drop_pct = (p["price"] - last_high["price"]) / last_high["price"] * 100
            contractions.append({
                "high_date": last_high["date"], "high": last_high["price"],
                "low_date": p["date"], "low": p["price"],
                "drop_pct": round(drop_pct, 2),
            })
            last_high = None
    return contractions


def vcp_judgment(contractions: List[Dict]) -> Dict[str, Any]:
    """Judge VCP quality: 2~6 contractions with progressively smaller drops."""
    n = len(contractions)
    if n < 2:
        return {"verdict": "insufficient (<2 contractions)", "count": n}
    drops = [abs(c["drop_pct"]) for c in contractions]
    decreasing = all(drops[i] >= drops[i + 1] - 2 for i in range(len(drops) - 1))  # tolerance 2%p
    recent_tight = len(drops) >= 3 and max(drops[-3:]) < 12
    if 2 <= n <= 6 and decreasing and recent_tight:
        return {"verdict": "textbook VCP", "count": n, "drops": drops, "pivot": contractions[-1]["high"]}
    if 2 <= n <= 6 and recent_tight:
        return {"verdict": "quasi VCP (recent contractions tight)", "count": n, "drops": drops, "pivot": contractions[-1]["high"]}
    return {"verdict": "not VCP (volatility expanding or too many contractions)", "count": n, "drops": drops}


def volume_analysis(bars: List[Dict]) -> Dict[str, float]:
    """Volume pattern: 20d avg, 5d avg, latest multiple."""
    vols = [b["volume"] for b in bars]
    if len(vols) < 20:
        return {}
    v20 = sum(vols[-20:]) / 20
    v5 = sum(vols[-5:]) / 5
    return {
        "latest_vol": vols[-1],
        "avg_5d": round(v5, 0),
        "avg_20d": round(v20, 0),
        "latest_vs_20d": round(vols[-1] / v20, 2) if v20 else None,
    }


def price_structure(bars: List[Dict]) -> Dict[str, Any]:
    """Price highs/lows and distance from extremes."""
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    latest = bars[-1]["close"]
    hi_52w = max(highs)
    lo_52w = min(lows)
    return {
        "latest": latest,
        "52w_high": hi_52w,
        "52w_low": lo_52w,
        "from_52w_high_pct": round((latest - hi_52w) / hi_52w * 100, 2),
        "from_52w_low_pct": round((latest - lo_52w) / lo_52w * 100, 2),
    }


def analyze(bars: List[Dict]) -> Dict[str, Any]:
    """One-stop TA analysis. Returns all key metrics."""
    if not bars:
        return {"error": "no bars"}
    closes = [b["close"] for b in bars]
    mas = moving_averages(closes)
    latest_close = closes[-1]
    contractions = compute_contractions(bars, lookback=60, window=3)
    return {
        "price": price_structure(bars),
        "ma": mas,
        "minervini_template": minervini_trend_template(latest_close, mas),
        "stage": stage_analysis(latest_close, mas),
        "contractions": contractions,
        "vcp": vcp_judgment(contractions),
        "volume": volume_analysis(bars),
    }


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python ta_utils.py <bars_json_file>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        bars = json.load(f)
    result = analyze(bars)
    print(json.dumps(result, ensure_ascii=False, indent=2))
