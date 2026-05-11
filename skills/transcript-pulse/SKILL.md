---
name: transcript-pulse
description: 미장 상장사 earnings call transcript를 최근 3분기 자동 수집·비교하여 "이번 컨콜에서 갑자기 강조된 것"과 "톤·뉘앙스 변화"를 추출하는 스킬. fool.com transcript를 1차 소스로 사용. "transcript pulse", "컨콜 톤", "earnings call 분석", "/transcript-pulse {TICKER}" 등 트리거 또는 사용자가 fool.com URL 붙여넣기. guru-investment 미장 종목 분석 시 자동 subcall 됨.
---

# Transcript Pulse — Earnings Call Nuance Tracker

지난 2-3개 분기의 earnings call transcript를 동시에 컨텍스트에 두고, 가장 최근 transcript에서 **갑자기 강조된 주제 / 톤 강도 변화 / 사라진 narrative**를 추출하는 스킬.

**핵심 가치**: GAAP 숫자가 못 잡는 alpha의 진짜 원천은 경영진이 같은 주제를 분기마다 어떻게 다르게 말하는지에 있다. 예: LB Q1 2026의 "we have higher conviction than ever that West Texas is on its way to becoming the next major data center hub" — 이전 분기들의 미온적 표현과 비교하면 명백한 narrative pivot 신호.

## Scope

- **지원**: 미장 상장사 (NYSE, NASDAQ). fool.com 커버 대상.
- **미지원**: 한국 종목 (한국 transcript 컬쳐 다르고 fool.com 미커버). v2에서 확장.

## 트리거 조건

- `/transcript-pulse {TICKER}` 명시적 호출
- "transcript pulse", "{TICKER} 컨콜 톤", "{TICKER} earnings call 분석", "{TICKER} 컨퍼런스 콜 변화"
- 사용자가 fool.com transcript URL 직접 붙여넣기
- guru-investment 미장 종목 분석 시 자동 subcall (Step 2.5b)

---

## How to Use This Skill

### Step 1: Transcript URL Discovery

입력: ticker (예: AAPL, LB, NVDA) 또는 사용자가 직접 제공한 fool.com transcript URL.

**Primary path — WebSearch**:

```
WebSearch query: "site:fool.com {ticker} earnings transcript"
```

응답에서 다음 URL 패턴 인식:
```
https://www.fool.com/earnings/call-transcripts/{YYYY}/{MM}/{DD}/{slug}-{ticker}-q{N}-{YYYY}-earnings-transcript/
```

응답에서 URL 5-10개 추출 후 발행일 desc 정렬, **최근 3개** 선택.
- T0 = 가장 최근
- T-1, T-2 = baseline

**Fallback path 1 — yfinance earnings_dates**:
```python
import yfinance as yf
t = yf.Ticker("{ticker}")
ed = t.earnings_dates  # 분기별 4개 발표일
```
실제 발표일 + 1~2일 추정으로 fool.com URL 패턴 직접 시도.

**Fallback path 2 — 사용자 직접 제공**:
사용자가 fool.com URL을 본문에 붙여넣은 경우 그것을 T0로 사용. T-1, T-2는 `site:fool.com` 검색으로 보충.

**Fallback path 3 — 모든 경로 실패**:
"fool.com에서 {ticker} transcript를 찾을 수 없습니다. 회사 IR 페이지의 webcast/transcript URL을 제공해주세요." 메시지 출력 후 사용자 입력 대기.

---

### Step 2: Body Extraction

WebFetch 호출 (3개 transcript 각각):

```
WebFetch(
  url=<transcript_url>,
  prompt="Extract the FULL earnings call transcript verbatim, including:
   (1) introduction/operator remarks,
   (2) prepared remarks from CEO and CFO with their names as section headers,
   (3) full analyst Q&A with analyst names and firms.
   Preserve all phrases — do NOT summarize.
   Output as plain text with speaker labels."
)
```

