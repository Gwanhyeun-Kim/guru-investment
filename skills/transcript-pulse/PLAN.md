# transcript-pulse + guru-investment Update — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 미장 종목 earnings call transcript 3분기 자동 분석 신규 skill 작성 + guru-investment에 transcript-pulse subcall 통합 + 모든 분석에 압축 투자검토 보고서 자동 생성 추가.

**Architecture:** transcript-pulse는 stand-alone skill로 작성하고 guru-investment에서 미장 종목 분석 시 subcall 트리거. guru-investment는 모든 분석 종료 시 풀 리포트 + 압축 투자검토 보고서 (.md) 양쪽 생성. 사용자 환경은 markdown-driven skill 시스템이며 코드 컴파일·테스트 없음 — verification은 grep 룰 + 수동 walkthrough.

**Tech Stack:** Markdown SKILL.md 정의, WebSearch + WebFetch tools, Bash grep 검증, Claude의 자체 컨텍스트 처리. 별도 Python/실행 코드 작성 없음.

**관련 design:** `~/.claude/skills/transcript-pulse/DESIGN.md`

---

## File Structure

신규/수정 파일 목록:

```
신규:
  ~/.claude/skills/transcript-pulse/SKILL.md                     (~6K chars)
  ~/.claude/projects/-Users-{username}/memory/project_transcript_pulse_skill.md

수정:
  ~/.claude/skills/guru-investment/SKILL.md
    - Step 2.5와 Step 2.6 사이 "Step 2.5b: Earnings Call Pulse (미장 only)" 삽입
    - "Step 3: Structure the output" 끝 부분에 "압축 투자검토 보고서 자동 생성" 추가
    - "Important Guidelines" 섹션 끝에 보고서 자동 생성 규칙 명시
  ~/.claude/projects/-Users-{username}/memory/MEMORY.md
    - project_transcript_pulse_skill.md 인덱스 한 줄 추가
```

저장 경로 (시너지):
- Primary: `~/.claude/skills/transcript-pulse/` (SKILL.md, DESIGN.md, PLAN.md 모두)
- Archive 동기화: `~/Desktop/Claude/skill-designs/` (DESIGN.md, PLAN.md만)

---

## Phase 1 — `transcript-pulse` Skill 작성

### Task 1: SKILL.md 헤더 + frontmatter + 트리거 정의

**Files:**
- Create: `~/.claude/skills/transcript-pulse/SKILL.md`

- [ ] **Step 1: 파일 생성 + YAML frontmatter + 트리거 keywords**

```markdown
---
name: transcript-pulse
description: 미장 상장사 earnings call transcript를 최근 3분기 자동 수집·비교하여 "이번 컨콜에서 갑자기 강조된 것"과 "톤·뉘앙스 변화"를 추출하는 스킬. fool.com transcript를 1차 소스로 사용. "transcript pulse", "{TICKER} 컨콜 톤", "{TICKER} earnings call 분석", "/transcript-pulse {TICKER}" 등 트리거 또는 사용자가 fool.com URL 붙여넣기. guru-investment 미장 종목 분석 시 자동 subcall 됨.
---

# Transcript Pulse — Earnings Call Nuance Tracker

지난 2-3개 분기의 earnings call transcript를 동시에 컨텍스트에 두고, 가장 최근 transcript에서 **갑자기 강조된 주제 / 톤 강도 변화 / 사라진 narrative**를 추출하는 스킬.

**핵심 가치**: GAAP 숫자가 못 잡는 alpha의 진짜 원천은 경영진이 같은 주제를 분기마다 어떻게 다르게 말하는지에 있다. 예: LB Q1 2026 "we have higher conviction than ever that West Texas is on its way to becoming the next major data center hub" — 이전 분기들의 미온적 표현과 비교 시 명백한 narrative pivot.

## Scope

- **지원**: 미장 상장사 (NYSE, NASDAQ). fool.com 커버 대상.
- **미지원**: 한국 종목 (한국 transcript 컬쳐 다르고 fool.com 미커버). v2에서 확장.
```

- [ ] **Step 2: Verify frontmatter parsable**

Run: `head -5 ~/.claude/skills/transcript-pulse/SKILL.md`
Expected: name, description, triggers 모두 포함

- [ ] **Step 3: 다음 task로**

