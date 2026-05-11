# SEC EDGAR Direct API 가이드

## 개요

미국 상장기업 분석의 **1차 소스**. SEC EDGAR는 키 불필요·무제한 무료 공개 데이터로 한국 DART의 미국 등가물이다. 본 가이드는 직접 HTTP API 호출 패턴을 정리한다 (Python `urllib` + `BeautifulSoup`만 필요).

**핵심 가치:** 펀더멘탈 시계열·18개월 공시 전수·공시 본문 파싱·세그먼트 매출까지 모두 1차 소스에서 직접 추출. 가공된 2차 소스(FMP·yfinance fundamentals)보다 정확·완전하며 권한 차단 없음.

## 인증·헤더

키 발급 불필요. **User-Agent 헤더만 필수** (SEC 정책).

```python
UA = os.environ.get("EDGAR_IDENTITY", "Your-Project your.email@example.com")
import urllib.request
req = urllib.request.Request(url, headers={'User-Agent': UA})
```

User-Agent가 없거나 형식이 어긋나면 403 Forbidden. 형식: `"<용도> <연락처이메일>"`.

## 4개 핵심 엔드포인트

### 1. Submissions API — 회사별 공시 메타데이터

```
https://data.sec.gov/submissions/CIK{10자리CIK}.json
예: https://data.sec.gov/submissions/CIK0000320193.json  (Apple)
```

반환: 회사 프로필 + 최근 1,000건 공시 메타. 18개월 공시 분석의 출발점.

**핵심 필드 (`filings.recent` 안)**:
- `accessionNumber[]`: 공시 고유번호 (Archives URL 생성용)
- `filingDate[]`: 공시일 (YYYY-MM-DD)
- `reportDate[]`: 보고 기준일
- `form[]`: 공시 유형 (10-K, 10-Q, 8-K, DEF 14A, SC 13G 등)
- `items[]`: **8-K Item Code** (5.02, 2.02 등 — 공시 내용 분류 핵심)
- `primaryDocument[]`: 본문 HTML 파일명 (Archives URL 생성용)
- `primaryDocDescription[]`: 문서 설명

### 2. CompanyFacts API — XBRL 재무 시계열 (DART `fnlttSinglAcntAll` 등가)

```
https://data.sec.gov/api/xbrl/companyfacts/CIK{10자리CIK}.json
```

반환: 회사가 SEC에 제출한 모든 us-gaap 컨셉의 시계열 (보통 503개 컨셉, 분기 60개+).

**구조**:
```python
data['facts']['us-gaap']['Revenues']['units']['USD']  # 리스트, 각 항목은:
{
  'start': '2024-12-29',  # 기간 시작 (instant 컨셉은 없음)
  'end':   '2025-03-29',  # 기간 종료
  'val':   95359000000,
  'form':  '10-Q',
  'fy':    2025, 'fp': 'Q2',
  'filed': '2025-05-02',
  'frame': 'CY2025Q1',
  'accn':  '0000320193-25-000057',
}
```

**핵심 컨셉 (구루 분석 필수 12개)**:

