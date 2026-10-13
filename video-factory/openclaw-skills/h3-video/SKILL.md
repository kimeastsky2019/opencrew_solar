---
name: h3-video
description: Make MiniMax H3 videos with sound (9:16 shorts) from a Korean scene idea, queue them, and report saved files. Paid API; always confirm first.
homepage: https://platform.minimax.io/docs/guides/video-generation
metadata: { "openclaw": { "requires": { "bins": ["python3"] }, "primaryEnv": "MINIMAX_API_KEY" } }
---

# H3 Video

Turn a scene idea into a MiniMax H3 video (picture + synchronized sound) on this Mac.

Everything lives in `~/h3-video`:

- `prompts/` – prompt files (`<slug>.txt`)
- `prompts/queue/` – prompts waiting for the nightly batch
- `prompts/done/` – queue prompts that finished
- `output/` – finished `.mp4` files and `tasks.log` (task IDs)

Run the tool with the `exec` tool as `python3 ~/h3-video/h3_video.py ...`. It reads the key from the `MINIMAX_API_KEY` environment variable, which the user configures. Never print, echo, read from files, or ask for the API key.

## Workflow

1. **Write the prompt.** Use the `h3-prompt-writing` skill (T2VA unless the user gives a first/last frame image). Defaults for BRICO shorts: 9:16, 6 seconds, live-action.
   - Do **not** put readable on-screen text (signs, documents, UI, subtitles) in the prompt. Korean text breaks in generated video; titles and UI are added later in Remotion.
   - Always fill `overall_soundscape`. Korean narration is added later with TTS, so avoid dialogue unless the user asks for it.
2. **Save it** to `~/h3-video/prompts/<slug>.txt` (lowercase, hyphens, e.g. `mother-tablet.txt`). Never overwrite an existing file; add `-2`, `-3` instead.
3. **Dry run** (free): `python3 ~/h3-video/h3_video.py ~/h3-video/prompts/<slug>.txt --dry-run --ratio 9:16 --duration 6`
4. **Confirm cost.** Show the user the prompt summary, ratio, duration, resolution and number of videos, and say it is billed by MiniMax. Generate only after an explicit yes in this conversation. A "yes" covers only the videos listed.
5. **Generate:** `python3 ~/h3-video/h3_video.py ~/h3-video/prompts/<slug>.txt --ratio 9:16 --duration 6`
   It takes a few minutes; it prints `저장 완료: <path>` when the file is saved.
6. **Report** the saved path. If the channel supports file attachments, send the `.mp4`.

## Queue (batch)

- To add without generating now: save the prompt into `~/h3-video/prompts/queue/` instead of `prompts/`.
- To process the queue: `python3 ~/h3-video/h3_video.py --queue --max-jobs 3`. Finished prompts move to `prompts/done/`; failed ones stay in the queue.
- Never raise `--max-jobs` above what the user approved.

## Options

| Option | Default | Notes |
|---|---|---|
| `--ratio` | `9:16` | 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 (ignored when a frame image is given) |
| `--duration` | `6` | MiniMax-H3: 4–15 s; MiniMax-H3-Max: 5–15 s |
| `--resolution` | `768P` | H3: 768P/2K; H3-Max: 480P/768P |
| `--model` | `MiniMax-H3` | `MiniMax-H3-Max` is faster |
| `--first-frame` / `--last-frame` | – | image path or URL |
| `--task-id ID` | – | re-download a finished task (IDs in `output/tasks.log`) |

## Errors

- `HTTP 401` – API key missing or wrong. Tell the user to re-save it in Terminal (see `~/h3-video/README.md`); never ask for the key in chat.
- `HTTP 402` – MiniMax balance is empty. Tell the user to top up at https://platform.minimax.io. Stop; do not retry.
- `HTTP 429` – rate limited. Wait a minute and retry once.
- `CERTIFICATE_VERIFY_FAILED` – regenerate `~/h3-video/system-ca.pem` as in the README.
