"""多渠道排版助手：画布切换、主题、水印、通用纸条。

用法：
    import sys
    sys.path.insert(0, '<skill>/scripts'); sys.path.insert(0, '<skill>/engine/scripts')
    from layout import set_channel, apply_theme, paper_strip, write_script_for_channel
    import 手排 as S

    set_channel('xiaohongshu')   # 切换画布（会改 S.W / S.H）
    apply_theme('dark')          # 切换主题（会改 S.CREAM / S.CYAN）
    ...
    write_script_for_channel('题目', 'xiaohongshu', theme, path='页面脚本-xiaohongshu.json')
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
RED = (229, 57, 53)  # 与引擎一致的标注红，不依赖 import 手排

# 渠道：名 -> (宽, 高)
CHANNELS = {
    'xiaohongshu': (1080, 1440),    # 小红书图文 3:4
    'wechat-cover': (900, 383),     # 公众号封面 2.35:1
    'wechat-body': (900, 1200),     # 公众号正文图
    'poster': (1080, 1920),         # 私域海报 9:16
    'poster-square': (1080, 1080),  # 私域方图 1:1
    'douyin': (1080, 1920),         # 抖音图文 9:16
}

THEMES = {
    'dark': {
        'background': '#080808', 'title_line1': '#F3F1E9', 'title_line2': '#00E5FF',
        'accent': '#00E5FF', 'body_font': '文楷', 'body_fill': '#F3F1E9',
        'paper': '#F4EFE4', 'watermark_text': '',
    },
    'paper': {
        'background': '#F5F1E8', 'title_line1': '#1A1A1A', 'title_line2': '#C92928',
        'accent': '#C92928', 'body_font': '文楷', 'body_fill': '#1A1A1A',
        'paper': '#FFFFFF', 'watermark_text': '',
    },
    'brand-blue': {
        'background': '#0A1A33', 'title_line1': '#FFFFFF', 'title_line2': '#4DA6FF',
        'accent': '#4DA6FF', 'body_font': '文楷', 'body_fill': '#EAF2FF',
        'paper': '#F4EFE4', 'watermark_text': '',
    },
}

_current_theme = dict(THEMES['dark'])
_current_channel = 'master'


def set_channel(name):
    """切换画布尺寸。name 为 CHANNELS 的键。返回 (w, h)。"""
    global _current_channel
    import 手排 as S
    w, h = CHANNELS[name]
    S.W, S.H = w, h
    _current_channel = name
    return w, h


def apply_theme(name_or_dict):
    """切换主题：改 S.CREAM（标题行1/正文）与 S.CYAN（标题行2/强调色）。"""
    global _current_theme
    import 手排 as S
    t = dict(THEMES[name_or_dict]) if isinstance(name_or_dict, str) and not name_or_dict.endswith('.json') \
        else json.loads(Path(name_or_dict).read_text(encoding='utf-8')) if isinstance(name_or_dict, str) \
        else dict(name_or_dict)
    _current_theme = t
    S.CREAM = t['title_line1']
    S.CYAN = t['accent']
    # body() 默认 fill 就是 CREAM；如需独立正文色，调用方显式传 fill
    return t


def current_theme():
    return dict(_current_theme)


def write_script_for_channel(topic, channel, path):
    """包一层 S.write_script：顺手把 config 的 accent/background/水印按主题修正，
    并关掉每页水印（除非主题配了 watermark_text）。"""
    import 手排 as S
    S.write_script(topic, 'layout.py', path=path)
    t = _current_theme
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    cfg = d.get('config', {})
    cfg['accent'] = t['accent']
    cfg['background'] = t['background']
    wm = t.get('watermark_text', '')
    cfg['watermark_text'] = wm
    cfg['account_name'] = wm or '账号名'
    d['config'] = cfg
    for p in d.get('pages', []):
        p['watermark'] = bool(wm)
    Path(path).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


def paper_strip(text, target_w=1440, font_size=46, keywords=(), pad_x=70, pad_y=46,
                leading=1.62, paper=None, font_path=None):
    """通用原文纸条：官方原文逐字排版，关键词画红线。不改原文，只加标注。
    不限 PDF——法条、判决、网页原文都可用。返回 PIL.Image（RGB）。"""
    paper = paper or _current_theme['paper']
    if font_path is None:
        # 优先用 <skill>/engine 自带的 Noto Serif SC（git clone cy-carousel 后）
        cands = [HERE.parent / 'engine' / 'assets' / 'fonts' / 'NotoSerifSC[wght].ttf']
        font_path = next((c for c in cands if c.is_file()), None)
        if font_path is None:
            raise FileNotFoundError(
                '找不到 NotoSerifSC 字体：请先按 SKILL.md 把 cy-carousel 克隆到 <skill>/engine，或显式传 font_path')
    font = ImageFont.truetype(str(font_path), font_size)
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    max_w = target_w - pad_x * 2
    # 逐单元换行：关键词作为原子单元，不从中间拆开（保证红线标注能命中）
    lines, cur = [], ''
    i, n = 0, len(text)
    while i < n:
        kw = next((k for k in keywords if text.startswith(k, i)), None)
        unit = kw if kw else text[i]
        if probe.textlength(cur + unit, font=font) <= max_w:
            cur += unit
            i += len(unit)
        elif cur:
            lines.append(cur)
            cur = ''
        else:
            for ch in unit:  # 单个单元就超宽时逐字硬拆（理论上不会发生）
                if probe.textlength(cur + ch, font=font) <= max_w:
                    cur += ch
                else:
                    lines.append(cur)
                    cur = ch
            i += len(unit)
    if cur:
        lines.append(cur)
    # 防孤字：末行不足2个有效字就从上一行挪一个下来
    PUNCT = '，。、：；！？…」』》）、,.!?:;·'
    while len(lines) >= 2:
        tail = ''.join(c for c in lines[-1] if c not in PUNCT)
        if len(tail) >= 2 or len(lines[-2]) <= 2:
            break
        lines[-2], lines[-1] = lines[-2][:-1], lines[-2][-1] + lines[-1]
    # 标点不居行首：行首是收尾标点就收到上一行末尾
    CLOSING = '，。、：；！？…」』》）、,.!?:;·'
    for i in range(1, len(lines)):
        while lines[i] and lines[i][0] in CLOSING:
            lines[i - 1] += lines[i][0]
            lines[i] = lines[i][1:]
    lh = round(font_size * leading)
    im = Image.new('RGB', (target_w, pad_y * 2 + lh * len(lines)), paper)
    d = ImageDraw.Draw(im)
    y = pad_y
    for line in lines:
        d.text((pad_x, y), line, font=font, fill='#1A1A1A')
        for kw in keywords:
            idx = line.find(kw)
            while idx != -1:
                x0 = pad_x + probe.textlength(line[:idx], font=font)
                x1 = x0 + probe.textlength(kw, font=font)
                yy = y + font_size * 1.22
                d.line([(x0, yy), (x1, yy)], fill=RED, width=6)
                idx = line.find(kw, idx + 1)
        y += lh
    return im
