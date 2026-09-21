# -*- coding: utf-8 -*-
"""Отличается ли идея от базы РОВНО ОДНИМ — своим ключом.

Правило проекта: идея = одна строка подсказки или один флаг, всё остальное
совпадает с базой. Когда правка тронула сотни строк моста, верить этому на
слово нельзя: код мог изменить обычный запрос незаметно, и тогда серия меряла
бы две разницы вместо одной, а выглядела бы законной.

Проверка прямая: берём НАСТОЯЩИЕ состояния отыгранных партий, строим на них
`situation` обеими версиями моста и сравниваем тексты дословно.

    git worktree add /tmp/база <sha моста базы>
    python3 check_same_as_base.py /tmp/база [<каталог с трассами>]

Расхождение печатается первым отличающимся куском, а не одним «не совпало»:
искать его глазами по семи тысячам символов — работа на полчаса.

ОГРАНИЧЕНИЕ, которое надо знать. Проверяется ОБЫЧНЫЙ такт при выключенном
ключе — то есть ровно то, чем идея обязана совпадать с базой. Поведение
включённого ключа этим не проверяется никак, и не должно: в том и смысл идеи,
что она ведёт себя иначе.
"""
import difflib, glob, hashlib, json, os, subprocess, sys

ТРАССЫ = '/Users/gs/coss3-res/2026-09-21/base24'
ШАГ = 17          # берём каждое N-е состояние: нужен разброс, а не все подряд
СКОЛЬКО = 25


def запросы(путь_версии, трассы):
    """Тексты `situation` этой версии моста — отдельным процессом.

    Отдельным нарочно: два llm_policy в одном процессе не уживаются, у модуля
    есть глобальные счётчики (РЕСУРСЫ_ИСТОРИЯ и прочие), и второй импорт
    молча пользовался бы состоянием первого.
    """
    код = f'''
import json, glob, sys
sys.path.insert(0, {путь_версии!r})
import llm_policy as L
состояния = []
for ф in sorted(glob.glob({трассы!r} + "/*/coss3_bot.jsonl")):
    for строка in open(ф, encoding="utf-8"):
        строка = строка.strip()
        if not строка:
            continue
        x = json.loads(строка)
        if "finish" in x:
            continue
        st = x.get("state")
        if isinstance(st, dict) and "gametime" in st:
            состояния.append(st)
готово = []
for st in состояния[::{ШАГ}][:{СКОЛЬКО}]:
    L.РЕСУРСЫ_ИСТОРИЯ.clear()
    готово.append(L.situation(st, st, [], "", None, [], False, [], {{}}, [], [], "", ""))
print(json.dumps(готово, ensure_ascii=False))
'''
    # ENCODING И ENV ЯВНО. Инструмент писан на маке, где вывод и так utf-8;
    # на Windows subprocess берёт cp1252, и первая же кириллица в запросе
    # роняет проверку UnicodeDecodeError, а поверх неё — невнятным
    # «NoneType has no attribute strip». 21.09 это стоило запуска.
    среда = dict(os.environ, PYTHONIOENCODING="utf-8")
    вывод = subprocess.run([sys.executable, "-c", код], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           env=среда)
    if вывод.returncode:
        print(вывод.stderr[-2000:])
        raise SystemExit(f"версия {путь_версии} не отработала")
    return json.loads(вывод.stdout.strip().splitlines()[-1])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    база, трассы = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else ТРАССЫ)
    а = запросы(база, трассы)
    б = запросы(".", трассы)
    if len(а) != len(б):
        raise SystemExit(f"разное число запросов: {len(а)} против {len(б)}")
    плохих = 0
    for i, (х, у) in enumerate(zip(а, б)):
        if х == у:
            continue
        плохих += 1
        print(f"\n--- запрос {i}: РАЗОШЁЛСЯ "
              f"({hashlib.md5(х.encode()).hexdigest()[:8]} против "
              f"{hashlib.md5(у.encode()).hexdigest()[:8]})")
        for строка in list(difflib.unified_diff(х.splitlines(), у.splitlines(),
                                                "база", "идея", lineterm="", n=1))[:20]:
            print("   " + строка)
    print(f"\nзапросов сверено: {len(а)}, разошлось: {плохих}")
    if плохих:
        print("ОТЛИЧИЕ НЕ ОДНО: при ВЫКЛЮЧЕННОМ ключе мост говорит не то же, "
              "что база. Сравнение будет мерить две разницы.")
        raise SystemExit(1)
    print("ОТЛИЧИЕ РОВНО ОДНО: при выключенном ключе запрос дословно тот же, "
          "что у базы")


if __name__ == "__main__":
    main()
