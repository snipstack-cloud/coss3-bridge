#!/usr/bin/env bash
# Один контейнер = одна копия игры + свой мост.
#
# Порядок намеренно такой: экран -> графический слой -> установка моста в игру
# -> игра -> ожидание ПУЛЬСА -> политика. Политику нельзя пускать раньше
# пульса: она сразу начнёт искать состояние, не найдёт и решит, что мост не
# встал, — ровно та диагностическая ложь, с которой воевали весь проект.
set -euo pipefail

# Имена переменных только латиницей: bash не допускает многобайтовые символы
# в именах, и такая строка становится командой, а не присваиванием.
log() { echo "[coss3 $(date +%H:%M:%S)] $*"; }
die() { log "ОСТАНОВКА: $*"; exit 1; }

: "${COSS3_GAME:=/opt/cossacks}"
: "${COSS3_RES:=800x600}"
: "${COSS3_D3D:=dxvk}"
: "${COSS3_VNC:=0}"
# Номер копии берём из имени хоста (compose называет контейнер по службе:
# coss3-7 -> 7). Так environment остаётся единым для всех копий, и ключ слияния
# YAML не может его молча съесть — эта грабля уже случилась при написании
# compose.yaml.
: "${COSS3_SLOT:=$(hostname | sed -n 's/.*-\([0-9][0-9]*\)$/\1/p')}"
: "${COSS3_SLOT:=0}"
: "${COSS3_IO:=/io}"          # сюда уходят трасса и лог, наружу из контейнера
: "${COSS3_INSTALL:=1}"       # ставить ли мост в игру при старте
: "${COSS3_RUN_POLICY:=1}"    # запускать ли модель; 0 — только игра, для отладки
: "${COSS3_HINTS:=/opt/bridge/hints_human.txt}"
: "${COSS3_MODEL:=@preset/coss3-bot}"
: "${COSS3_EVERY:=20}"
: "${COSS3_WAVE_MIN:=20}"
: "${COSS3_HB_TIMEOUT:=180}"  # сколько ждать пульса, прежде чем признать провал

mkdir -p "$COSS3_IO"

# --- экран -------------------------------------------------------------------
log "копия $COSS3_SLOT, экран $COSS3_RES"
Xvfb :99 -screen 0 "${COSS3_RES}x24" -nolisten tcp &
XVFB_PID=$!
for i in $(seq 1 50); do
    xdpyinfo -display :99 >/dev/null 2>&1 && break
    sleep 0.2
done
xdpyinfo -display :99 >/dev/null 2>&1 || die "Xvfb не поднялся"
export DISPLAY=:99

if [ "$COSS3_VNC" = "1" ]; then
    # Первый бой всё равно заводится руками — через VNC видно меню игры.
    x11vnc -display :99 -forever -shared -nopw -quiet -rfbport 5900 &
    log "VNC на 5900 (без пароля — только за доверенной сетью!)"
fi

# --- префикс Wine ------------------------------------------------------------
# Обычно он запечён в образ при сборке. Но если сборка шла на Apple Silicon,
# под эмуляцией x86 Xvfb зависает, и префикса в образе нет — тогда создаём его
# здесь, на сервере, где всё родное. Говорим об этом вслух: лишние тридцать
# секунд на старте должны иметь объяснение в логе, а не выглядеть подвисанием.
if [ ! -f "${WINEPREFIX}/system.reg" ]; then
    log "префикса Wine в образе нет — создаю (это 20-30 с, один раз на контейнер)"
    /opt/bridge/firstrun.sh || die "не удалось создать префикс Wine"
else
    log "префикс Wine готов (запечён при сборке)"
fi

# --- графический слой --------------------------------------------------------
# Проверяем Vulkan ВСЛУХ. Молчаливый откат на программный растеризатор — это
# разница между партией за 11 минут и партией за пять часов, и узнать о нём
# из тормозов вместо строки в логе мы не хотим.
if command -v vulkaninfo >/dev/null 2>&1; then
    GPU=$(vulkaninfo --summary 2>/dev/null | grep -m1 "deviceName" | cut -d= -f2- | xargs || true)
    if [ -n "${GPU:-}" ]; then
        log "Vulkan: ${GPU}"
        case "$GPU" in
            *llvmpipe*|*lavapipe*|*"Software"*)
                log "ВНИМАНИЕ: это ПРОГРАММНЫЙ растеризатор, видеокарты у контейнера нет."
                log "          Игра пойдёт, но медленно. Дать карту: --device /dev/dri" ;;
        esac
    else
        log "ВНИМАНИЕ: Vulkan не отвечает — DXVK не заведётся, перехожу на wined3d"
        COSS3_D3D=wined3d
    fi
fi

