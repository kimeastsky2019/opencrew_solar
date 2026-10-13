"""명령 한 줄로 조사 → 세트 → 초안 → 발행 준비.

  python -m autopilot.cli run --seed "발코니 태양광" --sets 5
  python -m autopilot.cli run --seed "발코니 태양광" --mock          # API 키 없이 흐름 확인
  python -m autopilot.cli render --posts posts --out out            # 써 둔 원고만 렌더링
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from . import drafter, planner, render, research
from .validate import check

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> None:
    import os
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def cmd_research(a) -> Path:
    if a.mock:
        fx = json.loads((ROOT / "data" / "mock_research.json").read_text(encoding="utf-8"))
        rows = []
        for r in fx["rows"]:
            ratio, v = research.verdict(r["monthly_search"], r["blog_docs"], r.get("recent_30d"))
            rows.append({**r, "ratio": ratio, "verdict": v})
        rows.sort(key=lambda r: (research.VERDICT_ORDER.index(r["verdict"]), -r["monthly_search"]))
    else:
        ads, blog = research.clients_from_env()
        kws = research.expand(a.seed, ads, use_autocomplete=not a.no_autocomplete, limit=a.limit)
        print(f"[expand] {len(kws)}개 키워드")
        rows = research.measure(kws, ads, blog)
    path = research.save_record(rows, a.seed, ROOT / "data" / "research", mock=a.mock)
    print(f"[research] 저장: {path.relative_to(ROOT)}")
    for r in rows[:15]:
        print(f"  {r['verdict']:<4} {r['ratio'] if r['ratio'] is not None else '-':>6}  "
              f"{r['monthly_search']:>7,} / {r['blog_docs']:>9,}  {r['keyword']}")
    return path


def cmd_plan(a, record: Path | None = None) -> Path:
    rec = json.loads(Path(record or a.record).read_text(encoding="utf-8"))
    sets = planner.build_sets(rec["rows"], n_sets=a.sets)
    out = ROOT / "data" / "sets.json"
    out.write_text(json.dumps({"measured_on": rec["measured_on"], "mock": rec.get("mock", False), "sets": sets},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[plan] 세트 {len(sets)}개 → {out.relative_to(ROOT)}")
    for s in sets:
        print(f"  메인 「{s['main']}」  서브 {' / '.join(s['subs'])}")
    return out


def cmd_draft(a, sets_path: Path | None = None) -> list[Path]:
    data = json.loads(Path(sets_path or a.sets_file).read_text(encoding="utf-8"))
    paths = drafter.draft_sets(data["sets"], ROOT / "knowledge" / "facts.md", ROOT / "drafts", data["measured_on"])
    if paths:
        print(f"[draft] 원고 {len(paths)}편 생성 → drafts/")
    else:
        print("[draft] ANTHROPIC_API_KEY가 없어 프롬프트만 만들었어요 → drafts/prompts/ (Claude 대화창에 붙여 쓰면 됨)")
    return paths


def cmd_render(a) -> None:
    posts_dir = Path(a.posts)
    posts = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(posts_dir.glob("*.json"))]
    if not posts:
        sys.exit(f"{posts_dir}에 원고 JSON이 없습니다")
    rows, measured_on, mock = [], None, False
    if a.record:
        rec = json.loads(Path(a.record).read_text(encoding="utf-8"))
        rows, measured_on, mock = rec["rows"], rec["measured_on"], rec.get("mock", False)
        by = {r["keyword"].replace(" ", ""): r for r in rows}
        for p in posts:  # 원고 키워드에 조사 기록을 붙인다
            if not p.get("evidence"):
                p["evidence"] = [by[k.replace(" ", "")] for k in [p["main"], *p["subs"]] if k.replace(" ", "") in by]
    res = render.render_all(posts, Path(a.out), rows, measured_on, mock)
    bad = [q for q in res["queue"] if q["issues"]]
    print(f"[render] {len(posts)}편 → {a.out}/ (naver_html, markdown, publish_queue.json, preview.html)")
    print(f"[check] 규칙 통과 {len(posts) - len(bad)}편, 확인 필요 {len(bad)}편")
    for q in bad:
        print(f"  - {q['slug']}: {'; '.join(q['issues'])}")


def cmd_run(a) -> None:
    rec = cmd_research(a)
    sets = cmd_plan(a, rec)
    drafted = cmd_draft(a, sets)
    if drafted:
        a.posts, a.record = str(ROOT / "drafts"), str(rec)
        cmd_render(a)


def main(argv=None) -> None:
    load_env()
    p = argparse.ArgumentParser(prog="autopilot")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("research", "run"):
        s = sub.add_parser(name)
        s.add_argument("--seed", required=True)
        s.add_argument("--mock", action="store_true", help="API 없이 예시 데이터로 실행")
        s.add_argument("--no-autocomplete", action="store_true")
        s.add_argument("--limit", type=int, default=40)
        s.add_argument("--sets", type=int, default=5)
        s.add_argument("--out", default=str(ROOT / "out"))
    s = sub.add_parser("plan"); s.add_argument("--record", required=True); s.add_argument("--sets", type=int, default=5)
    s = sub.add_parser("draft"); s.add_argument("--sets-file", default=str(ROOT / "data" / "sets.json"))
    s = sub.add_parser("render"); s.add_argument("--posts", default=str(ROOT / "posts")); s.add_argument("--record")
    s.add_argument("--out", default=str(ROOT / "out"))
    s = sub.add_parser("check"); s.add_argument("--posts", default=str(ROOT / "posts"))
    a = p.parse_args(argv)
    if a.cmd == "check":
        for f in sorted(Path(a.posts).glob("*.json")):
            issues = check(json.loads(f.read_text(encoding="utf-8")))
            print(f"{'OK ' if not issues else 'FIX'} {f.name} {'; '.join(issues)}")
        return
    {"research": cmd_research, "plan": cmd_plan, "draft": cmd_draft, "render": cmd_render, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    main()
