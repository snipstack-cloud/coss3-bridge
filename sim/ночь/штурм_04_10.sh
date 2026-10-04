#!/bin/bash
# 4.10 (§88-§89): поиск с рычагом «штурм при перевесе» и отходом по голове; три зерна, затем проверка.
set -u
cd ~/coss3-bridge || exit 1
OUT=sim/ночь/штурм_04_10
mkdir -p "$OUT"
echo "старт $(date '+%F %T')" > "$OUT/журнал.txt"
for s in 1 2 3; do
  COSS3_MIX=случайный python3 sim/поиск_стратегии.py --смесь --хозяйство --тактика --все-прокачки --состав --штурм \
    --gens 80 --pop 48 --k 18 --seed "$s" --out "sim/поиск/шт_s$s.json" > "$OUT/поиск_s$s.txt" 2>&1 &
done
wait
echo "поиск кончен $(date '+%F %T')" >> "$OUT/журнал.txt"
python3 sim/проверка_пары.py sim/поиск/отрА_s2.json sim/поиск/шт_s1.json sim/поиск/шт_s2.json sim/поиск/шт_s3.json 2>&1 \
  | grep -v "^ПРОТИВНИК\|^ХОЗЯЙ\|^корпус" > "$OUT/ИТОГ.txt"
echo "конец $(date '+%F %T')" >> "$OUT/журнал.txt"
