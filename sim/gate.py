# -*- coding: utf-8 -*-
"""Ворота симулятора (шаг 3): ядро экономики против записанной партии.

Открытый цикл: ядру подаются наблюдённые входы партии — кто где работает (`on_*`
из частых снимков), что стоит в очередях (`train_now` из тактов), какие здания
заложены (рост счётчиков), какие апгрейды взяты (`upg_done`) и по какой цене
(`upg_shown`/`upg_aca`), посевы (SEED в `cmds`), потери (`my_mil_lost`,
`my_pea_lost`). Сравниваются ВЫХОДЫ: шесть ресурсов, крестьяне, пехота.

Так проверяются механики — темпы, цены, порог еды, удорожание, — а не логика
распределения моста. Порог из спецификации: медиана относительной ошибки за
первые 600 с не больше 15 %. Не прошло — в спецификацию добавляется механика.

    python3 sim/gate.py <каталог прогона или корень> [ещё...] [--food чистая|валовая|обе] [--show N]
"""
import glob
import json
import os
import re
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

СРАВНИВАЕМ = ("food", "wood", "stone", "gold", "iron", "coal", "peasants", "mil_inf")
ЗАДЕРЖКА = 20.0   # секунд доставки добычи, ключ --lag; 20 — [замер] ворота 25.09
ПОРОГ = 0.15
БУКВЫ = {"f": "food", "w": "wood", "s": "stone", "g": "gold", "i": "iron", "c": "coal"}


