# redbook-video-transcript-extractor

小红书链接提取文字稿字幕工具。输入一个小红书/Redbook 分享链接，工具会自动下载视频并生成文字稿、结构化 JSON 和 SRT 字幕文件。

> 建议 GitHub 仓库名：`redbook-video-transcript-extractor`

## Features

- Paste a Xiaohongshu/Redbook share link and process it from the command line or a double-click launcher.
- Download video content through [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader).
- Generate a transcript bundle with `transcript.txt`, `transcript.json`, `transcript.srt`, `note.json`, and `meta.json`.
- Use local CPU transcription with `faster-whisper`.
- Use an OpenAI-compatible transcription API when `OPENAI_API_KEY` is configured.
- Keep generated downloads/transcripts outside the source tree by default.

## Easiest Windows Usage

1. Download or clone this repository.
2. Double-click `launcher.py`, or run it from PowerShell:

```powershell
python .\launcher.py
```

3. Paste a Xiaohongshu/Redbook share link when prompted.
4. Wait for the transcript bundle path printed at the end.

The default launcher uses local transcription:

```powershell
.\xhs-video-to-text.ps1 -Url "https://xhslink.com/xxxx" -Local -LocalModel medium -LocalLanguage zh
```

On first run, the PowerShell script prepares a portable Python runtime, installs Python dependencies, clones XHS-Downloader into `third_party\XHS-Downloader`, and stores local model/cache files under this repository.

## Output

By default, output files are written under:

```text
%USERPROFILE%\ai-media\xhs-video-transcriber\transcripts
```

Each run creates a timestamped folder containing:

- `transcript.txt`: plain text transcript.
- `transcript.json`: raw transcript payload and segments when available.
- `transcript.srt`: subtitle file, created when segment timestamps are available.
- `note.json`: metadata returned by XHS-Downloader.
- `meta.json`: local run metadata such as source video path and title.

Downloaded media is stored under:

```text
%USERPROFILE%\ai-media\xhs-video-transcriber\downloads
```

## Configuration

You can override paths with parameters:

```powershell
.\xhs-video-to-text.ps1 `
  -Url "https://xhslink.com/xxxx" `
  -Local `
  -DataRoot "D:\xhs-transcriber-data" `
  -ModelRoot "D:\xhs-models" `
  -XhsRepo "D:\redbook-transcriber\XHS-Downloader"
```

Supported environment variables:

- `XHS_COOKIE`: optional Xiaohongshu web cookie. Some links may require it.
- `OPENAI_API_KEY`: required for API transcription mode.
- `OPENAI_BASE_URL`: optional OpenAI-compatible API base URL.
- `XHS_DOWNLOADER_REPO`: use an existing local XHS-Downloader checkout.
- `XHS_TRANSCRIBER_DATA_ROOT`: override the default data directory.
- `XHS_TRANSCRIBER_DOWNLOAD_ROOT`: override the download directory.
- `XHS_TRANSCRIBER_OUTPUT_ROOT`: override the transcript output directory.
- `XHS_TRANSCRIBER_MODEL_ROOT`: override the local Whisper model directory.
- `XHS_TRANSCRIBER_PY_HOME`: override the embedded Python directory.
- `XHS_TRANSCRIBER_UV_CACHE`: override the uv cache directory.
- `XHS_TRANSCRIBER_UV_BIN`: override the local uv binary directory.

## API Mode

Local mode is the default recommendation for one-click use. To use an OpenAI-compatible transcription API instead:

```powershell
$env:OPENAI_API_KEY = "sk-..."
.\xhs-video-to-text.ps1 -Url "https://xhslink.com/xxxx" -Model "whisper-1"
```

If your provider uses a custom endpoint:

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_BASE_URL = "https://your-provider.example/v1"
.\xhs-video-to-text.ps1 -Url "https://xhslink.com/xxxx" -Model "whisper-1"
```

API mode keeps the original 25 MB upload limit check for transcription requests.

## Project Layout

```text
.
├── launcher.py
├── xhs-video-to-text.ps1
├── xhs_to_transcript.py
├── XhsVideoToText.spec
└── packaging
    ├── XhsVideoToText.cs
    └── launch-xhs-video-to-text.cmd
```

Generated local-only folders such as `python312-embed`, `.cache`, `third_party`, `models`, `downloads`, and `transcripts` are intentionally ignored by Git.

## Packaging

For public GitHub releases, prefer this structure:

- Keep source code in the repository.
- Put built executables in GitHub Releases assets instead of committing them to Git.
- Include `XhsVideoToText.exe`, `xhs-video-to-text.ps1`, and `xhs_to_transcript.py` together if using an external wrapper release package.

PyInstaller users can build from the included spec:

```powershell
pyinstaller .\XhsVideoToText.spec
```

The spec uses paths relative to the repository root and bundles the PowerShell/helper scripts as data for the launcher.

## Notes and Limitations

- This project is currently Windows-first and expects PowerShell.
- First run requires network access to download portable Python, install uv/dependencies, and clone XHS-Downloader.
- Local CPU transcription can be slow, especially with larger Whisper models.
- Local models and caches may take several GB of disk space.
- Some Xiaohongshu links may require `XHS_COOKIE`.
- Do not commit cookies, API keys, downloaded videos, transcripts, local models, or cache folders.

## Legal and Platform Notice

Use this tool only for content you are allowed to access and process. Respect Xiaohongshu/Redbook's terms, copyright, privacy, and local law.
