#!/usr/bin/env python3
"""MiniMax H3 영상 생성 스크립트 (표준 라이브러리만 사용, 추가 설치 불필요).

사용 예:
  # 프롬프트 파일 하나로 9:16, 6초 영상 만들기
  python3 h3_video.py prompts/coffee.txt

  # 폴더 안의 프롬프트(.txt) 전부 한꺼번에 만들기
  python3 h3_video.py prompts/*.txt

  # 첫 장면 이미지를 지정해서 만들기 (이미지→영상)
  python3 h3_video.py prompts/coffee.txt --first-frame cup.jpg

  # 실제 요청 없이 보낼 내용만 확인 (요금 0원)
  python3 h3_video.py prompts/coffee.txt --dry-run

  # 중간에 끊긴 작업 이어서 받기
  python3 h3_video.py --task-id 424010985738629

API 키는 환경변수 MINIMAX_API_KEY 에서 읽습니다.
API 문서: https://platform.minimax.io/docs/guides/video-generation
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_URL = "https://api.minimax.io"
POLL_SECONDS = 10
HOME_DIR = Path.home() / "h3-video"
DEFAULT_CA_FILE = HOME_DIR / "system-ca.pem"


def ssl_context():
    # 회사망처럼 인증서를 중간에서 바꾸는 환경에서는 macOS 시스템 인증서 묶음을 사용
    cafile = os.environ.get("SSL_CERT_FILE") or (str(DEFAULT_CA_FILE) if DEFAULT_CA_FILE.exists() else None)
    return ssl.create_default_context(cafile=cafile)


def request(method, path, api_key, body=None, ctx=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        hints = {
            401: "API 키가 틀렸거나 만료됐습니다.",
            402: "잔액이 부족합니다. Pay-as-you-go 충전 상태를 확인하세요.",
            429: "요청이 너무 많습니다. 잠시 뒤 다시 시도하세요.",
        }
        raise SystemExit(f"[오류] HTTP {e.code} {hints.get(e.code, '')}\n{detail}")


def image_item(src, role):
    # URL이면 그대로, 로컬 파일이면 data URL(Base64)로 변환
    if re.match(r"^https?://", src):
        url = src
    else:
        p = Path(src).expanduser()
        if not p.is_file():
            raise SystemExit(f"[오류] 이미지 파일이 없습니다: {p}")
        if p.stat().st_size > 30 * 1024 * 1024:
            raise SystemExit(f"[오류] 이미지가 30MB를 넘습니다: {p}")
        mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
        url = f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    return {"type": "image_url", "image_url": {"url": url}, "role": role}


def build_payload(prompt, args):
    content = [{"type": "text", "text": prompt}]
    if args.first_frame:
        content.append(image_item(args.first_frame, "first_frame"))
    if args.last_frame:
        content.append(image_item(args.last_frame, "last_frame"))
    payload = {
        "model": args.model,
        "content": content,
        "resolution": args.resolution,
        "duration": args.duration,
    }
    # 텍스트만으로 만들 때만 비율 지정 (이미지가 있으면 이미지 비율을 따름)
    if not (args.first_frame or args.last_frame):
        payload["ratio"] = args.ratio
    return payload


def poll(task_id, api_key, ctx):
    start = time.time()
    while True:
        task = request("GET", f"/v2/query/video_generation/{task_id}", api_key, ctx=ctx)["task"]
        status = task["status"]
        print(f"  [{task_id}] {status} ({int(time.time() - start)}초 경과)", flush=True)
        if status == "succeeded":
            return task
        if status in ("failed", "cancelled"):
            raise RuntimeError(f"생성 실패: status={status}, error={task.get('error')}")
        time.sleep(POLL_SECONDS)


def download(url, dest, ctx):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, context=ctx, timeout=300) as resp, open(dest, "wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)


def unique_path(out_dir, stem):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"{stem}-{stamp}.mp4"
    n = 2
    while path.exists():  # 기존 파일은 절대 덮어쓰지 않음
        path = out_dir / f"{stem}-{stamp}-{n}.mp4"
        n += 1
    return path


def main():
    ap = argparse.ArgumentParser(description="MiniMax H3 API로 영상(소리 포함)을 만듭니다.")
    ap.add_argument("prompt_files", nargs="*", help="프롬프트가 들어 있는 .txt 파일 (여러 개 가능)")
    ap.add_argument("--prompt", help="파일 대신 프롬프트를 직접 입력")
    ap.add_argument("--model", default="MiniMax-H3", choices=["MiniMax-H3", "MiniMax-H3-Max"])
    ap.add_argument("--ratio", default="9:16", choices=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"])
    ap.add_argument("--duration", type=int, default=6, help="길이(초). H3: 4~15, H3-Max: 5~15")
    ap.add_argument("--resolution", default="768P", choices=["480P", "768P", "2K"])
    ap.add_argument("--first-frame", help="첫 장면 이미지 (URL 또는 파일 경로)")
    ap.add_argument("--last-frame", help="마지막 장면 이미지 (URL 또는 파일 경로)")
    ap.add_argument("--out", default=str(Path.home() / "h3-video" / "output"), help="영상 저장 폴더")
    ap.add_argument("--task-id", action="append", default=[], help="이미 만든 작업 ID로 결과만 받기")
    ap.add_argument("--queue", action="store_true", help="prompts/queue/*.txt를 처리하고, 끝난 파일은 prompts/done/으로 이동")
    ap.add_argument("--max-jobs", type=int, default=3, help="--queue 한 번에 처리할 최대 개수 (요금 안전장치, 기본 3)")
    ap.add_argument("--dry-run", action="store_true", help="요청 내용만 보여 주고 실제로 보내지 않음")
    args = ap.parse_args()

    # 입력값 검사 (요금이 나가기 전에 미리 걸러냄)
    lo = 5 if args.model == "MiniMax-H3-Max" else 4
    if not lo <= args.duration <= 15:
        ap.error(f"{args.model}의 길이는 {lo}~15초입니다.")
    if args.model == "MiniMax-H3" and args.resolution == "480P":
        ap.error("MiniMax-H3는 768P 또는 2K만 됩니다. 480P는 MiniMax-H3-Max에서만 됩니다.")
    if args.model == "MiniMax-H3-Max" and args.resolution == "2K":
        ap.error("MiniMax-H3-Max는 2K를 지원하지 않습니다.")

    jobs = []  # (이름, 프롬프트)
    queue_files = {}  # 이름 → 대기열 파일 (성공하면 done/으로 이동)
    if args.queue:
        qdir = HOME_DIR / "prompts" / "queue"
        qdir.mkdir(parents=True, exist_ok=True)
        picked = sorted(qdir.glob("*.txt"))[: max(args.max_jobs, 0)]
        if not picked:
            print("대기열이 비어 있습니다: " + str(qdir))
            return
        args.prompt_files = list(args.prompt_files) + [str(p) for p in picked]
        queue_files = {p.stem: p for p in picked}
    if args.prompt:
        jobs.append(("prompt", args.prompt.strip()))
    for f in args.prompt_files:
        p = Path(f).expanduser()
        text = p.read_text(encoding="utf-8").strip()
        if not text:
            ap.error(f"빈 프롬프트 파일입니다: {p}")
        jobs.append((p.stem, text))
    for name, text in jobs:
        if len(text) > 7000:
            ap.error(f"프롬프트가 7000자를 넘습니다: {name} ({len(text)}자)")
    if not jobs and not args.task_id:
        ap.error("프롬프트 파일, --prompt, --task-id, --queue 중 하나는 필요합니다.")

    if args.dry_run:
        for name, text in jobs:
            payload = build_payload(text, args)
            for item in payload["content"]:
                if item["type"] == "image_url" and item["image_url"]["url"].startswith("data:"):
                    item["image_url"]["url"] = item["image_url"]["url"][:40] + "...(생략)"
            print(f"--- {name}\nPOST {BASE_URL}/v2/video_generation")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("[오류] MINIMAX_API_KEY 환경변수가 없습니다. README.md의 'API 키 설정'을 참고하세요.")
    ctx = ssl_context()
    out_dir = Path(args.out).expanduser()

    # 1) 작업을 모두 먼저 제출 (여러 개면 서버에서 동시에 만들어짐)
    tasks = [(f"task-{tid}", tid) for tid in args.task_id]
    for name, text in jobs:
        tid = request("POST", "/v2/video_generation", api_key, build_payload(text, args), ctx)["task_id"]
        print(f"제출 완료: {name} → task_id {tid}", flush=True)
        tasks.append((name, tid))

    log = out_dir / "tasks.log"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        for name, tid in tasks:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{name}\t{tid}\n")

    # 2) 하나씩 완료될 때까지 기다렸다가 3) 내려받기
    failed = 0
    for name, tid in tasks:
        print(f"생성 대기: {name}", flush=True)
        try:
            task = poll(tid, api_key, ctx)
            dest = unique_path(out_dir, name)
            download(task["content"]["url"], dest, ctx)
            print(f"저장 완료: {dest}  ({task.get('ratio')}, {task.get('duration')}초, {task.get('resolution')})")
            if name in queue_files:
                done_dir = HOME_DIR / "prompts" / "done"
                done_dir.mkdir(parents=True, exist_ok=True)
                target = done_dir / queue_files[name].name
                if target.exists():
                    target = done_dir / f"{queue_files[name].stem}-{datetime.now():%Y%m%d-%H%M%S}.txt"
                queue_files[name].rename(target)
        except (RuntimeError, urllib.error.URLError) as e:
            failed += 1
            print(f"[실패] {name} ({tid}): {e}", file=sys.stderr)
    if failed:
        raise SystemExit(f"{failed}개 실패. 작업 ID는 {log} 에 남아 있습니다.")


if __name__ == "__main__":
    main()
