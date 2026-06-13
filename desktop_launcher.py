"""E북 구매 추적기 — 데스크톱 실행기.

PyInstaller 로 빌드하면 이 파일이 프로그램의 진입점이 됩니다.
더블클릭 한 번으로:
  1. 내장된 Streamlit 서버를 백그라운드로 띄우고
  2. 기본 웹브라우저에 앱 화면을 자동으로 엽니다.
검은 콘솔 창은 보이지 않습니다(--windowed 빌드).
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def base_dir() -> Path:
    """소스 실행/번들(.exe) 양쪽에서 앱 파일이 있는 폴더를 반환."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def hide_console() -> None:
    """콘솔(검은 창)을 숨겨 완성된 프로그램처럼 보이게 한다 (Windows 전용).

    콘솔 서브시스템으로 빌드하면 Python 표준 스트림 초기화가 안정적이라
    'init_sys_streams' 같은 시작 충돌을 피할 수 있다. 그 대신 시작 직후
    콘솔 창만 숨겨 사용자에게는 검은 창이 보이지 않게 한다.
    """
    try:
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
    except Exception:
        pass


def guard_std_streams() -> None:
    """콘솔 없는 빌드에서 stdout/stderr 가 None 이면 로그 파일로 대체.

    (Streamlit 내부가 stdout 에 쓰다가 죽는 것을 방지)
    """
    if sys.stdout is None or sys.stderr is None:
        log_path = Path(os.path.expanduser("~")) / "ebook_tracker_log.txt"
        f = open(log_path, "a", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = f
        if sys.stderr is None:
            sys.stderr = f


def free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def choose_port() -> int:
    """EBOOK_PORT 환경변수가 지정되면 그 포트를, 아니면 빈 포트를 자동 선택."""
    env = os.environ.get("EBOOK_PORT", "").strip()
    if env.isdigit():
        return int(env)
    return free_port()


def open_when_ready(port: int) -> None:
    """서버가 응답하기 시작하면 브라우저를 연다 (최대 ~30초 대기)."""
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    hide_console()
    guard_std_streams()
    base = base_dir()
    app_path = base / "ebook_app.py"
    port = choose_port()

    threading.Thread(target=open_when_ready, args=(port,), daemon=True).start()

    # Streamlit 을 이 프로세스의 메인 스레드에서 실행 (블로킹)
    sys.argv = [
        "streamlit", "run", str(app_path),
        "--server.port", str(port),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
    ]
    from streamlit.web import cli as stcli
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
