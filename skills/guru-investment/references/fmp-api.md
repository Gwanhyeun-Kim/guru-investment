# FMP (Financial Modeling Prep) API 가이드 — **DEPRECATED (사용 금지)**

> ⚠️ **2026-05-09 deprecated**. 미장 분석에서 FMP를 더 이상 사용하지 않는다. 대체 스택 사용:
> - **펀더멘탈 시계열** → `references/us-edgar-api.md` (SEC XBRL companyfacts API)
> - **시장 데이터·기관·인사이더·analyst TP** → `references/us-prices-api.md` (yfinance)
> - **분기 컨센서스 EPS·earnings calendar** → `references/finnhub.md` (Finnhub free)
> - **매크로 (Fed·CPI·yield)** → `references/us-macro-fred.md` (FRED)
>
> ## Deprecation 사유 (AAPL 분석 검증)
> 1. **`/api/v3/` 경로 deprecated** → `/stable/`로 마이그레이션 필요
> 2. **무료 티어 limit cap = 4** (분기 12개 시계열 못 받음). SEC XBRL은 분기 60+ 무료
> 3. **premium 차단**: key-metrics, ratios, transcripts, institutional-ownership, 분기 컨센
> 4. **2차 가공 데이터** — SEC가 1차 소스이므로 굳이 거칠 이유 없음
> 5. **유료 starter $14/mo도 SEC XBRL 깊이 못 따라옴**
>
> 본 파일은 과거 분석 reproducibility를 위해 보존한다. 새 분석에서는 절대 사용 금지.

---

## (이하 historical reference, 사용 금지)

## 개요

FMP API는 미국/글로벌 상장사의 재무제표, 밸류에이션, 기술적 지표, 애널리스트 추정치 등을 제공하는 금융 데이터 API다. guru-investment 분석 시 WebSearch/Playwright 대신 FMP API로 구조화된 데이터를 직접 조회한다.

- **Base URL:** `https://financialmodelingprep.com`
- **인증:** 모든 요청에 `?apikey=YOUR_API_KEY` 추가
- **무료 플랜:** 일 250회 호출, 5년 히스토리
- **응답 형식:** JSON (일부 CSV 지원)

## API Key

환경변수 `FMP_API_KEY`로 관리. WebFetch 호출 시 URL에 apikey 파라미터 포함.

---

## 핵심 엔드포인트

### 1. Company Profile (기업 개요)
```
GET /api/v3/profile/{symbol}
```
**반환:** 기업명, 섹터, 시가총액, 직원수, CEO, 설명, 52주 범위 등
**구루 용도:** Lynch 카테고리 분류, Buffett 사업 이해

**예시:**
```
https://financialmodelingprep.com/api/v3/profile/MU?apikey=YOUR_KEY
```

---

### 2. Income Statement (손익계산서)
```
GET /api/v3/income-statement/{symbol}?period=quarter&limit=20
```
**반환:** 매출, 매출원가, 매출총이익, 영업이익, 순이익, EPS 등
**파라미터:**
- `period`: `annual` (기본) 또는 `quarter`
- `limit`: 반환할 기간 수 (기본 10)

**구루 용도:**
- Minervini: EPS 가속 패턴 ("Code 33")
- O'Neil: C (Current EPS), A (Annual EPS)
- Lynch: 사이클 이익 추이
- Greenblatt: EBIT 계산

---

### 3. Balance Sheet (대차대조표)
```
GET /api/v3/balance-sheet-statement/{symbol}?period=quarter&limit=20
```
**반환:** 총자산, 총부채, 자기자본, 현금, 재고, 유동자산/부채 등

**구루 용도:**
- Lynch: 부채비율, 순현금 포지션
- Greenblatt: Invested Capital (NWC + Net Fixed Assets)
- Buffett: 재무건전성

---

### 4. Cash Flow Statement (현금흐름표)
```
GET /api/v3/cash-flow-statement/{symbol}?period=quarter&limit=20
```
**반환:** 영업활동CF, 투자활동CF(CapEx), 재무활동CF, FCF 등

**구루 용도:**
- Buffett: Owner Earnings
- Lynch: FCF 확인
- Greenblatt: CapEx 분석

---

### 5. Financial Ratios (재무비율)
```
GET /api/v3/ratios/{symbol}?period=quarter&limit=20
```
**반환:** P/E, P/B, P/S, ROE, ROA, ROIC, Debt/Equity, Current Ratio, Gross Margin, Operating Margin, Net Margin, PEG 등 50+ 비율

**구루 용도:**
- Greenblatt: ROIC, Earnings Yield
- Lynch: PEG, PEGY
- O'Neil: ROE (A 기준 17%+)
- Marks: 밸류에이션 수준 판단

---

### 6. Key Metrics (핵심 지표)
```
GET /api/v3/key-metrics/{symbol}?period=quarter&limit=20
```
**반환:** EV/EBITDA, EV/Revenue, Revenue Per Share, Net Income Per Share, Book Value Per Share, FCF Per Share, Dividends Per Share 등

**구루 용도:**
- Greenblatt: EV 기반 밸류에이션
- Dalio: 부채/수익 비율

---

### 7. Stock Quote (실시간 시세)
```
GET /api/v3/quote/{symbol}
```
**반환:** 현재가, 변동률, 시가총액, 거래량, 52주 고저, 50일/200일 MA, EPS, P/E 등

**구루 용도:**
- Minervini: 트렌드 템플릿 (가격 vs MA)
- O'Neil: 리더/래거드 판단

---

### 8. Historical Price (과거 주가)
```
GET /api/v3/historical-price-full/{symbol}?from=2025-01-01&to=2026-03-22
```
**반환:** 일별 시가, 고가, 저가, 종가, 거래량, 변동률

