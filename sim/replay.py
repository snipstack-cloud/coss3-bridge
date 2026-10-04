# -*- coding: utf-8 -*-
"""Проверка сборки: команды записанной партии в ЗАМКНУТОМ цикле против той же трассы.

В отличие от `gate.py` (открытый цикл: кто где работает — из трассы), здесь
симулятор сам распределяет людей по командам BALANCE/BUILDERS, сам строит по
BUILD, нанимает по TRAIN, водит волны по ATTACK и дерётся с записанным врагом.
Сравнивается с трассой: ресурсы, крестьяне, пехота, наши потери, его потери от
нас, время первого выхода волны за 180 единиц.

    python3 sim/replay.py <корень с прогонами> [ещё...] [--show N] [--seed S]
"""
import glob
import os
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as SIM   # noqa: E402

СРАВНИВАЕМ = ("food", "wood", "stone", "gold", "iron", "coal", "peasants", "mil_inf", "mil_shooters", "my_mil_lost", "p1_mil_lost", "p1_pea_lost")


def команды_такта(r: dict) -> list:
    """Команды моста из записи такта: `cmds` + волна из полей attack/target/aim + move."""
    из = list(r.get("cmds") or [])
    if r.get("attack"):
        c = {"cmd": "ATTACK", "attack": r.get("attack"), "target": r.get("target") or "base", "aim": r.get("aim")}
        m = r.get("march")
        if isinstance(m, dict) and m.get("via") and m.get("t0") == r.get("gt"):
            c["via"] = m["via"]
        из.append(c)
    mv = r.get("move")
    if isinstance(mv, dict) and mv.get("count"):
        из.append({"cmd": "MOVE", "count": mv.get("count"), "target": mv.get("target") or "home", "aim": mv.get("aim")})
    return из


def прогнать(каталог, seed=0, журнал=None):
    """`журнал` — список: в него каждый такт пишется (t, наши потери, его убитые, убитые крестьяне) — для вех §69/§72 и батареи ядра."""
    з = SIM.Запись(каталог)
    if len(з.снапы) < 20 or len(з.такты) < 5:
        return None
    сим = SIM.Симулятор(з, seed)
    # партии яруса 1: дебют шёл мостом, в `cmds` его нет — иначе реплей стоит без
    # ратуши. Признак: ратуша появилась, а BUILD center в командах не было.
    import debut as D
    from tier1 import в_словарь
    # признак: в ПЕРВОМ записанном такте ратуша уже есть (или строится) — значит,
    # дебют шёл до первого запроса модели и в `cmds` его нет (tier1/2: первый такт
    # на 159-й секунде с BUILD center от модели, а ратуша стоит с 15-й)
    st0 = з.такты[0][1] if з.такты else {}
    дебют_вне_трассы = SIM.ч(st0.get("centers")) > 0 or (з.такты and з.такты[0][0] > 100 and SIM.ч(st0.get("building_now")) > 0)
    дебют = D.Дебют(20) if дебют_вне_трассы else None
    такты = iter(з.такты)
    ближ = next(такты, None)
    ряды = {k: [] for k in СРАВНИВАЕМ}
    времена = []
    первая_волна = {"сим": None, "факт": None}
    # КАЗАРМЫ (27.09): когда встали и сколько казармо-минут вышло. Нужно потому, что
    # армия симулятора была в 1,8 раза больше живой при верном темпе найма, и остаётся
    # проверить единственное — не строит ли он вторую казарму раньше игры (§16г).
    казармы = {"сим1": None, "сим2": None, "казмин_сим": 0.0}
    for x in з.снапы:
        if SIM.ч(x.get("mil_far")) >= 180 and первая_волна["факт"] is None:
            первая_волна["факт"] = SIM.ч(x["gametime"])
    последний = SIM.ч(з.снапы[-1]["gametime"])
    while сим.t < последний and not сим.исход:
        if дебют is not None and not дебют.готов(сим.состояние()):
            cmds, _ = дебют.такт(сим.состояние(), int(сим.t))
            сим.команды([в_словарь(c) for c in cmds])
        while ближ is not None and ближ[0] <= сим.t:
            сим.команды(команды_такта(ближ[2]))
            ближ = next(такты, None)
        сим.такт()
        if журнал is not None:
            журнал.append((сим.t, сим.my_mil_lost, сим.убито_бойцов, сим.убито_крестьян))
        казармы["казмин_сим"] += сим.эк.здания.get("ba17", 0) * SIM.DT / 60.0
        if казармы["сим1"] is None and сим.эк.здания.get("ba17", 0) >= 1:
            казармы["сим1"] = сим.t
        if казармы["сим2"] is None and сим.эк.здания.get("ba17", 0) >= 2:
            казармы["сим2"] = сим.t
        s = сим.состояние()
        f = з.снимок_до(сим.t)
        времена.append(сим.t)
        for k in СРАВНИВАЕМ:
            ряды[k].append((SIM.ч(s.get(k)), SIM.ч(f.get(k))))
        if s.get("mil_far", 0) >= 180 and первая_волна["сим"] is None:
            первая_волна["сим"] = сим.t
    сим.казармы = казармы
    return времена, ряды, сим, первая_волна


