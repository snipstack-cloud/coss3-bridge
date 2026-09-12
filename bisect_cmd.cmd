@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Cossacks 3 - бисекция блока команд

if "%~1"=="" (
  echo.
  echo Ищем, на какой половине блока команд встаёт тик игры.
  echo.
  echo   bisect_cmd.cmd 1   только сторож и включение лога, файлы НЕ читаются
  echo   bisect_cmd.cmd 2   + чтение файла команд, BUILD и TRAIN
  echo   bisect_cmd.cmd 3a  + только BALANCE на добычу
  echo   bisect_cmd.cmd 3b  + шахты
  echo   bisect_cmd.cmd 3   + BALANCE, шахты и UPGRADE ^(всё, кроме ATTACK^)
  echo   bisect_cmd.cmd 4   полный блок
  echo.
  echo После каждого: закрыть игру, запустить бой, постоять 15 секунд,
  echo вернуться сюда. Окно само скажет, жив тик или нет.
  echo.
  pause & exit /b 1
)

set "GAME="
for %%P in (
  "C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
  "C:\Program Files\Steam\steamapps\common\Cossacks 3"
  "D:\Steam\steamapps\common\Cossacks 3"
  "D:\SteamLibrary\steamapps\common\Cossacks 3"
  "E:\SteamLibrary\steamapps\common\Cossacks 3"
) do if exist "%%~P\cossacks.exe" set "GAME=%%~P"
if "%GAME%"=="" set /p GAME="Укажи папку с cossacks.exe: "
if not exist "%GAME%\cossacks.exe" (echo Нет cossacks.exe в "%GAME%" & pause & exit /b 1)

set "IO=%USERPROFILE%\coss3-io"
if not exist "%IO%" mkdir "%IO%"
del /q "%IO%\coss3_*.dat" 2>nul

set "LVL=--cmd-level %~1"
if "%~1"=="4" set "LVL="

echo.
echo --- ставлю уровень %~1 ---
python install_bridge.py "%GAME%" --reinstall --outdir "%IO%" --human-only --human-state --human-cmd %LVL%
if errorlevel 1 (echo УСТАНОВКА НЕ УДАЛАСЬ, откатываю & python install_bridge.py "%GAME%" --uninstall & pause & exit /b 1)

echo.
echo ===== ЗАПУСТИ ИГРУ И БОЙ, ПОСТОЙ 15 СЕКУНД =====
echo Свой слот ЧЕЛОВЕК, советник ВЫКЛЮЧЕН. Потом вернись и нажми клавишу.
pause >nul

echo.
set "HB=нет"
set "ECO=нет"
if exist "%IO%\coss3_hb.dat" set "HB=ЕСТЬ"
for %%N in (0 1 2 3 4 5 6 7) do if exist "%IO%\coss3_eco_P%%N.dat" set "ECO=ЕСТЬ"
echo   пульс  coss3_hb.dat      : %HB%
echo   состояние coss3_eco_P*   : %ECO%
echo.
if "%HB%"=="ЕСТЬ" (
  echo ТИК ЖИВ на уровне %~1. Ставь следующий уровень.
) else (
  echo ТИК МЁРТВ на уровне %~1. Виновата та часть, что добавилась именно здесь.
  echo Пришли мне этот вывод. Откатить игру: rollback.cmd
)
echo.
pause
