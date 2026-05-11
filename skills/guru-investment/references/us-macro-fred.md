# FRED API 가이드 — 매크로 시계열 1차 소스

## 개요

**FRED (Federal Reserve Economic Data, St. Louis Fed)**: 미국 정부기관이 운영하는 매크로 시계열 데이터베이스. 80만+ 시계열 (Fed funds, Treasury yield curve, CPI, PCE, 실업률, 통화공급, 환율, 원자재 등). **Druckenmiller·Dalio·Marks·Soros 매크로 구루 분석 시 필수 1차 소스**. 한국 분석에서 매크로 보강이 필요할 때도 사용 (US 매크로가 KR 자산에 미치는 영향).

**핵심 가치:** 무료·키 발급만으로 평생 사용. 정부 1차 소스라 신뢰도 절대. WebSearch로 "현재 Fed rate" 묻는 것보다 시계열을 직접 받아 추세·변곡·과거 사이클과 비교 가능.

## 인증

키 환경변수: `FRED_API_KEY` (32자 hex). 모든 요청 URL에 `&api_key=$FRED_API_KEY` 필수.

```bash
curl "https://api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&api_key=$FRED_API_KEY&file_type=json"
```

Rate limit: **120 req/분**, 일일 무제한. 사실상 제한 없음.

## 핵심 엔드포인트 3개

| 엔드포인트 | 목적 |
|---|---|
| `/fred/series/observations` | 시계열 관측값 (가장 많이 사용) |
| `/fred/series` | 시계열 메타 (제목·단위·빈도·갱신일) |
| `/fred/series/search` | 키워드 시계열 검색 |

### 1. observations — 시계열 데이터

```
GET https://api.stlouisfed.org/fred/series/observations
  ?series_id=FEDFUNDS                # 시계열 ID
  &api_key=$FRED_API_KEY
  &file_type=json
  &observation_start=2020-01-01      # YYYY-MM-DD (옵션)
  &observation_end=2026-05-09        # YYYY-MM-DD (옵션)
  &limit=1000                        # 1~100,000 (기본 100,000)
  &sort_order=desc                   # asc / desc (기본 asc)
  &frequency=m                       # d/w/m/q/sa/a 변환 (옵션)
  &aggregation_method=avg            # avg / sum / eop (옵션)
```

**응답 구조**:
```json
{
  "count": 28,
  "observations": [
    {"date": "2024-06-01", "value": "5.33"},
    {"date": "2024-07-01", "value": "5.33"},
    ...
  ]
}
```

`value`가 `"."`이면 결측. 필터 필요:
```python
obs = [o for o in data['observations'] if o['value'] not in ('.', '')]
```

## 구루 분석 필수 시계열 ID 25개

### 금리 (Druckenmiller·Dalio·Marks)

| ID | 의미 | 빈도 |
|---|---|---|
| `FEDFUNDS` | Fed funds effective rate | 월 |
| `DFF` | Fed funds (일별 기준) | 일 |
| `DGS3MO` | 3M Treasury yield | 일 |
| `DGS2` | **2Y Treasury yield** ★ | 일 |
| `DGS10` | **10Y Treasury yield** ★ | 일 |
| `DGS30` | 30Y Treasury yield | 일 |
| `T10Y2Y` | **10Y - 2Y spread** ★ (장단기 역전 지표) | 일 |
| `T10Y3M` | 10Y - 3M spread (NBER 권장 침체 지표) | 일 |
| `MORTGAGE30US` | 30년 모기지 평균 금리 | 주 |

### 인플레이션 (Marks·Dalio·Buffett)

| ID | 의미 | 빈도 |
|---|---|---|
| `CPIAUCSL` | **CPI All Urban Consumers (Headline)** ★ | 월 |
| `CPILFESL` | Core CPI (식품·에너지 제외) | 월 |
| `PCEPI` | PCE Price Index | 월 |
| `PCEPILFE` | **Core PCE** ★ (Fed 선호 지표) | 월 |
| `PPIACO` | PPI All Commodities | 월 |
| `T5YIE` | 5Y breakeven inflation (TIPS spread) | 일 |

### 노동·경기 (Druckenmiller·Soros)

