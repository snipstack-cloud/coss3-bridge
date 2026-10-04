#!/bin/bash
# 4.10 (§76, §79-§81): поиск стратегии с долей мушкетёров и отрядами. А — ядро (наш строй выкл.),
# Б — гипотеза COSS3_OUR_SCREEN=1. По два зерна. Запуск: nohup caffeinate -i bash ... &
set -u
cd ~/coss3-bridge || exit 1
OUT=sim/ночь/отряды_04_10
mkdir -p "$OUT"
echo "старт $(date '+%F %T')" > "$OUT/журнал.txt"
for s in 1 2; do
  COSS3_MIX=случайный python3 sim/поиск_стратегии.py --смесь --хозяйство --тактика --все-прокачки --состав --отряды \
    --gens 80 --pop 48 --k 18 --seed "$s" --out "sim/поиск/отрА_s$s.json" > "$OUT/поиск_А$s.txt" 2>&1 &
  COSS3_OUR_SCREEN=1 COSS3_MIX=случайный python3 sim/поиск_стратегии.py --смесь --хозяйство --тактика --все-прокачки --состав --отряды \
    --gens 80 --pop 48 --k 18 --seed "$s" --out "sim/поиск/отрБ_s$s.json" > "$OUT/поиск_Б$s.txt" 2>&1 &
done
wait
echo "поиск кончен $(date '+%F %T')" >> "$OUT/журнал.txt"
{
  echo "=== ядро (наш строй выкл.) ==="
  python3 sim/проверка_пары.py sim/поиск/сл2_s1.json sim/поиск/отрА_s1.json sim/поиск/отрА_s2.json sim/поиск/отрБ_s1.json sim/поиск/отрБ_s2.json 2>&1 | grep -v "^ПРОТИВНИК\|^ХОЗЯЙ\|^корпус"
  echo; echo "=== гипотеза (COSS3_OUR_SCREEN=1) ==="
  COSS3_OUR_SCREEN=1 python3 sim/проверка_пары.py sim/поиск/сл2_s1.json sim/поиск/сл2_мушк15.json sim/поиск/отрА_s1.json sim/поиск/отрА_s2.json sim/поиск/отрБ_s1.json sim/поиск/отрБ_s2.json 2>&1 | grep -v "^ПРОТИВНИК\|^ХОЗЯЙ\|^корпус"
} > "$OUT/ИТОГ.txt"
echo "конец $(date '+%F %T')" >> "$OUT/журнал.txt"
