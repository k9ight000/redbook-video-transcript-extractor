import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def sanitize_filename(value: str, fallback: str = "xhs_video") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" .")
    return cleaned[:120] or fallback


def fmt_time(seconds: float) -> str:
    millis = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def fmt_srt_time(seconds: float) -> str:
    return fmt_time(seconds).replace(".", ",")


def find_latest_video(download_root: Path, start_time: float) -> Path:
    candidates = [p for p in download_root.rglob("*") if p.is_file() and p.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"}]
    if not candidates:
        raise FileNotFoundError(f"No downloaded video file found under {download_root}")
    recent = [p for p in candidates if p.stat().st_mtime >= start_time - 5]
    return max(recent or candidates, key=lambda p: p.stat().st_mtime)


def find_latest_note_json(download_root: Path, start_time: float) -> dict:
    candidates = [p for p in download_root.rglob("*.json") if p.is_file()]
    recent = [p for p in candidates if p.stat().st_mtime >= start_time - 5]
    source = recent or candidates
    if not source:
        return {}
    latest = max(source, key=lambda p: p.stat().st_mtime)
    try:
        return json.loads(latest.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def pick_title(data: dict, video_path: Path) -> str:
    if isinstance(data, dict):
        for key in ("作品标题", "标题", "title", "desc", "描述"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return video_path.stem


def download_with_node(url: str, target: Path) -> None:
    node_exe = shutil.which("node")
    if not node_exe:
        raise RuntimeError("Node.js is not installed or not in PATH.")

    script = r"""
const fs = require('fs');
const https = require('https');
const { URL } = require('url');

const url = process.argv[1];
const target = process.argv[2];

function fetch(currentUrl, redirects) {
  const parsed = new URL(currentUrl);
  const req = https.get({
    hostname: parsed.hostname,
    path: parsed.pathname + parsed.search,
    protocol: parsed.protocol,
    headers: { 'User-Agent': 'redbook-video-transcript-extractor/1.0' },
  }, (res) => {
    if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location && redirects > 0) {
      const nextUrl = new URL(res.headers.location, currentUrl).toString();
      res.resume();
      return fetch(nextUrl, redirects - 1);
    }
    if (res.statusCode !== 200) {
      console.error(`HTTP ${res.statusCode} for ${currentUrl}`);
      res.resume();
      process.exit(1);
    }
    const output = fs.createWriteStream(target);
    res.pipe(output);
    output.on('finish', () => output.close(() => process.exit(0)));
    output.on('error', (err) => {
      console.error(err.message || String(err));
      process.exit(1);
    });
  });
  req.on('error', (err) => {
    console.error(err.message || String(err));
    process.exit(1);
  });
}

fetch(url, 6);
"""
    result = subprocess.run(
        [node_exe, "-e", script, url, str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "unknown node download error"
        raise RuntimeError(detail)


def download_file(url: str, target: Path) -> None:
    part = target.with_suffix(target.suffix + ".part")
    if part.exists():
        part.unlink(missing_ok=True)

    last_error = None
    try:
        import httpx

        headers = {"User-Agent": "redbook-video-transcript-extractor/1.0"}
        with httpx.Client(follow_redirects=True, headers=headers, timeout=None, http2=False) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with part.open("wb") as output:
                    for chunk in response.iter_bytes(1024 * 1024):
                        if chunk:
                            output.write(chunk)
        part.replace(target)
        return
    except Exception as exc:
        last_error = exc
        if part.exists():
            part.unlink(missing_ok=True)

    try:
        download_with_node(url, part)
        part.replace(target)
        return
    except Exception as exc:
        last_error = exc
        if part.exists():
            part.unlink(missing_ok=True)

    raise RuntimeError(str(last_error) if last_error else f"Failed to download {url}")


def ensure_faster_whisper_model(model_name: str, model_root: Path) -> str:
    candidate = Path(model_name)
    if candidate.exists():
        return str(candidate.resolve())

    if model_name.startswith("Systran/faster-whisper-"):
        repo_id = model_name
        local_name = model_name.split("/")[-1]
    else:
        repo_id = f"Systran/faster-whisper-{model_name}"
        local_name = f"faster-whisper-{model_name}"

    local_dir = model_root / local_name
    local_dir.mkdir(parents=True, exist_ok=True)

    required = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
    base_urls = [
        "https://hf-mirror.com",
        "https://huggingface.co",
    ]

    for filename in required:
        target = local_dir / filename
        if target.exists() and target.stat().st_size > 0:
            continue

        last_error = None
        for base_url in base_urls:
            url = f"{base_url}/{repo_id}/resolve/main/{filename}"
            for attempt in range(1, 4):
                try:
                    print(
                        f"Downloading local Whisper model file: {repo_id}/{filename} from {base_url} (attempt {attempt})",
                        file=sys.stderr,
                    )
                    download_file(url, target)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    time.sleep(1.5 * attempt)
            if last_error is None:
                break
        if last_error is not None:
            raise RuntimeError(f"Failed to download model file {repo_id}/{filename}: {last_error}")

    return str(local_dir.resolve())


async def run_xhs_download(url: str, xhs_repo: Path, download_root: Path, cookie: str) -> None:
    sys.path.insert(0, str(xhs_repo))
    from source import XHS

    async with XHS(
        work_path=str(download_root),
        folder_name="Download",
        cookie=cookie or "",
        record_data=True,
        image_download=False,
        video_download=True,
        live_download=False,
        download_record=False,
        language="zh_CN",
    ) as xhs:
        data = await xhs.extract(url, True)
        if not data:
            raise RuntimeError("XHS-Downloader did not return note data.")


def transcribe_video_api(video_path: Path, model: str, api_key: str, base_url: str = "") -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    with video_path.open("rb") as file_handle:
        response = client.audio.transcriptions.create(model=model, file=file_handle, response_format="json")
    if hasattr(response, "model_dump"):
        payload = response.model_dump()
    elif isinstance(response, dict):
        payload = response
    else:
        payload = {"text": str(response)}
    if not isinstance(payload.get("text"), str) or not payload["text"].strip():
        raise RuntimeError("Transcription response did not include transcript text.")
    return payload


def transcribe_video_local(video_path: Path, model_name: str, model_root: Path, language: str = "") -> dict:
    from faster_whisper import WhisperModel

    model_path = ensure_faster_whisper_model(model_name, model_root)
    model = WhisperModel(
        model_path,
        device="cpu",
        compute_type="int8",
        cpu_threads=max(1, min(os.cpu_count() or 4, 8)),
    )
    lang = language.strip() or None
    segments_iter, info = model.transcribe(
        str(video_path),
        language=lang,
        vad_filter=True,
        beam_size=5,
    )
    segments = []
    for idx, segment in enumerate(segments_iter, 1):
        text = segment.text.strip()
        if not text:
            continue
        segments.append({
            "id": idx,
            "start": float(segment.start),
            "end": float(segment.end),
            "text": text,
        })
    full_text = "\n".join(s["text"] for s in segments).strip()
    if not full_text:
        raise RuntimeError("Local transcription returned no text.")
    return {
        "text": full_text,
        "segments": segments,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration": getattr(info, "duration", None),
        "engine": "faster-whisper",
        "local_model": model_name,
    }


def write_bundle(output_root: Path, title: str, video_path: Path, note_data: dict, transcript_payload: dict) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_title = sanitize_filename(title, fallback=video_path.stem)
    bundle_root = output_root / f"{timestamp}-{safe_title}"
    bundle_root.mkdir(parents=True, exist_ok=True)
    transcript_txt = bundle_root / "transcript.txt"
    transcript_json = bundle_root / "transcript.json"
    transcript_srt = bundle_root / "transcript.srt"
    note_json = bundle_root / "note.json"
    meta_json = bundle_root / "meta.json"

    transcript_txt.write_text(transcript_payload["text"], encoding="utf-8")
    transcript_json.write_text(json.dumps(transcript_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    note_json.write_text(json.dumps(note_data, ensure_ascii=False, indent=2), encoding="utf-8")

    segments = transcript_payload.get("segments") or []
    if segments:
        srt_parts = []
        for idx, segment in enumerate(segments, 1):
            srt_parts.append(str(idx))
            srt_parts.append(f"{fmt_srt_time(segment['start'])} --> {fmt_srt_time(segment['end'])}")
            srt_parts.append(segment["text"])
            srt_parts.append("")
        transcript_srt.write_text("\n".join(srt_parts), encoding="utf-8")

    meta_json.write_text(json.dumps({"video_file": str(video_path), "created_at": datetime.now().isoformat(), "title": title}, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {
        "bundle_root": str(bundle_root),
        "transcript_txt": str(transcript_txt),
        "transcript_json": str(transcript_json),
        "note_json": str(note_json),
        "meta_json": str(meta_json),
    }
    if transcript_srt.exists():
        result["transcript_srt"] = str(transcript_srt)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--model", default="whisper-1")
    parser.add_argument("--xhs-repo", required=True)
    parser.add_argument("--download-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--local-model", default="medium")
    parser.add_argument("--local-language", default="")
    parser.add_argument("--model-root", default="")
    args = parser.parse_args()

    cookie = os.environ.get("XHS_COOKIE", "")
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL", "")
    xhs_repo = Path(args.xhs_repo).resolve()
    download_root = Path(args.download_root).resolve()
    output_root = Path(args.output_root).resolve()
    model_root = Path(args.model_root).resolve() if args.model_root else Path.cwd() / "models"
    if not xhs_repo.exists():
        raise FileNotFoundError(f"XHS-Downloader repo not found: {xhs_repo}")
    download_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    model_root.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    asyncio.run(run_xhs_download(args.url, xhs_repo, download_root, cookie))
    search_root = download_root / "Download"
    root = search_root if search_root.exists() else download_root
    video_path = find_latest_video(root, start_time)
    note_data = find_latest_note_json(root, start_time)
    size_mb = video_path.stat().st_size / (1024 * 1024)

    if args.local:
        transcript_payload = transcribe_video_local(video_path, args.local_model, model_root, args.local_language)
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set. Use -Local for offline transcription or set OPENAI_API_KEY for API transcription.")
        if size_mb > 25:
            raise RuntimeError(f"Downloaded file is {size_mb:.1f} MB, which exceeds the 25 MB transcription upload limit: {video_path}")
        transcript_payload = transcribe_video_api(video_path, args.model, api_key, base_url)

    title = pick_title(note_data, video_path)
    bundle = write_bundle(output_root, title, video_path, note_data, transcript_payload)
    print(json.dumps({
        "message": "success",
        "title": title,
        "video_path": str(video_path),
        "video_size_mb": round(size_mb, 2),
        "mode": "local" if args.local else "api",
        "model": args.local_model if args.local else args.model,
        "base_url": "" if args.local else base_url,
        **bundle,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
