# yfinance 가이드 — 미국·글로벌 시장 데이터

## 개요

`yfinance`는 Yahoo Finance의 비공식 Python 래퍼. 미국·글로벌 종목의 **가격·info·기관·인사이더·애널리스트 추천·earnings calendar**를 키 불필요로 제공. SEC EDGAR가 펀더멘탈 1차 소스라면 yfinance는 **시장 데이터 + 보조 메타** 1차 소스 (한국 KRX 등가물).

**핵심 가치:** Forward PE·PEG·52주 고저·MA 계산용 일봉·analyst price targets·institutional holders·insider transactions를 한 라이브러리로 통합 조회. SEC + yfinance 조합이 현재 미장 분석 표준 스택.

## 설치 및 환경

```bash
pip3 install --user yfinance
```

키 발급 불필요. import 후 즉시 사용. 단 Yahoo가 가끔 (연 2~3회) 스크레이프 막아 라이브러리 깨지는 경우 발생 — 며칠 내 패치됨. 깨질 경우 fallback은 Stooq csv 또는 SEC + 시장 거래소 직접.

```python
import yfinance as yf
import warnings; warnings.filterwarnings('ignore')

t = yf.Ticker("AAPL")
```

## 핵심 메서드

### 1. `t.info` — 종합 메타 (가장 자주 쓰는 한 방)

반환: dict (200+ 필드). 핵심 사용 필드:

| 필드 | 의미 | 예시 (AAPL) |
|---|---|---|
| `currentPrice` | 현재가 | 293.32 |
| `marketCap` | 시총 | 4,308,095,467,520 |
| `beta` | 5년 베타 | 1.065 |
| `trailingPE` | TTM PER | 35.47 |
| `forwardPE` | Forward PER | 30.68 |
| `pegRatio` | PEG | 2.52 |
| `priceToBook` | PBR | 40.40 |
| `dividendYield` | 배당수익률 (%) | 0.37 |
| `payoutRatio` | 배당성향 | 0.126 |
| `sharesOutstanding` | 발행주식수 | 14,687,355,344 |
| `floatShares` | 유동주식수 | 14,662,240,621 |
| `heldPercentInsiders` | 인사이더 보유율 | 0.0164 |
| `heldPercentInstitutions` | 기관 보유율 | 0.6535 |
| `fiftyTwoWeekHigh` | 52주 고점 | 294.76 |
| `fiftyTwoWeekLow` | 52주 저점 | 192.87 |
| `averageVolume` | 평균 거래량 | 44,381,843 |
| `averageVolume10days` | 10일 평균 | 53,546,890 |
| `sector` / `industry` | 섹터·산업 | Technology / Consumer Electronics |
| `fullTimeEmployees` | 직원 수 | 166,000 |
| `website` / `longBusinessSummary` | 회사 정보 | — |

### 2. `t.history(period=...)` — 가격 일봉

```python
h = t.history(period="5y")  # "1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"
h = t.history(start="2023-05-01", end="2026-05-08")  # 명시 범위
```

DataFrame: index = Date (timezone-aware), columns = Open/High/Low/Close/Volume/Dividends/Stock Splits.

**MA·52주 직접 계산 패턴**:
```python
import statistics as st
prices = [float(r['Close']) for _, r in h.iterrows()]
ma20  = st.mean(prices[-20:])
ma50  = st.mean(prices[-50:])
ma150 = st.mean(prices[-150:])
ma200 = st.mean(prices[-200:])
high_52w = max(float(r['High']) for _, r in h.tail(252).iterrows())
low_52w  = min(float(r['Low']) for _, r in h.tail(252).iterrows())
```

### 3. `t.analyst_price_targets` — 컨센 목표가

```python
{'current': 293.32, 'high': 355.0, 'low': 215.0, 'mean': 303.38, 'median': 310.0}
```

mean·median과 현재가 비교로 +/- 업사이드 즉시 산출.

### 4. `t.earnings_dates` — 분기 실적 캘린더 + EPS surprise

