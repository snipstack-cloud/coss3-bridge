#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (259), 6.11: слово игрока «вообще не должно быть запрета атаки для игр с человеком». Против живого игрока
(`p<n>_human` и метка среды COSS3_VS_LIVE от против_игрока.py) `без_атаки_до` не действует, срок похода — `выход_к_человек` 180;
в контейнере (нет метки) и против ИИ — как было.
    python3 selftest_без_атаки_человек.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
def стратегия(доп=None):
    д = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8")); д["итог"].update(доп or {})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f: json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
st = {"gametime": 300, "my_cx": 3, "my_cy": 3, "p0_human": 0, "p1_human": 1, "p1_enemy": 1, "враг_слот": 1, "p1_army": 0, "mil_inf": 30, "centers": 1}
удар = [{"cmd": "ATTACK", "count": 30, "target": "cell", "cx": 15, "cy": 15}]   # дом без obuild — (8,8); 15 дальше радиуса 5
проверить(float(стратегия().п.get("без_атаки_до", 0)) == 720, "(0) живой файл: без_атаки_до 720 (слово 30.10 про бота) — ключ не трогаем, снимает флаг живой партии")
os.environ["COSS3_VS_LIVE"] = "1"
из, w = стратегия()._без_атаки(copy.deepcopy(удар), dict(st))
проверить(len(из) == 1 and "противник человек" in w and "запрета атаки" in w, f"(1) живой игрок: ATTACK на 5:00 проходит, вслух один раз ({w[:80]})")
С = стратегия(); С._без_атаки(copy.deepcopy(удар), dict(st)); из2, w2 = С._без_атаки(copy.deepcopy(удар), dict(st))
проверить(len(из2) == 1 and w2 == "", "(1б) второй такт — проходит молча")
из3, w3 = стратегия({"без_атаки_и_человек": 1})._без_атаки(copy.deepcopy(удар), dict(st))
проверить(len(из3) == 0 and "без атаки до 720" in w3, "(2) ключ без_атаки_и_человек 1 — прежний запрет и против человека")
из4, w4 = стратегия()._без_атаки(copy.deepcopy(удар), dict(st, p1_human=0))
проверить(len(из4) == 0, "(3) противник — родной ИИ: запрет действует")
os.environ.pop("COSS3_VS_LIVE", None)
из5, w5 = стратегия()._без_атаки(copy.deepcopy(удар), dict(st))
проверить(len(из5) == 0 and "без атаки до 720" in w5, "(4) без метки среды (контейнер бот-против-бота, оба слота «человеческие») — запрет как был")
_src = open(os.path.join(К, "strategy_live.py"), encoding="utf-8").read(); _pl = open(os.path.join(К, "против_игрока.py"), encoding="utf-8").read()
проверить('"выход_к_человек", 180' in _src and 'COSS3_VS_LIVE' in _src, "(5) выход_к против живого игрока — выход_к_человек 180 по той же метке")
проверить('среда["COSS3_VS_LIVE"] = "1"' in _pl, "(6) против_игрока.py ставит метку живой партии")
print(f"selftest_без_атаки_человек: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
