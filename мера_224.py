# -*- coding: utf-8 -*-
"""Меры задания 224: размен с ИИ, его крестьяне, удержание, одиночки — по партиям.

    python3 мера_224.py <trace.jsonl> [<trace.jsonl> ...]

Зачем отдельно от series_report.py: тот отвечает «взята ли цель», а мак назвал
до серии четыре своих меры, и три из них в трассе лежат по разным местам.

ВРАГ В КОНТЕЙНЕРЕ — СЛОТ 1. Бот играет слотом 0 против родного ИИ (`p1_ai` 1),
то есть наоборот живым партиям, где игрок был слотом 0. Размен считается
`p1_mil_lost / my_mil_lost`, его крестьяне — `p1_pea_lost`. Перепутать слоты
здесь стоило бы перевёрнутого вывода.

Числа берутся ПОСЛЕДНИМ НЕПУСТЫМ значением поля: последняя запись такта бывает
урезана, и прямое чтение `[-1]` даёт None.
"""
import json
import sys

ПОЛЯ_ТЕКСТА = ("why", "lesson", "idea", "cause", "march", "critic_hyp")
МАРКЕРЫ = ("ОДИНОЧКИ", "СУДЬЯ УДАРА", "ВСТРЕЧА", "ПАЧКА УДАРА", "DEFEND 0/0")


def такты(путь):
    out = []
    for строка in open(путь, encoding="utf-8", errors="replace"):
        строка = строка.strip()
        if not строка:
            continue
        try:
            out.append(json.loads(строка))
        except Exception:
            continue
    return out


def партии(строки):
    """Партия кончается записью finish; у незавершённой её нет."""
    out, текущая = [], []
    for r in строки:
        текущая.append(r)
        if "finish" in r:
            out.append(текущая)
            текущая = []
    if текущая:
        out.append(текущая)
    return out


def текст(r):
    """Весь текст такта ОДНИМ РЕГИСТРОМ.

    5.11: правило `ПОДТОК НЕ В БОЙ` пишется в трассе заглавными, а искал я его
    строчными — и получил ноль на всех четырёх копиях там, где срабатываний было
    19, 38, 9 и 46. Из этого нуля вышел ложный вывод «пара негодна, виноват
    горизонт», и снимать его пришлось маку. Сравнение регистра здесь — не
    удобство, а защита от того же.
    """
    return " ".join(str(r.get(k) or "") for k in ПОЛЯ_ТЕКСТА).upper()


def последнее(тк, поле):
    for r in reversed(тк):
        v = r["state"].get(поле)
        if v not in (None, ""):
            return v
    return None


def разбор(путь):
    пп = партии(такты(путь))
    for i, п in enumerate(пп, 1):
        тк = [r for r in п if "finish" not in r and r.get("state")]
        if not тк:
            continue
        наши = последнее(тк, "my_mil_lost") or 0
        его = последнее(тк, "p1_mil_lost") or 0
        размен = (его / наши) if наши else None
        держ = sum(1 for r in тк if (r["state"].get("my_held") or 0) > 0)
        концовка = [r.get("finish") for r in п if "finish" in r]
        print("  партия %d: gt до %-5d тактов %-4d %s" % (
            i, тк[-1]["gt"], len(тк), концовка[0] if концовка else "НЕ ДОИГРАНА"))
        print("     размен %s (наши %s, его %s) | его крестьян убито %s | наших крестьян потеряно %s" % (
            ("%.2f" % размен) if размен is not None else "— (наши потери 0)",
            наши, его, последнее(тк, "p1_pea_lost"), последнее(тк, "my_pea_lost")))
        print("     my_held > 0 в %d из %d тактов (%.0f %%) | армия к концу %s | его крестьян осталось %s" % (
            держ, len(тк), 100.0 * держ / len(тк),
            sum(последнее(тк, f) or 0 for f in ("mil_inf", "mil_shooters", "mil_cav", "mil_guns")),
            последнее(тк, "p1_peasants")))
        print("     маркеры: " + ", ".join(
            "%s %d" % (м, sum(1 for r in п if м in текст(r))) for м in МАРКЕРЫ))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for путь in sys.argv[1:]:
        print(путь)
        разбор(путь)
    return 0


if __name__ == "__main__":
    sys.exit(main())
