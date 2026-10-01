#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Партия ЧЕЛОВЕК ПРОТИВ БОТА: поднять матч, где бот сидит в СВОЁМ слоте.

    python против_игрока.py                        # по против_игрока.ini
    python против_игрока.py --ini другой.ini
    python против_игрока.py --только-проверка      # ничего не запускать

Зачем отдельный пускатель, а не ключ к llm_policy. До 1.10 человеческий слот
был ОДИН: бот играл за слот 0, врагом стоял нативный ИИ. В партии против живого
игрока человеческих слотов ДВА, и из этого следуют три вещи, которые руками
забываются:

1. **Слот игрока офлайн всегда 0.** Движок иначе локального игрока не сажает
   (`showcustomgame.inc:556` пишет туда имя профиля). Значит бот — слот 1 и
   дальше, и настроить это из меню нельзя: человеческим слот становится только
   по сетевому lanid (`:530-537`). Умеет это лишь команда NEW моста, потому что
   она пишет `gMap.players[...]` ДО загрузки карты.
2. **Слот боту надо ЗАКРЕПИТЬ.** Политика по умолчанию ищет слот по свежести
   состояния, а при двух человеческих слотах оба пишутся каждую игровую секунду
   — поиск мог пересадить модель на слот игрока. Поэтому здесь всегда идёт
   `--plind`.
3. **Квитанцию надо ПРОЧИТАТЬ.** Настройки уезжают до `DoNewGame`, а загрузка
   после него наши поля уже перетирала (25.09, скорость игры вернулась из
   профиля). Поэтому проверяется не желание, а то, что движок отдал назад:
   слот бота должен быть `human=1` и `ai=0`.

Контроль ДО старта, как в `пуск_в_срок.py`: не прошёл — ничего не поднимаем и
говорим, почему. Молчаливый отброс неотличим от бездействия.
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import configparser
import os
import subprocess
import sys
import time

from coss3_bridge import Bridge

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
ИГРА_ПО_УМОЛЧАНИЮ = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"


def _ц(к: configparser.SectionProxy, имя: str, умолчание: int = -1) -> int:
    v = (к.get(имя) or "").strip()
    try:
        return int(v)
    except ValueError:
        return умолчание


def прочитать(путь: str) -> tuple[dict, dict]:
    к = configparser.ConfigParser()
    # Ключи с кириллицей и БЕЗ приведения регистра: configparser по умолчанию
    # опускает имена в нижний регистр, а у нас они и так строчные — но пусть
    # будет явно, чтобы правка ini не ломала чтение.
    к.optionxform = str
    прочитано = к.read(путь, encoding="utf-8")
    if not прочитано:
        raise SystemExit(f"не нашёл настройку {путь}")
    if "партия" not in к or "бот" not in к:
        raise SystemExit(f"в {путь} нужны разделы [партия] и [бот]")
    п, б = к["партия"], к["бот"]
    партия = dict(
        слот=_ц(п, "слот_бота", 1),
        нация=(п.get("нация") or "").strip(),
        mapsize=_ц(п, "размер_карты"),
        res=_ц(п, "ресурсы"),
        peace=_ц(п, "мир"),
        balloon=_ц(п, "шар"),
        cannons=_ц(п, "пушки"),
        capture=_ц(п, "захват"),
        market=_ц(п, "рынок"),
        century18=_ц(п, "век18"),
        speed=_ц(п, "скорость"),
    )
    бот = dict(
        модель=(б.get("модель") or "").strip(),
        каждые=_ц(б, "решение_раз_в", 15),
        горизонт=_ц(б, "горизонт", 900),
        подсказка=(б.get("подсказка") or "").strip(),
        запрет=(б.get("запрет") or "").strip(),
        армия_по_клеткам=_ц(б, "армия_по_клеткам", 0),
        числа18=_ц(б, "числа_18_века", 0),
        каталог=(б.get("каталог") or "").strip(),
    )
    return партия, бот


