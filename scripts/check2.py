#!/usr/bin/env python3
"""check2.py — 多渠道检查：读 render2 的 render-report.json，按目标尺寸验硬红线。

用法：
    python3 check2.py 页面脚本-<渠道>.json --pages pages-<渠道> --width 1080 --height 1440
errors 为空才算通过；风格建议不在此列（人工目检）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image

PAGE_COUNTER = re.compile(r'(P\d+|第\s*\d+\s*页|p\d+)', re.I)
CLOSE_PUNCT = set('，。、：；！？…」』》）、,.!?:;·')


def main():
    a = argparse.ArgumentParser()
    a.add_argument('script', type=Path)
    a.add_argument('--pages', type=Path, required=True)
    a.add_argument('--width', type=int, required=True)
    a.add_argument('--height', type=int, required=True)
    a.add_argument('--loose', action='store_true',
                   help='宽松模式：跳过页数与封面标题数规则，用于正文配图、海报等单图/少页交付')
    v = a.parse_args()
    W, H = v.width, v.height
    scale = W / 1440

    data = json.loads(v.script.read_text(encoding='utf-8'))
    report = json.loads((v.pages / 'render-report.json').read_text(encoding='utf-8'))
    errors = []

    if len(data['pages']) != len(report):
        errors.append('脚本与渲染报告页数不一致')
    if not v.loose:
        if not (9 <= len(data['pages']) <= 13):
            errors.append('正式稿必须为封面＋8–12张内页')
        if data['pages'] and data['pages'][0].get('layout') != 'cover':
            errors.append('第一页必须为封面')

    for n, (p, r) in enumerate(zip(data['pages'], report), 1):
        tag = f'P{n:02}'
        img_path = v.pages / f'p{n:02}.png'
        if not img_path.is_file():
            errors.append(f'{tag}缺成图')
            continue
        if Image.open(img_path).size != (W, H):
            errors.append(f'{tag}成品尺寸不对，应为{W}x{H}')

        if p.get('layout') == 'cover' and not v.loose:
            titles = [e for e in p.get('elements', []) if e.get('text_role') == 'headline']
            if len(titles) != 2:
                errors.append('封面必须有两行独立大标题')

        for e in p.get('elements', []):
            if e.get('kind') == 'caption':
                errors.append(f'{tag}有图注：图上不写出处/说明')
            if e.get('kind') == 'text':
                if e.get('text_role') == 'label':
                    if e.get('size', 60) * scale < 28 * scale:
                        errors.append(f'{tag}人名标签过小：{e["text"][:12]}')
                    if re.search(r'(?i)wikimedia|commons|public domain|CC[ -]?BY|CC0|图源|来源', e['text']):
                        errors.append(f'{tag}标签里写了出处/授权：{e["text"][:12]}')
                elif e.get('size', 60) * scale < 48 * scale - 0.5:
                    # 注意：size 是 1440 基准字号，实际渲染按 W/1440 缩放
                    if e.get('size', 60) < 48:
                        errors.append(f'{tag}文字小于48px（1440基准）：{e["text"][:12]}')
                if PAGE_COUNTER.search(e['text']):
                    errors.append(f'{tag}有页码/栏目编号：{e["text"][:12]}')

        for t in r.get('text', []):
            b = t.get('ink_bounds')
            if b and (b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H):
                errors.append(f'{tag}文字墨迹越界：{t["text"][:16]}')
            if t.get('used_height', 0) > t.get('capacity_height', 0) + 1:
                errors.append(f'{tag}正文盒溢出')
            glyphs = t.get('glyphs') or []
            rows = {}
            for g in glyphs:
                rows.setdefault(g.get('line'), []).append(g.get('char', ''))
            if len(rows) > 1 and any(
                    len([c for c in v2 if c not in CLOSE_PUNCT]) < 2 for v2 in rows.values()):
                errors.append(f'{tag}有孤字行：{t["text"][:12]}')
            if t.get('font_file', {}).get('fallback'):
                errors.append(f'{tag}授权字库回退，不能视为正式接入成功')

    out = {'errors': errors, 'pages': len(report), 'size': [W, H]}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
