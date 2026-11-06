#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (262), 6.11: сетевая партия — мост читает из пульса стадию лобби, слот и нацию игрока, ждёт старта и отдаёт слот
боту. Проверяет: разбор пульса, выбор стратегии по нации, признак старта, команду политики без --new, поля блока цикла.
    python3 selftest_сетевая.py
"""
import os, sys, tempfile, time
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К)
import сетевая_партия as СП
import против_игрока as ПИ
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
d = tempfile.mkdtemp()
def пульс(**kw):
    поля = {"realtime": 100, "gametime": 0, "myplind": 1, "victory": 0, "stage": 0, "stage_name": "lobby", "my_cid": 6, "my_csid": "pol",
            "my_name": "Georgy", "my_ready": "true", "online": "true", "server": "true", "players": 2}
    поля.update(kw)
    with open(os.path.join(d, "coss3_hb.dat"), "w", encoding="latin-1") as f:
        f.write("section.begin\n" + "".join(f"   {k} = {v}\n" for k, v in поля.items()) + "section.end\n")
    return СП.прочитать_пульс(d)
л = СП.лобби(пульс())
проверить(л["слот"] == 1 and л["нация"] == "pol" and л["стадия"] == "lobby" and л["хост"] and л["онлайн"] and л["игроков"] == 2 and л["готов"], f"(1) лобби из пульса: {л}")
л2 = СП.лобби(пульс(my_csid="", my_cid=13))
проверить(л2["нация"] == "net", "(1б) нет csid — нация по номеру (13 → net)")
проверить(СП.стратегия_для("pol")[0].endswith("польша_судья_по_врагу.json") and СП.стратегия_для("net")[0].endswith("копить.json"), "(2) стратегия по нации")
проверить(СП.стратегия_для("tur")[0] == СП.ЗАПАСНАЯ and "своей стратегии нет" in СП.стратегия_для("tur")[1], "(2б) чужая нация — запасная вслух")
проверить(СП.стратегия_для("tur", "x.json") == ("x.json", "стратегия задана ключом: x.json"), "(2в) явная стратегия старше нации")
# старт: стадия started + свежее состояние слота
проверить(not СП.партия_началась(None, СП.лобби(пульс()), d), "(3а) в лобби старта нет")
л3 = СП.лобби(пульс(stage_name="started", gametime=4))
проверить(not СП.партия_началась(None, л3, d), "(3б) started, но состояния слота нет — ждём")
open(os.path.join(d, "coss3_eco_P1.dat"), "w").write("section.begin\nsection.end\n")
проверить(СП.партия_началась(СП.лобби(пульс(stage_name="loading")), л3, d), "(3в) started и состояние слота свежее — СТАРТ")
проверить(not СП.партия_началась(л3, СП.лобби(пульс(stage_name="started", gametime=400)), d), "(3г) партия давно идёт (gt 400, прежде тоже started) — повторного старта нет")
л5 = СП.лобби(пульс(online="false", server="false", my_csid="", my_cid=-1))
проверить(л5["стадия"] == "меню", "(1в) главное меню: stage 0 без online/server — «меню», не «lobby» (263)")
л4 = СП.лобби(пульс(server="false"))
проверить(not л4["хост"] and "КЛИЕНТ" in СП.строка(л4), "(4) клиент — вслух «мост не поведёт, хостите лобби»")
# команда политики
бот = dict(модель="m", каждые=15, горизонт=900, подсказка="", запрет="", армия_по_клеткам=0, числа18=0, каталог="", адрес="", ключи="")
к = ПИ.команда_политики("D:\\игра", 1, бот, партий=1, стратегия="sim/поиск/польша_судья_по_врагу.json")
проверить("--new" not in к and "--plind" in к and к[к.index("--plind") + 1] == "1" and "--strategy" in к and "--human" in к and к[к.index("--every") + 1] == "15",
          f"(5) команда политики: без --new, слот 1, стратегия, такт из ini ({' '.join(к[3:12])})")
_g = open(os.path.join(К, "block_gameloop.inc"), encoding="latin-1").read()
проверить(all(x in _g for x in ("'stage_name'", "'my_csid'", "'my_cid'", "'server'", "'online'", "'players'", "gc_map_gamestage_started")), "(6) блок цикла пишет стадию, нацию слота, хоста и игроков в пульс")
print(f"selftest_сетевая: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