def контроль(игра: str, партия: dict) -> list[str]:
    """Что должно быть верно ДО того, как что-то поднимать."""
    беды = []
    if партия["слот"] < 1:
        беды.append(f"слот_бота = {партия['слот']}: нельзя, 0 — это слот игрока "
                    "(офлайн движок сажает локального игрока только туда)")
    prg = os.path.join(игра, "data", "scripts", "units", "global.inc", "progress.inc")
    try:
        код = open(prg, "rb").read().decode("latin-1")
    except OSError as e:
        беды.append(f"не читается установленный progress.inc: {e}")
        return беды
    # Мост стоит? И стоит ли в нём то, что нужно этой партии?
    for имя, кусок in (("состояние человеческого слота", "=== BRIDGE HUMAN STATE"),
                       ("команды человеческого слота", "=== BRIDGE HUMAN COMMANDS"),
                       ("петля эпизодов", "=== BRIDGE LOOP"),
                       ("слот бота в NEW", "'botslot'")):
        if кусок not in код:
            беды.append(f"в установленном progress.inc нет: {имя} ({кусок!r}). "
                        "Поставьте мост заново — команда в RESUME.md")
    # События гибели живут в ДРУГОМ файле, и установка без --human-kills их
    # СНИМАЕТ. 29.09 это уже случилось.
    dmg = os.path.join(игра, "data", "scripts", "lib", "miscext2.script")
    try:
        if "br_kills" not in open(dmg, "rb").read().decode("latin-1"):
            беды.append("нет блока событий гибели в lib/miscext2.script — "
                        "установка шла без --human-kills, кто кого убил не запишется")
    except OSError as e:
        беды.append(f"не читается miscext2.script: {e}")
    return беды


def пульс(игра: str) -> str:
    """Контрольная пара: что живо, а что нет. Отвечает за минуту и без установок."""
    def свеж(имя):
        p = os.path.join(игра, имя)
        try:
            return time.time() - os.path.getmtime(p) < 30
        except OSError:
            return None
    gui, hb = свеж("coss3_gui.dat"), свеж("coss3_hb.dat")
    if gui is None and hb is None:
        return "игра не дошла до главного меню — проверка пустая"
    if gui and hb:
        return "живо"
    if gui and not hb:
        return "интерфейс жив, мёртв тик Progress — виноват блок"
    return "неясно: " + f"gui={gui}, hb={hb}"


