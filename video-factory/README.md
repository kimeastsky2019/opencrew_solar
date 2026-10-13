# Video Factory

MiniMax H3로 9:16 쇼츠 영상을 생성하고, OpenClaw 스킬로 자동화하는 서비스입니다.

| 경로 | 내용 |
|---|---|
| `h3-video/` | 영상 생성 스크립트 (`h3_video.py`, Python 표준 라이브러리만 사용), 사용 설명서, 링크 허브, 예시 프롬프트 |
| `openclaw-skills/h3-prompt-writing/` | 장면 설명 → H3 프롬프트 작성 스킬 |
| `openclaw-skills/h3-video/` | 프롬프트 저장 → 무료 미리보기 → 승인 후 생성 스킬 |

## 설치

```bash
cp -R h3-video ~/h3-video
cp -R openclaw-skills/* ~/.openclaw/skills/
security find-certificate -a -p /Library/Keychains/System.keychain /System/Library/Keychains/SystemRootCertificates.keychain > ~/h3-video/system-ca.pem
```

API 키(`MINIMAX_API_KEY`)는 저장소에 넣지 않습니다. 설정 방법은 `h3-video/README.md`를 보세요.
