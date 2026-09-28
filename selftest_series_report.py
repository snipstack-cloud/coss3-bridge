# -*- coding: utf-8 -*-
"""series_report: взятая цель зовётся 'win', и счёт обязан её видеть.

Повод, 28.09. Инструмент считал цель по `исход == "цель"` — метке компьютерного
слота, — а `Bridge.outcome` отдаёт `'win'`/`'lose'`/`''`, и в трассу это идёт как
есть. Значит строка «ИТОГО: цель N из M» печатала НОЛЬ и там, где партия
выиграна. Нашлось на серии `auto_upgrade`: у идеи и у базы по одной победе в
записи `finish`, а отчёт в обоих плечах говорил «0 из 3» — то есть главное число
отчёта врало, и врало давно.

Это ложный ноль ровно того класса, о котором предупреждает скилл разбора:
считаем по полю, которого в данных нет в таком виде, получаем чистый ноль и
делаем вывод. Поэтому здесь синтетическая трасса с `finish: win` — и проверка,
что счёт её видит.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

беды = []


def проверка(имя, условие, пояснение=""):
    if условие:
        print("  ОК    " + имя)
    else:
        беды.append(имя)
        print("  ПЛОХО " + имя + (" — " + str(пояснение)[:300] if пояснение else ""))


ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
ИСХОДНИК = io.open(os.path.join(ЗДЕСЬ, "series_report.py"), encoding="utf-8").read()

проверка("счёт цели принимает 'win'", '"win"' in ИСХОДНИК and 'э["исход"] in (' in ИСХОДНИК,
         "сравнение с одной меткой 'цель' даёт ложный ноль на победах")
проверка("прежняя метка тоже принимается — старые трассы не теряем",
         '"цель"' in ИСХОДНИК)


def трасса(путь, исход):
    """Две записи такта и запись конца — этого хватает, чтобы счёт сработал."""
    with io.open(путь, "w", encoding="utf-8") as f:
        for gt in (10, 300):
            f.write(json.dumps({"gt": gt, "cmds": [], "state": {
                "gametime": gt, "peasants": 20, "mil_inf": 5, "mil_shooters": 0,
                "p1_peasants": 18}}, ensure_ascii=False) + "\n")
        f.write(json.dumps({"gt": 476, "finish": исход}, ensure_ascii=False) + "\n")


with tempfile.TemporaryDirectory() as врем:
    идея = os.path.join(врем, "идея")
    for копия, исход in (("1", "win"), ("2", "горизонт"), ("3", "lose")):
        os.makedirs(os.path.join(идея, копия))
        трасса(os.path.join(идея, копия, "coss3_bot.jsonl"), исход)
    р = subprocess.run([sys.executable, os.path.join(ЗДЕСЬ, "series_report.py"), идея],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    вывод = (р.stdout or "") + (р.stderr or "")
    проверка("инструмент отработал", р.returncode == 0, вывод[-200:])
    проверка("одна победа из трёх посчитана", "цель 1 из 3" in вывод,
             [с for с in вывод.split("\n") if "ИТОГО" in с])
    проверка("проигрыш и горизонт за цель не считаются",
             "цель 1 из 3" in вывод and "цель 2" not in вывод and "цель 3" not in вывод)

print()
if беды:
    print(f"ПЛОХО: {len(беды)} — " + "; ".join(беды))
    raise SystemExit(1)
print("все проверки прошли")
