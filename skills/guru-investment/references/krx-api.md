# KRX Open API 연동 가이드

## 개요
한국거래소(KRX)의 Open API를 활용하여 KOSPI/KOSDAQ 상장종목의 **시장 데이터**(주가, 시가총액, 거래량, 지수)를 조회한다. DART가 재무제표/공시를, KRX가 시세/시장 데이터를 담당하는 상호보완 구조다.

### DART vs KRX 역할 분담

| 데이터 | DART | KRX |
|--------|------|-----|
| 재무제표 (매출, 영업이익, BS, CF) | ✅ | ❌ |
| 공시 (유상증자, M&A, 지분변동) | ✅ | ❌ |
| 주가 (OHLCV, 등락률) | ❌ | ✅ |
| 시가총액 | ❌ | ✅ |
| 상장주식수 | ❌ | ✅ |
| 지수 시세 (KOSPI, KOSDAQ) | ❌ | ✅ |
| ETF 시세 (NAV, 괴리율) | ❌ | ✅ |
| PER/PBR | ❌ | ❌ (직접 계산) |
| 배당 | ✅ | ❌ |
| 기업개황 | ✅ | 일부 (기본정보) |

> **PER/PBR 계산**: KRX 주가 + DART EPS/BPS로 직접 산출한다.
> PER = TDD_CLSPRC / EPS, PBR = MKTCAP / 자본총계

## 인증

```
API_KEY = os.environ["KRX_API_KEY"]  # 발급: https://openapi.krx.co.kr/
BASE_URL = "https://data-dbg.krx.co.kr/svc/apis"
```

**인증 방식**: HTTP 헤더에 `AUTH_KEY` 포함
```python
headers = {"AUTH_KEY": API_KEY}
```

**일일 호출 제한**: 10,000건
**데이터 제공 기간**: 2010년 1월 이후

## 주요 엔드포인트

### 1. 유가증권(KOSPI) 일별매매정보
KOSPI 전 종목의 일별 시세, 거래량, 시가총액.
```
GET {BASE_URL}/sto/stk_bydd_trd?basDd={YYYYMMDD}
Headers: AUTH_KEY: {API_KEY}
```

**응답 필드 (`OutBlock_1[]`):**

| 필드 | 설명 | 예시 |
|------|------|------|
| BAS_DD | 기준일자 | "20260409" |
| ISU_CD | 종목코드 (6자리) | "005930" |
| ISU_NM | 종목명 | "삼성전자" |
| MKT_NM | 시장구분 | "KOSPI" |
| SECT_TP_NM | 소속부 | "" |
| TDD_CLSPRC | **종가** | "55000" |
| CMPPREVDD_PRC | 전일대비 | "-500" |
| FLUC_RT | **등락률(%)** | "-0.90" |
| TDD_OPNPRC | 시가 | "55500" |
| TDD_HGPRC | 고가 | "55700" |
| TDD_LWPRC | 저가 | "54800" |
| ACC_TRDVOL | **거래량** | "12345678" |
| ACC_TRDVAL | **거래대금** | "678901234567" |
| MKTCAP | **시가총액** | "328264942500000" |
| LIST_SHRS | **상장주식수** | "5969782550" |

> **주의**: 전 종목 일괄 반환. 특정 종목 필터링은 응답에서 ISU_CD로 직접 필터링.

### 2. 코스닥(KOSDAQ) 일별매매정보
```
GET {BASE_URL}/sto/ksq_bydd_trd?basDd={YYYYMMDD}
```
응답 필드 동일 (MKT_NM = "KOSDAQ", SECT_TP_NM에 "벤처기업부" 등 포함).

### 3. 유가증권 종목기본정보
종목의 ISIN, 영문명, 상장일, 액면가, 상장주식수 등 기본 정보.
```
GET {BASE_URL}/sto/stk_isu_base_info?basDd={YYYYMMDD}
```

