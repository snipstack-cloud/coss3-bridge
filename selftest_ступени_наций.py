#!/usr/bin/env python3
"""СТУПЕНИ КАЗАРМЫ ЛЮБОЙ НАЦИИ ВИДНЫ ОЦЕНЩИКУ (1.11). Бот Польшей четыре партии не покупал `bar.pikemanpol.*`: оценщик знал
только линейки Нидерландов. Таблица `sim/ступени.json` (из `lib/country.script`, `sim/ступени_казармы.py`)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combat_math as CM
import прокачки as P

ок = 0
плохо = []


def проверка(имя, усл, что=""):
    global ок
    if усл:
        ок += 1
        print("ОК  ", имя)
    else:
        плохо.append(имя)
        print("ПЛОХО", имя, что)


# (1) живые прибавки Польши 1.11 (его пика 8 → 9 → 10 → 11 → 13, защита 0 → 1 → 2 → 4) и цены живого ценника
пол = [CM.прибавка_ступени("pikemanpol", 1, у, ц) for у, ц in ((1, {"food": 500, "gold": 50}), (2, {"food": 1400, "gold": 100}),
                                                             (3, {"food": 3200, "gold": 450}), (4, {"food": 8200, "gold": 2220}))]
проверка("атака пики Польши +1,+1,+1,+2 (живьём 9/10/11/13)", пол == [1, 1, 1, 2], пол)
защ = [CM.прибавка_ступени("pikemanpol", 2, у, ц) for у, ц in ((1, {"food": 250, "gold": 75}), (2, {"food": 800, "gold": 150}),
                                                             (3, {"food": 3500, "gold": 225}))]
проверка("защита пики Польши +1,+1,+2 (живьём 1/2/4)", защ == [1, 1, 2], защ)
# (2) Нидерланды — те же числа, что прежняя таблица
нид = [CM.прибавка_ступени("pikeman", 1, у, ц) for у, ц in ((1, {"food": 900, "gold": 150}), (2, {"food": 700, "gold": 400}),
                                                          (3, {"food": 3100, "gold": 250}))]
проверка("атака пики Нидерландов по цене = прежней таблице", нид == list(CM.ПРИБАВКИ_СТУПЕНЕЙ[("pikeman", 1)][:3]), нид)
# (3) род линейки для всех наций
проверка("линейки наций → род", all(CM.род_линейки(л) == "infantry17" for л in
                                     ("pikeman", "pikemanpol", "pikemanrus", "pikemantur", "pikemansco", "pikemanpor", "pikemanswi", "pikemanspa"))
         and all(CM.род_линейки(л) == "musk17" for л in ("musketeernet", "musketeerpol", "musketeeraus", "musketeer"))
         and CM.род_линейки("pikeman18") is None)
# (4) оценщик видит ступени Польши на снимке
st = {"gametime": 360, "food": 3000, "gold": 2000, "iron": 1000,
      "fighters": "infantry17=pikemanpol,hp90,atk8,wkind1,pause0,rmax206,dmgs0,dmgp0,dinit8,dpike0,dsword0,dbullet0,food25,gold1,iron0,coal0 "
                  "musk17=musketeerpol,hp70,atk9,wkind3,pause312,rmax1312,dmgs0,dmgp0,dinit9,dpike0,dsword0,dbullet0,food40,gold3,iron3,coal0",
      "en_fighters": "infantry17=hp90,atk8,wkind1,pause0,rmax206,dmgs0,dmgp0,dinit8,dpike0,dsword0,dbullet0",
      "upg_avail": "bar.pikemanpol.1.1=f500g50i0,bar.pikemanpol.2.1=f250g75i0,bar.musketeerpol.1.1=f500g125i0",
      "mil_inf": 80, "mil_shooters": 10, "p1_inf": 80, "p1_shoot": 0}
оц = P.оценить(st)
имена = {к["имя"] for к in оц["кандидаты"]}
проверка("оценщик видит bar.pikemanpol.1.1 и 2.1", {"bar.pikemanpol.1.1", "bar.pikemanpol.2.1"} <= имена, имена)
# (5) таблица покрывает пику и мушкетёра каждой нации, у которой они есть в казарме
import json
з = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim", "ступени.json"), encoding="utf-8"))["записи"]
линейки = {r["линейка"] for r in з}
нужно = {"pikeman", "pikemanpol", "pikemanrus", "pikemantur", "pikemansco", "pikemanpor", "pikemanswi", "pikemanspa",
         "musketeer", "musketeernet", "musketeerpol", "musketeeraus", "musketeerspa", "musketeersco"}
проверка("в таблице есть все линейки пик и мушкетёров наций", нужно <= линейки, sorted(нужно - линейки))

print(f"\n{ок} из {ок + len(плохо)}")
sys.exit(1 if плохо else 0)