---

### Task 2: SKILL.md "Step 1: URL Discovery" 섹션

**Files:**
- Modify: `~/.claude/skills/transcript-pulse/SKILL.md` (append)

- [ ] **Step 1: Step 1 섹션 작성**

```markdown
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

응답에서 URL 5-10개 추출 후 발행일 desc 정렬, **최근 3개** 선택. T0 = 가장 최근, T-1, T-2 = baseline.

**Fallback path 1 — yfinance earnings_dates**:
yfinance `t.earnings_dates`에서 실제 발표일 (분기별 4개) 확인 후 fool.com URL 직접 시도.

**Fallback path 2 — 사용자 직접 제공**:
사용자가 fool.com URL을 본문에 붙여넣은 경우 그것을 T0로 사용. T-1, T-2는 site: 검색으로 보충.

**Fallback path 3 — 모든 경로 실패**:
"fool.com에서 {ticker} transcript를 찾을 수 없습니다. 회사 IR 페이지의 webcast/transcript URL을 제공해주세요" 메시지 출력 후 사용자 입력 대기.
```

- [ ] **Step 2: Verify**

Run: `grep -c "Step 1: Transcript URL Discovery" ~/.claude/skills/transcript-pulse/SKILL.md`
Expected: 1

---

### Task 3: SKILL.md "Step 2: Body Extraction"

**Files:**
- Modify: `~/.claude/skills/transcript-pulse/SKILL.md` (append)

- [ ] **Step 1: Step 2 섹션 작성**

```markdown
### Step 2: Body Extraction

WebFetch 호출 (3개 transcript 각각):

```
WebFetch(url=<transcript_url>, prompt="Extract the FULL earnings call transcript verbatim, including: (1) introduction/operator remarks, (2) prepared remarks from CEO and CFO with their names as section headers, (3) full analyst Q&A with analyst names and firms. Preserve all phrases, do NOT summarize. Output as plain text with speaker labels.")
```

각 transcript 본문 6-10K words 추출. 3개 합계 ~24-30K words → Claude context 내 한 번에 처리 가능.

**Edge case**: WebFetch가 paywall/cookie/JS 이슈로 본문 못 가져온 경우 (3회 retry):
- URL을 사용자에게 보여주고 "fool.com 페이지를 직접 열어 본문을 paste해주세요" 요청.
- 다른 transcript는 정상 수집 시 부분 분석 진행.
```

---

### Task 4: SKILL.md "Step 3: 3-Dimension Analysis"

**Files:**
- Modify: `~/.claude/skills/transcript-pulse/SKILL.md` (append)

- [ ] **Step 1: Step 3 섹션 작성 — Dimension 1 (Surge)**

```markdown
### Step 3: 3-Dimension Analysis

T0 = 가장 최근 transcript, T-1, T-2 = baseline.

#### Dimension 1: "갑자기 강조 (Surge in T0)"

T-1, T-2에서 한 번도 안 나왔거나 한두 번 짧게 언급된 주제가 T0에서 강조·반복·확신.

**판단 방식 (Claude의 의미 기반 분석)**:
1. T0를 먼저 읽고 경영진이 반복적으로 강조하는 주제 5-7개 추출 (단순 키워드 빈도가 아니라 의미적 emphasis)
2. 각 주제에 대해 T-1, T-2에서 동일/유사 주제가 어떻게 다루어졌는지 확인
3. "T0에서 처음 등장" 또는 "T-1,T-2에서 미온적 → T0에서 확신" 패턴 식별
4. 각 surge item에 대해 T0의 가장 강한 인용구 1-2개 직접 발췌 (의역 금지)

출력: Top 3-5 surge items, 각각 직접 인용구 포함.

#### Dimension 2: "톤 강도 변화 (Tone Shift on same topic)"

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

출력: 톤 변화가 있는 주제 2-5개, 각각 T-2 → T-1 → T0 phrase contrast.

#### Dimension 3: "소멸한 narrative (Faded from T0)"

T-1, T-2에서 강조됐는데 T0에서 빠진 것.

**판단 방식**:
1. T-1, T-2에서 반복 강조됐던 주제 식별
2. T0에서 그 주제가 한 번도 또는 매우 짧게 언급되었는지 확인
3. 해석: 회피 시그널 / deprioritize / 완료된 마일스톤 / 컨텍스트 변화

출력: 소멸한 narrative 1-3개 + 각각의 해석.

#### Bonus Dimension: Analyst Q&A 우려 포인트

분석사들이 (여러 명이 또는 같은 분석사가 follow-up으로) 집요하게 묻는 1-2가지 주제. 경영진의 답변이 직답인지 우회인지 평가.

출력: 1단락 짧게.
```