| 라벨 | us-gaap 컨셉 후보 | 단위 | 종류 |
|---|---|---|---|
| 매출 | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet` | USD | duration |
| 매출총이익 | `GrossProfit` | USD | duration |
| 영업이익 | `OperatingIncomeLoss` | USD | duration |
| 당기순이익 | `NetIncomeLoss` | USD | duration |
| R&D | `ResearchAndDevelopmentExpense` | USD | duration |
| SG&A | `SellingGeneralAndAdministrativeExpense` | USD | duration |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | USD | duration |
| CapEx | `PaymentsToAcquirePropertyPlantAndEquipment` | USD | duration |
| 자사주매입 | `PaymentsForRepurchaseOfCommonStock` | USD | duration |
| 배당지급 | `PaymentsOfDividendsCommonStock`, `PaymentsOfDividends` | USD | duration |
| 현금·증권 | `CashAndCashEquivalentsAtCarryingValue` | USD | instant |
| 자기자본 | `StockholdersEquity` | USD | instant |
| 장기차입금 | `LongTermDebtNoncurrent` | USD | instant |
| EPS diluted | `EarningsPerShareDiluted` | USD/shares | duration |
| 가중평균 주식수 | `WeightedAverageNumberOfDilutedSharesOutstanding` | shares | duration |

**컨셉 후보가 여러 개**: 회사마다 사용하는 us-gaap 컨셉이 다름. 후보 리스트에서 첫 번째로 존재하는 것 선택. ASC 606 이후 대부분 `RevenueFromContractWithCustomerExcludingAssessedTax` 사용.

### 3. Archives URL — Filing 본문 다운로드

```
https://www.sec.gov/Archives/edgar/data/{CIK_숫자}/{accession_no_dashes}/{primary_doc}
```

**accession_no_dashes**: `0000320193-25-000057` → `000032019325000057` (대시 제거)

**예**:
```
https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm
```

이게 한국 DART `document.xml` API의 등가물. 차이: SEC는 ZIP 압축 없이 HTML 직접 제공.

### 4. Tickers API — 티커 → CIK 변환

```
https://www.sec.gov/files/company_tickers.json
```

반환: 모든 미국 상장사의 ticker / cik / title 매핑. 한 번 받아두고 캐시.

## 단분기 시계열 추출 — 누적값 → 단분기 역산

XBRL의 `fp='Q1'`, `'Q2'`, `'Q3'`은 **누적값** (한국 DART와 동일 함정). `'FY'`는 연간. `'Q4'`는 보통 없음.

**해결: `(end - start)` duration으로 단분기 직접 추출** — fp 라벨 무시.

```python
from datetime import datetime
from collections import defaultdict

def parse_d(s): return datetime.strptime(s, '%Y-%m-%d').date() if s else None

def get_3m_quarterly(facts, concept, unit='USD'):
    """80~100일 duration = 단분기. 같은 end 날짜에 중복 시 latest filed."""
    if concept not in facts or unit not in facts[concept]['units']:
        return []
    raw = facts[concept]['units'][unit]
    by_end = defaultdict(list)
    for r in raw:
        s = parse_d(r.get('start')); e = parse_d(r['end'])
        if not s: continue
        days = (e - s).days
        if 80 <= days <= 100:  # 한 분기
            by_end[e].append(r)
    out = []
    for e, recs in by_end.items():
        recs.sort(key=lambda x: x['filed'] or '', reverse=True)
        out.append(recs[0])
    out.sort(key=lambda x: x['end'])
    return out

def get_annual(facts, concept, unit='USD'):
    """350~380일 duration = 연간."""
    raw = facts[concept]['units'][unit]
    by_end = defaultdict(list)
    for r in raw:
        s = parse_d(r.get('start')); e = parse_d(r['end'])
        if not s: continue
        days = (e - s).days
        if 350 <= days <= 380:
            by_end[e].append(r)
    out = []
    for e, recs in by_end.items():
        recs.sort(key=lambda x: x['filed'] or '', reverse=True)
        out.append(recs[0])
    out.sort(key=lambda x: x['end'])
    return out

def get_instant(facts, concept, unit='USD'):
    """instant 컨셉 (BS 스냅샷). start 없는 항목."""
    raw = facts[concept]['units'][unit]
    by_end = defaultdict(list)
    for r in raw:
        if r.get('start'): continue
        e = parse_d(r['end'])
        by_end[e].append(r)
    out = []
    for e, recs in by_end.items():
        recs.sort(key=lambda x: x['filed'] or '', reverse=True)
        out.append(recs[0])
    out.sort(key=lambda x: x['end'])
    return out
