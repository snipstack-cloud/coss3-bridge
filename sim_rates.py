# -*- coding: utf-8 -*-
"""Темпы для симулятора — из ТРАСС, а не из кода: добыча, найм, рост населения, марш.

Вторая половина параметров симулятора. Первую (цены, здоровье, оружие, время
найма) читает из кода `sim_params_llm.py`. Здесь то, чего в коде нет в готовом
виде: сколько реально приносит крестьянин в секунду на каждом ресурсе с учётом
ходьбы, сколько бойцов в минуту выпускает казарма при бесконечном заказе,
сколько ест деревня. Всё меряется по частым снимкам (`coss3_snap.jsonl`, шаг
около 5 игровых секунд) и только по СВЕЖИМ прогонам — корпус старше это история
моста (правило проекта, купленное 24.09 пять раз).

Как считается, чтобы не врать:
  * добыча: на шаге берётся прирост ресурса на одного занятого; траты
    (найм, стройка, апгрейд) дают провал, поэтому берутся только шаги с
    приростом, а итог — МЕДИАНА, не среднее: медиана не сдвинется от редких
    трат, которые попали в шаг с добычей;
  * еда: прирост уже за вычетом того, что съела деревня; отдельно оценивается
    расход на голову по шагам, где на еде никто не стоит;
  * найм: прирост пехоты на казарму на шаге при бесконечном заказе и без
    потерь на этом шаге;
  * марш: скорость по снимкам не считается — она измерена живой игрой (136
    единиц за 122 с, около 1,1 ед/с) и лежит в `world.md` как [замер].

    python3 sim_rates.py <корень с прогонами> [ещё корни...] [--out sim/темпы.json]
"""
import glob
import json
import os
import statistics as S
import sys

РЕСУРСЫ = {"food": "on_food", "wood": "on_wood", "stone": "on_stone",
           "gold": "on_gold", "iron": "on_iron", "coal": "on_coal"}
МИН_ШАГОВ = 30


