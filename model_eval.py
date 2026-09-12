#!/usr/bin/env python3
"""Стенд оценки моделей: кто лучше решает НАШУ задачу, а не вообще.

    python model_eval.py                                  # набор по умолчанию
    python model_eval.py --models "a/b,c/d" --repeat 2
    python model_eval.py --models "$(cat список.txt)"

Зачем отдельно от --compare: тот меряет задержку и сбои, то есть можно ли
модель вообще ставить в такт. Здесь меряется КАЧЕСТВО решения — понимает ли
она зависимости построек и двигает ли цепочку к цели.

Проверяются жёсткие правила игры, а не вкусовщина:
  * казарма требует кузницу (lib/country.script:2926) — заказ казармы без
    кузницы игра молча проигнорирует, это прямая потеря такта;
  * без крестьян не растут ресурсы и не строится ничего;
  * готовую армию надо посылать, иначе цель недостижима;
  * повторять заказ, который «НЕ НАЧАЛОСЬ», бессмысленно.

Ситуации подобраны по звеньям цепочки из reward.py плюс случаи, на которых
модели расходятся: режим мира, нехватка ресурсов, занятые слоты стройки,
незавершённый заказ. Каждая даёт один вызов — прогон модели стоит 11 запросов.

Подсказки в промпт по умолчанию НЕ идут. `hints.txt` пишется под конкретную
партию («перемирия нет, атаковать можно с первой секунды»), а случаи здесь
общие и на такую строку ломаются: haiku-4.5 дала 10/39 с живыми подсказками и
19/39 без них, то есть с ними мерились они, а не модель. Вернуть прежнее
поведение — `--hints hints.txt`.

Потолок тут 11 из 11, и сильные модели его возьмут. Смысл не в том, чтобы
кого-то обойти по очкам, а в том, чтобы отсеять ошибающихся: дальше среди
равных по качеству выбирает скорость, потому что она превращается в число
решений за партию.
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import os
import time
from collections import Counter

import llm_policy as LP

# База: полное состояние, чтобы промпт собирался как в бою.
БАЗА = {
    "gametime": 120, "food": 2000, "wood": 2000, "stone": 1000,
    "gold": 500, "iron": 300, "coal": 300,
    "peasants": 20, "on_food": 8, "on_wood": 7, "on_stone": 5,
    "centers": 1, "smiths": 0, "ba17": 0, "mills": 0, "my_stores": 1,
    "houses": 0, "mil_inf": 0, "mil_shooters": 0, "mil_cav": 0,
    "my_freewar": 0, "build_slots_used": 0, "build_slots_total": 12,
    "bai": 1, "p0_enemy": 1,
}


def сост(**правки) -> dict:
    s = dict(БАЗА)
    s.update(правки)
    return s


# (имя, состояние, прошлое состояние, прошлый заказ, обязательно, запрещено)
# «обязательно» — хотя бы одна из пар (команда, роль) должна быть в ответе.
# «запрещено» — ни одной из пар быть не должно.
СЛУЧАИ = [
    ("голый старт",
     сост(peasants=6, smiths=0, ba17=0), None, [],
     [("TRAIN", "peasant")], [("BUILD", "ba17")]),

    ("кузницы нет",
     сост(peasants=20, smiths=0, ba17=0), None, [],
     [("BUILD", "smith")], [("BUILD", "ba17")]),

    ("кузница есть, казармы нет",
     сост(peasants=20, smiths=1, ba17=0), None, [],
     [("BUILD", "ba17")], [("BUILD", "mill"), ("BUILD", "market")]),

    ("казарма есть, армии нет",
     сост(peasants=20, smiths=1, ba17=1), None, [],
     [("TRAIN", "infantry17"), ("TRAIN", "musk17")], [("BUILD", "mill")]),

    ("армия готова — бить",
     сост(peasants=20, smiths=1, ba17=1, mil_inf=8, my_freewar=8), None, [],
     [("ATTACK", "")], []),

    ("заказ не прошёл — не долбить",
     сост(peasants=6, smiths=0, ba17=0, wood=40, stone=10),
     сост(peasants=6, smiths=0, ba17=0, wood=40, stone=10),
     [("BUILD", "smith", 1)],
     [("TRAIN", "peasant")], [("BUILD", "smith")]),

    # --- ниже случаи, где модели расходятся: на них шесть предыдущих насыщаются ---

    ("режим мира — атака запрещена игрой",
     сост(peasants=20, smiths=1, ba17=1, mil_inf=10, my_freewar=10, peacemode=1),
     None, [],
     [("TRAIN", "infantry17"), ("TRAIN", "musk17")], [("ATTACK", "")]),

    ("ресурсов нет совсем",
     сост(peasants=8, smiths=0, wood=5, stone=0, gold=0, food=120), None, [],
     [("TRAIN", "peasant")],
     [("BUILD", "smith"), ("BUILD", "ba17"), ("BUILD", "mill"), ("BUILD", "store")]),

    ("все слоты стройки заняты",
     сост(peasants=20, smiths=0, build_slots_used=12, build_slots_total=12),
     None, [],
     [("TRAIN", "peasant"), ("TRAIN", "infantry17")],
     [("BUILD", "smith"), ("BUILD", "ba17"), ("BUILD", "mill"), ("BUILD", "store")]),

    ("армия набрана, враг рядом — не строить",
     сост(peasants=20, smiths=1, ba17=1, mil_inf=12, my_freewar=12, en_near_dist=180),
     None, [],
     [("ATTACK", "")],
     [("BUILD", "mill"), ("BUILD", "store"), ("BUILD", "market"), ("BUILD", "house")]),

    # --- перераспределение крестьян. Добавлено 11.09.2026: за весь живой эпизод
    # модель не отдала НИ ОДНОЙ BALANCE, хотя такт за тактом писала, что надо.
    # Стенд этого не ловил — среди одиннадцати случаев не было ни одного, где
    # правильный ответ содержит BALANCE, то есть чемпион выбирался вслепую по
    # главному узкому месту партии.

    ("камень в нуле, крестьяне на дереве, свободные есть",
     сост(peasants=20, on_food=2, on_wood=12, on_stone=0, stone=10, wood=1500,
          iron=0, smiths=1, ba17=0),
     None, [],
     [("BALANCE", "stone")],
     [("BUILD", "mineiron"), ("BUILD", "ba17")]),

    ("еда кончается, на еде никого",
     сост(peasants=20, on_food=0, on_wood=14, on_stone=6, food=90, wood=1200),
     None, [],
     [("BALANCE", "food")], []),

    ("кузница строится — заняться следующим",
     сост(peasants=20, smiths=0, ba17=0, build_slots_used=1),
     сост(peasants=20, smiths=0, ba17=0, build_slots_used=0),
     [("BUILD", "smith", 1)],
     [("TRAIN", "peasant"), ("TRAIN", "infantry17")], [("BUILD", "mill"), ("BUILD", "store")]),
]


def разобрать(data: dict) -> list[tuple[str, str]]:
    """Ответ модели -> пары (команда, роль). ATTACK идёт с пустой ролью."""
    пары = []
    for item in (data.get("commands") or [])[:6]:
        if not isinstance(item, dict):
            continue
        # Через ту же нормализацию, что и мост: стенд должен мерить то, что
        # ДОЙДЁТ до игры, а не то, как модель назвала поля.
        c, role, _n = LP.нормализовать(item)
        пары.append((c, "" if c == "ATTACK" else role))
    return пары


def оценить(client, model: str, think: bool, repeat: int,
            подсказки: str = "") -> dict:
    очки, всего, сбои, время = 0, 0, 0, []
    провалы = []
    # Причины сбоёв: молчаливый счётчик уравнивает «модель глупая» и «провайдер
    # держит лимит», а это разные выводы. 11.09.2026 haiku-4.5 набрала 8/39 при
    # 12 сбоях, и по одному числу было не понять, что 12 из них — не её вина.
    причины: Counter = Counter()
    for имя, st, было, заказ, надо, нельзя in СЛУЧАИ:
        for _ in range(repeat):
            всего += 1
            prompt = LP.situation(st, {}, [], подсказки, было, заказ)
            t = time.time()
            try:
                data = LP.ask(client, model, prompt, think, retry=0)
            except Exception as e:
                сбои += 1
                т = str(e)
                код = ("429 лимит" if "429" in т or "rate" in т.lower() else
                       "404 нет модели" if "404" in т else
                       "401/403 доступ" if "401" in т or "403" in т else
                       "таймаут" if "timeout" in т.lower() or "timed out" in т else
                       т[:60])
                причины[код] += 1
                continue
            время.append(time.time() - t)
            пары = разобрать(data)
            есть_нужное = any(п in пары for п in надо)
            есть_лишнее = any(п in пары for п in нельзя)
            if есть_нужное and not есть_лишнее:
                очки += 1
            else:
                беда = "не сделал нужного" if not есть_нужное else "сделал запрещённое"
                провалы.append(f"{имя}: {беда} ({пары})")
    return {"очки": очки, "всего": всего, "сбои": сбои,
            "время": время, "провалы": провалы, "причины": причины}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="",
                    help="список через запятую; пусто — CANDIDATES из llm_policy")
    ap.add_argument("--repeat", type=int, default=1, help="прогонов каждой ситуации")
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--key", default="")
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--verbose", action="store_true", help="печатать все промахи")
    ap.add_argument("--hints", default="", metavar="файл",
                    help="подсказки в промпт; по умолчанию БЕЗ них. Живой "
                         "hints.txt писан под конкретную партию и её настройки, "
                         "а случаи стенда общие — тогда меряются подсказки, а не "
                         "модель. Замер 11.09.2026: haiku-4.5 дала 10/39 с живыми "
                         "подсказками и 19/39 без них. Прежнее поведение — "
                         "--hints hints.txt")
    ap.add_argument("--system", default="", metavar="файл",
                    help="взять SYSTEM из файла вместо зашитого: так сравнивают "
                         "старый промпт с новым на одних и тех же случаях")
    a = ap.parse_args()

    if a.system:
        LP.SYSTEM = open(a.system, encoding="utf-8").read()
        print(f"SYSTEM подменён: {a.system} ({len(LP.SYSTEM)} симв.)")

    key, src = LP.load_key(a.key)
    if not key:
        print("нет ключа: положите его в nim_key.txt или задайте --key")
        return 1
    from openai import OpenAI
    client = OpenAI(base_url=LP.BASE_URL, api_key=key,
                    timeout=a.timeout, max_retries=0)

    подсказки = LP.load_hints(a.hints) if a.hints else ""
    print("подсказки: " + (f"{a.hints}, {len(подсказки)} симв." if подсказки
                           else "без них — меряем SYSTEM и состояние"))

    модели = [m.strip() for m in a.models.split(",") if m.strip()] or LP.CANDIDATES
    print(f"адрес {LP.BASE_URL}")
    print(f"{len(СЛУЧАИ)} ситуаций × {a.repeat} прогон(а) = "
          f"{len(СЛУЧАИ) * a.repeat} вызовов на модель\n")

    итоги = []
    for m in модели:
        r = оценить(client, m, a.think, a.repeat, подсказки)
        med = sorted(r["время"])[len(r["время"]) // 2] if r["время"] else 0.0
        худш = max(r["время"]) if r["время"] else 0.0
        итоги.append((m, r["очки"], r["всего"], r["сбои"], med, худш, r["провалы"]))
        print(f"  {m:44s} {r['очки']}/{r['всего']} верных, "
              f"медиана {med:5.1f} с, худшая {худш:5.1f} с, сбоев {r['сбои']}")
        if r["сбои"]:
            print("      сбои: " + ", ".join(f"{к} ×{n}" for к, n
                                             in r["причины"].most_common()))
        if a.verbose:
            for стр in r["провалы"]:
                print(f"      {стр}")

    # Сортируем по качеству, при равенстве — по скорости. Быстрая, но глупая
    # модель хуже медленной и умной: такт можно и удлинить, а ошибку нет.
    итоги.sort(key=lambda x: (-x[1], x[4]))
    print("\nот лучшей к худшей:")
    for m, оч, вс, сб, med, худш, _ in итоги:
        print(f"  {оч}/{вс}  {med:5.1f} с  {m}" + (f"  (сбоев {сб})" if сб else ""))
    лучший = итоги[0]
    print(f"\nставить так: python llm_policy.py --model {лучший[0]}")
    if лучший[1] < лучший[2]:
        print(f"  но и она ошибается в {лучший[2] - лучший[1]} из {лучший[2]} — "
              f"прогоните с --verbose и поправьте hints.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