```

**검증된 작동 패턴 (AAPL FY26 Q2 = 2026-03-28 종료, 단분기 매출 $111.2B)**: 위 함수로 정확 추출 확인.

## 18개월 공시 3-Tier 프로토콜 (한국 DART Step 2.7 등가)

미국 공시 분석 시 **반드시 18개월 전수 → 3-Tier 분류 → 본문 정독** 흐름 적용.

### Tier 1 (본문 정독 — 23건 내외 평균)

10-K (연간) · 10-Q (분기) · DEF 14A (주총·보수) · 8-K (중요사건) · SC 13G/D (5%+ 주요주주) · S-1/S-3 (등록·발행)

**8-K Item Code 우선순위 (정독 vs 스킵 결정)**:

| Item | 의미 | Tier | 비고 |
|---|---|---|---|
| **2.02** | Results of Operations | **★ 본문 정독** | 분기·연간 실적 발표 (보통 EX-99.1 첨부) |
| **5.02** | Departure/Election of Directors/Officers | **★ 본문 정독** | 임원·이사 변경 (가장 중요) |
| **5.07** | Submission of Matters to Vote | 정독 | 주총 표결 결과 |
| **8.01** | Other Events | 정독 | 자사주 매입 추가 승인 등 중요 발표 |
| **1.01** | Material Definitive Agreement | 정독 | 큰 계약·M&A |
| **2.01** | Completion of Acquisition | 정독 | M&A 완료 |
| **3.02** | Unregistered Sales of Equity | 정독 | 비상장 주식 발행 |
| **9.01** | Financial Statements and Exhibits | 보조 | 첨부서류만 — 다른 Item과 함께 등장 |
| **7.01** | Regulation FD Disclosure | 스킵 가능 | 일반 IR 메시지 |

### Tier 2 (집계만 — 평균 60~80건)

Form 4 (인사이더 거래) · Form 3 (신규 인사이더) · SD (specialized disclosure) — 건수 + 패턴만 추출.

### Tier 3 (스킵 — 평균 30~50건)

Form 144 (매도예정 신고) · 25-NSE (상장폐지 신고는 ETF만) · S-8 (ESOP 등록) 등 행정 공시.

### 분류 코드

```python
TIER1_FORMS = {'8-K', '10-K', '10-Q', 'DEF 14A', 'PRE 14A',
               'SC 13G', 'SC 13G/A', 'SC 13D', 'SC 13D/A',
               'S-1', 'S-3', 'S-4', '20-F', '6-K'}
TIER2_FORMS = {'4', '4/A', '3', '5', 'SD', 'CORRESP'}

def classify_tier(form):
    if form in TIER1_FORMS: return 1
    if form in TIER2_FORMS: return 2
    return 3
```

## Filing 본문 파싱 (DART `document.xml` 등가)

```python
import urllib.request, re
from bs4 import BeautifulSoup

UA = os.environ.get("EDGAR_IDENTITY", "Your-Project your.email@example.com")
CIK_NUM = "320193"  # leading zero 없는 숫자

def fetch_filing_body(accession, primary_doc):
    acc_clean = accession.replace('-', '')
    url = f"https://www.sec.gov/Archives/edgar/data/{CIK_NUM}/{acc_clean}/{primary_doc}"
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace'), url

def to_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script','style']): tag.decompose()
    txt = soup.get_text('\n', strip=True)
    return re.sub(r'\n{3,}', '\n\n', txt), soup
```

**활용 — 8-K Item 5.02 본문 추출 (임원 교체 사유·승계자 정보)**:
```python
text, _ = to_text(html)
m = re.search(r'Item\s*5\.02[^\n]*', text, re.IGNORECASE)
if m:
    body = text[m.start():m.start()+2000]  # 통상 5.02는 1~2KB
```

**활용 — 10-K 세그먼트 표 추출**:
```python
soup = BeautifulSoup(html, 'html.parser')
for tbl in soup.find_all('table'):
    t = tbl.get_text(' ', strip=True)
    if 'Greater China' in t and 'Americas' in t:
        # 지역별 매출 + OP 표
        rows = []
        for tr in tbl.find_all('tr'):
            cells = [td.get_text(' ', strip=True) for td in tr.find_all(['td','th'])]
            cells = [c for c in cells if c]
            if cells: rows.append(cells)
```

## 표준 워크플로우 (미국 종목 분석 시)

```python
# 1) 메타데이터 + 18개월 공시 목록
submissions = fetch_json(f"https://data.sec.gov/submissions/CIK{cik:0>10}.json")

