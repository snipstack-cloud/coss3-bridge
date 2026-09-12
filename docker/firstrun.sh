#!/usr/bin/env bash
# Готовит префикс Wine. Выполняется ОДИН РАЗ при сборке образа, а не при старте
# контейнера: wineboot на холодную занимает десятки секунд, и платить их
# десять раз при запуске десяти копий незачем.
#
# Экран поднимаем САМИ, а не через xvfb-run: тому нужен xauth, а тащить его в
# ранний слой значит заново копировать 8,3 ГБ игры при каждой такой правке.
set -euo pipefail

export WINEDEBUG=-all

# Вывод Xvfb ловим в файл. Первая редакция его выбрасывала, и сборка сказала
# «Xvfb не поднялся» без единой подробности — ровно тот молчаливый отказ, за
# который в этом проекте бьют.
export DISPLAY=:99
# Экран может быть уже поднят: entrypoint делает это до вызова firstrun, когда
# префикса нет и его приходится создавать на сервере. Второй Xvfb на том же
# :99 просто не встанет, поэтому сначала спрашиваем.
if xdpyinfo -display :99 >/dev/null 2>&1; then
    echo "[firstrun] экран :99 уже есть, свой не поднимаю"
else
mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
Xvfb :99 -screen 0 640x480x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
XVFB=$!
trap 'kill "$XVFB" 2>/dev/null || true' EXIT
# 60 секунд, а не 10: образ собирается на маке под эмуляцией x86, и там всё
# медленнее в разы.
for _ in $(seq 1 300); do
    xdpyinfo -display :99 >/dev/null 2>&1 && break
    kill -0 "$XVFB" 2>/dev/null || break
    sleep 0.2
done
if ! xdpyinfo -display :99 >/dev/null 2>&1; then
    echo "[firstrun] Xvfb не поднялся. Его вывод:"
    cat /tmp/xvfb.log || true
    kill -0 "$XVFB" 2>/dev/null && echo "[firstrun] процесс Xvfb ЖИВ, но экран не отвечает" \
                                || echo "[firstrun] процесс Xvfb умер"
    exit 1
fi
fi

echo "[firstrun] создаю префикс ${WINEPREFIX} (арх. ${WINEARCH})"
wineboot --init
wineserver --wait

# Версия Windows. Игра 2016 года и на XP не рассчитана; win7 — то, под чем её
# и выпускали. Ставим явно, чтобы поведение не зависело от версии Wine.
echo "[firstrun] windows version -> win7"
wine reg add 'HKCU\Software\Wine' /v Version /d win7 /f
wineserver --wait

echo "[firstrun] префикс готов"
