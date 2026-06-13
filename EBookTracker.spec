# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 빌드 설정 — E북 구매 추적기 (Windows 데스크톱 프로그램).

빌드:  pyinstaller EBookTracker.spec --noconfirm
결과:  dist/EBookTracker/  폴더 (이 폴더 전체를 압축해 지인에게 전달)
"""

from PyInstaller.utils.hooks import collect_all, copy_metadata

datas = []
binaries = []
hiddenimports = []

# --- 앱 소스 & 데이터 (.streamlit 은 개인 API 키가 있으므로 포함하지 않음) ---
datas += [
    ("ebook_app.py", "."),
    ("ebook_tracker", "ebook_tracker"),
    ("sample_data", "sample_data"),
]

# --- 무거운 라이브러리들을 통째로 수집 (datas/binaries/hiddenimports) ---
for pkg in ("streamlit", "playwright", "altair", "pyarrow", "pandas",
            "openpyxl", "bs4"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# --- 일부 패키지는 메타데이터(버전 정보)가 있어야 동작 ---
for pkg in ("streamlit", "playwright"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# --- 우리 패키지 모듈 명시 ---
hiddenimports += [
    "ebook_tracker",
    "ebook_tracker.config",
    "ebook_tracker.database",
    "ebook_tracker.importer",
    "ebook_tracker.sync",
    "ebook_tracker.paths",
]

block_cipher = None

a = Analysis(
    ["desktop_launcher.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EBookTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # console=True 로 빌드하되 desktop_launcher.hide_console() 가 시작 직후
    # 콘솔 창을 숨긴다. (windowed 빌드는 Wine/일부 환경에서 Python 표준 스트림
    # 초기화 충돌이 나므로, 콘솔 서브시스템으로 빌드 후 창만 숨기는 방식이 안정적)
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="EBookTracker",
)