# 2) 펀더멘탈 시계열 (분기·연간)
facts = fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:0>10}.json")['facts']['us-gaap']

# 3) 18개월 필터 + Tier 분류
recent = filter_18months(submissions['filings']['recent'])
tier1 = [r for r in recent if classify_tier(r['form']) == 1]

# 4) Tier 1 본문 다운로드 (parallel)
for r in tier1:
    html, url = fetch_filing_body(r['accession'], r['primaryDocument'])
    save(html)

# 5) 단분기 시계열 + 4국면 판정 + Skin in Game (Form 4 + 13G/D)
quarterly = get_3m_quarterly(facts, 'RevenueFromContractWithCustomerExcludingAssessedTax')
```

## 한국 ↔ 미국 등가 매핑

<table>
<thead><tr><th>한국 (DART)</th><th>미국 (SEC EDGAR)</th></tr></thead>
<tbody>
<tr><td>company.json (기업개황)</td><td>submissions API의 메타 (cik, name, sic, exchanges, tickers)</td></tr>
<tr><td>list.json (공시 목록)</td><td>submissions API의 filings.recent</td></tr>
<tr><td>fnlttSinglAcntAll.json (전체 재무)</td><td>companyfacts API (us-gaap 503개 컨셉)</td></tr>
<tr><td>document.xml (공시 본문)</td><td>Archives URL로 HTML 직접 다운로드</td></tr>
<tr><td>hyslrSttus.json (최대주주)</td><td>DEF 14A 본문 "Beneficial Ownership" 표 + SC 13G/D</td></tr>
<tr><td>majorstock.json (5%+ 대량보유)</td><td>SC 13G/D filings (form 코드)</td></tr>
<tr><td>elestock.json (임원 보유)</td><td>Form 4 (취득·처분) + Form 3 (신규 신고) + DEF 14A</td></tr>
<tr><td>분기 단분기 역산 (1Q=11013 등)</td><td>XBRL duration 80~100일 필터</td></tr>
<tr><td>3-Tier 18개월 공시 프로토콜</td><td>3-Tier 18개월 공시 프로토콜 (form + 8-K item code)</td></tr>
</tbody>
</table>

## 함정·주의

- **CIK 0-padding**: submissions/companyfacts URL은 10자리 0-padding (`CIK0000320193`), Archives URL은 leading zero 없는 숫자 (`/data/320193/...`)
- **회계연도 차이**: Apple FY는 9월말 종료. Microsoft FY는 6월말. 단분기 역산 시 회사 FY 기준으로 정렬
- **분기 컨센서스 미제공**: SEC는 발표된 실적만. 컨센서스(Wall Street estimate)는 별도 소스 (yfinance·Finnhub) 필요
- **Earnings call transcripts 미제공**: 회사 IR 사이트에서 PDF 직접 다운로드 또는 별도 유료 소스
- **Rate limit**: 권장 10 req/sec, 일일 limit 없음. User-Agent 명확히 하면 사실상 무제한
- **CompanyFacts 응답 크기**: 회사당 1~5MB. 한 번 받아 캐시
- **단위**: 모든 USD는 달러 (한국 DART는 원). 환산 불필요

## 부록 — edgartools MCP (대안)

`edgartools` Python 라이브러리에 MCP 서버가 내장돼 있어 Claude Code에서 직접 호출 가능. 다만:
- 별도 설치 필요 (`pip install edgartools[ai]`)
- MCP 서버 설정 필요
- 본 가이드의 직접 API 호출이 더 가볍고 안정적 (MCP 의존성 0)

설치 시 `~/Library/Application Support/Claude/claude_desktop_config.json`에 추가:
```json
{"mcpServers": {"edgartools": {"command": "uvx", "args": ["--from", "edgartools[ai]", "edgartools-mcp"], "env": {"EDGAR_IDENTITY": "Your Name your.email@example.com"}}}}
```

기본 권장은 **직접 API 호출** (본 가이드 메인 섹션). MCP는 옵션.
