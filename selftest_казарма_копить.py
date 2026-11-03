#!/usr/bin/env python3
"""КОПИТЬ НА КАЗАРМУ (3.11, слово игрока «делай»): ключ `казарма_копить` (§170я (г)).

Зеркало bot2_aca_mirror/1, сторона ранней академии (`results/2026-11-03/bot2_aca_mirror_1_P1/coss3_bot.jsonl`): с 13:58 по
19:50 золото уходило на ступени пики (bar.*) и aca.3, держалось на 8–10 тыс. при цене третьей казармы 12 500, и казарма
встала в 22:12. Прогон трассы через ответ() файлом ранней академии: без ключа UPGRADE bar.* при двух казармах уходят;
с `казарма_копить` 0,5 — при золоте ≥ 6 250 и двух казармах не уходит ни одна прокачка, до этого (меньше золота) идут.
    python3 selftest_казарма_копить.py"""
import copy
import json
import os
import sys
import tempfile

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import strategy_live as SL  # noqa: E402
import анализ_врага as АВ  # noqa: E402
import агент_армия as А  # noqa: E402

ошибок = 0


def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл


def живое(t):
    st = {k: (";".join(",".join(str(x) for x in r) for r in v)
              if isinstance(v, list) and v and all(isinstance(r, list) for r in v) else v)
          for k, v in t["state"].items()}
    st["gametime"] = t["gt"]
    # живьём доступные ступени приходят полем upg_avail; в трассе их пишет снимок под именем upg_shown
    st.setdefault("upg_avail", st.get("upg_shown"))
    return st


T, _ = А.последняя_партия(os.path.join(К, "results/2026-11-03/bot2_aca_mirror_1_P1/coss3_bot.jsonl"))


def прогон(доп):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    д = json.load(open(os.path.join(К, "sim/поиск/ветка_качели2_академия2_отряд.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    при_копке, до_копки = [], []
    for t in T:
        st = живое(t)
        if t["gt"] > 1320:
            break
        о = С.ответ(copy.deepcopy(st))
        ups = [c.get("role") or c.get("upg") for c in о["commands"] if c.get("cmd") == "UPGRADE"]
        if int(st.get("ba17") or 0) == 2 and t["gt"] >= 600:
            (при_копке if float(st.get("gold") or 0) >= 6250 else до_копки).extend(ups)
    return при_копке, до_копки, С


п0, д0, _ = прогон({})
проверить(any(str(u).startswith("bar.") for u in п0), f"(а) без ключа при двух казармах и золоте ≥ 6250 прокачки пики идут: {п0[:6]}")
п1, д1, С1 = прогон({"казарма_копить": 0.5})
проверить(not п1, f"(б) с `казарма_копить` 0,5 при золоте ≥ 6250 и двух казармах — ни одной прокачки: {п1[:6]}")
проверить(д1 == д0, f"(в) пока золота меньше половины цены — прокачки те же, что без ключа: {д1[:6]} / {д0[:6]}")
print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
