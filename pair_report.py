# -*- coding: utf-8 -*-
"""Разбор пары волн бот-против-бота: прямая + зеркало, по три копии.

Ярлыки сторон — из опыт.json (поля флаги/флаги2), а НЕ по имени файла.
Итоговые числа — ПОСЛЕДНЕЕ НЕПУСТОЕ значение поля (последняя запись урезана).
Армия считается ГОЛОВАМИ: mil_inf + mil_shooters + mil_cav + mil_guns.
Поле fighters — строка-каталог юнитов движка, для счёта НЕ годится.
Академия своей стороны читается из трассы ПРОТИВНИКА (p1_academi), потому что
своего поля академии в снимке нет.
"""
import json, os, sys, statistics as S

# Имена волн и дата — аргументами: pair_report.py <прямая> <зеркало> [дата]
# Зашитые имена однажды уже заставили править скрипт под каждую пару.
_арг = sys.argv[1:]
ВОЛНЫ = _арг[:2] if len(_арг) >= 2 else ["bot2_save_net", "bot2_save_net_mirror"]
_дата = _арг[2] if len(_арг) > 2 else "2026-11-03"
БАЗА = os.path.expanduser("~/coss3-results/" + _дата)
АРМИЯ = ("mil_inf", "mil_shooters", "mil_cav", "mil_guns")