DataFrame: 미래 발표 예정 + 과거 8분기 EPS Estimate / Reported / Surprise(%). 8분기 연속 beat 패턴 등 추출.

```python
ed = t.earnings_dates
# 컬럼: EPS Estimate, Reported EPS, Surprise(%)
```

### 5. `t.institutional_holders` — Top 10 기관

DataFrame: Date Reported / Holder / pctHeld / Shares / Value / pctChange. **pctChange가 결정적** — Berkshire/JPMorgan 등의 추세적 매수·매도 식별.

```python
ih = t.institutional_holders
# 컬럼: Date Reported, Holder, pctHeld, Shares, Value, pctChange
```

### 6. `t.major_holders` — 보유 비중 요약

```python
{'insidersPercentHeld': 0.0164,
 'institutionsPercentHeld': 0.6535,
 'institutionsFloatPercentHeld': 0.6644,
 'institutionsCount': 7558}
```

### 7. `t.insider_transactions` — 인사이더 거래 (최근)

DataFrame: Shares / Value / Transaction Start Date / Ownership / Insider 등. SEC Form 4의 yfinance 가공본. 18개월 패턴 분석 시 SEC Form 4 본문이 더 정확하지만 빠른 스크리닝엔 충분.

### 8. `t.recommendations` — 분석사 추천 분포

DataFrame: period (0m, -1m, -2m, -3m) / strongBuy / buy / hold / sell / strongSell. 4개월 추세 변화로 분석사 의견 흐름 추출.

```python
{'period': '0m', 'strongBuy': 7, 'buy': 24, 'hold': 15, 'sell': 1, 'strongSell': 1}
```

### 9. `t.calendar` — 다음 실적 발표·배당 일정

dict: Earnings Date / EPS Estimate / Revenue Estimate / Dividend Date 등.

### 10. `t.dividends` / `t.splits` — 배당·분할 history

Series: index Date, value 배당금 / 분할비율.

### 11. `t.options` / `t.option_chain(date)` — 옵션 체인 (선물 트레이더용)

Druckenmiller·Soros 같은 매크로 트레이더 분석 시 IV·풋콜 비율로 시장 sentiment 추정 가능.

## 워크플로우 — 한 번에 캐시 (AAPL 분석 검증 패턴)

```python
import yfinance as yf, json, datetime, warnings
warnings.filterwarnings('ignore')

def cache_ticker(ticker, output_path):
    t = yf.Ticker(ticker)
    cache = {}
    cache['info'] = t.info
    cache['analyst_price_targets'] = t.analyst_price_targets

    ed = t.earnings_dates
    cache['earnings_dates'] = ed.reset_index().to_dict('records') if ed is not None else None

    ih = t.institutional_holders
    cache['institutional_holders'] = ih.to_dict('records') if ih is not None else None

    mh = t.major_holders
    cache['major_holders'] = mh.reset_index().to_dict('records') if mh is not None else None

    it = t.insider_transactions
    cache['insider_transactions'] = it.to_dict('records') if it is not None else None

    rec = t.recommendations
    cache['recommendations'] = rec.to_dict('records') if rec is not None else None

    h = t.history(period="5y")
    cache['price_history_5y'] = [
        {'date': d.strftime('%Y-%m-%d'),
         'open': float(r['Open']), 'high': float(r['High']),
         'low': float(r['Low']), 'close': float(r['Close']),
         'volume': int(r['Volume'])}
        for d, r in h.iterrows()
    ]

    cache['dividends'] = [
        {'date': d.strftime('%Y-%m-%d'), 'amount': float(v)}
        for d,v in t.dividends.items()
    ][-30:]
    cache['splits'] = [
        {'date': d.strftime('%Y-%m-%d'), 'ratio': float(v)}
        for d,v in t.splits.items()
    ]

    cache['_pulled_at'] = datetime.datetime.now().isoformat()
    with open(output_path, 'w') as f:
        json.dump(cache, f, indent=2, default=str)
```

