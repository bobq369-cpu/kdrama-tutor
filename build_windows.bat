@echo off
chcp 65001 >nul
title E북 구매 추적기 - Windows 빌드

echo ============================================================
echo   E북 구매 추적기 - Windows 프로그램 만들기
echo ============================================================
echo.
echo 이 작업은 한 번만 하면 됩니다. (몇 분 걸립니다)
echo.

REM --- Python 설치 확인 ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python 이 설치돼 있지 않습니다.
    echo        https://www.python.org/downloads/ 에서 Python 3.10 이상을 먼저 설치하세요.
    echo        설치할 때 "Add Python to PATH" 를 꼭 체크하세요.
    pause
    exit /b 1
)

echo [1/3] 필요한 패키지를 설치합니다...
python -m pip install --upgrade pip
python -m pip install -r requirements-ebook.txt
python -m pip install pyinstaller
if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [2/3] 프로그램을 빌드합니다... (시간이 걸립니다. 기다려 주세요)
python -m PyInstaller EBookTracker.spec --noconfirm
if errorlevel 1 (
    echo [오류] 빌드에 실패했습니다. 위의 메시지를 확인하세요.
    pause
    exit /b 1
)

echo.
echo [3/3] 완료!
echo ------------------------------------------------------------
echo  결과물:  dist\EBookTracker\  폴더
echo.
echo  이 폴더 전체를 압축(zip)해서 지인에게 보내세요.
echo  지인은 압축을 푼 뒤 그 안의  EBookTracker.exe  를 더블클릭하면 됩니다.
echo  (브라우저는 지인 PC의 Chrome 또는 Edge 를 자동으로 사용합니다.)
echo ------------------------------------------------------------
pause
