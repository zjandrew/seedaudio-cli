---
name: seedaudio
version: 0.1.0
description: "Volcengine 豆包语音合成大模型 2.0 文本转语音端到端工作流：写好"为听而写"的合成文本 + 用 seedaudio-cli 落地成音频。当用户提到语音合成、文本转语音、TTS、配音、旁白、有声书、AI 配音、播报、念稿、读出来、生成语音、豆包语音、音色、长文本转音频、多角色对话配音等场景时使用。"
metadata:
  requires:
    bins: ["seedaudio-cli"]
  cliHelp: "seedaudio-cli --help"
---

# seedaudio

**双重职责**:
1. **把文本改写成"为听而写"的合成文本** —— Part 2(创意层):数字/符号规范化、停顿节奏、情感语气、多音字兜底。
2. **用 `seedaudio-cli` 把文本跑成音频文件落到本地** —— Part 1(工程层)。

完整闭环:**用户给文本/意图 → Part 2 改写成可听文本 + 选音色/语气 → Part 1 跑 CLI → 落盘音频 → 可选分段拼接**。

**核心原则**:
- 合成文本 ≠ 阅读文本。为"耳朵"写,不是为"眼睛"写:`3.14` 写成"三点一四","$5" 写成"五美元",用标点控制停顿。
- 跑合成一律走 `seedaudio-cli`,不手拼 curl,不绕开 envelope/退出码。
- **Claude 听不见音频**——只能验文件存在 + 大小 + 报元数据,需要"听"时用 `ffprobe` 报时长,别假装听过。
- 单次请求文本有长度上限(约 1024 字节 ≈ 300 汉字),**长文本必须分段**(见 Part 3.2)。

---

# Part 1 — 怎么调用 CLI(工程层)

## 1.1 前置