| ID | 의미 | 빈도 |
|---|---|---|
| `UNRATE` | **실업률** ★ | 월 |
| `PAYEMS` | 비농업 고용 (NFP) | 월 |
| `ICSA` | 신규 실업수당 청구 (선행) | 주 |
| `INDPRO` | 산업생산지수 | 월 |
| `RETAILSL` | 소매판매 | 월 |
| `UMCSENT` | 미시간 소비자심리지수 | 월 |
| `RSAFS` | 소매판매 advance | 월 |

### 통화·환율·자산 (Druckenmiller·Soros·Aschenbrenner)

| ID | 의미 | 빈도 |
|---|---|---|
| `M2SL` | **M2 통화공급** ★ | 월 |
| `WALCL` | Fed 자산 (QE/QT 추적) | 주 |
| `DTWEXBGS` | **달러 인덱스 (broad)** ★ | 일 |
| `DEXKOUS` | KRW/USD 환율 | 일 |
| `DEXJPUS` | JPY/USD 환율 | 일 |
| `DEXCHUS` | CNY/USD 환율 | 일 |

### 원자재 (Druckenmiller·Soros)

| ID | 의미 | 빈도 |
|---|---|---|
| `DCOILWTICO` | **WTI 원유** ★ | 일 |
| `DCOILBRENTEU` | Brent 원유 | 일 |
| `GOLDAMGBD228NLBM` | 금 (London PM fix) | 일 |
| `PCOPPUSDM` | 구리 (Global price) | 월 |
| `DHHNGSP` | Henry Hub 천연가스 | 일 |

### 위기 지표 (Marks·Dalio)

| ID | 의미 | 빈도 |
|---|---|---|
| `VIXCLS` | **VIX (S&P 옵션 변동성)** ★ | 일 |
| `BAMLH0A0HYM2` | High-yield credit spread (BofA) | 일 |
| `BAMLC0A0CM` | IG corporate spread | 일 |
| `STLFSI4` | St. Louis Fed Financial Stress Index | 주 |
| `NFCI` | Chicago Fed National Financial Conditions Index | 주 |

## 표준 워크플로우 — 구루 분석 시 매크로 컨텍스트 자동 수집

```python
import urllib.request, json, time, os
from datetime import date, timedelta

FRED_KEY = os.environ['FRED_API_KEY']

CORE_SERIES = {
    'fed_funds':       ('FEDFUNDS',     'monthly'),
    'us_2y':           ('DGS2',         'daily'),
    'us_10y':          ('DGS10',        'daily'),
    'yield_curve_2_10':('T10Y2Y',       'daily'),
    'cpi_yoy':         ('CPIAUCSL',     'monthly'),
    'core_pce':        ('PCEPILFE',     'monthly'),
    'unemployment':    ('UNRATE',       'monthly'),
    'dxy':             ('DTWEXBGS',     'monthly'),
    'krw_usd':         ('DEXKOUS',      'daily'),
    'wti':             ('DCOILWTICO',   'daily'),
    'vix':             ('VIXCLS',       'daily'),
    'm2':              ('M2SL',         'monthly'),
    'high_yield_spread':('BAMLH0A0HYM2','daily'),
}

def fetch_fred(series_id, start_date=None, limit=260):
    start = start_date or (date.today() - timedelta(days=5*365)).isoformat()
    url = (f"https://api.stlouisfed.org/fred/series/observations"
           f"?series_id={series_id}&api_key={FRED_KEY}&file_type=json"
           f"&observation_start={start}&limit=100000")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    obs = [o for o in data.get('observations', []) if o['value'] not in ('.', '')]
    return [{'date': o['date'], 'value': float(o['value'])} for o in obs[-limit:]]

def macro_snapshot():
    """현재 매크로 스냅샷 + 5년 추세."""
    out = {}
    for label, (sid, freq) in CORE_SERIES.items():
        try:
            obs = fetch_fred(sid)
            cur = obs[-1]
            yr_ago = obs[-13] if freq == 'monthly' else obs[-252] if len(obs) >= 252 else obs[0]
            out[label] = {
                'series': sid,
                'current': cur,
                'yoy_change': cur['value'] - yr_ago['value'],
                'recent_30': obs[-30:],
            }
        except Exception as e:
            out[label] = {'series': sid, '_err': str(e)}
        time.sleep(0.3)  # politeness
    return out
```

