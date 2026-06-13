"""데이터 저장 위치.

개발 중에는 물론, 설치형(.exe)으로 배포했을 때도 안전하게 쓰도록
사용자별 쓰기 가능한 폴더(Windows: %APPDATA%\\EBookTracker)에 저장합니다.
프로그램이 Program Files 같은 읽기 전용 위치에 설치돼도 데이터가 안전합니다.
"""

from __future__ import annotations

import os
from pathlib import Path


def user_data_dir() -> Path:
    base = (
        os.environ.get("APPDATA")          # Windows
        or os.environ.get("XDG_DATA_HOME")  # Linux
        or os.path.expanduser("~")
    )
    d = Path(base) / "EBookTracker"
    d.mkdir(parents=True, exist_ok=True)
    return d
