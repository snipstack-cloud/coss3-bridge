#!/usr/bin/env python3
"""ФАНТОМ «ждём mil.1» (18.10, §163): в Д7 строка такта несла «живая игра не умеет: TRAIN peasant -1 (§147б: ждём
mil.1) ×3» в 108 тактах с 4:13 до 13:16, а пауза §155 длилась 21 с (4:08 → 4:29). Счётчики `Стратегии` `пропущено`/
`отдано` копятся всю партию, а `ЖиваяСтратегия.ответ` печатал накопленное. Теперь — только разность за такт, и события
правил (`отдано`) вслух. Состояния — Д4 3:59 (пауза) и 6:32 (mil.1 в `upg_doing`), как в `selftest_д4_mil1.py`.

(а) такт паузы: why несёт «правила: §147б пауза крестьян», без счёта команд; (а2) заказ снят — «ждём mil.1» один такт; (б) такт снятия: «правила: §147б крестьяне
снова (mil.1 куплена)» и НИ «ждём mil.1», ни «пауза крестьян»; (в) следующий такт: ничего из §147б; (г) накопленные
счётчики для селфтестов не тронуты.

    python3 selftest_д7_фантом.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ

д4 = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д4_11_10_2_00-12_30.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл

def стратегия():
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"]["пауза_крестьян"] = 1   # 23.10 игрок снял паузу в файле; тест судит правило и ставит ключ сам
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)

def ответ(С, st):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    return С.ответ(copy.deepcopy(st))

при = lambda t: next(s for s in д4 if s["gametime"] >= t)
st_239, st_392 = при(239), при(392)
С = стратегия()

о = ответ(С, st_239); w = о["why"]
проверить("правила: " in w and "§147б пауза крестьян под mil.1" in w and "BALANCE" not in w, f"(а) такт паузы: {w[:300]}")
st_а2 = copy.deepcopy(при(254)); st_а2["gametime"] = 260; st_а2["train_now"] = "pikeman:inf"
о = ответ(С, st_а2); w = о["why"]
проверить("ждём mil.1" in w and "пауза крестьян под" not in w, f"(а2) заказ снят, ярус 1 просит -1: пропуск вслух один раз: {w[:300]}")

st_г = copy.deepcopy(st_392); st_г["train_now"] = "pikeman:inf"
о = ответ(С, st_г); w = о["why"]
проверить("§147б крестьяне снова (mil.1 куплена)" in w and "ждём mil.1" not in w and "пауза крестьян под" not in w,
          f"(б) такт снятия — без фантома: {w[:300]}")

st_в = copy.deepcopy(st_г); st_в["gametime"] += 5; st_в["train_now"] = "peaeng:inf,pikeman:inf"
о = ответ(С, st_в); w = о["why"]
проверить("147б" not in w and "ждём mil.1" not in w, f"(в) следующий такт — тишина по §147б: {w[:300]}")

проверить(С.стр.пропущено.get("TRAIN peasant -1 (§147б: ждём mil.1)", 0) >= 1
          and С.стр.отдано.get("§147б крестьяне снова (mil.1 куплена)", 0) == 1,
          f"(г) накопленные счётчики целы: {dict(С.стр.пропущено)}")

print(f"\nошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
