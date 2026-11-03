# -*- coding: utf-8 -*-
# Двигались ли бойцы в такте «отката»? Сверяем ocells (наши клетки с числами)
# до и после. Если клетки те же, а mil_away упал — переехал якорь базы или сетка.
import json, glob

ПОРОГ_ДОЛЯ, ПОРОГ_ЧЕЛОВЕК = 0.35, 40

def такты(путь):
    T = []
    for l in open(путь, encoding="utf-8", errors="replace"):
        l = l.strip()
        if not l:
            continue
        try:
            T.append(json.loads(l))
        except Exception:
            pass
    return [t for t in T if "finish" not in t]

def why(t):
    w = t.get("why")
    return " | ".join(map(str, w)) if isinstance(w, list) else str(w or "")

def клетки(s):
    v = s.get("ocells")
    если = {}
    if isinstance(v, list):
        for r in v:
            try:
                если[(int(r[0]), int(r[1]))] = int(r[2])
            except Exception:
                pass
    return если

совпали = двинулись = 0
примеры = []
for f in sorted(glob.glob("/home/lapst/io-*/coss3_bot*.jsonl")):
    try:
        T = такты(f)
    except Exception:
        continue
    if len(T) < 50:
        continue
    import collections
    м = collections.Counter(str(t.get("model") or "") for t in T)
    if м.get("стратегия", 0) <= len(T) * 0.5:
        continue
    том = f.split("/")[3]
    for i in range(1, len(T)):
        s0, s1 = (T[i - 1].get("state") or {}), (T[i].get("state") or {})
        a0, a1 = s0.get("mil_away"), s1.get("mil_away")
        g = T[i].get("gt") or 0
        if a0 is None or a1 is None or g < 120 or a0 < ПОРОГ_ЧЕЛОВЕК:
            continue
        п = a0 - a1
        if п < ПОРОГ_ЧЕЛОВЕК or п < ПОРОГ_ДОЛЯ * a0:
            continue
        w = why(T[i])
        if any(x in w for x in ("сироты", "МАЛО_СИЛ", "заслон", "стойка дома",
                                "ВЫХОД ОТМЕНЁН", "ДОМОЙ", "ОТХОД", "RETREAT")):
            continue
        к0, к1 = клетки(s0), клетки(s1)
        if not к0 or not к1:
            continue
        общие = set(к0) & set(к1)
        схожесть = sum(min(к0[c], к1[c]) for c in общие)
        всего0 = sum(к0.values()) or 1
        доля = схожесть / всего0
        если_стояли = доля >= 0.9
        if если_стояли:
            совпали += 1
        else:
            двинулись += 1
        if len(примеры) < 8:
            примеры.append((том, g, a0, a1, всего0, sum(к1.values()), round(доля, 2),
                            "СТОЯЛИ НА МЕСТЕ" if если_стояли else "двигались",
                            sorted(к0.items())[:4], sorted(к1.items())[:4]))

print("БЕЗЫМЯННЫЕ ОТКАТЫ, у которых есть клетки:")
print("   бойцы СТОЯЛИ (клетки те же на 90 %%+): %d" % совпали)
print("   бойцы действительно двигались:         %d" % двинулись)
print()
for том, g, a0, a1, в0, в1, доля, вид, к0, к1 in примеры:
    print("   %-11s %2d:%02d  mil_away %4d->%4d | в клетках всего %4d->%4d | совпало %.0f%% — %s"
          % (том, g // 60, g % 60, a0, a1, в0, в1, доля * 100, вид))
    print("        клетки до:    %s" % к0)
    print("        клетки после: %s" % к1)