각 transcript 본문 6-10K words 추출. 3개 합계 ~24-30K words → Claude context 내 한 번에 처리 가능.

**Edge case — WebFetch 실패** (paywall/cookie/JS, 3회 retry 후):
- URL을 사용자에게 보여주고 "fool.com 페이지를 직접 열어 본문을 paste해주세요" 요청.
- 다른 transcript는 정상 수집 시 부분 분석으로 진행.

---

### Step 3: 3-Dimension Analysis

T0 = 가장 최근 transcript, T-1, T-2 = baseline.

#### Dimension 1: 갑자기 강조 (Surge in T0)

T-1, T-2에서 한 번도 안 나왔거나 한두 번 짧게 언급된 주제가 T0에서 강조·반복·확신.

**판단 방식 (Claude의 의미 기반 분석)**:
1. T0를 먼저 읽고 경영진이 반복적으로 강조하는 주제 5-7개 추출 (단순 키워드 빈도가 아니라 의미적 emphasis)
2. 각 주제에 대해 T-1, T-2에서 동일/유사 주제가 어떻게 다루어졌는지 확인
3. "T0에서 처음 등장" 또는 "T-1, T-2에서 미온적 → T0에서 확신" 패턴 식별
4. 각 surge item에 대해 T0의 가장 강한 인용구 1-2개 직접 발췌 (의역 금지)

**출력**: Top 3-5 surge items, 각각 직접 인용구 포함.

#### Dimension 2: 톤 강도 변화 (Tone Shift on same topic)

동일 주제에 대해 phrase 강도가 분기마다 어떻게 변했는지 추적.

**강도 ladder 예시**:
```
약 ────────────────────────────────► 강
"exploring" / "considering"
→ "evaluating" / "looking at"
→ "expect" / "anticipate"
→ "confident in" / "well-positioned"
→ "highly confident" / "strong conviction"
→ "highest conviction ever" / "no doubt"
```

**판단 방식**:
1. 두 transcript 이상에서 등장하는 주제 식별 (T-2, T-1, T0 모두 또는 T-1, T0)
2. 각 분기에서 그 주제에 대한 가장 대표적 phrase 1개씩 발췌 (CEO/CFO 발언 우선)
3. 강도 ladder 위치 변화 표시 (↗ 강화 / ↘ 약화 / → 유지)

**출력**: 톤 변화가 있는 주제 2-5개, 각각 T-2 → T-1 → T0 phrase contrast.

#### Dimension 3: 소멸한 narrative (Faded from T0)

T-1, T-2에서 강조됐는데 T0에서 빠진 것.

**판단 방식**:
1. T-1, T-2에서 반복 강조됐던 주제 식별
2. T0에서 그 주제가 한 번도 또는 매우 짧게 언급되었는지 확인
3. 해석: 회피 시그널 / deprioritize / 완료된 마일스톤 / 컨텍스트 변화

**출력**: 소멸한 narrative 1-3개 + 각각의 해석.

#### Bonus Dimension: Analyst Q&A 우려 포인트

분석사들이 (여러 명이 또는 같은 분석사가 follow-up으로) 집요하게 묻는 1-2가지 주제. 경영진의 답변이 직답인지 우회인지 평가.

**출력**: 1단락 짧게.

---

### Step 4: Korea Portfolio Cross-Reference

사용자가 별도로 한국(또는 다른 시장) 종목 분석을 저장한 위치가 있다면 자동 스캔하여 미장 시그널이 그 종목 thesis에 미치는 영향 식별. **이 단계는 선택사항** — 사용자가 cross-reference 대상 노트가 없다면 skip.

**스캔 대상 (사용자가 customize)**:
```bash
# 예시: Claude memory directory (oh-my-claudecode 사용자)
ls ~/.claude/projects/-Users-{username}/memory/project_*_guru_analysis.md

# 또는 Obsidian vault 내 분석 노트
ls {vault_root}/Investment\ Research/KR_stocks/**/*.md
```

