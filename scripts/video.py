#!/usr/bin/env python3
"""video.py — 抖音视频模式：关键帧 + TTS 口播 + 字幕 + 进度条 → 竖屏 MP4。

输入：--pages 图目录（1080×1920 最佳；其它尺寸自动虚化填充到 1080×1920），
      --narration narration.json [{"image": "01-封面.png", "text": "口播文案"}, ...]
流程：每页 tts 配音 → 按句切分估算时间轴 → 30fps 逐帧渲染（慢推+字幕+进度条）
      → ffmpeg 合成 1080×1920 H.264 + AAC。
字幕为句子级（按字数比例估算句时），文字全部代码绘制，保证清晰。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30
PAD_HEAD, PAD_TAIL = 0.4, 0.6
ACCENT = '#00E5FF'
TTS_CMD = 'tts'  # 可被 --tts-cmd 覆盖；期望接口：tts speak --language <code> --output <path> --text-stdin < text


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f'命令失败: {cmd}\n{r.stderr[-2000:]}')
    return r


def tts_speak(text, out, tts_cmd):
    r = run([tts_cmd, 'speak', '--language', 'zh', '--output', str(out), '--text-stdin'],
            input=text)
    return json.loads(r.stdout)['path']


def audio_dur(path):
    r = run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)])
    return float(json.loads(r.stdout)['format']['duration'])


def check_audio(path, max_silence=2.5):
    """TTS 静音质检：单段配音里不许出现超过 max_silence 秒的静音（防 TTS 截断）。"""
    r = subprocess.run(
        ['ffmpeg', '-hide_banner', '-i', str(path),
         '-af', f'silencedetect=noise=-40dB:d={max_silence}', '-f', 'null', '-'],
        capture_output=True, text=True)
    bad = [l for l in r.stderr.splitlines() if 'silence_duration' in l]
    if bad:
        raise RuntimeError(f'TTS 音频有超长静音（>{max_silence}s），疑似截断：{path}\n' + '\n'.join(bad))


def split_sentences(text):
    parts = [p for p in re.split(r'(?<=[。！？；])', text) if p.strip()]
    return parts or [text]


def wrap_idx(sent, font, draw, max_w, limit=2):
    """换行并返回每行的字符区间 [(a,b), ...]。"""
    ranges, cur, start = [], '', 0
    i = 0
    n = len(sent)
    while i < n:
        ch = sent[i]
        if draw.textlength(cur + ch, font=font) <= max_w:
            cur += ch
            i += 1
        else:
            ranges.append((start, start + len(cur)))
            start += len(cur)
            cur = ''
            if len(ranges) >= limit:
                return ranges
    if cur and len(ranges) < limit:
        ranges.append((start, start + len(cur)))
    return ranges


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--pages', type=Path, required=True)
    a.add_argument('--narration', type=Path, required=True)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--engine', type=Path, required=True, help='渲染引擎仓库根目录（取字体）')
    a.add_argument('--tts-cmd', default=TTS_CMD,
                   help='TTS 命令（默认 tts，需支持: tts speak --language <code> --output <path> --text-stdin）。也可用 edge-tts 等自行封装。')
    a.add_argument('--workdir', type=Path, default=Path('video-work'))
    v = a.parse_args()
    tts_cmd = v.tts_cmd

    segs = json.loads(v.narration.read_text(encoding='utf-8'))
    v.workdir.mkdir(parents=True, exist_ok=True)
    font_sub = ImageFont.truetype(
        str(v.engine / 'assets/fonts/NotoSansSC[wght].ttf'), 46, index=0)
    try:
        font_sub.set_variation_by_axes([700])
    except Exception:
        pass
    font_hud = ImageFont.truetype(
        str(v.engine / 'assets/fonts/NotoSansSC[wght].ttf'), 30, index=0)

    # 1. 配音 + 时间轴
    timeline = []
    for i, s in enumerate(segs):
        mp3 = v.workdir / f'seg{i:02}.mp3'
        if not mp3.is_file():
            tts_speak(s['text'], mp3, tts_cmd)
        check_audio(mp3)  # 防 TTS 截断：超长静音直接报错
        dur = audio_dur(mp3)
        sents = split_sentences(s['text'])
        total_chars = sum(len(x) for x in sents)
        t = PAD_HEAD
        marks = []
        for sent in sents:
            sd = dur * len(sent) / max(1, total_chars)
            marks.append((t, t + sd, sent))
            t += sd
        seg_dur = PAD_HEAD + dur + PAD_TAIL
        timeline.append({'image': s['image'], 'mp3': mp3, 'dur': seg_dur,
                         'audio': dur, 'marks': marks})
        print(f'seg{i:02} {s["image"]}: audio {dur:.1f}s -> seg {seg_dur:.1f}s, {len(sents)}句')

    total_dur = sum(s['dur'] for s in timeline)
    total_frames = round(total_dur * FPS)
    print(f'总时长 {total_dur:.1f}s, {total_frames}帧')

    # 2. 拼整轨音频（先音频，后开 ffmpeg）
    lst = v.workdir / 'concat.txt'
    with open(lst, 'w', encoding='utf-8') as f:
        for i, s in enumerate(timeline):
            seg_wav = v.workdir / f'seg{i:02}_pad.m4a'
            if not seg_wav.is_file():
                run(['ffmpeg', '-y', '-v', 'quiet', '-i', str(s['mp3']),
                     '-af', f'adelay={int(PAD_HEAD*1000)}|{int(PAD_HEAD*1000)},apad=pad_dur={s["dur"]:.3f}',
                     '-t', f'{s["dur"]:.3f}', '-c:a', 'aac', str(seg_wav)])
            f.write(f"file '{seg_wav.resolve()}'\n")
    run(['ffmpeg', '-y', '-v', 'quiet', '-f', 'concat', '-safe', '0',
         '-i', str(lst), '-c', 'copy', str(v.workdir / 'audio_full.m4a')])

    # 3. 逐帧渲染 → pipe 给 ffmpeg
    ff = subprocess.Popen(
        ['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
         '-r', str(FPS), '-i', '-',
         '-i', str(v.workdir / 'audio_full.m4a'),
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '23',
         '-c:a', 'aac', '-b:a', '128k', '-shortest', str(v.out)],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frame_idx = 0
    elapsed = 0.0
    for si, s in enumerate(timeline):
        img = Image.open(v.pages / s['image']).convert('RGB')
        # 背景：cover 填充 + 虚化压暗
        bg = img.resize((W, round(W * img.height / img.width)), Image.LANCZOS)
        if bg.height < H:
            bg = img.resize((round(H * img.width / img.height), H), Image.LANCZOS)
        x0 = (bg.width - W) // 2
        y0 = (bg.height - H) // 2
        bg = bg.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new('RGB', (W, H), (0, 0, 0)), 0.45)
        base_w = W
        base_h = round(W * img.height / img.width)
        n_frames = round(s['dur'] * FPS)
        for fi in range(n_frames):
            t_seg = fi / FPS
            t_abs = elapsed + t_seg
            z = 1.0 + 0.05 * (fi / max(1, n_frames - 1))  # 慢推
            fw, fh = round(base_w * z), round(base_h * z)
            fg = img.resize((fw, fh), Image.LANCZOS)
            frame = bg.copy()
            frame.paste(fg, ((W - fw) // 2, (H - fh) // 2))
            d = ImageDraw.Draw(frame, 'RGBA')
            # 字幕：当前句（按估算时间轴）
            cur = next((m for m in s['marks'] if m[0] <= t_seg < m[1]), None)
            if cur:
                _, _, sent = cur
                ranges = wrap_idx(sent, font_sub, d, W - 160)
                lh = 64
                bh = lh * len(ranges) + 44
                by = H - 60 - bh  # 贴底，避开页面内容区
                d.rounded_rectangle([60, by, W - 60, by + bh], radius=18, fill=(0, 0, 0, 150))
                spoken_ratio = min(1.0, max(0.0, (t_seg - cur[0]) / max(0.01, cur[1] - cur[0])))
                spoken_n = round(len(sent) * spoken_ratio)
                y = by + 22
                for (a, b) in ranges:
                    line = sent[a:b]
                    d.text((80, y), line, font=font_sub, fill=(255, 255, 255, 120))
                    if spoken_n > a:
                        d.text((80, y), sent[a:min(b, spoken_n)], font=font_sub, fill=ACCENT)
                    y += lh
            # HUD：页码
            d.text((W - 140, 60), f'{si+1}/{len(timeline)}', font=font_hud,
                   fill=(255, 255, 255, 160))
            # 进度条
            pw = (frame_idx + 1) / total_frames
            d.rectangle([0, H - 8, W * pw, H], fill=ACCENT)
            ff.stdin.write(frame.tobytes())
            frame_idx += 1
        elapsed += s['dur']
    ff.stdin.close()
    ff.wait()
    print('done:', v.out, f'{frame_idx}帧')


if __name__ == '__main__':
    main()
