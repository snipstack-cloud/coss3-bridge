#!/bin/bash
# 4.10 (§74): поиск стратегии с рычагами сбора волн (--сбор), три зерна, затем проверка.
# Запуск: nohup caffeinate -i bash sim/ночь/сбор_04_10.sh > /dev/null 2>&1 &
set -u
cd ~/coss3-bridge || exit 1
OUT=sim/ночь/сбор_04_10
mkdir -p "$OUT"
echo "старт $(date '+%F %T')" > "$OUT/журнал.txt"
for s in 1 2 3; do
  COSS3_MIX=случайный python3 sim/поиск_стратегии.py --смесь --хозяйство --тактика --все-прокачки --сбор \
    --gens 80 --pop 48 --k 18 --seed "$s" --out "sim/поиск/сб_s$s.json" > "$OUT/поиск_s$s.txt" 2>&1 &
done
wait
echo "поиск кончен $(date '+%F %T')" >> "$OUT/журнал.txt"
python3 sim/проверка_пары.py sim/поиск/сл2_s1.json sim/поиск/н4_s1.json sim/поиск/сб_s1.json sim/поиск/сб_s2.json sim/поиск/сб_s3.json \
  --json "$OUT/стратегии.json" > "$OUT/ИТОГ.txt" 2>&1
echo "конец $(date '+%F %T')" >> "$OUT/журнал.txt"