def оценка(времена, ряды):
    из = {}
    for k, пары in ряды.items():
        отн = [abs(s - f) / max(f, 50.0) for (s, f), t in zip(пары, времена) if t <= 600]
        s_к, f_к = пары[-1] if пары else (0, 0)
        из[k] = {"до600": S.median(отн) if отн else None, "конец_сим": s_к, "конец_факт": f_к}
    return из


def main():
    арг = [a for a in sys.argv[1:] if not a.startswith("--")]
    показать = 0
    seed = 0
    for i, a in enumerate(sys.argv):
        if a == "--show":
            показать = int(sys.argv[i + 1]); арг = [x for x in арг if x != sys.argv[i + 1]]
        if a == "--seed":
            seed = int(sys.argv[i + 1]); арг = [x for x in арг if x != sys.argv[i + 1]]
    if not арг:
        raise SystemExit(__doc__)
    каталоги = []
    for корень in арг:
        каталоги += [os.path.dirname(x) for x in sorted(glob.glob(os.path.join(корень, "**", "coss3_snap.jsonl"), recursive=True))]
    свод = {k: [] for k in СРАВНИВАЕМ}
    концы = {k: [] for k in СРАВНИВАЕМ}
    волны = []
    исходы = []
    n = 0
    for кат in каталоги:
        r = прогнать(кат, seed)
        if not r:
            continue
        времена, ряды, сим, пв = r
        о = оценка(времена, ряды)
        n += 1
        исходы.append(сим.исход)
        for k in СРАВНИВАЕМ:
            if о[k]["до600"] is not None:
                свод[k].append(о[k]["до600"])
            концы[k].append((о[k]["конец_сим"], о[k]["конец_факт"]))
        if пв["сим"] and пв["факт"]:
            волны.append((пв["сим"], пв["факт"]))
        if показать and n <= показать:
            print(f"\n{кат}: исход {сим.исход}, первая волна за 180: сим {пв['сим']} / факт {пв['факт']}")
            for k in СРАВНИВАЕМ:
                print("  %-12s ошибка600 %4.0f%%  конец %7.0f / %-7.0f" % (k, 100 * (о[k]["до600"] or 0), о[k]["конец_сим"], о[k]["конец_факт"]))
            print("  отказов:", len(сим.квитанции), "; первые:", [q[1][:40] for q in сим.квитанции[:5]])
    print(f"\nЗАМКНУТЫЙ ЦИКЛ, партий {n}; исходы: " + ", ".join(f"{x}: {исходы.count(x)}" for x in sorted(set(map(str, исходы)))))
    print("  %-12s %9s  %s" % ("", "ошибка600", "конец сим/факт (медианы)"))
    for k in СРАВНИВАЕМ:
        if свод[k]:
            print("  %-12s %8.0f%%  %.0f / %.0f" % (k, 100 * S.median(свод[k]), S.median(x for x, _ in концы[k]), S.median(x for _, x in концы[k])))
    if волны:
        print("  первая волна за 180 ед: сим %.0f с / факт %.0f с (медианы, %d партий)" % (
            S.median(x for x, _ in волны), S.median(x for _, x in волны), len(волны)))


if __name__ == "__main__":
    main()
