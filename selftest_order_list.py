# -*- coding: utf-8 -*-
"""СПИСОК ПРИКАЗОВ В ФАЙЛЕ (4.10, §78 мака): правка блока + сторона python.

Что проверяется здесь (блок проверяется живой игрой, а не отсюда):

1. `attack_many` пишет `orders = N` и ключи каждого приказа с префиксом `<i>_`;
2. плоские ключи ПЕРВОГО приказа остаются — старый блок в игре прочитает его как
   прежде, а остальные молча не увидит. Это не изящество, а совместимость: ровно
   так 16.09 приезжал `mode`;
3. проверки у списка и у одиночного приказа ОДНИ И ТЕ ЖЕ (общий `_приказ`):
   клетка вне сетки отвергает весь файл, а не уезжает в него;
4. `retreat` с целью-клеткой в списке живёт (правка 3.10 про «к своим»);
5. в блоке есть цикл по приказам, имя группы несёт номер приказа, и бойца два
   приказа одного такта не делят.

    python selftest_order_list.py
"""
import os
import re
import sys
import tempfile

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
if ЗДЕСЬ not in sys.path:
    sys.path.insert(0, ЗДЕСЬ)

import coss3_bridge as CB

беды = []


def поля(текст: str) -> dict:
    из = {}
    for s in текст.splitlines():
        m = re.match(r"\s*([A-Za-z_0-9]+)\s*=\s*(.*?)\s*$", s)
        if m:
            из[m.group(1)] = m.group(2)
    return из


with tempfile.TemporaryDirectory() as кат:
    br = CB.Bridge(кат, plind=1)

    # --- 1-2. список из двух приказов -------------------------------------
    ок = br.attack_many([
        {"count": 10, "target": "army", "mode": "engage"},
        {"count": 200, "target": "cell", "mode": "retreat", "cx": 6, "cy": 7},
    ])
    if not ок:
        беды.append("attack_many вернул False на двух годных приказах")
    else:
        п = поля(open(br.atk_path, encoding="latin-1").read())
        if п.get("orders") != "2":
            беды.append(f"нет orders = 2, есть {п.get('orders')!r}")
        # приказ 0
        for к, v in (("0_count", "10"), ("0_target", "army"), ("0_mode", "engage")):
            if п.get(к) != v:
                беды.append(f"{к} = {п.get(к)!r}, ждали {v!r}")
        # приказ 1
        for к, v in (("1_count", "200"), ("1_target", "cell"), ("1_mode", "retreat"),
                     ("1_cx", "6"), ("1_cy", "7")):
            if п.get(к) != v:
                беды.append(f"{к} = {п.get(к)!r}, ждали {v!r}")
        # плоские ключи первого приказа — для старого блока
        for к, v in (("count", "10"), ("target", "army"), ("mode", "engage")):
            if п.get(к) != v:
                беды.append(f"плоский {к} = {п.get(к)!r}, ждали {v!r} (старый блок "
                            f"читает только их)")
        os.unlink(br.atk_path)

    # --- 3. негодная клетка отвергает ВЕСЬ файл ---------------------------
    if br.attack_many([{"count": 10, "target": "army"},
                       {"count": 10, "target": "cell", "cx": 99, "cy": 0}]):
        беды.append("приказ с клеткой вне сетки уехал в списке — проверки списка "
                    "и одиночного приказа разошлись")
    if os.path.exists(br.atk_path):
        беды.append("файл приказа написан, хотя список негоден")

    # --- 4. одиночный путь не изменился -----------------------------------
    if not br.attack(9, "cell", mode="retreat", cx=3, cy=4):
        беды.append("одиночный attack (retreat в клетку) перестал работать")
    else:
        п = поля(open(br.atk_path, encoding="latin-1").read())
        if п.get("orders") != "1" or п.get("0_target") != "cell" or п.get("target") != "cell":
            беды.append(f"одиночный приказ пишется не так: {п}")
        os.unlink(br.atk_path)

    # --- 5. пустой список ничего не пишет ---------------------------------
    if br.attack_many([]):
        беды.append("пустой список приказов не должен уходить в игру")

    # --- 6. ГРУППЫ (§78): номер уезжает, приказ без count живёт только с ним
    if not br.attack_many([
            {"count": 20, "target": "cell", "mode": "move", "cx": 9, "cy": 7, "group": 1},
            {"count": 0, "target": "home", "mode": "retreat", "group": 2}]):
        беды.append("список с номерами групп не ушёл")
    else:
        п = поля(open(br.atk_path, encoding="latin-1").read())
        if п.get("0_group") != "1" or п.get("1_group") != "2":
            беды.append(f"номера групп не уехали: {п}")
        if п.get("1_count") != "0":
            беды.append("приказ существующей группе должен идти с count 0 — "
                        "тогда блок берёт запомненных, а не отбирает заново")
        os.unlink(br.atk_path)
    # Приказ без группы и без бойцов не берёт никого — он бессмыслен.
    if br.attack_many([{"count": 0, "target": "home", "mode": "retreat"}]):
        беды.append("приказ с count 0 и без группы ушёл в игру")
    if os.path.exists(br.atk_path):
        os.unlink(br.atk_path)

# --- 6. то, что должно стоять в БЛОКЕ --------------------------------------
# Сам блок проверяется живой игрой (контейнер для .inc негоден), но его форму
# можно прочитать здесь — и не узнать потом, что цикла в установленном файле нет.
inc = open(os.path.join(ЗДЕСЬ, "block_hcmd.inc"), encoding="latin-1").read()
для_каждого = [
    ("цикл по приказам", "for haoi := 0 to haon-1 do"),
    ("число приказов из файла", "ParserGetIntValueByKeyByHandle(hah, 'orders')"),
    ("префикс ключей", "hapre := IntToStr(haoi) + '_'"),
    ("имя группы с номером приказа", "+ '_' + IntToStr(haoi)"),
    ("занятые бойцы не делятся", "gTmpIntList.Add(gIntegerList.Get(hak))"),
    ("ключи читаются с префиксом", "hapre + 'count'"),
    # Группы (§78): номер читается, состав запоминается в парсере и берётся из него.
    ("номер группы из приказа", "hapre + 'group'"),
    ("приказ существующей группе", "var hagold : Boolean = (hagid > 0) and (hawant <= 0)"),
    ("состав группы в парсере", "ParserCreate('br_hgrp')"),
    ("состав группы читается", "ParserSelectByKey('br_hgrp')"),
    ("погибшие не берутся", "if (not TObj(haghp).bdead) then"),
    ("своё имя у номерной группы", "'coss3_grp_' + IntToStr(hagid)"),
]
for имя, кусок in для_каждого:
    if кусок not in inc:
        беды.append(f"в block_hcmd.inc нет: {имя} ({кусок!r})")
# Кириллица в .inc смертельна: установщик пишет latin-1.
for n, s in enumerate(inc.splitlines(), 1):
    if any(ord(c) > 127 for c in s):
        беды.append(f"block_hcmd.inc:{n} — не-ASCII в блоке")
        break

if беды:
    print("ПЛОХО:")
    for б in беды:
        print("  -", б)
    raise SystemExit(1)
print("ХОРОШО: файл приказа несёт список, плоские ключи первого на месте, "
      "проверки общие, и в блоке есть цикл с префиксом и своим именем группы")
