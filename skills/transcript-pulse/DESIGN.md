# transcript-pulse — Design Document

**작성일**: 2026-05-11
**상태**: Design (구현 전)
**관련 skill**: 신규 `transcript-pulse` + 기존 `guru-investment` 업데이트

---

## 1. Background

guru-investment skill로 미장 종목 (AAPL, LB) 분석을 수행하면서 **earnings call transcript가 GAAP 숫자로는 잡히지 않는 alpha의 핵심 원천**임을 확인. 특히 LB Q1 2026 컨콜에서 경영진이 "we have higher conviction than ever that West Texas is on its way to becoming the next major data center hub"라고 발언한 것은 이전 분기들의 미온적 톤과 비교했을 때 명백한 narrative pivot 신호.

이런 종류의 신호는 다음 조건에서만 포착됨:
1. 최근 2-3분기 transcript를 동시에 컨텍스트에 둠 (단일 분기로는 비교 불가)
2. 동일 주제에 대한 phrase 강도 변천 추적
3. 갑자기 등장한 / 사라진 키워드 식별

수동으로 매 분석마다 transcript 3개를 찾아 비교하는 것은 비현실적. 자동화 skill 필요.

## 2. Goals & Non-goals

**Goals**:
- 미장 종목 ticker 입력 → 자동으로 최근 3개 분기 fool.com transcript 수집
- 3개 transcript 컨텍스트로 가장 최근 분기의 narrative 변화 추출
- 사용자 한국 포트폴리오에 미치는 cross-impact 자동 식별
- guru-investment 분석 시 자동 통합 (Part 1.4b 섹션)
- guru-investment 결과물에 **별도 압축 투자검토 보고서 (.md)** 자동 추가 생성

**Non-goals (v1)**:
- 한국 종목 transcript 분석 (transcript 컬쳐 다름, fool.com 미커버)
- transcript 정량 sentiment scoring (FinBERT 등 ML 모델 사용 안 함)
- earnings surprise prediction (forward-looking forecasting 회피)
- transcript 외 자료 (10-K MD&A 등) 통합 분석 (out of scope)

## 3. Two Deliverables

본 design은 두 가지 결과물을 생성:

### Deliverable A: `transcript-pulse` 신규 skill
- Stand-alone 호출 가능 (`/transcript-pulse AAPL` 등)
- 출력: 채팅에 분석 결과 표시 (또는 guru-investment subcall 시 markdown section 반환)

### Deliverable B: `guru-investment` skill 업데이트
- 미장 종목 분석 시 transcript-pulse 자동 subcall → Part 1.4b 섹션으로 통합
- **모든** guru-investment 분석 시 별도 압축 투자검토 보고서 (`{종목명}_투자검토_{YYYYMMDD}.md`) 자동 생성 (한국 종목 포함)

---

## 4. Part A — `transcript-pulse` Skill Design

### 4.1 Architecture

```
사용자 입력 (ticker or fool.com URL)
       │
       ▼
[Step 1] URL Discovery
   - WebSearch: "site:fool.com {ticker} earnings transcript"
   - URL pattern 인식 + 날짜 desc 정렬 + 최근 3개 선택
   - Fallback: yfinance earnings_dates 활용
       │
       ▼
[Step 2] Body Extraction
   - WebFetch × 3 (각 transcript)
   - Prompt: "prepared remarks + Q&A 전문, 발언자 라벨 보존"
   - 각 transcript ~6-10K words
       │
       ▼
[Step 3] Comparative Analysis (T0 vs T-1, T-2)
   - 3개 dimension 추출 (아래 4.2 참조)
       │
       ▼
[Step 4] Korea Cross-Reference
   - 사용자 메모리 grep → 관련 한국 종목 thesis 식별
   - 미장 시그널이 한국 보유 종목에 미치는 영향 1-2단락
       │
       ▼
출력 (one of):
   (a) Stand-alone: 채팅에 markdown 형식 응답
   (b) guru-investment subcall: Part 1.4b 섹션 markdown 반환
```

### 4.2 Analysis Dimensions (3개)

T0 = 가장 최근 transcript, T-1, T-2 = baseline.

#### Dimension 1: "갑자기 강조 (Surge in T0)"
T-1, T-2에서 한 번도 안 나왔거나 한두 번 짧게 언급된 주제가 T0에서 강조·반복·확신.

