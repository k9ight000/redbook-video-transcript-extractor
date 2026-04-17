# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

spec_root = Path(SPECPATH)


a = Analysis(
    [str(spec_root / "launcher.py")],
    pathex=[str(spec_root)],
    binaries=[],
    datas=[
        (str(spec_root / "xhs-video-to-text.ps1"), "."),
        (str(spec_root / "xhs_to_transcript.py"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="XhsVideoToText",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir="runtime-tmp",
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
