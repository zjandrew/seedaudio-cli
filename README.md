# seedaudio-cli

CLI for Volcengine Doubao speech synthesis (豆包语音合成大模型 2.0, `seed-tts-2.0`), with an
accompanying SKILL for Claude Code / AI agents.

It targets the **V3 HTTP Chunked unidirectional** TTS endpoint
(`/api/v3/tts/unidirectional`): one-shot text in, audio file out. Synthesis is synchronous —
there is no task/polling model.

## Install

```bash
# Recommended:
uv tool install zjandrew-seedaudio-cli

# Or with pipx:
pipx install zjandrew-seedaudio-cli

# Companion SKILL:
npx skills add zjandrew/seedaudio-cli -g -y
```

The PyPI distribution is named `zjandrew-seedaudio-cli`; the binary is still `seedaudio-cli`.

Local development:

```bash
git clone https://github.com/zjandrew/seedaudio-cli.git
cd seedaudio-cli
uv sync --all-extras
uv run seedaudio-cli --version
```

## Configure

TTS auth is the 语音技术 console **API Key** model — a single `X-Api-Key`, *not* the Ark
`ARK_API_KEY` Bearer that the video API uses. Get it from
[控制台 > API Key 管理](https://console.volcengine.com/speech/new/setting/apikeys).

```bash
# Interactive wizard (creates ~/.seedaudio-cli/config.json, chmod 600):
seedaudio-cli config init

# Or env vars:
export SEEDAUDIO_API_KEY=...
export SEEDAUDIO_ENDPOINT=https://openspeech.bytedance.com   # optional

# Or programmatic:
seedaudio-cli config set api_key ...
seedaudio-cli config set default_voice zh_female_vv_uranus_bigtts
seedaudio-cli config set resource_id seed-tts-2.0            # seed-icl-2.0 for cloned voices
```

Priority: CLI flag > env var > config file > built-in default.

### Multiple profiles

```bash
seedaudio-cli config list
seedaudio-cli config add prod
seedaudio-cli config use prod
seedaudio-cli --profile prod synthesize -p "..."
```

## Usage

```bash
# Text → speech (mp3)
seedaudio-cli synthesize -p "你好，欢迎使用豆包语音合成" \
  --voice zh_female_vv_uranus_bigtts --out hello.mp3

# Tune delivery
seedaudio-cli synthesize -p "新闻播报示例" --voice zh_male_liufei_uranus_bigtts \
  --speech-rate 10 --loudness-rate 0 --pitch 0 --encoding wav --sample-rate 24000 --out news.wav

# Emotion / style via voice instruction (context_texts)
seedaudio-cli synthesize -p "今天真是太开心啦" --voice zh_female_vv_uranus_bigtts \
  -m seed-tts-2.0-expressive --instruct "用特别开心、撒娇的语气说" --out happy.mp3

# Long text from a file
seedaudio-cli synthesize --text-file chapter1.txt --voice zh_male_yangguangqingnian_uranus_bigtts --out ch1.mp3

# Word-level timestamps alongside the audio
seedaudio-cli synthesize -p "字幕对齐示例" --voice zh_female_vv_uranus_bigtts \
  --subtitle --out clip.mp3   # writes clip.mp3 + clip.mp3.words.json

# Discover voices (curated subset; full list in the console)
seedaudio-cli voices --language zh

# Dry run (prints the request body, no API call — works without credentials)
seedaudio-cli --dry-run synthesize -p "..." --voice zh_female_vv_uranus_bigtts
```

## SKILL

`skills/seedaudio/SKILL.md` ships in this repo. Install for Claude Code:

```bash
npx skills add zjandrew/seedaudio-cli -g -y
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success |
| 2 | INVALID_INPUT / CONFIG_MISSING |
| 3 | IO_ERROR |
| 4 | API_ERROR |
| 5 | NETWORK_ERROR |
| 10 | INTERNAL |

## License

MIT
