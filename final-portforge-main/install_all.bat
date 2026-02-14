@echo off
chcp 65001 > nul
echo ============================================
echo   Portforge MSA - 전체 환경 설치
echo ============================================
echo.

REM 루트 디렉토리 저장
set ROOT_DIR=%CD%

REM 1. 루트 Poetry 설치
echo [1/7] 루트 의존성 설치 중...
call poetry install --no-root
if errorlevel 1 (
    echo ❌ 루트 Poetry 설치 실패
    pause
    exit /b 1
)
echo ✅ 루트 의존성 설치 완료
echo.

REM 2. Auth 서비스
echo [2/7] Auth 서비스 설치 중...
cd "%ROOT_DIR%\Auth"
if not exist ".env" copy ".env.example" ".env" 2>nul
call poetry install --no-root
if errorlevel 1 (
    echo ❌ Auth 서비스 설치 실패
    cd "%ROOT_DIR%"
    pause
    exit /b 1
)
echo ✅ Auth 서비스 설치 완료
echo.

REM 3. Project 서비스
echo [3/7] Project 서비스 설치 중...
cd "%ROOT_DIR%\Project_Service"
if not exist ".env" copy ".env.example" ".env" 2>nul
call poetry install --no-root
if errorlevel 1 (
    echo ❌ Project 서비스 설치 실패
    cd "%ROOT_DIR%"
    pause
    exit /b 1
)
echo ✅ Project 서비스 설치 완료
echo.

REM 4. Team 서비스
echo [4/7] Team 서비스 설치 중...
cd "%ROOT_DIR%\Team-BE"
if not exist ".env" copy ".env.example" ".env" 2>nul
call poetry install --no-root
if errorlevel 1 (
    echo ❌ Team 서비스 설치 실패
    cd "%ROOT_DIR%"
    pause
    exit /b 1
)
echo ✅ Team 서비스 설치 완료
echo.

REM 5. AI 서비스
echo [5/7] AI 서비스 설치 중...
cd "%ROOT_DIR%\Ai"
if not exist ".env" copy ".env.example" ".env" 2>nul
call poetry install --no-root
if errorlevel 1 (
    echo ❌ AI 서비스 설치 실패
    cd "%ROOT_DIR%"
    pause
    exit /b 1
)
echo ✅ AI 서비스 설치 완료
echo.

REM 6. Support 서비스
echo [6/7] Support 서비스 설치 중...
cd "%ROOT_DIR%\Support_Communication_Service"
if not exist ".env" copy ".env.example" ".env" 2>nul
call poetry install --no-root
if errorlevel 1 (
    echo ❌ Support 서비스 설치 실패
    cd "%ROOT_DIR%"
    pause
    exit /b 1
)
echo ✅ Support 서비스 설치 완료
echo.

REM 7. Frontend
echo [7/7] Frontend 설치 중...
cd "%ROOT_DIR%\FE"
call npm install
if errorlevel 1 (
    echo ❌ Frontend 설치 실패
    cd "%ROOT_DIR%"
    pause
    exit /b 1
)
echo ✅ Frontend 설치 완료
echo.

cd "%ROOT_DIR%"

echo ============================================
echo ✅ 모든 서비스 설치 완료!
echo ============================================
echo.
echo 다음 단계:
echo   1. Docker 실행: docker compose up -d
echo   2. 테이블 생성: create_all_tables.bat
echo   3. 시드 데이터: python seed_all.py
echo   4. 서비스 시작: start_services.bat
echo.
pause
