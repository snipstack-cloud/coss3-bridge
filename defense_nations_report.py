#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор серии «только оборона» по нациям противника (28.10).

    python defense_nations_report.py ~/io-d-*            # тома фермы
    python defense_nations_report.py results/2026-10-28/defense_nations_v2/*

Для каждой копии (= нации) читает coss3_snap.jsonl (полное состояние по тактам), coss3_bot.jsonl (приказы
и клетка ратуши), match.dat (nat1) и отчёт.md (исход). Печатает таблицу и по каждой нации — нашествия:
отрезки, когда его бойцы стояли в 5 клетках от нашей ратуши (начало, пик, состав), первое движение его
группы к нам, его войска по видам из p1_fighters, потери обеих сторон. Это сбор данных, а не сравнение.
"""
import glob
import json
import os
import re
import sys

NATIONS = {-2: "spe", 0: "aus", 1: "fra", 2: "eng", 3: "spa", 4: "rus", 5: "ukr", 6: "pol", 7: "swe", 8: "pru", 9: "ven",
           10: "tur", 11: "alg", 12: "mis", 13: "net", 14: "den", 15: "por", 16: "pie", 17: "sax", 18: "bav", 19: "hun",
           20: "swi", 21: "sco", 22: "tat", 23: "lit"}
ИМЕНА = {"aus": "Австрия", "fra": "Франция", "eng": "Англия", "spa": "Испания", "rus": "Россия", "ukr": "Украина",
         "pol": "Польша", "swe": "Швеция", "pru": "Пруссия", "ven": "Венеция", "tur": "Турция", "alg": "Алжир",
         "net": "Нидерланды", "den": "Дания", "por": "Португалия", "pie": "Пьемонт", "sax": "Саксония",
         "bav": "Бавария", "hun": "Венгрия", "swi": "Швейцария", "sco": "Шотландия"}
R = 5          # клеток от ратуши — «у базы», как в hints_home_defense
ЗНАЧИМО = 5    # бойцов у базы, с которых считаем нашествие


def мм(gt):
    gt = int(gt or 0)
    return f"{gt // 60}:{gt % 60:02d}"


def jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    for l in open(path, encoding="utf-8", errors="replace"):
        l = l.strip()
        if not l:
            continue
        try:
            out.append(json.loads(l))
        except Exception:
            pass
    return out


def i(st, k):
    try:
        return int(float(st.get(k) or 0))
    except (TypeError, ValueError):
        return 0


def разобрать(d):
    snap = jsonl(os.path.join(d, "coss3_snap.jsonl"))
    bot = jsonl(os.path.join(d, "coss3_bot.jsonl"))
    if not snap:
        return None
    дом = None
    for r in bot:
        st = r.get("state") or {}
        if st.get("my_cx") is not None:
            дом = (int(st["my_cx"]), int(st["my_cy"]))
            break
    nat1 = None
    m = os.path.join(d, "match.dat")
    if os.path.exists(m):
        mm_ = re.search(r"nat1\s*=\s*(-?\d+)", open(m, encoding="latin-1").read())
        nat1 = int(mm_.group(1)) if mm_ else None
    исход = ""
    o = os.path.join(d, "отчёт.md")
    if os.path.exists(o):
        for l in open(o, encoding="utf-8", errors="replace"):
            if l.startswith("| 1 |"):
                исход = " ".join(x.strip() for x in l.strip("|\n").split("|")[1:4])
                break
    кон = snap[-1]
    # первое движение его группы к нашей базе
    движ = next((r for r in snap if i(r, "p1_mv_base") > 0), None)
    # его бойцы у нашей базы по тактам
    ряд = []
    for r in snap:
        n = пик = стр = кон_ = 0
        if дом:
            for c in r.get("ecells") or []:
                try:
                    if max(abs(int(c["x"]) - дом[0]), abs(int(c["y"]) - дом[1])) <= R:
                        n += i(c, "n"); пик += i(c, "пик"); стр += i(c, "стрелков"); кон_ += i(c, "конных")
                except (KeyError, TypeError, ValueError):
                    pass
        ряд.append((i(r, "gametime"), n, пик, стр, кон_, i(r, "en_near_dist")))
    нашествия = []
    тек = None
    for gt, n, p, s, c, _ in ряд:
        if n >= ЗНАЧИМО:
            if тек is None:
                тек = {"с": gt, "по": gt, "пик": (n, p, s, c), "пик_gt": gt}
            else:
                тек["по"] = gt
                if n > тек["пик"][0]:
                    тек["пик"], тек["пик_gt"] = (n, p, s, c), gt
        elif тек is not None:
            нашествия.append(тек); тек = None
    if тек is not None:
        нашествия.append(тек)
    # en_near_dist — мировые единицы от ратуши до ближайшего его объекта; клетка сетки = map_w / 16 (block_hstate: floor(x*16/hmw)).
    клетка = float(кон.get("map_w") or 256) / 16.0
    близко = next((gt for gt, n, *_ , dist in ряд if 0 < dist <= R * клетка), None)
    виды = re.findall(r"(\w+)=hp", str(кон.get("p1_fighters") or ""))
    армия_пик = max(i(r, "p1_army") for r in snap)
    вехи = {}
    for k, имя in (("p1_ba17", "казарма"), ("p1_tower", "башня"), ("p1_stable", "конюшня"), ("p1_academi", "академия"),
                   ("p1_ba18", "казарма18")):
        r = next((r for r in snap if i(r, k) > 0), None)
        if r:
            вехи[имя] = мм(r["gametime"])
    return dict(
        dir=d, sid=NATIONS.get(nat1, f"?{nat1}"), nat1=nat1, исход=исход, gt=i(кон, "gametime"),
        его=(i(кон, "p1_army"), i(кон, "p1_inf"), i(кон, "p1_shoot"), i(кон, "p1_cav")), его_пик=армия_пик,
        его_кр=i(кон, "p1_peasants"), его_потери=(i(кон, "p1_mil_lost"), i(кон, "p1_pea_lost")),
        наши=(i(кон, "mil_inf"), i(кон, "mil_shooters"), i(кон, "mil_cav"), i(кон, "peasants")),
        наши_потери=(i(кон, "my_mil_lost"), i(кон, "my_pea_lost")),
        движ=(мм(движ["gametime"]), i(движ, "p1_mv_n")) if движ else None,
        близко=мм(близко) if близко is not None else None, нашествия=нашествия, виды=виды, вехи=вехи, дом=дом)


def main(argv):
    пути = []
    for a in argv or ["~/io-d-*"]:
        пути += sorted(glob.glob(os.path.expanduser(a)))
    строки = [x for x in (разобрать(p) for p in пути if os.path.isdir(p)) if x]
    print("| нация | исход | его армия к концу (пех/стр/кон), пик | его крестьян | его потери (бойцов/кр.) | наши потери | "
          "первое движение к нам | первый враг в 5 кл. | нашествий | наша армия |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for x in строки:
        print(f"| {ИМЕНА.get(x['sid'], x['sid'])} ({x['sid']}) | {x['исход'] or мм(x['gt'])} | {x['его'][0]} ({x['его'][1]}/{x['его'][2]}/{x['его'][3]}), "
              f"пик {x['его_пик']} | {x['его_кр']} | {x['его_потери'][0]}/{x['его_потери'][1]} | "
              f"{x['наши_потери'][0]}/{x['наши_потери'][1]} | "
              f"{(x['движ'][0] + ' (' + str(x['движ'][1]) + ')') if x['движ'] else '—'} | {x['близко'] or '—'} | "
              f"{len(x['нашествия'])} | {x['наши'][0]}+{x['наши'][1]}+{x['наши'][2]} при {x['наши'][3]} кр. |")
    for x in строки:
        print(f"\n### {ИМЕНА.get(x['sid'], x['sid'])} ({x['sid']}, nat1={x['nat1']}) — {x['dir']}")
        print(f"ратуша {x['дом']}; его виды войск: {', '.join(x['виды']) or '—'}; вехи: "
              + (", ".join(f"{k} {v}" for k, v in x['вехи'].items()) or "—"))
        if not x["нашествия"]:
            print(f"нашествий у базы (≥{ЗНАЧИМО} бойцов в {R} кл.) не было")
        for н in x["нашествия"]:
            n, p, s, c = н["пик"]
            print(f"  нашествие {мм(н['с'])}–{мм(н['по'])}: пик {n} бойцов в {мм(н['пик_gt'])} (пех {p}, стр {s}, кон {c})")


if __name__ == "__main__":
    main(sys.argv[1:])