본 skill에는 cross-reference 대상이 하드코딩되어 있지 않음. 사용자가 자신의 한국 portfolio thesis 노트 경로를 지정하면 그 폴더 내 .md 파일들을 grep으로 키워드 매칭.

**판단 방식**:
1. 미장 종목 transcript에서 발견한 시그널의 핵심 키워드 추출 (예: "Permian data center", "AI capex acceleration", "Hormuz oil supply", "AI infrastructure power", "HBM demand")
2. 사용자 한국 종목 노트들을 grep으로 관련 키워드 검색
3. 관련성 확인된 종목에 대해 1-2 문장으로 cross-impact 서술

**출력**: "한국(또는 타 시장) 포트폴리오 implications" 섹션 1-2 단락. 관련 종목이 없거나 cross-reference 대상이 설정되지 않은 경우 이 섹션 omit.

---

## Output Templates

### Variant A: Stand-alone 호출 (채팅 응답)

전체 분석 결과를 markdown으로 출력. 채팅 응답이므로 **파이프 테이블 사용 OK**.

````markdown
# {종목명} ({TICKER}) — Earnings Call Pulse

**Transcripts 분석**: T0 = {date_T0}, T-1 = {date_T-1}, T-2 = {date_T-2}
**발표자**: {CEO 이름} (CEO), {CFO 이름} (CFO)
**전체 word count**: T0 ~{N}k, T-1 ~{N}k, T-2 ~{N}k

## ★ T0 Standalone 핵심 정리

(3-quarter 비교와 별개로 T0 자체의 핵심 메시지·인용·인사이트)

### 핵심 메시지 5-7가지
1. {T0 컨콜의 가장 강한 메시지 한 줄 + 1-2줄 부연}
2. ...

### 직접 인용 4-5가지 (verbatim, 보존 가치 높음)
> **CEO 이름 on {주제}**: "{원문 인용 1-2 문장}"
> **CFO 이름 on {주제}**: "{원문 인용}"
...

### 새로 announce된 액션 / 가이던스
- 가이던스 raise/maintain/cut + 구체 수치
- 신규 계약·partnership
- M&A·자본 action
- 기타 forward-looking 발언

### 분석사 Q&A 핵심 (2-3가지)
1. **({분석사}) "{질문 요지}"** → 회사 답변 요지
...

### T0 컨콜에서 읽히는 핵심 인사이트 (Claude 해석)
{이 컨콜의 진짜 alpha. 3-quarter 비교에서 보이는 narrative pivot. 200-400자.}

### ★ T0 전문 임베드 (FULL VERBATIM, 접을 수 있게)

WebFetch로 T0 transcript를 prepared remarks (CEO + CFO) + analyst Q&A 두 파트로 나누어 verbatim 가져온 후, `<details>` 블록으로 통째 임베드. 핵심 alpha 시그널 문장에 `==하이라이트==` (Obsidian 형광펜) 적용.

```html
<details>
<summary><b>★ {분기} Earnings Call 전문 (verbatim, 핵심 문장 하이라이트). 펼쳐서 보기.</b></summary>

**출처**: [fool.com transcript]({T0_URL}) | 발표일 {date}

---

### Operator Intro
{IR 담당자 intro 전문}

---

### CEO {이름} — Prepared Remarks
{CEO 발언 verbatim 전체. 핵심 문장은 ==하이라이트== 또는 ==**볼드+하이라이트**==}

---

### CFO {이름} — Prepared Remarks
{CFO 발언 verbatim 전체. 정량 가이던스·실적 수치 ==하이라이트==}

---

### Analyst Q&A
#### Q1 — {분석사 + 분석사 이름}
**{이름}**: {질문 verbatim}
**CEO**: {답변 verbatim, 핵심 ==하이라이트==}
... (모든 Q&A 동일)

</details>
```

