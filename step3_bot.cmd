@echo off
chcp 65001 >nul
title Cossacks 3 - ступень 3: БОТ ИГРАЕТ ЗА ЧЕЛОВЕКА
call :findgame || exit /b 1
set "IO=%USERPROFILE%\coss3-io"
if not exist "%IO%" mkdir "%IO%"
echo.
echo ===== СТУПЕНЬ 3: БОТ =====
echo Ставит блок команд. С этого момента бот СТРОИТ, НАНИМАЕТ, ДОБЫВАЕТ и АТАКУЕТ.
echo.
python verify_blocks.py "%GAME%" block_hstate.inc block_hcmd.inc || (echo ПРОВЕРКА НЕ ПРОЙДЕНА & pause & exit /b 1)
python install_bridge.py "%GAME%" --reinstall --outdir "%IO%" --human-only --human-state --human-cmd
if errorlevel 1 (echo УСТАНОВКА НЕ УДАЛАСЬ, откатываю & python install_bridge.py "%GAME%" --uninstall & pause & exit /b 1)
echo.
echo ===== ЗАПУСТИ ИГРУ И БОЙ =====
echo Свой слот ЧЕЛОВЕК, советник ВЫКЛЮЧЕН, противник компьютер.
echo Когда бой начнётся - вернись сюда и нажми любую клавишу.
pause >nul
if "%OPENROUTER_BASE_URL%"=="" set "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1"
echo.
echo Запускаю модель. Останов - Ctrl+C. Лог решений: coss3_llm.log
echo Лог действий бота: coss3_bot.jsonl и строки bridge-human в логе игры.
echo.
python llm_policy.py --human --hints hints_human.txt --model deepseek/deepseek-v4.1-flash --every 20 --ban market,academi --provider-ignore "Morph,Io Net"
echo.
echo Партия закончилась. Разбор:
python log_review.py coss3_llm.log
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
