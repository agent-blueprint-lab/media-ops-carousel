# media-ops-carousel

新媒体多渠道图文/视频内容生产 skill（Claude Code / Codex 可用）。给一个选题，按投放渠道出一整套可直接用的素材包。

## 能做什么

| 渠道 | 交付 |
|---|---|
| 小红书 | 1080×1440 图文组图＋标题/正文/话题/置顶评论 |
| 公众号 | 900×383 封面＋900×1200 正文配图＋标题/摘要/正文 |
| 私域 | 1080×1920 或 1080×1080 海报＋短文案 |
| 抖音 | 1080×1920 图文＋竖屏讲解视频（TTS 配音＋跟读字幕＋进度条） |

每个渠道都是**完整素材包**（图片＋文案＋来源.md），运营拿到直接能用。

## 依赖

- Python 3.10+，`pip install Pillow numpy PyMuPDF`
- ffmpeg（视频模式）
- TTS 命令行（视频模式，`--tts-cmd` 可换，默认 `tts`）
- 渲染引擎：按 SKILL.md 安装步骤准备（`engine/` 目录）

## 用法

把本仓库放到 skills 目录（如 `~/.claude/skills/media-ops-carousel`），然后对 AI 说：

> 做一个小红书图文，选题：xxx

或指定多渠道：

> 选题 xxx，出小红书＋公众号＋抖音视频三套

AI 会按 `SKILL.md` 流程执行：选题 → 查证 → 定渠道 → 主题 → 手排 → 渲染 → 检查 → 打包（zip）。

## 结构

```
SKILL.md            主流程（先读这个）
references/
  channels.md       各渠道尺寸与版式规范
  themes.md         主题系统（dark/paper/brand-blue/自定义）
  copywriting.md    各渠道文案规范＋完整素材包清单
  video.md          抖音视频模式规范
scripts/
  layout.py         多尺寸画布＋主题＋水印＋通用原文纸条
  render2.py        多尺寸渲染（引擎补丁入口）
  check2.py         按渠道尺寸的硬红线检查
  video.py          图文转竖屏视频（配音＋字幕＋进度条）
```

## 说明

- MIT License.
