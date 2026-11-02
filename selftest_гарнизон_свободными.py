#!/usr/bin/env python3
"""ГАРНИЗОН СВОБОДНЫМИ (2.11, разбор капли): ключ `гарнизон_свободными`.

storm_pol (1.11, мост 0e6a6c6), 17:02: его лагерь 37 пик в (8,8), наших дома 197 — в отряде строем 189, свободных 8.
Удар по лагерю с гарнизоном 30 шёл ЧИСЛОМ 167, прогноз считал отряд в числе уходящих, а счётный приказ блок исполняет
одними свободными: пять минут каждые 5 с уходило по 2–14, отряд стоял, его лагерь 37 → 74. Кейс — настоящие состояния
трассы 15:00–17:10 (`sim/кейсы/капля_storm_pol_1500-1710.jsonl`), анализ врага копит историю по ним же.
    python3 selftest_гарнизон_свободными.py"""
import json
import os
import sys

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import strategy_live as SL  # noqa: E402
import анализ_врага as АВ  # noqa: E402

ошибок = 0


def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл


КЕЙС = [json.loads(s) for s in open(os.path.join(К, "sim/кейсы/капля_storm_pol_1500-1710.jsonl"), encoding="utf-8")]
ФАЙЛ = os.path.join(К, "sim/поиск/штурм_всем_основа.json")


def живое(st):
    """Трасса хранит клетки и здания списками, живое состояние моста — строками «x,y,…;…» (их и ждёт анализ врага)."""
    из = {}
    for k, v in st.items():
        if isinstance(v, list) and v and all(isinstance(r, list) for r in v):
            из[k] = ";".join(",".join(str(x) for x in r) for r in v)
        else:
            из[k] = v
    return из


def удар(доп):
    """Прогнать анализ по кейсу и вернуть (приказ удара по лагерю в 17:02 или None, запись why, стратегия)."""
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    стр = SL.ЖиваяСтратегия(ФАЙЛ)
    стр.п = dict(стр.п, **доп)
    for t in КЕЙС:
        st = dict(живое(t["state"]), gametime=t["gt"])
        АВ.текущий(st)
        if t["gt"] >= 1022:
            из, з = стр._тактика([], st)
            уд = [c for c in из if c.get("cmd") == "ATTACK" and c.get("target") == "cell"]
            return (уд[0] if уд else None), з, стр, st
    return None, "", стр, None


п0, з0, с0, st = удар({})
проверить(st is not None and int(st.get("my_insquad") or 0) >= 180 and int(st.get("my_freewar") or 0) <= 10,
          f"(а) кейс тот самый: в отряде {st.get('my_insquad')}, свободных {st.get('my_freewar')}")
проверить(п0 is not None and "УДАР ПО ЛАГЕРЮ" in з0,
          f"(б) без ключа удар по лагерю отдаётся: {з0[:90]}")
проверить(п0 is not None and not п0.get("all") and int(п0.get("count") or 0) > int(st.get("my_freewar") or 0),
          f"(в) без ключа — КАПЛЯ: число {п0.get('count') if п0 else None} без `all` при {st.get('my_freewar')} свободных, "
          "отряд приказом не берётся")

п1, з1, с1, _ = удар({"гарнизон_свободными": 1})
проверить(п1 is not None and п1.get("all") == 1,
          f"(г) с ключом приказ несёт `all` — отряд уходит целиком: {п1}")
проверить(п1 is not None and int(п1.get("count") or 0) <= max(1, int(st.get("my_freewar") or 0)),
          f"(д) числом — только вне отряда сверх гарнизона: count {п1.get('count') if п1 else None}")
проверить("гарнизон свободными" in з1 and с1.реестр.мера["лагерь: гарнизон свободными"] == 1,
          "(е) сказано вслух и посчитано мерой")
проверить(с0.реестр.мера["лагерь: гарнизон свободными"] == 0 and "гарнизон свободными" not in з0,
          "(ж) без ключа ни меры, ни строки — прежние плечи не поедут")
проверить(п1 is not None and п1.get("_гарнизон") == 30,
          "(з) гарнизон помечен: правило «оборона всем» его не превращает в весь дом заново")

print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
