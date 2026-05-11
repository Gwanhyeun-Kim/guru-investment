#!/usr/bin/env python3
"""Super-Investor Reverse Sweep — guru-investment skill Step 2.5c.

Given a TICKER + CUSIP, loop through 16 pre-mapped super-investors
(known_filers.json in guru-13f skill), fetch their last 3 quarterly 13F-HR
filings from SEC EDGAR, filter for CUSIP holdings, build a position-by-quarter
matrix with trajectory tags.

Usage:
    python3 super_investor_sweep.py TICKER CUSIP [output_dir]
Example:
    python3 super_investor_sweep.py AMZN 023135106 /tmp/amzn_sweep
    python3 super_investor_sweep.py AAPL 037833100 /tmp/aapl_sweep

Output: stdout matrix + JSON file (super_investor_sweep.json) in output_dir.

Dependencies: stdlib only (urllib, xml, json, concurrent.futures).
"""
import json, urllib.request, datetime, sys, os, re
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Investment-Research vivienjun@snu.ac.kr"

# Default known_filers location (guru-13f skill)
KNOWN_FILERS_PATH = os.path.expanduser(
    "~/.claude/skills/guru-13f/known_filers.json"
)


def load_filers(path=KNOWN_FILERS_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Cannot find {path}. Install guru-13f skill or pass --filers-path."
        )
    with open(path) as f:
        return json.load(f)["filers"]


def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def fetch_text(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', errors='replace')


def get_13f_filings(cik, n_quarters=3):
    """Return list of dicts with last n 13F-HR filings."""
    sub = fetch_json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    rec = sub['filings']['recent']
    results = []
    for i in range(len(rec['accessionNumber'])):
        if rec['form'][i] in ('13F-HR', '13F-HR/A'):
            results.append({
                'period': rec['reportDate'][i],
                'accession': rec['accessionNumber'][i],
                'primary_doc': rec['primaryDocument'][i],
                'cik_num': int(cik)
            })
            if len(results) >= n_quarters:
                break
    return results


def get_holdings_for_cusip(cik_num, accession, primary_doc, cusip):
    """Parse 13F-HR info table XML, return total shares + value for given CUSIP."""
    acc_clean = accession.replace('-', '')
    folder_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_clean}/"
    try:
        listing = fetch_text(folder_url)
    except Exception as e:
        return 0, 0, f"folder fetch fail: {e}"
    xml_files = re.findall(r'href="([^"]+\.xml)"', listing)
    info_table_xml = None
    for x in xml_files:
        name = x.split('/')[-1].lower()
        if 'infotable' in name or 'informationtable' in name:
            info_table_xml = x.split('/')[-1]
            break
    if not info_table_xml:
        for x in xml_files:
            name = x.split('/')[-1].lower()
            if 'primary' not in name and 'index' not in name and 'cover' not in name:
                info_table_xml = x.split('/')[-1]
                break
    if not info_table_xml:
        return 0, 0, "no info table xml found"
    try:
        xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_clean}/{info_table_xml}"
        xml_text = fetch_text(xml_url)
        root = ET.fromstring(xml_text)
    except Exception as e:
        return 0, 0, f"xml parse fail: {e}"
    rows = [c for c in root.iter() if c.tag.endswith('infoTable')]
    total_shares = 0
    total_value = 0
    for row in rows:
        row_cusip = None
        row_value = 0
        row_shares = 0
        for c in row:
            if c.tag.endswith('cusip'):
                row_cusip = c.text
            elif c.tag.endswith('value'):
                try:
                    row_value = int(c.text or 0)
                except:
                    row_value = 0
            elif c.tag.endswith('shrsOrPrnAmt'):
                for cc in c:
                    if cc.tag.endswith('sshPrnamt'):
                        try:
                            row_shares = int(cc.text or 0)
                        except:
                            row_shares = 0
        if row_cusip == cusip:
            total_shares += row_shares
            total_value += row_value
    return total_shares, total_value, "ok"


def sweep_one_filer(key, info, cusip):
    cik = info['cik']
    try:
        filings = get_13f_filings(cik, n_quarters=3)
    except Exception as e:
        return {'key': key, 'name': info['entity'], 'error': f"submissions fetch: {e}"}
    if not filings:
        return {'key': key, 'name': info['entity'], 'error': 'no 13F-HR filings'}
    quarters = []
    for f in filings:
        shares, value, status = get_holdings_for_cusip(
            f['cik_num'], f['accession'], f['primary_doc'], cusip
        )
        quarters.append({
            'period': f['period'],
            'shares': shares,
            'value_k': value,
            'status': status,
        })
    return {
        'key': key,
        'name': info['entity'],
        'manager': info['manager'],
        'style': info['style'],
        'quarters': quarters
    }