def ч(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def строки(путь):
    из = []
    for s in open(путь, encoding="utf-8"):
        s = s.strip()
        if s:
            try:
                из.append(json.loads(s))
            except json.JSONDecodeError:
                pass
    return из


def партия(каталог):
    снапы = sorted((x for x in строки(os.path.join(каталог, "coss3_snap.jsonl")) if "gametime" in x),
                   key=lambda x: ч(x["gametime"]))
    такты = []
    for r in строки(os.path.join(каталог, "coss3_bot.jsonl")):
        st = r.get("state")
        if isinstance(st, dict) and "gametime" in st:
            такты.append((ч(st["gametime"]), st, r.get("cmds") or []))
    такты.sort(key=lambda x: x[0])
    # хвост трассы — последняя партия (файл дописывается)
    границы = [i for i in range(1, len(такты)) if такты[i][0] < такты[i - 1][0] - 60]
    if границы:
        такты = такты[границы[-1]:]
    return снапы, такты


def такт_до(такты, t):
    лучший = None
    for gt, st, cmds in такты:
        if gt <= t:
            лучший = (gt, st, cmds)
        else:
            break
    return лучший


def заказы_из(train_now: str) -> dict:
    из = {}
    for кусок in str(train_now or "").split(","):
        if ":" in кусок:
            имя, сколько = кусок.split(":", 1)
            из[имя.strip()] = сколько.strip() not in ("", "0")
    return из


def цены_апгрейдов(st) -> dict:
    из = {}
    for поле in ("upg_shown", "upg_aca"):
        for кусок in str(st.get(поле) or "").split(","):
            if "=" in кусок:
                имя, цена = кусок.split("=", 1)
                из[имя.strip()] = {БУКВЫ[m[0]]: int(m[1]) for m in re.findall(r"([fwsgic])(\d+)", цена)}
    return из


def прогнать(каталог, п, т, вариант_еды):
    снапы, такты = партия(каталог)
    if len(снапы) < 20 or not такты:
        return None
    нач = dict(снапы[0])
    т0 = такт_до(такты, ч(нач["gametime"])) or такты[0]
    for поле in ("stables", "academi"):
        нач.setdefault(поле, т0[1].get(поле))
    эк = core.Экономика(п, т, нач, вариант_еды, ЗАДЕРЖКА)
    ряды = {k: [] for k in СРАВНИВАЕМ}
    времена = []
    взятые = set(x for x in str(т0[1].get("upg_done") or "").split(",") if x)
    посевы_учтены = set()
    прошлый_такт_gt = None
    # Стройка: игра списывает цену ПРИ ЗАКЛАДКЕ (в трассе `wip` появляется, ресурсы
    # падают), а счётчик здания растёт при ЗАВЕРШЕНИИ (шахта 96 -> 142 с). Поэтому
    # списываем по появлению роли в `wip`, а при росте счётчика гасим ожидание.
    ожидают = {}          # роль -> сколько заложено, но ещё не достроено
    прошлый_wip = None
    for a, b in zip(снапы, снапы[1:]):
        t0, t1 = ч(a["gametime"]), ч(b["gametime"])
        dt = t1 - t0
        if dt <= 0 or dt > 30:
            continue
        тк = такт_до(такты, t0)
        st_т = тк[1] if тк else {}
        wip = str(st_т.get("wip") or "")
        роль_wip = wip.split("/")[0] if wip else ""
        if роль_wip and роль_wip != прошлый_wip and роль_wip in core.ЗДАНИЯ:
            эк.списать(эк.цена_здания_с_ожиданием(роль_wip, ожидают.get(роль_wip, 0)), f"BUILD {роль_wip}", t0)
            ожидают[роль_wip] = ожидают.get(роль_wip, 0) + 1
        прошлый_wip = роль_wip
        # события между снимками: здания
        for роль, (sid, поле) in core.ЗДАНИЯ.items():
            было, стало = ч(a.get(поле)), ч(b.get(поле))
            if поле in ("stables", "academi"):
                было, стало = эк.здания[поле], ч(st_т.get(поле))
            for _ in range(int(max(0, стало - было))):
                if ожидают.get(роль, 0) > 0:
                    ожидают[роль] -= 1
                    эк.здания[поле] += 1
                else:
                    эк.заложить(роль, t0)
        # апгрейды и посевы — по тактам, попавшим в этот шаг
        for gt, st, cmds in такты:
            if t0 <= gt < t1 or (прошлый_такт_gt is None and gt < t1):
                новые = set(x for x in str(st.get("upg_done") or "").split(",") if x) - взятые
                if новые:
                    цены = цены_апгрейдов(тк[1] if тк else st)
                    for имя in новые:
                        if имя in цены:
                            эк.списать(цены[имя], f"UPGRADE {имя}", gt)
                    взятые |= новые
                for c in cmds:
                    if c.get("cmd") == "SEED" and (gt, id(c)) not in посевы_учтены:
                        n = int(c.get("a2") or 0) or 1
                        эк.списать({"gold": core.ЦЕНА_ПОЛЯ["gold"] * n}, "SEED", gt)
                        посевы_учтены.add((gt, id(c)))
                прошлый_такт_gt = gt
        потери = {"mil_inf": ч(b.get("my_mil_lost")) - ч(a.get("my_mil_lost")),
                  "peasants": ч(b.get("my_pea_lost")) - ч(a.get("my_pea_lost"))}
        входы = dict(a)
        входы["food_ready"] = st_т.get("food_ready")
        эк.шаг(dt, t0, входы, заказы_из(st_т.get("train_now")), потери, взятые)
        сн = эк.снимок()
        времена.append(t1)
        for k in СРАВНИВАЕМ:
            ряды[k].append((сн.get(k, 0), ч(b.get(k))))
    return времена, ряды, эк


def балансовые_темпы(каталог, п, т):
    """Баланс партии по НАБЛЮДЁННЫМ событиям: здания и апгрейды — по трассе, найм —
    по приросту численности плюс потери (не по найму симулятора: тот зависит от
    порога еды и завёл бы круг). Возвращает на партию: крестьяно-секунды по
    ресурсам, добыто (конец − начало + списано), голово-секунды — для совместной
    подгонки темпа еды и расхода на голову по всем партиям сразу.
    """
    r = прогнать(каталог, п, т, "валовая")
    if not r:
        return None
    снапы, такты = партия(каталог)
    списано = {k: 0.0 for k in core.РЕСУРСЫ}
    for _, за_что, цена in r[2].журнал:
        if за_что.startswith("TRAIN"):
            continue
        for k, v in цена.items():
            списано[k] += v
    # найм по факту: прирост + потери
    a0, a1 = снапы[0], снапы[-1]
    нанято = {"peaeng": max(0.0, ч(a1.get("peasants")) - ч(a0.get("peasants")) + ч(a1.get("my_pea_lost")) - ч(a0.get("my_pea_lost"))),
              "pikeman": max(0.0, ч(a1.get("mil_inf")) - ч(a0.get("mil_inf")) + ч(a1.get("my_mil_lost")) - ч(a0.get("my_mil_lost"))),
              "musketeernet": max(0.0, ч(a1.get("mil_shooters")) - ч(a0.get("mil_shooters"))),
              "dragoon": max(0.0, ч(a1.get("mil_cav")) - ч(a0.get("mil_cav")))}
    for имя, n in нанято.items():
        for k, v in r[2].цена_юнита(имя).items():
            списано[k] += v * n
    раб = {k: 0.0 for k in core.РЕСУРСЫ}
    головы = 0.0
    for a, b in zip(снапы, снапы[1:]):
        dt = ч(b["gametime"]) - ч(a["gametime"])
        if dt <= 0 or dt > 30:
            continue
        for k in core.РЕСУРСЫ:
            раб[k] += ч(a.get("on_" + k)) * dt
        головы += (ч(a.get("peasants")) + ч(a.get("mil_inf")) + ч(a.get("mil_shooters")) + ч(a.get("mil_cav"))) * dt
    добыто = {k: ч(a1.get(k)) - ч(a0.get(k)) + списано[k] for k in core.РЕСУРСЫ}
    return {"раб": раб, "добыто": добыто, "головы": головы}


def свести_темпы(партии):
    """Медианы темпов по партиям; еда — МНК по двум неизвестным (валовый темп и расход на голову)."""
    import numpy as np
    итог = {}
    for k in core.РЕСУРСЫ:
        xs = sorted(x["добыто"][k] / x["раб"][k] for x in партии if x["раб"][k] > 300 and k != "food")
        if xs:
            n = len(xs)
            итог[k] = {"n": n, "медиана": round(S.median(xs), 4), "кв1": round(xs[n // 4], 4), "кв3": round(xs[3 * n // 4], 4)}
    строки_ = [x for x in партии if x["раб"]["food"] > 300]
    A = np.array([[x["раб"]["food"], -x["головы"]] for x in строки_])
    y = np.array([x["добыто"]["food"] for x in строки_])
    g, c = np.linalg.lstsq(A, y, rcond=None)[0]
    ост = y - A @ np.array([g, c])
    итог["food"] = {"n": len(строки_), "медиана": round(float(g), 4), "кв1": None, "кв3": None,
                    "подгонка": f"МНК по {len(строки_)} партиям: темп {g:.3f}/с на крестьянина, расход {c:.4f}/с на голову, "
                                f"медиана |остатка| {float(np.median(np.abs(ост))):.0f} еды за партию"}
    итог["food_расход_на_голову"] = round(float(c), 4)
    return итог


def оценка(времена, ряды, до=600):
    из = {}
    for k, пары in ряды.items():
        отн = [abs(s - f) / max(f, 50.0) for (s, f), t in zip(пары, времена) if t <= до]
        отн_все = [abs(s - f) / max(f, 50.0) for (s, f) in пары]
        s_к, f_к = пары[-1] if пары else (0, 0)
        из[k] = {"до600": S.median(отн) if отн else None, "всё": S.median(отн_все) if отн_все else None,
                 "конец_сим": s_к, "конец_факт": f_к}
    return из


def main():
    арг = [a for a in sys.argv[1:] if not a.startswith("--")]
    вариант = "обе"
    показать = 0
    global ЗАДЕРЖКА
    for i, a in enumerate(sys.argv):
        if a == "--lag":
            ЗАДЕРЖКА = float(sys.argv[i + 1])
            арг = [x for x in арг if x != sys.argv[i + 1]]
        if a == "--food":
            вариант = sys.argv[i + 1]
            арг = [x for x in арг if x != вариант]
        if a == "--show":
            показать = int(sys.argv[i + 1])
            арг = [x for x in арг if x != sys.argv[i + 1]]
    if not арг:
        raise SystemExit(__doc__)
    п, т = core.загрузить()
    каталоги = []
    if "--rates" in sys.argv:
        партии_ = []
        for корень in арг:
            for x in sorted(glob.glob(os.path.join(корень, "**", "coss3_snap.jsonl"), recursive=True)):
                б = балансовые_темпы(os.path.dirname(x), п, т)
                if б:
                    партии_.append(б)
        итог = свести_темпы(партии_)
        print("БАЛАНСОВЫЕ ТЕМПЫ (ресурс/с на крестьянина; в скобках пошаговая медиана из темпы.json):")
        for k in core.РЕСУРСЫ:
            q = итог.get(k)
            if q:
                print("  %-6s медиана %.3f  кв1 %s  кв3 %s  партий %d   (было %.3f)" % (
                    k, q["медиана"], q["кв1"], q["кв3"], q["n"], т["добыча_на_крестьянина_в_сек"][k]["медиана"]))
        print("  еда:", итог["food"]["подгонка"])
        if "--write" in sys.argv:
            for путь in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "параметры.json"),
                         os.path.join(os.path.dirname(os.path.abspath(__file__)), "темпы.json")):
                д = json.load(open(путь, encoding="utf-8"))
                цель = д["темпы_из_трасс"] if "темпы_из_трасс" in д else д
                цель["добыча_балансовая_на_крестьянина_в_сек"] = {k: v for k, v in итог.items() if k in core.РЕСУРСЫ}
                цель["еда_расход_на_голову_в_сек_баланс"] = итог["food_расход_на_голову"]
                цель["как_читать_баланс"] = ("валовый темп на крестьяно-секунду по балансу партии: (конец − начало + "
                    "списано по наблюдённым покупкам) / Σ on_X·dt; еда — совместная МНК-подгонка темпа и расхода на голову")
                json.dump(д, open(путь, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("записано в параметры.json и темпы.json")
        return
    for корень in арг:
        if os.path.exists(os.path.join(корень, "coss3_snap.jsonl")):
            каталоги.append(корень)
        else:
            каталоги += [os.path.dirname(x) for x in sorted(glob.glob(os.path.join(корень, "**", "coss3_snap.jsonl"), recursive=True))]
    варианты = ("чистая", "валовая") if вариант == "обе" else (вариант,)
    for в in варианты:
        свод = {k: [] for k in СРАВНИВАЕМ}
        концы = {k: [] for k in СРАВНИВАЕМ}
        n = 0
        for кат in каталоги:
            r = прогнать(кат, п, т, в)
            if not r:
                continue
            времена, ряды, эк = r
            о = оценка(времена, ряды)
            n += 1
            for k in СРАВНИВАЕМ:
                if о[k]["до600"] is not None:
                    свод[k].append(о[k]["до600"])
                концы[k].append((о[k]["конец_сим"], о[k]["конец_факт"]))
            if показать and n <= показать:
                print(f"\n{кат} [{в}]")
                print("  %-9s %8s %8s %8s" % ("", "ошибка600", "сим_кон", "факт_кон"))
                for k in СРАВНИВАЕМ:
                    print("  %-9s %7.0f%% %8.0f %8.0f" % (k, 100 * (о[k]["до600"] or 0), о[k]["конец_сим"], о[k]["конец_факт"]))
                print("  списания: " + "; ".join(f"{з}" for _, з, _ in эк.журнал[:12]) + (" ..." if len(эк.журнал) > 12 else ""))
        print(f"\nВОРОТА, еда «{в}», партий {n}: медиана относительной ошибки за первые 600 с (порог {ПОРОГ:.0%})")
        print("  %-9s %9s %9s  %s" % ("", "ошибка", "верд.", "конец сим/факт (медианы)"))
        for k in СРАВНИВАЕМ:
            if not свод[k]:
                continue
            м = S.median(свод[k])
            сим = S.median(x for x, _ in концы[k])
            факт = S.median(x for _, x in концы[k])
            print("  %-9s %8.0f%% %9s  %.0f / %.0f" % (k, 100 * м, "ок" if м <= ПОРОГ else "НЕТ", сим, факт))


if __name__ == "__main__":
    main()
