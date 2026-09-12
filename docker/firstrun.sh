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
# Протухший замок X. Файл /tmp/.X99-lock мог уехать в слой образа со сборки
# (там firstrun однажды поднимал Xvfb), и тогда новый Xvfb отказывается
# стартовать со словами "Server is already active for display 99" — при том
# что никакого сервера нет. Снимаем замок и сокет, но только если процесса
# Xvfb действительно нет: иначе убили бы работающий экран.
if ! pgrep -x Xvfb >/dev/null 2>&1; then
    rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
fi

# Та же поправка, что в entrypoint: судим по сокету, а не по xdpyinfo — его в
# образе нет, и проверка через него всегда проваливалась.
if [ -S /tmp/.X11-unix/X99 ]; then
    echo "[firstrun] экран :99 уже есть, свой не поднимаю"
else
mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
# +extension GLX обязателен, и это не мелочь: Xvfb по умолчанию GLX НЕ
# включает. Без него окно создаётся, а OpenGL в него не рисует — экран чёрный,
# ошибок нет, игра «работает». 12.09 это стоило часа: xwininfo показывал окно
# 800x600 в состоянии IsViewable, снимок экрана весил 212 байт (сплошная
# заливка), и только пустой вывод xdpyinfo про GLX объяснил, почему.
# cossacks.exe импортирует opengl32.dll и GLU32.dll, то есть без GLX она
# бессильна независимо от того, DXVK у неё или WineD3D.
Xvfb :99 -screen 0 640x480x24 +extension GLX +extension RANDR +render -nolisten tcp >/tmp/xvfb.log 2>&1 &
XVFB=$!
trap 'kill "$XVFB" 2>/dev/null || true' EXIT
# 60 секунд, а не 10: образ собирается на маке под эмуляцией x86, и там всё
# медленнее в разы.
for _ in $(seq 1 300); do
    [ -S /tmp/.X11-unix/X99 ] && break
    kill -0 "$XVFB" 2>/dev/null || break
    sleep 0.2
done
if [ ! -S /tmp/.X11-unix/X99 ]; then
    echo "[firstrun] Xvfb не поднялся. Его вывод:"
    cat /tmp/xvfb.log || true
    kill -0 "$XVFB" 2>/dev/null && echo "[firstrun] процесс Xvfb ЖИВ, но экран не отвечает" \
                                || echo "[firstrun] процесс Xvfb умер"
    exit 1
fi
fi

# Mono и Gecko отключаем НАСТРОЙКОЙ, а не терпением. На свежем префиксе
# wineboot показывает диалоги «установить Wine Mono / Gecko» и ЖДЁТ нажатия —
# а окно уходит на виртуальный экран, где нажимать некому, и контейнер висит
# без объяснений. Игре они не нужны: .NET и встроенный браузер Cossacks 3 не
# использует.
export WINEDLLOVERRIDES="mscoree,mshtml="

echo "[firstrun] создаю префикс ${WINEPREFIX} (арх. ${WINEARCH}), Mono/Gecko отключены"
wineboot --init
wineserver --wait
echo "[firstrun] wineboot отработал"

# Версия Windows. Игра 2016 года и на XP не рассчитана; win7 — то, под чем её
# и выпускали. Ставим явно, чтобы поведение не зависело от версии Wine.
echo "[firstrun] windows version -> win7"
wine reg add 'HKCU\Software\Wine' /v Version /d win7 /f
wineserver --wait

# ВИРТУАЛЬНЫЙ РАБОЧИЙ СТОЛ. Без него игра уходит в полный экран и пытается
# сменить видеорежим, а у Xvfb экран ровно один и неизменный: смена
# проваливается, и остаётся ЧЁРНЫЙ ЭКРАН при живом окне и исправном OpenGL.
# 12.09 это выглядело так: xwininfo показывает окно IsViewable нужного размера,
# glxinfo рапортует llvmpipe с OpenGL 4.5, ошибок нигде нет — а снимок экрана
# весит 212 байт. Экран профиля при этом рисовался (обычное окно Windows), и
# чернело ровно на переходе в игровой режим.
#
# В виртуальном столе Wine рисует всё в одно окно и видеорежим не трогает.
# Ставим это настройкой префикса, а не ключом запуска: так действует на любой
# .exe, включая config.exe, и не зависит от того, кто и как запускает игру.
echo "[firstrun] включаю виртуальный рабочий стол ${COSS3_DESKTOP:-1024x768}"
wine reg add 'HKCU\Software\Wine\Explorer' /v Desktop /d Default /f
wine reg add 'HKCU\Software\Wine\Explorer\Desktops' /v Default \
    /d "${COSS3_DESKTOP:-1024x768}" /f
wineserver --wait

echo "[firstrun] префикс готов"
