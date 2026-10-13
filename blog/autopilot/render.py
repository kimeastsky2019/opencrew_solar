"""Step 4 준비: 글 JSON -> 네이버 스마트에디터 붙여넣기용 HTML, 마크다운, 발행 대기열, 미리보기 페이지."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .validate import body_chars, check

TEMPLATE = Path(__file__).with_name("preview_template.html")


def to_naver_html(post: dict) -> str:
    """스마트에디터 ONE에 붙여넣어도 깨지지 않는 단순 태그만 사용 (p, b, span 인라인 스타일)."""
    e = html.escape
    out = [f'<p><span style="font-size:15px;color:#555">{e(post["subtitle"])}</span></p>', "<p><br></p>"]
    out += [f"<p>{e(p)}</p>" for p in _paras(post["intro"])]
    for s in post["sections"]:
        out.append("<p><br></p>")
        out.append(f'<p><b><span style="font-size:19px">{e(s["heading"])}</span></b></p>')
        out.append(f'<p><span style="color:#888">[사진: {e(s["photo"])}]</span></p>')
        out += [f"<p>{e(p)}</p>" for p in s["body"]]
    if post.get("sources"):
        out.append("<p><br></p>")
        out.append('<p><span style="font-size:13px;color:#888">참고 자료</span></p>')
        out += [f'<p><span style="font-size:13px;color:#888">· {e(src["title"])} — {e(src["url"])}</span></p>'
                for src in post["sources"]]
    return "\n".join(out)


def to_markdown(post: dict) -> str:
    lines = [f"# {post['title']}", "", f"_{post['subtitle']}_", "", post["intro"], ""]
    for s in post["sections"]:
        lines += [f"## {s['heading']}", "", f"[사진: {s['photo']}]", ""]
        lines += [p + "\n" for p in s["body"]]
    if post.get("tags"):
        lines += [" ".join("#" + t.replace(" ", "") for t in post["tags"]), ""]
    if post.get("sources"):
        lines += ["참고 자료"] + [f"- [{s['title']}]({s['url']})" for s in post["sources"]]
    return "\n".join(lines)


def _paras(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n") if p.strip()]


def render_all(posts: list[dict], out_dir: Path, research_rows: list[dict] | None = None,
               measured_on: str | None = None, mock: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "naver_html").mkdir(exist_ok=True)
    (out_dir / "markdown").mkdir(exist_ok=True)
    queue, bundle = [], []
    for p in posts:
        issues = check(p)
        nh = to_naver_html(p)
        (out_dir / "naver_html" / f"{p['slug']}.html").write_text(nh, encoding="utf-8")
        (out_dir / "markdown" / f"{p['slug']}.md").write_text(to_markdown(p), encoding="utf-8")
        queue.append({"slug": p["slug"], "title": p["title"], "visibility": "비공개", "status": "대기",
                      "chars": body_chars(p), "issues": issues, "tags": p.get("tags", [])})
        bundle.append({**p, "naver_html": nh, "chars": body_chars(p), "issues": issues})
    (out_dir / "publish_queue.json").write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    page = TEMPLATE.read_text(encoding="utf-8")
    data = {"posts": bundle, "research": research_rows or [], "measured_on": measured_on, "mock": mock}
    page = page.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (out_dir / "preview.html").write_text(page, encoding="utf-8")
    return {"queue": queue, "preview": out_dir / "preview.html"}
