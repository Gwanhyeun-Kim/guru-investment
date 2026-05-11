#!/usr/bin/env python3
"""
fetch_compare.py — SEC EDGAR 13F-HR multi-quarter fetcher + comparator

Usage:
    python3 fetch_compare.py <CIK> [num_quarters] [out_dir]

Args:
    CIK            — SEC Central Index Key (digits only or zero-padded)
    num_quarters   — how many recent 13F-HR quarters to compare (default: 3)
    out_dir        — output directory (default: ./output/<cik>)

Outputs in <out_dir>:
    raw/<reportDate>.xml          — raw 13F-HR information tables
    holdings_<reportDate>.json    — per-quarter parsed holdings
    comparison.json               — multi-quarter matrix (all data needed for reports + charts)
    meta.json                     — filer metadata + filing dates

Requires:
    - requests (stdlib alternative: urllib)
    - No API key. SEC EDGAR requires a User-Agent header identifying the requester.
"""

import sys
import os
import json
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

USER_AGENT = "Personal Research vivienjun@snu.ac.kr"
NS = {"x": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}


def http_get(url: str, accept: str = "application/json", retries: int = 3) -> bytes:
    """SEC-compliant GET with User-Agent. Returns raw bytes."""
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": accept,
                "Accept-Encoding": "gzip, deflate",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                enc = r.headers.get("Content-Encoding", "")
                if enc == "gzip":
                    import gzip
                    data = gzip.decompress(data)
                elif enc == "deflate":
                    import zlib
                    data = zlib.decompress(data)
                return data
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} attempts: {url} -- {last_err}")


def find_recent_13f(cik: str, n: int = 3) -> list:
    """Returns list of {form, reportDate, filingDate, accession, primaryDoc} dicts, most-recent first."""
    cik_padded = str(cik).lstrip("0").zfill(10)
    sub_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    data = json.loads(http_get(sub_url))
    entity_name = data.get("name", "Unknown")
    recent = data["filings"]["recent"]
    results = []
    for i in range(len(recent["form"])):
        if recent["form"][i] == "13F-HR":
            results.append({
                "form": recent["form"][i],
                "reportDate": recent["reportDate"][i],
                "filingDate": recent["filingDate"][i],
                "accession": recent["accessionNumber"][i],
                "primaryDoc": recent["primaryDocument"][i],
            })
            if len(results) >= n:
                break
    return entity_name, results


def find_info_table_xml(cik: str, accession: str) -> str:
    """Discover the information-table XML filename inside an accession folder.
    The file is conventionally named form13f_YYYYMMDD.xml but we list the
    folder via index.json for robustness."""
    cik_int = str(int(cik))
    acc_clean = accession.replace("-", "")
    folder_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/"
    idx = json.loads(http_get(folder_url + "index.json"))
    items = idx.get("directory", {}).get("item", [])
    candidates = [it["name"] for it in items if it["name"].endswith(".xml") and it["name"].lower() != "primary_doc.xml"]
    if not candidates:
        raise RuntimeError(f"No information-table xml in {folder_url}")
    if len(candidates) > 1:
        prefer = [n for n in candidates if "form13f" in n.lower() or "informationtable" in n.lower() or "infotable" in n.lower()]
        if prefer:
            candidates = prefer
    return folder_url + candidates[0]


def parse_information_table(xml_bytes: bytes) -> list:
    """Returns list of holding dicts from a 13F information-table XML."""
    root = ET.fromstring(xml_bytes)
    holdings = []
    for info in root.findall("x:infoTable", NS):
        name = info.findtext("x:nameOfIssuer", default="", namespaces=NS).strip()
        cls = info.findtext("x:titleOfClass", default="", namespaces=NS).strip()
        cusip = info.findtext("x:cusip", default="", namespaces=NS).strip()
        value = int(info.findtext("x:value", default="0", namespaces=NS) or 0)
        shrs_node = info.find("x:shrsOrPrnAmt", NS)
        shrs = int(shrs_node.findtext("x:sshPrnamt", default="0", namespaces=NS) or 0)
        shtype = shrs_node.findtext("x:sshPrnamtType", default="", namespaces=NS)
        putcall = info.findtext("x:putCall", default="", namespaces=NS).strip()
        holdings.append({
            "name": name,
            "cls": cls,
            "cusip": cusip,
            "value": value,       # in $1,000
            "shares": shrs,
            "shtype": shtype,
            "putcall": putcall,
        })
    return holdings


