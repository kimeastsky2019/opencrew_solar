# 발코니 태양광 블로그 오토파일럿

쇼츠에서 소개한 "키워드 재기 → 글쓰기 → 발행까지 한 대화" 흐름을 네이버 공식 API로 다시 만든 파이프라인입니다.
제3자 MCP(uplika) 없이 내 키로 돌아가고, 조사 기록이 날짜별로 남습니다.

| 단계 | 쇼츠의 도구 | 여기서 하는 일 | 파일 |
|---|---|---|---|
| 1 | expand_naver_keywords | 시드 → 연관 키워드 (자동완성 + 검색광고 연관키워드) | `autopilot/research.py` `expand()` |
| 2 | research_naver_keywords | 월간 검색량(검색광고 API) · 블로그 문서 수 · 최근 30일 발행(검색 API) → 비율 · 판정 | `research.py` `measure()` `verdict()` |
| 3 | 클로드 | 세트(메인 1 + 서브 3) → 배치 규칙대로 초안 | `planner.py` `drafter.py` |
| 4 | publish | 규칙 검사 → 스마트에디터용 HTML · 발행 대기열 · 미리보기 → Claude in Chrome으로 **비공개** 발행 | `validate.py` `render.py` |

## 판정 규칙
비율 = 월간 검색 ÷ 블로그 문서 수. 높을수록 찾는 사람에 비해 쓴 글이 적습니다.

| 판정 | 조건 (기본값, `research.DEFAULT_RULES`에서 조정) |
|---|---|
| 희소 | 월간 검색 30 미만 |
| 벽 | 문서 10만 이상이고 비율 0.1 미만 |
| 과열 | 최근 30일 발행 100건 이상이고 월간 검색의 50% 이상 |
| 최적 | 비율 0.7 이상 |
| 가능 | 0.5 ~ 0.7 |
| 어려움 | 0.25 ~ 0.5 |
| 포화 | 0.25 미만 |

영상 속 측정값(0.80 최적, 0.46 어려움, 1.48 최적, 0.78 최적)과 같은 판정이 나오도록 맞췄습니다 (`tests/test_pipeline.py`).

## 배치 규칙 (글 프롬프트)
- 메인 키워드 = 제목 맨 앞
- 서브 키워드 3개 = 소제목 1~3에 1:1
- 소제목 4 = 마무리, 키워드 없음
- 공백 포함 800~1,200자, 소제목마다 `[사진: 무엇을 찍은 사진인지]`
- 수치는 `knowledge/facts.md`에 출처와 함께 있는 것만 사용, 꾸며낸 후기 금지

## 준비
1. 네이버 검색광고 → 도구 → API 사용 관리: `API 키`, `비밀키`, `CUSTOMER_ID`
2. developers.naver.com → 애플리케이션 등록 → 검색 API: `Client ID`, `Client Secret`
3. (선택) Anthropic API 키 — 없으면 프롬프트 파일만 만들고, Claude 대화창에서 글을 쓰면 됩니다.
4. `cp .env.example .env` 후 값 입력, `pip install requests` (선택: `pip install anthropic`)

## 실행
```bash
python -m autopilot.cli run --seed "발코니 태양광" --sets 5      # 조사 → 세트 → 초안 → 렌더
python -m autopilot.cli run --seed "발코니 태양광" --mock        # 키 없이 흐름만 확인 (예시 숫자)
python -m autopilot.cli render --posts posts --record data/research/<날짜>_발코니태양광.json
python -m autopilot.cli check --posts posts                     # 규칙 검사만
```
결과물: `out/preview.html`(원고 미리보기 · 복사 버튼 · 조사표), `out/naver_html/`, `out/markdown/`, `out/publish_queue.json`

## 발행 (비공개 먼저)
네이버 블로그 글쓰기 API는 종료되어 공식 발행 API가 없습니다. 발행은 로그인된 내 브라우저에서 합니다.
- **Claude에게 맡기기**: "out/publish_queue.json의 대기 글을 네이버 블로그에 비공개로 올려줘" → Claude in Chrome이
  `https://blog.naver.com/GoBlogWrite.naver`를 열고 제목·본문 붙여넣기 → 공개 설정 **비공개** → 태그 → 발행.
- **직접**: `preview.html`에서 제목 복사 → 본문 복사(서식 유지) → 스마트에디터에 붙여넣기 → `[사진: …]` 자리에 사진 넣기.
- 사진을 넣고 내용을 확인한 뒤 공개로 바꾸세요. 한 번에 여러 편을 공개하기보다 하루 1~2편씩 나누는 편이 안전합니다.

## 주의
- 자동완성 엔드포인트(`ac.search.naver.com`)는 공식 API가 아니라 언제든 바뀔 수 있습니다. 실패하면 검색광고 연관키워드만으로 진행합니다.
- 세트 묶기는 글자 겹침 기반 휴리스틱입니다. 의미가 어색하면 `data/sets.json`을 고치거나 Claude에게 검토를 맡기세요.
- 지자체 보조금은 해마다 바뀝니다. `knowledge/facts.md`의 확인일을 보고 갱신하세요.
