# -*- coding: utf-8 -*-
"""Убито крестьян врага НАМИ, за вычетом голодных смертей.

Зачем. Поле p<n>_pea_lost - это ПОТЕРИ врага по ЛЮБОЙ причине: движок
увеличивает gPlayer[pl].stat.killed у ВЛАДЕЛЬЦА уничтоженного юнита
(_unit_RemoveObjFromPlayerCounters, lib/unit.script:3869). Когда у врага
кончается еда, его крестьяне мрут сами, и это ложилось в нашу меру: по 29
свежим прогонам 23-24.09 первая гибель в 28 случаях приходится на 236-256 с
ровно при нулевой еде врага, когда наша армия ещё дома.

Правило счёта здесь ровно то же, что в мосту с 24.09: прирост pea_lost,
случившийся в такте с нулевой едой врага, - голодный, остальное наше.

Запуск:
    python starve_report.py <путь к coss3_snap.jsonl или папке>...

Папка обходится вглубь: можно дать целую серию или целый день.
"""
import io, json, os, sys


def счесть(путь):
    """(всего, голод, чисто, первая_гибель_с, еда_при_первой) по одному снимку."""
    было, голод, первая, еда_при = 0, 0, None, None
    for строка in io.open(путь, encoding="utf-8", errors="replace"):
        строка = строка.strip()
        if not строка:
            continue
        try:
            r = json.loads(строка)
        except ValueError:
            continue
        pl, еда = r.get("p1_pea_lost"), r.get("p1_food")
        if pl is None:
            continue
        try:
            pl = int(float(pl))
        except (TypeError, ValueError):
            continue
        try:
            еда = int(float(еда)) if еда is not None else None
        except (TypeError, ValueError):
            еда = None
        прирост = pl - было
        if прирост > 0:
            if первая is None:
                первая, еда_при = r.get("gametime"), еда
            if еда == 0:
                голод += прирост
        # Откат вниз - новая партия, а не отрицательные потери.
        было = pl if прирост >= 0 else pl
    return было, голод, max(0, было - голод), первая, еда_при


def снимки(пути):
    for п in пути:
        if os.path.isdir(п):
            for корень, _, файлы in os.walk(п):
                for ф in файлы:
                    if ф == "coss3_snap.jsonl":
                        yield os.path.join(корень, ф)
        elif os.path.basename(п) == "coss3_snap.jsonl" or п.endswith(".jsonl"):
            yield п


def main(argv):
    пути = argv[1:] or ["."]
    строки = []
    for ф in sorted(снимки(пути)):
        всего, голод, чисто, первая, еда_при = счесть(ф)
        имя = os.path.dirname(ф).replace(os.sep, "/")
        имя = "/".join(имя.split("/")[-3:])
        строки.append((имя, всего, голод, чисто, первая, еда_при))
    if not строки:
        print("снимков не найдено (ищется coss3_snap.jsonl)")
        return 1
    print("%-28s %7s %7s %7s %9s %9s" % (
        "прогон", "всего", "голод", "НАШИХ", "1-я, с", "еда тогда"))
    for имя, всего, голод, чисто, первая, еда_при in строки:
        print("%-28s %7d %7d %7d %9s %9s" % (
            имя, всего, голод, чисто,
            "-" if первая is None else первая,
            "-" if еда_при is None else еда_при))
    ч = [с[3] for с in строки]
    г = [с[2] for с in строки]
    ч_сорт = sorted(ч)
    медиана = ч_сорт[len(ч_сорт) // 2]
    print()
    print("прогонов %d; наших убийств: сумма %d, медиана %d; голодных всего %d"
          % (len(строки), sum(ч), медиана, sum(г)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
