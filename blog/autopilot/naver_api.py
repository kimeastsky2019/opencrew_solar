"""Thin clients for the three data sources.

1. Naver Search Ad API  /keywordstool      -> related keywords + monthly search volume (PC+mobile)
2. Naver Open API       /v1/search/blog    -> total blog documents, recent 30-day publish count
3. Naver autocomplete   ac.search.naver.com -> spaced related phrases (unofficial, optional)
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import time

import requests

ADS_BASE = "https://api.searchad.naver.com"
SEARCH_BASE = "https://openapi.naver.com/v1/search/blog.json"
AC_URL = "https://ac.search.naver.com/nx/ac"


def norm(keyword: str) -> str:
    """Comparison key: keywordstool returns keywords without spaces."""
    return "".join(keyword.split()).lower()


def _to_int(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().replace(",", "")
    if s.startswith("<"):  # "< 10" -> treat as 5
        return 5
    try:
        return int(float(s))
    except ValueError:
        return 0


class SearchAdClient:
    """Naver 검색광고 API (searchad.naver.com > 도구 > API 사용 관리)."""

    def __init__(self, api_key: str, secret_key: str, customer_id: str, pause: float = 0.25):
        self.api_key, self.secret, self.customer_id, self.pause = api_key, secret_key, customer_id, pause

    def _headers(self, method: str, uri: str) -> dict:
        ts = str(int(time.time() * 1000))
        msg = f"{ts}.{method}.{uri}".encode()
        sig = base64.b64encode(hmac.new(self.secret.encode(), msg, hashlib.sha256).digest()).decode()
        return {
            "X-Timestamp": ts,
            "X-API-KEY": self.api_key,
            "X-Customer": str(self.customer_id),
            "X-Signature": sig,
        }

    def keywordstool(self, hints: list[str]) -> list[dict]:
        """Up to 5 hint keywords per call. Returns the hints themselves + related keywords."""
        uri = "/keywordstool"
        params = {"hintKeywords": ",".join(norm(h) for h in hints[:5]), "showDetail": "1"}
        r = requests.get(ADS_BASE + uri, params=params, headers=self._headers("GET", uri), timeout=20)
        r.raise_for_status()
        time.sleep(self.pause)
        rows = []
        for item in r.json().get("keywordList", []):
            pc, mo = _to_int(item.get("monthlyPcQcCnt", 0)), _to_int(item.get("monthlyMobileQcCnt", 0))
            rows.append({"keyword": item["relKeyword"], "monthly_search": pc + mo, "pc": pc, "mobile": mo,
                         "ad_competition": item.get("compIdx")})
        return rows

    def volumes(self, keywords: list[str]) -> dict[str, int]:
        """Exact monthly search volume for each keyword (keyed by norm())."""
        out: dict[str, int] = {}
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i + 5]
            wanted = {norm(k) for k in batch}
            for row in self.keywordstool(batch):
                key = norm(row["keyword"])
                if key in wanted:
                    out[key] = row["monthly_search"]
        return out


class BlogSearchClient:
    """Naver 검색 API — developers.naver.com 애플리케이션 등록 (검색 API 선택)."""

    def __init__(self, client_id: str, client_secret: str, pause: float = 0.12):
        self.h = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        self.pause = pause

    def _get(self, **params) -> dict:
        r = requests.get(SEARCH_BASE, params=params, headers=self.h, timeout=20)
        r.raise_for_status()
        time.sleep(self.pause)
        return r.json()

    def total_docs(self, query: str) -> int:
        return int(self._get(query=query, display=1).get("total", 0))

    def recent_30d(self, query: str, today: dt.date | None = None) -> int:
        """Posts in the last 30 days among the 100 newest. 100 means '100 or more'."""
        today = today or dt.date.today()
        cutoff = (today - dt.timedelta(days=30)).strftime("%Y%m%d")
        items = self._get(query=query, display=100, sort="date").get("items", [])
        return sum(1 for it in items if it.get("postdate", "0") >= cutoff)


def autocomplete(seed: str) -> list[str]:
    """Spaced phrases from Naver's search-box autocomplete. Unofficial endpoint: may change; failures return []."""
    params = {"q": seed, "con": "1", "frm": "nv", "ans": "2", "r_format": "json", "r_enc": "UTF-8",
              "r_unicode": "0", "t_koreng": "1", "run": "2", "rev": "4", "q_enc": "UTF-8", "st": "100"}
    try:
        r = requests.get(AC_URL, params=params, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    found: list[str] = []

    def walk(node):
        if isinstance(node, str):
            if node.strip() and node not in found and len(node) <= 40:
                found.append(node.strip())
        elif isinstance(node, list):
            # autocomplete rows look like [["keyword"], ...] — take first string of each row
            if node and isinstance(node[0], str):
                walk(node[0])
            else:
                for child in node:
                    walk(child)

    walk(data.get("items", []))
    return found
