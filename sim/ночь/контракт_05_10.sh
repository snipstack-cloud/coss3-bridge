#!/bin/bash
# 5.10 ночь (§97): контракт волны живого моста (Windows 5.10) в симуляторе.
# Вопрос: правило «готовая волна бьёт ближнюю кучу при местном перевесе ≥ штурм_при (0,92)» —
# по §94 такой удар против этого игрока проигрышен. Держит ли шт_s2 размен с ним, и какой порог нужен.
# МЕРЫ ДО ПРОГОНА:
#  A. шт_s2 без контракта / с контрактом при рядом_при 0,92 (как живьём) 1,2 1,5 2,0 3,0 99 (= не бить ближнюю):
#     размен на p5 (агент p3о по записи p5) и p3о — ЖДЁМ, что 0,92 хуже «без контракта», а 1,5+ ближе к нему;
#     случайный — уничтожена/размен (на нём ИИ-подобный противник; победа 5.10 над ИИ шла с 0,92).
#  B. поиск с контрактом: кр_s1-3 с рычагом рядом_при (--рядом), кш_s4-6 без него (рядом = штурм_при, как живьём).
#     ЖДЁМ: рядом_при у кр сходится выше 1,2 во всех трёх зёрнах; кр не хуже кш на p3о/p5.
#  C. проверка всех на случайный / p3 / p3о / p2 / p5 с контрактом.
set -u
cd ~/coss3-bridge || exit 1
OUT=sim/ночь/контракт_05_10
mkdir -p "$OUT"
J="$OUT/журнал.txt"
echo "старт $(date '+%F %T') на $(git rev-parse --short HEAD)" > "$J"
export COSS3_P5=1

# A. сетка порога ближней кучи на шт_s2
python3 - <<'PY'
import json
w = json.load(open("sim/поиск/шт_s2.json", encoding="utf-8"))
for р in (1.2, 1.5, 2.0, 3.0, 99.0):
    x = json.loads(json.dumps(w)); x["итог"]["рядом_при"] = р
    json.dump(x, open(f"sim/ночь/контракт_05_10/шт_s2_рядом{р:g}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PY
COSS3_WAVE_CONTRACT=0 python3 sim/проверка_пары.py sim/поиск/шт_s2.json --json "$OUT/A_без.json" > "$OUT/A_без.txt" 2>&1
COSS3_WAVE_CONTRACT=1 python3 sim/проверка_пары.py sim/поиск/шт_s2.json "$OUT"/шт_s2_рядом*.json --json "$OUT/A_контракт.json" > "$OUT/A_контракт.txt" 2>&1
echo "A кончено $(date '+%F %T')" >> "$J"

# B. поиск с контрактом, 80 × 48 × 18, как §90
for s in 1 2 3; do
  COSS3_WAVE_CONTRACT=1 COSS3_MIX=случайный python3 sim/поиск_стратегии.py --смесь --хозяйство --тактика --все-прокачки --состав --штурм --рядом \
    --gens 80 --pop 48 --k 18 --seed "$s" --out "sim/поиск/кр_s$s.json" > "$OUT/поиск_кр_s$s.txt" 2>&1 &
done
wait
echo "B1 кончено $(date '+%F %T')" >> "$J"
for s in 4 5 6; do
  COSS3_WAVE_CONTRACT=1 COSS3_MIX=случайный python3 sim/поиск_стратегии.py --смесь --хозяйство --тактика --все-прокачки --состав --штурм \
    --gens 80 --pop 48 --k 18 --seed "$s" --out "sim/поиск/кш_s$s.json" > "$OUT/поиск_кш_s$s.txt" 2>&1 &
done
wait
echo "B2 кончено $(date '+%F %T')" >> "$J"

# C. проверка с контрактом
COSS3_WAVE_CONTRACT=1 python3 sim/проверка_пары.py sim/поиск/шт_s2.json sim/поиск/кр_s1.json sim/поиск/кр_s2.json sim/поиск/кр_s3.json \
  sim/поиск/кш_s4.json sim/поиск/кш_s5.json sim/поиск/кш_s6.json --json "$OUT/C.json" > "$OUT/C.txt" 2>&1
python3 - <<'PY' >> "$OUT/C.txt"
import json
for f in ("кр_s1", "кр_s2", "кр_s3", "кш_s4", "кш_s5", "кш_s6"):
    try:
        п = json.load(open(f"sim/поиск/{f}.json", encoding="utf-8"))["итог"]
        print(f, "штурм_при", round(п.get("штурм_при", 0), 2), "рядом_при", round(п.get("рядом_при", п.get("штурм_при", 0)), 2),
              "T1", round(п["T1"]), "доля_мушк", round(п.get("доля_мушк", 0), 2), "отход", round(п.get("отход", 0), 2))
    except Exception as e:
        print(f, "нет:", e)
PY
echo "конец $(date '+%F %T')" >> "$J"
