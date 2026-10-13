"""발행 전 규칙 검사: 제목 앞 메인, 소제목 4개, 서브 1:1, 마무리 무키워드, 분량, 사진 자리."""
from __future__ import annotations

from .naver_api import norm

MIN_CHARS, MAX_CHARS = 800, 1200


def body_chars(post: dict) -> int:
    """공백 포함 글자 수 (도입 + 소제목 + 소제목 본문). 네이버 글자 수 세기와 같은 기준. 사진 자리·출처는 제외."""
    parts = [post.get("intro", "")] + [s["heading"] + "".join(s["body"]) for s in post["sections"]]
    return len("".join(parts).replace("\n", ""))


def check(post: dict) -> list[str]:
    issues = []
    main, subs = post["main"], post["subs"]
    if not norm(post["title"]).startswith(norm(main)):
        issues.append(f"제목이 메인 키워드 「{main}」로 시작하지 않음")
    secs = post.get("sections", [])
    if len(secs) != 4:
        issues.append(f"소제목이 4개가 아님 ({len(secs)}개)")
    for i, sub in enumerate(subs[:3]):
        if i < len(secs) and norm(sub) not in norm(secs[i]["heading"]):
            issues.append(f"소제목 {i + 1}에 서브 키워드 「{sub}」 없음")
    if len(secs) == 4:
        last = norm(secs[3]["heading"])
        for kw in [main, *subs]:
            if norm(kw) in last:
                issues.append(f"마무리 소제목에 키워드 「{kw}」가 들어감")
    for i, s in enumerate(secs, 1):
        if not s.get("photo"):
            issues.append(f"소제목 {i}에 사진 자리 없음")
    n = body_chars(post)
    if not MIN_CHARS <= n <= MAX_CHARS:
        issues.append(f"분량 {n}자 (공백 포함) — 권장 {MIN_CHARS}~{MAX_CHARS}자")
    return issues
