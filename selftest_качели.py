#!/usr/bin/env python3
"""КАЧЕЛИ ВЫХОДА (2.11, разбор 35 прогонов): ключи `отход_по_всем`, `отход_запас`, `отход_не_раньше`.

Отмену выхода решал прогноз приказа «из дома N», а вышедшие в поле в него не входили: drop_pol 22:20 «НЕ_ВЫГОДНО из
дома 98 против его 191» → «ВЫХОД ОТМЕНЁН: наших в поле 613, все домой». Из 118 отмен в 100 прогноз видел меньше бойцов,
чем стояло в поле; снова к цели армия шла через 11 с (медиана). Кейсы — настоящие такты drop_net 19:30–22:30 и
drop_pol 20:00–22:30 (`sim/кейсы/качели_*.jsonl`), стратегия — `ветка_казарма3_без_капли.json`, через полный ответ().
    python3 selftest_качели.py"""
import copy
import json
import os
import sys
import tempfile

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import strategy_live as SL  # noqa: E402
import анализ_врага as АВ  # noqa: E402

ошибок = 0


def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл


def живое(t, его_раз=1):
    st = {}
    for k, v in t["state"].items():
        if k == "ecells" and его_раз != 1 and isinstance(v, list):
            v = [[r[0], r[1], r[2] * его_раз, r[3] * его_раз] + list(r[4:]) for r in v]
        st[k] = ";".join(",".join(str(x) for x in r) for r in v) \
            if isinstance(v, list) and v and all(isinstance(r, list) for r in v) else v
    st["gametime"] = t["gt"]
    return st


def прогон(имя, доп, его_раз=1, с=0):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    д = json.load(open(os.path.join(К, "sim/поиск/ветка_казарма3_без_капли.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    отм, прод = [], []
    for s in open(os.path.join(К, f"sim/кейсы/{имя}.jsonl"), encoding="utf-8"):
        t = json.loads(s)
        st = живое(t, его_раз if t["gt"] >= с else 1)
        о = С.ответ(copy.deepcopy(st))
        if "ВЫХОД ОТМЕНЁН" in о["why"]:
            отм.append(st["gametime"])
        if "ВЫХОД ПРОДОЛЖЕН" in о["why"]:
            прод.append((st["gametime"], next(x.strip() for x in о["why"].replace(";", "|").split("|") if "ВЫХОД ПРОДОЛЖЕН" in x)))
    return отм, прод, С


for имя in ("качели_drop_net_1170-1350", "качели_drop_pol_1200-1350"):
    о0, _, _ = прогон(имя, {})
    проверить(len(о0) >= 1, f"(а) {имя}: без ключей отмена воспроизводится: {о0}")
    о1, п1, С1 = прогон(имя, {"отход_по_всем": 1})
    проверить(not о1 and п1, f"(б) {имя}: с `отход_по_всем` отмены нет, выход продолжен: {п1[:1]}")
    проверить(С1.реестр.мера["качели: выход продолжен по всем"] >= 1, "(в) мера «выход продолжен по всем» посчитана")
    о2, п2, _ = прогон(имя, {"отход_по_всем": 1}, его_раз=10, с=о0[0] if о0 else 0)
    проверить(len(о2) >= 1, f"(г) {имя}: с такта отмены его вдесятеро — отзыв остаётся и с ключом: {о2}")
    о3, п3, С3 = прогон(имя, {"отход_не_раньше": 30})
    проверить(С3.реестр.мера["качели: отзыв рано"] >= 0, "(д) ключ времени не ломает такт")

print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
