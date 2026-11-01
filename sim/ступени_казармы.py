#!/usr/bin/env python3
"""СТУПЕНИ КАЗАРМЫ ВСЕХ НАЦИЙ ИЗ КОДА ИГРЫ → `sim/ступени.json` (1.11, слово игрока: «прокачки пик под его прокачки»).

Зачем. Оценщик `прокачки.py` знал прибавки двух линеек — `pikeman` и `musketeernet` (`combat_math.ПРИБАВКИ_СТУПЕНЕЙ`,
числа Нидерландов). У семи наций пика своя (`pikemanrus/pol/tur/sco/por/swi`, у Испании `pikemanspa`), мушкетёр своего имени
у всех, кроме общего `musketeer`. Их ступени оценщик не видел вовсе: бот Польшей за четыре партии не купил ни одной прокачки
пик, а игрок к 9:22 довёл свою до atk 13 / защита 4 против нашей 8 / 0 (`igrok_01_11_Польша_пики`). И прибавки у наций
РАЗНЫЕ: атака пики Нидерландов +1,+2,+2,+1,+2, Польши +1,+1,+1,+2,+2 (`lib/country.script:959, 966`).

Что читается (`lib/country.script`, процедура заполнения нации, раздел `// barracks` и до `_country_ClearOfficerFormations`):
  * `SetUpgStructFoodGold[Iron[Coal]](upgstruct, place, member, v0, f0, g0, [i0, [c0,]] b0, ..., v5, f5, g5 ...)` — шесть
    ступеней пакета; вид (1 атака / 2 защита) — по следующему `AddUpgradePack(..., ctypeDamage* | ctypeProtection*)`;
  * `_country_AddUpgradeWithAccessControl(country, upgplace+'.'+member+'.K.'+IntToStr(L), _, _, _, VALUE, ..., FOOD, wood,
    stone, GOLD, IRON, ...)` — добавочные ступени (шестая пик и т. п.).
Имя линейки (`member`) — по последнему `case cid of … member := …` (с веткой `else`) или прямому `member := '…'`; нация — по
префиксу строки `_pol :` или по охватывающему `_pol : begin` / `if (cid=_pol)`. Ключ записи — нация, линейка, вид, ступень и
ЦЕНА (еда, золото, железо): живой ценник `upg_avail` совпадает со скриптом до единицы (проверено на Польше и Нидерландах 1.11),
поэтому по цене ступень находится и без знания своей нации.

    python3 sim/ступени_казармы.py [<игра>/data/scripts/lib/country.script]
"""
import json
import os
import re
import sys

К = os.path.dirname(os.path.abspath(__file__))
ИГРА = "/Users/gs/Downloads/Cossacks 3. Digital Deluxe Edition v2.2.3.92.6008 (23969) [GOG]"
ВЫХОД = os.path.join(К, "ступени.json")


def аргументы(s):
    """Аргументы вызова верхнего уровня (скобки внутри — `IntToStr(6)` — не режут)."""
    s = s[s.index("(") + 1:]
    out, глуб, тек = [], 0, ""
    for c in s:
        if c == "(":
            глуб += 1
        elif c == ")":
            if глуб == 0:
                out.append(тек.strip())
                return out
            глуб -= 1
        if c == "," and глуб == 0:
            out.append(тек.strip())
            тек = ""
        else:
            тек += c
    out.append(тек.strip())
    return out


def число(x):
    try:
        return int(x)
    except ValueError:
        return None