---

### Task 5: SKILL.md "Step 4: Korea Cross-Reference"

**Files:**
- Modify: `~/.claude/skills/transcript-pulse/SKILL.md` (append)

- [ ] **Step 1: Step 4 섹션 작성**

```markdown
### Step 4: Korea Portfolio Cross-Reference

사용자 메모리의 한국 보유/관심 종목 분석 결과를 자동 스캔하여 미장 시그널이 한국 종목 thesis에 미치는 영향 식별.

**스캔 대상**:
```bash
ls ~/.claude/projects/-Users-{username}/memory/project_*_guru_analysis.md
```

(사용자가 별도로 저장한 한국 종목 thesis 노트들이 있다면 자동 grep — 본 skill은 종목 리스트를 하드코딩하지 않음)

**판단 방식**:
1. 미장 종목 transcript에서 발견한 시그널의 핵심 키워드 추출 (예: "Permian data center", "AI capex acceleration", "Hormuz oil supply", "AI infrastructure power")
2. 각 한국 종목 메모리 파일을 grep으로 관련 키워드 검색
3. 관련성 확인된 종목에 대해 1-2 문장으로 cross-impact 서술

**출력**: "한국 포트폴리오 implications" 섹션 1-2 단락. 관련 한국 종목이 없으면 명시적으로 "직접적 cross-impact 없음" 표시.
```

---

### Task 6: SKILL.md "Output Templates" — Stand-alone + Subcall variants

**Files:**
- Modify: `~/.claude/skills/transcript-pulse/SKILL.md` (append)

- [ ] **Step 1: Output template 섹션 작성**

```markdown
## Output Templates

### Variant A: Stand-alone 호출 (채팅 응답)

전체 분석 결과를 markdown으로 출력.

\`\`\`markdown
# {종목명} ({TICKER}) — Earnings Call Pulse

**Transcripts 분석**: T0 = {date_T0}, T-1 = {date_T-1}, T-2 = {date_T-2}
**발표자**: {CEO 이름} (CEO), {CFO 이름} (CFO)
**전체 word count**: T0 ~{N}k, T-1 ~{N}k, T-2 ~{N}k

## 1. 이번 컨콜의 새 강조 (T0 Surge)

### {주제 1} ★ 가장 강한 시그널
T0에서 처음 강조 (T-1, T-2에서는 한 번도/한두 번 짧게 언급).
- 핵심 인용 (T0): "{CEO/CFO 원문 인용 1-2 문장}"
- 의미: {왜 이게 alpha인가, 한 줄 해석}

### {주제 2}
...

## 2. 톤 강도 변화

(채팅 응답에서는 pipe table 사용 가능)

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

{1-2 단락 — 발견한 시그널이 사용자의 한국 보유 종목 thesis에 미치는 영향. 관련 종목 wikilink 형식 포함, 예: [[프로젝트_skt_guru_analysis]]}

---
> Analysis basis: fool.com transcripts (free, full text). Source URLs: {T0_url}, {T-1_url}, {T-2_url}.
\`\`\`

### Variant B: guru-investment subcall (markdown section만 반환)

위 Variant A의 압축 버전 (~2-3K chars). guru-investment 풀 리포트의 Part 1.4 (분기별 재무) 직후, Part 1.5 (18개월 공시) 직전에 "## Part 1.4b: Earnings Call Pulse" 섹션으로 삽입.

압축 규칙:
- Surge: Top 3만 (Stand-alone은 5)
- 톤 강도: HTML table 사용 (저장 .md 파일이므로 pipe table 금지)
- 사용자 양식 검증 grep 룰 적용 (저장 전 0건 확인)

저장 .md 파일이므로 HTML table 변환 필요:
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
```

---

### Task 7: SKILL.md "Fallback Handling" 표

**Files:**
- Modify: `~/.claude/skills/transcript-pulse/SKILL.md` (append)