AAPL 기준 캐시 ≈ 285KB. 5년 일봉 1,256일 + 메타 통합.

## Minervini Trend Template 자동화 (`scripts/ta_utils.py`와 결합)

```python
def minervini_trend_template(prices):
    """
    7개 항목 자동 체크. RS는 별도 (S&P 500 대비 1년 수익률 비교 필요).
    """
    import statistics as st
    last = prices[-1]
    ma50  = st.mean(prices[-50:])
    ma150 = st.mean(prices[-150:])
    ma200 = st.mean(prices[-200:])
    ma200_1mo_ago = st.mean(prices[-220:-20])
    high_52w = max(prices[-252:])
    low_52w  = min(prices[-252:])

    return {
        '1_above_ma150_ma200': last > ma150 and last > ma200,
        '2_ma150_above_ma200': ma150 > ma200,
        '3_ma200_uptrending':  ma200 > ma200_1mo_ago,
        '4_above_ma50_stack':  last > ma50 and ma50 > ma150 and ma50 > ma200,
        '5_above_30pct_low':   last >= low_52w * 1.30,
        '6_within_25pct_high': last >= high_52w * 0.75,
        '7_5d_momentum':       prices[-1] > prices[-5],
    }
```

## 한국 ↔ 미국 등가 매핑

<table>
<thead><tr><th>한국 (KRX)</th><th>미국 (yfinance)</th></tr></thead>
<tbody>
<tr><td>일봉 OHLCV</td><td>t.history(period="5y")</td></tr>
<tr><td>시가총액·발행주식수</td><td>t.info[marketCap, sharesOutstanding]</td></tr>
<tr><td>52주 고저</td><td>t.info[fiftyTwoWeekHigh/Low]</td></tr>
<tr><td>외국인·기관·개인 매매</td><td>t.institutional_holders (월별·기관별)</td></tr>
<tr><td>(없음)</td><td>t.recommendations (분석사 추천 분포)</td></tr>
<tr><td>(없음)</td><td>t.analyst_price_targets (컨센 TP)</td></tr>
<tr><td>증권사 리포트 PDF</td><td>(yfinance 미제공 — 별도)</td></tr>
</tbody>
</table>

## 함정·주의

- **데이터 신선도**: yfinance는 Yahoo가 갱신할 때마다 갱신. 분기 실적은 발표 후 1~2일 지연 가능
- **Yahoo 차단 사고**: 연 2~3회 라이브러리 깨짐. `pip install --upgrade yfinance` 또는 며칠 대기
- **`t.info` rate limit**: 동일 ticker 1초 내 반복 호출 시 일부 필드 빈값 반환 가능. 한 번 캐시
- **글로벌 ticker**: 미국 외 종목은 suffix 필요. 도쿄 `7203.T`, 런던 `BARC.L`, 한국 `005930.KS`(삼성전자 코스피), `009150.KQ` 등. 한국 종목은 KRX API 우선 — yfinance는 시세 지연·갱신 누락 잦음
- **Earnings call transcripts**: yfinance 미제공. 회사 IR 사이트 또는 별도 유료 소스
- **Forward EPS 분기 컨센**: yfinance는 연간 컨센만. 분기는 Finnhub free 활용

## 사용 우선순위 (미장 분석)

| 데이터 | 1순위 | 2순위 |
|---|---|---|
| 펀더멘탈 시계열 | SEC XBRL companyfacts | yfinance financials (보조) |
| 공시 본문 | SEC EDGAR Archives | — |
| 가격·MA·52주 | yfinance.history | — |
| 시총·PER·PEG | yfinance.info | — |
| 기관 보유 변동 | yfinance.institutional_holders | SEC 13F (분기) |
| 인사이더 거래 | SEC Form 4 본문 | yfinance.insider_transactions |
| 컨센 TP·추천 | yfinance.analyst_price_targets · recommendations | Finnhub |
| 분기 컨센 EPS | Finnhub | WebSearch |
| 매크로 (Fed·CPI·yield) | FRED API | yfinance (DXY 등 일부) |
