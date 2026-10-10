#!/usr/bin/env python3
"""render2.py — cy-carousel render.py 的多尺寸渲染入口。

实现方式：运行时读取引擎 render.py 源码，打两处补丁后 exec：
  1. render() 签名加 height 参数；
  2. 去掉 width!=1440 的硬限制，H 改为 height（缺省则按 4:3）。
补丁锚点命中失败会直接报错（引擎升级后按报错信息更新锚点）。
引擎：MIT 协议，https://github.com/chengyi-ai/cy-carousel-skill
"""
import argparse
import sys
from pathlib import Path

SIG_OLD = "def render(script,out,width=1440,assets_root=None):"
SIG_NEW = "def render(script,out,width=1440,height=None,assets_root=None):"
BODY_OLD = (" if width!=1440:raise ValueError('成品固定1440×1920；预览另用拼图脚本等比裁切')\n"
            " W=width;H=width*4//3;")
BODY_NEW = " W=width;H=(height or width*4//3);"


def main():
    a = argparse.ArgumentParser(description='多尺寸渲染（cy-carousel 引擎补丁入口）')
    a.add_argument('script', type=Path)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--width', type=int, default=1440)
    a.add_argument('--height', type=int, default=None)
    a.add_argument('--engine', type=Path, required=True, help='cy-carousel 仓库根目录')
    a.add_argument('--assets-root', type=Path)
    v = a.parse_args()

    eng_scripts = v.engine / 'scripts'
    if not (eng_scripts / 'render.py').is_file():
        raise SystemExit(f'引擎目录不对，找不到 {eng_scripts / "render.py"}')
    sys.path.insert(0, str(eng_scripts))
    src = (eng_scripts / 'render.py').read_text(encoding='utf-8')
    assert SIG_OLD in src, '引擎 render.py 签名已变更，请更新 render2.py 补丁锚点'
    assert BODY_OLD in src, '引擎 render.py 宽度限制处已变更，请更新 render2.py 补丁锚点'
    src = src.replace(SIG_OLD, SIG_NEW).replace(BODY_OLD, BODY_NEW)
    g = {'__file__': str(eng_scripts / 'render.py'), '__name__': 'render2_patched'}
    exec(compile(src, 'render2_patched', 'exec'), g)
    h = v.height or v.width * 4 // 3
    n = len(g['render'](v.script.resolve(), v.out.resolve(), v.width, v.height, v.assets_root))
    print(f'Rendered {n} pages at {v.width}x{h}')


if __name__ == '__main__':
    main()