- [ ] **Step 1: Fallback 표 작성 (HTML, 저장 .md용)**

```markdown
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

## 검증 규칙 (저장 .md 출력 시)

guru-investment subcall로 .md에 통합될 때 반드시 통과해야 할 grep:
1. `grep -cE '^\|.*\|.*\|$' <file>` → 0건 (파이프 테이블 금지, 코드블록 제외)
2. `grep -cE '\*\*[^*\n]{1,200}["'"'"')\].,!?;:”’」』》]\*\*[가-힣]' <file>` → 0건 (bold+한글조사 right-flanking 위반 금지)

Stand-alone 채팅 응답은 파이프 테이블 OK (사용자의 feedback_chat_vs_md_tables.md 룰).
```

---

### Task 8: SKILL.md 마무리 (Important Guidelines + Disclaimer)

**Files:**
- Modify: `~/.claude/skills/transcript-pulse/SKILL.md` (append)

- [ ] **Step 1: 마무리 섹션 작성**

```markdown
## Important Guidelines

- **인용은 verbatim**: 의역 금지. 경영진의 정확한 phrase를 보존.
- **3 dimension은 동등하게 다룸**: Surge만 보고 끝나지 않기. Faded와 Tone Shift도 alpha source.
- **한국 cross-reference는 반드시 수행**: 사용자가 한국 종목 보유자이므로 미장 시그널을 한국 thesis와 연결하는 게 핵심 가치.
- **결과는 매우 절제된 톤으로**: hype 표현 금지. 인용구 + 데이터 + 한 줄 해석 패턴 유지.
- **Source URL 명시 의무**: 모든 출력 하단에 3개 transcript URL 명시.

## Disclaimer

본 분석은 교육·분석 목적이며 투자 권유가 아닙니다. fool.com 무료 transcript를 1차 소스로 사용. 경영진 발언의 해석은 Claude의 추론이며 사실 자체와 구분됩니다.
```

- [ ] **Step 2: 전체 SKILL.md 검증**

Run:
```bash
echo "=== Pipe table check (코드블록 외 0건 기대) ==="
grep -cE '^\|.*\|.*\|$' ~/.claude/skills/transcript-pulse/SKILL.md
echo "=== Bold+Korean check (0건 기대) ==="
grep -cE '\*\*[^*]*["'"'"')\].,!?;:”’」』》]\*\*[가-힣]' ~/.claude/skills/transcript-pulse/SKILL.md
echo "=== Char count ==="
wc -m ~/.claude/skills/transcript-pulse/SKILL.md
```

Expected:
- Pipe table: 코드블록 안 template만 (수 개), 외부 0건
- Bold+Korean: 0
- Char count: 5K-7K

---

### Task 9: 수동 verification — AAPL stand-alone mental walkthrough

- [ ] **Step 1: SKILL.md 전체 다시 읽기**

- [ ] **Step 2: AAPL stand-alone 호출 시뮬레이션**

다음 시나리오를 mental walkthrough:
1. 사용자: "AAPL transcript pulse"
2. Skill 트리거됨
3. Step 1 — WebSearch "site:fool.com AAPL earnings transcript"
4. 응답에서 최근 3개 URL 추출
5. Step 2 — WebFetch × 3
6. Step 3 — 3 dimensions 분석
7. Step 4 — 한국 cross-reference (AAPL 시그널 중 어떤 게 한국 종목 thesis에 영향 줄지)
8. Variant A 출력

각 단계에서 SKILL.md에 명확한 지침이 있는지 확인. 빠진 부분 있으면 Task 1-8 해당 부분 수정.

---

## Phase 2 — `guru-investment` Skill 업데이트

### Task 10: guru-investment SKILL.md — Step 2.5b 삽입

**Files:**
- Modify: `~/.claude/skills/guru-investment/SKILL.md`

- [ ] **Step 1: 현재 Step 2.5와 2.6 위치 확인**

Run: `grep -n "^### Step 2\." ~/.claude/skills/guru-investment/SKILL.md`
Expected: Step 2, Step 2.5, Step 2.6, Step 2.7 등 발견

- [ ] **Step 2: Step 2.5와 2.6 사이에 Step 2.5b 삽입**

Step 2.6 직전에 다음 섹션 삽입:

