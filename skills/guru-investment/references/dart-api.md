# DART OpenAPI 연동 가이드

## 개요
금융감독원 전자공시시스템(DART)의 OpenAPI를 활용하여 한국 상장기업의 재무제표, 기업개황, 지분공시, 주요사항 등을 조회한다. 구루 분석 시 한국 주식의 정량 데이터를 실시간으로 확보하는 데 사용한다.

## 인증
```
import os
API_KEY = os.environ["DART_API_KEY"]  # 발급: https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do
BASE_URL = "https://opendart.fss.or.kr/api"
```

## 주요 엔드포인트

### 1. 기업개황 (Company Overview)
대표자명, 업종, 자본금, 상장일 등 기본 정보.
```
GET {BASE_URL}/company.json?crtfc_key={API_KEY}&corp_code={corp_code}
```
- `corp_code`: 고유번호 8자리 (종목코드와 다름)

### 2. 공시검색 (Disclosure Search)
특정 기업 또는 전체 시장의 공시 목록 조회.
```
GET {BASE_URL}/list.json?crtfc_key={API_KEY}&corp_code={corp_code}&bgn_de={시작일}&end_de={종료일}&pblntf_ty={공시유형}
```
- `pblntf_ty`: A=정기공시, B=주요사항보고, C=발행공시, D=지분공시, E=기타공시, F=외부감사관련, G=펀드공시, H=자산유동화, I=거래소공시, J=공정위공시

### 3. 단일회사 주요계정 (Key Financial Accounts)
매출액, 영업이익, 당기순이익, 자산총계, 부채총계, 자본총계 등 핵심 재무 데이터.
```
GET {BASE_URL}/fnltt_singl_acnt.json?crtfc_key={API_KEY}&corp_code={corp_code}&bsns_year={사업연도}&reprt_code={보고서코드}
```
- `reprt_code`: 11013=1분기, 11012=반기, 11014=3분기, 11011=사업보고서
- 최근 3년치 데이터 반환

### 4. 단일회사 전체 재무제표 (Full Financial Statements)
재무상태표, 손익계산서, 현금흐름표의 전체 계정과목.
```
GET {BASE_URL}/fnltt_singl_acnt_all.json?crtfc_key={API_KEY}&corp_code={corp_code}&bsns_year={사업연도}&reprt_code={보고서코드}&fs_div={재무제표구분}
```
- `fs_div`: OFS=개별재무제표, CFS=연결재무제표

### 5. 다중회사 주요계정 (Multi-Company Comparison)
여러 회사의 주요 재무 데이터를 한번에 비교.
```
GET {BASE_URL}/fnltt_multi_acnt.json?crtfc_key={API_KEY}&corp_code={corp_code1,corp_code2,...}&bsns_year={사업연도}&reprt_code={보고서코드}
```

### 6. 배당에 관한 사항 (Dividend Info)
```
GET {BASE_URL}/alot.json?crtfc_key={API_KEY}&corp_code={corp_code}&bsns_year={사업연도}&reprt_code={보고서코드}
```

### 7. 최대주주 현황 (Largest Shareholders)
```
GET {BASE_URL}/hyslr.json?crtfc_key={API_KEY}&corp_code={corp_code}&bsns_year={사업연도}&reprt_code={보고서코드}
```

### 8. 자기주식 취득/처분 현황 (Treasury Stock)
```
GET {BASE_URL}/tesstkacqsdsp.json?crtfc_key={API_KEY}&corp_code={corp_code}&bsns_year={사업연도}&reprt_code={보고서코드}
```

### 9. 임원 현황 (Executive Info)
```
GET {BASE_URL}/exctvSttus.json?crtfc_key={API_KEY}&corp_code={corp_code}&bsns_year={사업연도}&reprt_code={보고서코드}
```

### 10. 대량보유 상황보고 (Major Shareholders Report)
```
GET {BASE_URL}/majorstock.json?crtfc_key={API_KEY}&corp_code={corp_code}
```

### 11. 임원/주요주주 소유보고 (Executive/Major Shareholder Ownership)
```
GET {BASE_URL}/elestock.json?crtfc_key={API_KEY}&corp_code={corp_code}
```

### 12. 공시서류 원문 다운로드 (Document Full Text)
공시 본문을 ZIP(XML) 형태로 다운로드. 18개월 공시 분석(Step 2.7) Tier 1/2에서 본문을 읽을 때 사용.
```
GET {BASE_URL}/document.xml?crtfc_key={API_KEY}&rcept_no={접수번호}
```
- `rcept_no`: `list.json`에서 얻은 접수번호 (14자리)
- **응답**: ZIP 파일 → 내부에 `{rcept_no}.xml` (HTML-like XML)
- **파싱**: BeautifulSoup으로 텍스트 추출

```python
import requests, zipfile, io
from bs4 import BeautifulSoup

def read_disclosure(rcept_no):
    """공시 원문 텍스트 추출."""
    url = f"{BASE_URL}/document.xml"
    resp = requests.get(url, params={"crtfc_key": API_KEY, "rcept_no": rcept_no})
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        xml_name = z.namelist()[0]
        with z.open(xml_name) as f:
            soup = BeautifulSoup(f, "html.parser")
    return soup.get_text(separator="\n", strip=True)
```

> **기존 curl 2단계 크롤링(dsaf001 → viewer.do) 대신 이 API를 우선 사용한다.** 공식 API이므로 안정적이고 rate limit 내에서 자유롭게 호출 가능.

---

## 고유번호(corp_code) 조회

