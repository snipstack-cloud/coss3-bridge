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
import json, glob, os, sys
# ПУТЬ ПРОВЕРЯЕМ, А НЕ ДОВЕРЯЕМ. 21.09 каталог со старой версией был удалён, и
# sys.path.insert молча уронил импорт на текущий каталог: инструмент сравнил
# ветку САМУ С СОБОЙ и сказал «отличие ровно одно». Проверка, которая
# оправдывает при пустом входе, хуже отсутствующей.
_путь = os.path.abspath({путь_версии!r})
if not os.path.isfile(os.path.join(_путь, "llm_policy.py")):
    raise SystemExit("НЕТ ВЕРСИИ: " + os.path.join(_путь, "llm_policy.py"))
sys.path.insert(0, _путь)
import llm_policy as L
if os.path.abspath(os.path.dirname(L.__file__)) != _путь:
    raise SystemExit("импортирован ЧУЖОЙ llm_policy: " + L.__file__)
print("ВЗЯТО:", L.__file__, file=sys.stderr)
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
    вывод = subprocess.run([sys.executable, "-c", код], capture_output=True, text=True)
    if вывод.returncode:
        print(вывод.stderr[-2000:])
        raise SystemExit(f"версия {путь_версии} не отработала")
    for строка in вывод.stderr.splitlines():
        if строка.startswith("ВЗЯТО:"):
            print(" ", строка)
    return json.loads(вывод.stdout.strip().splitlines()[-1])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    база, трассы = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else ТРАССЫ)
    if os.path.abspath(база) == os.getcwd():
        raise SystemExit("база и идея — один каталог: сравнивать нечего")
    а = запросы(база, трассы)
    б = запросы(os.getcwd(), трассы)
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
