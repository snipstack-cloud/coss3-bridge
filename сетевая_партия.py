#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""СЕТЕВАЯ ПАРТИЯ (262, слово игрока 6.11): «нужно, чтобы мост видел, что я выбираю в сетевой игре под своим профилем нацию,
и ждал старта игры; дальше управление передаётся боту».

Как это устроено:
  * лобби ведёте вы сами (сетевая игра, свой профиль). Блок цикла (block_gameloop.inc, 262) пишет в пульс `coss3_hb.dat`
    стадию партии (`stage_name`: lobby / loading / started), ваш слот (`myplind`), нацию слота (`my_csid`, `my_cid`),
    готовность, число игроков и кто хост (`server`);
  * этот пускатель читает пульс раз в 2 с, печатает лобби при каждом изменении, кладёт файл открытия для вашего слота
    (ратуша и мельница на первом тике), выбирает стратегию по нации и, как только стадия стала `started` и состояние слота
    пошло, запускает llm_policy тем же набором ключей, что `против_игрока.py` (без --new), с меткой живой партии
    COSS3_VS_LIVE (запрета атаки против человека нет — 259);
  * ОГРАНИЧЕНИЕ ДВИЖКА: блок цикла и приказы блока работают только у ХОСТА лобби (`not _net_IsClient`; приказы идут
    сетевым путём через `blan` у сервера). Если пульс говорит `online 1, server 0` — вы клиент, и мост игру не поведёт:
    создайте лобби сами.

    python сетевая_партия.py --dir "<папка игры>" [--ini против_игрока.ini] [--стратегия файл.json] [--один]