def aggregate_by_key(holdings: list) -> dict:
    """Group by (name, putcall) so call/put options are tracked separately from common stock."""
    out = defaultdict(lambda: {"value": 0, "shares": 0, "cusip": "", "cls": ""})
    for h in holdings:
        k = (h["name"], h["putcall"])
        out[k]["value"] += h["value"]
        out[k]["shares"] += h["shares"]
        out[k]["cusip"] = h["cusip"]
        out[k]["cls"] = h["cls"]
    return out


def build_matrix(quarter_aggs: list, quarter_labels: list, quarter_totals: list) -> list:
    """Construct rows joining N quarters by issuer/putcall key.

    quarter_aggs[i] is aggregate dict for quarter_labels[i] (newest at i=0).
    """
    all_keys = set()
    for q in quarter_aggs:
        all_keys.update(q.keys())
    rows = []
    for key in all_keys:
        name, pc = key
        per_q = []
        for i, q in enumerate(quarter_aggs):
            qr = q.get(key, {"value": 0, "shares": 0, "cusip": "", "cls": ""})
            per_q.append({
                "label": quarter_labels[i],
                "value": qr["value"],
                "shares": qr["shares"],
                "cusip": qr["cusip"],
                "cls": qr["cls"],
                "pct_of_aum": (qr["value"] / quarter_totals[i] * 100) if quarter_totals[i] else 0,
            })

        latest = per_q[0]
        prior = per_q[1] if len(per_q) > 1 else {"value": 0, "shares": 0}
        # status vs immediately prior quarter
        if prior["value"] == 0 and latest["value"] > 0:
            status = "NEW"
        elif latest["value"] == 0 and prior["value"] > 0:
            status = "EXIT"
        elif latest["shares"] > prior["shares"] and prior["shares"] > 0:
            status = "ADD"
        elif latest["shares"] < prior["shares"] and latest["shares"] > 0:
            status = "TRIM"
        else:
            status = "HOLD"

        # trajectory tag using all quarters (oldest → newest)
        share_series = [q["shares"] for q in reversed(per_q)]
        traj = trajectory_tag(share_series)

        rows.append({
            "name": name,
            "putcall": pc,
            "status_vs_prior": status,
            "trajectory": traj,
            "quarters": per_q,
            "latest_value": latest["value"],
            "latest_shares": latest["shares"],
            "latest_pct": latest["pct_of_aum"],
        })
    rows.sort(key=lambda r: (-r["latest_value"], -r["quarters"][1]["value"] if len(r["quarters"]) > 1 else 0))
    return rows