**응답 필드 (`OutBlock_1[]`):**

| 필드 | 설명 | 예시 |
|------|------|------|
| ISU_CD | ISIN 코드 (12자리) | "KR7005930003" |
| ISU_SRT_CD | 단축코드 (6자리) | "005930" |
| ISU_NM | 종목명 (정식) | "삼성전자보통주" |
| ISU_ABBRV | 종목 약칭 | "삼성전자" |
| ISU_ENG_NM | 영문명 | "Samsung Electronics Co.,Ltd." |
| LIST_DD | 상장일 | "19750611" |
| MKT_TP_NM | 시장 | "KOSPI" |
| SECUGRP_NM | 증권그룹 | "주권" |
| KIND_STKCERT_TP_NM | 주식종류 | "보통주" |
| PARVAL | 액면가 | "100" |
| LIST_SHRS | 상장주식수 | "5969782550" |

### 4. 코스닥 종목기본정보
```
GET {BASE_URL}/sto/ksq_isu_base_info?basDd={YYYYMMDD}
```

### 5. KOSPI 지수 일별시세
```
GET {BASE_URL}/idx/kospi_dd_trd?basDd={YYYYMMDD}
```

**응답 필드 (`OutBlock_1[]`):**

| 필드 | 설명 | 예시 |
|------|------|------|
| BAS_DD | 기준일자 | "20260409" |
| IDX_CLSS | 지수 분류 | "KOSPI" |
| IDX_NM | 지수명 | "코스피" |
| CLSPRC_IDX | **종가 지수** | "2650.32" |
| CMPPREVDD_IDX | 전일대비 | "-15.28" |
| FLUC_RT | 등락률(%) | "-0.57" |
| OPNPRC_IDX | 시가 지수 | "2665.60" |
| HGPRC_IDX | 고가 지수 | "2668.10" |
| LWPRC_IDX | 저가 지수 | "2642.15" |
| ACC_TRDVOL | 거래량 | "1026732958" |
| ACC_TRDVAL | 거래대금 | "33473404312827" |
| MKTCAP | 시장 전체 시가총액 | "4759726731566801" |

### 6. KOSDAQ 지수 일별시세
```
GET {BASE_URL}/idx/kosdaq_dd_trd?basDd={YYYYMMDD}
```

### 7. KRX 시리즈 지수 일별시세
```
GET {BASE_URL}/idx/krx_dd_trd?basDd={YYYYMMDD}
```

### 8. ETF 일별매매정보
```
GET {BASE_URL}/etp/etf_bydd_trd?basDd={YYYYMMDD}
```

**응답 필드 (`OutBlock_1[]`):**

| 필드 | 설명 | 예시 |
|------|------|------|
| BAS_DD | 기준일자 | "20260409" |
| ISU_CD | 종목코드 | "069500" |
| ISU_NM | 종목명 | "KODEX 200" |
| TDD_CLSPRC | 종가 | "28145" |
| CMPPREVDD_PRC | 전일대비 | "-535" |
| FLUC_RT | 등락률(%) | "-1.87" |
| NAV | **순자산가치** | "28180.63" |
| TDD_OPNPRC | 시가 | "28475" |
| TDD_HGPRC | 고가 | "28600" |
| TDD_LWPRC | 저가 | "28055" |
| ACC_TRDVOL | 거래량 | "108127" |
| ACC_TRDVAL | 거래대금 | "3056549147" |
| MKTCAP | 시가총액 | "299744250000" |
| INVSTASST_NETASST_TOTAMT | **순자산총액** | "300123679797" |
| LIST_SHRS | 상장좌수 | "10650000" |
| IDX_IND_NM | 기초지수명 | "코스피 200" |
| OBJ_STKPRC_IDX | 기초지수 종가 | "865.75" |
| CMPPREVDD_IDX | 기초지수 전일대비 | "-17.06" |
| FLUC_RT_IDX | 기초지수 등락률(%) | "-1.93" |

