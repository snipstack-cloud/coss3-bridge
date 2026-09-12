@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Cossacks 3 - ступень 1: зонд человеческого слота

echo.
echo ===== СТУПЕНЬ 1: ЗОНД =====
echo Ставит блок, который ТОЛЬКО читает мир и пишет один файл.
echo Игра при этом не меняется. Откат - rollback.cmd
echo.

set "GAME="
for %%P in (
  "C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
  "C:\Program Files\Steam\steamapps\common\Cossacks 3"
  "D:\Steam\steamapps\common\Cossacks 3"
  "D:\SteamLibrary\steamapps\common\Cossacks 3"
  "E:\SteamLibrary\steamapps\common\Cossacks 3"
) do if exist "%%~P\cossacks.exe" set "GAME=%%~P"

if "%GAME%"=="" (
  echo НЕ НАШЁЛ ИГРУ в обычных местах.
  set /p GAME="Укажи папку с cossacks.exe: "
)
if not exist "%GAME%\cossacks.exe" (
  echo Нет cossacks.exe в "%GAME%" - выходим, ничего не трогая.
  pause & exit /b 1
)
echo Игра: %GAME%

set "IO=%USERPROFILE%\coss3-io"
if not exist "%IO%" mkdir "%IO%"
del /q "%IO%\coss3_probe_P*.dat" 2>nul

echo.
echo --- проверка блоков перед установкой ---
python verify_blocks.py "%GAME%" block_human.inc || (
  echo ПРОВЕРКА НЕ ПРОЙДЕНА - ставить нельзя. Пришли этот вывод.
  pause & exit /b 1
)

echo.
echo --- установка зонда ---
python install_bridge.py "%GAME%" --reinstall --outdir "%IO%" --human-probe
if errorlevel 1 (
  echo УСТАНОВКА НЕ УДАЛАСЬ. Откатываю.
  python install_bridge.py "%GAME%" --uninstall
  pause & exit /b 1
)

echo.
echo ===== ТЕПЕРЬ ЗАПУСТИ ИГРУ =====
echo Одиночный бой. Свой слот - ЧЕЛОВЕК. Советник ВЫКЛЮЧЕН.
echo Простой сухопутной карты хватит. Постой в бою 30 секунд.
echo.
echo Я жду файл зонда (до 10 минут). Не закрывай это окно.
echo.

set /a TRIES=0
:wait
set /a TRIES+=1
for %%N in (0 1 2 3 4 5 6 7) do if exist "%IO%\coss3_probe_P%%N.dat" goto found
if %TRIES% GEQ 120 goto timeout
timeout /t 5 /nobreak >nul
goto wait

:found
echo.
echo ===== ЗОНД СРАБОТАЛ =====
for %%F in ("%IO%\coss3_probe_P*.dat") do (
  echo --- %%~nxF ---
  type "%%F"
)
echo.
echo Скопируй всё, что выше, и пришли мне. Дальше - ступень 2.
pause & exit /b 0

:timeout
echo.
echo ===== ФАЙЛА НЕТ =====
echo Значит либо тик на человеческом слоте не выполняется, либо игра не дошла
echo до боя, либо файл лёг не туда. Проверь заодно: %IO%
echo Пришли мне:
echo   1) весь вывод этого окна;
echo   2) последний файл из "%USERPROFILE%\OneDrive\Documents\cossacks\log\"
echo   3) запустилась ли игра вообще.
echo.
echo Откатить всё: rollback.cmd
pause & exit /b 2
