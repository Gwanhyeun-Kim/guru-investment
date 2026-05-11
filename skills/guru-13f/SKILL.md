---
name: guru-13f
description: Use when the user asks to check a super-investor's 13F (Druckenmiller, Buffett, Burry, Ackman, Tepper, Klarman, Soros, Bridgewater 등), track quarter-over-quarter portfolio changes, or compare what a guru is buying/selling. Automates SEC EDGAR 13F-HR fetch across the last 3 quarters, builds a position-level matrix (NEW/EXIT/ADD/TRIM/HOLD + multi-quarter trajectory tags), produces 6 PNG charts, and writes a Korean-language report with macro thesis interpretation and cross-reference to the user's holdings.
---

# guru-13f — 슈퍼투자자 13F 추적·비교·시각화

## Overview

이 스킬은 SEC EDGAR에 13F-HR을 제출하는 운용사(슈퍼투자자 패밀리오피스·헤지펀드·기관)의 **최근 3개 분기 보유 종목을 자동으로 가져와 비교하고 차트로 시각화하는 데이터 파이프라인 + 리포트 작성기**다. 매번 CIK 검색·XML 파싱·delta 계산·차트 그리기를 수동으로 하지 않고, 한 번 호출로 끝낸다.

**Core principle**: 단일 분기 13F는 스냅샷에 불과하다. **3개 분기 비교**는 "이게 단발 베팅인지 누적 매집인지"를 분리해주며, **trajectory tag** (SCALING_UP / SCALING_DOWN / NEW_AND_ADDING / REVERSAL 등)이 그 시그널을 한 줄로 압축한다.

## When to Use

- "Druckenmiller 13F 확인해" / "Buffett 최근 매수" / "Burry는 뭘 들고 있어"
- "이번 분기 슈퍼투자자 누가 X 매수했어"
- "Pershing Square 분기 변동" / "Citadel 신규 종목"
- 형님 보유 종목과 슈퍼투자자 13F를 교차하고 싶을 때
- 13F 시계열 차트가 필요할 때 (AUM 추이, Top 15 분기 변화, NEW vs EXIT 비교)

**NOT for:**
- 한 종목을 깊이 분석할 때 → `guru-investment` 스킬 사용
- 한국 KOSPI/KOSDAQ 분석 → `guru-investment` + DART/KRX (13F는 미국 상장만)
- 13F 정성 해석이 끝나면 흥미로운 종목은 `guru-investment`로 chaining

## Quick Reference

<table>
<thead><tr><th>단계</th><th>도구</th><th>출력</th></tr></thead>
<tbody>
<tr><td>1. Filer → CIK 매핑</td><td>known_filers.json 우선 / 모르면 EDGAR 회사검색</td><td>cik (digits)</td></tr>
<tr><td>2. 최근 3분기 13F-HR 페치 + 비교 매트릭스</td><td><code>scripts/fetch_compare.py CIK [N] [out_dir]</code></td><td>raw/, holdings_*.json, comparison.json, meta.json</td></tr>
<tr><td>3. 차트 6개 생성</td><td><code>scripts/visualize.py out_dir</code></td><td>charts/01~06.png</td></tr>
<tr><td>4. 리포트 작성</td><td>아래 템플릿 따라 한국어로</td><td>Desktop + Obsidian 양쪽 저장</td></tr>
</tbody>
</table>

## Workflow

### Step 1 — Filer 식별

1. `known_filers.json` 읽고 사용자 입력(이름·alias)을 매칭.
2. 매칭 안 되면 SEC EDGAR 회사검색 (`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={query}&type=13F`)으로 CIK 찾기.
3. 검증: `https://data.sec.gov/submissions/CIK{cik:010}.json` 호출해서 entity name 확인.
4. `known_filers.json`에 없는 새 filer는 분석 후 추가 (PR 가능).

### Step 2 — 3분기 자동 페치 + 비교