> **괴리율 계산**: (TDD_CLSPRC - NAV) / NAV × 100

### 9. ETN 일별매매정보
```
GET {BASE_URL}/etp/etn_bydd_trd?basDd={YYYYMMDD}
```

### 10. 채권지수 시세정보
```
GET {BASE_URL}/idx/bon_dd_trd?basDd={YYYYMMDD}
```

### 11. 파생상품지수 시세정보
```
GET {BASE_URL}/idx/der_dd_trd?basDd={YYYYMMDD}
```

## Python 헬퍼 함수

```python
import requests

API_KEY = os.environ["KRX_API_KEY"]  # 발급: https://openapi.krx.co.kr/
BASE_URL = "https://data-dbg.krx.co.kr/svc/apis"
HEADERS = {"AUTH_KEY": API_KEY}

def krx_get(endpoint, basDd):
    """KRX API 호출 공통 함수."""
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, params={"basDd": basDd}, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("OutBlock_1", [])

def get_stock_price(stock_code, basDd, market="KOSPI"):
    """특정 종목의 일별 시세 조회."""
    endpoint = "sto/stk_bydd_trd" if market == "KOSPI" else "sto/ksq_bydd_trd"
    data = krx_get(endpoint, basDd)
    for item in data:
        if item["ISU_CD"] == stock_code:
            return {
                "종가": int(item["TDD_CLSPRC"]),
                "등락률": float(item["FLUC_RT"]),
                "거래량": int(item["ACC_TRDVOL"]),
                "거래대금": int(item["ACC_TRDVAL"]),
                "시가총액": int(item["MKTCAP"]),
                "상장주식수": int(item["LIST_SHRS"]),
            }
    return None

def get_market_summary(basDd, market="KOSPI"):
    """시장 전체 요약 (지수, 시총, 거래대금)."""
    endpoint = "idx/kospi_dd_trd" if market == "KOSPI" else "idx/kosdaq_dd_trd"
    data = krx_get(endpoint, basDd)
    # 첫 번째 항목이 대표 지수
    if data:
        idx = data[0]
        return {
            "지수명": idx["IDX_NM"],
            "종가": idx.get("CLSPRC_IDX", ""),
            "등락률": idx.get("FLUC_RT", ""),
            "거래대금": int(idx["ACC_TRDVAL"]),
            "시장시총": int(idx["MKTCAP"]),
        }
    return None

def get_etf_data(etf_code, basDd):
    """ETF 시세 및 NAV 조회."""
    data = krx_get("etp/etf_bydd_trd", basDd)
    for item in data:
        if item["ISU_CD"] == etf_code:
            nav = float(item["NAV"])
            price = int(item["TDD_CLSPRC"])
            return {
                "종가": price,
                "NAV": nav,
                "괴리율": round((price - nav) / nav * 100, 2),
                "거래량": int(item["ACC_TRDVOL"]),
                "시가총액": int(item["MKTCAP"]),
                "순자산총액": int(item["INVSTASST_NETASST_TOTAMT"]),
                "기초지수": item["IDX_IND_NM"],
            }
    return None

def calc_per_pbr(stock_code, basDd, eps, bps, market="KOSPI"):
    """KRX 주가 + DART EPS/BPS로 PER/PBR 계산."""
    price_data = get_stock_price(stock_code, basDd, market)
    if not price_data or not eps or not bps:
        return None
    price = price_data["종가"]
    return {
        "주가": price,
        "시가총액": price_data["시가총액"],
        "PER": round(price / eps, 2) if eps > 0 else None,
        "PBR": round(price / bps, 2) if bps > 0 else None,
    }

def get_price_history(stock_code, dates, market="KOSPI"):
    """여러 날짜의 주가를 조회하여 추세 파악.
    dates: ["20260101", "20260201", ...] 형태의 리스트.
    주의: 날짜당 1회 API 호출 → 호출 횟수 관리 필요.
    """
    history = []
    endpoint = "sto/stk_bydd_trd" if market == "KOSPI" else "sto/ksq_bydd_trd"
    for d in dates:
        data = krx_get(endpoint, d)
        for item in data:
            if item["ISU_CD"] == stock_code:
                history.append({
                    "날짜": d,
                    "종가": int(item["TDD_CLSPRC"]),
                    "거래량": int(item["ACC_TRDVOL"]),
                    "시가총액": int(item["MKTCAP"]),
                })
                break
    return history
```

