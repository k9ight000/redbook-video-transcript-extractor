@echo off
setlocal

set "PS_SCRIPT=%~dp0..\xhs-video-to-text.ps1"
if not exist "%PS_SCRIPT%" (
    set "PS_SCRIPT=%USERPROFILE%\xhs-video-to-text.ps1"
)
if not exist "%PS_SCRIPT%" (
    echo Script not found: %PS_SCRIPT%
    pause
    exit /b 1
)

if "%~1"=="" (
    set /p "XHS_URL=Paste the Xiaohongshu/Redbook share link, then press Enter: "
) else (
    set "XHS_URL=%~1"
)

if not defined XHS_URL (
    echo No link was entered.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -Url "%XHS_URL%" -Local -LocalModel medium -LocalLanguage zh
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Finished with errors.
    pause
    exit /b %EXIT_CODE%
)

echo.
echo Done.
pause
exit /b 0
