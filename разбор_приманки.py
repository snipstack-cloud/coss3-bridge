# -*- coding: utf-8 -*-
"""Разбор пары приманки (задание 234): слот с ключом против слота без него.

    python3 разбор_приманки.py <каталог копии> [<каталог копии> ...]

ЯРЛЫКИ СТОРОН БЕРУТСЯ ИЗ `опыт.json`, А НЕ ИЗ ИМЕНИ ВОЛНЫ. В прямой волне
приманка у слота 0 (`флаги`), в зеркале — у слота 1 (`флаги2`), и трассы зовутся
`coss3_bot.jsonl` и `coss3_bot_P1.jsonl`. Один раз прочитать по имени файла —
и вывод выйдет перевёрнутым; правило 177 про это и написано.

Числа берутся ПОСЛЕДНИМ НЕПУСТЫМ значением поля: последняя запись такта бывает
урезана.
"""
import json
import os
import re
import sys

РУБЕЖИ = (900, 1800)
АРМИЯ = ("mil_inf", "mil_shooters", "mil_cav", "mil_guns")
МАРКЕРЫ = ("ПРИМАНКА", "НАЛЁТ У РАТУШИ", "ОБОРОНА УДАРОМ", "гистерезис",
           "стойка дома", "некого послать")


def такты(путь):
    out = []
    if not os.path.isfile(путь):
        return out
    for строка in open(путь, encoding="utf-8", errors="replace"):
        строка = строка.strip()
        if not строка:
            continue
        try:
            out.append(json.loads(строка))
        except Exception:
            continue
    return out


def ярлыки(каталог):
    """Какой слот несёт приманку — по --strategy в полях флаги/флаги2."""
    п = os.path.join(каталог, "опыт.json")
    д = json.load(open(п, encoding="utf-8")) if os.path.isfile(п) else {}
    out = {}
    for поле, слот in (("флаги", 0), ("флаги2", 1)):
        m = re.search(r"--strategy (\S+)", str(д.get(поле) or ""))
        файл = os.path.basename(m.group(1)) if m else "?"
        out[слот] = ("БЕЗ приманки" if "без_приманки" in файл else "С ПРИМАНКОЙ", файл)
    return д.get("опыт", "?"), out


def текст(r):
    return " ".join(str(r.get(k) or "") for k in
                    ("why", "lesson", "idea", "cause", "march", "critic_hyp"))


def сторона(каталог, слот, подпись):
    файл = "coss3_bot.jsonl" if слот == 0 else "coss3_bot_P1.jsonl"
    стр = такты(os.path.join(каталог, файл))
    тк = [r for r in стр if "finish" not in r and r.get("state")]
    if not тк:
        print("    слот %d (%s): трассы нет" % (слот, подпись))
        return
    концовка = [r.get("finish") for r in стр if "finish" in r]

    def на(gt, поле):
        знач = None
        for r in тк:
            if r["state"].get("gametime", 0) <= gt:
                v = r["state"].get(поле)
                if v not in (None, ""):
                    знач = v
        return знач

    print("    слот %d — %s (%s), тактов %d, конец %s" % (
        слот, подпись[0], подпись[1], len(тк),
        концовка[0] if концовка else "НЕ ДОИГРАНА"))
    for gt in РУБЕЖИ:
        if тк[-1]["state"]["gametime"] < gt - 60:
            continue
        армия = sum(на(gt, f) or 0 for f in АРМИЯ)
        print("       %2d:00  армия %4d | потерял бойцов %4s, крестьян %3s | крестьян %3s" % (
            gt // 60, армия, на(gt, "my_mil_lost"), на(gt, "my_pea_lost"),
            на(gt, "peasants")))
    есть = ", ".join("%s %d" % (м, sum(1 for r in стр if м in текст(r)))
                     for м in МАРКЕРЫ)
    print("       маркеры: " + есть)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for каталог in sys.argv[1:]:
        волна, яр = ярлыки(каталог)
        print("%s  (волна %s)" % (каталог, волна))
        for слот in (0, 1):
            сторона(каталог, слот, яр.get(слот, ("?", "?")))
        бл = os.path.join(каталог, "приманка_блок.log")
        if os.path.isfile(бл):
            текстбл = open(бл, encoding="utf-8", errors="replace").read()
            по_расст = текстбл.count("enemy within")
            по_сроку = текстбл.count("time is up")
            print("    строки блока: взведено %d, спуск по расстоянию %d, по сроку %d" % (
                текстбл.count("retreat armed"), по_расст, по_сроку))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
