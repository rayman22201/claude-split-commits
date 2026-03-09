@echo off
REM Install the split-commits skill + git-hunk-tool for Claude Code.
REM
REM Usage:
REM   install.bat
REM
REM Detects whether "python" is Python 3. Falls back to "python3".

setlocal enabledelayedexpansion

REM --- Detect Python 3 ---
set "PYTHON="

python -c "import sys; exit(0 if sys.version_info.major==3 else 1)" 2>nul
if %errorlevel%==0 (
    set "PYTHON=python"
    goto :found_python
)

python3 -c "import sys; exit(0 if sys.version_info.major==3 else 1)" 2>nul
if %errorlevel%==0 (
    set "PYTHON=python3"
    goto :found_python
)

echo Error: Python 3 not found. Install Python 3 and ensure "python" or "python3" is on PATH.
exit /b 1

:found_python
echo Using Python 3 via: %PYTHON%

REM --- Install package ---
echo.
echo === Installing git-hunk-tool Python package ===
%PYTHON% -m pip install "%~dp0"

REM --- Install skill with correct python command ---
echo.
echo === Installing split-commits Claude Code skill ===
if not exist "%USERPROFILE%\.claude\commands" mkdir "%USERPROFILE%\.claude\commands"

REM Substitute {{PYTHON}} placeholder with detected binary
powershell -NoProfile -Command ^
    "(Get-Content '%~dp0skill\split-commits.md') -replace '\{\{PYTHON\}\}', '%PYTHON%' | Set-Content '%USERPROFILE%\.claude\commands\split-commits.md'"

echo.
echo Done! You can now use /split-commits in Claude Code.
echo.
echo Verify with:
echo   %PYTHON% -m git_hunk_tool --help
