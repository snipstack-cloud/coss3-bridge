#!/usr/bin/env bash
# Замер ОДНОЙ копии: сколько ядер она ест и с какой скоростью идёт игровое
# время. Из этих двух чисел считается, какой сервер нужен на десять копий и
# сколько партий в час он даст.
#
# Зачем отдельный скрипт. Выбор между «16 выделенных ядер за $336» и
# «видеокарта RTX 4000 Ada за $555» целиком зависит от того, сколько CPU
# съедает программный растеризатор и во сколько раз он замедляет игру. Это
# ДОГАДКА, пока не измерено, а разница в решении — сотни долларов в месяц.
# Замер на самом дешёвом выделенном дроплете стоит тринадцать центов
# (CPU-Optimized 2 vCPU, $0.0625/час) и занимает двадцать минут.
#
#   ./docker/measure.sh              замерить 120 секунд
#   ./docker/measure.sh 300          замерить 300 секунд
#
# Запускать НА СЕРВЕРЕ. Модель не нужна и ключ не нужен: измеряем игру, а не бота.
set -euo pipefail

SECONDS_TO_MEASURE="${1:-120}"
TAG="${COSS3_TAG:-coss3:1}"
NAME="coss3-measure"
IO="$(mktemp -d)"

log() { echo "[замер $(date +%H:%M:%S)] $*"; }

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "=== чем располагает сервер"
CORES=$(nproc)
MEM_GB=$(awk '/MemTotal/ {printf "%.0f", $2/1048576}' /proc/meminfo)
echo "  ядер: ${CORES}, памяти: ${MEM_GB} ГБ"
if [ -e /dev/dri ]; then
    echo "  /dev/dri есть — видеокарта будет проброшена в контейнер"
    GPU_ARG="--device=/dev/dri:/dev/dri"
else
    echo "  /dev/dri НЕТ — рендер ляжет на процессор (lavapipe)"
    GPU_ARG=""
fi

cleanup
log "поднимаю одну копию (модель выключена, VNC включён)"
# shellcheck disable=SC2086
docker run -d --name "$NAME" $GPU_ARG \
    -e COSS3_RUN_POLICY=0 -e COSS3_VNC=1 \
    -e COSS3_RES="${COSS3_RES:-800x600}" \
    -e COSS3_D3D="${COSS3_D3D:-dxvk}" \
    -p 5900:5900 -v "$IO:/io" "$TAG" >/dev/null

echo
echo "=== ТЕПЕРЬ РУКАМИ, иначе мерить нечего"
echo "  Мост живёт в тике Progress, а тик идёт ТОЛЬКО В БОЮ. Пока игра в меню,"
echo "  игровое время не тикает и замер бессмыслен."
echo
echo "  1. Подключись VNC-клиентом к <адрес сервера>:5900 (без пароля)."
echo "     С мака проще всего:  open vnc://<адрес>:5900"
echo "     Через ssh-туннель:   ssh -L 5900:localhost:5900 user@<адрес>"
echo "  2. Начни бой: свой слот ЧЕЛОВЕК, советник ВЫКЛЮЧЕН, противник компьютер,"
echo "     настройки 1к 0пт, без рынка, без дипа, без пушек."
echo
log "жду появления состояния игры (${IO}/../coss3_eco_P*.dat внутри контейнера)"

# Ждём, пока игра начнёт писать состояние. Признак боя — не пульс: пульс идёт
# и в меню, а вот состояние пишет наш блок, который работает только в партии.
for _ in $(seq 1 600); do
    if docker exec "$NAME" sh -c 'ls /opt/cossacks/coss3_eco_P*.dat' >/dev/null 2>&1; then
        break
    fi
    sleep 2
done
if ! docker exec "$NAME" sh -c 'ls /opt/cossacks/coss3_eco_P*.dat' >/dev/null 2>&1; then
    echo
    echo "ЗА 20 МИНУТ БОЙ ТАК И НЕ НАЧАЛСЯ. Смотреть по порядку:"
    echo "  docker logs $NAME | tail -40                 что сказал контейнер"
    echo "  docker exec $NAME cat /io/game.log | tail    стартовал ли Wine"
    echo "  docker exec $NAME ls /opt/cossacks/*.dat     есть ли пульс coss3_hb.dat"
    echo "Нет даже пульса — не собрался тик Progress, и это уже не про замер."
    exit 1
fi
log "бой идёт, состояние пишется — меряю ${SECONDS_TO_MEASURE} с"

gametime() {
    docker exec "$NAME" sh -c \
        'cat /opt/cossacks/coss3_eco_P*.dat' 2>/dev/null \
        | sed -n 's/.*gametime *= *\([0-9][0-9]*\).*/\1/p' | head -1
}

