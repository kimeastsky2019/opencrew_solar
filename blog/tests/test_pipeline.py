"""python -m pytest -q  (또는 python tests/test_pipeline.py)"""
import datetime as dt
import json
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autopilot import naver_api, planner, research, validate  # noqa: E402


def test_verdict_matches_reference_examples():
    # 영상 속 조사 기록: 0.80 최적 / 0.46 어려움 / 1.48 최적 / 0.78 최적
    assert research.verdict(710, 892, 10)[1] == "최적"
    assert research.verdict(590, 1272, 10)[1] == "어려움"
    assert research.verdict(80, 54, 1)[1] == "최적"
    assert research.verdict(50, 64, 1)[1] == "최적"
    assert research.verdict(10, 5, 0)[1] == "희소"
    assert research.verdict(3000, 200_000, 50)[1] == "벽"
    assert research.verdict(150, 400, 120)[1] == "과열"


def test_keywordstool_parsing_and_signature_headers():
    fake = mock.Mock()
    fake.json.return_value = {"keywordList": [
        {"relKeyword": "베란다태양광", "monthlyPcQcCnt": 400, "monthlyMobileQcCnt": 2500, "compIdx": "중간"},
        {"relKeyword": "베란다태양광철거", "monthlyPcQcCnt": "< 10", "monthlyMobileQcCnt": 70, "compIdx": "낮음"}]}
    fake.raise_for_status.return_value = None
    with mock.patch.object(naver_api.requests, "get", return_value=fake) as g, mock.patch.object(naver_api.time, "sleep"):
        c = naver_api.SearchAdClient("k", "s", "123")
        vols = c.volumes(["베란다 태양광", "베란다 태양광 철거"])
        headers = g.call_args.kwargs["headers"]
        assert set(headers) == {"X-Timestamp", "X-API-KEY", "X-Customer", "X-Signature"}
        assert g.call_args.kwargs["params"]["hintKeywords"] == "베란다태양광,베란다태양광철거"
    assert vols == {"베란다태양광": 2900, "베란다태양광철거": 75}


def test_blog_total_and_recent():
    today = dt.date(2026, 10, 12)
    items = [{"postdate": "20261010"}] * 30 + [{"postdate": "20260801"}] * 70
    fake = mock.Mock()
    fake.raise_for_status.return_value = None
    fake.json.side_effect = [{"total": 4100}, {"items": items}]
    with mock.patch.object(naver_api.requests, "get", return_value=fake), mock.patch.object(naver_api.time, "sleep"):
        b = naver_api.BlogSearchClient("id", "secret")
        assert b.total_docs("베란다 태양광") == 4100
        assert b.recent_30d("베란다 태양광", today) == 30


def test_planner_and_posts():
    fx = json.loads((ROOT / "data" / "mock_research.json").read_text(encoding="utf-8"))
    rows = []
    for r in fx["rows"]:
        ratio, v = research.verdict(r["monthly_search"], r["blog_docs"], r["recent_30d"])
        rows.append({**r, "ratio": ratio, "verdict": v})
    sets = planner.build_sets(rows, n_sets=5)
    assert sets and all(len(s["subs"]) == 3 for s in sets)
    used = [k for s in sets for k in [s["main"], *s["subs"]]]
    assert len(used) == len(set(used)), "키워드가 두 세트에 중복 배치됨"
    for f in sorted((ROOT / "posts").glob("*.json")):
        assert validate.check(json.loads(f.read_text(encoding="utf-8"))) == [], f.name


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
