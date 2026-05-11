# guru-investment + transcript-pulse + guru-13f

Claude Code skills for **institutional-grade stock and super-investor portfolio analysis** through the lens of legendary investors (Buffett, Marks, Lynch, Dalio, Soros, Druckenmiller, Minervini, O'Neil, Greenblatt, Aschenbrenner), with automated data collection from SEC EDGAR, DART (Korea), KRX, FRED, fool.com earnings call transcripts, and SEC 13F-HR filings.

## What's included

### 1. `guru-investment/` — Multi-Guru Stock Analysis Engine

- **10 investor framework reference files** (`references/*.md`) — Buffett, Marks, Lynch, Dalio, Soros, Druckenmiller, Minervini, O'Neil, Greenblatt, Aschenbrenner. Each ~10-20KB, dense reconstructions of how each guru actually thinks (not parrot quotes).
- **Data API integration guides**:
  - `dart-api.md` — Korean DART OpenAPI (financials, disclosures, ownership)
  - `krx-api.md` — Korea Exchange Open API (prices, market data, ETFs)
  - `us-edgar-api.md` — SEC EDGAR direct API (XBRL companyfacts, 18-month filings, body parsing)
  - `us-prices-api.md` — yfinance (US market data, holders, insiders, analyst TPs)
  - `us-macro-fred.md` — FRED API (Fed funds, CPI, yields, oil, DXY)
  - `finnhub.md` — Finnhub free (quarterly consensus EPS, earnings calendar)
  - `mckinsey-chart-style-guide.md` — Visual style guide for institutional report charts
- **Batch fetch scripts** (`scripts/*.py`):
  - `fetch_dart_bundle.py` — Korean stock: company overview + annual/quarterly financials + 18-month disclosures + ownership in one command
  - `fetch_us_bundle.py` — US stock: SEC submissions + companyfacts + yfinance cache + (optional) FRED macro + Finnhub estimates
  - `fetch_krx_daily.py` — KRX daily price/volume history
  - `ta_utils.py` — Minervini SEPA trend template + VCP pattern + stage analysis helpers

### 2. `transcript-pulse/` — Earnings Call Nuance Tracker

Analyzes the last 3 quarters of fool.com earnings call transcripts to extract:
- **Surge in T0**: topics emphasized for the first time or with new conviction this quarter
- **Tone Shift**: phrase intensity changes on the same topic across quarters (e.g., "exploring" → "expect" → "highest conviction ever")
- **Faded narrative**: topics emphasized previously but dropped in the latest call
- **Analyst Q&A concerns**: what analysts keep probing (avoidance vs direct answers)
- **T0 standalone summary**: standalone analysis of the most recent call with verbatim quotes and `==highlights==`. Verbatim transcript embedded in collapsible Obsidian callout (`> [!quote]-`) — survives heading/HR/unbalanced-highlight rendering bugs that break raw `<details>` blocks.

Designed to slot into `guru-investment` as a sub-call on US stocks, or run standalone with `transcript pulse {TICKER}`.

### 3. `guru-13f/` — Super-Investor 13F Tracker

Tracks the most recent 3 quarterly 13F-HR filings of any SEC-registered institutional investor (Druckenmiller, Buffett, Burry, Ackman, Tepper, Klarman, Soros, Bridgewater, Citadel, Viking, Coatue, Tiger Global, Renaissance, Greenlight, Third Point, Millennium, Pershing Square — 16 pre-mapped, plus EDGAR company search for unknown filers). Output:
- **Position-level matrix** (NEW / ADD / HOLD / TRIM / EXIT vs prior quarter)
- **Multi-quarter trajectory tags** (11 classes — `SCALING_UP`, `SCALING_DOWN`, `NEW_AND_ADDING`, `NEW_AND_TRIMMING`, `REVERSAL_TO_ADD`, `REVERSAL_TO_TRIM`, `HOLDING_STEADY`, etc.) that distinguish "conviction-confirming" from "test-and-retreat" patterns single-quarter analysis misses.
- **6 auto-generated PNG charts** — AUM history, Top-15 holdings ribbon, Top-15 share trajectory, status distribution, trajectory distribution, biggest NEW vs EXIT.
- **Korean-language report** — macro thesis interpretation through Druckenmiller's reference framework + cross-reference to the user's Korean portfolio holdings.

Run with `python3 scripts/fetch_compare.py {CIK} 3 output/{slug}` → `python3 scripts/visualize.py output/{slug}` → Claude writes the report from `comparison.json`. SEC EDGAR direct API, no key required (only User-Agent header).

## Output structure

Each analysis produces:
1. **Full multi-guru report** (~50-90K chars) — Part 1 company deep-dive + Part 2 guru frameworks + Part 3 investment verdict
2. **Compressed CEO decision memo** (~3-5K chars) — 1-2 page thesis paper with BUY/HOLD/SELL/AVOID verdict, 3 key arguments, biggest risk, position management plan

Reports include 5+ McKinsey-style PNG charts (quarterly inflection, gross margin evolution, capacity roadmap, EPS surprise, price/MA) plus Mermaid diagrams (value chain, customer adoption cascade).

## Install

```bash
# Clone this repo
git clone https://github.com/Gwanhyeun-Kim/guru-investment.git
cd guru-investment

# Copy skills to Claude Code skills directory
cp -R skills/guru-investment ~/.claude/skills/
cp -R skills/transcript-pulse ~/.claude/skills/
cp -R skills/guru-13f ~/.claude/skills/

# Install Python dependencies
pip3 install --user requests beautifulsoup4 yfinance matplotlib
```

## Environment variables

Copy `.env.example` to `.env`, then either source it (`source .env`) or export each variable.

| Variable | Required for | Where to get (free) |
|---|---|---|
| `DART_API_KEY` | Korean stock fundamentals | https://opendart.fss.or.kr/ |
| `KRX_API_KEY` | Korean stock market data | https://openapi.krx.co.kr/ |
| `EDGAR_IDENTITY` | US SEC EDGAR (any free-form `Name email@example.com`) | Just use your name + email |
| `FRED_API_KEY` | US macro (Fed funds, CPI, yields) | https://fred.stlouisfed.org/ |
| `FINNHUB_API_KEY` | US quarterly consensus EPS | https://finnhub.io/ |

All four free-tier APIs. No paid subscriptions required.

## Usage

In Claude Code, after the skills are installed:

```
# Korean stock analysis
guru investment 삼성전자

# US stock analysis (auto-runs transcript-pulse sub-call)
guru investment NVDA

# Standalone earnings call analysis
transcript pulse AAPL

# Super-investor 13F tracking (3-quarter comparison + 6 charts)
guru 13f druckenmiller
guru 13f buffett
guru 13f burry
```

Or use the slash command form:
```
/guru-investment {ticker_or_name}
/transcript-pulse {US_TICKER}
/guru-13f {filer_name_or_CIK}
```

## Output organization

By default, reports are saved to `~/Desktop/Investment Research/{ticker}/`. You can customize this path in the skill's `Important Guidelines` section. If you use Obsidian, the skill also sync-saves to your vault under `Investment Research/{KR_stocks or US Stocks}/{ticker}/` — adjust the iCloud Obsidian path for your setup.

## Notes on philosophy

This skill is opinionated about what "institutional-grade" means:
- **Verbatim quotes over paraphrasing**, especially in earnings call analysis
- **API 1st-party data over web scraping** (SEC EDGAR > web aggregators)
- **Quarterly granularity** (12 quarters), not just annual
- **18-month disclosure body parsing**, not just titles (3-Tier filtering: 8-K Item 5.02 / 2.02 / 5.07 priority for US, 주요사항보고 priority for Korea)
- **5 guru weighted consensus**, not single-framework — verdict is the weighted average + transcript pulse signal

## License

MIT. See `LICENSE`.

## Disclaimer

Educational/analytical tool only. Not investment advice. All output is the model's reasoning over public data — verify before acting. Past performance doesn't predict future results.