```bash
cd ~/.claude/skills/guru-13f
python3 scripts/fetch_compare.py <CIK> 3 output/<slug>
```

생성물:
- `raw/<reportDate>.xml` — SEC information-table XML 원본 (감사용)
- `holdings_<reportDate>.json` — 분기별 raw holdings
- `comparison.json` — 차트·리포트에 쓰는 마스터 데이터. 구조:
  - `entity`, `cik`, `quarter_labels` (newest first), `quarter_totals_k`
  - `summary_vs_prior`: {NEW, ADD, HOLD, TRIM, EXIT} 카운트 (최신 vs 직전)
  - `trajectory_buckets`: {SCALING_UP, SCALING_DOWN, NEW_AND_ADDING, …} 카운트 (3분기 패턴)
  - `rows[]`: 종목별 {name, putcall, status_vs_prior, trajectory, quarters[]} — quarters는 최신→오래된 순

**Trajectory 태그 사전** (3분기 비교 시 핵심):

<table>
<thead><tr><th>태그</th><th>의미 (oldest → newest 패턴)</th><th>시그널</th></tr></thead>
<tbody>
<tr><td>SCALING_UP</td><td>monotone 증가 (0 안 들어옴)</td><td>강한 누적 매집 — 가장 강한 컨빅션 시그널</td></tr>
<tr><td>SCALING_DOWN</td><td>monotone 감소</td><td>꾸준한 차익실현</td></tr>
<tr><td>NEW_AND_ADDING</td><td>0 → x → y (y &gt; x), 즉 직전 분기 신규 후 추가 매수</td><td>"시험 베팅 → 컨빅션 확정"</td></tr>
<tr><td>NEW_AND_HOLDING</td><td>0 → x → x</td><td>신규 후 관찰 단계</td></tr>
<tr><td>NEW_AND_TRIMMING</td><td>0 → x → y (y &lt; x)</td><td>"시험 베팅 → 후퇴"</td></tr>
<tr><td>NEW_LATEST</td><td>이번 분기에 처음 등장</td><td>신규 — 아직 컨빅션 미확정</td></tr>
<tr><td>REVERSAL_TO_ADD</td><td>줄이다 다시 매수</td><td>thesis 재확립</td></tr>
<tr><td>REVERSAL_TO_TRIM</td><td>늘리다 다시 매도</td><td>thesis 재검토</td></tr>
<tr><td>HOLDING_STEADY</td><td>3분기 모두 동일</td><td>장기 보유 / 코어 포지션</td></tr>
<tr><td>EXITED</td><td>nonzero → 0 (어디선가)</td><td>완전 매도</td></tr>
<tr><td>MIXED</td><td>위 어디에도 안 맞음</td><td>해석 보류 — 개별 검토</td></tr>
</tbody>
</table>

### Step 3 — 차트 생성

```bash
python3 scripts/visualize.py output/<slug>
```

생성물 (`output/<slug>/charts/`):
1. `01_aum_history.png` — 분기별 13F AUM ($B) 추이
2. `02_top15_ribbon.png` — Top 15 latest holdings의 분기별 value (grouped bars, 최신=진한색)
3. `03_top15_share_trajectory.png` — Top 15의 share count 라인 그래프 (3개 분기)
4. `04_status_distribution.png` — 직전 분기 대비 NEW/ADD/HOLD/TRIM/EXIT 카운트
5. `05_trajectory_distribution.png` — 3분기 trajectory 태그 분포
6. `06_top_new_vs_exit.png` — 가장 큰 NEW Top 10 vs 가장 큰 EXIT Top 10 ($M)

### Step 4 — 한국어 리포트 작성

저장 경로 (양쪽 필수):
- `~/Desktop/Claude/Investment Research/GURU/<Manager>_13F/`
- `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Secretary/Investment Research/GURU/<Manager>_13F/`

파일명: `<Entity>_13F_<YYYYQq>_<YYYYMMDD>.md` (예: `Duquesne_13F_2025Q4_20260511.md`)

