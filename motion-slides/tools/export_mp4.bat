@echo off
REM Drag & drop a .pptx onto this file -> MP4 in the same folder
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0export_mp4.ps1" -Pptx "%~1"
pause