종목코드(6자리, 예: 005930)와 고유번호(8자리, 예: 00126380)는 다르다. 고유번호를 모를 때는 기업코드 목록(ZIP)을 다운로드해서 매핑하거나, OpenDartReader 라이브러리를 사용한다.

**고유번호 목록 다운로드:**
```
GET https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={API_KEY}
```
→ ZIP 파일로 반환, 내부에 CORPCODE.xml 포함

**주요 기업 고유번호 (자주 쓰는 것):**
| 기업명 | 종목코드 | 고유번호(corp_code) |
|--------|----------|-------------------|
| 삼성전자 | 005930 | 00126380 |
| SK하이닉스 | 000660 | 00164779 |
| 현대자동차 | 005380 | 00164742 |
| 카카오 | 035720 | 00258801 |
| 네이버 | 035420 | 00266961 |
| LG에너지솔루션 | 373220 | 01444707 |
| 삼성바이오로직스 | 207940 | 00759735 |
| 기아 | 000270 | 00106644 |
| 셀트리온 | 068270 | 00421045 |
| POSCO홀딩스 | 005490 | 00126186 |
| KB금융 | 105560 | 00434456 |
| 한화솔루션 | 009830 | 00143043 |

## 구루별 DART 활용 매핑

| 구루 | 주로 조회할 DART 데이터 |
|------|----------------------|
| **버핏** | 전체 재무제표(ROE, 부채비율, Owner Earnings 계산), 자기주식 현황, 배당 |
| **그린블라트** | 주요계정(EBIT, 자산, 부채 → ROIC & EY 계산), 다중회사 비교 |
| **린치** | 주요계정(EPS 성장률, 매출 성장률 → PEG 계산), 임원 소유보고 |
| **오닐/미너비니** | 주요계정(분기별 EPS 가속, 매출 가속, ROE), 대량보유 변동 |
| **막스** | 기업개황(업종, 규모), 공시검색(구조조정, 특수상황 공시) |
| **달리오** | 다중회사 비교(섹터별 재무 비교), 배당 현황 |
| **소로스** | 공시검색(주요사항보고 — 유상증자, CB, BW 등 자본구조 변화) |
| **드러켄밀러** | 주요계정(실적 추세), 대량보유(외국인 동향) |
| **아셴브레너** | 전체 재무제표(capex 추세, 매출 성장), 기업개황(업종 확인) |

## Python 활용 예시

```python
import requests

import os
API_KEY = os.environ["DART_API_KEY"]  # 발급: https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do
BASE = "https://opendart.fss.or.kr/api"

def get_financials(corp_code, year, report="11011"):
    """단일회사 주요계정 조회"""
    url = f"{BASE}/fnltt_singl_acnt.json"
    params = {
        "crtfc_key": API_KEY,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": report
    }
    r = requests.get(url, params=params)
    data = r.json()
    if data["status"] == "000":
        return data["list"]
    return None

def get_full_financials(corp_code, year, report="11011", fs_div="CFS"):
    """단일회사 전체 재무제표 (연결)"""
    url = f"{BASE}/fnltt_singl_acnt_all.json"
    params = {
        "crtfc_key": API_KEY,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": report,
        "fs_div": fs_div
    }
    r = requests.get(url, params=params)
    data = r.json()
    if data["status"] == "000":
        return data["list"]
    return None

def get_company_info(corp_code):
    """기업개황 조회"""
    url = f"{BASE}/company.json"
    params = {"crtfc_key": API_KEY, "corp_code": corp_code}
    r = requests.get(url, params=params)
    return r.json()

def get_dividends(corp_code, year, report="11011"):
    """배당에 관한 사항"""
    url = f"{BASE}/alot.json"
    params = {
        "crtfc_key": API_KEY,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": report
    }
    r = requests.get(url, params=params)
    data = r.json()
    if data["status"] == "000":
        return data["list"]
    return None

def get_major_shareholders(corp_code):
    """대량보유 상황보고"""
    url = f"{BASE}/majorstock.json"
    params = {"crtfc_key": API_KEY, "corp_code": corp_code}
    r = requests.get(url, params=params)
    data = r.json()
    if data["status"] == "000":
        return data["list"]
    return None

def search_disclosures(corp_code=None, start=None, end=None, pblntf_ty=None):
    """공시검색"""
    url = f"{BASE}/list.json"
    params = {"crtfc_key": API_KEY}
    if corp_code: params["corp_code"] = corp_code
    if start: params["bgn_de"] = start
    if end: params["end_de"] = end
    if pblntf_ty: params["pblntf_ty"] = pblntf_ty
    r = requests.get(url, params=params)
    data = r.json()
    if data["status"] == "000":
        return data["list"]
    return None
```

## 응답 상태 코드
| 코드 | 의미 |
|------|------|
| 000 | 정상 |
| 010 | 등록되지 않은 키 |
| 011 | 사용할 수 없는 키 |
| 012 | 접근할 수 없는 IP |
| 013 | 조회된 데이터가 없음 |
| 020 | 요청 제한 초과 |
| 100 | 필드의 부적절한 값 |
| 800 | 시스템 점검 중 |

## 사용 시 주의사항
- 일일 요청 한도: 개인 10,000건
- corp_code(고유번호 8자리)와 stock_code(종목코드 6자리)를 혼동하지 말 것
- 연결재무제표(CFS)를 우선 사용하고, 없으면 개별재무제표(OFS)로 폴백
- 최신 사업보고서는 보통 3월 말(12월 결산 법인 기준)에 제출됨
- 분기보고서로 최신 실적 확인 시 reprt_code 주의 (11013=1Q, 11012=2Q, 11014=3Q)
