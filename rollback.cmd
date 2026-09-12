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
echo Если игра всё равно не запускается - в папке игры лежат резервные копии.
echo Мост патчит ДВА файла, и копии лежат рядом с каждым:
echo   data\scripts\units\global.inc\progress.inc.bak-*
echo   data\gui\menu.inc\doprogress.inc.bak-*
echo Верни нужный поверх .inc - они побайтно те же, что были до установки.
pause