```markdown
### Step 2.5b: Earnings Call Pulse (미장 only)

**미국 상장사 분석 시 필수.** 한국 종목 분석 시 skip.

**조건**: SEC EDGAR CIK 매핑이 성공한 미장 종목에 한해 실행. 한국 종목 (KOSPI/KOSDAQ)은 transcript 컬쳐가 다르고 fool.com 미커버이므로 이 단계를 건너뛴다.

**동작**: `transcript-pulse` skill을 subcall 호출.

```
Skill(skill="transcript-pulse", args="{ticker} --subcall-mode")
```

또는 직접 워크플로우 실행:
1. WebSearch "site:fool.com {ticker} earnings transcript"
2. 최근 3개 transcript URL 추출
3. WebFetch × 3 본문 가져오기
4. 3-Dimension 분석 (Surge / Tone Shift / Faded) + Analyst Q&A 우려 + 한국 cross-reference
5. Markdown section 생성 ("## Part 1.4b: Earnings Call Pulse")
6. 본 섹션을 풀 리포트의 Part 1.4 (분기별 재무) 직후, Part 1.5 (18개월 공시 타임라인) 직전에 삽입

자세한 워크플로우는 `~/.claude/skills/transcript-pulse/SKILL.md` 참조.

**중요**: Subcall mode일 때는 HTML table 사용 (저장 .md용). Stand-alone 채팅 응답은 pipe table OK.
```

- [ ] **Step 3: Verify insertion**

Run: `grep -n "Step 2.5b" ~/.claude/skills/guru-investment/SKILL.md`
Expected: 1 line found

---

### Task 11: guru-investment SKILL.md — Step 3 끝에 압축 보고서 생성 규칙 추가

**Files:**
- Modify: `~/.claude/skills/guru-investment/SKILL.md`

- [ ] **Step 1: 현재 Step 3 끝 위치 확인**

Run: `grep -n "^### Step" ~/.claude/skills/guru-investment/SKILL.md`

- [ ] **Step 2: Step 3 끝부분 (또는 Step 4 직전)에 압축 보고서 섹션 추가**

