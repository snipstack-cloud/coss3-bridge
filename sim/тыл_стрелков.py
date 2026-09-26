# -*- coding: utf-8 -*-
"""Что даёт ключ `--rear-shooters`: пикинёры в контакт, стрелки в шести клетках позади.

Ключ сделан Windows 27.09 и проверен живой партией (смоук `smoke_rear/1`: все волны
ушли «КЕМ: infantry17», мушкетёры дважды отведены в клетку за шесть от боя). Здесь
симулятор ПРЕДСКАЗЫВАЕТ, что это даст, чтобы число было названо ДО серии.

Три режима на одном и том же плане:

* `куча` — как сейчас: вся армия одним приказом;
* `раздельно, закон выкл` — пикинёры бьют, стрелки стоят в тылу и в бою НЕ
  участвуют (так устроено ядро без `ПОДДЕРЖКА_ИЗ_ТЫЛА`);
* `раздельно, закон вкл` — стрелки из тыла бьют каждый такт и не гибнут
  (`combat.поддержка`, 5,6–15 клеток).

Разница между вторым и третьим и есть цена закона: если серия покажет, что ключ
работает, значит закон нужен; если ключ не изменит ничего, закон отвергается.

    python3 sim/тыл_стрелков.py <корни> [--партий 12]
"""
import os
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combat            # noqa: E402
import debut as D        # noqa: E402
import sim as SIM        # noqa: E402
import train as TR       # noqa: E402
from tier1 import в_словарь  # noqa: E402

ЗАЩИТА = [f"bar.pikeman.2.{i}" for i in range(1, 7)]
СТРОЙКИ = (("smith", "smiths", 1, {"wood": 100, "stone": 30}),
           ("minegold", "mines_gold", 1, {"wood": 100, "stone": 100}),
           ("ba17", "ba17", 1, {"wood": 100, "stone": 100, "gold": 500}),
           ("mineiron", "mines_iron", 1, {"wood": 100, "stone": 100}),
           ("ba17", "ba17", 2, {"wood": 100, "stone": 100, "gold": 2500}),
           ("store", "my_stores", 1, {"wood": 50, "stone": 20}))
ТЫЛ_КЛЕТОК = 6      # столько ставит ключ: `--rear-shooters 6`


