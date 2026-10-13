# h3-video

MiniMax H3 API로 소리가 들어간 영상을 만드는 스크립트입니다. Python 3만 있으면 되고 추가 설치는 필요 없습니다.

## 폴더 구성

```
h3-video/
├── h3_video.py      스크립트
├── system-ca.pem    macOS 시스템 인증서 (회사망 인증서 오류 방지용)
├── prompts/         프롬프트(.txt) 넣는 곳
│   └── coffee.txt   예시: 핸드드립 커피 9:16
└── output/          완성된 영상(.mp4)과 작업 기록(tasks.log)이 저장되는 곳
```

## 1. API 키 준비 (처음 한 번)

1. https://platform.minimax.io 에 가입하고 **Pay-as-you-go**(쓴 만큼 결제)를 선택합니다. H3는 이 요금제에서만 됩니다.
2. Account Management → API Keys에서 키를 만듭니다.
3. 터미널에서 아래 명령을 실행하고, 키를 붙여넣은 뒤 Enter를 누릅니다. 입력한 키는 화면에 보이지 않습니다.

```bash
read -s "KEY?MiniMax API 키 붙여넣기: " && echo "export MINIMAX_API_KEY='$KEY'" >> ~/.zshrc && unset KEY && source ~/.zshrc
```

### 예시: 키가 `sk-api-123456123456`일 때

> 아래 키는 설명용 가짜 값입니다. 실제로는 발급받은 키로 바꿔서 붙여넣으세요.

1) 터미널에 위의 `read -s ...` 명령을 붙여넣고 Enter를 누릅니다.

```
M6_A@M6A ~ % read -s "KEY?MiniMax API 키 붙여넣기: " && echo "export MINIMAX_API_KEY='$KEY'" >> ~/.zshrc && unset KEY && source ~/.zshrc
MiniMax API 키 붙여넣기:
```

2) `MiniMax API 키 붙여넣기:`가 나오면 `sk-api-123456123456`을 붙여넣고 Enter를 누릅니다. 화면에는 아무것도 보이지 않는 게 정상입니다.

3) 저장이 됐는지 확인합니다. 키 전체 대신 앞 7글자만 보여 줍니다.

```
M6_A@M6A ~ % echo ${MINIMAX_API_KEY:0:7}...
sk-api-...
```

이제 `~/.zshrc` 맨 아래에 다음 한 줄이 추가된 상태입니다.

```bash
export MINIMAX_API_KEY='sk-api-123456123456'
```

4) 영상을 만들면 이렇게 진행됩니다.

```
M6_A@M6A ~ % cd ~/h3-video && python3 h3_video.py prompts/coffee.txt
제출 완료: coffee → task_id 424010985738629
생성 대기: coffee
  [424010985738629] queued (0초 경과)
  [424010985738629] running (60초 경과)
  ...
  [424010985738629] succeeded (250초 경과)
저장 완료: /Users/M6_A/h3-video/output/coffee-20261004-160512.mp4  (9:16, 6초, 768P)
```

키가 가짜이거나 틀리면 요금 없이 바로 이렇게 멈춥니다.

```
[오류] HTTP 401 API 키가 틀렸거나 만료됐습니다.
```

키를 바꾸려면 `~/.zshrc`에서 `export MINIMAX_API_KEY=` 줄을 지운 뒤 위 1)부터 다시 하세요.

## 2. 영상 만들기

```bash
cd ~/h3-video
python3 h3_video.py prompts/coffee.txt --dry-run   # 보낼 내용만 확인 (무료)
python3 h3_video.py prompts/coffee.txt             # 실제 생성 (요금 발생)
```

완성된 영상은 `output/coffee-날짜-시간.mp4`로 저장됩니다.

## 자주 쓰는 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--ratio` | `9:16` | 화면 비율: 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 |
| `--duration` | `6` | 길이(초): H3는 4~15, H3-Max는 5~15 |
| `--resolution` | `768P` | H3는 768P/2K, H3-Max는 480P/768P |
| `--model` | `MiniMax-H3` | `MiniMax-H3-Max`는 더 빠른 버전 |
| `--first-frame` | 없음 | 첫 장면 이미지(파일 또는 URL). 쓰면 비율은 이미지를 따릅니다 |
| `--last-frame` | 없음 | 마지막 장면 이미지 |
| `--prompt "..."` | 없음 | 파일 대신 프롬프트를 직접 입력 |
| `--task-id ID` | 없음 | 중간에 끊긴 작업의 결과만 다시 받기 (ID는 `output/tasks.log`에 있음) |

## 여러 개 한꺼번에

`prompts/` 폴더에 .txt 파일을 여러 개 넣고 아래처럼 실행하면 모두 한 번에 제출되고, 끝나는 대로 차례로 저장됩니다.

```bash
python3 h3_video.py prompts/*.txt
```

## 대기열 (일괄 생성)

`prompts/queue/`에 프롬프트(.txt)를 넣어 두고 아래 명령을 실행하면, 이름순으로 최대 `--max-jobs`개를 만듭니다. 끝난 프롬프트는 `prompts/done/`으로 옮겨지고, 실패한 것은 대기열에 남습니다.

```bash
python3 h3_video.py --queue --max-jobs 3
```

## 오픈클로에서 쓰기

이 맥의 `~/.openclaw/skills/`에 스킬 두 개가 들어 있습니다.

- `h3-prompt-writing`: 장면 설명을 H3 프롬프트로 정리
- `h3-video`: 프롬프트 저장 → 무료 미리보기 → 승인받은 뒤 생성 → 저장 경로 보고

오픈클로 채팅에서 "태블릿 보는 어머니 컷 H3로 만들어 줘"처럼 말하면 됩니다. 요금이 나가는 생성은 매번 확인을 받습니다.

모든 링크는 `hub.html`(바탕화면의 "H3 스튜디오")에 모여 있습니다.

## 다른 맥미니로 옮기기

이 폴더를 통째로 복사하고(AirDrop, USB 등), 그 맥에서 위의 **1. API 키 준비 3번**만 다시 하면 됩니다. `output/` 폴더는 복사하지 않아도 됩니다.

## 문제가 생기면

- **HTTP 401**: API 키가 틀렸습니다. 1번을 다시 하세요.
- **HTTP 402**: 잔액이 부족합니다. 충전하세요.
- **CERTIFICATE_VERIFY_FAILED**: `system-ca.pem`이 없거나 오래됐습니다. 아래 명령으로 다시 만드세요.

```bash
security find-certificate -a -p /Library/Keychains/System.keychain /System/Library/Keychains/SystemRootCertificates.keychain > ~/h3-video/system-ca.pem
```
