@echo off
chcp 65001 >nul
title Cossacks 3 - откат всех правок
set "GAME="
for %%P in (
  "C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
  "C:\Program Files\Steam\steamapps\common\Cossacks 3"
  "D:\Steam\steamapps\common\Cossacks 3"
  "D:\SteamLibrary\steamapps\common\Cossacks 3"
) do if exist "%%~P\cossacks.exe" set "GAME=%%~P"
if "%GAME%"=="" set /p GAME="Укажи папку с cossacks.exe: "
echo Снимаю все блоки моста из %GAME%
python install_bridge.py "%GAME%" --uninstall
echo.
echo Если игра всё равно не запускается - в папке игры лежат резервные копии
echo data\scripts\units\global.inc\*.bak-* : верни любой из них поверх .inc
pause
