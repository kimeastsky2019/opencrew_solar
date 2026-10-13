"""Step 3b: 세트 -> 글 초안 (draftPrompt). ANTHROPIC_API_KEY가 있으면 Claude API로 생성, 없으면 프롬프트 파일만 만든다."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

# 영상의 글 프롬프트 원문 + 배치 규칙(메인=제목 앞쪽, 서브=소제목 1:1, 마무리=키워드 없이)
DRAFT_PROMPT = """아래 키워드로 네이버 블로그
글 한 편을 써 줘.
제목, 부제목, 소제목 4개와
각 본문, 사진 자리까지 전부.
권장 분량은 800~1,200자.
[사진: 무엇을 찍은 사진인지]

## 키워드 표 (조사 기록 {measured_on})
{table}

## 배치 규칙
- 메인 키워드 「{main}」는 제목 맨 앞에 그대로 둔다.
- 소제목 1~3에는 서브 키워드를 순서대로 하나씩 그대로 넣는다: {subs_list}
- 소제목 4는 마무리. 키워드를 넣지 않는다.
- 분량은 공백 포함 800~1,200자 (도입 + 소제목 4개와 본문 합계, 사진 자리·출처 제외).
- 소제목마다 사진 자리 1개를 [사진: …] 형식으로 지정한다.

## 사실 규칙
- 수치·제도·날짜는 아래 '확인된 사실'에 있는 것만 쓴다. 없는 수치는 만들지 않는다.
- 지자체 지원 내용은 "해당 연도 공고 기준"임을 밝히고, 신청 전 확인하라고 안내한다.
- 직접 써 본 후기·지인 사례처럼 꾸며낸 경험담은 쓰지 않는다.
- 문체: 친근한 해요체, 문단은 2~3문장.

## 확인된 사실
{facts}

## 출력 형식 (JSON만)
{{"title": "...", "subtitle": "...", "intro": "...",
  "sections": [{{"heading": "...", "body": ["문단", "문단"], "photo": "무엇을 찍은 사진인지"}}, ... 4개],
  "tags": ["...", "..."], "sources": [{{"title": "...", "url": "..."}}]}}
"""


def build_prompt(set_: dict, facts: str, measured_on: str) -> str:
    lines = ["| 구분 | 키워드 | 월간 검색 | 블로그 문서 | 비율 | 판정 |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(set_["evidence"]):
        tag = "메인" if i == 0 else f"서브{i}"
        lines.append(f"| {tag} | {r['keyword']} | {r['monthly_search']} | {r['blog_docs']} | {r['ratio']} | {r['verdict']} |")
    return DRAFT_PROMPT.format(measured_on=measured_on, table="\n".join(lines), main=set_["main"],
                               subs_list=" → ".join(f"「{s}」" for s in set_["subs"]), facts=facts.strip())


def generate(prompt: str, model: str | None = None) -> dict:
    import anthropic  # optional dependency

    client = anthropic.Anthropic()
    msg = client.messages.create(model=model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"),
                                 max_tokens=4000, messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("모델 응답에서 JSON을 찾지 못했습니다")
    return json.loads(m.group(0))


def draft_sets(sets: list[dict], facts_path: Path, out_dir: Path, measured_on: str, slug_prefix: str = "post") -> list[Path]:
    facts = facts_path.read_text(encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompts").mkdir(exist_ok=True)
    written = []
    use_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
    for i, s in enumerate(sets, 1):
        slug = f"{slug_prefix}-{i:02d}"
        prompt = build_prompt(s, facts, measured_on)
        (out_dir / "prompts" / f"{slug}.txt").write_text(prompt, encoding="utf-8")
        if not use_api:
            continue
        post = generate(prompt)
        post.update({"slug": slug, "main": s["main"], "subs": s["subs"], "evidence": s["evidence"]})
        p = out_dir / f"{slug}.json"
        p.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(p)
    return written