case "$COSS3_D3D" in
  dxvk)
    log "графика: DXVK (D3D9 -> Vulkan)"
    install -m0644 /opt/dxvk/x32/d3d9.dll "$WINEPREFIX/drive_c/windows/system32/d3d9.dll"
    wine reg add 'HKCU\Software\Wine\DllOverrides' /v d3d9 /d native /f >/dev/null 2>&1
    ;;
  wined3d)
    log "графика: штатный WineD3D (D3D9 -> OpenGL)"
    wine reg delete 'HKCU\Software\Wine\DllOverrides' /v d3d9 /f >/dev/null 2>&1 || true
    ;;
  *) die "COSS3_D3D должен быть dxvk или wined3d, а не «${COSS3_D3D}»" ;;
esac
wineserver --wait

# --- мост в игру -------------------------------------------------------------
# Каталог обмена НЕ задаём (--outdir): без него блоки пишут рядом с
# cossacks.exe, и этот путь одинаково виден игре (как папка игры) и питону
# (как /opt/cossacks). Трансляции путей Wine тут не нужно вовсе.
cd /opt/bridge
if [ "$COSS3_INSTALL" = "1" ]; then
    log "проверяю блоки перед установкой"
    python3 verify_blocks.py "$COSS3_GAME" block_human.inc block_hstate.inc block_hcmd.inc \
        || die "verify_blocks завернул блок — в игру такое не ставим"

    log "ставлю человеческий слот"
    python3 install_bridge.py "$COSS3_GAME" --reinstall \
            --human-only --human-state --human-cmd 2>&1 | tee "$COSS3_IO/install.log"

    grep -q "проверка после записи: все блоки на месте" "$COSS3_IO/install.log" \
        || die "установщик не подтвердил, что блоки на месте (см. $COSS3_IO/install.log)"

    # Проверяем ПО МЕТКАМ, а не по числу строк. Первая редакция сравнивала с
    # 248 — и не сработала бы НИКОГДА: установщик печатает «1119», потому что
    # считает через split("\r\n") и ловит хвостовой пустой элемент, а
    # splitlines() даёт 1118. Число зависит от способа счёта и от поставки игры
    # (в GOG-копии чистый progress.inc — 187 строк, а не 248, как на Steam).
    # Метка блока от этого не зависит: её либо вставили, либо нет.
    python3 - "$COSS3_GAME" <<'PY' || die "в игре нет человеческого блока"
import os, sys
путь = os.path.join(sys.argv[1], "data", "scripts", "units",
                    "global.inc", "progress.inc")
д = open(путь, "rb").read()
метки = {
    "состояние": b"// === BRIDGE HUMAN STATE",
    "команды":   b"// === BRIDGE HUMAN COMMANDS",
    "петля":     b"// === BRIDGE LOOP",
}
нет = [и for и, м in метки.items() if м not in д]
print(f"progress.inc: {len(д.splitlines())} строк, "
      f"блоки: {', '.join(и for и in метки if и not in нет) or 'НИ ОДНОГО'}")
if нет:
    print(f"СТОП: в progress.inc нет блоков: {', '.join(нет)}")
    sys.exit(1)
PY
fi

# --- игра --------------------------------------------------------------------
cd "$COSS3_GAME"
rm -f coss3_hb.dat coss3_eco_P*.dat
log "запускаю cossacks.exe"
wine cossacks.exe >"$COSS3_IO/game.log" 2>&1 &
GAME_PID=$!

# Пульс пишет петля эпизодов, и он НЕ зависит от блока состояния: если нет
# даже его, значит не собрался весь тик Progress. Это главный признак беды,
# купленный дорого 12.09.
log "жду пульс (coss3_hb.dat), до ${COSS3_HB_TIMEOUT} с"
for i in $(seq 1 "$COSS3_HB_TIMEOUT"); do
    [ -f coss3_hb.dat ] && break
    kill -0 "$GAME_PID" 2>/dev/null || die "игра завершилась, не дав пульса (см. $COSS3_IO/game.log)"
    sleep 1
done
if [ -f coss3_hb.dat ]; then
    log "пульс есть: тик Progress жив"
else
    log "ПУЛЬСА НЕТ за ${COSS3_HB_TIMEOUT} с."
    log "  Это либо не собрался тик Progress (смотри game.log), либо игра стоит"
    log "  в меню и боя ещё нет. Второе — норма для первого запуска: подключись"
    log "  по VNC (COSS3_VNC=1) и начни бой руками, дальше партии идут сами."
fi

# --- политика ----------------------------------------------------------------
if [ "$COSS3_RUN_POLICY" = "1" ]; then
    cd /opt/bridge
    log "запускаю модель: $COSS3_MODEL, такт $COSS3_EVERY, порог волны $COSS3_WAVE_MIN"
    exec python3 llm_policy.py --human \
        --dir "$COSS3_GAME" \
        --hints "$COSS3_HINTS" \
        --model "$COSS3_MODEL" \
        --every "$COSS3_EVERY" \
        --wave-min "$COSS3_WAVE_MIN" \
        --ban market,academi \
        --botlog "$COSS3_IO/coss3_bot.jsonl" \
        --log "$COSS3_IO/coss3_llm.log"
else
    log "политика выключена (COSS3_RUN_POLICY=0) — держу игру"
    wait "$GAME_PID"
fi
