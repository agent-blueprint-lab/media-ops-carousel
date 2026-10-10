# 主题系统 themes

cy-carousel 原版只有暗底/纸底两套，且水印写死作者名。本 skill 的主题全部走配置，换主题=换一套参数，不改排版代码。

## 用法

```python
from layout import set_channel, apply_theme, THEMES
set_channel('xiaohongshu')
apply_theme('brand-blue')   # 或 'dark' / 'paper' / 自定义 dict
```

`apply_theme(name_or_dict)` 会覆盖：底色、标题两行颜色、强调色、正文字体、正文颜色、纸条纸色。排版代码里只写 `headline/big/body`，不写死颜色。

## 内置主题

| 主题 | 底色 | 标题行1/行2 | 强调色 | 正文字体 | 适合 |
|---|---|---|---|---|---|
| `dark`（默认） | #080808 | 米白 #F3F1E9 / 电子青 #00E5FF | #00E5FF | 文楷 | 科技、知识、深度内容 |
| `paper` | #F5F1E8 纸色 | 墨黑 #1A1A1A / 朱砂红 #C92928 | #C92928 | 文楷 | 文化、历史、人文 |
| `brand-blue` | #0A1A33 深蓝 | 白 #FFFFFF / 亮蓝 #4DA6FF | #4DA6FF | 文楷 | 企业、产品、品牌稿 |

## 自定义主题

在任务笔记目录建 `theme.json`，例如：

```json
{
  "background": "#0B0B0C",
  "title_line1": "#F3F1E9",
  "title_line2": "#FFB300",
  "accent": "#FFB300",
  "body_font": "文楷",
  "body_fill": "#EDEDE6",
  "paper": "#F4EFE4",
  "watermark_text": "你的账号名"
}
```

`apply_theme('theme.json')` 直接读文件。**水印必须从配置读**，不许写死任何人名；不知道账号名就设 `""` 关闭水印。

## 规则

- 一篇内容只用一个主题，不混搭。
- 强调色只用于：标题第二行、大数字、关键词标注、贴条底色；正文不用强调色。
- 纸条（paper_strip）纸色跟主题走，`paper` 参数可覆盖。
