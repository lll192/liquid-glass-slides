@echo off
setlocal
title Liquid Glass Slides
cd /d "%~dp0"
set "CHECK_ARG="
if /I "%~1"=="--check" set "CHECK_ARG=-CheckOnly"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_windows.ps1" %CHECK_ARG%
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Launch failed. Keep this window open and review the message above.
  pause
)
exit /b %EXIT_CODE%