차트는 두 경로 모두에 `charts/` 서브폴더로 복사. Obsidian은 `![](charts/01_aum_history.png)` 또는 `![[01_aum_history.png]]` 임베드.

#### Frontmatter (필수)

```yaml
---
tags:
  - investment
  - investment/US
  - investment/guru
  - investment/<manager-slug>
  - 13F
aliases:
  - <Manager> 13F <Qn YYYY>
created: <today>
filer: <Entity name from EDGAR>
cik: "<CIK>"
report_period: <latest reportDate YYYY-MM-DD>
filing_date: <filingDate>
accession: <accession>
quarters_compared: 3
---
```

#### 리포트 섹션 (순서대로)

1. **Executive Summary** — 한 문단 + 핵심 수치 표 (3분기 AUM, NEW/EXIT 카운트, top trajectory 패턴 3개)
2. **AUM 추이** — `01_aum_history.png` 임베드 + 1줄 해석
3. **Top 15 Holdings (latest)** — `02_top15_ribbon.png` + 3분기 값 테이블 + trajectory 태그
4. **Share count trajectory** — `03_top15_share_trajectory.png` + 가속/감속 종목 짚어줌
5. **Multi-quarter trajectory 분포** — `05_trajectory_distribution.png` + SCALING_UP/SCALING_DOWN 종목 리스트 (가장 강한 컨빅션 시그널)
6. **NEW vs EXIT** — `06_top_new_vs_exit.png` + 양쪽 Top 10 표
7. **ADD / TRIM 주요** — 표
8. **매크로 thesis 해석** — `references/<guru>.md` 프레임워크 (Druckenmiller라면 macro hierarchy, Buffett이라면 quality moat) 적용해서 그가 보고 있는 매크로 그림 reverse-engineer
9. **사용자 포트와의 교차** — MEMORY.md + `~/Desktop/Claude/Investment Research/` + Obsidian Investment Research/ 스캔하여 형님이 보유·관심·분석한 종목 중 13F와 겹치는 것 표
10. **검토 후보** — 13F에서 형님 thesis 보강해줄 종목 5개 정도 (한국·미국 가리지 않고)
11. **위험 시그널** — 13F의 본질적 한계 (long-only, 분기말 스냅샷, 시점 갭)
12. **부록 — 데이터 소스** — XML URL, accession, 검증 가능한 1차 출처

#### CLAUDE.md MD lint (저장 직전 grep 두 개 모두 0건 확인)

```bash
grep -cE '\*\*[^*]{1,200}["'"'"')\].,!?;:”’」』》]\*\*[가-힣]' <file>   # → 0
grep -cE '^\|.*\|.*\|$' <file>                                      # → 0
```

표는 HTML `<table>`만, 강조 안에서 구두점 뒤 한글 조사 금지. 한자 금지(億/兆 → 억/조).

## Common Mistakes