```markdown
### Step 3.5: 압축 투자검토 보고서 자동 생성 (필수, 모든 분석)

guru-investment의 풀 리포트 작성 직후, **항상** 별도 압축 투자검토 보고서를 .md로 추가 생성한다. 한국 종목·미장 종목 모두 적용.

**파일명**: `{종목명_or_TICKER}_투자검토_{YYYYMMDD}.md`

**저장 경로**: 풀 리포트와 동일 폴더 (Desktop + Obsidian 양쪽)
- `~/Desktop/Claude/Investment Research/{종목명 or TICKER}/`
- Obsidian `Investment Research/{KR_stocks or US Stocks}/{종목명 or TICKER}/`

**분량**: 3-5K chars (1-2 페이지). CEO·투자집행자가 30초~1분에 읽고 결정.

**Verdict 책임**: Claude가 BUY/HOLD/SELL/AVOID 결정. 5인 구루 가중 평균 + transcript pulse 시그널을 종합.

**Template (저장 .md, HTML table 사용)**:

\`\`\`markdown
---
tags:
  - investment
  - investment/{KR 또는 US}
  - investment/{종목명}
  - investment/review
---

# {종목명} ({TICKER}) — 투자검토 보고서

**작성일**: {YYYY-MM-DD}
**현재가**: ${price} / 시총: ${marketCap}
**풀 리포트**: [[{종목명}_멀티구루_{YYYYMMDD}]]

## Verdict

**[BUY / HOLD / SELL / AVOID]** — 확신도: {High / Medium / Low}
권장 비중: {X-Y%} of portfolio
진입 가격대: ${entry_range}

## 한 줄 thesis

{왜 이 종목을 사야/말아야 하나, 한 문장으로 압축}

## 3 핵심 근거

1. **{포인트 1 핵심 키워드}** — {30-50자 데이터·사실 근거}
2. **{포인트 2}** — {30-50자 근거}
3. **{포인트 3}** — {30-50자 근거}

## Earnings Call Pulse 알파 (미장만)

{transcript-pulse 분석에서 가장 alpha-rich 발견 1-2개. T0 인용구 직접 포함. 총 ~300자.}

## 가장 큰 리스크 (단 1개)

**{리스크 한 줄}** — 발생 확률 {X%}.
대응: {매도 / 관망 / 비중 축소 트리거 조건}

## 포지션 운영

- 초기 진입: ${entry} × {n}%
- 추가 매수: ${level} 지지 시 +{Y}%
- 매도 트리거: {조건}
- 관망 트리거: {조건}

## 한국 포트폴리오 cross-reference

{미장 분석 시: 한국 보유 종목에 미치는 영향 1-2 단락}
{한국 분석 시: 같은 산업 미국 종목과의 비교 1-2 단락}

---
> 본 보고서는 풀 리포트의 압축본. 상세 데이터·구루별 분석은 풀 리포트 참조.
> Claude verdict = 5인 구루 가중 평균 + transcript pulse signal 종합.
> 본 분석은 교육·분석 목적이며 투자 권유가 아닙니다.
\`\`\`

**검증**: 저장 전 grep 셀프 검증 필수:
- `^\|.*\|.*\|$` → 0건 (파이프 테이블 금지)
- `\*\*[^*]*["')\].,!?;:”’」』》]\*\*[가-힣]` → 0건 (bold+한글조사 right-flanking 위반 금지)
```

- [ ] **Step 3: Verify**

Run: `grep -n "Step 3.5" ~/.claude/skills/guru-investment/SKILL.md`
Expected: 1 line found

---

### Task 12: guru-investment SKILL.md — Important Guidelines 섹션 업데이트

**Files:**
- Modify: `~/.claude/skills/guru-investment/SKILL.md`

- [ ] **Step 1: 현재 "Important Guidelines" 섹션 끝 부분 확인**

- [ ] **Step 2: 두 가지 새 guideline 추가**

```markdown
- **Earnings Call Pulse (미장만)**: 미국 종목 분석 시 Step 2.5b에서 transcript-pulse skill subcall 또는 직접 워크플로우 실행. 결과를 풀 리포트의 Part 1.4b 섹션으로 통합. 한국 종목은 skip.
- **압축 투자검토 보고서 (필수, 모든 분석)**: 풀 리포트 작성 후 반드시 별도 `{종목명}_투자검토_{YYYYMMDD}.md`를 동일 폴더에 추가 생성. Verdict는 Claude가 결정. 1-2 페이지 (~3-5K chars). 사용자가 CEO·투자집행자 입장에서 30초-1분에 읽고 판단할 수 있는 thesis 설득 페이퍼.
```

---

## Phase 3 — Memory & Final Verification

### Task 13: 메모리 파일 작성

**Files:**
- Create: `~/.claude/projects/-Users-{username}/memory/project_transcript_pulse_skill.md`

- [ ] **Step 1: 메모리 파일 작성**

```markdown
---
name: transcript-pulse 스킬
description: 미장 종목 earnings call transcript 3분기 자동 비교 신규 스킬 + guru-investment 압축 투자검토 보고서 자동 생성 (2026-05-11 작성)
type: project
---

transcript-pulse 신규 skill 작성 (2026-05-11).

**핵심 기능**:
- 미장 종목 ticker 입력 → fool.com에서 최근 3개 분기 transcript 자동 수집
- 3-Dimension 분석: (1) Surge in T0 (이번 분기 갑자기 강조), (2) Tone Shift (동일 주제 phrase 강도 변화), (3) Faded narrative (사라진 주제)
- 한국 포트폴리오 cross-reference: 사용자 메모리의 한국 종목 thesis에 미치는 영향 자동 식별
- guru-investment에서 미장 분석 시 자동 subcall (Part 1.4b 섹션 통합)

**guru-investment 영구 변경**:
- Step 2.5b 추가: transcript-pulse subcall (미장 only)
- Step 3.5 추가: 모든 분석에 압축 투자검토 보고서 (.md) 자동 생성
- 압축 보고서 verdict는 Claude가 결정 (사용자 명시 요구)

**파일 위치**:
- ~/.claude/skills/transcript-pulse/SKILL.md (신규)
- ~/.claude/skills/transcript-pulse/DESIGN.md (설계 문서)
- ~/.claude/skills/transcript-pulse/PLAN.md (구현 계획)
- ~/.claude/skills/guru-investment/SKILL.md (수정)

**한계**:
- v1: 미장 only (fool.com). 한국 종목 transcript는 v2에서 확장.
- IPO 첫 분기 종목은 Dimension 2, 3 적용 불가 (baseline 없음)
- fool.com 미커버 small cap은 사용자에게 IR URL 요청

**참조 패턴**: guru-13f skill의 SEC EDGAR 3분기 비교 + Korean cross-reference 패턴과 유사 구조.
```

---

### Task 14: MEMORY.md 인덱스 업데이트

**Files:**
- Modify: `~/.claude/projects/-Users-{username}/memory/MEMORY.md`

- [ ] **Step 1: 인덱스 한 줄 추가**

마지막 항목 (`project_guru_13f_skill.md` 뒤) 추가:

```markdown
- [project_transcript_pulse_skill.md](project_transcript_pulse_skill.md): transcript-pulse 신규 스킬 (2026-05-11) — 미장 종목 fool.com 컨콜 3분기 자동 비교 + guru-investment에 압축 투자검토 보고서 자동 생성 영구 추가. 미장만 v1, 한국 v2 확장 예정.
```

---

### Task 15: 최종 End-to-End Verification

- [ ] **Step 1: 두 SKILL.md 파일 모두 grep 검증**

```bash
for f in ~/.claude/skills/transcript-pulse/SKILL.md ~/.claude/skills/guru-investment/SKILL.md; do
  echo "=== $f ==="
  echo "Char count: $(wc -m < $f)"
  echo "Pipe tables: $(grep -cE '^\|.*\|.*\|$' $f)"
  echo "Bold+Korean violations: $(grep -cE '\*\*[^*]*["'"'"')\].,!?;:”’」』》]\*\*[가-힣]' $f)"
done
```

- [ ] **Step 2: Skill registry 검증**

Run: `ls ~/.claude/skills/transcript-pulse/`
Expected: SKILL.md, DESIGN.md, PLAN.md 모두 존재

- [ ] **Step 3: PLAN.md를 Desktop archive에도 동기화**

Run: `cp ~/.claude/skills/transcript-pulse/PLAN.md "~/Desktop/skill-designs/2026-05-11-transcript-pulse-plan.md"`

- [ ] **Step 4: Mental smoke test — LB 시나리오**

다음을 mental walkthrough (실제 호출 X, design 검증만):
- 시나리오 A: 사용자 "LB transcript pulse" → transcript-pulse skill stand-alone → fool.com URL 3개 (LB Q3 2025, Q4 2025, Q1 2026) → WebFetch × 3 → 3 dimensions 분석 → Korea cross-ref → markdown 출력
- 시나리오 B: 사용자 "guru investment LB" → guru-investment 트리거 → Step 2.5b에서 transcript-pulse subcall → 결과를 Part 1.4b로 통합 → Step 3.5에서 압축 투자검토 보고서 자동 생성 → 풀 리포트 + 압축 보고서 양쪽 저장

각 단계에서 SKILL.md에 명확한 지침이 있는지 확인. 빠진 부분이 있으면 Phase 1 또는 2의 해당 task로 돌아가 수정.

---

## Success Criteria (재확인)

- [ ] `~/.claude/skills/transcript-pulse/SKILL.md` 존재, frontmatter 정확, 트리거 키워드 명시
- [ ] SKILL.md에 Step 1-4 + Output Templates + Fallback + Important Guidelines 모두 있음
- [ ] `guru-investment/SKILL.md`에 Step 2.5b 추가됨 (transcript-pulse subcall 통합)
- [ ] `guru-investment/SKILL.md`에 Step 3.5 추가됨 (압축 투자검토 보고서)
- [ ] 메모리 파일 + MEMORY.md 인덱스 업데이트
- [ ] 모든 .md 파일 grep 검증 통과 (pipe table 0, bold+Korean 0)

## Self-Review (구현 후)

1. **Spec coverage**: DESIGN.md의 모든 섹션이 SKILL.md에 반영됐는지 확인
2. **Type consistency**: T0/T-1/T-2 표기 일관, Dimension 명칭 일관 (Surge/Tone Shift/Faded)
3. **Placeholder scan**: TBD/TODO 0건
4. **Cross-file references**: guru-investment의 Step 2.5b가 transcript-pulse skill 경로 정확히 가리키는지

이슈 발견 시 inline 수정.
