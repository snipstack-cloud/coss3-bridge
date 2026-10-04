#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ВОРОТА СОСТАВА КЛЕТОК (4.10, §95): где стоят его стрелки — агент против записи.

Замкнутый цикл с агентом (команды записи, противник — агент вида записи) на партиях игрока с
`ecells` по составу (мост с 29.09). В каждом такте, где наша группа стоит в клетке с его бойцами
(контакт), сравниваются: доля стрелков среди его бойцов В КЛЕТКЕ контакта и доля его стрелков,
стоящих В СОСЕДНИХ клетках (из окна 3×3), — у агента (сетка типов `враг.s`; без типов — общая доля
армии) и в записи (ecells того же времени). Мера, названная до счёта: средняя доля стрелков в
клетке контакта у агента в пределах ±0,15 от записи на p3 и p5 (пики есть) и на p2 (пик нет).

    python3 sim/ворота_типов.py [--зёрен 3]
"""
import os
import statistics as St
import sys
from multiprocessing import Pool

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
sys.path.insert(0, os.path.dirname(К))

ЗАПИСИ = (("p3", "~/coss3-res-игрок-отл/igrok_03_10_p3/1"), ("p3", "~/coss3-res-игрок-отл/igrok_04_10_p5/1"),
          ("p2", "~/coss3-res-игрок-отл/igrok_02_10_p2/1"), ("p2", "~/coss3-res-игрок/igrok_01_10/2"))


def _одна(з):
    вид, кат, seed, типы = з
    os.environ["COSS3_AGENT_TYPES"] = "1" if типы else "0"
    import sim as SIM
    SIM.ТИПЫ_АГЕНТА = типы
    import тактик as ТК, replay as R, debut as D
    from tier1 import в_словарь
    ТК._настроить(вид)
    кат = os.path.expanduser(кат)
    з_ = SIM.Запись(кат)
    сим = SIM.Симулятор(з_, seed)
    st0 = з_.такты[0][1] if з_.такты else {}
    дебют_вне = SIM.ч(st0.get("centers")) > 0 or (з_.такты and з_.такты[0][0] > 100 and SIM.ч(st0.get("building_now")) > 0)
    дебют = D.Дебют(20) if дебют_вне else None
    такты = iter(з_.такты); ближ = next(такты, None)
    посл = float(з_.снапы[-1]["gametime"])
    пары = []      # (доля стрелков в клетке контакта: агент, запись; доля его стрелков в соседях: агент, запись)
    while сим.t < посл and not сим.исход:
        if дебют is not None and not дебют.готов(сим.состояние()):
            cmds, _ = дебют.такт(сим.состояние(), int(сим.t)); сим.команды([в_словарь(c) for c in cmds])
        while ближ is not None and ближ[0] <= сим.t:
            сим.команды(R.команды_такта(ближ[2])); ближ = next(такты, None)
        сим.такт()
        снап = з_.снимок_до(сим.t)
        ec = {(c["x"], c["y"]): c for c in (снап.get("ecells") or []) if c.get("n", 0) >= 1 and c.get("стрелков") is not None}
        if not ec:
            continue
        h = сим.враг.h; s = сим.враг.s
        общая = сим._доля_стрелков_врага(снап)
        for г in сим.группы:
            n = sum(г["состав"].values())
            if n < 1:
                continue
            cx, cy = int(round(г["x"])), int(round(г["y"]))
            if not (0 <= cy < 16 and 0 <= cx < 16) or h[cy][cx] < 1:
                continue
            # агент
            а_кл = (s[cy][cx] / h[cy][cx]) if s is not None else общая
            сос_h = sum(h[yy][xx] for yy in range(max(0, cy - 1), min(16, cy + 2)) for xx in range(max(0, cx - 1), min(16, cx + 2)) if (xx, yy) != (cx, cy))
            сос_s = (sum(s[yy][xx] for yy in range(max(0, cy - 1), min(16, cy + 2)) for xx in range(max(0, cx - 1), min(16, cx + 2)) if (xx, yy) != (cx, cy))
                     if s is not None else сос_h * общая)
            окно_s = сос_s + (s[cy][cx] if s is not None else h[cy][cx] * общая)
            а_сос = сос_s / окно_s if окно_s > 0 else None
            # запись: та же клетка (если его там нет — пропуск)
            c = ec.get((cx, cy))
            if not c:
                continue
            з_кл = c["стрелков"] / max(c["n"], 1)
            з_сос_s = sum(q["стрелков"] for (x, y), q in ec.items() if max(abs(x - cx), abs(y - cy)) == 1)
            з_окно = з_сос_s + c["стрелков"]
            з_сос = з_сос_s / з_окно if з_окно > 0 else None
            пары.append((а_кл, з_кл, а_сос, з_сос))
    return вид, os.path.basename(os.path.dirname(кат)), типы, пары


def main():
    зёрен = int(sys.argv[sys.argv.index("--зёрен") + 1]) if "--зёрен" in sys.argv else 3
    зад = [(вид, кат, s, типы) for типы in (False, True) for вид, кат in ЗАПИСИ for s in range(зёрен)]
    with Pool(8) as пул:
        р = пул.map(_одна, зад)
    print("доля его стрелков В КЛЕТКЕ контакта (агент / запись) и доля его стрелков окна, стоящих В СОСЕДНИХ клетках (агент / запись); тактов контакта")
    for типы in (False, True):
        print(f"  {'СЕТКА ТИПОВ' if типы else 'без типов'}:")
        for вид, кат in ЗАПИСИ:
            имя = os.path.basename(os.path.dirname(os.path.expanduser(кат)))
            п = [q for v, и, т, пары in р if т == типы and и == имя for q in пары]
            if not п:
                print(f"    {имя:16} нет контактов с составом в записи"); continue
            кл = [(a, b) for a, b, _, _ in п]; сос = [(a, b) for _, _, a, b in п if a is not None and b is not None]
            print(f"    {имя:16} агент «{вид}»: в клетке {St.mean(a for a, _ in кл):.2f} / {St.mean(b for _, b in кл):.2f} | в соседних "
                  + (f"{St.mean(a for a, _ in сос):.2f} / {St.mean(b for _, b in сос):.2f}" if сос else " — ") + f" | тактов {len(кл)}")


if __name__ == "__main__":
    main()
