#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""СВЕРКА СОБЫТИЙ ГИБЕЛИ СО СЧЁТЧИКАМИ: сколько смертей прошло через ворота урона.

События (`block_kills.inc`, поле `kills`) пишутся в единственном месте движка, где
в миг смерти известны и жертва, и убийца — в воротах смерти `_misc_DoDamage`.
Через них проходит всё, что убито уроном. НЕ проходит то, что умерло иначе:
голод, роспуск, захват. Картовые счётчики (`my_mil_lost`, `my_pea_lost`,
`p<n>_mil_lost`, `p<n>_pea_lost` — `gPlayer.stat.killed`) считают всё.

Поэтому мера — не «сходится ли», а РАЗРЫВ по каждой стороне и классу: события
против счётчика. Живая партия 27.09: наших 22 события против 22 по счётчику, его
бойцов 2 против 2, его крестьян 13 против 16 — три смерти вне урона, и это факт
о партии (голод или роспуск у него), а не дефект поля.

Вторая половина инструмента — сама раскладка: где гибли и от кого, обеими
сторонами. Это то, чем калибруются законы боя по клеткам, и то, что модель
получает в такте секцией «Гибель за такт».

    python мера_потерь.py --dir "<папка игры>"             # живая партия
    python мера_потерь.py --trace coss3_bot.jsonl         # по записям тактов
    python мера_потерь.py --snap coss3_snap.jsonl         # по снимкам раз в 5 с

Живьём события копятся по НОМЕРУ: кольцо блока несёт 48 последних, читать надо
чаще, чем гибнут 48 человек, — раз в секунду хватает.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coss3_map as M
from coss3_bridge import Bridge


def _ц(v, п=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return п


def свод(события: list[dict], plind: int, счётчики: dict) -> list[str]:
    """Строки отчёта: разрыв со счётчиками по сторонам и классам, клетки, убийцы."""
    наши = [с for с in события if с["жертва_pl"] == plind]
    его = [с for с in события if с["жертва_pl"] != plind]
    из = [f"событий всего {len(события)}, наших {len(наши)}, его {len(его)}"]

    def сторона(имя, соб, mil, pea):
        кл = Counter(с["жертва"] for с in соб)
        бойцы = sum(n for к, n in кл.items() if к in "ISCG")
        крест = кл.get("P", 0)
        из.append(f"{имя}: бойцов по событиям {бойцы} против счётчика {mil} "
                  f"(разрыв {mil - бойцы:+d}); крестьян {крест} против {pea} "
                  f"(разрыв {pea - крест:+d}); классы {dict(кл)}")
        if соб:
            клетки = Counter((с["x"], с["y"]) for с in соб).most_common(6)
            из.append("   где: " + ", ".join(f"({x},{y}) {n}" for (x, y), n in клетки))
            убийцы = Counter((с["убийца"], с["оружие"]) for с in соб).most_common(5)
            из.append("   от кого: " + ", ".join(
                f"{M.КЛАСС_ГИБЕЛИ.get(к, к)} {M.ОРУЖИЕ_ГИБЕЛИ.get(о, о)} {n}"
                for (к, о), n in убийцы))

    сторона("НАШИ", наши, _ц(счётчики.get("my_mil_lost")), _ц(счётчики.get("my_pea_lost")))
    # Чужие слоты — по образцу имени: индекс врага бывает не первым.
    враг = next((k[:2] for k in счётчики if k.startswith("p") and k.endswith("_mil_lost")
                 and k[1:2].isdigit() and int(k[1]) != plind), "p1")
    сторона("ЕГО ", его, _ц(счётчики.get(f"{враг}_mil_lost")), _ц(счётчики.get(f"{враг}_pea_lost")))
    return из


def по_файлу(путь: str, ключ: str) -> int:
    """Трасса или снимки: события лежат списками в `гибель`, счётчики — в последней записи."""
    события: dict = {}
    последняя: dict = {}
    for строка in open(путь, encoding="utf-8"):
        строка = строка.strip()
        if not строка:
            continue
        try:
            з = json.loads(строка)
        except ValueError:
            continue
        ист = з.get("state") or з
        for с in (з.get("гибель") or []):
            if len(с) == 11:
                события[с[0]] = dict(seq=с[0], gt=с[1], жертва_pl=с[2], жертва=с[3], x=с[4], y=с[5],
                                     убийца_pl=с[6], убийца=с[7], kx=с[8], ky=с[9], оружие=с[10])
        if any(k in ист for k in ("my_mil_lost", "kills_n")):
            последняя = ист
    if not события and "kills_n" not in последняя:
        print(f"{путь}: событий гибели нет ни в одной записи — это {ключ} ДО правки 27.09")
        return 0
    print(f"{путь}:")
    for с in свод(sorted(события.values(), key=lambda с: с["seq"]),
                 _ц(последняя.get("plind")), последняя):
        print("  " + с)
    return 0


def живьём(d: str, plind: int, секунд: float) -> int:
    br = Bridge(d, plind)
    начало = time.time()
    события: dict = {}
    st: dict = {}
    видел_поле = False
    while time.time() - начало < секунд:
        новое = br.read_state()
        if новое:
            st = новое
            if M.есть_события_гибели(st):
                if not видел_поле:
                    видел_поле = True
                    print(f"{_ц(st.get('gametime'))} с: поле kills есть", flush=True)
                for с in M.события_гибели(st):
                    if с["seq"] not in события:
                        события[с["seq"]] = с
                        кто = "наш" if с["жертва_pl"] == plind else "его"
                        print(f"{с['gt']:>5} с  {кто} {M.КЛАСС_ГИБЕЛИ.get(с['жертва'], с['жертва'])} "
                              f"в ({с['x']},{с['y']}) от {M.КЛАСС_ГИБЕЛИ.get(с['убийца'], с['убийца'])} "
                              f"{M.ОРУЖИЕ_ГИБЕЛИ.get(с['оружие'], с['оружие'])} из ({с['kx']},{с['ky']})",
                              flush=True)
        time.sleep(1.0)
    if not видел_поле:
        print("поля kills в состоянии не было: мост без блока событий (--human-kills)")
        return 1
    print()
    for с in свод(sorted(события.values(), key=lambda с: с["seq"]), plind, st):
        print(с)
    пропущено = _ц(st.get("kills_n")) - len(события)
    if пропущено > 0:
        print(f"ВНИМАНИЕ: {пропущено} событий не прочитано — кольцо на 48 переполнялось между чтениями")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="", help="папка игры: следить за живой партией")
    ap.add_argument("--trace", default="", help="трасса тактов coss3_bot.jsonl")
    ap.add_argument("--snap", default="", help="снимки coss3_snap.jsonl")
    ap.add_argument("--plind", type=int, default=0)
    ap.add_argument("--seconds", type=float, default=960.0)
    a = ap.parse_args()
    if a.trace:
        return по_файлу(a.trace, "трасса")
    if a.snap:
        return по_файлу(a.snap, "снимки")
    if not a.dir:
        ap.error("нужен --dir, --trace или --snap")
    return живьём(a.dir, a.plind, a.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