## 구루별 활용 패턴

### Druckenmiller — 매크로 + 바텀업

분석 시 표준 dashboard:
- **Fed funds + 2Y/10Y + yield curve**: 금리 사이클 위치
- **DXY**: 달러 강세/약세 (글로벌 자금 흐름 시그널)
- **High-yield spread + VIX**: risk-on/risk-off
- **WTI + Gold + Copper**: commodity 사이클 / inflation 시그널

기준: yield curve 역전 (T10Y2Y < 0) = 6~18개월 후 침체. 역전 해소 (re-steepening) = 침체 임박. 

### Dalio — All Weather 4계절 매크로

4사분면 분류:
- 성장 ↑ + 인플레 ↑: Fed 긴축 사이클 (현재 부분 해당)
- 성장 ↑ + 인플레 ↓: Goldilocks (주식 우호)
- 성장 ↓ + 인플레 ↓: 디플레 (채권 우호)
- 성장 ↓ + 인플레 ↑: 스태그플레이션

지표:
- 성장: PAYEMS YoY · INDPRO · RSAFS · UMCSENT
- 인플레: Core PCE · CPI YoY · breakeven (T5YIE)

### Marks — 사이클 인식 + 진자

- **VIX**: 진자가 공포(40+) ↔ 탐욕(15-) 위치
- **High-yield spread**: 신용 사이클 (확장/긴축)
- **Credit spread + VIX 동시 상승**: 진자가 비관 측 → quality buy 영역

### Soros — 반사성 + 통화 베팅

- **DXY + commodity 통화 (AUD, CAD)**: USD funding 시그널
- **EM 환율 (DEXKOUS, DEXBZUS)**: hot money flow
- 통화 위기 패턴: 단기 외환보유고 ↓ + 환율 약세 + interest 인상 + capital outflow

### Buffett — 거의 안 보지만 한 번씩

- **10Y Treasury yield**: discount rate 비교 기준 (Owner Earnings yield > 10Y가 매수 기준)
- **Buffett Indicator**: Wilshire 5000 / GDP — FRED `WILL5000PRFC` / `GDP`로 직접 계산

## 한국 주식 분석 시 활용

한국 종목도 미국 매크로 환경 영향 받음. 특히:
- **DXY + KRW**: 외국인 매수·매도 흐름
- **US 10Y yield**: 한국 채권·환율 동조
- **High-yield spread**: risk-on/risk-off로 신흥 시장 자금 흐름
- **WTI**: 정유·화학 종목 마진 영향
- **Copper**: 전선·산업재 종목 영향

한국 매크로 1차 소스는 별도 한국은행 ECOS API 필요 (현재 미발급).

## 함정·주의

- **빈도 차이**: 일별 시계열은 영업일만 (주말·공휴일 빈값). 월별과 비교 시 frequency 변환 필요
- **`value = "."`**: 결측 처리 필수
- **갱신 지연**: CPI는 익월 중순, PCE는 익월말, GDP는 분기말 +1개월. WebSearch로 보완 시 발표 일정 명시
- **Index vs YoY**: CPIAUCSL은 인덱스 (1982-84=100). YoY 계산은 본인 책임 — 13개월 전 값과 비교
- **Real vs Nominal**: 원자재·금리는 nominal. 실질치는 별도 (PCE 디플레이트 후 계산 등)
- **Series ID 변경**: FRED는 가끔 시계열 ID 변경. 404 시 search 엔드포인트로 재검색

## 자주 쓰는 빠른 호출 패턴

```bash
# 현재 Fed funds rate
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&api_key=$FRED_API_KEY&file_type=json&sort_order=desc&limit=1" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['observations'][0])"

# 10Y yield 5년 시계열
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=$FRED_API_KEY&file_type=json&observation_start=2021-01-01"

# CPI YoY (직접 계산)
# 최근 + 13개월 전 값 받아서 (cur/year_ago - 1) * 100
```
