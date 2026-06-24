---
name: seedaudio
version: 0.1.0
description: "当用户要做语音合成 / 文本转语音 / TTS,要配音、旁白、有声书、播报、念稿,或要写好中文 TTS 文案、选音色与语气、做多角色对话配音、把长文一次转成音频时使用。基于火山引擎豆包语音合成大模型 2.0(seedaudio-cli)。相关词:AI 配音、读出来、生成语音、豆包语音、音色、有声阅读、广播剧。"
metadata:
  requires:
    bins: ["seedaudio-cli"]
  cliHelp: "seedaudio-cli --help"
---

# seedaudio

**双重职责**:
1. **把文本改写成"为听而写"的合成文本** —— Part 2(创意层):数字/符号规范化、停顿节奏、情感语气、多音字兜底。
2. **用 `seedaudio-cli` 把文本跑成音频文件落到本地** —— Part 1(工程层)。

完整闭环:**用户给文本/意图 → Part 2 改写成可听文本 + 选音色/语气 → Part 1 跑 CLI → 落盘音频(多角色用 `dialogue` 自动拼接)**。

**核心原则**(其余自检见 §1.11 红线):
- 合成文本 ≠ 阅读文本。为"耳朵"写,不是为"眼睛"写:`3.14` 写成"三点一四","$5" 写成"五美元",用标点控制停顿。
- **Claude 听不见音频**——只能验文件存在 + 大小 + 报元数据,需要"听"时用 `ffprobe` 报时长,别假装听过。
- 这是**流式**接口,单次请求就能合成**很长**的整段(实测 4000+ 汉字一把出,约 14 分钟音频),普通文章/章节直接 `synthesize --text-file` 即可,**不用分段**。书本级超长(上万字)走官方异步长文本接口(本 CLI 暂未封装)。

---

# Part 1 — 怎么调用 CLI(工程层)

**选哪个命令**:

| 想做 | 命令 |
|---|---|
| 念稿 / 单段 / 整段长文(任意长度) | `synthesize`(§3.1) |
| 多角色对话配音(每行不同音色) | `dialogue`(§3.2) |
| 查音色 / 多 profile 配置 | `voices` / `config` |

## 1.1 前置

