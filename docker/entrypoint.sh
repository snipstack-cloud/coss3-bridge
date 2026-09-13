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
# Wine не должен спрашивать про Mono и Gecko: диалог уходит на виртуальный
# экран, нажимать его некому, и контейнер висит молча. Игре они не нужны.
export WINEDLLOVERRIDES="mscoree,mshtml="
# Python буферизует вывод, когда он идёт не в терминал, а в `docker logs`:
# строки копятся по нескольку килобайт и появляются пачками. Для наблюдателя
# это неотличимо от зависания — 13.09 контейнер выглядел мёртвым, пока модель
# спокойно играла. Молчание не имеет права быть неотличимым от бездействия.
export PYTHONUNBUFFERED=1

log() { echo "[coss3 $(date +%H:%M:%S)] $*"; }
# Остановка НЕ должна убивать контейнер. 13.09 он умирал на проверке «партия
# так и не началась» — то есть ровно тогда, когда надо зайти и посмотреть, что
# внутри. `docker exec` на остановленном контейнере отвечает «is not running»,
# и причина остаётся неизвестной. Держим его стоять, как после конца прогона.
die() {
    log "ОСТАНОВКА: $*"
    if [ "${COSS3_KEEP_ALIVE:-1}" = "1" ]; then
        log "контейнер оставлен стоять — зайдите и посмотрите:"
        log "  docker exec <имя> tail -40 ${COSS3_IO:-/io}/game.log"
        log "  docker exec <имя> ls -la /opt/cossacks/coss3_hb.dat /opt/cossacks/coss3_eco_P*.dat"
        log "  docker exec <имя> sh -c 'ls -lat /opt/cossacks/*.log | head'"
        log "  COSS3_KEEP_ALIVE=0 — падать сразу, как раньше"
        while true; do sleep 3600; done
    fi
    exit 1
}

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
: "${COSS3_EPISODES:=1}"      # сколько партий подряд сыграть в этом контейнере
: "${COSS3_KEEP_ALIVE:=1}"    # держать контейнер живым после конца партии,
                              # чтобы можно было зайти за логами боя

mkdir -p "$COSS3_IO"

# --- экран -------------------------------------------------------------------
log "копия $COSS3_SLOT, экран $COSS3_RES"
# Каталог сокетов X. Без него Xvfb не поднимется, и это НЕ экзотика: в
# debian-slim его нет, а сам Xvfb молча не создаёт. В firstrun.sh эта строка
# была, здесь её не было — из-за чего контейнер падал с «Xvfb не поднялся» и
# ни словом не объяснял причину.
mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
# Протухший замок X. Файл /tmp/.X99-lock мог уехать в слой образа со сборки
# (там firstrun однажды поднимал Xvfb), и тогда новый Xvfb отказывается
# стартовать со словами "Server is already active for display 99" — при том
# что никакого сервера нет. Снимаем замок и сокет, но только если процесса
# Xvfb действительно нет: иначе убили бы работающий экран.
if ! pgrep -x Xvfb >/dev/null 2>&1; then
    rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
fi

# Вывод Xvfb ловим в файл и показываем при неудаче. Проверка, которая говорит
# «не получилось» и молчит о том, почему, — это половина проверки.
# Готовность экрана проверяем ПО СОКЕТУ, а не через xdpyinfo.
#
# 12.09 эта проверка стоила вечера: xdpyinfo живёт в пакете x11-utils, которого
# в образе нет. Команда не находилась, возвращала 127, и проверка объявляла
# «Xvfb не поднялся» — при живом процессе, пустом логе ошибок и созданном
# сокете. Экран был всё это время. Я успел списать это на эмуляцию x86 на
# Apple Silicon и записать ложную причину в документацию.
#
# Сокет /tmp/.X11-unix/X<N> — это ровно то, чем X-сервер объявляет о готовности,
# и он не требует ни одного дополнительного пакета.
экран_готов() {
    [ -S /tmp/.X11-unix/X99 ] || return 1
    # Если x11-utils всё же есть — спросим сервер по-настоящему. Нет — сокета
    # достаточно, но скажем об этом вслух, а не промолчим.
    if command -v xdpyinfo >/dev/null 2>&1; then
        xdpyinfo -display :99 >/dev/null 2>&1
    else
        return 0
    fi
}
# +extension GLX обязателен, и это не мелочь: Xvfb по умолчанию GLX НЕ
# включает. Без него окно создаётся, а OpenGL в него не рисует — экран чёрный,
# ошибок нет, игра «работает». 12.09 это стоило часа: xwininfo показывал окно
# 800x600 в состоянии IsViewable, снимок экрана весил 212 байт (сплошная
# заливка), и только пустой вывод xdpyinfo про GLX объяснил, почему.
# cossacks.exe импортирует opengl32.dll и GLU32.dll, то есть без GLX она
# бессильна независимо от того, DXVK у неё или WineD3D.
Xvfb :99 -screen 0 "${COSS3_RES}x24" +extension GLX +extension RANDR +render -nolisten tcp >"$COSS3_IO/xvfb.log" 2>&1 &
XVFB_PID=$!
for i in $(seq 1 150); do        # 30 с: на медленном диске и в WSL бывает
    экран_готов && break
    kill -0 "$XVFB_PID" 2>/dev/null || break
    sleep 0.2
