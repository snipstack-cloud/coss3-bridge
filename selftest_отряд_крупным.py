#!/usr/bin/env python3
"""КРУПНАЯ СИЛА У СТОЯЩЕГО ОТРЯДА (3.11, слово игрока «делай»): ключ `отряд_крупным`.

Кейс — настоящие такты bot2_aca_mirror/1, слот 1, 15:40–17:40 (`sim/кейсы/отряд_крупным_aca_mirror1_P1_1540-1740.jsonl`):
отряд в удержании без бонуса терял по 6–9 за такт при его ≥ половины отряда рядом, и `_отряд_в_поле` молчал (ключ
`отряд_отвечает` бьёт только малую группу). Без нового ключа — как было (ни одного приказа в больших тактах); с ним —
в этих тактах уходит ATTACK отрядом (наших не меньше) или RETREAT отрядом к ратуше (меньше).
    python3 selftest_отряд_крупным.py"""
import json
import os
import sys
import tempfile

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import strategy_live as SL  # noqa: E402

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
    return st


T = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/отряд_крупным_aca_mirror1_P1_1540-1740.jsonl"), encoding="utf-8")]


def прогон(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/ветка_качели2_академия2_отряд.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    приказы = []
    for t in T:
        из, речь = С._отряд_в_поле([], живое(t))
        приказы += [(t["gt"], c["cmd"]) for c in из if c.get("_отряд")]
    return приказы, dict(С.реестр.мера)


п0, м0 = прогон({})
п1, м1 = прогон({"отряд_крупным": 1})
проверить(not any(c in ("RETREAT",) for _, c in п0), f"(а) без ключа отхода отрядом нет: {п0[:4]}")
проверить(len(п1) > len(п0), f"(б) с ключом приказов отряду больше: {len(п1)} против {len(п0)}")
проверить(м1.get("отряд в поле: крупным — отход", 0) + м1.get("отряд в поле: крупным — удар", 0) >= 1,
          f"(в) счётчики крупной силы растут: отход {м1.get('отряд в поле: крупным — отход', 0)}, удар {м1.get('отряд в поле: крупным — удар', 0)}")
проверить(м0.get("отряд в поле: крупным — отход", 0) == 0 and м0.get("отряд в поле: крупным — удар", 0) == 0,
          "(г) без ключа счётчики крупной силы нулевые")
print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