def make_trajectory(quarters):
    if not quarters or len(quarters) < 1:
        return "NO_DATA"
    q0 = quarters[0]['shares'] if len(quarters) > 0 else 0
    q1 = quarters[1]['shares'] if len(quarters) > 1 else 0
    q2 = quarters[2]['shares'] if len(quarters) > 2 else 0
    if q0 == 0 and q1 == 0 and q2 == 0:
        return "NEVER_HELD"
    if q0 == 0 and q1 > 0:
        return f"EXITED (was {q1/1e3:.0f}K → 0)"
    if q1 == 0 and q0 > 0:
        return "RE_ENTRY" if q2 > 0 else "NEW_LATEST"
    if q0 > q1 > q2:
        return "SCALING_UP_3Q"
    if q0 > q1 and q1 <= q2:
        return "REVERSAL_TO_ADD"
    if q0 < q1 < q2:
        return "SCALING_DOWN_3Q"
    if q0 < q1 and q1 >= q2:
        return "REVERSAL_TO_TRIM"
    if q0 > q1 == q2:
        return "ADDED_LATEST"
    if q0 == q1 == q2 and q0 > 0:
        return "HOLDING_STEADY"
    if q0 < q1 == q2:
        return "TRIMMED_LATEST"
    return "MIXED"


def fmt_q(q):
    if not q or q['shares'] == 0:
        return "—"
    return f"{q['shares']/1e3:.0f}K (${q['value_k']/1e6:.1f}M)"


def main():
    if len(sys.argv) < 3:
        print("Usage: super_investor_sweep.py TICKER CUSIP [output_dir]", file=sys.stderr)
        sys.exit(1)
    ticker = sys.argv[1].upper()
    cusip = sys.argv[2]
    out_dir = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()
    os.makedirs(out_dir, exist_ok=True)

    filers = load_filers()
    print(f"Sweeping {len(filers)} super-investors for {ticker} (CUSIP {cusip})")
    print(f"Output: {out_dir}\n")

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(sweep_one_filer, k, v, cusip): k for k, v in filers.items()}
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(
        key=lambda r: r['quarters'][0]['shares'] if 'quarters' in r and r['quarters'] else -1,
        reverse=True
    )

    print("=" * 115)
    print(f"{'Filer':<28} {'Manager':<22} {'Q-0':<14} {'Q-1':<14} {'Q-2':<14} {'Trajectory':<20}")
    print("-" * 115)

    out_data = []
    for r in results:
        if 'error' in r:
            print(f"{r['name'][:27]:<28} ERROR: {r['error'][:60]}")
            continue
        q = r['quarters']
        traj = make_trajectory(q)
        if 'NEVER_HELD' in traj or 'NO_DATA' in traj:
            continue
        q0s = fmt_q(q[0]) if len(q) > 0 else "—"
        q1s = fmt_q(q[1]) if len(q) > 1 else "—"
        q2s = fmt_q(q[2]) if len(q) > 2 else "—"
        print(f"{r['name'][:27]:<28} {r['manager'][:21]:<22} {q0s:<14} {q1s:<14} {q2s:<14} {traj}")
        out_data.append({
            'filer_key': r['key'],
            'entity': r['name'],
            'manager': r['manager'],
            'style': r['style'],
            'quarters': q,
            'trajectory': traj,
        })

    print("\n--- NEVER_HELD ---")
    for r in results:
        if 'error' in r:
            continue
        if make_trajectory(r['quarters']) == "NEVER_HELD":
            print(f"  - {r['name']} ({r['manager']}) — {r['style']}")

    out_path = os.path.join(out_dir, "super_investor_sweep.json")
    with open(out_path, 'w') as f:
        json.dump({
            'ticker': ticker, 'cusip': cusip,
            'as_of': datetime.datetime.now().isoformat(),
            'holders': out_data,
            'all_results': results,
        }, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")
    print(f"Holders: {len(out_data)} / {len(filers)}")


if __name__ == "__main__":
    main()