done
if ! экран_готов; then
    log "Xvfb не поднялся. Его вывод:"
    cat "$COSS3_IO/xvfb.log" 2>/dev/null | sed 's/^/    /' || true
    kill -0 "$XVFB_PID" 2>/dev/null \
        && log "  процесс Xvfb ЖИВ, но экран не отвечает" \
        || log "  процесс Xvfb умер"
    log "  что есть в /tmp/.X11-unix: $(ls -la /tmp/.X11-unix 2>&1 | tail -2 | tr '\n' ' ')"
    die "без экрана игра не запустится (лог сохранён в ${COSS3_IO}/xvfb.log)"
fi
export DISPLAY=:99

if [ "$COSS3_VNC" = "1" ]; then
    # Первый бой всё равно заводится руками — через VNC видно меню игры.
    x11vnc -display :99 -forever -shared -nopw -quiet -rfbport 5900 &
    log "VNC на 5900 (без пароля — только за доверенной сетью!)"
fi

# --- мост из git -------------------------------------------------------------
# Рабочий мост приезжает из репозитория, запечённый в образ — запасной. Версия
# ОБЯЗАНА попасть в лог и в /io/bridge.sha: на ферме опытов через неделю никто
# не вспомнит, какой мост дал какой результат, и трасса без версии бесполезна.
: "${COSS3_BRIDGE_GIT:=}"
: "${COSS3_BRIDGE_REF:=master}"
if [ -n "$COSS3_BRIDGE_GIT" ]; then
    log "мост из git: ${COSS3_BRIDGE_GIT} @ ${COSS3_BRIDGE_REF}"
    # Приватный репозиторий берём по deploy key. Ключ ТОЛЬКО монтируется
    # (-v ...:/ssh/deploy_key:ro) и никогда не попадает в образ: слой с ключом
    # остаётся в истории образа навсегда, и его достанет любой, у кого образ
    # есть. Токен в переменной окружения тоже плох — он виден в
    # `docker inspect` и в списке процессов.
    if [ -f /ssh/deploy_key ]; then
        # ssh откажется от ключа с открытыми правами, а на смонтированном
        # томе права приходят с хоста. Копируем к себе и сужаем.
        install -m 700 -d /root/.ssh
        install -m 600 /ssh/deploy_key /root/.ssh/deploy_key
        sed -i 's#-i /ssh/deploy_key#-i /root/.ssh/deploy_key#' /opt/bridge/ssh_wrapper.sh
        export GIT_SSH_COMMAND=/opt/bridge/ssh_wrapper.sh
        log "  доступ по deploy key ($(ssh-keygen -lf /root/.ssh/deploy_key | awk '{print $2}'))"
    elif [ "${COSS3_BRIDGE_GIT#git@}" != "$COSS3_BRIDGE_GIT" ] \
      || [ "${COSS3_BRIDGE_GIT#ssh://}" != "$COSS3_BRIDGE_GIT" ]; then
        die "адрес по ssh (${COSS3_BRIDGE_GIT}), а ключа в /ssh/deploy_key нет.
     Смонтируйте его: docker run -v ~/.ssh/coss3_deploy:/ssh/deploy_key:ro ...
     exp.py делает это сам, если ключ лежит в COSS3_DEPLOY_KEY."
    fi
    rm -rf /opt/bridge-git
    if git clone --quiet --no-single-branch "$COSS3_BRIDGE_GIT" /opt/bridge-git 2>&1 \
       && git -C /opt/bridge-git checkout --quiet "$COSS3_BRIDGE_REF" 2>&1; then
        SHA=$(git -C /opt/bridge-git rev-parse HEAD)
        # Файлы моста, но НЕ docker/: скрипты контейнера остаются от образа,
        # иначе правка entrypoint в ветке может сломать сам запуск и отладить
        # это будет нечем.
        cp /opt/bridge-git/*.py /opt/bridge-git/*.inc /opt/bridge-git/*.txt /opt/bridge/ 2>/dev/null || true
        echo "$SHA" > "$COSS3_IO/bridge.sha"
        log "мост обновлён: $(git -C /opt/bridge-git log --oneline -1)"
        log "  SHA записан в ${COSS3_IO}/bridge.sha"
    else
        # Молчаливый откат на запасной мост означал бы опыт над НЕ ТОЙ версией,
        # а результат выглядел бы законным. Это хуже, чем не запуститься.
        die "не смог взять мост из ${COSS3_BRIDGE_GIT} @ ${COSS3_BRIDGE_REF}.
     Проверь адрес, доступ (для приватного репозитория нужен токен в URL)
     и что ref существует. Опыт над неизвестной версией моста бессмыслен,
     поэтому на запасную копию НЕ откатываюсь."
    fi
else
    echo "запечён-в-образ" > "$COSS3_IO/bridge.sha"
    log "мост из образа (COSS3_BRIDGE_GIT не задан) — годится для проверки"
    log "  образа, но не для опытов: версия моста ничем не подтверждена"
fi

# --- идея опыта из git -------------------------------------------------------
# Идея берётся ИЗ КЛОНА, а не строкой в -e. Тогда она версионирована: по SHA
# моста видно не только код, но и с какими флагами он играл, и у десяти копий
# она заведомо одна и та же. Разбор — в pick_experiment.py, потому что он
# обновляется из git, а этот скрипт запечён в образ.
: "${COSS3_EXPERIMENT:=}"
if [ -n "$COSS3_EXPERIMENT" ]; then
    INI=/opt/bridge-git/docker/experiments.ini
    if [ ! -f "$INI" ]; then
        die "задан COSS3_EXPERIMENT=${COSS3_EXPERIMENT}, но файла идей нет:
     ${INI}
     Идея обязана приезжать из git, иначе не сказать, что проверялось.
     Задайте COSS3_BRIDGE_GIT либо снимите COSS3_EXPERIMENT."
    fi
    IDEA=$(python3 /opt/bridge/pick_experiment.py "$INI" "$COSS3_EXPERIMENT" \
               --io "$COSS3_IO" --copy "$COSS3_SLOT" 2>&1) \
        || die "идея не взята:
${IDEA}
     Прогон «без флагов» под именем идеи выглядел бы законным и попал бы в
     сравнение — поэтому не начинаю."
    IDEA_FLAGS=$(printf '%s\n' "$IDEA" | sed -n 's/^COSS3_EXTRA_FLAGS=//p')
    IDEA_WHAT=$(printf '%s\n' "$IDEA" | sed -n 's/^IDEA_WHAT=//p')
    log "идея «${COSS3_EXPERIMENT}»: ${IDEA_WHAT}"
    if [ -n "${COSS3_EXTRA_FLAGS:-}" ]; then
        # Явно заданное перебивает файл, но молча этого делать нельзя: отчёт
        # ссылался бы на идею, а игра шла бы с другими флагами.
        log "  флаги из окружения ПЕРЕБИВАЮТ файл идей:"
        log "    файл:      ${IDEA_FLAGS:-—}"
        log "    окружение: ${COSS3_EXTRA_FLAGS}"
    else
        COSS3_EXTRA_FLAGS="$IDEA_FLAGS"
        log "  флаги: ${COSS3_EXTRA_FLAGS:-— (как на мастере)}"
    fi
fi

# --- профиль игры ------------------------------------------------------------
# Профиль (и настройки партии вместе с ним) игра держит в
# Documents/cossacks внутри префикса, то есть ВНУТРИ контейнера. С --rm он
# умирает вместе с контейнером, и каждый запуск начинается с чистого листа: игра
# заново спрашивает профиль, а настройки партии — нация, сложность, ресурсы —
# каждый раз чьи угодно. Для десяти копий это значит десять разных условий, то
# есть несравнимые опыты.
#
# Поэтому каталог можно подменить томом: смонтируйте свой в /profile, и все
# копии будут стартовать с одинаковыми настройками, которые вы выставили один
# раз.
#   docker run -v "$PWD/profile:/profile" ...
DOCS="${WINEPREFIX}/drive_c/users/root/Documents"
if [ -d /profile ]; then
    mkdir -p "$DOCS"
    rm -rf "$DOCS/cossacks"
    ln -s /profile "$DOCS/cossacks"
    log "профиль игры из тома /profile (общий для всех копий)"
    [ -d /profile/profiles ] && log "  профили: $(ls /profile/profiles 2>/dev/null | tr '\n' ' ')" \
                             || log "  том пуст — игра создаст профиль сама, и он останется здесь"
else
    log "профиль игры внутри контейнера: пропадёт вместе с ним."
    log "  Для повторяемых опытов смонтируйте том: -v \$PWD/profile:/profile"
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
            --human-only --human-state --human-cmd --endgame \
            2>&1 | tee "$COSS3_IO/install.log"

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
# Блок конца партии стоит в ДРУГОМ файле — в интерфейсном акторе. Проверять
# только progress.inc значит не заметить его отсутствия: партия кончится, мост
# смолчит, контейнер встанет. Ровно так 12.09 установщик отрапортовал успех,
# не поставив блок.
гуй = os.path.join(sys.argv[1], "data", "gui", "menu.inc", "doprogress.inc")
try:
    if b"// === BRIDGE ENDGAME" not in open(гуй, "rb").read():
        нет.append("конец партии (doprogress.inc)")
    else:
        print("doprogress.inc: блок конца партии на месте")
except OSError as e:
    нет.append(f"конец партии — файл не прочитан: {e}")
if нет:
    print(f"СТОП: не хватает блоков: {', '.join(нет)}")
    sys.exit(1)
PY
fi

# --- игра --------------------------------------------------------------------
cd "$COSS3_GAME"
# Чистим и пульс интерфейса: без этого файл от ПРОШЛОГО запуска сказал бы
# «партия кончилась поражением» про партию, которой ещё нет.
rm -f coss3_hb.dat coss3_gui.dat coss3_eco_P*.dat

# Трасса прошлого запуска. Она НЕ удаляется — это данные для обучения, — но и
# дописывать в неё нельзя: llm_policy открывает файл на дозапись, и трассы
# разных запусков сливаются в одну. 13.09 отчёт из-за этого объявил «партий 3»,
# хотя запуск был один: разбор режет партии по откату игрового времени и принял
# за них три прогона РАЗНЫХ дней и РАЗНЫХ версий моста.
if [ -s "$COSS3_IO/coss3_bot.jsonl" ]; then
    ARCH="$COSS3_IO/coss3_bot.$(date +%Y%m%d-%H%M%S).jsonl"
    mv "$COSS3_IO/coss3_bot.jsonl" "$ARCH"
    log "трасса прошлого запуска отложена: $(basename "$ARCH")"
fi
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

# --- партия ------------------------------------------------------------------
# Пульса МАЛО. Он идёт и в главном меню: на фоне там крутится демонстрационный
# бой, тик Progress работает, а человеческого игрока нет — и состояние не
# пишется. Политику в такой момент запускать нельзя: она не найдёт состояние и
# решит, что мост не встал. Ждём именно состояние, а если партии нет — начинаем
# её сами командой NEW (блок петли зовёт DoNewGame изнутри игры).
state_ready() { ls "$COSS3_GAME"/coss3_eco_P*.dat >/dev/null 2>&1; }

if state_ready; then
    log "состояние пишется — партия уже идёт"
else
    # Условия партии. Без них DoNewGame берёт то, что осталось в меню, и у
    # десяти копий условия окажутся разными — сравнивать идеи станет нельзя.
    # Префикс MATCH_ нарочно: COSS3_RES уже занято разрешением ЭКРАНА, и
    # столкновение имён тут стоило бы долгой путаницы.
    NEWARGS=""
    [ -n "${COSS3_MATCH_RES:-}" ]    && NEWARGS="$NEWARGS --res ${COSS3_MATCH_RES}"
    [ -n "${COSS3_MATCH_PEACE:-}" ]  && NEWARGS="$NEWARGS --peace ${COSS3_MATCH_PEACE}"
    [ -n "${COSS3_MATCH_AI:-}" ]     && NEWARGS="$NEWARGS --ai ${COSS3_MATCH_AI}"
    [ -n "${COSS3_MATCH_NATION:-}" ] && NEWARGS="$NEWARGS --nation ${COSS3_MATCH_NATION}"
    if [ -n "$NEWARGS" ]; then
        log "состояния нет: игра в меню. Начинаю партию: ${NEWARGS}"
    else
        log "состояния нет: игра в меню. Начинаю партию на настройках из меню."
        log "  Условия НЕ заданы — для опытов задайте COSS3_MATCH_RES/PEACE/AI/NATION,"
        log "  иначе у копий окажутся разные условия и сравнивать их будет нельзя"
    fi
    cd /opt/bridge
    # shellcheck disable=SC2086
    python3 send.py --dir "$COSS3_GAME" --new $NEWARGS 2>&1 | sed 's/^/    /' || true
    cd "$COSS3_GAME"
    for _ in $(seq 1 "${COSS3_NEW_TIMEOUT:-90}"); do
        state_ready && break
        kill -0 "$GAME_PID" 2>/dev/null || die "игра завершилась, не начав партию (см. ${COSS3_IO}/game.log)"
        sleep 1
    done
fi

if state_ready; then
    STATE_FILE=$(ls "$COSS3_GAME"/coss3_eco_P*.dat | head -1)
    log "партия идёт: $(basename "$STATE_FILE")"
    # Слот обязан быть человеческим и без советника — это правило хакатона, и
    # проверить его надо ДО того, как модель наиграет час на негодном слоте.
    if grep -q "human = True" "$STATE_FILE" && grep -q "adviser = False" "$STATE_FILE"; then
        log "  слот человеческий, советник выключен — как требуется"
        # Условия партии — в лог и рядом с трассой: через неделю по трассе без
        # них не сказать, на чём сравнивались идеи.
        for _field in cid food peasants; do
            grep -E "^   ${_field} = " "$STATE_FILE" | sed 's/^/    /' || true
        done
        if [ -f "$COSS3_GAME/coss3_ack.dat" ]; then
            cp "$COSS3_GAME/coss3_ack.dat" "$COSS3_IO/match.dat" 2>/dev/null || true
            grep -E "nat0|nat1|ai1|res|peace" "$COSS3_IO/match.dat" 2>/dev/null \
                | sed 's/^/    условия: /' || true
        fi
    else
        log "  ВНИМАНИЕ: слот НЕ человеческий или включён советник:"
        grep -E "human|adviser" "$STATE_FILE" | sed 's/^/    /'
        log "  опыт на таком слоте негоден — правьте настройки партии"
    fi
else
    die "партия так и не началась за ${COSS3_NEW_TIMEOUT:-90} с.
     Пульс есть, значит тик Progress жив, но человеческого игрока в игре нет.
     Вероятнее всего игра стоит в меню и NEW не сработал. Смотреть:
       docker exec <имя> cat ${COSS3_IO}/game.log
       docker exec <имя> cat ${COSS3_GAME}/coss3_ack.dat"
fi

# --- посмертное -------------------------------------------------------------
# Контейнер НЕ должен умирать вместе с политикой. До 13.09 последней строкой
# стоял `exec python3 llm_policy.py`: политика становилась PID 1, и как только
# партия кончалась, контейнер останавливался. Логи боя после этого не прочитать
# ничем — `docker exec` на остановленном контейнере отвечает
# «container ... is not running», а log_review.py лежит внутри образа.
#
# Поэтому теперь: политика запускается ОБЫЧНЫМ процессом, после неё пишется
# разбор рядом с трассой, и контейнер держится живым.
postmortem() {
    local rc="$1"
    log "модель вышла, код $rc (0 = цель взята, 2 = партия прошла без цели)"
    # Документ по прогону пишется ВСЕГДА, даже когда трассы нет: «модель не
    # сделала ни одного хода» — это тоже результат, и он должен лежать в том же
    # месте, что и удачный, а не теряться в логе контейнера.
    log "пишу документ прогона: ${COSS3_IO}/отчёт.md"
    python3 /opt/bridge/run_report.py "$COSS3_IO" --out "$COSS3_IO/отчёт.md" \
        >/dev/null 2>&1 || log "  не получилось — смотрите трассу руками"
    if [ -s "$COSS3_IO/coss3_bot.jsonl" ]; then
        log "пишу разбор по тактам: ${COSS3_IO}/report.txt"
        python3 /opt/bridge/log_review.py --trace "$COSS3_IO/coss3_bot.jsonl" \
            >"$COSS3_IO/report.txt" 2>&1 || true
    else
        log "трассы нет или она пуста: ${COSS3_IO}/coss3_bot.jsonl"
    fi
    # В лог контейнера — сам документ: он короткий, и это первое, что видно
    # в `docker logs` после конца прогона.
    [ -s "$COSS3_IO/отчёт.md" ] && sed 's/^/    /' "$COSS3_IO/отчёт.md"
    # Квитанция последней команды и хвост лога игры — то, за чем чаще всего
    # лезут после неудачного прогона.
    cp -f "$COSS3_GAME/coss3_ack.dat" "$COSS3_IO/ack_last.dat" 2>/dev/null || true
    echo "$rc" >"$COSS3_IO/policy.rc"
    # Результат наружу, пока контейнер жив. Без этого прогон умирает вместе с
    # ним, а на ферме из десяти копий сравнивать становится нечего уже к утру.
    if [ -n "${COSS3_RESULTS_GIT:-}" ]; then
        RUN_NAME="${COSS3_RESULTS_NAME:-${COSS3_EXPERIMENT:-прогон}/${COSS3_SLOT}}"
        log "отправляю результат в git: ${COSS3_RESULTS_GIT} (${RUN_NAME})"
        python3 /opt/bridge/push_results.py \
            --io "$COSS3_IO" \
            --repo "$COSS3_RESULTS_GIT" \
            --branch "${COSS3_RESULTS_BRANCH:-results}" \
            --key "${COSS3_RESULTS_KEY:-/ssh/results_key}" \
            --name "$RUN_NAME" 2>&1 | sed 's/^/    /' \
            || log "  НЕ ОТПРАВИЛОСЬ. Файлы целы в ${COSS3_IO} — прогон не пропал"
    fi
    if [ "${COSS3_KEEP_ALIVE:-1}" = "1" ]; then
        log "держу контейнер живым (COSS3_KEEP_ALIVE=0 — выключить). Смотреть так:"
        log "  docker exec <имя> cat ${COSS3_IO}/отчёт.md      <- итог прогона"
        log "  docker exec <имя> cat ${COSS3_IO}/report.txt"
        log "  docker exec <имя> python3 /opt/bridge/log_review.py --trace ${COSS3_IO}/coss3_bot.jsonl --ideas"
        # Ждём именно игру, а не sleep: пока она жива, живо и всё остальное,
        # и в контейнер можно зайти за состоянием, квитанцией, логом Wine.
        wait "$GAME_PID" 2>/dev/null || true
        log "игра закрылась — дальше просто стою"
        while true; do sleep 3600; done
    fi
    exit "$rc"
}

# --- политика ----------------------------------------------------------------
if [ "$COSS3_RUN_POLICY" = "1" ]; then
    cd /opt/bridge
    log "запускаю модель: $COSS3_MODEL, такт $COSS3_EVERY, порог волны $COSS3_WAVE_MIN, партий $COSS3_EPISODES"
    # COSS3_EXTRA_FLAGS — то, чем идея отличается от базы (его ставит exp.py).
    # Дописывается В КОНЕЦ, поэтому перебивает одноимённые ключи выше: argparse
    # берёт последнее вхождение. Так идея «--wave-min 40» работает, не требуя
    # трогать COSS3_WAVE_MIN.
    if [ -n "${COSS3_EXTRA_FLAGS:-}" ]; then
        log "  флаги идеи: ${COSS3_EXTRA_FLAGS}"
    fi
    # set +e на время вызова: политика возвращает 2, когда партия прошла без
    # цели, и это НЕ ошибка. С `set -e` такой код обрывал бы скрипт до разбора.
    set +e
    # shellcheck disable=SC2086
    # -u к тому же PYTHONUNBUFFERED: переменную окружения легко потерять при
    # ручном запуске, а ключ виден прямо в команде.
    python3 -u llm_policy.py --human \
        --dir "$COSS3_GAME" \
        --hints "$COSS3_HINTS" \
        --model "$COSS3_MODEL" \
        --every "$COSS3_EVERY" \
        --wave-min "$COSS3_WAVE_MIN" \
        --episodes "$COSS3_EPISODES" \
        --ban market,academi \
        --botlog "$COSS3_IO/coss3_bot.jsonl" \
        --log "$COSS3_IO/coss3_llm.log" \
        ${COSS3_EXTRA_FLAGS:-}
    rc=$?
    set -e
    postmortem "$rc"
else
    log "политика выключена (COSS3_RUN_POLICY=0) — держу игру"
    wait "$GAME_PID"
fi
