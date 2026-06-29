@echo off
chcp 65001 >nul
cd /d "%~dp0"

cls
echo.
echo  ============================================================
echo    🔬 Research Agent  v2.0.0 - 설치 마법사
echo    Multi-Agent Research System Setup
echo  ============================================================
echo.

REM ── STEP 1: 환경 확인 ────────────────────────────────────────
echo  [STEP 1/4] 환경 확인 중...
echo.

git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [오류] Git 이 설치되지 않았습니다.
    echo         https://git-scm.com 에서 Git 을 설치하세요.
    echo.
    pause
    exit /b 1
)
echo  [OK] Git 확인

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [오류] Python 이 설치되지 않았습니다.
    echo         https://python.org 에서 Python 을 설치하세요.
    echo.
    pause
    exit /b 1
)
echo  [OK] Python 확인
echo.

REM ── STEP 2: 코드 다운로드 ────────────────────────────────────
echo  [STEP 2/4] 코드 다운로드 중...
echo.

REM 이미 research_agent 폴더 안에 있는 경우 (git pull)
if exist "%~dp0app.py" if exist "%~dp0requirements.txt" (
    echo  [INFO] 이미 설치됨 - 최신 코드로 업데이트 중...
    git pull --autostash
    if %errorlevel%==0 (
        echo  [OK] 코드 업데이트 완료
    ) else (
        echo  [INFO] 업데이트 실패 (네트워크 확인)
    )
    set "APP_DIR=%~dp0"
    goto step_install
)

REM 처음 설치 - GitHub 에서 클론
echo  [INFO] GitHub 에서 코드 다운로드 중...
echo         (시간이 걸릴 수 있습니다...)
echo.
git clone https://github.com/mmkang-ein/aistrategy.git
if %errorlevel% neq 0 (
    echo.
    echo  [오류] 다운로드 실패 - 인터넷 연결 및 GitHub 주소를 확인하세요.
    echo.
    pause
    exit /b 1
)
echo  [OK] 다운로드 완료
set "APP_DIR=%~dp0aistrategy\research_agent"
cd /d "%APP_DIR%"
echo.

REM ── STEP 3: 패키지 설치 ──────────────────────────────────────
:step_install
echo  [STEP 3/4] 패키지 설치 중...
echo.
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  [오류] 패키지 설치 실패
    echo.
    pause
    exit /b 1
)
python -m pip install streamlit python-docx fpdf2 >nul 2>&1
echo  [OK] 패키지 설치 완료
echo.

REM ── STEP 4: API 키 설정 ──────────────────────────────────────
echo  [STEP 4/4] API 키 설정...
echo.
if not defined APP_DIR set "APP_DIR=%~dp0"
if exist "%APP_DIR%.env" (
    echo  [OK] .env 파일이 이미 존재합니다.
    goto step_launch
)

echo  Anthropic API 키가 필요합니다.
echo  https://console.anthropic.com 에서 발급받을 수 있습니다.
echo.
set /p "API_KEY=  API 키를 입력하세요 (sk-ant-...): "
if "%API_KEY%"=="" (
    echo.
    echo  [경고] API 키를 입력하지 않았습니다.
    echo         나중에 .env 파일에 직접 입력하세요:
    echo         ANTHROPIC_API_KEY=sk-ant-...
    echo.
    goto step_launch
)
echo ANTHROPIC_API_KEY=%API_KEY%> "%APP_DIR%.env"
echo  [OK] .env 파일 생성 완료
echo.

REM ── 설치 완료 → 바로 실행 안내 ──────────────────────────────
:step_launch
echo  ============================================================
echo    설치 완료!
echo  ============================================================
echo.
echo  지금 바로 실행하시겠습니까?
set /p "LAUNCH=  실행하려면 Y, 나중에 실행하려면 N 입력: "
if /i "%LAUNCH%"=="Y" (
    if not defined APP_DIR set "APP_DIR=%~dp0"
    call "%APP_DIR%연구자동화시스템_런처.bat"
)

echo.
echo  나중에 실행할 때는 아래 파일을 더블클릭하세요:
if not defined APP_DIR set "APP_DIR=%~dp0"
echo  %APP_DIR%연구자동화시스템_런처.bat
echo.
pause
exit /b 0
