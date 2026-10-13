"""Step 3a: 조사 기록 -> 세트(메인 1 + 서브 3). 메인 = 제목 앞쪽, 서브 = 소제목 1:1.

묶는 기준: 모든 키워드가 공유하는 주제어(예: '베란다 태양광')를 지운 뒤 남는 '구체어'가 겹치는지 본다.
구체어가 없는 넓은 키워드(예: '미니태양광')는 어느 세트에나 붙을 수 있고, 관련 서브가 모자라면 남은 키워드 중 점수 순으로 채운다.
의미상 더 정교한 묶음이 필요하면 data/sets.json을 직접 고치거나 Claude에게 검토를 맡긴다.
"""
from __future__ import annotations

from collections import Counter

from .naver_api import norm

MAIN_OK = {"최적", "가능"}
SUB_OK = {"최적", "가능", "어려움"}


def _bigrams(s: str) -> set[str]:
    s = norm(s)
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def score(row: dict) -> float:
    """검색량이 크고 비율이 높을수록 우선. 비율은 2에서 상한 — 검색량 거의 없는 롱테일 과대평가 방지."""
    return row["monthly_search"] * min(row["ratio"] or 0, 2.0)


def build_sets(rows: list[dict], n_sets: int = 5, subs_per_set: int = 3, common_share: float = 0.3) -> list[dict]:
    df = Counter(g for r in rows for g in _bigrams(r["keyword"]))
    common = {g for g, c in df.items() if c > common_share * len(rows)}
    specific = {norm(r["keyword"]): _bigrams(r["keyword"]) - common for r in rows}

    def rel(a: str, b: str) -> float:
        A, B = specific[norm(a)], specific[norm(b)]
        if not A or not B:          # 넓은 키워드는 어디에나 어울리지만 구체어 일치보다는 후순위
            return 0.05
        return len(A & B) / len(A | B)

    used: set[str] = set()
    mains = sorted([r for r in rows if r["verdict"] in MAIN_OK], key=score, reverse=True)
    sets = []
    for main in mains:
        if len(sets) >= n_sets:
            break
        mk = norm(main["keyword"])
        if mk in used:
            continue
        pool = [r for r in rows if r["verdict"] in SUB_OK and norm(r["keyword"]) not in used
                and norm(r["keyword"]) != mk]
        pool.sort(key=lambda r: (rel(main["keyword"], r["keyword"]), score(r)), reverse=True)
        subs = pool[:subs_per_set]
        if len(subs) < subs_per_set:
            continue
        for r in [main, *subs]:
            used.add(norm(r["keyword"]))
        sets.append({"main": main["keyword"], "subs": [s["keyword"] for s in subs], "evidence": [main, *subs]})
    return sets