## 구루별 KRX 데이터 활용

| 구루 | KRX에서 가져올 것 | 용도 |
|------|-----------------|------|
| **Buffett** | 시가총액, 주가 | Owner Earnings Yield = Owner Earnings / MKTCAP, 안전마진 계산 |
| **Greenblatt** | 시가총액, 주가 | Earnings Yield = EBIT / EV (EV = MKTCAP + 순차입금) |
| **Lynch** | 주가, 시가총액 | PEG = (주가/EPS) / EPS성장률 |
| **O'Neil/Minervini** | 주가 히스토리, 거래량 | 52주 신고가 근접도, 거래량 패턴, Stage 분석 |
| **Marks** | 시가총액, 지수 | 밸류에이션 수준 판단, 시장 센티먼트 |
| **Dalio** | 지수, ETF NAV, 거래대금 | 매크로 사이클, 시장 유동성 |
| **Soros** | 주가 추세, 거래량 급등 | 반사성 피드백 루프 탐지 |
| **Druckenmiller** | 주가, 시가총액, 지수 | 탑다운 매크로 + 바텀업 타이밍 |

## 호출 최적화

### 문제: 전 종목 일괄 반환
KRX API는 종목 필터 파라미터가 없어 전 종목 데이터를 반환한다 (KOSPI ~950개, KOSDAQ ~1,700개). 특정 종목만 필요할 때도 전체를 받아야 한다.

### 최적화 전략
1. **캐싱**: 같은 날짜의 같은 엔드포인트는 1회만 호출하고 결과를 메모리에 캐싱
2. **배치 처리**: 여러 종목을 비교할 때는 1회 호출로 전체 받아서 필터링
3. **날짜 최소화**: 주가 히스토리는 월말/분기말 등 핵심 날짜만 조회 (일별 호출 X)
4. **우선순위**: 최신 시세 1회 → DART 재무 → 필요시 과거 시세 추가

### 일일 호출 예산 배분 (10,000건 한도)
| 용도 | 예상 호출 수 |
|------|------------|
| 분석 대상 종목 최신 시세 | 1~2건 |
| 지수 시세 (KOSPI + KOSDAQ) | 2건 |
| **일봉 250영업일** (1년 — MA/VCP/거래량/Stage 분석) | **250건** |
| 주봉 보완 (필요시) | ~20건 |
| ETF 시세 (필요시) | 1건 |
| **소계** | ~280건/분석 |

→ 하루 35건 분석 가능, 여유 충분.

## 주의사항

1. **HTTPS 필수**: `http://`로 요청하면 302 리다이렉트 → `https://` 사용
2. **영업일만 데이터 있음**: 주말/공휴일 날짜로 조회하면 빈 배열 반환 → 직전 영업일 사용
3. **값이 문자열**: 모든 숫자 값이 string으로 반환됨 → `int()` / `float()` 변환 필요
4. **종목코드 차이**: KRX는 6자리 단축코드(ISU_CD), DART는 8자리 고유번호(corp_code). 매핑 필요.
5. **지수 빈값**: 일부 지수에서 CLSPRC_IDX 등이 빈 문자열로 올 수 있음 (장 마감 전 or 특수 지수)
6. **상용 이용 제한**: KRX Open API 결과는 영리 목적으로 직접 사용 불가 (분석 참고용)
