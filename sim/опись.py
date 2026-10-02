#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ОПИСЬ ПРОКАЧЕК: всё, что игра даёт купить, против того, что знает симулятор (2.10, §46).

Зачем (игрок 2.10: «я всё подсказываю — почему модель сама не изучает?»). Поиск и сеть
выбирают только из рычагов, которые им дали; рычаги добавлялись по подсказкам игрока —
мельница, академия, отряды. Опись снимает эту зависимость: каждая прокачка из кода игры
с ценой и эффектом, где она показывалась боту вживую и учтена ли она в симуляторе.

Источники:
* код — `data/scripts/lib/country.script`, прямые вызовы `_country_AddUpgrade*`
  (цена — аргументы 11-16: еда, дерево, камень, золото, железо, уголь; поправка
  Нидерландов `_net : _country_ModifyUpgrade` — поверх). Пакеты казарм и конюшни
  (`SetUpgStructFoodGold` + `AddUpgradePack`) разбираются по записям: имя
  `bar.<юнит>.<линия>.<ступень>`, линия 1 — атака, 2 — защита;
* записи — поля `upg_shown`/`upg_aca` (что игра показывала с ценой) и `upg_done` (что взято)
  во всех трассах `~/coss3-res` и `~/coss3-res-игрок`.

    python3 sim/опись.py            # → sim/ОПИСЬ.md и sim/опись.json