**구루 용도:**
- Minervini: VCP 패턴 분석, 거래량 시그니처
- O'Neil: 차트 패턴, 브레이크아웃 확인

---

### 9. Analyst Estimates (애널리스트 추정치)
```
GET /api/v3/analyst-estimates/{symbol}?period=quarter&limit=10
```
**반환:** 분기/연간 EPS 추정치 (평균, 고, 저), 매출 추정치

**구루 용도:**
- O'Neil: 어닝 서프라이즈 확인
- Marks: 컨센서스 vs 실제 괴리

---

### 10. Analyst Price Target (목표가)
```
GET /api/v4/price-target?symbol={symbol}
```
**반환:** 애널리스트별 목표가, 투자의견, 날짜

---

### 11. Insider Trading (내부자 거래)
```
GET /api/v4/insider-trading?symbol={symbol}&limit=50
```
**반환:** 거래일, 거래자, 직위, 매수/매도, 수량, 가격

**구루 용도:**
- Lynch: 내부자 매수 = 강한 신호
- O'Neil: I (Institutional Sponsorship) 보완

---

### 12. Institutional Holders (기관 보유)
```
GET /api/v3/institutional-holder/{symbol}
```
**반환:** 기관명, 보유수량, 변동, 보유비율

**구루 용도:**
- O'Neil: I (Institutional Sponsorship)
- Lynch: 기관 보유율 낮으면 undiscovered

---

### 13. Stock Screener (종목 스크리너)
```
GET /api/v3/stock-screener?marketCapMoreThan=1000000000&sector=Technology&limit=100
```
**파라미터:** marketCap, price, volume, beta, sector, country, isActivelyTrading 등

**구루 용도:**
- Greenblatt: Magic Formula 스크리닝
- Minervini: 트렌드 템플릿 스크리닝

---

### 14. Company Peers (동종 기업)
```
GET /api/v4/stock_peers?symbol={symbol}
```
**반환:** 동종 업계 티커 리스트

**구루 용도:** 피어 비교 분석의 출발점

---

### 15. Enterprise Value (기업가치)
```
GET /api/v3/enterprise-values/{symbol}?period=quarter&limit=20
```
**반환:** Market Cap, +Debt, -Cash, Enterprise Value, 주식수

**구루 용도:**
- Greenblatt: Earnings Yield = EBIT / EV

---

## 구루별 필수 API 호출 매핑

| 구루 | 필수 엔드포인트 | 핵심 데이터 |
|------|---------------|-----------|
| **Lynch** | profile, ratios, income-statement, balance-sheet | PEG, D/E, GM 추이, EPS 사이클 |
| **Greenblatt** | ratios (ROIC), enterprise-values, income-statement | ROIC, Earnings Yield, 정규화 이익 |
| **Minervini** | quote (MA), historical-price, income-statement | 50/200일 MA, VCP, EPS 가속 |
| **O'Neil** | income-statement, ratios, quote, institutional-holder | EPS 가속, ROE, RS, 기관 보유 |
| **Buffett** | profile, ratios, cash-flow, income-statement | Moat, Owner Earnings, GM 안정성 |
| **Marks** | ratios, enterprise-values, key-metrics | 밸류에이션 수준, 리스크 프리미엄 |
| **Dalio** | balance-sheet, key-metrics, ratios | 부채 사이클, D/E, 금리 민감도 |
| **Druckenmiller** | quote, analyst-estimates, historical-price | 모멘텀, 유동성, 컨센서스 |
| **Aschenbrenner** | profile, income-statement, cash-flow | CapEx, 매출 성장, AI 노출 |

---

## 호출 패턴 (WebFetch 사용)

guru-investment 분석 시 FMP API를 WebFetch로 호출한다:

```
WebFetch:
  url: https://financialmodelingprep.com/api/v3/ratios/MU?period=quarter&limit=12&apikey=YOUR_KEY
  prompt: "Extract all financial ratios for Micron for the last 12 quarters. Return ROE, ROIC, P/E, P/B, PEG, Debt/Equity, Gross Margin, Operating Margin, Net Margin in a table format."
```

### 표준 분석 호출 세트 (미국 주식)

1단계 - 기업 개요:
```
/api/v3/profile/{symbol}
```

2단계 - 재무제표 (분기 12개):
```
/api/v3/income-statement/{symbol}?period=quarter&limit=12
/api/v3/balance-sheet-statement/{symbol}?period=quarter&limit=12
/api/v3/cash-flow-statement/{symbol}?period=quarter&limit=12
```

3단계 - 비율 & 지표:
```
/api/v3/ratios/{symbol}?period=quarter&limit=12
/api/v3/key-metrics/{symbol}?period=quarter&limit=12
/api/v3/enterprise-values/{symbol}?period=quarter&limit=12
```

4단계 - 시장 데이터:
```
/api/v3/quote/{symbol}
/api/v3/analyst-estimates/{symbol}?period=quarter&limit=8
```

5단계 - 소유 구조:
```
/api/v4/insider-trading?symbol={symbol}&limit=30
/api/v3/institutional-holder/{symbol}
```

---

## 무료 플랜 제한 사항

- **일 250회 호출** — 표준 분석 세트가 ~11회이므로, 하루 ~20개 종목 분석 가능
- **5년 히스토리** — 장기 사이클 분석에는 부족할 수 있음 (유료 플랜은 30년)
- **실시간 데이터 15분 지연** — 실시간 트레이딩에는 부적합, 리서치에는 충분

---

## 참고

- FMP 공식 문서: https://site.financialmodelingprep.com/developer/docs
- FMP MCP 서버 (오픈소스): https://github.com/cdtait/fmp-mcp-server
- API 키 발급: https://site.financialmodelingprep.com/register