def сыграть(каталог, seed, раздельно, доля_стрелков=0.3, доля_еды=0.5, до=1200.0):
    з = SIM.Запись(каталог)
    сим = SIM.Симулятор(з, seed)
    деб = D.Дебют(20)
    отведены_к = None
    while сим.t < до and not сим.исход:
        s = сим.состояние()
        из = []
        if not деб.готов(s):
            из += [в_словарь(c) for c in деб.такт(s, int(сим.t))[0]]
        else:
            if float(s.get("centers") or 0) > 0:
                из.append({"cmd": "TRAIN", "role": "peasant", "total": -1})
            for роль, поле, скл, цена in СТРОЙКИ:
                if float(s.get(поле) or 0) >= скл:
                    continue
                нет = [р for р, надо in цена.items() if float(s.get(р) or 0) < надо]
                if нет:
                    из += [{"cmd": "BALANCE", "role": р, "total": 10} for р in нет]
                elif float(s.get("building_now") or 0) == 0:
                    из.append({"cmd": "BUILD", "role": роль, "total": скл})
                break
            кр = float(s.get("peasants") or 0)
            в_шахтах = 0.0
            for рес, поле in (("gold", "mines_gold"), ("iron", "mines_iron")):
                ш = float(s.get(поле) or 0)
                if ш > 0:
                    в_шахтах += 5 * ш
                    из.append({"cmd": "BALANCE", "role": рес, "total": int(5 * ш)})
            назем = max(кр - в_шахтах, 0.0)
            еда = int(round(назем * доля_еды))
            дер = int(round((назем - еда) * 2 / 3))
            кам = int(назем) - еда - дер
            for рес, n in (("food", еда), ("wood", дер), ("stone", кам)):
                if n > 0:
                    из.append({"cmd": "BALANCE", "role": рес, "total": n})
            if float(s.get("ba17") or 0) > 0:
                пик = float(s.get("mil_inf") or 0)
                стр = float(s.get("mil_shooters") or 0)
                есть = стр / max(пик + стр, 1e-9)
                из.append({"cmd": "TRAIN", "role": "musk17" if есть < доля_стрелков else "infantry17",
                           "total": -1})
            for u in ЗАЩИТА:
                if u not in сим.апгрейды:
                    из.append({"cmd": "UPGRADE", "upg": u})
                    break
            if float(s.get("my_freewar") or 0) > 0 and сим.t >= 520:
                цель = "wave" if float(s.get("mil_away") or 0) > 0 else "peasants"
                if раздельно:
                    # пикинёры в контакт, стрелки — в клетку за шесть от боя к нашей базе
                    из.append({"cmd": "ATTACK", "count": "all", "who": "infantry17", "target": цель})
                else:
                    из.append({"cmd": "ATTACK", "count": "all", "target": цель})
        сим.команды(из)
        # отвод стрелков отдельным тактом: файл приказа один, и ключ делает так же
        if раздельно and float(s.get("mil_shooters") or 0) > 0:
            бой = [г for г in сим.группы[1:] if г.get("в_контакте")]
            if бой:
                г = бой[0]
                дом = сим.группы[0]
                dx, dy = дом["x"] - г["x"], дом["y"] - г["y"]
                норма = max((dx * dx + dy * dy) ** 0.5, 1e-9)
                цx = max(0, min(SIM.СЕТКА - 1, int(round(г["x"] + dx / норма * ТЫЛ_КЛЕТОК))))
                цy = max(0, min(SIM.СЕТКА - 1, int(round(г["y"] + dy / норма * ТЫЛ_КЛЕТОК))))
                if отведены_к != (цx, цy):
                    сим.команда({"cmd": "MOVE", "count": "all", "who": "musk17",
                                 "target": "cell", "cx": цx, "cy": цy})
                    отведены_к = (цx, цy)
        сим.такт()
    s = сим.состояние()
    return dict(убито=сим.убито_крестьян, потери=сим.my_mil_lost, его=сим.убито_бойцов,
                армия=float(s.get("mil_inf") or 0) + float(s.get("mil_shooters") or 0),
                поддержек=getattr(сим, "тактов_поддержки", 0))


def main():
    корни = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(sys.argv[sys.argv.index("--партий") + 1]) if "--партий" in sys.argv else 12
    все = TR.партии(корни)
    _, тест = TR.разбить(все)
    партии = тест[:n]
    print(f"партий {len(партии)}; доля стрелков 0,30, еда 50 %, две казармы, тыл {ТЫЛ_КЛЕТОК} клеток")
    print("%-26s %7s %7s %7s %7s %8s" % ("режим", "убито", "потери", "его", "размен", "поддержек"))
    for имя, раздельно, закон in (("куча (как сейчас)", False, False),
                                  ("раздельно, закон выкл", True, False),
                                  ("раздельно, закон ВКЛ", True, True)):
        combat.ПОДДЕРЖКА_ИЗ_ТЫЛА = закон
        из = [сыграть(d, i, раздельно) for i, d in enumerate(партии)]
        р = sum(x["его"] for x in из) / max(sum(x["потери"] for x in из), 1)
        print("%-26s %7.1f %7.0f %7.0f %7.2f %8.0f" % (
            имя, S.median(x["убито"] for x in из), S.median(x["потери"] for x in из),
            S.median(x["его"] for x in из), р, S.median(x["поддержек"] for x in из)), flush=True)
    combat.ПОДДЕРЖКА_ИЗ_ТЫЛА = False


if __name__ == "__main__":
    main()