def разобрать(путь):
    L = open(путь, encoding="latin-1").read().split("\n")
    начало = next(i for i, l in enumerate(L) if l.strip() == "// barracks")
    конец = next(i for i, l in enumerate(L) if "procedure _country_ClearOfficerFormations" in l)
    записи = []
    члены = {}          # нация → линейка ('*' — ветка else)
    набор = None        # строящийся `case cid of … member := …`
    после_else = False
    нация_блока = None  # охватывающий `_xxx : begin` или `if (cid=_xxx)`
    for i in range(начало, конец):
        s = L[i].split("//")[0].strip()
        if not s or s.startswith("{"):
            continue
        if re.match(r"case\s+cid\s+of", s):
            набор, после_else = {}, False
            continue
        m = re.match(r"(_\w+)\s*:\s*member\s*:=\s*'(\w*)'", s)
        if m and набор is not None:
            набор[m.group(1)] = m.group(2)
            continue
        if s == "else":
            после_else = True
            continue
        m = re.match(r"member\s*:=\s*'(\w*)'", s)
        if m:
            if набор is not None and после_else:
                набор["*"] = m.group(1)
                члены, набор = набор, None
            else:
                члены = {"*": m.group(1)}
            после_else = False
            continue
        if набор is not None and s.startswith("end") and набор:
            члены, набор = набор, None      # case без else
        после_else = False if not s.startswith("begin") else после_else
        m = re.match(r"if\s*\(cid\s*=\s*(_\w+)\)", s)
        if m:
            нация_блока = m.group(1)
        m = re.match(r"(_\w+)\s*:\s*begin", s)
        if m:
            нация_блока = m.group(1)
        if s == "begin" and после_else:
            нация_блока, после_else = "*", False
        m = re.match(r"(?:(_\w+)\s*:\s*)?(SetUpgStructFoodGold(?:IronCoal|Iron)?)\s*\(", s)
        if m:
            нация = m.group(1) or нация_блока or "*"
            а = аргументы(s)
            шаг = {"SetUpgStructFoodGold": 4, "SetUpgStructFoodGoldIron": 5, "SetUpgStructFoodGoldIronCoal": 6}[m.group(2)]
            вид = None
            for j in range(i + 1, min(конец, i + 40)):
                t = L[j]
                if "AddUpgradePack(" in t:
                    вид = 1 if "ctypeDamage" in t else 2
                    break
            член = члены.get(нация, члены.get("*"))
            if вид is None or not член:
                continue
            for ур in range(6):
                база = 3 + ур * шаг
                if база + 2 >= len(а):
                    break
                v, f, g = число(а[база]), число(а[база + 1]), число(а[база + 2])
                ir = число(а[база + 3]) if шаг >= 5 else 0
                if v:
                    записи.append({"нация": нация, "линейка": член, "вид": вид, "ступень": ур + 1, "прибавка": v,
                                   "еда": f, "золото": g, "железо": ir or 0, "строка": i + 1})
            continue
        if "_country_AddUpgradeWithAccessControl(" in s and "member+'." in s:
            m = re.search(r"member\+'\.(\d)\.'\+IntToStr\((\d)\)", s)
            if not m:
                continue
            а = аргументы(s)
            член = члены.get(нация_блока, члены.get("*")) if нация_блока else члены.get("*")
            if not член:
                continue
            записи.append({"нация": нация_блока or "*", "линейка": член, "вид": int(m.group(1)), "ступень": int(m.group(2)),
                           "прибавка": число(а[5]), "еда": число(а[11]), "золото": число(а[14]), "железо": число(а[15]) or 0,
                           "строка": i + 1})
    return записи


def main():
    путь = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ИГРА, "data", "scripts", "lib", "country.script")
    з = разобрать(путь)
    json.dump({"источник": "lib/country.script", "записи": з}, open(ВЫХОД, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    линейки = sorted({(r["линейка"]) for r in з})
    print(f"записей {len(з)}, линеек {len(линейки)} → {ВЫХОД}")
    for нация, лин in (("_pol", "pikemanpol"), ("_net", "pikeman"), ("_pol", "musketeerpol"), ("_net", "musketeernet")):
        for вид in (1, 2):
            r = sorted((x for x in з if x["линейка"] == лин and x["вид"] == вид and x["нация"] in (нация, "*")),
                       key=lambda x: (x["ступень"], x["нация"] == "*"))
            по = {}
            for x in r:
                по.setdefault(x["ступень"], x)
            print(f"  {нация} {лин}.{вид}: " + ", ".join(f"{k}:+{x['прибавка']} f{x['еда']}g{x['золото']}" for k, x in sorted(по.items())))


if __name__ == "__main__":
    main()
