# Picture Book Page Extractor Skill

一个用于 Codex 的绘本视频逐页提取技能。它会比较前后帧、识别翻页和稳定页面，把视频中的封面、单页和跨页整理成有顺序的图片，并在不改写文字与插画的前提下清理背景、校正透视和提升清晰度。

## 能做什么

- 结合帧差、感知相似度、页面边界和持续时间识别真正的翻页。
- 合并同一页面的平移、缩放、旋转和不同曝光画面。
- 从多个真实视频帧重建完整页面，减少手部、反光、模糊和遮挡。
- 区分封面、单页、双页跨页、扉页、封底、局部页和不确定页面。
- 去除桌面、墙面、黑边、播放器界面、片头片尾、广告和无关频道元素。
- 按页面类型统一尺寸，使用留白适配而不是拉伸或裁掉书籍内容。
- 生成自然、保真、扫描感三种增强结果，并保护印刷文字的像素结构。
- 输出按顺序编号的页面、`manifest.json`、联系表和待人工复核候选。

## 安装

克隆仓库：

```powershell
git clone https://github.com/cenzuook/picture-book-page-extractor-skill.git
```

把技能目录复制到 Codex 的个人技能目录：

```powershell
Copy-Item -Recurse ".\picture-book-page-extractor-skill\skills\extract-picture-book-pages" "$env:USERPROFILE\.codex\skills\"
```

也可以让 Codex 直接从这个 GitHub 仓库中的 `skills/extract-picture-book-pages` 安装技能。

## 使用

在 Codex 中上传或提供绘本视频，然后说：

```text
使用 $extract-picture-book-pages 分析这个绘本视频，按顺序提取每一页，去掉无关背景和广告，保留文字与插画原样，并生成清晰、像扫描件一样的页面。
```

技能内置的确定性处理入口：

```powershell
python skills/extract-picture-book-pages/scripts/process_book_video.py `
  --input "<video>" `
  --output "<output-dir>"

python skills/extract-picture-book-pages/scripts/verify_pages.py `
  --input "<output-dir>"
```

使用 `--help` 查看采样、画布、跨页、保真和分辨率选项。

## 运行依赖

- Python 3.10+
- FFmpeg 与 FFprobe
- Pillow
- NumPy
- OpenCV（可选；用于更高级的对齐与透视校正）

```powershell
python -m pip install Pillow numpy
python -m pip install opencv-python  # 可选
```

## 目录结构

```text
skills/extract-picture-book-pages/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── detection-profiles.md
│   ├── enhancement-and-text.md
│   ├── page-geometry.md
│   ├── quality-gates.md
│   └── reconstruction.md
└── scripts/
    ├── process_book_video.py
    ├── reconstruct_page.py
    └── verify_pages.py
```

## 保真原则

该技能优先恢复真实视频中已经存在的内容，不使用生成式填充重写印刷文字或补画从未出现的区域。若所有源帧都缺少某一部分，它会把页面标记为不完整或不确定，而不是猜测内容。

## License

[MIT](LICENSE)