1. 确认 `seedaudio-cli` 可执行(`which seedaudio-cli` 或 `seedaudio-cli --version`)。不可执行则提示 `uv tool install zjandrew-seedaudio-cli` 或 `pipx install zjandrew-seedaudio-cli`(PyPI 包名;命令名 `seedaudio-cli` 不变)。
2. 配置鉴权:豆包语音用**语音技术控制台的 API Key**(单个 `X-Api-Key`),**不是** Seedance 视频那套 `ARK_API_KEY`。优先 env `SEEDAUDIO_API_KEY`;缺失时引导 `seedaudio-cli config init`。Key 在[控制台 > API Key 管理](https://console.volcengine.com/speech/new/setting/apikeys)获取。
3. 默认 endpoint `https://openspeech.bytedance.com`,默认 resource_id `seed-tts-2.0`(官方音色)。复刻音色用 `seed-icl-2.0`。

## 1.2 多 profile 配置

```bash
seedaudio-cli config list                 # 列所有 profile,标 active
seedaudio-cli config use <name>           # 切 active
seedaudio-cli config add <name>           # 向导式新增(prompt 走 stderr,stdout 仍是干净 envelope)
seedaudio-cli config set default_voice zh_female_vv_uranus_bigtts
seedaudio-cli config set resource_id seed-icl-2.0       # 用复刻音色时
seedaudio-cli --profile <name> synthesize ...           # 单次覆盖,不改 active
seedaudio-cli config show [<name>]        # 查看(api_key 已脱敏)
```

优先级:`--api-key/--endpoint/--resource-id flag > SEEDAUDIO_* env > 文件 profile > 内置默认`。`--profile` 选 profile,字段级 flag 不会让它失效。

## 1.3 核心命令速查

```bash
# 文本 → 语音(默认 mp3)
seedaudio-cli synthesize -p "你好,欢迎使用豆包语音合成" \
  --voice zh_female_vv_uranus_bigtts --out hello.mp3

# 调节奏与音量音调
seedaudio-cli synthesize -p "新闻播报示例" --voice zh_male_liufei_uranus_bigtts \
  --speech-rate 10 --loudness-rate 0 --pitch 0 --encoding wav --sample-rate 24000 --out news.wav

# 情感/语气:用语音指令(context_texts)
seedaudio-cli synthesize -p "今天真是太开心啦" --voice zh_female_vv_uranus_bigtts \
  --instruct "用特别开心、撒娇的语气说" --out happy.mp3

# 长文本从文件读
seedaudio-cli synthesize --text-file chapter1.txt --voice zh_male_yangguangqingnian_uranus_bigtts --out ch1.mp3

# 字级时间戳(对齐字幕)
seedaudio-cli synthesize -p "字幕对齐示例" --voice zh_female_vv_uranus_bigtts \
  --subtitle --out clip.mp3        # 同时写 clip.mp3 + clip.mp3.words.json

# 发现音色(精选子集,完整列表看控制台音色库)
seedaudio-cli voices --language zh
seedaudio-cli voices --search 男声

# 预览请求体(不发请求,无需凭证)—— 全局 flag 放在子命令前
seedaudio-cli --dry-run synthesize -p "..." --voice zh_female_vv_uranus_bigtts

# 脚本化:全局 --jq 取字段(放子命令前)
seedaudio-cli --jq '.audio_path' synthesize -p "..." --voice vv --out a.mp3
```

> ⚠️ **全局 flag 必须放在子命令前**:`--dry-run` / `--jq` / `--format` / `--profile` / `--api-key` / `--endpoint` / `--resource-id` 属于根命令。写 `seedaudio-cli --dry-run synthesize ...`,不是 `synthesize ... --dry-run`。

## 1.4 音色选型(`--voice` / `resource_id`)

- 音色由 `--voice <speaker_id>` 指定(可在 profile 里设 `default_voice` 省略)。**官方音色**走 `resource_id=seed-tts-2.0`;**自己复刻的音色**(id 形如 `S_xxxx`)走 `resource_id=seed-icl-2.0`。
- `seedaudio-cli voices` 内置的是**精选子集**(可能过时),**权威清单在[控制台音色库](https://console.volcengine.com/speech/new/voices)**——给用户用音色前,不确定就让用户去控制台确认 id。
- 选音色优先级:用户指定 > profile `default_voice` > 按场景从 voices 里挑(见 `references/voices-and-style.md` 的场景对照)。
- **用"我的声音/本人音色"复刻合成**:用 `S_14TMJlS62`(本仓 owner 的复刻音色),并加 `--resource-id seed-icl-2.0`;要用指令/标签再加 `-m seed-tts-2.0-expressive`:
  ```bash
  seedaudio-cli --resource-id seed-icl-2.0 synthesize -p "用我的声音念这句" --voice S_14TMJlS62 --out mine.mp3
  ```

## 1.5 参数选型(CLI flag)

| 意图 | 推荐参数 |
|---|---|
| 通用人声 mp3 | `--encoding mp3 --sample-rate 24000`(默认即可) |
| 高保真存档 | `--encoding wav --sample-rate 44100` |
| 后续要二次处理/拼接 | `--encoding wav`(无损,拼接不掉音质) |
| 念快一点 / 慢一点 | `--speech-rate 20` / `--speech-rate -20`(范围 [-50,100],100=2倍速) |
| 音量大一点 | `--loudness-rate 20`(范围 [-50,100]) |
| 音调高/低 | `--pitch 3` / `--pitch -3`(范围 [-12,12]) |
| 句尾留白(衔接/呼吸) | `--silence-ms 300` |
| 要字幕时间戳 | `--subtitle`(仅 2.0,仅中英文) |

> `--bit-rate` 仅对 mp3 生效。更冷门的参数(`explicit_language` 显式语种、`explicit_dialect` 方言、`use_tag_parser` 标签、`disable_markdown_filter` 等)v1 没做成 flag,用 `--from-json base.json` 传完整 `req_params`,其它 flag 仍可覆盖顶层字段。

## 1.6 文本输入与长度上限

- 短文本用 `-p/--text`;长文本/多行用 `--text-file PATH`(UTF-8)。
- **单次请求约 1024 字节(≈ 300 汉字)上限**。超了 API 会报错。**长文本必须先按句切段**,每段独立合成,再拼接(见 Part 3.2)。
- 不确定长度时:中文按"一个汉字约 3 字节"估;接近上限就切。

## 1.7 情感、语气与停顿

- **语气/情感**:`--instruct "<语音指令>"`(底层 `context_texts`),如 `--instruct "用温柔安抚的语气,语速放慢"`。可重复传多条。官方 2.0 音色可直接用;**复刻音色**需要 `-m seed-tts-2.0-expressive` 才支持指令。
- **停顿**:靠**标点**控制最稳(逗号短停、句号长停、省略号拖顿);句尾留白用 `--silence-ms`;中英文音色还可用 **SSML**(`--ssml`,把文本当 SSML 解析,详见 Part 2.8)。
- **表现力 vs 稳定**:`-m seed-tts-2.0-standard`(默认)时延低、稳;`-m seed-tts-2.0-expressive` 表现力强但效果有波动。要强情感/指令时用 expressive,要稳定批量时用 standard。

## 1.8 字幕 / 对齐

`--subtitle` 会请求字级时间戳,合成成功后除音频外再写一份 `<音频>.words.json`(`[{word,startTime,endTime,confidence}, ...]`),envelope 里给 `subtitle_path`。用于做卡拉OK字幕/视频对轨。仅 2.0 音色、仅中英文支持。

## 1.9 产物验证(Claude 听不见音频)

实话:**你听不到声音**。能做的:
1. 确认 envelope 的 `audio_path` 存在、`bytes` 非零。
2. 把 `voice` / `encoding` / `sample_rate` / `usage.text_words`(计费字数)报给用户。
3. 想知道时长/是否正常,用 ffprobe(不是 Read):
   ```bash
   ffprobe -v error -show_entries format=duration,bit_rate -of default=nw=1 out.mp3
   ```
   没 ffprobe 就明说"装一下 ffmpeg 或你自己听",别假装听过。

## 1.10 常见错误处置(按退出码)

- `CONFIG_MISSING` / `INVALID_INPUT`(exit 2)→ 引导 `config init` 或修参数(看 message,含用了哪个 flag/约束)。
- `IO_ERROR`(exit 3)→ 检查 `--out` 路径可写;父目录不存在时用结尾带 `/` 的目录形式触发自动创建。
- `API_ERROR`(exit 4)→ 看 `details`:HTTP 401/403 多半 key/resource_id 不对或没开通;400 看 message(常见:文本超长、speaker id 不存在、该音色不支持某参数);429 退避重试。
- `NETWORK_ERROR`(exit 5)→ 重试;多次失败核对 `config show` 的 endpoint。
- `INTERNAL`(exit 10)→ bug,带 `--verbose` 跑一次拿 stacktrace,报 issue。

## 1.11 Red Flags — 出现立即停下

- 我正要 `Read out.mp3` → 停,Read 读不出音频,用 ffprobe 报元数据。
- 我正要把整篇长文一次性塞进 `-p` → 停,会超长度上限,先按句切段。
- 我正要把数字/符号/英文缩写原样丢给 TTS → 停,先按 Part 2.3 规范化成"读法"。
- 我正要凭记忆汇报"已生成"→ 停,先确认 `audio_path` 存在 + `bytes` 非零。
- 我正要给复刻音色用 `--instruct` 但没加 `-m seed-tts-2.0-expressive` → 停,复刻音色的指令需要 expressive。
- 我正要在分段合成里中途换音色/换 `--speech-rate`/换 `--sample-rate` → 停,拼接会音色/节奏/采样率撕裂。
- 我正要手拼 curl 调 openspeech → 停,走 CLI,envelope/错误路径才统一。

## 1.12 不要做

- 不要做语音识别(ASR,语音→文本)——本 CLI 只做合成(文本→语音)。
- 不要把 `X-Api-Key` 写进 shell history,用 `config init` 或 env。
- 不要默认乱挑音色——不确定就 `voices` 查或让用户去控制台确认 id。
- 不要一次性合成几千字——按句切段,逐段落盘,再拼。

## 1.13 安全与预期

- 合成是**同步**的(几百 ms ~ 几秒返回),没有任务轮询。文本越长、采样率越高,稍慢。
- 计费看 `usage.text_words`(含标点);`context_texts` 指令文本不计费。
- 音频文件务必传 `--out` 显式路径,别在任意目录默认落盘。
- 脚本场景首选默认 `--format json` + 全局 `--jq '.audio_path'`,稳定可解析。

---

# Part 2 — 怎么写合成文本(创意层)

你是豆包语音合成的"文本规范化 + 配音导演"。目标:让模型**读得对、读得自然、读出情绪**。

## 2.1 平台规格(豆包语音合成大模型 2.0)

| 维度 | 规格 |
|---|---|
| resource_id | `seed-tts-2.0`(官方音色)/ `seed-icl-2.0`(复刻音色) |
| 模型版本(`-m`) | `seed-tts-2.0-standard`(默认,稳/快)/ `seed-tts-2.0-expressive`(强表现力,有波动) |
| 语种 | 中、英、日、西等 + 多种方言口音(粤语/四川/北京等,需音色支持) |
| 文本长度 | 单次约 1024 字节(≈300 汉字),超长分段 |
| 音频格式 | mp3 / wav / pcm / ogg_opus |
| 采样率 | 8000–48000 Hz(常用 24000) |
| 语速/音量 | [-50,100](100=2倍) |
| 音调 | post_process.pitch [-12,12] |
| 字幕 | 字级时间戳,仅中英文 |

## 2.2 核心心法:为"听"而写,不是为"看"而写

人读文字会自动脑补读法;模型不会。你的首要任务是把**面向眼睛的文本**改写成**面向耳朵的可听文本**:展开数字符号、控制停顿、消歧多音字、标注情绪。

| 心法 | 落到哪一节 |
|---|---|
| 数字/符号/缩写 → 读法 | 2.3 文本规范化 |
| 用标点和留白控制节奏 | 2.4 停顿与节奏 |
| 用语音指令给情绪 | 2.5 情感与语气 |
| 多语种/方言显式锚定 | 2.6 多语种与方言 |
| 长文本切段不撕裂 | 2.7 长文本分段 |

## 2.3 文本规范化(读对的前提)

把"写法"改成"读法",并在交付时**透明披露**改了什么:

- **数字**:`3.14`→"三点一四";`2026`(年)→"二零二六";`2026`(数量)→"两千零二十六";电话 `13800138000` 逐位"幺三八……"。
- **金额/单位**:`$5`→"五美元";`5kg`→"五千克";`5%`→"百分之五";`12:30`→"十二点三十分"。
- **符号**:`&`→"和";`/`→"每"或"斜杠"(按语义);`~`→"到"。
- **英文缩写**:`API`→按字母"诶屁挨"或保留(看音色能力);`Mr.`→"先生"。
- **多音字/生僻字兜底**:模型易读错多音字/形近字,改写成发音一致的常用同音字(如"重(chóng)庆"歧义时上下文足够通常没事;真读错就换字),并在"优化问题"里披露替换。
- **Markdown/表情**:默认会过滤 Markdown 语法和 emoji;要保留星号等原样朗读时,用 `--from-json` 传 `additions.disable_markdown_filter=false`。

## 2.4 停顿与节奏

- **标点是最稳的停顿控制**:逗号(短停)、句号/问号/叹号(长停)、分号(中停)、省略号(拖顿/迟疑)、破折号(语气延展)。该停的地方加标点,别写成一长串没标点的句子。
- **句尾留白**:段落衔接、呼吸感用 `--silence-ms 200~500`。
- **SSML**(中英文音色):需要精确停顿/读法时用 `--ssml` + `<break time="300ms"/>` 等(见 2.8)。

## 2.5 情感与语气(语音指令)

用 `--instruct` 给一条自然语言指令描述"怎么说"。模板:`用<情绪><强度>的语气,<语速/音量提示>说`。

- 开心:`用特别开心、上扬雀跃的语气说`
- 安抚:`用温柔、放慢、带安抚感的语气说`
- 痛心:`用特别痛心、低沉的语气说`
- 播报:`用专业、清晰、中正的播报语气说`
- 悬念:`用压低声音、带神秘感的语气说`

要点:
- 官方 2.0 音色可直接用指令;**复刻音色**要 `-m seed-tts-2.0-expressive`。
- 一条指令聚焦一种语气,别把"开心又悲伤又愤怒"塞一条里。
- 强情感不稳时,降低期待或换 `standard` 求稳;同一段落别频繁切语气。

更多指令句式见 `references/voices-and-style.md`。

## 2.6 多语种与方言

- 文本里混多语种时,可用 `--from-json` 传 `additions.explicit_language`:`zh-cn`(中英混读)/`en`/`ja`/`es-mx`/`id`/`pt-br`/`ko`,只读指定语种。
- 方言:选**支持该方言的音色**,再用 `additions.explicit_dialect`。不确定哪些音色支持就查控制台音色库。
- 小语种台词建议单独成段、单独指定语种,避免与中文混在一句里读串。

## 2.7 长文本分段(超 1024 字节)

**原理**:按句/段把长文切成每段 ≤ ~300 汉字的小块,逐块合成,跨块保持同一音色/语速/采样率,最后拼接。详细 workflow 见 Part 3.2。

**切段规则**:
1. 优先在句号/段落边界切,别从句子中间断开。
2. 每段独立自包含(模型不跨请求记忆上下文)。
3. 跨段**音色、`--speech-rate`、`--encoding`、`--sample-rate` 必须一致**,否则拼接处会有突变。
4. 段间留白用 `--silence-ms` 或拼接时插静音。

## 2.8 SSML 速览(中英文音色)

`--ssml` 把 `-p`/`--text-file` 的内容当 SSML 解析。常用:

```xml
<speak>
  第一句话。<break time="400ms"/>第二句话。
  数字读法:<say-as interpret-as="digits">110</say-as>。
  <prosody rate="slow" pitch="+2st">这一句放慢、升调。</prosody>
</speak>
```

> SSML 仅中英文音色支持;不确定音色是否支持就先用标点 + flag 控制,别盲目上 SSML。

## 2.9 场景模板(详见 references)

- **有声书/旁白**:沉稳中性音色 + `standard` 求稳 + 按章节分段 + 段间 `--silence-ms 300`。
- **新闻/播报**:专业播报音色 + `--instruct "专业清晰的播报语气"` + `--speech-rate 5~15`。
- **广告/营销**:有感染力音色 + `expressive` + 情绪指令 + 关键词前后留停顿。
- **多角色对话**:每个角色一个音色,逐句分别合成再按顺序拼接(见 Part 3.3)。

完整音色场景对照、指令库、规范化清单在 `references/voices-and-style.md`。

---

# Part 3 — 端到端 workflow

## 3.1 单段合成(≤ ~300 汉字)

```
Step 1: 听用户要念什么 / 什么场景
Step 2: 按 Part 2 把文本规范化成可听文本(数字符号展开、停顿标点、必要的同音字替换)
Step 3: 选音色(voices 或用户指定)+ 选语气(--instruct)+ 选格式
Step 4: seedaudio-cli synthesize 跑(默认同步返回 + 落盘)
Step 5: 确认 audio_path 存在 + bytes 非零,报 voice/encoding/usage 给用户;需要时 ffprobe 报时长
```

最小例子:
```bash
seedaudio-cli synthesize -m seed-tts-2.0-standard \
  -p "你好,这里是今天的天气预报。" \
  --voice zh_male_liufei_uranus_bigtts \
  --encoding mp3 --sample-rate 24000 \
  --out weather.mp3
```

## 3.2 长文本一条命令落地:`narrate`(本 SKILL 主战场)

**触发词**:"把这篇文章读出来"、"有声书"、"长文转音频"、"整段念出来"、"几千字配音"。

超过单次上限(~300 汉字)的长文,**优先用 `narrate`**——它内部自动:按标点切段(每段 ≤ `--max-bytes` 字节,默认 900)→ 逐段合成(跨段同音色/同参数)→ 拼接成一个成片。你**不用手动切、不用手写 ffmpeg**。

```bash
# 先按 Part 2.3 把长文规范化(数字/符号展开、停顿标点),写进一个 txt
seedaudio-cli narrate \
  --text-file story.txt \
  --voice zh_male_xuanyijieshuo_uranus_bigtts \
  --speech-rate 0 --silence-ms 300 \
  --keep-segments \
  --out audio/story.mp3
```

读 stdout envelope:`segments`(切了几段)、`audio_path`、`bytes`、`concat`(`ffmpeg` / `wav` / `pcm`)、`usage.text_words`。进度逐段打到 stderr。

**拼接方式**:装了 `ffmpeg` 就用 ffmpeg(支持 mp3/wav/ogg);没装 ffmpeg 时 `--encoding wav` 或 `pcm` 用标准库无依赖拼接,`mp3`/`ogg_opus` 会**直接报 `INVALID_INPUT`** 让你装 ffmpeg 或换 wav——不会偷偷产出撕裂文件。

**关键 flag**:
- `--max-bytes N`:每段字节上限(默认 900,留了余量;API 硬上限 ~1024)。
- `--keep-segments`:保留分段文件到 `<out>.segments/`,某段不满意只重念那一段再重拼;不传则用临时目录、拼完即删。
- `--encoding`:长文+无 ffmpeg 选 `wav`;有 ffmpeg 默认 mp3 即可。
- 文本规范化仍是你的活——`narrate` 只切不改写,数字/符号/多音字要先按 Part 2.3 处理好。

### 必须做 / 必须不做(长文)

- ✅ 先规范化文本(数字/符号/多音字),再交给 `narrate`
- ✅ 长文**复述切段预期**给用户(可先 `--dry-run` 看 `segments` 和每段 `preview`)
- ✅ 重念用 `--keep-segments`,只补那一段
- ❌ 把整篇塞进 `synthesize -p`(会超长度上限报错)——长文走 `narrate`
- ❌ 在 `narrate` 里中途想换音色/语速(整篇统一;要换风格就拆成多次 `narrate` 再自己拼)
- ❌ 没装 ffmpeg 还硬要 mp3 长文——换 `--encoding wav`

> **手动模式(可选,需要逐段精细控制时)**:也可以自己用 `synthesize` 逐段(每段统一 `--voice/--encoding/--sample-rate`)落到 `seg-0{i}.wav`,再 `ffmpeg -f concat -safe 0 -i list.txt -c copy final.wav` 拼。`narrate` 就是把这套固化了,常规长文不必手动。

## 3.3 多角色对话配音

每个角色固定一个音色,**逐句**按角色分别合成,再按对话顺序拼接:

```bash
# 旁白
seedaudio-cli synthesize -p "夜深了,她推开门。" --voice zh_male_yangguangqingnian_uranus_bigtts \
  --encoding wav --sample-rate 24000 --out dlg/01-narr.wav
# 角色 A(温柔)
seedaudio-cli synthesize -p "你回来啦?" --voice zh_female_wenrouxiaoya_uranus_bigtts \
  --instruct "用温柔关切的语气说" --encoding wav --sample-rate 24000 --out dlg/02-a.wav
# 角色 B(沉稳)
seedaudio-cli synthesize -p "嗯,路上堵了很久。" --voice zh_male_liufei_uranus_bigtts \
  --encoding wav --sample-rate 24000 --out dlg/03-b.wav
# 再用 ffmpeg concat 按 01→02→03 顺序拼接
```

- 所有段**统一编码 / 采样率**,只换音色和语气。
- 角色与音色的映射一次定好,全程别换(同一角色换音色会"换人")。

---

# Part 4 — 交互指引

识别到语音合成需求时:

### Step 1 — 听需求
用户给的可能是:一段要念的文本 / 一个意图("帮我把这篇推文配个音")/ 一个场景("有声书旁白")。

### Step 2 — 确认关键项(用户说清的可跳过)
1. **音色/角色**:男声/女声、风格(沉稳/温柔/活泼/播报),或具体 speaker id。不确定就 `voices` 列几个给用户挑。
2. **语气情感**:平述 / 开心 / 安抚 / 播报 / 悬念…(→ `--instruct`)。
3. **格式**:mp3(通用)还是 wav(要二次处理/拼接);采样率。
4. **长度**:短句 / 长文(>300 汉字 → 走 3.2 分段)。

### Step 3 — 规范化文本
按 Part 2.3 把数字/符号/缩写展开,按 2.4 补停顿标点,必要时换同音字,并准备"优化问题"披露改动。

### Step 4 — 跑 CLI
按 Part 1 的 `synthesize` 跑(默认同步 + 落盘),不手拼 curl。

### Step 5 — 验证 + 汇报
- `audio_path` 存在?`bytes` 非零?
- 报 `voice` / `encoding` / `sample_rate` / `usage.text_words`;需要时 ffprobe 报时长。

### Step 6 — 微调
用户可要求:换音色/语气、调语速音量音调、改某段文本、长文重切段、换格式。

---

# 注意事项汇总

- **合成文本必须先规范化**:数字/金额/符号/缩写展开成读法,用标点控制停顿(Part 2.3 / 2.4)。
- **Claude 听不见音频**:验文件 + 大小 + 报元数据 + 可选 ffprobe;别假装听过,别 Read 音频文件。
- **鉴权是 `X-Api-Key`**(语音技术控制台),不是 Seedance 的 `ARK_API_KEY`。
- **音色 id 以控制台音色库为准**;`voices` 只是精选子集;复刻音色走 `resource_id=seed-icl-2.0`。
- **长文本必须分段**(单次约 1024 字节/300 汉字),跨段统一音色/语速/编码/采样率,再拼接。
- **复刻音色用 `--instruct`/标签**需要 `-m seed-tts-2.0-expressive`;要稳用 `standard`。
- **全局 flag 放子命令前**(`--dry-run`/`--jq`/`--profile`/`--api-key`/`--resource-id`)。
- **拼接用无损 wav**,统一参数;别用有损 mp3 反复拼。
- 不要做 ASR(语音识别),本 CLI 只做合成;不要手拼 curl,走 CLI 统一 envelope/退出码。
- 不要把 `X-Api-Key` 写进 shell history。