def ч(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def снимки(путь):
    из = []
    for строка in open(путь, encoding="utf-8"):
        строка = строка.strip()
        if not строка:
            continue
        try:
            из.append(json.loads(строка))
        except json.JSONDecodeError:
            continue
    из.sort(key=lambda x: ч(x.get("gametime")))
    return из


def такты(путь):
    из = []
    for строка in open(путь, encoding="utf-8"):
        строка = строка.strip()
        if not строка:
            continue
        try:
            r = json.loads(строка)
        except json.JSONDecodeError:
            continue
        st = r.get("state")
        if isinstance(st, dict) and "gametime" in st:
            из.append(st)
    # трасса дописывается партия за партией: границу даёт падение времени
    из_партий, тек, прошлое = [], [], None
    for st in из:
        gt = ч(st.get("gametime"))
        if прошлое is not None and gt < прошлое - 60:
            из_партий.append(тек)
            тек = []
        тек.append(st)
        прошлое = gt
    из_партий.append(тек)
    return max(из_партий, key=len) if из_партий else []


def квартили(xs):
    xs = sorted(xs)
    n = len(xs)
    return {"n": n, "медиана": round(S.median(xs), 4),
            "кв1": round(xs[n // 4], 4), "кв3": round(xs[3 * n // 4], 4)}


def main(корни, выход):
    добыча = {r: [] for r in РЕСУРСЫ}
    еда_расход = []          # еды на крестьянина в секунду, когда на еде никто не стоит
    найм = []                # пехоты в минуту на казарму
    найм_крестьян = []       # крестьян в минуту на ратушу
    файлов = шагов = 0
    for корень in корни:
        for п in sorted(glob.glob(os.path.join(корень, "**", "coss3_snap.jsonl"), recursive=True)):
            сн = снимки(п)
            if len(сн) < 10:
                continue
            файлов += 1
            for a, b in zip(сн, сн[1:]):
                dt = ч(b.get("gametime")) - ч(a.get("gametime"))
                if dt <= 0 or dt > 30:
                    continue
                шагов += 1
                for r, поле in РЕСУРСЫ.items():
                    раб = ч(a.get(поле))
                    d = ч(b.get(r)) - ч(a.get(r))
                    if раб > 0 and d > 0:
                        добыча[r].append(d / раб / dt)
                # расход еды на голову: никто не добывает еду, еда падает
                if ч(a.get("on_food")) == 0 and ч(a.get("peasants")) > 0:
                    d = ч(b.get("food")) - ч(a.get("food"))
                    if d < 0:
                        едоки = ч(a.get("peasants")) + ч(a.get("mil_inf")) + ч(a.get("mil_shooters")) + ч(a.get("mil_cav"))
                        if едоки > 0:
                            еда_расход.append(-d / едоки / dt)
            # НАЙМ — по тактам трассы: в частых снимках нет поля очереди, а без него
            # шаги с пустой казармой размывали бы темп нулями.
            бот = os.path.join(os.path.dirname(п), "coss3_bot.jsonl")
            if os.path.exists(бот):
                тк = такты(бот)
                for a, b in zip(тк, тк[1:]):
                    dt = ч(b.get("gametime")) - ч(a.get("gametime"))
                    if dt <= 0 or dt > 60:
                        continue
                    каз = ч(a.get("ba17"))
                    if каз > 0 and "pikeman:inf" in str(a.get("train_now") or "") \
                            and ч(b.get("my_mil_lost")) == ч(a.get("my_mil_lost")):
                        d = ч(b.get("mil_inf")) - ч(a.get("mil_inf"))
                        if d >= 0:
                            найм.append(d / каз / dt * 60)
                    цен = ч(a.get("centers"))
                    if цен > 0 and "peaeng:inf" in str(a.get("train_now") or "") \
                            and ч(b.get("my_pea_lost")) == ч(a.get("my_pea_lost")):
                        d = ч(b.get("peasants")) - ч(a.get("peasants"))
                        if d >= 0:
                            найм_крестьян.append(d / цен / dt * 60)
    итог = {"источник": корни, "файлов": файлов, "шагов": шагов,
            "добыча_на_крестьянина_в_сек": {r: квартили(v) for r, v in добыча.items() if len(v) >= МИН_ШАГОВ},
            "еда_расход_на_голову_в_сек": квартили(еда_расход) if len(еда_расход) >= МИН_ШАГОВ else None,
            "найм_пехоты_в_мин_на_казарму": квартили(найм) if len(найм) >= МИН_ШАГОВ else None,
            "найм_крестьян_в_мин_на_ратушу": квартили(найм_крестьян) if len(найм_крестьян) >= МИН_ШАГОВ else None,
            "марш_ед_в_сек": {"значение": 1.1, "источник": "[замер] живая игра: 136 единиц за 122 с (world.md)"},
            "как_читать": "медиана по шагам ~5 игровых с; добыча — только шаги с приростом, "
                          "поэтому это верхняя оценка чистого притока; найм — при бесконечном "
                          "заказе, среднее по казармам, включает нули шагов без выпуска"}
    os.makedirs(os.path.dirname(выход) or ".", exist_ok=True)
    json.dump(итог, open(выход, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"файлов {файлов}, шагов {шагов}")
    for r, q in итог["добыча_на_крестьянина_в_сек"].items():
        print(f"  {r:6} на крестьянина: медиана {q['медиана']:.3f}/с (кв1 {q['кв1']:.3f}, кв3 {q['кв3']:.3f}, шагов {q['n']})")
    for имя in ("еда_расход_на_голову_в_сек", "найм_пехоты_в_мин_на_казарму", "найм_крестьян_в_мин_на_ратушу"):
        q = итог[имя]
        print(f"  {имя}: " + (f"медиана {q['медиана']} (кв1 {q['кв1']}, кв3 {q['кв3']}, шагов {q['n']})" if q else "мало данных"))
    print(f"файл: {выход}")


if __name__ == "__main__":
    арг = [a for a in sys.argv[1:] if not a.startswith("--")]
    выход = os.path.join("sim", "темпы.json")
    if "--out" in sys.argv:
        выход = sys.argv[sys.argv.index("--out") + 1]
        арг = [a for a in арг if a != выход]
    if not арг:
        raise SystemExit(__doc__)
    main(арг, выход)
