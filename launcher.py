import subprocess
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_dir():
    root = getattr(sys, "_MEIPASS", None)
    return Path(root).resolve() if root else None


def copy_bundled_file(name: str, target_dir: Path) -> None:
    source_root = bundled_dir()
    if not source_root:
        return
    source = source_root / name
    target = target_dir / name
    if target.exists() or not source.exists():
        return
    try:
        target.write_bytes(source.read_bytes())
    except OSError:
        # Fall back to PyInstaller's extraction dir if the exe dir is read-only.
        pass


def find_ps_script():
    current_app_dir = app_dir()
    if getattr(sys, "frozen", False):
        copy_bundled_file("xhs-video-to-text.ps1", current_app_dir)
        copy_bundled_file("xhs_to_transcript.py", current_app_dir)

    candidates = [
        current_app_dir / "xhs-video-to-text.ps1",
        Path(__file__).resolve().parent / "xhs-video-to-text.ps1",
    ]
    source_root = bundled_dir()
    if source_root:
        candidates.append(source_root / "xhs-video-to-text.ps1")
    candidates.extend([
        Path.cwd() / "xhs-video-to-text.ps1",
        Path.home() / "xhs-video-to-text.ps1",
    ])

    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            return resolved
    return None


def pause(message: str) -> None:
    if sys.stdin and sys.stdin.isatty():
        try:
            input(message)
        except EOFError:
            pass


def main() -> int:
    ps_script = find_ps_script()
    if not ps_script:
        print("未找到脚本: xhs-video-to-text.ps1")
        pause("按回车退出...")
        return 1

    if len(sys.argv) > 1:
        url = sys.argv[1].strip()
    else:
        print("请输入小红书分享链接，然后按回车：")
        try:
            url = input().strip()
        except EOFError:
            url = ""

    if not url:
        print("没有输入链接。")
        pause("按回车退出...")
        return 1

    cmd = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ps_script),
        "-Url",
        url,
        "-Local",
        "-LocalModel",
        "medium",
        "-LocalLanguage",
        "zh",
    ]

    try:
        result = subprocess.run(cmd)
        code = result.returncode
    except KeyboardInterrupt:
        code = 130
    except Exception as exc:
        print(f"启动失败: {exc}")
        code = 1

    if code != 0:
        print("处理结束，但有报错。")
        pause("按回车退出...")
    else:
        print("处理完成。")
        pause("按回车退出...")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