1. 确认 `seedaudio-cli` 可执行(`which seedaudio-cli` 或 `seedaudio-cli --version`)。不可执行则提示 `uv tool install zjandrew-seedaudio-cli` 或 `pipx install zjandrew-seedaudio-cli`(PyPI 包名;命令名 `seedaudio-cli` 不变)。
2. 配置鉴权:豆包语音用**语音技术控制台的 API Key**(单个 `X-Api-Key`),**不是** Seedance 视频那套 `ARK_API_KEY`。优先 env `SEEDAUDIO_API_KEY`;缺失时引导 `seedaudio-cli config init`。Key 在[控制台 > API Key 管理](https://console.volcengine.com/speech/new/setting/apikeys)获取。
3. 默认 endpoint `https://openspeech.bytedance.com`;`resource_id` 按音色自动推断(复刻音色 `seed-icl-2.0`,其余 `seed-tts-2.0`),一般不用管。

## 1.2 多 profile 配置

```bash
seedaudio-cli config list                 # 列所有 profile,标 active
seedaudio-cli config use <name>           # 切 active
seedaudio-cli config add <name>           # 向导式新增(prompt 走 stderr,stdout 仍是干净 envelope)
seedaudio-cli config set default_voice zh_female_vv_uranus_bigtts
# resource_id 一般不用设(按音色自动推断);只有想全局钉死某个 resource 时才设
seedaudio-cli config set resource_id seed-icl-2.0       # 可选:全局钉死(覆盖自动推断)
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

- 音色由 `--voice <speaker_id>` 指定(可在 profile 里设 `default_voice` 省略)。**`resource_id` 会按音色自动推断**:`S_*`/`ICL_*`/`saturn_*`(复刻音色)→ `seed-icl-2.0`,其余官方音色 → `seed-tts-2.0`。`synthesize`/`dialogue` 都自动处理,**不用手动加 `--resource-id`**;只有遇到推断不了的特殊 resource(如新资源类型)才用 `--resource-id` 显式覆盖。
- `seedaudio-cli voices` 内置的是**精选子集**(可能过时),**权威清单在[控制台音色库](https://console.volcengine.com/speech/new/voices)**——给用户用音色前,不确定就让用户去控制台确认 id。
- 选音色优先级:用户指定 > profile `default_voice` > 按场景从 voices 里挑(见 `references/voices-and-style.md` 的场景对照)。
- **用"我的声音/本人音色"复刻合成**:直接用 `S_14TMJlS62`(本仓 owner 的复刻音色),resource_id 自动走 `seed-icl-2.0`;要用指令/标签再加 `-m seed-tts-2.0-expressive`:
  ```bash
  seedaudio-cli synthesize -p "用我的声音念这句" --voice S_14TMJlS62 --out mine.mp3
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

## 1.6 文本输入与长度

- 短文本用 `-p/--text`;长文本/多行用 `--text-file PATH`(UTF-8)。
- **流式接口,单次请求就能出很长的整段**(实测 2000+ 汉字、6KB 文本一次成功)。普通文章/章节直接 `synthesize --text-file` 一把合成,**不用分段**。
- 真正书本级超长(上万字)走官方异步长文本接口(可到 10 万字,本 CLI 暂未封装);常规长文一次合成即可。

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

## 1.11 红线 — 动手前自检,出现立即停下

- 别 `Read` 音频文件 → 读不出,用 `ffprobe` 报时长/元数据。
- 别凭记忆说"已生成" → 先确认 `audio_path` 存在 + `bytes` 非零。
- 别把数字/符号/英文缩写原样丢给 TTS → 先按 Part 2.3 规范化成"读法"。
- 别为普通长文手动切段/逐句调用 → `synthesize --text-file` 一次就出整段(流式接口)。
- 复刻音色用 `--instruct`/标签 → 必须加 `-m seed-tts-2.0-expressive`。
- 一段 `dialogue` 里同一角色别换音色(否则像"换了人")。
- 别手拼 curl 调 openspeech → 走 CLI,envelope/退出码才统一。
- 别做 ASR(本 CLI 只合成);别乱挑音色(不确定就 `voices` 查 / 让用户去控制台确认);别把 `X-Api-Key` 写进 shell history。

## 1.12 安全与预期

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
| 文本长度 | 单次请求可合成很长文本(流式;实测 4000+ 汉字一次出整段,约 14 分钟);书本级超长走异步长文本接口 |
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

## 2.7 长文本怎么处理

普通长文(文章/章节)**直接一次合成**(`synthesize --text-file`)——流式接口实测 4000+ 汉字一把出整段(约 14 分钟音频),不用分段。真正书本级超长(上万字)走官方异步长文本接口(本 CLI 暂未封装)。

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
- **多角色对话**:每个角色一个音色,逐句分别合成再按顺序拼接(见 Part 3.2)。

完整音色场景对照、指令库、规范化清单在 `references/voices-and-style.md`。

---

# Part 3 — 端到端 workflow

## 3.1 单段 / 整段合成(synthesize,含普通长文)

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

> **普通长文也走这里**:流式接口,几千字的文章/章节(乃至十几分钟音频)`synthesize --text-file story.txt ...` 一次就出整段,不用分段;文本规范化(Part 2.3)照做。书本级超长(上万字)才走官方异步长文本接口。

## 3.2 多角色对话配音:`dialogue`

**触发词**:"多角色配音"、"对话配音"、"剧本配音"、"每个人不同声音"、"广播剧"。

一条命令吃一个**剧本**(每行 `角色: 台词`)+ 一份**角色→音色**映射,逐行按角色音色合成,按剧本顺序拼成一段。

剧本 `play.txt`:
```
# 注释行(# 开头)和空行会被忽略
旁白: 夜已经很深了,公寓的门被轻轻推开。
小美: 你怎么才回来呀,我都等你好久了。
阿强: 路上堵得厉害,对不住。
```

```bash
seedaudio-cli dialogue --script play.txt \
  --voice 旁白=zh_male_xuanyijieshuo_uranus_bigtts \
  --voice 小美=zh_female_wenrouxiaoya_uranus_bigtts \
  --voice 阿强=zh_male_liufei_uranus_bigtts \
  --instruct 小美="用温柔、略带撒娇的语气说" \
  --keep-segments --out play.mp3
```

要点:
- `--voice 角色=音色ID` 可重复;每个出现的角色都必须有映射,缺了报 `INVALID_INPUT`(会列出缺哪个)。
- `--instruct 角色=指令` 可重复,给某角色固定语气;官方音色直接用,复刻音色要配 `-m seed-tts-2.0-expressive`。
- **resource_id 自动按音色推断**:`S_*`/`ICL_*`/`saturn_*` 走 `seed-icl-2.0`(复刻),其余 `seed-tts-2.0`——所以**一个剧本里官方音色和你的复刻音色可以混用**,不用手动切 `--resource-id`。
- 编码/采样率全剧统一(命令级 `--encoding`/`--sample-rate`),只有音色和语气随角色变。
- 角色↔音色映射一次定好别换(同角色换音色 = 换人);`--keep-segments` 把每行音频留在 `<out>.segments/`,某句不满意只重做那行。
- 也可以不写文件,用 `-p "旁白: ...\n小美: ..."` 直接传剧本。

---

# Part 4 — 交互指引

识别到语音合成需求时:

### Step 1 — 听需求
用户给的可能是:一段要念的文本 / 一个意图("帮我把这篇推文配个音")/ 一个场景("有声书旁白")。

### Step 2 — 确认关键项(用户说清的可跳过)
1. **音色/角色**:男声/女声、风格(沉稳/温柔/活泼/播报),或具体 speaker id。不确定就 `voices` 列几个给用户挑。
2. **语气情感**:平述 / 开心 / 安抚 / 播报 / 悬念…(→ `--instruct`)。
3. **格式**:mp3(通用)还是 wav(要二次处理/拼接);采样率。
4. **长度/形态**:短句或普通长文都用 `synthesize`(一次出整段);多角色对话走 `dialogue`(3.2)。

### Step 3 — 规范化文本
按 Part 2.3 把数字/符号/缩写展开,按 2.4 补停顿标点,必要时换同音字,并准备"优化问题"披露改动。

### Step 4 — 跑 CLI
按 Part 1 的 `synthesize` 跑(默认同步 + 落盘),不手拼 curl。

### Step 5 — 验证 + 汇报
- `audio_path` 存在?`bytes` 非零?
- 报 `voice` / `encoding` / `sample_rate` / `usage.text_words`;需要时 ffprobe 报时长。

### Step 6 — 微调
用户可要求:换音色/语气、调语速音量音调、改某段文本、长文重切段、换格式。
