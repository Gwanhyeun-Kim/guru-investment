# Finnhub 가이드 — 분기 컨센·뉴스·추천 트렌드 (Free 티어)

## 개요

**Finnhub**: 스위스 기반 핀테크 데이터 회사. 미국·글로벌 종목의 분석사 컨센서스·뉴스·earnings calendar·추천 트렌드를 제공. 핵심은 **분기별 EPS·Revenue 컨센서스** (yfinance가 연간만 주는 것 보완) + **분석사 추천 월별 추세 시계열** + **회사별 뉴스 헤드라인**.

**핵심 가치:** SEC + yfinance 조합의 빈 자리 메움. 분기 가이던스 vs 컨센 비교, 분석사 의견 변화 추적, 단기 뉴스 모니터링에 사용.

## 인증

키 환경변수: `FINNHUB_API_KEY`. URL에 `&token=$FINNHUB_API_KEY`로 전달.

```bash
curl "https://finnhub.io/api/v1/calendar/earnings?symbol=AAPL&token=$FINNHUB_API_KEY"
```

Rate limit: **60 req/분**, 일일 무제한 (free 티어). 우리 용도엔 충분.

## Free 티어 작동 엔드포인트 7개 (검증됨)

### 1. ⭐ Earnings Calendar — 분기 컨센 + 발표 일정

```
GET /api/v1/calendar/earnings
  ?symbol=AAPL                 # 옵션 (지정 시 한 종목)
  &from=2026-05-01             # YYYY-MM-DD
  &to=2026-08-31
  &token=$FINNHUB_API_KEY
```

**활용**: yfinance는 분기별 컨센 EPS·Rev 직접 못 받지만 **calendar/earnings에 포함됨**.

```json
{"earningsCalendar": [
  {"date": "2026-07-29", "hour": "amc",
   "symbol": "AAPL",
   "epsEstimate": 1.9105,
   "revenueEstimate": 109573000000,
   "year": 2026, "quarter": 3}
]}
```

→ AAPL 다음 분기 (2026 Q3, 7/29 발표) 컨센: EPS $1.91 / Rev $109.6B. 이게 free 티어에서 분기 컨센 받는 우회로.

### 2. ⭐ Recommendation Trends — 월별 분석사 추천 시계열

```
GET /api/v1/stock/recommendation?symbol=AAPL&token=$FINNHUB_API_KEY
```

**응답 (최근 4개월)**:
```json
[
  {"period":"2026-05-01", "strongBuy":15, "buy":24, "hold":13, "sell":2, "strongSell":0, "symbol":"AAPL"},
  {"period":"2026-04-01", "strongBuy":14, "buy":23, "hold":15, "sell":2, "strongSell":0},
  {"period":"2026-03-01", "strongBuy":14, "buy":22, "hold":16, "sell":2, "strongSell":0},
  {"period":"2026-02-01", "strongBuy":14, "buy":21, "hold":17, "sell":2, "strongSell":0}
]
```

**yfinance.recommendations와 비교**: yfinance는 4개 시점(0m, -1m, -2m, -3m)만, Finnhub은 더 긴 추세 + 정확한 일자 라벨. **분석사 의견 변화 추적**에 강함 (Hold → Buy 이동 등).

### 3. Company News — 회사별 뉴스 헤드라인

```
GET /api/v1/company-news
  ?symbol=AAPL
  &from=2026-05-01
  &to=2026-05-09
  &token=$FINNHUB_API_KEY
```

**응답**: 카테고리·datetime·headline·source·url·summary 배열.

**활용**: 분기 사이 단기 뉴스·이벤트 모니터링. 18개월 공시 분석 보조.

### 4. Company Profile

```
GET /api/v1/stock/profile2?symbol=AAPL&token=$FINNHUB_API_KEY
```

회사 기본 정보. yfinance.info와 중복이지만 가벼움 (1KB 미만).

### 5. Financials Reported (XBRL)

```
GET /api/v1/stock/financials-reported?symbol=AAPL&freq=quarterly&token=$FINNHUB_API_KEY
```

SEC XBRL 가공본. **SEC companyfacts API가 더 깊으니 보통 안 쓰지만**, accessNumber 매핑이나 필요할 때 보조.

### 6. Stock Peers

```
GET /api/v1/stock/peers?symbol=AAPL&token=$FINNHUB_API_KEY
```

**응답**: `["AAPL","SNDK","DELL","WDC","HPE","P","NTAP","SMCI","HPQ","IONQ"]`