def такты(путь):
    out = []
    with open(путь, encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
    return out


def чис(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def посл(ts, поле):
    for t in reversed(ts):
        v = t.get("state", {}).get(поле)
        if v not in (None, "", [], {}):
            return v
    return None


def на(ts, поле, сек):
    лучш = None
    for t in ts:
        gt = t.get("gt") or t.get("state", {}).get("gametime")
        if gt is None or gt > сек:
            continue
        v = t.get("state", {}).get(поле)
        if v not in (None, ""):
            лучш = v
    return лучш


def армия(ts, сек=None):
    s = 0
    for поле in АРМИЯ:
        v = на(ts, поле, сек) if сек else посл(ts, поле)
        v = чис(v)
        if v:
            s += v
    return int(s)


def впервые(ts, поле, порог):
    for t in ts:
        v = чис(t.get("state", {}).get(поле))
        gt = t.get("gt") or t.get("state", {}).get("gametime")
        if v is None or gt is None:
            continue
        if v >= порог:
            return gt
    return None


def ммсс(s):
    return "—" if s is None else "%d:%02d" % (int(s) // 60, int(s) % 60)


def сторона(кат, слот):
    o = json.load(open(os.path.join(кат, "опыт.json"), encoding="utf-8"))
    стр = o.get("флаги" if слот == 0 else "флаги2", "")
    ч = стр.split("--strategy")
    файл = ч[1].split()[0] if len(ч) > 1 else ""
    # ЯРЛЫК СТОРОНЫ — ИЗ ИМЕНИ ФАЙЛА, а не угаданный: в зеркале имя волны
    # читается наоборот, и 3.11 это уже стоило снятого вывода. Короткое имя —
    # хвост после «ветка_», чтобы влезало в таблицу.
    кор = os.path.basename(файл).replace(".json", "")
    if кор.startswith("ветка_"):
        кор = кор[len("ветка_"):]
    return (кор or "—"), os.path.basename(файл)


def разбор(кат, слот, чужая):
    p = os.path.join(кат, "coss3_bot.jsonl" if слот == 0 else "coss3_bot_P1.jsonl")
    if not os.path.exists(p):
        return None
    ts = такты(p)
    с_сост = [t for t in ts if t.get("state")]
    финиш = [t for t in ts if "finish" in t]

    мои_п = чис(посл(ts, "my_pea_lost")) or 0
    мои_б = чис(посл(ts, "my_mil_lost")) or 0
    его_п = чис(посл(ts, "p1_pea_lost")) or 0
    его_б = чис(посл(ts, "p1_mil_lost")) or 0
    свои, чужие = мои_б, его_б   # мера как в (168)/(177): ТОЛЬКО БОЙЦЫ

    d = {
        "сторона": сторона(кат, слот)[0],
        "файл": сторона(кат, слот)[1],
        "тактов": len(ts),
        "первый_ход": (с_сост[0].get("gt") if с_сост else None),
        "финиш": (финиш[-1].get("finish") if финиш else None),
        "пеа600": чис(на(ts, "peasants", 600)),
        "еда600": чис(на(ts, "food", 600)),
        "казарма2": впервые(ts, "ba17", 2),
        "казарма3": впервые(ts, "ba17", 3),
        "офицер": впервые(ts, "my_officers", 1),
        "отряд": впервые(ts, "squads", 1),
        # академия СВОЕЙ стороны — из трассы противника
        "академия": (впервые(чужая, "p1_academi", 1) if чужая else None),
        "армия1200": армия(ts, 1200),
        "армия1800": армия(ts),
        "пеа_конец": чис(посл(ts, "peasants")),
        "враг_пеа": чис(посл(ts, "p1_peasants")),
        "враг_армия": чис(посл(ts, "p1_army")),
        "мои_пеа_уб": мои_п,
        "его_пеа_уб": его_п,
        "свои_потери": свои,
        "чужие_потери": чужие,
        "размен": (чужие / свои) if свои else None,
    }

    отход, граница, без_u, без_d = 0, 0, 0, 0
    пред = None
    for t in ts:
        s = t.get("state")
        if not s:
            continue
        away, au = чис(s.get("mil_away")), чис(s.get("mil_away_u"))
        гол = sum(чис(s.get(k)) or 0 for k in АРМИЯ)
        if s.get("mil_away_u") is None:
            без_u += 1
        if s.get("mil_dist_avg") is None:
            без_d += 1
        if away is None:
            continue
        if пред and пред[0] >= 20 and away <= пред[0] * 0.6:
            цела = гол >= пред[2] * 0.95
            u_упал = (au is not None and пред[1] is not None and au <= пред[1] * 0.6)
            if цела and not u_упал:
                граница += 1
            else:
                отход += 1
        пред = (away, au, гол)
    d.update({"откат_отход": отход, "откат_граница": граница,
              "без_away_u": без_u, "без_dist": без_d})
    return d


строки = []
for волна in ВОЛНЫ:
    for к in sorted(os.listdir(os.path.join(БАЗА, волна))):
        кат = os.path.join(БАЗА, волна, к)
        t0 = такты(os.path.join(кат, "coss3_bot.jsonl"))
        t1p = os.path.join(кат, "coss3_bot_P1.jsonl")
        t1 = такты(t1p) if os.path.exists(t1p) else []
        for слот, чужая in ((0, t1), (1, t0)):
            d = разбор(кат, слот, чужая)
            if d:
                d.update({"волна": волна, "копия": к.split("-")[0], "слот": слот})
                строки.append(d)

print("ПАРА: %s (прямая) + %s (зеркало), каталог %s" % (ВОЛНЫ[0], ВОЛНЫ[1], _дата))
print()
ш = "%-10s %-4s %-5s %-26s %7s %7s %7s %7s %7s %8s %8s %7s"
print(ш % ("волна", "коп", "слот", "сторона", "акад", "каз3", "офиц", "отряд",
           "армия", "враг_арм", "врагпеа", "размен"))
for d in строки:
    print(ш % ("прямая" if d["волна"] == ВОЛНЫ[0] else "зеркало",
               d["копия"], d["слот"], d["сторона"][:26],
               ммсс(d["академия"]), ммсс(d["казарма3"]), ммсс(d["офицер"]),
               ммсс(d["отряд"]), d["армия1800"],
               "%g" % (d["враг_армия"] or 0), "%g" % (d["враг_пеа"] or 0),
               ("%.2f" % d["размен"]) if d["размен"] else "—"))

print()
print("ГОДНОСТЬ НА 10:00 (крестьян >= 45, еда > 0), первый ход, исход")
for d in строки:
    год = "ГОДНА" if (d["пеа600"] or 0) >= 45 and (d["еда600"] or 0) > 0 else "НЕГОДНА"
    print("  %-8s коп%s слот%s %-26s пеа %-5g еда %-8g ход %-6s финиш %-10s %s"
          % ("прямая" if d["волна"] == ВОЛНЫ[0] else "зеркало",
             d["копия"], d["слот"], d["сторона"][:26], d["пеа600"] or 0,
             d["еда600"] or 0, ммсс(d["первый_ход"]), str(d["финиш"]), год))

print()
print("ПО СТОРОНАМ — шесть копий пары (главное: непересечение размахов)")
for метка in sorted({d["сторона"] for d in строки}):
    гр = [d for d in строки if d["сторона"] == метка]
    р = sorted(x["размен"] for x in гр if x["размен"])
    а = sorted(x["армия1800"] for x in гр)
    к3 = sorted(x["казарма3"] for x in гр if x["казарма3"])
    print("  %-26s копий %d" % (метка, len(гр)))
    if р:
        print("     размен        %s   медиана %.2f" %
              (" / ".join("%.2f" % x for x in р), S.median(р)))
    print("     армия 30:00   %s   медиана %.0f" %
          (" / ".join("%d" % x for x in а), S.median(а)))
    print("     казарма 3     %s   (срок 15:30; не встала у %d из %d)" %
          (" / ".join(ммсс(x) for x in к3), len(гр) - len(к3), len(гр)))

print()
print("ПО СЛОТАМ — проверка стороны карты")
for слот in (0, 1):
    гр = [d for d in строки if d["слот"] == слот]
    р = sorted(x["размен"] for x in гр if x["размен"])
    а = sorted(x["армия1800"] for x in гр)
    if р:
        print("  слот %d: размен %s  медиана %.2f | армия %s" %
              (слот, " / ".join("%.2f" % x for x in р), S.median(р),
               " / ".join("%d" % x for x in а)))

print()
print("ПОЛЯ (175): откаты mil_away и наличие полей")
for d in строки:
    print("  %-8s коп%s слот%s: отход %d, шаг через границу %d; тактов %d, "
          "без mil_away_u %d, без mil_dist_avg %d"
          % ("прямая" if d["волна"] == ВОЛНЫ[0] else "зеркало",
             d["копия"], d["слот"], d["откат_отход"], d["откат_граница"],
             d["тактов"], d["без_away_u"], d["без_dist"]))
