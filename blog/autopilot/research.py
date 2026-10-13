"""Step 1+2: expand keywords, measure volume & doc count, compute ratio and verdict, keep a dated record."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
from pathlib import Path

from .naver_api import BlogSearchClient, SearchAdClient, autocomplete, norm

# 판정 7종 (영상: 최적·가능·어려움·벽·과열·포화·희소). 기준값은 config에서 바꿀 수 있음.
DEFAULT_RULES = {
    "min_search": 30,          # 월 검색량이 이보다 적으면 희소
    "wall_docs": 100_000,      # 문서 수가 이 이상이고 비율이 낮으면 벽
    "wall_ratio": 0.1,
    "hot_recent_share": 0.5,   # 최근 30일 발행 / 월검색량 이 이상이면 과열 (한 달 새 글이 검색 수요의 절반 이상)
    "optimal": 0.7,            # 비율 >= 0.7 최적
    "possible": 0.5,           # 0.5 ~ 0.7 가능
    "hard": 0.25,              # 0.25 ~ 0.5 어려움, 그 아래 포화
}

VERDICT_ORDER = ["최적", "가능", "어려움", "포화", "과열", "벽", "희소"]


def verdict(search: int, docs: int, recent30: int | None, rules: dict = DEFAULT_RULES) -> tuple[float | None, str]:
    """비율 = 월간 검색 ÷ 블로그 문서. 높을수록 찾는 사람에 비해 쓴 글이 적다."""
    if search < rules["min_search"]:
        return (round(search / docs, 2) if docs else None), "희소"
    ratio = round(search / docs, 2) if docs else 99.0
    if docs >= rules["wall_docs"] and ratio < rules["wall_ratio"]:
        return ratio, "벽"
    if recent30 is not None and recent30 >= 100 and recent30 / max(search, 1) >= rules["hot_recent_share"]:
        return ratio, "과열"
    if ratio >= rules["optimal"]:
        return ratio, "최적"
    if ratio >= rules["possible"]:
        return ratio, "가능"
    if ratio >= rules["hard"]:
        return ratio, "어려움"
    return ratio, "포화"


def expand(seed: str, ads: SearchAdClient | None, use_autocomplete: bool = True, limit: int = 40) -> list[str]:
    """expand_naver_keywords 대응: 자동완성(띄어쓰기 형태) + 검색광고 연관키워드를 합친다."""
    phrases: dict[str, str] = {norm(seed): seed}
    if use_autocomplete:
        for p in autocomplete(seed):
            phrases.setdefault(norm(p), p)
    if ads:
        for row in ads.keywordstool([seed]):
            phrases.setdefault(norm(row["keyword"]), row["keyword"])
    return list(phrases.values())[:limit]


def measure(keywords: list[str], ads: SearchAdClient, blog: BlogSearchClient, rules: dict = DEFAULT_RULES,
            with_recent: bool = True) -> list[dict]:
    """research_naver_keywords 대응: 검색량·문서 수·비율·판정."""
    vols = ads.volumes(keywords)
    rows = []
    for kw in keywords:
        search = vols.get(norm(kw), 0)
        docs = blog.total_docs(kw)
        recent = blog.recent_30d(kw) if with_recent else None
        ratio, v = verdict(search, docs, recent, rules)
        rows.append({"keyword": kw, "monthly_search": search, "blog_docs": docs, "recent_30d": recent,
                     "ratio": ratio, "verdict": v})
    return sorted(rows, key=lambda r: (VERDICT_ORDER.index(r["verdict"]), -(r["monthly_search"] or 0)))


def save_record(rows: list[dict], seed: str, out_dir: Path, measured_on: dt.date | None = None, mock: bool = False) -> Path:
    """저장된 조사 기록 — 날짜별로 남겨서 다음 조사와 비교할 수 있게."""
    measured_on = measured_on or dt.date.today()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{measured_on.isoformat()}_{norm(seed)}{'_MOCK' if mock else ''}"
    (out_dir / f"{stem}.json").write_text(json.dumps(
        {"seed": seed, "measured_on": measured_on.isoformat(), "mock": mock, "rows": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")
    with open(out_dir / f"{stem}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return out_dir / f"{stem}.json"


def clients_from_env() -> tuple[SearchAdClient, BlogSearchClient]:
    missing = [k for k in ("NAVER_AD_API_KEY", "NAVER_AD_SECRET", "NAVER_AD_CUSTOMER_ID",
                           "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"환경변수가 없습니다: {', '.join(missing)}  (.env.example 참고, 또는 --mock)")
    ads = SearchAdClient(os.environ["NAVER_AD_API_KEY"], os.environ["NAVER_AD_SECRET"], os.environ["NAVER_AD_CUSTOMER_ID"])
    blog = BlogSearchClient(os.environ["NAVER_CLIENT_ID"], os.environ["NAVER_CLIENT_SECRET"])
    return ads, blog