"""
import argparse
import json
import os
import subprocess
import sys
import time

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ЗДЕСЬ)
from coss3_bridge import Bridge, parse_parser_file, ратуша_у_леса  # noqa: E402
import против_игрока as ПИ  # noqa: E402

# Стратегия по нации (sid страны из лобби). Нет своей — польский файл вслух (экономика и бой общие, прокачки по цене).
СТРАТЕГИЯ_ПО_НАЦИИ = {
    "pol": "sim/поиск/польша_судья_по_врагу.json",
    "net": "sim/поиск/ветка_казарма3_качели2_лес_академия2_копить.json",
}
# cid → sid, если лобби пишет только номер (из архива: pol 6, net 13); остальное допишет живая проверка
СИД_ПО_CID = {6: "pol", 13: "net"}
ЗАПАСНАЯ = "sim/поиск/польша_судья_по_врагу.json"


def прочитать_пульс(игра: str) -> dict | None:
    p = os.path.join(игра, "coss3_hb.dat")
    try:
        with open(p, "r", encoding="latin-1") as f:
            d = parse_parser_file(f.read())
        d["_свежесть"] = time.time() - os.path.getmtime(p)
        return d
    except OSError:
        return None


def _и(d: dict, k: str, умолч=None):
    try:
        return int(float(d.get(k)))
    except (TypeError, ValueError):
        return умолч


def _б(d: dict, k: str) -> bool:
    return str(d.get(k) or "").strip().lower() in ("1", "true", "yes", "да")


def лобби(hb: dict) -> dict:
    """Что говорит пульс о лобби: слот, нация (sid и номер), стадия, хост, игроки."""
    cid = _и(hb, "my_cid")
    csid = str(hb.get("my_csid") or "").strip().lower()
    if not csid and cid is not None:
        csid = СИД_ПО_CID.get(cid, "")
    return dict(слот=_и(hb, "myplind"), нация=csid, cid=cid, стадия=str(hb.get("stage_name") or "").strip() or "?",
                имя=str(hb.get("my_name") or "").strip(), готов=_б(hb, "my_ready"), игроков=_и(hb, "players"),
                онлайн=_б(hb, "online"), хост=_б(hb, "server"), gt=_и(hb, "gametime", 0))


def стратегия_для(нация: str, явная: str = "") -> tuple[str, str]:
    """Файл стратегии и слово о выборе."""
    if явная:
        return явная, f"стратегия задана ключом: {явная}"
    if нация in СТРАТЕГИЯ_ПО_НАЦИИ:
        return СТРАТЕГИЯ_ПО_НАЦИИ[нация], f"стратегия по нации {нация}: {СТРАТЕГИЯ_ПО_НАЦИИ[нация]}"
    return ЗАПАСНАЯ, f"для нации {нация or '?'} своей стратегии нет — беру {ЗАПАСНАЯ} (вслух)"


def партия_началась(прежний: dict | None, тек: dict, игра: str) -> bool:
    """Старт: стадия `started`, время идёт и состояние нашего слота свежее 15 с."""
    if тек["стадия"] != "started" or тек["слот"] is None:
        return False
    p = os.path.join(игра, f"coss3_eco_P{тек['слот']}.dat")
    try:
        свеж = time.time() - os.path.getmtime(p)
    except OSError:
        return False
    return свеж < 15 and (прежний is None or прежний["стадия"] != "started" or тек["gt"] < 30)


def строка(л: dict) -> str:
    return (f"стадия {л['стадия']}, ваш слот {л['слот']}, нация {л['нация'] or '?'} (cid {л['cid']}), профиль {л['имя'] or '—'}, "
            f"готов {'да' if л['готов'] else 'нет'}, игроков {л['игроков']}, "
            f"{'хост' if л['хост'] else ('КЛИЕНТ — мост не поведёт, хостите лобби сами' if л['онлайн'] else 'офлайн')}")


def main() -> int:
    ap = argparse.ArgumentParser(description="сетевая партия: лобби ведёт игрок, мост ждёт старта и отдаёт слот боту")
    ap.add_argument("--dir", default=ПИ.ИГРА_ПО_УМОЛЧАНИЮ, help="папка игры")
    ap.add_argument("--ini", default=os.path.join(ЗДЕСЬ, "против_игрока.ini"), help="настройка [бот] (модель, каталог, ключи)")
    ap.add_argument("--стратегия", default="", dest="стратегия", help="файл стратегии; пусто — по нации из лобби")
    ap.add_argument("--каждые", type=int, default=0, dest="каждые")
    ap.add_argument("--один", action="store_true", dest="один", help="одна партия и выход; иначе ждать следующее лобби")
    ap.add_argument("--без-открытия", action="store_true", dest="без_открытия")
    a = ap.parse_args()
    _, бот = ПИ.прочитать(a.ini)
    print(f"сетевая партия: жду пульс {os.path.join(a.dir, 'coss3_hb.dat')} (игра запущена, вы в лобби сетевой игры)")
    прежняя, открытие_для, прежний_текст = None, None, ""
    while True:
        hb = прочитать_пульс(a.dir)
        if hb is None or hb.get("stage_name") is None:
            if hb is not None and hb.get("stage_name") is None:
                print("пульс есть, но без stage_name — в игре стоит блок цикла старше 262: git pull и установка")
                return 1
            time.sleep(2); continue
        л = лобби(hb)
        т = строка(л)
        if т != прежний_текст:
            print(time.strftime("%H:%M:%S"), т); прежний_текст = т
        if л["онлайн"] and not л["хост"]:
            time.sleep(2); прежняя = л; continue
        if л["стадия"] != "started" and л["слот"] is not None and л["нация"]:
            ключ = (л["слот"], л["нация"])
            if открытие_для != ключ and not a.без_открытия:
                файл, _ = стратегия_для(л["нация"], a.стратегия)
                br = Bridge(a.dir, plind=л["слот"])
                near = ратуша_у_леса(os.path.join(ЗДЕСЬ, файл))
                print(f"  файл открытия для слота {л['слот']}: {br.write_opening(near=near)}" + (f" (ратуша у леса {near})" if near else ""))
                открытие_для = ключ
        if партия_началась(прежняя, л, a.dir):
            файл, слово = стратегия_для(л["нация"], a.стратегия)
            print(f"ПАРТИЯ НАЧАЛАСЬ: слот {л['слот']}, нация {л['нация'] or '?'}; {слово}")
            команда = ПИ.команда_политики(a.dir, л["слот"], бот, партий=1, каждые=a.каждые, стратегия=файл)
            среда = dict(os.environ); среда.setdefault("COSS3_KITE", "0.35"); среда["COSS3_VS_LIVE"] = "1"
            if бот["адрес"]:
                среда["OPENROUTER_BASE_URL"] = бот["адрес"]
            if бот["каталог"]:
                os.makedirs(бот["каталог"], exist_ok=True)
                with open(os.path.join(бот["каталог"], "опыт.json"), "w", encoding="utf-8") as f:
                    json.dump({"опыт": "сетевая партия (лобби игрока)", "стратегия": файл, "слот_бота": л["слот"], "нация": л["нация"],
                               "лобби": л, "флаги": " ".join(команда[3:]), "начало": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False, indent=1)
            print("запускаю модель:\n  " + " ".join(команда))
            код = subprocess.call(команда, cwd=ЗДЕСЬ, env=среда)
            print(f"политика вышла с кодом {код}")
            открытие_для = None
            if a.один:
                return код
        прежняя = л
        time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())