<table>
<thead><tr><th>실수</th><th>현실</th><th>대응</th></tr></thead>
<tbody>
<tr><td>"이 슈퍼투자자 한국 종목 들고 있다"</td><td>13F는 미국 상장 long only. 한국·일본·유럽 직상장은 13F에 안 나옴. 그가 본인 인터뷰에서 한국 보유한다고 했어도 13F엔 안 나타남.</td><td>한국 익스포저는 ADR (CPNG, KEP 등)에서만 확인 가능. 본인 발언과 13F 차이를 보고서에 반드시 명시</td></tr>
<tr><td>"숏 포지션 있다"</td><td>13F는 long position만. 채권 숏, 통화 베팅, 옵션 헷지는 누락</td><td>채권 숏·통화 베팅·금은 본인 인터뷰·서한·CFTC COT (있는 경우)로 보완</td></tr>
<tr><td>"분기말이니까 이게 현재 포지션이다"</td><td>13F는 분기말 +45일 마감. 보고 시점에 이미 6~12주 지난 데이터</td><td>"보고 시점 vs 보유 시점 갭" 섹션을 보고서에 항상 명시</td></tr>
<tr><td>"단일 분기 NEW를 그대로 따라 사면 된다"</td><td>NEW_AND_TRIMMING(시험 베팅 후 후퇴)이 NEW_AND_ADDING(컨빅션 확정)보다 훨씬 많음</td><td>3분기 trajectory 태그가 단순 NEW보다 신뢰도 높음. SCALING_UP·NEW_AND_ADDING 우선</td></tr>
<tr><td>"매그7 전부 매수했다"</td><td>"Magnificent Seven" 같은 별칭은 13F에 안 나옴. 종목명은 SEC 등록 issuer 이름 (Alphabet Inc, Amazon Com Inc 등)</td><td>이름 매칭 시 SEC 표기 기준</td></tr>
<tr><td>"옵션도 보였다"</td><td>13F에 putCall 필드 — Call/Put 노출은 별도 행으로 표시. 같은 issuer가 보통주 + 콜로 두 번 등장 가능</td><td>aggregate 시 (name, putcall) 키로 분리</td></tr>
<tr><td>"한국 종목 직접 추천"</td><td>13F에서 한국 ADR 외 한국 종목 추천은 못 함</td><td>한국 종목은 별도로 guru-investment + DART/KRX로 분석</td></tr>
</tbody>
</table>

## Cross-skill chaining

- 13F에서 흥미로운 종목 발견 시 → **guru-investment 스킬**로 그 종목 deep dive
- 형님 보유 한국 종목과 비교 시 → MEMORY.md `project_*_guru_analysis.md` 참조
- 산업 단위 분석 필요 시 → **industry-dive 스킬** (탑다운 섹터 분석)

## Real-World Impact

베이스라인(이 스킬 도입 전, Druckenmiller 13F 분석 사례):
- 직전 1분기만 비교 → SCALING_UP·NEW_AND_ADDING 같은 다분기 패턴 식별 불가
- 차트 없음 → 텍스트만으로 패턴 전달
- CIK 매번 EDGAR 검색
- 보고서 구조 매번 처음부터 작성

이 스킬 도입 후:
- 3분기 trajectory 태그 11종으로 시그널 분리 (SCALING_UP, REVERSAL 등)
- 6개 차트 자동 (AUM 시계열, Top 15 ribbon, share trajectory, status 분포, trajectory 분포, NEW vs EXIT)
- 16명 슈퍼투자자 CIK pre-mapped (`known_filers.json`)
- 표준 한국어 리포트 구조 12 섹션
- 호출: `python3 scripts/fetch_compare.py {CIK} 3 output/{slug}` → `python3 scripts/visualize.py output/{slug}` → 리포트 작성

## Implementation Notes

- **HTTP**: `urllib.request` (stdlib). User-Agent 헤더 필수 (SEC EDGAR 요구사항).
- **Rate limit**: SEC EDGAR는 분당 10 req. 본 스크립트는 분기당 ~2 req + 0.15s sleep으로 안전.
- **XML 파싱**: `xml.etree.ElementTree` stdlib. namespace 처리 필수.
- **차트**: matplotlib only (의존성 최소화). Obsidian PNG 직접 임베드 호환.
- **확장**: 4분기 이상으로 늘리려면 `fetch_compare.py CIK 4` (단, 차트는 분기당 색 4개까지만 미리 정의 — 더 늘리면 visualize.py의 `quarter_palette` 확장 필요).

## Files

- `SKILL.md` (this file)
- `known_filers.json` — 16명 슈퍼투자자 CIK 매핑
- `scripts/fetch_compare.py` — EDGAR 페치 + 파싱 + 비교 매트릭스 (stdlib only)
- `scripts/visualize.py` — 6 PNG 차트 (matplotlib)
- `output/<slug>/` — per-manager 캐시 (raw XML, JSON, charts)