**하이라이트 대상 (alpha 시그널 우선순위)**:
1. 새로운 가이던스 수치 (revenue, OPM, EPS, cash 등 raise/cut)
2. CEO/CFO의 "conviction" 표현 ("we are not constrained", "first time in history", "highest conviction" 등)
3. Customer 명시적 인용 ("Oracle pivoted to...", "majority of backlog from..." 등)
4. Capacity 또는 scale milestone ("5 GW annual", "10x manufacturing" 등)
5. Forward-looking 시그널 ("secular demand for many years", "inference > training" 등)
6. 경쟁 우위 명시 ("we don't compare with engines and turbines, apples and oranges" 등)
7. 분석사 우려에 대한 직답 (회피 vs 직답 구분)

**원칙**: 한 transcript 당 15-25개 ==하이라이트== 적정. 너무 많으면 (50+) 가치 희석. 너무 적으면 (<10) signal 누락.

## 1. 이번 컨콜의 새 강조 (T0 Surge)

### {주제 1} ★ 가장 강한 시그널
T0에서 처음 강조 (T-1, T-2에서는 한 번도/한두 번 짧게 언급).
- 핵심 인용 (T0): "{CEO/CFO 원문 인용 1-2 문장}"
- 의미: {왜 이게 alpha인가, 한 줄 해석}

### {주제 2}
...

## 2. 톤 강도 변화

| 주제 | T-2 ({date}) | T-1 ({date}) | T0 ({date}) | 변화 |
|---|---|---|---|---|
| {주제 A} | "{phrase}" | "{phrase}" | "{phrase}" | ↗↗ |
| {주제 B} | — | "{phrase}" | "{phrase}" | ↗ |

## 3. 소멸한 Narrative

- **{주제 X}**: T-2, T-1에서 핵심 강조 (각 분기 N회 이상 언급) → T0에서 1회 미만.
  - 해석: {회피 / deprioritize / 완료 / 컨텍스트 변화}

## 4. Analyst Q&A 우려 포인트

{1단락 — 분석사들이 집요하게 묻는 1-2가지 주제 + 경영진 답변 톤 평가 (직답/우회)}

## 5. 한국 포트폴리오 cross-reference

{1-2 단락 — 발견한 시그널이 사용자의 한국 보유 종목 thesis에 미치는 영향. 관련 종목 wikilink 형식 포함, 예: [[project_skt_guru_analysis]]}

---
> Analysis basis: fool.com transcripts (free, full text). Source URLs: {T0_url}, {T-1_url}, {T-2_url}.
````

### Variant B: guru-investment subcall (저장 .md용 섹션)

위 Variant A의 압축 버전 (~2-3K chars). guru-investment 풀 리포트의 Part 1.4 (분기별 재무) **직후**, Part 1.5 (18개월 공시) **직전**에 "## Part 1.4b: Earnings Call Pulse" 섹션으로 삽입.

**압축 규칙**:
- Surge: Top 3만 (Stand-alone은 5)
- 톤 강도 표는 **HTML table** 사용 (저장 .md 파일이므로 pipe table 금지 — 사용자 양식 룰)
- 사용자 양식 검증 grep 룰 적용 (저장 전 0건 확인)

**HTML table 변환 예시**:
```html
<table>
<thead>
<tr><th>주제</th><th>T-2 ({date})</th><th>T-1 ({date})</th><th>T0 ({date})</th><th>변화</th></tr>
</thead>
<tbody>
<tr><td>{주제 A}</td><td>"{phrase}"</td><td>"{phrase}"</td><td>"{phrase}"</td><td>↗↗</td></tr>
</tbody>
</table>
```

---

## Fallback Handling

