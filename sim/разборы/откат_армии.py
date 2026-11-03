# -*- coding: utf-8 -*-
# РЕЗКИЙ ОТКАТ АРМИИ НАЗАД: ищем такты, где mil_away падает сильно.
# Отход от гибели отделяем потерями: выросли — перебили, не выросли — ушла сама.
import json, os, glob, re, collections

ПОРОГ_ДОЛЯ = 0.35      # падение не меньше 35 % от того, что было в поле
ПОРОГ_ЧЕЛОВЕК = 40     # и не меньше 40 бойцов — чтобы не ловить мелочь

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

ПРИЧИНЫ = [
    ("ВЫХОД ОТМЕНЁН", "выход отменён"),
    ("ОТХОД ПРИ ПОДХОДЕ", "отход при подходе"),
    ("сироты", "сироты (отзыв заблудившихся)"),
    ("ДОМОЙ", "волна домой"),
    ("RETREAT", "приказ RETREAT"),
    ("стойка дома", "стойка дома"),
    ("ЛАГЕРЬ СНЯТ", "лагерь снят"),
    ("МАЛО_СИЛ", "мало сил"),
    ("заслон", "заслон"),
]

всего = collections.Counter()
события = []
файлы = sorted(glob.glob("/home/lapst/io-*/coss3_bot.jsonl")) + sorted(glob.glob("/home/lapst/io-*/coss3_bot_P1.jsonl"))
for f in файлы:
    try:
        T = такты(f)
    except Exception:
        continue
    if len(T) < 50:
        continue
    том = f.split("/")[3]
    сторона = "P1" if f.endswith("_P1.jsonl") else "P0"
    пред_away = пред_потери = None
    for t in T:
        s = t.get("state") or {}
        away = s.get("mil_away")
        пот = s.get("my_mil_lost")
        if away is None:
            continue
        if пред_away is not None and пред_away >= ПОРОГ_ЧЕЛОВЕК:
            падение = пред_away - away
            if падение >= ПОРОГ_ЧЕЛОВЕК and падение >= ПОРОГ_ДОЛЯ * пред_away:
                убыль = (пот - пред_потери) if (пот is not None and пред_потери is not None) else None
                w = why(t)
                метки = [имя for игла, имя in ПРИЧИНЫ if игла in w]
                вид = "ПЕРЕБИЛИ" if (убыль is not None and убыль >= падение * 0.6) else (
                      "УШЛА САМА" if (убыль is not None and убыль <= падение * 0.2) else "СМЕШАННО")
                всего[вид] += 1
                for m in метки:
                    всего["причина: " + m] += 1
                события.append((том, сторона, t.get("gt") or 0, пред_away, away, падение, убыль, вид, метки))
        пред_away, пред_потери = away, пот

print("ФАЙЛОВ разобрано:", len(файлы), "| событий резкого откатa:", len(события))
print()
print("ПО ВИДУ:")
for k in ("УШЛА САМА", "СМЕШАННО", "ПЕРЕБИЛИ"):
    print("   %-10s %d" % (k, всего[k]))
print()
print("ПРИЧИНЫ В ТАКТЕ ОТКАТА (сколько событий их несут):")
for k, v in всего.most_common():
    if k.startswith("причина: "):
        print("   %-34s %d" % (k[9:], v))
print()
print("САМЫЕ КРУПНЫЕ ОТКАТЫ, КОТОРЫЕ НЕ ГИБЕЛЬ:")
ушла = [e for e in события if e[7] != "ПЕРЕБИЛИ"]
ушла.sort(key=lambda e: -e[5])
for том, сторона, gt, было, стало, падение, убыль, вид, метки in ушла[:12]:
    print("   %-9s %s %2d:%02d  в поле %4d -> %4d (-%3d), потери +%s, %s, %s"
          % (том, сторона, gt // 60, gt % 60, было, стало, падение,
             убыль if убыль is not None else "?", вид, ", ".join(метки) or "метки нет"))