def trajectory_tag(share_series: list) -> str:
    """Classify N-quarter share trajectory.

    share_series is oldest → newest. Returns one of:
    - NEW_AND_ADDING:     0 → x → y  with y > x
    - NEW_AND_HOLDING:    0 → x → x
    - NEW_AND_TRIMMING:   0 → x → y  with y < x
    - NEW_LATEST:         only present in newest quarter
    - SCALING_UP:         monotone increasing across quarters
    - SCALING_DOWN:       monotone decreasing
    - HOLDING_STEADY:     all equal nonzero
    - REVERSAL_TO_ADD:    was trimming, now adding
    - REVERSAL_TO_TRIM:   was adding, now trimming
    - EXITED:             nonzero → ... → 0
    - ABSENT:             never held
    - MIXED:              other patterns
    """
    if not any(share_series):
        return "ABSENT"
    n = len(share_series)
    if n < 2:
        return "MIXED"
    newest = share_series[-1]
    prev = share_series[-2]
    if newest == 0 and prev > 0:
        return "EXITED"
    if all(x == 0 for x in share_series[:-1]) and newest > 0:
        return "NEW_LATEST"
    if n >= 3 and share_series[0] == 0 and all(x > 0 for x in share_series[1:]):
        if share_series[-1] > share_series[-2]:
            return "NEW_AND_ADDING"
        elif share_series[-1] < share_series[-2]:
            return "NEW_AND_TRIMMING"
        else:
            return "NEW_AND_HOLDING"
    # all nonzero from here on
    if all(x > 0 for x in share_series):
        if all(share_series[i] <= share_series[i+1] for i in range(n-1)) and share_series[-1] > share_series[0]:
            return "SCALING_UP"
        if all(share_series[i] >= share_series[i+1] for i in range(n-1)) and share_series[-1] < share_series[0]:
            return "SCALING_DOWN"
        if all(share_series[i] == share_series[i+1] for i in range(n-1)):
            return "HOLDING_STEADY"
        if n >= 3:
            # reversals: middle is extreme
            mid = share_series[-2]
            old = share_series[-3]
            new = share_series[-1]
            if mid < old and new > mid:
                return "REVERSAL_TO_ADD"
            if mid > old and new < mid:
                return "REVERSAL_TO_TRIM"
    return "MIXED"


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_compare.py <CIK> [num_quarters] [out_dir]", file=sys.stderr)
        sys.exit(2)
    cik = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    out_dir = Path(sys.argv[3] if len(sys.argv) > 3 else f"./output/{cik}")
    raw_dir = out_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] resolving CIK {cik} on EDGAR...", file=sys.stderr)
    entity_name, filings = find_recent_13f(cik, n)
    if len(filings) < 2:
        print(f"warning: only {len(filings)} 13F-HR filings available (need >= 2 for comparison)", file=sys.stderr)
    if not filings:
        print("error: no 13F-HR filings found", file=sys.stderr)
        sys.exit(1)
    print(f"      entity: {entity_name}", file=sys.stderr)
    for f in filings:
        print(f"      {f['form']} reportDate={f['reportDate']} filed={f['filingDate']} acc={f['accession']}", file=sys.stderr)

    print(f"[2/4] downloading information tables...", file=sys.stderr)
    quarter_aggs = []
    quarter_labels = []
    quarter_totals = []
    quarter_meta = []
    for f in filings:
        xml_url = find_info_table_xml(cik, f["accession"])
        xml_bytes = http_get(xml_url, accept="application/xml")
        raw_path = raw_dir / f"{f['reportDate']}.xml"
        raw_path.write_bytes(xml_bytes)
        holdings = parse_information_table(xml_bytes)
        agg = aggregate_by_key(holdings)
        total_k = sum(h["value"] for h in holdings)
        quarter_aggs.append(agg)
        quarter_labels.append(f["reportDate"])
        quarter_totals.append(total_k)
        quarter_meta.append({
            **f,
            "xml_url": xml_url,
            "total_value_k": total_k,
            "n_lines": len(holdings),
            "n_unique_keys": len(agg),
        })
        per_q_path = out_dir / f"holdings_{f['reportDate']}.json"
        per_q_path.write_text(json.dumps(holdings, indent=2, ensure_ascii=False))
        time.sleep(0.15)

    print(f"[3/4] building comparison matrix...", file=sys.stderr)
    rows = build_matrix(quarter_aggs, quarter_labels, quarter_totals)

    summary_buckets = defaultdict(int)
    for r in rows:
        summary_buckets[r["status_vs_prior"]] += 1
    trajectory_buckets = defaultdict(int)
    for r in rows:
        trajectory_buckets[r["trajectory"]] += 1

    comparison = {
        "cik": cik,
        "entity": entity_name,
        "n_quarters": len(filings),
        "quarter_labels": quarter_labels,        # newest → oldest
        "quarter_totals_k": quarter_totals,
        "quarter_meta": quarter_meta,
        "summary_vs_prior": dict(summary_buckets),
        "trajectory_buckets": dict(trajectory_buckets),
        "rows": rows,
    }
    (out_dir / "comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False))
    (out_dir / "meta.json").write_text(json.dumps({
        "cik": cik,
        "entity": entity_name,
        "filings": quarter_meta,
    }, indent=2, ensure_ascii=False))

    print(f"[4/4] done. {len(rows)} unique issuer/putCall keys across {len(filings)} quarters.", file=sys.stderr)
    print(f"      output: {out_dir}", file=sys.stderr)
    print(json.dumps({
        "entity": entity_name,
        "quarter_labels": quarter_labels,
        "quarter_totals_k": quarter_totals,
        "summary_vs_prior": dict(summary_buckets),
        "trajectory_buckets": dict(trajectory_buckets),
        "out_dir": str(out_dir),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