**추출 방식**:
- T0에서 5회 이상 언급된 키워드 / 주제 식별
- T-1, T-2에서 동일 키워드 언급 빈도 비교
- 빈도 점프가 5x 이상인 항목 = "surge"
- 각 surge item에 대해 T0에서 가장 강한 인용구 1-2개 직접 발췌

#### Dimension 2: "톤 강도 변화 (Tone Shift on same topic)"
동일 주제에 대해 phrase 강도가 시간 따라 어떻게 변했는지.

**phrase 강도 ladder 예시**:
```
약 ─────────────────────────────────► 강
"exploring" → "considering" → "expect" → "confident in"
→ "highly confident" → "highest conviction ever"
```

**추출 방식**:
- 두 transcript 이상에서 등장하는 주제 식별
- 각 분기에서 그 주제에 대한 가장 대표적 phrase 1개씩 발췌
- T-2 → T-1 → T0 phrase contrast 표시

#### Dimension 3: "소멸한 narrative (Faded from T0)"
T-1, T-2에서 강조됐는데 T0에서 빠진 것.

**추출 방식**:
- T-1, T-2에서 5회 이상 언급된 키워드 중 T0에서 0-1회로 떨어진 것
- 회피 또는 deprioritize 시그널로 해석

### 4.3 Output Format — Stand-alone

```markdown
# {종목명} ({TICKER}) — Earnings Call Pulse

**Transcripts 분석**: T0 = {date}, T-1 = {date}, T-2 = {date}
**발표자**: {CEO} (CEO), {CFO} (CFO)

## 1. 이번 컨콜의 새 강조 (T0 Surge)

### {주제 1}
- T0 언급 빈도: {X}회 (T-1: {Y}회, T-2: {Z}회) → {X/avg(Y,Z)}x 점프
- 핵심 인용: "{T0 인용구}"

### {주제 2}
...

## 2. 톤 강도 변화

| 주제 | T-2 ({date}) | T-1 ({date}) | T0 ({date}) | 강도 변화 |
|---|---|---|---|---|
| {주제} | "{phrase}" | "{phrase}" | "{phrase}" | ↗↗ |

## 3. 소멸한 Narrative

- **{주제}** — T-1, T-2 핵심 주제 ({N}회 언급) → T0에서 1회 미만
- 해석: {회피/deprioritize/완료}

## 4. Analyst Q&A 우려 포인트

{분석사들이 집요하게 묻는 1-2가지 주제. 경영진의 답변 톤 (직답 vs 우회) 평가.}

## 5. 한국 포트폴리오 cross-reference

{발견한 시그널이 사용자의 한국 보유/관심 종목에 미치는 영향 1-2 단락}
```

### 4.4 Output Format — guru-investment subcall

위 stand-alone 구조의 압축 버전 (전체 ~2-3K chars). guru-investment 리포트의 Part 1.4 (분기별 재무) **직후**, Part 1.5 (18개월 공시) **직전** 위치에 "Part 1.4b: Earnings Call Pulse" 섹션으로 삽입.

### 4.5 Trigger Rules

**Stand-alone trigger words**:
- `/transcript-pulse {TICKER}`
- "transcript pulse"
- "{TICKER} 컨콜 톤"
- "{TICKER} earnings call 분석"
- "{TICKER} 컨퍼런스 콜 변화"
- 사용자가 fool.com transcript URL 직접 붙여넣기

**guru-investment에서 자동 subcall**:
- 미장 종목 (SEC CIK 매핑 성공) 분석 시 항상 실행
- 한국 종목 분석 시 skip

### 4.6 Fallback Handling

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
</tbody>
</table>

---

## 5. Part B — `guru-investment` Skill Update

### 5.1 Integration Point 1 — transcript-pulse Auto-Subcall

기존 guru-investment의 분석 흐름에 다음 추가:

**위치**: Step 2.5와 Step 2.6 사이 (재무 데이터 수집 후, 18개월 공시 분석 전).

**조건부 실행**:
- 미장 종목 (`CIK` 매핑 성공) → transcript-pulse subcall 실행
- 한국 종목 → skip

**통합 방식**:
- transcript-pulse가 반환한 markdown section을 Part 1.4b로 삽입
- 풀 리포트(`{종목명}_멀티구루_{YYYYMMDD}.md`) 안에 통합

