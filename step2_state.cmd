@echo off
chcp 65001 >nul
title Cossacks 3 - ступень 2: состояние человеческого слота
call :findgame || exit /b 1
set "IO=%USERPROFILE%\coss3-io"
if not exist "%IO%" mkdir "%IO%"
del /q "%IO%\coss3_eco_P*.dat" 2>nul
echo.
echo ===== СТУПЕНЬ 2: СОСТОЯНИЕ =====
echo Блок читает мир и пишет coss3_eco_P^<n^>.dat раз в игровую секунду.
echo Приказов по-прежнему НЕ отдаёт: игра меняться не должна.
echo.
python verify_blocks.py "%GAME%" block_hstate.inc || (echo ПРОВЕРКА НЕ ПРОЙДЕНА & pause & exit /b 1)
python install_bridge.py "%GAME%" --reinstall --outdir "%IO%" --human-state
if errorlevel 1 (echo УСТАНОВКА НЕ УДАЛАСЬ, откатываю & python install_bridge.py "%GAME%" --uninstall & pause & exit /b 1)
echo.
echo Запусти бой: свой слот ЧЕЛОВЕК, советник ВЫКЛЮЧЕН. Постой минуту.
echo Жду файл состояния...
set /a T=0
:wait
set /a T+=1
for %%N in (0 1 2 3 4 5 6 7) do if exist "%IO%\coss3_eco_P%%N.dat" goto found
if %T% GEQ 120 (echo ФАЙЛА НЕТ - пришли мне вывод и лог игры & pause & exit /b 2)
timeout /t 5 /nobreak >nul
goto wait
:found
echo.
echo ===== СОСТОЯНИЕ ПИШЕТСЯ =====
for %%F in ("%IO%\coss3_eco_P*.dat") do type "%%F"
echo.
echo Проверь глазами: peasants, on_wood, centers, pea_food, p0_peasants.
echo Пришли мне это. Дальше - ступень 3, там бот начнёт действовать.
pause & exit /b 0

:findgame
set "GAME="
for %%P in (
  "C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
  "C:\Program Files\Steam\steamapps\common\Cossacks 3"
  "D:\Steam\steamapps\common\Cossacks 3"
  "D:\SteamLibrary\steamapps\common\Cossacks 3"
) do if exist "%%~P\cossacks.exe" set "GAME=%%~P"
if "%GAME%"=="" set /p GAME="Укажи папку с cossacks.exe: "
if not exist "%GAME%\cossacks.exe" (echo Нет cossacks.exe & pause & exit /b 1)
echo Игра: %GAME%
exit /b 0
