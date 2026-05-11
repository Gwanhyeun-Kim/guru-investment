"""
DART fundamentals one-stop bundle fetcher for a Korean stock.

Fetches 8+ endpoints in sequence:
  1. company       — overview (업종, 대표자, 설립일)
  2. annual        — 3-year 주요계정 (most recent fiscal year's reprt_code=11011)
  3. quarterly     — 12 quarters across latest 3 fiscal years × reprt_codes (11013/11012/11014/11011)
  4. full_fs       — 전체 재무제표 CFS (most recent year)
  5. dividend      — 배당에 관한 사항
  6. major_shareholders — 최대주주 현황
  7. disclosures   — 최근 18개월 공시 목록
  8. bulk_holdings — 대량보유 변동

Usage:
    python fetch_dart_bundle.py <corp_code_8digit_or_stock_code_6digit> [output_dir]
    python fetch_dart_bundle.py 00159023
    python fetch_dart_bundle.py 005930 ~/Desktop/research/samsung/dart

Requires environment variable DART_API_KEY (register free at
https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do).

If 6-digit stock_code is provided, auto-resolves corp_code from DART corpCode.xml.
"""
from __future__ import annotations
import requests, json, time, zipfile, io, re, sys, os, warnings
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

API_KEY = os.environ.get("DART_API_KEY", "")
if not API_KEY:
    sys.exit("ERROR: Set DART_API_KEY env var. Register at https://opendart.fss.or.kr/")
BASE = "https://opendart.fss.or.kr/api"


def _get(endpoint: str, **params) -> dict:
    """Generic DART GET with API key."""
    params = {"crtfc_key": API_KEY, **params}
    r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def resolve_corp_code(code: str) -> str:
    """If `code` is 8-digit, return as-is. If 6-digit stock code, resolve via corpCode.xml."""
    if len(code) == 8 and code.isdigit():
        return code
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"invalid code: {code} (expected 6-digit stock or 8-digit corp)")
    print(f"Resolving corp_code for stock {code}...")
    r = requests.get(f"{BASE}/corpCode.xml", params={"crtfc_key": API_KEY}, timeout=60)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open(z.namelist()[0]) as f:
            data = f.read().decode("utf-8")
    match = re.search(rf"<list>[^<]*<corp_code>(\d{{8}})</corp_code>[^<]*<corp_name>([^<]+)</corp_name>[^<]*<corp_eng_name>[^<]*</corp_eng_name>[^<]*<stock_code>{code}</stock_code>", data)
    if not match:
        raise ValueError(f"stock_code {code} not found in DART corpCode")
    corp_code, corp_name = match.group(1), match.group(2)
    print(f"  -> {corp_code} ({corp_name})")
    return corp_code


def fetch_bundle(corp_code: str, out_dir: Path, years: int = 3) -> dict:
    """Fetch the full bundle and save JSON files under out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    this_year = datetime.now().year
    recent_year = str(this_year - 1) if datetime.now().month < 4 else str(this_year - 1)  # latest published annual

    def save(name, data):
        with open(out_dir / f"{name}.json", "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        results[name] = data

    def safe_fetch(label: str, fn):
        try:
            data = fn()
            status = data.get("status") if isinstance(data, dict) else None
            print(f"  {label}: status={status}")
            return data
        except Exception as e:
            print(f"  {label}: ERROR {e}")
            return {"error": str(e)}

    # 1. Company overview
    save("company", safe_fetch("company", lambda: _get("company.json", corp_code=corp_code)))
    time.sleep(0.2)

    # 2. Annual 주요계정 (most recent published)
    save("annual", safe_fetch("annual", lambda: _get("fnlttSinglAcnt.json", corp_code=corp_code, bsns_year=recent_year, reprt_code="11011")))
    time.sleep(0.2)

    # 3. Quarterly 주요계정 (3 years × 4 report codes)
    quarterly = {}
    for yr in [str(this_year - 2), str(this_year - 1), str(this_year)]:
        for rc in ["11013", "11012", "11014", "11011"]:
            key = f"{yr}_{rc}"
            try:
                d = _get("fnlttSinglAcnt.json", corp_code=corp_code, bsns_year=yr, reprt_code=rc)
                quarterly[key] = d
                time.sleep(0.15)
            except Exception as e:
                quarterly[key] = {"error": str(e)}
    save("quarterly", quarterly)
    print(f"  quarterly: {len(quarterly)} combos fetched")

    # 4. Full FS CFS
    save("full_fs", safe_fetch("full_fs", lambda: _get("fnlttSinglAcntAll.json", corp_code=corp_code, bsns_year=recent_year, reprt_code="11011", fs_div="CFS")))
    time.sleep(0.2)

    # 5. Dividend
    save("dividend", safe_fetch("dividend", lambda: _get("alot.json", corp_code=corp_code, bsns_year=recent_year, reprt_code="11011")))
    time.sleep(0.2)

    # 6. Major shareholders
    save("major_shareholders", safe_fetch("major_shareholders", lambda: _get("hyslr.json", corp_code=corp_code, bsns_year=recent_year, reprt_code="11011")))
    time.sleep(0.2)

    # 7. 18-month disclosures
    today = datetime.now()
    bgn = (today - timedelta(days=548)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    save("disclosures_18m", safe_fetch("disclosures_18m", lambda: _get("list.json", corp_code=corp_code, bgn_de=bgn, end_de=end, page_count="100")))
    time.sleep(0.2)

    # 8. Bulk holdings
    save("bulk_holdings", safe_fetch("bulk_holdings", lambda: _get("majorstock.json", corp_code=corp_code)))
    time.sleep(0.2)

    # 9. Executive ownership
    save("exec_holdings", safe_fetch("exec_holdings", lambda: _get("elestock.json", corp_code=corp_code)))

    print(f"\nSaved bundle to: {out_dir}")
    return results


def read_disclosure(rcept_no: str) -> str:
    """Fetch and extract text from a single disclosure by rcept_no (Tier 1 full-text reading)."""
    from bs4 import BeautifulSoup
    r = requests.get(f"{BASE}/document.xml", params={"crtfc_key": API_KEY, "rcept_no": rcept_no}, timeout=30)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open(z.namelist()[0]) as f:
            soup = BeautifulSoup(f, "html.parser")
    return soup.get_text(separator="\n", strip=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_dart_bundle.py <corp_code_or_stock_code> [output_dir]")
        sys.exit(1)
    code = sys.argv[1]
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd() / "dart"
    corp_code = resolve_corp_code(code)
    fetch_bundle(corp_code, out_dir)
