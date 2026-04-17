# 小红书链接提取文字稿字幕 / Redbook Video Transcript Extractor

中文名：小红书链接提取文字稿字幕  
English name: Redbook Video Transcript Extractor
Repository name: `redbook-video-transcript-extractor`

输入一个小红书/Redbook 分享链接，自动下载视频，并生成文字稿、JSON 结果和 SRT 字幕文件。这个项目优先面向中文用户，README 采用中文为主、英文辅助的形式。

Paste a Xiaohongshu/Redbook share link, download the video, and export transcript text, JSON data, and SRT subtitles. This repository is primarily written for Chinese-speaking users, with English notes included where helpful.

## 功能 Features

- 输入小红书分享链接，自动处理视频下载和转写。
- 支持命令行运行，也支持 Windows 双击式启动体验。
- 通过 [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) 下载小红书视频。
- 输出 `transcript.txt`、`transcript.json`、`transcript.srt`、`note.json`、`meta.json`。
- 支持本地 `faster-whisper` 转写，适合不想上传音视频的场景。
- 支持 OpenAI-compatible transcription API，适合有 API key、希望更快处理的场景。
- 默认把下载视频和转写结果放在用户目录，不污染源码仓库。

## 最简单的 Windows 用法

如果你只是想一键使用，推荐下载 GitHub Releases 里的 Windows zip：

1. 下载 `redbook-video-transcript-extractor-windows-x64.zip`。
2. 解压到一个普通文件夹，例如桌面或 `D:\Tools\redbook-video-transcript-extractor`。
3. 双击 `XhsVideoToText.exe`。
4. 粘贴小红书分享链接，然后回车。

如果你是从源码运行：

1. 下载或 clone 这个仓库。
2. 双击 `launcher.py`，或在 PowerShell 中运行：

```powershell
python .\launcher.py
```

3. 根据提示粘贴小红书分享链接。
4. 等待处理完成，终端会打印输出文件夹路径。

默认启动器使用本地转写模式：

```powershell
.\xhs-video-to-text.ps1 -Url "https://xhslink.com/xxxx" -Local -LocalModel medium -LocalLanguage zh
```

第一次运行时，脚本会自动准备便携 Python、安装依赖、把 XHS-Downloader clone 到 `third_party\XHS-Downloader`，并把模型和缓存放到仓库内的本地目录。

## 输出文件

默认转写结果目录：

```text
%USERPROFILE%\ai-media\xhs-video-transcriber\transcripts
```

每次运行会创建一个带时间戳的文件夹，里面包含：

- `transcript.txt`：纯文本文字稿。
- `transcript.json`：结构化转写结果，包含分段信息时会保留 segments。
- `transcript.srt`：字幕文件，有时间轴分段时生成。
- `note.json`：XHS-Downloader 返回的小红书笔记信息。
- `meta.json`：本次运行的本地元信息，例如视频路径、标题、创建时间。

默认下载视频目录：

```text
%USERPROFILE%\ai-media\xhs-video-transcriber\downloads
```

## 路径配置

可以通过参数覆盖默认路径：

```powershell
.\xhs-video-to-text.ps1 `
  -Url "https://xhslink.com/xxxx" `
  -Local `
  -DataRoot "D:\xhs-transcriber-data" `
  -ModelRoot "D:\xhs-models" `
  -XhsRepo "D:\redbook-transcriber\XHS-Downloader"
```

支持的环境变量：

- `XHS_COOKIE`：可选，小红书网页 Cookie。部分链接可能需要。
- `OPENAI_API_KEY`：API 转写模式需要。
- `OPENAI_BASE_URL`：可选，OpenAI-compatible API 地址。
- `XHS_DOWNLOADER_REPO`：使用已有的本地 XHS-Downloader 目录。
- `XHS_TRANSCRIBER_DATA_ROOT`：覆盖默认数据目录。
- `XHS_TRANSCRIBER_DOWNLOAD_ROOT`：覆盖下载目录。
- `XHS_TRANSCRIBER_OUTPUT_ROOT`：覆盖转写结果目录。
- `XHS_TRANSCRIBER_MODEL_ROOT`：覆盖本地 Whisper 模型目录。
- `XHS_TRANSCRIBER_PY_HOME`：覆盖便携 Python 目录。
- `XHS_TRANSCRIBER_UV_CACHE`：覆盖 uv 缓存目录。
- `XHS_TRANSCRIBER_UV_BIN`：覆盖本地 uv 程序目录。

## API 转写模式

如果不想使用本地转写，也可以使用 OpenAI-compatible transcription API：

```powershell
$env:OPENAI_API_KEY = "sk-..."
.\xhs-video-to-text.ps1 -Url "https://xhslink.com/xxxx" -Model "whisper-1"
```

如果你的服务商使用自定义 API 地址：

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_BASE_URL = "https://your-provider.example/v1"
.\xhs-video-to-text.ps1 -Url "https://xhslink.com/xxxx" -Model "whisper-1"
```

注意：API 模式保留 25 MB 上传限制检查，视频太大时建议使用本地模式。

## 项目结构

```text
.
|-- launcher.py
|-- xhs-video-to-text.ps1
|-- xhs_to_transcript.py
|-- XhsVideoToText.spec
`-- packaging
    |-- XhsVideoToText.cs
    `-- launch-xhs-video-to-text.cmd
```

这些目录通常是本地生成的，不应该提交到 Git：

- `python312-embed`
- `.cache`
- `third_party`
- `models`
- `downloads`
- `transcripts`

## 打包和发布建议

公开 GitHub 仓库建议只放源码，不直接提交 `.exe`。

更推荐的发布方式：

- 源码放在仓库里。
- 打包好的 `XhsVideoToText.exe` 放到 GitHub Releases 附件。
- 如果做 release zip，建议把 `XhsVideoToText.exe`、`xhs-video-to-text.ps1`、`xhs_to_transcript.py` 放在同一个目录。

PyInstaller 打包：

```powershell
pyinstaller .\XhsVideoToText.spec
```

当前 spec 已经改成基于仓库目录的相对路径，并会把 PowerShell 脚本和 Python helper 作为 data 一起打包。

## 依赖和限制

- 当前项目偏 Windows，依赖 PowerShell。
- 第一次运行需要联网下载便携 Python、安装 uv/依赖、clone XHS-Downloader。
- 本地 CPU 转写可能比较慢，模型越大越慢。
- 本地模型和缓存可能占用数 GB 磁盘空间。
- 部分小红书链接可能需要设置 `XHS_COOKIE`。
- 不要提交 API key、Cookie、下载视频、转写结果、本地模型和缓存目录。

## English Quick Start

This is a Windows-first tool for extracting transcripts/subtitles from Xiaohongshu/Redbook video links.

For one-click usage, download `redbook-video-transcript-extractor-windows-x64.zip` from GitHub Releases, unzip it, and double-click `XhsVideoToText.exe`.

```powershell
python .\launcher.py
```

Or run the PowerShell script directly:

```powershell
.\xhs-video-to-text.ps1 -Url "https://xhslink.com/xxxx" -Local -LocalModel medium -LocalLanguage zh
```

Use API mode with:

```powershell
$env:OPENAI_API_KEY = "sk-..."
.\xhs-video-to-text.ps1 -Url "https://xhslink.com/xxxx" -Model "whisper-1"
```

## 法律和平台说明

请只处理你有权访问和使用的内容。使用本工具时请遵守小红书/Redbook 平台规则、版权要求、隐私要求和当地法律。

Use this tool only for content you are allowed to access and process. Respect Xiaohongshu/Redbook's terms, copyright, privacy, and local law.