### 5.2 Integration Point 2 — 압축 투자검토 보고서 자동 생성

**언제**: guru-investment 모든 분석 종료 시 항상 (한국 종목 포함)

**파일명**: `{종목명}_투자검토_{YYYYMMDD}.md`

**저장 경로**: 풀 리포트와 동일 폴더
- `~/Desktop/Claude/Investment Research/{종목명 or Ticker}/`
- Obsidian `Investment Research/KR_stocks/{종목명}/` 또는 `US Stocks/{Ticker}/`

**분량**: 3-5K chars (1-2 페이지)

**구조** (정해진 템플릿):
```markdown
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

## 3 핵심 근거 (Bull or Bear)

1. **{포인트 1 — 핵심 단어}** — {30-50자 근거}
2. **{포인트 2}** — {30-50자 근거}
3. **{포인트 3}** — {30-50자 근거}

## Earnings Call Pulse 알파 (미장만)

{transcript-pulse의 가장 alpha-rich 발견 1-2개. T0 인용구 직접 포함. ~300자.}

## 가장 큰 리스크 (단 1개)

**{리스크 한 줄}** — 발생 확률 {X%}.
대응: {매도 / 관망 / 비중 축소 트리거 조건}

## 포지션 운영

- 초기 진입: ${entry} × {n}%
- 추가 매수: ${level} 지지 시 +{Y}%
- 매도 트리거: {조건}
- 관망 트리거: {조건}

## 한국 포트폴리오 cross-reference

{미장 종목인 경우, 한국 보유 종목에 미치는 영향 1-2 단락}
{한국 종목인 경우, 같은 산업 미국 종목들과의 비교 1-2 단락}

---

> 본 보고서는 풀 리포트의 압축본. 상세 데이터·구루별 분석은 풀 리포트 참조.
> Claude verdict는 5명 구루 가중 평균 + transcript pulse signal 종합.
```

**Claude의 판단 권한**: 
- Verdict (BUY/HOLD/SELL/AVOID)는 Claude가 결정 (사용자 명시 요구사항)
- 가중 평균 기반이되 transcript pulse 시그널을 추가 가중치로 반영
- 한국 보유 종목과의 cross-impact도 verdict에 반영

### 5.3 양식 검증 규칙

압축 투자검토 보고서도 풀 리포트와 동일 검증 룰 적용:
- MD 파이프 테이블 금지 → HTML `<table>` 사용
- `**{문장부호}**한글조사` 금지 → `<b>...</b> 한글조사` 변환
- 저장 전 두 grep 셀프 검증 0건 확인:
  1. `\*\*[^*\n]{1,200}["')\].,!?;:""''」』》]\*\*[가-힣]`
  2. `^\|.*\|.*\|$`

---

## 6. File Locations & Skill Files

### 신규 skill 파일

```
~/.claude/skills/transcript-pulse/
├── SKILL.md          # 트리거 + 사용법 + 4단계 워크플로우 (~5K chars)
├── DESIGN.md         # 본 design doc (구현 후 reference)
└── (선택) examples/  # 예시 출력 1-2개
```

### 업데이트되는 skill

```
~/.claude/skills/guru-investment/SKILL.md
   - Step 2.5와 Step 2.6 사이에 "Step 2.5b: transcript-pulse subcall (미장 only)" 추가
   - Step 3 "Structure the output" 끝에 압축 투자검토 보고서 자동 생성 규칙 추가
   - 압축 투자검토 템플릿 본문 추가 (또는 별도 reference 파일)
```

### 결과물 저장 경로 (변경 없음)

```
미장:
~/Desktop/Claude/Investment Research/{TICKER}/{종목명}_멀티구루_{YYYYMMDD}.md      (풀 리포트)
~/Desktop/Claude/Investment Research/{TICKER}/{종목명}_투자검토_{YYYYMMDD}.md      (압축 신규)
+ (Optional) Obsidian vault: Investment Research/US Stocks/{TICKER}/ 동일 2종

한국:
~/Desktop/Claude/Investment Research/{종목명}/{종목명}_멀티구루_{YYYYMMDD}.md      (풀 리포트)
~/Desktop/Claude/Investment Research/{종목명}/{종목명}_투자검토_{YYYYMMDD}.md      (압축 신규)
+ (Optional) Obsidian vault: Investment Research/KR_stocks/{종목명}/ 동일 2종
```

