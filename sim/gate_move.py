# -*- coding: utf-8 -*-
"""Ворота движения: скорость и время подхода волны по трассам против §4 спецификации.

Спецификация берёт марш 1,1 единицы в секунду ([замер] одной живой партии: 136
единиц за 122 с) и путь по прямой между центрами клеток (клетка 16 единиц).
Здесь то же проверяется по ВСЕМ записанным партиям тремя способами:

  1. по `mil_far` — расстоянию самого дальнего бойца от нашей ратуши (единицы):
     на отрезках между тактами, где оно растёт при бойцах вне дома, наклон и есть
     скорость головы колонны;
  2. по клетке волны `wave_cx/wave_cy`: смещение в клетках × 16 / время между
     тактами, только когда клетка сменилась;
  3. по контракту марша: от `t0` до `t_удара` против пути по прямой от места
     армии до клетки сбора `via` при 1,1 ед/с — насколько сбор дольше чистого
     хода (это и есть «растянутость», §4).

    python3 sim/gate_move.py <корень с прогонами> [ещё...]
"""
import glob
import json
import math
import os
import statistics as S
import sys

СКОРОСТЬ = 1.1       # ед/с, спецификация §4
КЛЕТКА = 16.0        # единиц в клетке при карте 256
ПОРОГ = 0.15


def ч(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def такты(путь):
    из = []
    for s in open(путь, encoding="utf-8"):
        s = s.strip()
        if not s:
            continue
        try:
            r = json.loads(s)
        except json.JSONDecodeError:
            continue
        st = r.get("state")
        if isinstance(st, dict) and "gametime" in st:
            из.append((ч(st["gametime"]), st, r))
    из.sort(key=lambda x: x[0])
    границы = [i for i in range(1, len(из)) if из[i][0] < из[i - 1][0] - 60]
    return из[границы[-1]:] if границы else из


def квартили(xs):
    xs = sorted(xs)
    n = len(xs)
    return (S.median(xs), xs[n // 4], xs[3 * n // 4], n) if n else (float("nan"),) * 3 + (0,)


def main(корни):
    наклоны, клетки, сборы, дистанции = [], [], [], []
    партий = 0
    for корень in корни:
        for путь in sorted(glob.glob(os.path.join(корень, "**", "coss3_bot.jsonl"), recursive=True)):
            тк = такты(путь)
            if len(тк) < 10:
                continue
            партий += 1
            максимум = max(ч(st.get("mil_far")) for _, st, _ in тк)
            if максимум > 0:
                дистанции.append(максимум)
            for (t0, a, ra), (t1, b, rb) in zip(тк, тк[1:]):
                dt = t1 - t0
                if dt <= 0 or dt > 60:
                    continue
                # 1. голова колонны: mil_far растёт, бойцы вне дома есть в оба такта
                d = ч(b.get("mil_far")) - ч(a.get("mil_far"))
                if d >= 8 and ч(a.get("mil_away")) > 0 and ч(b.get("mil_away")) > 0 \
                        and ч(a.get("mil_far")) > 20:
                    наклоны.append(d / dt)
                # 2. клетка волны
                if a.get("wave_cx") is not None and b.get("wave_cx") is not None \
                        and ч(a.get("wave_n")) > 0 and ч(b.get("wave_n")) > 0:
                    dx = ч(b["wave_cx"]) - ч(a["wave_cx"])
                    dy = ч(b["wave_cy"]) - ч(a["wave_cy"])
                    смещ = math.hypot(dx, dy)
                    if смещ >= 1:
                        клетки.append(смещ * КЛЕТКА / dt)
            # 3. контракты марша: t0 -> t_удара против пути до via
            виденные = set()
            for t, st, r in тк:
                m = r.get("march")
                if not isinstance(m, dict) or m.get("t_удара") is None or m.get("t0") in виденные:
                    continue
                виденные.add(m.get("t0"))
                via = m.get("via") or m.get("клетка")
                if not via or st.get("my_army_cx") is None:
                    continue
                # положение армии в такте, ближайшем к t0
                st0 = min(тк, key=lambda x: abs(x[0] - ч(m["t0"])))[1]
                cx, cy = ч(st0.get("my_army_cx")), ч(st0.get("my_army_cy"))
                if st0.get("my_army_cx") is None:
                    cx, cy = ч(st0.get("my_cx")), ч(st0.get("my_cy"))
                путь_ед = math.hypot(ч(via[0]) - cx, ч(via[1]) - cy) * КЛЕТКА
                факт = ч(m["t_удара"]) - ч(m["t0"])
                пред = путь_ед / СКОРОСТЬ
                if пред > 10 and факт > 0:
                    сборы.append((факт, пред, факт / пред, ч(m.get("послано")), ч(m.get("дошло"))))
    print(f"партий {партий}")
    м, к1, к3, n = квартили(наклоны)
    print(f"1. скорость головы колонны по mil_far: медиана {м:.2f} ед/с (кв1 {к1:.2f}, кв3 {к3:.2f}, отрезков {n}); "
          f"спецификация {СКОРОСТЬ}: расхождение {abs(м - СКОРОСТЬ) / СКОРОСТЬ:.0%} — {'ок' if abs(м - СКОРОСТЬ) / СКОРОСТЬ <= ПОРОГ else 'НЕТ'}")
    м, к1, к3, n = квартили(клетки)
    print(f"2. скорость волны по клеткам: медиана {м:.2f} ед/с (кв1 {к1:.2f}, кв3 {к3:.2f}, отрезков {n}); "
          f"клетка 16 ед и такт 15-25 с квантуют: одна клетка за такт = {КЛЕТКА / 20:.2f}")
    if дистанции:
        м, к1, к3, n = квартили(дистанции)
        print(f"   самый дальний боец за партию: медиана {м:.0f} ед (кв1 {к1:.0f}, кв3 {к3:.0f}); "
              f"путь до его базы при {СКОРОСТЬ} ед/с: {м / СКОРОСТЬ:.0f} с")
    if сборы:
        отн = [x[2] for x in сборы]
        м, к1, к3, n = квартили(отн)
        print(f"3. сбор марша: факт/предсказание по прямой до via — медиана {м:.2f} (кв1 {к1:.2f}, кв3 {к3:.2f}, маршей {n}); "
              f"медиана факта {S.median(x[0] for x in сборы):.0f} с при предсказании {S.median(x[1] for x in сборы):.0f} с")
        дольше = [x for x in сборы if x[2] > 1.5]
        print(f"   маршей, где сбор дольше пути в 1,5 раза и более: {len(дольше)} из {n} — это и есть цена ожидания хвоста")
    else:
        print("3. контрактов марша с t_удара в трассах нет")


if __name__ == "__main__":
    арг = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not арг:
        raise SystemExit(__doc__)
    main(арг)
