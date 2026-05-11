#!/usr/bin/env python3
"""
fetch_us_bundle.py — guru-investment 미국 종목 일괄 수집기 (한국 fetch_dart_bundle.py 등가)

사용법:
    python3 fetch_us_bundle.py AAPL [output_dir]
    python3 fetch_us_bundle.py --cik 0000320193 [output_dir]

수집 항목:
    SEC EDGAR (키 불필요, User-Agent만 필요):
      - submissions.json       (회사 메타 + 18개월 공시 목록)
      - companyfacts.json      (us-gaap 503개 컨셉 시계열)
      - filings/{label}.htm    (Tier 1 본문 — 10-K, 10-Q, DEF 14A, 8-K Item 5.02)
      - submissions_18m.json   (18개월 필터 + 3-Tier 분류 결과)

    yfinance (키 불필요):
      - yfinance_cache.json    (info, history 5y, analyst_TP, holders, insider, recommendations)

    Optional (환경변수 있을 때):
      - FRED_API_KEY  → fred_macro.json (Fed funds, 10Y yield, CPI, PCE 등)
      - FINNHUB_API_KEY → finnhub_estimates.json (분기 컨센, earnings calendar)

EDGAR_IDENTITY 환경변수에 "Name email@domain.com" 형식으로 식별자 설정 권장.
없으면 기본값 사용.
"""
import sys, os, json, urllib.request, urllib.parse, datetime, time
from collections import Counter, defaultdict
from datetime import timedelta

UA = os.environ.get("EDGAR_IDENTITY", "Your-Project your.email@example.com")
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:0>10}.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:0>10}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{primary_doc}"

TIER1_FORMS = {'8-K', '10-K', '10-Q', 'DEF 14A', 'PRE 14A',
               'SC 13G', 'SC 13G/A', 'SC 13D', 'SC 13D/A',
               'S-1', 'S-3', 'S-4', '20-F', '6-K'}
TIER2_FORMS = {'4', '4/A', '3', '5', 'SD', 'CORRESP'}

# 8-K Item Code priority (Tier 1 본문 정독 대상)
TIER1_8K_ITEMS = {'5.02', '2.02', '5.07', '8.01', '1.01', '2.01', '3.02'}


def fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_text(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')


def ticker_to_cik(ticker):
    data = fetch_json(TICKERS_URL)
    upper = ticker.upper()
    for entry in data.values():
        if entry['ticker'] == upper:
            return f"{entry['cik_str']:010d}", entry['title']
    raise ValueError(f"Ticker {ticker} not found in SEC tickers list")


def classify_tier(form, items=''):
    if form in TIER1_FORMS:
        if form == '8-K':
            # 8-K는 item code로 추가 분류
            item_codes = {x.strip() for x in items.split(',')}
            if item_codes & TIER1_8K_ITEMS:
                return 1
            return 2  # 7.01(FD) 등은 Tier 2
        return 1
    if form in TIER2_FORMS: return 2
    return 3


def filter_18months(recent, months=18):
    cutoff = (datetime.date.today() - timedelta(days=months*30)).isoformat()
    n = len(recent['accessionNumber'])
    out = []
    for i in range(n):
        if recent['filingDate'][i] >= cutoff:
            out.append({
                'date': recent['filingDate'][i],
                'form': recent['form'][i],
                'accession': recent['accessionNumber'][i],
                'primary_doc': recent['primaryDocument'][i],
                'rdate': recent['reportDate'][i],
                'items': recent.get('items', [''] * n)[i],
                'description': recent.get('primaryDocDescription', [''] * n)[i],
            })
    return out


def fetch_filing_body(cik_num, accession, primary_doc):
    acc_clean = accession.replace('-', '')
    url = ARCHIVE_URL.format(cik=int(cik_num), acc_clean=acc_clean, primary_doc=primary_doc)
    return fetch_text(url), url


def fetch_yfinance_cache(ticker):
    import yfinance as yf
    import warnings
    warnings.filterwarnings('ignore')
    t = yf.Ticker(ticker)
    cache = {'_pulled_at': datetime.datetime.now().isoformat()}
    try: cache['info'] = t.info
    except Exception as e: cache['info'] = {'_err': str(e)}
    try: cache['analyst_price_targets'] = t.analyst_price_targets
    except Exception as e: cache['analyst_price_targets'] = {'_err': str(e)}
    try:
        ed = t.earnings_dates
        cache['earnings_dates'] = ed.reset_index().to_dict('records') if ed is not None else None
    except Exception as e: cache['earnings_dates'] = {'_err': str(e)}
    try:
        ih = t.institutional_holders
        cache['institutional_holders'] = ih.to_dict('records') if ih is not None else None
    except Exception as e: cache['institutional_holders'] = {'_err': str(e)}
    try:
        mh = t.major_holders
        cache['major_holders'] = mh.reset_index().to_dict('records') if mh is not None else None
    except Exception as e: cache['major_holders'] = {'_err': str(e)}
    try:
        it_ = t.insider_transactions
        cache['insider_transactions'] = it_.to_dict('records') if it_ is not None else None
    except Exception as e: cache['insider_transactions'] = {'_err': str(e)}
    try:
        rec = t.recommendations
        cache['recommendations'] = rec.to_dict('records') if rec is not None else None
    except Exception as e: cache['recommendations'] = {'_err': str(e)}
    try:
        h = t.history(period="5y")
        cache['price_history_5y'] = [
            {'date': d.strftime('%Y-%m-%d'),
             'open': float(r['Open']), 'high': float(r['High']),
             'low': float(r['Low']), 'close': float(r['Close']),
             'volume': int(r['Volume'])}
            for d, r in h.iterrows()
        ]
    except Exception as e: cache['price_history_5y'] = {'_err': str(e)}
    try:
        cache['dividends'] = [
            {'date': d.strftime('%Y-%m-%d'), 'amount': float(v)}
            for d, v in t.dividends.items()
        ][-30:]
    except Exception as e: cache['dividends'] = {'_err': str(e)}
    try:
        cache['splits'] = [
            {'date': d.strftime('%Y-%m-%d'), 'ratio': float(v)}
            for d, v in t.splits.items()
        ]
    except Exception as e: cache['splits'] = {'_err': str(e)}
    return cache


def fetch_fred_macro(api_key):
    """FRED 핵심 매크로 시계열. 키 있을 때만."""
    series_ids = {
        'fed_funds': 'FEDFUNDS',          # Fed funds effective rate (월)
        'us_10y': 'DGS10',                # 10Y Treasury yield (일)
        'us_2y': 'DGS2',                  # 2Y Treasury yield (일)
        'cpi': 'CPIAUCSL',                # CPI all items (월)
        'pce': 'PCEPI',                   # PCE price index (월)
        'core_pce': 'PCEPILFE',           # Core PCE (월)
        'unemployment': 'UNRATE',         # 실업률 (월)
        'dxy': 'DTWEXBGS',                # 달러 인덱스 broad (월)
        'wti_oil': 'DCOILWTICO',          # WTI 원유 (일)
        'gold': 'GOLDAMGBD228NLBM',       # 금 가격 (일)
        'm2': 'M2SL',                     # M2 통화 공급 (월)
    }
    today = datetime.date.today().isoformat()
    start = (datetime.date.today() - timedelta(days=5*365)).isoformat()
    out = {}
    for label, sid in series_ids.items():
        url = (f"https://api.stlouisfed.org/fred/series/observations"
               f"?series_id={sid}&api_key={api_key}&file_type=json"
               f"&observation_start={start}&observation_end={today}")
        try:
            data = fetch_json(url)
            obs = [o for o in data.get('observations', []) if o['value'] not in ('.', '')]
            out[label] = {'series_id': sid,
                          'observations': [{'date': o['date'], 'value': float(o['value'])} for o in obs[-260:]]}
        except Exception as e:
            out[label] = {'series_id': sid, '_err': str(e)}
        time.sleep(0.3)
    return out


def fetch_finnhub(ticker, api_key):
    """Finnhub free 티어 — 작동 엔드포인트만 호출. 분기 컨센은 calendar/earnings로 우회."""
    today = datetime.date.today().isoformat()
    end_1y = (datetime.date.today() + timedelta(days=365)).isoformat()
    start_30d = (datetime.date.today() - timedelta(days=30)).isoformat()
    out = {}
    endpoints = {
        # 분기 컨센 EPS·Rev은 free 차단 → calendar/earnings에서 같은 데이터 추출
        'earnings_calendar': f'https://finnhub.io/api/v1/calendar/earnings?symbol={ticker}&from={today}&to={end_1y}&token={api_key}',
        'recommendation':    f'https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={api_key}',
        'profile':           f'https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={api_key}',
        'peers':             f'https://finnhub.io/api/v1/stock/peers?symbol={ticker}&token={api_key}',
        'recent_news':       f'https://finnhub.io/api/v1/company-news?symbol={ticker}&from={start_30d}&to={today}&token={api_key}',
    }
    for label, url in endpoints.items():
        try:
            out[label] = fetch_json(url)
        except Exception as e:
            out[label] = {'_err': str(e)}
        time.sleep(0.3)
    return out


def main():
    args = sys.argv[1:]
    if len(args) == 0:
        print(__doc__); sys.exit(1)

    if args[0] == '--cik':
        cik = args[1].zfill(10)
        ticker_or_cik = cik
        title = None
        out_dir = args[2] if len(args) > 2 else f"{cik}_data"
    else:
        ticker = args[0]
        cik, title = ticker_to_cik(ticker)
        ticker_or_cik = ticker
        out_dir = args[1] if len(args) > 1 else f"{ticker}_data"

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(f"{out_dir}/filings", exist_ok=True)
    print(f"=== Fetching {ticker_or_cik} (CIK {cik}) → {out_dir}/ ===")
    if title: print(f"  Company: {title}")
    print(f"  EDGAR_IDENTITY: {UA}")

    # 1) submissions
    print("\n[1/4] submissions...")
    sub_url = SUBMISSIONS_URL.format(cik=cik)
    sub = fetch_json(sub_url)
    json.dump(sub, open(f"{out_dir}/submissions.json", 'w'), indent=2)
    print(f"  saved submissions.json ({os.path.getsize(f'{out_dir}/submissions.json')//1024} KB)")
    print(f"  cik={sub.get('cik')}, name={sub.get('name')}, sic={sub.get('sic')} ({sub.get('sicDescription')})")

    # 2) companyfacts
    print("\n[2/4] companyfacts (XBRL)...")
    cf_url = COMPANYFACTS_URL.format(cik=cik)
    try:
        cf = fetch_json(cf_url)
        json.dump(cf, open(f"{out_dir}/companyfacts.json", 'w'), indent=2)
        print(f"  saved companyfacts.json ({os.path.getsize(f'{out_dir}/companyfacts.json')//1024} KB)")
        print(f"  us-gaap concepts: {len(cf['facts'].get('us-gaap', {}))}")
    except Exception as e:
        print(f"  ERR: {e} (continue)")

    # 3) 18-month filter + Tier classification
    print("\n[3/4] 18-month filings + 3-Tier...")
    recent = sub['filings']['recent']
    filings_18m = filter_18months(recent)
    for r in filings_18m:
        r['tier'] = classify_tier(r['form'], r['items'])
    by_tier = Counter(r['tier'] for r in filings_18m)
    by_form = Counter(r['form'] for r in filings_18m)
    print(f"  total 18m filings: {len(filings_18m)}")
    print(f"  tier counts: {dict(by_tier)}")
    print(f"  top forms: {dict(sorted(by_form.items(), key=lambda x: -x[1])[:8])}")

    out = {
        'cutoff': (datetime.date.today() - timedelta(days=18*30)).isoformat(),
        'total': len(filings_18m),
        'tier_counts': dict(by_tier),
        'form_counts': dict(by_form),
        'tier1': [r for r in filings_18m if r['tier'] == 1],
        'tier2_forms': dict(Counter(r['form'] for r in filings_18m if r['tier'] == 2)),
        'tier3_forms': dict(Counter(r['form'] for r in filings_18m if r['tier'] == 3)),
    }
    json.dump(out, open(f"{out_dir}/submissions_18m.json", 'w'), indent=2)
    print(f"  saved submissions_18m.json")

    # Tier 1 본문 다운로드
    print(f"\n  fetching {len(out['tier1'])} Tier 1 bodies...")
    cik_num = int(cik)
    for r in out['tier1']:
        try:
            html, url = fetch_filing_body(cik_num, r['accession'], r['primary_doc'])
            label = f"{r['date']}_{r['form'].replace(' ','').replace('/','-')}"
            if r['form'] == '8-K' and r['items']:
                label += f"_item{r['items'].replace(',','-')}"
            label = label[:80] + '.htm'
            path = f"{out_dir}/filings/{label}"
            open(path, 'w').write(html)
            print(f"    [{len(html)//1024:>4} KB] {label}")
            time.sleep(0.15)  # politeness
        except Exception as e:
            print(f"    ERR {r['accession']}: {e}")

    # 4) yfinance cache
    print("\n[4/4] yfinance cache...")
    if args[0] != '--cik':
        try:
            yf_cache = fetch_yfinance_cache(ticker_or_cik)
            json.dump(yf_cache, open(f"{out_dir}/yfinance_cache.json", 'w'), indent=2, default=str)
            print(f"  saved yfinance_cache.json ({os.path.getsize(f'{out_dir}/yfinance_cache.json')//1024} KB)")
        except ImportError:
            print("  yfinance not installed: pip3 install --user yfinance")
        except Exception as e:
            print(f"  ERR: {e}")

    # Optional — FRED
    fred_key = os.environ.get('FRED_API_KEY')
    if fred_key:
        print("\n[opt] FRED macro...")
        try:
            fred = fetch_fred_macro(fred_key)
            json.dump(fred, open(f"{out_dir}/fred_macro.json", 'w'), indent=2)
            print(f"  saved fred_macro.json ({os.path.getsize(f'{out_dir}/fred_macro.json')//1024} KB)")
        except Exception as e:
            print(f"  ERR: {e}")

    # Optional — Finnhub
    finnhub_key = os.environ.get('FINNHUB_API_KEY')
    if finnhub_key and args[0] != '--cik':
        print("\n[opt] Finnhub estimates...")
        try:
            fh = fetch_finnhub(ticker_or_cik, finnhub_key)
            json.dump(fh, open(f"{out_dir}/finnhub_estimates.json", 'w'), indent=2)
            print(f"  saved finnhub_estimates.json")
        except Exception as e:
            print(f"  ERR: {e}")

    print(f"\n=== DONE → {out_dir}/ ===")
    print("Outputs:")
    for f in sorted(os.listdir(out_dir)):
        if os.path.isdir(f"{out_dir}/{f}"):
            n = len(os.listdir(f"{out_dir}/{f}"))
            print(f"  {f}/ ({n} files)")
        else:
            print(f"  {f} ({os.path.getsize(f'{out_dir}/{f}')//1024} KB)")


if __name__ == '__main__':
    main()