yfinance는 메가캡 위주, Finnhub은 더 industry-narrow한 peer 선정. Lynch·Greenblatt 분석에서 동종비교 시 보조.

### 7. IPO Calendar

```
GET /api/v1/calendar/ipo?from=2026-05-01&to=2026-06-30&token=$FINNHUB_API_KEY
```

향후 IPO 일정. 산업 분석 시 신규 진입 종목 추적.

## ❌ Free 차단 (premium 전용)

- `stock/eps-estimate` (분기 컨센 EPS 단독) → calendar/earnings로 우회
- `stock/revenue-estimate` (분기 컨센 Rev 단독) → calendar/earnings로 우회
- `stock/price-target` (목표가 컨센) → yfinance.analyst_price_targets로 대체
- `news-sentiment` (뉴스 sentiment 분석) → 직접 분석
- `earnings-call-transcript` (콜 transcripts) → 회사 IR 사이트 PDF 직접

## 표준 워크플로우 — 종목 분석 시 자동 수집

```python
import urllib.request, json, time, os

KEY = os.environ['FINNHUB_API_KEY']
BASE = 'https://finnhub.io/api/v1'

def fh(endpoint, **params):
    params['token'] = KEY
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}/{endpoint}?{qs}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())

def collect_finnhub(ticker):
    out = {}
    out['recommendation'] = fh('stock/recommendation', symbol=ticker)
    time.sleep(0.3)
    out['profile'] = fh('stock/profile2', symbol=ticker)
    time.sleep(0.3)
    out['peers'] = fh('stock/peers', symbol=ticker)
    time.sleep(0.3)
    # 다음 4분기 컨센
    today = datetime.date.today()
    end = (today + datetime.timedelta(days=365)).isoformat()
    out['earnings_calendar'] = fh('calendar/earnings', symbol=ticker,
                                   **{'from': today.isoformat(), 'to': end})
    time.sleep(0.3)
    # 최근 30일 뉴스
    start = (today - datetime.timedelta(days=30)).isoformat()
    out['recent_news'] = fh('company-news', symbol=ticker,
                             **{'from': start, 'to': today.isoformat()})
    return out
```

## 구루별 활용 패턴

### Druckenmiller — 컨센 vs 가이던스 spread

다음 분기 EPS·Rev 컨센 받아 회사 가이던스(10-Q·8-K Item 2.02 본문)와 비교. **컨센 < 가이던스** (회사가 더 자신 있음) 패턴이면 surprise beat 가능성. 반대 (컨센 > 가이던스) 면 미스 risk.

### Lynch — 분석사 의견 변화 추세

`recommendation` 6개월 시계열로 추적:
- Hold 비중 ↓ + Buy 비중 ↑ = 의견 turn (positive 모멘텀)
- Strong Buy 신규 등장 (주요 sell-side house) = Lynch의 "10-bagger" 후보 시그널

### Marks — Sentiment 변곡점

Recommendation 분포가 한 방향으로 너무 쏠리면 (Buy/SB 70%+) **진자 낙관 측 = 비대칭 risk 불리**. 반대로 Hold/Sell이 많으면 (40%+) **진자 비관 측 = 매수 검토 영역**.

### Buffett — 잘 안 봄

Buffett은 분석사 컨센 안 봄. 다만 다음 분기 발표 일정 확인용으로만 사용.

## 한국 주식 적용 가능?

Finnhub은 한국 종목도 일부 커버 (e.g., `005930.KS` 삼성전자) but:
- 데이터 신선도 낮음 (DART보다 1~2주 지연)
- 한국 분석사 컨센 미반영 (글로벌 brokers만)
- 한국 분석은 **DART + KRX + WebSearch**가 더 깊고 정확
- → **미국·글로벌 종목 전용**으로 사용 권장

## 함정·주의

- **Free rate limit 60/분**: 종목 5~10개 동시 분석 시 batch 제어 필요. `time.sleep(0.3)` 권장
- **403 응답**: Premium 차단 항목. 위 작동 7개만 사용
- **데이터 신선도**: 추천 트렌드는 매월 1일 갱신. 분기 컨센은 EPS 발표 직후 빠르게 갱신
- **글로벌 종목**: 미국 외 ticker에 suffix 필요 (`SAMSUNG.KS` 같이). 국내 종목은 KRX·DART 우선
- **API 변경**: Finnhub은 free 정책을 가끔 조이는 편. 403이 새로 발생하면 premium 이동 또는 대체 우회 필요