---

## 7. Edge Cases & Limitations

### 7.1 fool.com 한계
- 일부 mid-small cap은 fool.com 미커버 가능. 사용자 ticker가 fool.com에 없을 때 분명한 에러 메시지 + IR URL 요청.
- fool.com이 분기 발표 후 1-2일 후 publish하는 경향. 최신 분기 발표 직후 호출 시 transcript 아직 없을 수 있음 → "최근 분기 발표일 {date} 이후 1-2일 대기 권장" 안내.

### 7.2 transcript 길이 제한
- 3개 transcript × ~10K words = ~30K words ≈ ~40K tokens. Claude context 충분히 수용.
- 매우 긴 컨콜 (HD대형 종목) ~50K tokens도 가능 — 여전히 context 내.

### 7.3 한국 종목 신호 cross-reference 정확도
- 사용자 메모리의 `project_*_guru_analysis.md` 파일을 grep으로 스캔.
- 키워드 매칭 기반이라 false positive 가능. Claude가 의미적으로 관련성 판단 후 inclusion 결정.

### 7.4 압축 보고서의 verdict 책임
- 사용자가 "매수/매도/관망 너가 결정해서"라고 명시.
- Claude가 verdict 책임지되, 항상 풀 리포트 5인 구루 분석 + transcript pulse 시그널의 가중 평균 근거 제시.
- 면책 조항: "교육·분석 목적이며 투자 권유 아님" 매 보고서 하단 표시.

### 7.5 압축 보고서의 의존성
- 풀 리포트 작성 후 압축 보고서 작성 (순서 의존). 풀 리포트 데이터 (재무, 구루별 verdict, transcript pulse)를 압축 보고서가 참조.

---

## 8. Implementation Order

1. **`transcript-pulse/SKILL.md` 작성** — 본 design 4.1~4.6 내용을 실행 가능한 형태로 변환. fool.com URL pattern, WebSearch query, Claude prompt 포함.
2. **`guru-investment/SKILL.md` 업데이트** — Step 2.5b 추가 + 압축 보고서 템플릿 추가.
3. **수동 테스트** — AAPL 또는 LB로 stand-alone 호출 검증. fool.com URL 발견 → 본문 추출 → 3-dimension 분석 → 출력.
4. **통합 테스트** — guru-investment AAPL 분석 호출 → Part 1.4b 자동 통합 확인 + 압축 보고서 자동 생성 확인.
5. **메모리 등록** — `project_transcript_pulse_skill.md` 추가, MEMORY.md 인덱스 업데이트.

## 9. Success Criteria

- [ ] `/transcript-pulse AAPL` 입력 시 fool.com 3개 transcript 자동 수집 + 3-dimension 분석 결과 출력
- [ ] guru-investment AAPL 분석 시 Part 1.4b "Earnings Call Pulse" 섹션 자동 통합
- [ ] guru-investment AAPL 분석 시 `AAPL_투자검토_20260511.md` 별도 .md 자동 생성
- [ ] guru-investment 한국 종목 (예: SK이노) 분석 시 압축 보고서만 생성 (transcript-pulse skip)
- [ ] 사용자가 fool.com 미커버 종목 입력 시 명확한 에러 메시지 + 대안 안내
- [ ] 모든 .md 출력이 사용자 양식 검증 grep 룰 2개 통과 (0건)

---

## 10. Open Questions

(설계 단계에서 명확히 결정되지 않았거나 구현 시 추가 결정 필요한 사항)

- **Q1**: 압축 투자검토 보고서의 verdict가 풀 리포트의 verdict와 다를 수 있는가?
  → 기본: 동일해야 함. transcript pulse 시그널이 결정적으로 바꾼다면 다를 수 있지만 그 경우 명시적 disclaimer 추가.

- **Q2**: 사용자가 압축 보고서만 원하고 풀 리포트는 skip하고 싶을 때?
  → guru-investment를 호출하면 항상 풀 리포트 생성. 압축만 따로 안 만듦. (확장 가능: 추후 `--brief-only` flag 추가 검토)

- **Q3**: transcript-pulse 분석을 한국 종목에도 부분 적용? (IR 페이지 PDF 수동 paste)
  → v1 out of scope. v2에서 검토.