GT0=$(gametime); WALL0=$(date +%s)
# docker stats --no-stream даёт мгновенный срез; берём несколько и усредняем,
# иначе одиночный выброс решит судьбу сервера за $500.
CPU_SUM=0; CPU_N=0
END=$((WALL0 + SECONDS_TO_MEASURE))
while [ "$(date +%s)" -lt "$END" ]; do
    C=$(docker stats --no-stream --format '{{.CPUPerc}}' "$NAME" 2>/dev/null | tr -d '%')
    # awk, а не bc: bc на голом сервере может отсутствовать, awk есть всегда.
    case "$C" in ''|*[!0-9.]*) ;; *) CPU_SUM=$(awk -v a="$CPU_SUM" -v b="$C" 'BEGIN{print a+b}'); CPU_N=$((CPU_N+1)) ;; esac
    sleep 5
done
GT1=$(gametime); WALL1=$(date +%s)

[ -n "$GT0" ] && [ -n "$GT1" ] || { echo "не смог прочитать gametime — состояние пустое?"; exit 1; }
DGT=$((GT1 - GT0)); DW=$((WALL1 - WALL0))
[ "$CPU_N" -gt 0 ] || { echo "docker stats ничего не дал"; exit 1; }

python3 - "$DGT" "$DW" "$CPU_SUM" "$CPU_N" "$CORES" "$MEM_GB" <<'PY'
import sys
dgt, dw, cpu_sum, cpu_n, cores, mem = (float(x) for x in sys.argv[1:7])
скорость = dgt / dw if dw else 0
ядер = (cpu_sum / cpu_n) / 100 if cpu_n else 0

print()
print("=" * 62)
print("РЕЗУЛЬТАТ ЗАМЕРА ОДНОЙ КОПИИ")
print("=" * 62)
print(f"  игрового времени за {dw:.0f} с реального: {dgt:.0f} с")
print(f"  СКОРОСТЬ ИГРЫ: {скорость:.2f}x "
      f"(на живой Windows-машине проекта было 1.38x)")
print(f"  ЕСТ ЯДЕР: {ядер:.2f} (усреднено по {cpu_n:.0f} замерам)")
print()

if скорость <= 0:
    print("  Игровое время не двигалось. Партия на паузе или в меню — замер негоден.")
    raise SystemExit(1)

эпизод_мин = 15 / скорость          # эпизод в 15 игровых минут
парт_час_копия = 60 / эпизод_мин
print(f"  эпизод в 15 игровых минут идёт {эпизод_мин:.0f} мин реального времени")
print(f"  одна копия даёт {парт_час_копия:.1f} партий в час")
print()
print("-" * 62)
print("СКОЛЬКО КОПИЙ И КАКОЙ ДРОПЛЕТ")
print("-" * 62)
ядер_на_10 = ядер * 10
память_на_10 = 1.5 * 10 + 2        # ~1.5 ГБ на копию плюс система
print(f"  десять копий попросят ~{ядер_на_10:.0f} ядер и ~{память_на_10:.0f} ГБ памяти")
print(f"  и дадут ~{парт_час_копия * 10:.0f} партий в час")
print()

планы = [
    ("CPU-Optimized  8/16",   8,  16, 168),
    ("CPU-Optimized 16/32",  16,  32, 336),
    ("CPU-Optimized 32/64",  32,  64, 672),
    ("General Purpose 16/64",16,  64, 504),
    ("GPU RTX 4000 Ada 8/32", 8,  32, 555),
]
print(f"  {'план':<22} {'ядер':>5} {'ГБ':>4} {'$/мес':>7}  вердикт")
for имя, c, m, цена in планы:
    хватает = c >= ядер_на_10 and m >= память_на_10
    if "GPU" in имя:
        вердикт = "мерить отдельно: с картой ядер нужно меньше"
    elif хватает:
        за_партию = цена / (парт_час_копия * 10 * 730) if парт_час_копия else 0
        вердикт = f"ГОДИТСЯ, ~${за_партию:.3f} за партию"
    else:
        не_хватает = []
        if c < ядер_на_10: не_хватает.append("ядер")
        if m < память_на_10: не_хватает.append("памяти")
        вердикт = "мало " + " и ".join(не_хватает)
    print(f"  {имя:<22} {c:>5} {m:>4} {цена:>7}  {вердикт}")
print()
print("  Сколько копий влезет на ЭТОТ сервер прямо сейчас: "
      f"{int(min(cores / ядер, (mem - 2) / 1.5)) if ядер else 0}")
print()
print("  Если скорость сильно ниже 1.0 — рендер считает процессор, и стоит")
print("  померить то же самое на GPU-дроплете: там ядра почти не тратятся,")
print("  а партий в час может выйти в разы больше за те же деньги.")
PY
echo
log "контейнер сейчас будет убран; чтобы оставить его — Ctrl+C не поможет, запусти без trap"