def main() -> int:
    ap = argparse.ArgumentParser(description="партия человек против бота")
    ap.add_argument("--ini", default=os.path.join(ЗДЕСЬ, "против_игрока.ini"))
    ap.add_argument("--dir", default=ИГРА_ПО_УМОЛЧАНИЮ, help="папка игры")
    ap.add_argument("--только-проверка", action="store_true", dest="только_проверка")
    ap.add_argument("--партий", type=int, default=1, dest="партий")
    a = ap.parse_args()

    партия, бот = прочитать(a.ini)
    print(f"настройка: {a.ini}")
    print(f"  вы — слот 0, бот — слот {партия['слот']}, нация "
          f"{партия['нация'] or 'как в меню'}, карта {партия['mapsize']}")

    беды = контроль(a.dir, партия)
    состояние = пульс(a.dir)
    print(f"  пульс: {состояние}")
    if состояние != "живо":
        беды.append(f"пульса нет: {состояние}. Игра должна быть ЗАПУЩЕНА и "
                    "доведена до главного меню, окно активно — свёрнутая игра "
                    "останавливает симуляцию вместе с блоком")
    if беды:
        print("\nКОНТРОЛЬ НЕ ПРОШЁЛ, ничего не поднимаю:")
        for б in беды:
            print("  -", б)
        return 1
    print("  контроль пройден")
    if a.только_проверка:
        return 0

    br = Bridge(a.dir, plind=партия["слот"])
    br.clear_ack()
    for _ in range(20):
        if br.control("NEW", 0, 0, res=партия["res"], peace=партия["peace"],
                      nation=партия["нация"], balloon=партия["balloon"],
                      cannons=партия["cannons"], capture=партия["capture"],
                      market=партия["market"], century18=партия["century18"],
                      mapsize=партия["mapsize"], speed=партия["speed"],
                      botslot=партия["слот"]):
            break
        time.sleep(1.0)
    else:
        print("NEW не отдан: прежняя команда лежит непрочитанной")
        return 1
    ack = br.wait_ack(timeout=60)
    print(f"квитанция: {ack}")

    # ЧИТАЕМ, А НЕ ВЕРИМ. Поля ставятся до DoNewGame, и загрузка после него наши
    # значения уже перетирала (25.09, скорость игры). Если движок не оставил
    # слот бота человеческим без ИИ — партия пойдёт не та, которую просили.
    плохо = []
    if str(ack.get("done") or "") != "newgame_called":
        плохо.append(f"NEW не дошёл: done = {ack.get('done')!r}")
    if str(ack.get("botslot") or "") != str(партия["слот"]):
        плохо.append(f"блок не принял слот бота: botslot = {ack.get('botslot')!r}")
    if str(ack.get("bot_human") or "").lower() not in ("1", "true"):
        плохо.append(f"слот бота НЕ человеческий: bot_human = {ack.get('bot_human')!r} "
                     "— движок наше поле не сохранил")
    if str(ack.get("bot_ai") or "").lower() in ("1", "true"):
        плохо.append(f"на слоте бота ВКЛЮЧЁН нативный ИИ: bot_ai = {ack.get('bot_ai')!r} "
                     "— он будет отдавать приказы той же армии, что и модель")
    if str(ack.get("my_team") or "") == str(ack.get("bot_team") or ""):
        плохо.append(f"вы и бот в ОДНОЙ команде: my_team = {ack.get('my_team')!r}, "
                     f"bot_team = {ack.get('bot_team')!r}")
    if плохо:
        print("\nПАРТИЯ ПОДНЯЛАСЬ НЕ ТА, модель не запускаю:")
        for б in плохо:
            print("  -", б)
        return 1
    print(f"слот бота {партия['слот']}: человеческий, нативный ИИ выключен, "
          f"команды {ack.get('my_team')} против {ack.get('bot_team')}")

    # Ждём, пока слот бота начнёт писать состояние: карта генерируется, и до
    # этого файла нет вовсе.
    путь = os.path.join(a.dir, f"coss3_eco_P{партия['слот']}.dat")
    до = time.time() + 180
    while time.time() < до:
        try:
            if time.time() - os.path.getmtime(путь) < 10:
                break
        except OSError:
            pass
        time.sleep(2.0)
    else:
        print(f"слот {партия['слот']} состояние не пишет — смотрите, "
              f"создался ли он в партии")
        return 1
    st = br.read_state() or {}
    print(f"слот бота ожил: gt={st.get('gametime')}, крестьян {st.get('peasants')}, "
          f"human={st.get('human')}")

    if бот["каталог"]:
        os.makedirs(бот["каталог"], exist_ok=True)

    команда = [sys.executable, "-u", os.path.join(ЗДЕСЬ, "llm_policy.py"), "--human",
               "--dir", a.dir,
               "--plind", str(партия["слот"]),
               "--model", бот["модель"],
               "--every", str(бот["каждые"]),
               "--horizon", str(бот["горизонт"]),
               "--episodes", str(a.партий)]
    if бот["запрет"]:
        команда += ["--ban", бот["запрет"]]
    if бот["подсказка"]:
        команда += ["--hints", бот["подсказка"]]
    if бот["армия_по_клеткам"]:
        команда += ["--army-cells", "1"]
    if бот["числа18"]:
        команда += ["--c18-numbers", "1"]
    if бот["каталог"]:
        команда += ["--botlog", os.path.join(бот["каталог"], "coss3_bot.jsonl"),
                    "--snaplog", os.path.join(бот["каталог"], "coss3_snap.jsonl"),
                    "--log", os.path.join(бот["каталог"], "coss3_llm.log")]
    # БЕЗ --new: партию мы уже начали сами, выше. С ключом политика начала бы
    # ЕЩЁ одну и смела бы ту, в которой игрок уже стоит.
    print("\nзапускаю модель:\n  " + " ".join(команда) + "\n")
    return subprocess.call(команда, cwd=ЗДЕСЬ)


if __name__ == "__main__":
    raise SystemExit(main())
