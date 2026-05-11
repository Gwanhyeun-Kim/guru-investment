"""
KRX daily OHLCV batch fetcher with local caching.

Usage:
    python fetch_krx_daily.py <ticker> [days]
    python fetch_krx_daily.py 017670 250

Output:
    ~/.cache/krx/{ticker}_{YYYYMMDD}.json  (daily bars list, ascending by date)
    Also prints summary: latest price, MA50/150/200, 52w hi/lo, volume stats.

Notes:
    - KRX `stk_bydd_trd` returns ALL stocks per date, so one call per day is required.
    - ~250 calls takes ~4 min. Local cache reused if file exists for same end-date.
    - Business days only (skips Sat/Sun).
    - Auto-switches KOSPI (stk_) vs KOSDAQ (ksq_) if initial endpoint returns no rows for the ticker.
"""
from __future__ import annotations
import requests, json, os, time, sys, warnings
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

API_KEY = os.environ.get("KRX_API_KEY", "")
if not API_KEY:
    sys.exit("ERROR: Set KRX_API_KEY env var. Register free at https://openapi.krx.co.kr/")
HEADERS = {"AUTH_KEY": API_KEY}
BASE = "https://data-dbg.krx.co.kr/svc/apis"
CACHE_DIR = Path.home() / ".cache" / "krx"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_day(date_str: str, endpoint: str = "sto/stk_bydd_trd", retries: int = 3) -> list:
    """Fetch a single day's data, with simple retry on transient errors."""
    url = f"{BASE}/{endpoint}"
    for attempt in range(retries):
        try:
            r = requests.get(url, params={"basDd": date_str}, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json().get("OutBlock_1", [])
        except Exception as e:
            if attempt == retries - 1:
                print(f"  WARN {date_str} failed after {retries}: {e}", file=sys.stderr)
                return []
            time.sleep(2 ** attempt)
    return []


def find_market(ticker: str) -> str:
    """Probe KOSPI first, then KOSDAQ, on most recent business day."""
    today = datetime.now()
    probe_date = today - timedelta(days=1)
    while probe_date.weekday() >= 5:
        probe_date -= timedelta(days=1)
    dstr = probe_date.strftime("%Y%m%d")
    for endpoint in ("sto/stk_bydd_trd", "sto/ksq_bydd_trd"):
        data = fetch_day(dstr, endpoint)
        for item in data:
            if item.get("ISU_CD") == ticker:
                return endpoint
    raise ValueError(f"ticker {ticker} not found in KOSPI/KOSDAQ on {dstr}")


def business_days(end_date: datetime, count: int) -> list:
    """Generate last `count` business days ending at end_date."""
    dates = []
    cur = end_date
    while len(dates) < count:
        if cur.weekday() < 5:
            dates.append(cur.strftime("%Y%m%d"))
        cur -= timedelta(days=1)
    return dates[::-1]


def fetch(ticker: str, days: int = 250, end_date: datetime | None = None) -> list:
    """Fetch `days` business days of OHLCV for ticker. Cached per (ticker, end_date)."""
    end_date = end_date or datetime.now()
    end_str = end_date.strftime("%Y%m%d")
    cache_file = CACHE_DIR / f"{ticker}_{end_str}_{days}.json"
    if cache_file.exists():
        print(f"Cache hit: {cache_file}")
        with open(cache_file) as f:
            return json.load(f)

    endpoint = find_market(ticker)
    print(f"Market: {endpoint}")
    dates = business_days(end_date, days + 10)  # buffer for holidays
    results = []
    for i, dt in enumerate(dates):
        data = fetch_day(dt, endpoint)
        for item in data:
            if item.get("ISU_CD") == ticker:
                results.append({
                    "date": dt,
                    "close": int(item["TDD_CLSPRC"]),
                    "open": int(item["TDD_OPNPRC"]),
                    "high": int(item["TDD_HGPRC"]),
                    "low": int(item["TDD_LWPRC"]),
                    "volume": int(item["ACC_TRDVOL"]),
                    "value": int(item["ACC_TRDVAL"]),
                    "mkcap": int(item["MKTCAP"]),
                })
                break
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(dates)}: {dt} ({len(results)} bars)")
        time.sleep(0.05)
    with open(cache_file, "w") as f:
        json.dump(results, f)
    print(f"Saved {len(results)} bars -> {cache_file}")
    return results


def summary(bars: list) -> None:
    """Print quick summary stats."""
    if not bars:
        print("No bars.")
        return
    closes = [b["close"] for b in bars]
    vols = [b["volume"] for b in bars]
    latest = bars[-1]
    print(f"\nLatest: {latest['date']} close={latest['close']:,} vol={latest['volume']:,}")
    print(f"52w high: {max(b['high'] for b in bars):,}  low: {min(b['low'] for b in bars):,}")
    for p in (50, 150, 200):
        if len(closes) >= p:
            ma = sum(closes[-p:]) / p
            print(f"MA{p}: {ma:,.0f}")
    if len(closes) >= 220:
        ma200_prev = sum(closes[-220:-20]) / 200
        print(f"MA200 1M ago: {ma200_prev:,.0f}  (current MA200 diff: {sum(closes[-200:])/200 - ma200_prev:+,.0f})")
    if len(vols) >= 20:
        v20 = sum(vols[-20:]) / 20
        print(f"20d avg vol: {v20:,.0f}  latest/avg: {vols[-1] / v20:.2f}x")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_krx_daily.py <ticker> [days]")
        sys.exit(1)
    ticker = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    bars = fetch(ticker, days)
    summary(bars)
