# -*- coding: utf-8 -*-
"""Сверка «ратуша у леса» ПО СЛОТАМ через пару волн: hall_report.py <прямая> <зеркало> [дата]

Зачем отдельный счёт. `wood_slots_near` — число деревьев вокруг поставленной
ратуши, и оно зависит от УГЛА КАРТЫ, в котором стоит слот, а не только от ключа.
Поэтому сравнивать слот 0 со слотом 1 внутри копии НЕЛЬЗЯ: это сравнение двух
разных углов. Честное сравнение — ОДИН И ТОТ ЖЕ слот в двух волнах: в прямой на
нём файл с ключом, в зеркале тот же слот без ключа. 3.11 я чуть не прочитал
«ключ работает в одной копии из трёх», сравнив слоты между собой.
"""
import json, os, sys, statistics as S

арг = sys.argv[1:]
if len(арг) < 2:
    print(__doc__)
    raise SystemExit(2)
ПРЯМАЯ, ЗЕРКАЛО = арг[0], арг[1]
ДАТА = арг[2] if len(арг) > 2 else "2026-11-03"
БАЗА = os.path.expanduser("~/coss3-results/" + ДАТА)


def такты(p):
    out = []
    for l in open(p, encoding="utf-8"):
        l = l.strip()
        if l:
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
    return out


def мм(g):
    return "—" if g is None else "%d:%02d" % (int(g) // 60, int(g) % 60)


def сторона(кат, слот):
    o = json.load(open(os.path.join(кат, "опыт.json"), encoding="utf-8"))
    стр = o.get("флаги" if слот == 0 else "флаги2", "")
    файл = стр.split("--strategy")[1].split()[0] if "--strategy" in стр else ""
    return os.path.basename(файл)


def снять(кат, слот):
    p = os.path.join(кат, "coss3_bot.jsonl" if слот == 0 else "coss3_bot_P1.jsonl")
    if not os.path.exists(p):
        return None
    с = [t for t in такты(p) if t.get("state")]
    рат = [t for t in с if (t["state"].get("centers") or 0) >= 1]
    s0 = рат[0]["state"] if рат else {}
    п5 = {}
    for t in с:
        if (t.get("gt") or 0) <= 300:
            п5 = t["state"]
    def впервые(поле, порог):
        for t in с:
            try:
                v = float(t["state"].get(поле))
            except (TypeError, ValueError):
                continue
            if v >= порог:
                return t.get("gt")
    return {
        "файл": сторона(кат, слот),
        "ключ": ("ЛЕС" if "_лес" in сторона(кат, слот) else "без ключа"),
        "ратуша_в": (рат[0].get("gt") if рат else None),
        "wood_sl": s0.get("wood_slots_near"),
        "stone_sl": s0.get("stone_slots_near"),
        "дер5": п5.get("wood"), "кам5": п5.get("stone"),
        "на_дер5": п5.get("on_wood"), "на_кам5": п5.get("on_stone"),
        "казарма2": впервые("ba17", 2),
    }


данные = {}
for волна in (ПРЯМАЯ, ЗЕРКАЛО):
    d = os.path.join(БАЗА, волна)
    if not os.path.isdir(d):
        print("нет каталога:", d)
        raise SystemExit(1)
    for к in sorted(os.listdir(d)):
        for слот in (0, 1):
            с = снять(os.path.join(d, к), слот)
            if с:
                данные[(волна, к.split("-")[0], слот)] = с

print("СВЕРКА ПО СЛОТАМ: %s (прямая) против %s (зеркало), каталог %s"
      % (ПРЯМАЯ, ЗЕРКАЛО, ДАТА))
print("Сравниваются ОДИН И ТОТ ЖЕ слот в двух волнах — один угол карты, разные файлы.")
print()
ш = "%-5s %-5s %-10s %8s %9s %8s %8s %9s"
print(ш % ("слот", "коп", "ключ", "ратуша", "wood_sl", "stone_sl", "дер 5:00", "казарма2"))
пары_wood = []
for слот in (0, 1):
    for коп in ("1", "2", "3"):
        a = данные.get((ПРЯМАЯ, коп, слот))
        b = данные.get((ЗЕРКАЛО, коп, слот))
        if not (a and b):
            continue
        for имя, d in (("прямая", a), ("зеркало", b)):
            print(ш % (слот, коп, d["ключ"], мм(d["ратуша_в"]), d["wood_sl"],
                       d["stone_sl"], d["дер5"], мм(d["казарма2"])))
        слес = a if a["ключ"] == "ЛЕС" else b
        сбез = b if a["ключ"] == "ЛЕС" else a
        if слес["ключ"] == сбез["ключ"]:
            # ОТКАЗ, А НЕ ЧИСЛО (3.11): если ключ стоит у ОБОИХ файлов (или ни у
            # одного), сравнивать нечего — скрипт иначе выдаёт разницу углов
            # карты за действие ключа. Проверено на паре bot2_wood_aca2, где
            # `ратуша_у_леса` есть у обоих плеч.
            print("      -> СРАВНЕНИЕ НЕ ДЕЛАЕТСЯ: ключ одинаков у обеих сторон"
                  " (%s и %s) — это не пара про ратушу у леса"
                  % (слес["файл"], сбез["файл"]))
            continue
        try:
            пары_wood.append((float(слес["wood_sl"]), float(сбез["wood_sl"])))
            print("      -> с ключом %s против %s без ключа: %+.0f деревьев"
                  % (слес["wood_sl"], сбез["wood_sl"],
                     float(слес["wood_sl"]) - float(сбез["wood_sl"])))
        except (TypeError, ValueError):
            print("      -> сравнить нечем: поля нет")
print()
if пары_wood:
    лучше = sum(1 for a, b in пары_wood if a > b)
    раз = [a - b for a, b in пары_wood]
    print("ИТОГ по шести сравнениям одного слота: ключ дал БОЛЬШЕ деревьев в %d из %d;"
          % (лучше, len(пары_wood)))
    print("   разница по деревьям: %s, медиана %+.0f"
          % (" / ".join("%+.0f" % x for x in sorted(раз)), S.median(раз)))
    print("   если разница около нуля — место и без ключа было у леса, и ключ ничего не меняет.")
