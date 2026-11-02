#!/usr/bin/env python3
"""ЦЕНЫ НАЙМА ПО НАЦИЯМ для ядра двойника (2.11, слово игрока «починить двойник под нации»).

Ядро (`core.py`) знало только Нидерланды: `параметры.json` склеил `pikemanpol` с `pikeman` и дал польской пике 20 железа
(в коде игры у неё 0). В двойнике бот Польшей упирался в железо на 17 пиках к 7:00 на любой записи. Таблица строится из
скриптов игры через `нации.py` (`роспись` — какой юнит нация берёт на роль, `юниты_из_скрипта` — цена и время найма) и
кладётся в `цены_наций.json`, чтобы двойник не читал скрипты на каждой партии.

    python3 sim/цены_наций.py        # пересобрать цены_наций.json (нужна папка игры, COSS3_GAME)
"""
import json
import os
import sys

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
РОЛИ = {"pikeman": "gc_ai_unit_infantry17", "musketeer": "gc_ai_unit_musk17", "dragoon": "gc_ai_unit_dragoon17"}


ЗДАНИЯ_SID = ("aca", "cen", "bla", "hou", "sta", "bar")


def здания_наций(игра=None) -> dict:
    """{нация: {sid: {ресурс: базовая цена}}} — ветки `case i of` блока `csid+'<sid>' : begin` в `lib/unit.script`
    (`SetObjBuildingExtProperties`, последние шесть чисел — еда, дерево, камень, золото, железо, уголь). Нации без своей
    ветки берут базовый вызов блока — их в таблицу не кладём (ядро возьмёт `параметры.json`)."""
    import re
    import нации as Н
    путь = os.path.join(игра or Н.ИГРА, "data", "scripts", "lib", "unit.script")
    т = open(путь, encoding="latin-1").read()
    из = {}
    for sid in ЗДАНИЯ_SID:
        k = т.find(f"csid+'{sid}' : begin")
        if k < 0:
            continue
        блок = т[k:т.find("csid+'", k + 10)]
        for m in re.finditer(r"\n\s*([a-z]{3})\s*:\s*SetObjBuildingExtProperties\(([^;]*)\);", блок):
            ар = [x.strip() for x in m.group(2).split(",")]
            if len(ар) < 14:
                continue
            цена = {}
            for r, x in zip(("food", "wood", "stone", "gold", "iron", "coal"), ар[8:14]):
                x = re.sub(r"\{[^}]*\}", "", x)
                try:
                    v = eval(x, {"__builtins__": {}}) if re.fullmatch(r"[0-9*+ ]+", x) else None
                except Exception:
                    v = None
                if v is not None:
                    цена[r] = int(v)
            if len(цена) == 6:
                из.setdefault(m.group(1), {})[sid] = цена
    return из


def собрать():
    import нации as Н
    юн, рос = Н.юниты_из_скрипта(), Н.роспись()
    из = {}
    for код in Н.НАЦИИ.values():
        роли = {роль: sid for sid, роль in (рос.get(код) or [])}
        н = {}
        for ядро, роль in РОЛИ.items():
            sid = роли.get(роль)
            if sid and sid in юн:
                н[ядро] = {"юнит": sid, "цена": {k: v for k, v in юн[sid]["цена"].items() if v}, "найм_с": юн[sid].get("найм_с")}
        крест = "pea" + код
        if крест in юн:
            н["peaeng"] = {"юнит": крест, "цена": {k: v for k, v in юн[крест]["цена"].items() if v}, "найм_с": юн[крест].get("найм_с")}
        из[код] = н
    return {"источник": "нации.py: lib/unit.script (цена, время найма; здания — ветки case i of), lib/country.script (роспись ролей)",
            "нации": из, "здания": здания_наций()}


if __name__ == "__main__":
    т = собрать()
    json.dump(т, open(os.path.join(К, "цены_наций.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print({к: {я: (в["юнит"], в["цена"], в["найм_с"]) for я, в in н.items()} for к, н in т["нации"].items() if к in ("net", "pol")})
    print({к: т["здания"].get(к) for к in ("net", "pol")})