"""
import collections
import glob
import json
import os
import re
import sys

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
ИГРА = os.path.abspath(os.path.join(os.path.expanduser("~"), "Downloads",
                                    "Cossacks 3. Digital Deluxe Edition v2.2.3.92.6008 (23969) [GOG]"))
КОД = os.path.join(ИГРА, "data", "scripts", "lib", "country.script")
РЕСУРСЫ = ("food", "wood", "stone", "gold", "iron", "coal")

# что значит тип эффекта по-русски, и есть ли у симулятора такая механика вообще
ТИПЫ = {
    "effectfood": ("сбор еды, +%", True), "effectfoodperc": ("сбор еды, +%", True),
    "effectwoodperc": ("сбор дерева, +%", True), "effectstoneperc": ("сбор камня, +%", True),
    "fieldlifeperc": ("срок жизни поля, +%", False), "fishingperc": ("рыбалка, +%", False),
    "damage": ("урон, +", True), "damageperc": ("урон, +%", True), "protection": ("защита, +", True),
    "shield": ("щит, +", False), "attpauseperc": ("перезарядка, %", True),
    "single_attpauseperc": ("перезарядка юнита, %", False), "attrangeperc": ("дальность, +%", False),
    "attdispertionperc": ("разброс, %", False), "buildtimeperc": ("время стройки/найма, %", False),
    "priceperc": ("цена, %", False), "lifeperc": ("жизнь, +%", False), "speedperc": ("скорость, +%", False),
    "healing": ("лечение", False), "enableunit": ("открывает юнита", False),
    "single_inside_mine": ("крестьян в шахте", False), "single_inside": ("вместимость", False),
    "single_buildgate": ("ворота", False), "geology": ("геология", False), "balloon": ("шар (разведка)", False),
    "none": ("—", False),
}


def _аргументы(текст):
    """Аргументы вызова верхнего уровня (запятые вне скобок и кавычек)."""
    из, глуб, кус, кав = [], 0, "", False
    for ch in текст:
        if ch == "'" :
            кав = not кав
        if not кав and ch in "({":
            глуб += 1
        if not кав and ch in ")}":
            глуб -= 1
        if ch == "," and глуб == 0 and not кав:
            из.append(кус.strip()); кус = ""
        else:
            кус += ch
    из.append(кус.strip())
    return из


def _число(s):
    s = re.sub(r"\{[^}]*\}", "", s).strip()
    try:
        return float(s)
    except ValueError:
        return None


def из_кода():
    L = open(КОД, encoding="latin-1").read().splitlines()
    место, из = None, {}
    i = 0
    while i < len(L):
        l = L[i]
        m = re.search(r"upgplace\s*(?::=|: String =)\s*(.+);", l)
        if m:
            выр = m.group(1)
            лит = re.findall(r"'([^']*)'", выр)
            место = ("".join(лит) + ("<member>" if "member" in выр else "")) if лит else выр
        if ("_country_AddUpgrade(" in l or "_country_AddUpgradeWithAccessControl(" in l) and место:
            текст = l
            j = i
            while ");" not in текст and j + 1 < len(L):
                j += 1; текст += L[j]
            внутри = текст[текст.index("(") + 1: текст.rindex(")")]
            а = _аргументы(внутри)
            имя_выр = а[1]
            суф = "".join(re.findall(r"'([^']*)'", имя_выр))
            if "member" in имя_выр and "<member>" not in место:
                суф = суф.replace("..", ".<member>.", 1) if суф.startswith("..") else ".<member>" + суф
            имя = место + суф
            тип = re.sub(r"^gc_upg_type_", "", а[4])
            цена = {r: _число(а[11 + k]) or 0 for k, r in enumerate(РЕСУРСЫ)} if len(а) > 16 else {}
            req = " ".join(а[17:]).lower()
            век18 = "century18" in req or any("req0 := century18" in L[k] for k in range(max(0, i - 8), i))
            # поправка Нидерландов в следующих строках до нового вызова
            k = j + 1
            while k < len(L) and "_country_AddUpgrade" not in L[k] and k < j + 25:
                mm = re.search(r"_net\s*:\s*_country_ModifyUpgrade\((.*)\)", L[k])
                if mm:
                    ма = _аргументы(mm.group(1))[2:]
                    for q, r in enumerate(РЕСУРСЫ):
                        if q + 1 < len(ма) and ма[q + 1] != "default" and _число(ма[q + 1]) is not None:
                            цена[r] = _число(ма[q + 1])
                k += 1
            # КОМУ: строки `_country_AddUpgradeSArrParam2MemberIfExists(..., garr_X[k])` или 'юнит'
            # сразу после вызова; без них — всем (экономика) или по оружию
            кому = []
            for q in range(j + 1, min(len(L), j + 6)):
                if "_country_AddUpgrade(" in L[q] or "_country_AddUpgradeWithAccessControl(" in L[q]:
                    break
                кому += re.findall(r"MemberIfExists\(country, ind-1, (?:garr_(\w+)\[k\]|'(\w+)')\)", L[q])
            кому = [a or b for a, b in кому]
            оружие = next((re.sub("gc_obj_weapon_kind_", "", x) for x in а[17:20] if "weapon_kind" in x), "")
            из.setdefault(имя, dict(имя=имя, тип=тип, значение=_число(а[5]), оружие=оружие,
                                    цена={r: v for r, v in цена.items() if v}, век18=век18, кому=", ".join(кому),
                                    строка=i + 1))
            i = j
        i += 1
    return из


def из_записей():
    показ, взято, цены = collections.Counter(), collections.Counter(), {}
    трассы = glob.glob(os.path.expanduser("~/coss3-res/2026-*/*/*/coss3_bot.jsonl")) + \
        glob.glob(os.path.expanduser("~/coss3-res-игрок/*/*/coss3_bot.jsonl"))
    for f in трассы:
        видел, брал = set(), set()
        for l in open(f, errors="replace"):
            if "upg_" not in l:
                continue
            try:
                st = json.loads(l).get("state") or {}
            except ValueError:
                continue
            for поле in ("upg_shown", "upg_aca"):
                for кус in str(st.get(поле) or "").split(","):
                    if "=" in кус:
                        имя, ц = кус.split("=", 1)
                        имя = имя.strip(); видел.add(имя)
                        цены.setdefault(имя, {dict(f="food", w="wood", s="stone", g="gold", i="iron", c="coal")[m[0]]: int(m[1])
                                              for m in re.findall(r"([fwsgic])(\d+)", ц)})
            for u in str(st.get("upg_done") or "").split(","):
                if u.strip():
                    брал.add(u.strip())
        показ.update(видел); взято.update(брал)
    return показ, взято, цены, len(трассы)


def в_симуляторе():
    import sim as SIM, core
    учтено = set(SIM.ЭФФЕКТЫ) | {u for т in core.ЭФФЕКТ_РЕСУРСА.values() for u in т} | set(SIM.АКАДЕМИЯ_УРОН) | set(SIM.АКАДЕМИЯ_ПАУЗА)
    import поиск_стратегии as ПС
    поиск = {f"bar.pikeman.{a}.{k}" for a in (1, 2) for k in range(1, 7)} | {"mil.1", "aca.1", "aca.2", "aca.3"}
    return учтено, поиск


def main():
    код = из_кода()
    показ, взято, цены, n_трасс = из_записей()
    учтено, поиск = в_симуляторе()
    имена = set(код) | set(показ) | set(взято)
    строки = []
    for имя in имена:
        к = код.get(имя) or {}
        if not к and имя.startswith(("bar.", "ba2.", "sta.")):
            ч = имя.split(".")
            тип = {"1": "damage", "2": "protection"}.get(ч[2] if len(ч) > 2 else "", "?")
            к = dict(тип=тип, значение=None, цена={}, век18=False, строка=None, оружие="")
        тип = к.get("тип", "?")
        смысл, механика = ТИПЫ.get(тип, (тип, False))
        if имя in учтено:
            сим = "учтён"
        elif механика:
            сим = "механика есть, эффект НЕ внесён"
        else:
            сим = "механики нет"
        строки.append(dict(имя=имя, тип=тип, смысл=смысл, значение=к.get("значение"), оружие=к.get("оружие", ""),
                           цена=цены.get(имя) or к.get("цена") or {}, цена_из="запись" if имя in цены else ("код" if к.get("цена") else "—"),
                           век18=к.get("век18", False), строка=к.get("строка"), кому=к.get("кому", "") or (имя.split(".")[1] if имя.startswith(("bar.", "sta.", "ba2.")) else ""), показ=показ.get(имя, 0),
                           взято=взято.get(имя, 0), симулятор=сим, поиск=имя in поиск))
    строки.sort(key=lambda r: (r["симулятор"] != "механика есть, эффект НЕ внесён", r["симулятор"] == "механики нет",
                               -r["показ"], r["имя"]))
    json.dump(строки, open(os.path.join(К, "опись.json"), "w"), ensure_ascii=False, indent=1)

    def цена(c):
        return ", ".join(f"{dict(food='еда', wood='дерево', stone='камень', gold='золото', iron='железо', coal='уголь')[r]} {int(v)}"
                         for r, v in c.items() if v) or "—"
    сч = collections.Counter(r["симулятор"] for r in строки)
    сч_пок = collections.Counter(r["симулятор"] for r in строки if r["показ"])
    md = ["# Опись прокачек: игра против симулятора", "",
          f"Сделано `sim/опись.py` (2.10, §46). Код — `country.script`, {len(код)} прямых объявлений; "
          f"записи — {n_трасс} трасс (что игра показывала боту с ценой и что взято).", "",
          "| в симуляторе | всего | из них игра показывала боту |", "|---|---|---|"]
    for k in ("учтён", "механика есть, эффект НЕ внесён", "механики нет"):
        md.append(f"| {k} | {сч[k]} | {сч_пок[k]} |")
    md += ["", "«Поиск» — может ли поиск стратегии заказать прокачку сам. «Показ / взято» — в скольких",
           "трассах игра показывала её с ценой и в скольких она взята.", ""]
    for заголовок, отбор in (("Механика есть, эффект не внесён — дописать числа", lambda r: r["симулятор"].startswith("механика есть")),
                             ("Учтено в симуляторе", lambda r: r["симулятор"] == "учтён"),
                             ("Механики в симуляторе нет — вопросы и работа", lambda r: r["симулятор"] == "механики нет")):
        часть = [r for r in строки if отбор(r)]
        md += [f"## {заголовок} ({len(часть)})", "", "| прокачка | эффект | кому | цена | показ / взято | поиск | код |", "|---|---|---|---|---|---|---|"]
        for r in часть:
            эф = r["смысл"] + (f" {r['значение']:g}" if isinstance(r["значение"], (int, float)) else "") + (f" ({r['оружие']})" if r["оружие"] else "") + (" · 18 век" if r["век18"] else "")
            md.append(f"| `{r['имя']}` | {эф} | {r['кому'] or 'всем'} | {цена(r['цена'])} ({r['цена_из']}) | {r['показ']} / {r['взято']} | {'да' if r['поиск'] else '—'} | {r['строка'] or '—'} |")
        md.append("")
    open(os.path.join(К, "ОПИСЬ.md"), "w").write("\n".join(md))
    print(f"прокачек {len(строки)}: " + ", ".join(f"{k} {v}" for k, v in сч.items()))
    print("из показанных боту: " + ", ".join(f"{k} {v}" for k, v in сч_пок.items()))


if __name__ == "__main__":
    main()