<table>
<thead>
<tr><th>상황</th><th>대응</th></tr>
</thead>
<tbody>
<tr><td>IPO 첫 분기 종목 (transcript 1개만 있음)</td><td>"T0 단독 분석 — 갑자기 강조 dimension 적용 불가" 명시 후 가용 분석 수행. Dimension 2, 3 skip.</td></tr>
<tr><td>fool.com 미커버 (very small cap)</td><td>WebSearch로 seekingalpha headline 시도. 실패 시 사용자에게 회사 IR webcast URL 요청.</td></tr>
<tr><td>사용자가 fool.com URL 직접 제공</td><td>그 URL을 T0로 우선 사용. T-1, T-2는 site:fool.com 검색으로 보충.</td></tr>
<tr><td>WebFetch 3회 retry 후 실패</td><td>URL을 사용자에게 보여주고 본문 직접 paste 요청.</td></tr>
<tr><td>분기 1-2개만 가용</td><td>가용한 만큼만 분석. T0 단독 또는 T0-T-1 비교 only.</td></tr>
<tr><td>한국 종목 ticker 입력</td><td>"transcript-pulse는 v1에서 미장 only 지원. 한국 종목은 v2에서 확장 예정." 메시지 출력 후 종료.</td></tr>
</tbody>
</table>

---

## 검증 규칙 (저장 .md 출력 시)

guru-investment subcall로 .md에 통합될 때 반드시 통과해야 할 grep:

```bash
# 1) 파이프 테이블 금지 (코드블록 제외)
grep -cE '^\|.*\|.*\|$' <file>
# 결과: 0건 기대

# 2) bold+한글조사 right-flanking 위반 금지
grep -cE '\*\*[^*]*["'"'"')\].,!?;:”’」』》]\*\*[가-힣]' <file>
# 결과: 0건 기대
```

Stand-alone 채팅 응답은 파이프 테이블 OK (사용자의 `feedback_chat_vs_md_tables.md` 룰).

---

## Important Guidelines

- **T0 standalone 정리 필수**: 3-quarter 비교 (Surge/Tone Shift/Faded) 전에 가장 최신 transcript 자체의 핵심 메시지·직접 인용·신규 액션·분석사 Q&A·Claude 해석을 별도 섹션으로 정리. 이것이 가장 가치있는 alpha이므로 항상 첫 섹션에 위치.
- **T0 전문 임베드 필수 (`<details>` + `==하이라이트==`)**: T0 standalone 정리 직후 가장 최신 transcript 전문을 verbatim으로 `<details>` 접기 블록에 통째 삽입. WebFetch를 2회 호출 (prepared remarks + Q&A 분리)로 풀 추출. 핵심 alpha 시그널 문장 15-25개에 Obsidian `==하이라이트==` 적용 (가이던스 수치·CEO conviction 표현·customer 명시 인용·capacity milestone·forward-looking 시그널·경쟁 우위·Q&A 직답 우선). 사용자가 원문을 직접 확인할 수 있도록 보존 + 핵심만 스캔 가능.
- **인용은 verbatim**: 의역 금지. 경영진의 정확한 phrase를 보존.
- **3 dimension은 동등하게 다룸**: Surge만 보고 끝나지 않기. Faded와 Tone Shift도 alpha source.
- **한국 cross-reference는 반드시 수행**: 사용자가 한국 종목 보유자이므로 미장 시그널을 한국 thesis와 연결하는 게 핵심 가치.
- **결과는 매우 절제된 톤으로**: hype 표현 금지. 인용구 + 데이터 + 한 줄 해석 패턴 유지.
- **Source URL 명시 의무**: 모든 출력 하단에 3개 transcript URL 명시.
- **CEO 교체·CFO 교체 분기 주의**: 새 발표자의 첫 컨콜은 baseline이 약함. T0가 신규 CEO 첫 분기인 경우 명시.

---

## Disclaimer

본 분석은 교육·분석 목적이며 투자 권유가 아닙니다. fool.com 무료 transcript를 1차 소스로 사용. 경영진 발언의 해석은 Claude의 추론이며 사실 자체와 구분됩니다.
