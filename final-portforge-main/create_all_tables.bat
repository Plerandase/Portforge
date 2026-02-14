@echo off
chcp 65001 > nul
echo ============================================
echo   Portforge MSA - 테이블 생성
echo ============================================
echo.

REM 루트 디렉토리 저장
set ROOT_DIR=%CD%

REM 1. Auth 테이블 생성
echo [1/5] Auth 테이블 생성 중...
cd "%ROOT_DIR%\Auth"
call poetry run python create_tables.py
if errorlevel 1 (
    echo ⚠️ Auth 테이블 생성 실패 (이미 존재할 수 있음)
) else (
    echo ✅ Auth 테이블 생성 완료
)
echo.

REM 2. Project 테이블 생성
echo [2/5] Project 테이블 생성 중...
cd "%ROOT_DIR%\Project_Service"
call poetry run python create_tables.py
if errorlevel 1 (
    echo ⚠️ Project 테이블 생성 실패 (이미 존재할 수 있음)
) else (
    echo ✅ Project 테이블 생성 완료
)
echo.

REM 3. Team 테이블 생성
echo [3/5] Team 테이블 생성 중...
cd "%ROOT_DIR%\Team-BE"
call poetry run python create_tables.py
if errorlevel 1 (
    echo ⚠️ Team 테이블 생성 실패 (이미 존재할 수 있음)
) else (
    echo ✅ Team 테이블 생성 완료
)
echo.

REM 4. AI 테이블 생성
echo [4/5] AI 테이블 생성 중...
cd "%ROOT_DIR%\Ai"
call poetry run python create_tables.py
if errorlevel 1 (
    echo ⚠️ AI 테이블 생성 실패 (이미 존재할 수 있음)
) else (
    echo ✅ AI 테이블 생성 완료
)
echo.

REM 5. Support 테이블 생성
echo [5/5] Support 테이블 생성 중...
cd "%ROOT_DIR%\Support_Communication_Service"
call poetry run python create_tables.py
if errorlevel 1 (
    echo ⚠️ Support 테이블 생성 실패 (이미 존재할 수 있음)
) else (
    echo ✅ Support 테이블 생성 완료
)
echo.

cd "%ROOT_DIR%"

echo ============================================
echo ✅ 테이블 생성 완료!
echo ============================================
echo.
echo 다음 단계: python seed_all.py
echo.
pause
