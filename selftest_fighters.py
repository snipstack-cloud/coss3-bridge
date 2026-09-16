"""Строка найма: свойства отдельно, цена отдельно, и ложной нехватки нет.

Строка взята С ЖИВОЙ ИГРЫ 16.09 (Windows, `coss3_eco_P0.dat`), не придумана.
"""
import llm_policy as П

БОЙЦЫ = ("infantry17=pikeman,hp90,atk8,dpike3,dsword2,dbullet4,"
         "food25,gold3,iron20,coal0 "
         "musk17=musketeernet,hp65,atk10,dpike0,dsword0,dbullet0,"
         "food50,gold8,iron4,coal0 "
         "officer17=officer,hp125,atk30,dpike2,dsword2,dbullet5,"
         "food50,gold150,iron30,coal0")

СОСТ = {
    "gametime": 500, "food": 21704, "wood": 900, "stone": 800, "gold": 1647,
    "iron": 3023, "coal": 500, "peasants": 40, "idle_pea": 5,
    "centers": 1, "mills": 1, "smiths": 1, "ba17": 1, "mil_inf": 10,
    "fighters": БОЙЦЫ,
}

ошибок = 0


def проверь(что, условие, пояснение=""):
    global ошибок
    print(("  ОК   " if условие else "  ПРОВАЛ ") + что
          + (f"  [{пояснение}]" if пояснение else ""))
    if not условие:
        ошибок += 1


print("== 1. Ложная нехватка ресурсов ==")
for роль in ("infantry17", "musk17", "officer17"):
    мало = П.не_по_карману(роль, СОСТ)
    боевые = [м for м in мало if any(с in м for с in ("atk", "dpike", "dsword", "dbullet"))]
    проверь(f"{роль}: боевые свойства не считаются ресурсом",
            not боевые, ", ".join(мало) or "нехватки нет")

бедно = dict(СОСТ, food=10, iron=0)
мало = П.не_по_карману("infantry17", бедно)
проверь("настоящую нехватку по-прежнему видит",
        any("еды" in м for м in мало) and any("железа" in м for м in мало),
        ", ".join(мало))

print()
print("== 2. Строка найма ==")
текст = П.situation(СОСТ, {}, [], "")
строка = next((s for s in текст.splitlines() if "нанять в бой" in s), "")
print("  " + строка.strip()[:300])
проверь("цена подписана словом ЦЕНА", "ЦЕНА" in строка)
проверь("атака названа словами", "бьёт на 8" in строка)
проверь("защита названа словами", "от пики" in строка and "от пули" in строка)
проверь("жизни названы словами", "90 жизней" in строка)
проверь("боевые числа НЕ выглядят ценой",
        "atk8" not in строка and "dpike3" not in строка)
проверь("нулевая цена не показана (coal0)", "0 угля" not in строка)
проверь("нулевая ЗАЩИТА показана — это не «неизвестно», а «не держит»",
        "0 от пики" in строка)
проверь("у мушкетёра атака 10, как в lib/unit.script:797", "бьёт на 10" in строка)

print()
print("ПРОВАЛОВ: %d" % ошибок)
raise SystemExit(1 if ошибок else 0)
