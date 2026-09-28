#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ВОРОТА БОЯ ПО МЕСТАМ: замкнутый цикл против событий гибели (29.09).

Жизнь — события гибели бойцов (`гибель` в снимках, с 27.09), место смерти по
клетке жертвы: у него (≤ 3 кл от центра его «e»), у нас (≤ 5 от нашего центра),
в поле. Симулятор — `журнал_боя` замкнутого цикла тех же партий (команды записи
против записанного врага), место по клетке боя тем же правилом.

Мера, названная до счёта (§21): размен по местам в пределах 1,4 раза от жизни
и суммы потерь сторон по местам в пределах 1,5 раза — при НЕ худших суммах по
архиву, чем до правки.

    python3 sim/ворота_мест.py ~/coss3-res/2026-09-28 ~/coss3-res/2026-09-27 [--seeds=3] [--клеткой | --моделью]
"""
import json, math, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from бой_по_событиям import центр, место, полоса, ПОЛОСЫ  # noqa: E402

МЕСТА = ("у него", "в поле", "у нас")
# полосы: True — наших в клетке против его в ОКНЕ 3×3 у обеих сторон (так закон видит бой
# в симуляторе); False — по его числу в самой клетке (так мерит `бой_по_событиям`)
ОКНОМ = True
МОДЕЛЬЮ = False


def жизнь(каталог):
    из = defaultdict(lambda: [0, 0])
    виден = set()
    for s in open(os.path.join(каталог, "coss3_snap.jsonl"), encoding="utf-8"):
        if not s.strip().startswith("{"):
            continue
        x = json.loads(s)
        if "kills_n" not in x:
            continue
        мой, его = центр(x.get("brow"), "bH"), центр(x.get("brow"), "e")
        for e in x.get("гибель") or []:
            if len(e) != 11 or e[0] in виден or e[3] not in "ISCG":
                continue
            виден.add(e[0])
            из[место(e[4], e[5], мой, его)][0 if e[2] == 0 else 1] += 1
    return из, len(виден)


def жизнь_по_полосам(каталог):
    """Как `бой_по_событиям`: только полные окна, полоса по точному `cells`."""
    import бой_по_событиям as Б
    итог = defaultdict(lambda: [0, 0])
    Б.запись(os.path.join(каталог, "coss3_snap.jsonl"), итог, defaultdict(int))
    return итог


def жизнь_окном(каталог):
    """Полосы жизни ТЕМ ЖЕ определением, что у симулятора: наших в клетке против ЕГО В
    ОКНЕ 3×3 (точные `cells`, где есть, иначе сетка `frow`). Смерти — в клетке контакта."""
    import бой_по_событиям as Б
    from отход_по_клеткам import _грид, _клетки, _окно
    итог = defaultdict(lambda: [0, 0])
    снимки = [json.loads(s) for s in open(os.path.join(каталог, "coss3_snap.jsonl"), encoding="utf-8")
              if s.strip().startswith("{")]
    снимки = [x for x in снимки if "kills_n" in x]
    события = {с[0]: с for x in снимки for с in (x.get("гибель") or []) if len(с) == 11}
    for a, b in zip(снимки, снимки[1:]):
        n0, n1 = int(a["kills_n"]), int(b["kills_n"])
        нужно = range(n0 + 1, n1 + 1)
        if n1 < n0 or any(q not in события for q in нужно) or not нужно:
            continue
        кл, fa = _клетки(a), _грид(a, "frow")
        мой, его = центр(a.get("brow"), "bH"), центр(a.get("brow"), "e")
        for q in нужно:
            с = события[q]
            if с[3] not in Б.БОЙЦЫ:
                continue
            c = кл.get((с[4], с[5]))
            if not c or not c.get("наших"):
                continue
            e9 = _окно(кл, fa, "его", с[4], с[5])
            if e9 <= 0:
                continue
            м = место(с[4], с[5], мой, его)
            итог[(м, полоса(c["наших"] / e9))][0 if с[2] == 0 else 1] += 1
    return итог


def симулятор(каталог, seed):
    r = replay.прогнать(каталог, seed)
    if not r:
        return None
    сим = r[2]
    з = сим.з
    мой, его = (з.my_cx, з.my_cy), з.en_base
    из = defaultdict(lambda: [0.0, 0.0])
    for (t, cx, cy, _, n, e, пн, пе, _), e1 in zip(сим.журнал_боя, сим.журнал_клетки):
        м = место(cx, cy, мой, его)
        # полоса — по его числу в САМОЙ клетке, как в жизни (`cells`); в клетке его нет,
        # а в окне есть — это «>3»: мы там одни против соседей
        # МОДЕЛЬЮ: у симулятора полоса по числу, которое закон видит (при местной модели
        # это его бойцы в нашей клетке), у жизни — по самой клетке
        if ОКНОМ and not МОДЕЛЬЮ:
            пол = полоса(n / e) if e > 0 else ">3"
        elif МОДЕЛЬЮ:
            пол = полоса(n / e) if e > 0 else ">3"
        else:
            пол = полоса(n / e1) if e1 > 0 else ">3"
        for ключ in (м, (м, пол)):
            из[ключ][0] += пн
            из[ключ][1] += пе
    return из


def main():
    арг = [a for a in sys.argv[1:] if not a.startswith("--")]
    сидов = 3
    global ОКНОМ
    global МОДЕЛЬЮ
    if "--клеткой" in sys.argv:
        ОКНОМ = False
    if "--моделью" in sys.argv:
        ОКНОМ, МОДЕЛЬЮ = False, True
    for a in sys.argv[1:]:
        if a.startswith("--seeds"):
            сидов = int(a.split("=")[1]) if "=" in a else 3
    ж = defaultdict(lambda: [0, 0])
    с = defaultdict(lambda: [0.0, 0.0])
    жп = defaultdict(lambda: [0, 0])
    n = 0
    for корень in арг:
        for d, _, ф in sorted(os.walk(os.path.expanduser(корень))):
            if "coss3_snap.jsonl" not in ф or "coss3_bot.jsonl" not in ф:
                continue
            жз, событий = жизнь(d)
            if not событий:
                continue
            сз = [симулятор(d, seed) for seed in range(сидов)]
            if any(x is None for x in сз):
                continue
            # живые полосы — ТОЛЬКО по партиям, прошедшим в симулятор (29.09: сначала
            # складывались все 36 записей против 18 сыгранных, и сравнение врало)
            for к, v in (жизнь_окном(d) if ОКНОМ else жизнь_по_полосам(d)).items():
                жп[к][0] += v[0]; жп[к][1] += v[1]
            n += 1
            for м in МЕСТА:
                ж[м][0] += жз[м][0]; ж[м][1] += жз[м][1]
            for x in сз:
                for к, v in x.items():
                    с[к][0] += v[0] / сидов; с[к][1] += v[1] / сидов
    print(f"партий {n}, зёрен {сидов}")
    print(f"{'место':7} | {'наши жизнь':>10} {'сим':>7} | {'его жизнь':>9} {'сим':>7} | {'размен жизнь':>12} {'сим':>6}")
    for м in МЕСТА + ("всё",):
        a = ж[м] if м != "всё" else [sum(ж[q][0] for q in МЕСТА), sum(ж[q][1] for q in МЕСТА)]
        b = с[м] if м != "всё" else [sum(с[q][0] for q in МЕСТА), sum(с[q][1] for q in МЕСТА)]
        print(f"{м:7} | {a[0]:10d} {b[0]:7.0f} | {a[1]:9d} {b[1]:7.0f} | {a[1] / max(a[0], 1):12.2f} {b[1] / max(b[0], 1e-9):6.2f}")
    print("\nПО ПОЛОСАМ ПЕРЕВЕСА, наших в клетке против его " + ("в окне 3×3" if ОКНОМ else "в самой клетке"))
    print(f"{'место':7} {'полоса':9} | {'наши жизнь':>10} {'сим':>7} | {'его жизнь':>9} {'сим':>7} | {'размен жизнь':>12} {'сим':>6}")
    for м in МЕСТА:
        for _, _, п in ПОЛОСЫ:
            a, b = жп.get((м, п), [0, 0]), с.get((м, п), [0.0, 0.0])
            if a[0] or a[1] or b[0] or b[1]:
                print(f"{м:7} {п:9} | {a[0]:10d} {b[0]:7.0f} | {a[1]:9d} {b[1]:7.0f} | "
                      f"{a[1] / max(a[0], 1):12.2f} {b[1] / max(b[0], 1e-9):6.2f}")


if __name__ == "__main__":
    main()
