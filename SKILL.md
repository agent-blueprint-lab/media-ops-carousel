---
name: media-ops-carousel
description: 新媒体多渠道图文内容生产：给一个选题，按渠道（小红书/公众号/私域/抖音）出多套版式；抖音渠道另支持视频模式（图文转竖屏讲解视频，TTS配音+跟读字幕+进度条）。流程：选题→查证→定渠道→主题→手排→渲染→检查→打包（视频模式加配音与合成）。基于 cy-carousel 渲染引擎，扩展多尺寸画布、主题系统、通用原文纸条、各渠道文案规范。用户要做小红书图文、公众号配图、私域海报、抖音图文/视频，或复用/精修这类内容时使用。
---

# 新媒体多渠道图文

给一个选题，交回**按渠道分套**的成品图＋文案。读者不是专业人士，节奏：反差钩子 → 一个看得懂的大例子 → 一句话定义 → 三条编号思考。

## 引擎安装（首次）

```bash
git clone https://github.com/chengyi-ai/cy-carousel-skill.git <skill>/engine
python3 -m pip install Pillow numpy PyMuPDF
```

本 skill 的 `scripts/` 在引擎之上加：多尺寸画布、主题、水印配置、通用纸条。引擎的 `SKILL.md` 红线（事实可回溯、开放授权素材、图上不写出处、不改原文、不自动发布）全部继承。

## 流程

1. **选题**：列 2–4 个候选，比素材、体裁、事实风险，选一个。写 `research/事实表.md`（陈述、原句、页码/URL、状态、用在哪页），另写"不写的内容"与"争议与写法"两节。
2. **定渠道**：先问用户投哪个渠道（用选项列出小红书/公众号/私域/抖音，可多选），用户不选就默认出一套组合（小红书＋公众号封面）。规范见 `references/channels.md`，先定渠道再排版——渠道决定画布尺寸，画布决定版式。
3. **定主题**：见 `references/themes.md`。`apply_theme()` 切换；水印从配置读，不许写死人名。
4. **手排**：写 `制作.py`，骨架如下（完整 API 照引擎 `examples/03-聪明汉斯/制作.py`）：

```python
import sys
sys.path.insert(0, '<skill>/scripts'); sys.path.insert(0, '<skill>/engine/scripts')
from layout import set_channel, apply_theme, paper_strip
import 手排 as S
from 手排 import headline, big, body, sticker, label, bottom, page

CHANNELS = ['xiaohongshu', 'wechat-cover']  # 本次渠道
apply_theme('dark')

def build(cv):  # 相对坐标，一套代码多渠道复用
    h = headline('第一行，\n[[第二行青色]]', 0.035, 0.022, 118)
    t = body('正文……', 0.035, bottom(h) + 0.025, 0.93, 60, font='文楷', typo=True)
    return [h, t, sticker('问句贴条', 0.035, bottom(t) + 0.04, 64)]

for ch in CHANNELS:
    set_channel(ch)          # 切换画布尺寸
    S.init(f'note-{ch}')
    cv = S.Canvas(); c = cv.save('P01')
    pages = S.pages; pages.append(page(c, build(cv), layout='cover'))
    for p in pages: p['watermark'] = False  # 或填账号名
    S.write_script('题目-' + ch, '制作.py', path=f'页面脚本-{ch}.json')
```

纸条用法：`paper_strip('官方原文……', keywords=('关键词',))` 返回 PIL 图，`cv.put(img.convert('RGBA'), 0, y, bleed='full')`。法条/网页原文通用，不限 PDF。

5. **渲染**：`python3 scripts/render2.py 页面脚本-<渠道>.json --out pages-<渠道> --width <宽> --height <高> --engine <skill>/engine`。宽幅封面（`wechat-cover`）单独排一版，不要复用竖版参数。
6. **检查**：`python3 scripts/check2.py 页面脚本-<渠道>.json --pages pages-<渠道> --width <宽> --height <高>`，errors 必须为零。风格建议项只作参考，不为凑指标改版式。
7. **文案**：按 `references/copywriting.md` 给每个渠道写文案文件（小红书：标题/正文/话题；公众号：标题/摘要；私域：文案；抖音：标题/口播备注），另写 `来源.md`。
8. **打包**：每渠道一个文件夹交付，内容按 `references/copywriting.md` 的"完整素材包"表齐套（图片＋文案＋来源.md，缺一项都不算交付）。打 zip 包给用户。
9. **视频模式**（抖音）：先按 `douyin` 渠道出 1080×1920 图文版，再转视频。规范见 `references/video.md`。一句话流程：写 `narration.json`（每页一段口播文案）→ `python3 scripts/video.py --pages <图目录> --narration narration.json --out 成片.mp4 --engine <cy-carousel>` → 抽帧验字幕/进度条 → 全片静音扫描 → 按完整素材包表打包（MP4＋标题/话题/口播文案/来源.md）。

## 常见坑

- 引擎 `render.py`/`check_all.py` 写死 1440×1920：多渠道一律用本 skill 的 `render2.py`/`check2.py`。
- 引擎 `write_script` 水印默认作者名：按页关闭或从主题配置读账号名。
- 非 macOS 没有 Times：`typo=True` 时拉丁字母回退 Noto Serif SC，有 warning，不影响出图。
- 正文防孤字：`check2` 会报孤字行，看到就调断句。
- TTS 配音：`video.py` 默认调用 `tts` 命令（`--tts-cmd` 可换，接口：`tts speak --language <code> --output <path> --text-stdin`；edge-tts 等按此接口自行封装也可）。口播文案里**避开裸英文单字母**（如"P""App"）：TTS 会截断，后面全是静音。数字用中文读法（"600亿"可照读）。`video.py` 自带静音质检（单段超 2.5 秒静音直接报错），报错就改文案重配。
