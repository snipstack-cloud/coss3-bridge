#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Очередь ночных разборов: по ОДНОЙ партии на идею, свежие вперёд.

    python3 очередь_разборов.py [--до 03:45] [--сколько 40]

Почему вширь, а не вглубь: партия разбирается около восьми минут, все 451 это
шестьдесят часов. За ночь пройдёт полтора-два десятка, и полезнее увидеть
двадцать РАЗНЫХ идей по разу, чем одну идею двадцать раз.

Очередь ВОЗОБНОВЛЯЕМАЯ: разобранное помечено в `разборы/реестр.tsv`, и второй
запуск продолжит с того места, где кончился первый. Часы (`--до`) — чтобы
прогон сам остановился к утру, а не был прибит на середине партии.
"""
import os, re, subprocess, sys, time
from datetime import datetime

КОРЕНЬ = os.path.dirname(os.path.abspath(__file__))
РЕЕСТР = os.path.join(КОРЕНЬ, "разборы", "реестр.tsv")
РЕЗ = os.path.expanduser("~/coss3-res")

до = "03:45"
сколько = 40
арг = sys.argv[1:]
for ключ in ("--до", "--сколько"):
    if ключ in арг:
        i = арг.index(ключ)
        знач = арг[i + 1]
        if ключ == "--до":
            до = знач
        else:
            сколько = int(знач)

часы, минуты = (int(x) for x in до.split(":"))
крайний = datetime.now().replace(hour=часы, minute=минуты, second=0, microsecond=0)

разобрано = set()
if os.path.exists(РЕЕСТР):
    for строка in open(РЕЕСТР, encoding="utf-8"):
        разобрано.add(строка.split("\t")[0])

# По одной партии на идею: <дата>/<идея>/<копия>/coss3_bot.jsonl -> берём первую копию
идеи = {}
for корень, папки, файлы in os.walk(РЕЗ):
    if "coss3_bot.jsonl" not in файлы:
        continue
    путь = os.path.join(корень, "coss3_bot.jsonl")
    части = путь.split(os.sep)
    if len(части) < 4:
        continue
    дата, идея, копия = части[-4], части[-3], части[-2]
    if not re.match(r"20\d\d-\d\d-\d\d", дата):
        continue
    ключ = (дата, идея)
    if ключ not in идеи or копия < идеи[ключ][0]:
        идеи[ключ] = (копия, путь)

очередь = [п for (дата, идея), (к, п) in sorted(идеи.items(), reverse=True)
           if os.path.relpath(п, os.path.expanduser("~")) not in разобрано]
print(f"идей всего {len(идеи)}, уже разобрано {len(разобрано)}, "
      f"в очереди {len(очередь)}, крайний срок {крайний:%H:%M}", flush=True)

сделано = 0
for путь in очередь[:сколько]:
    if datetime.now() >= крайний:
        print(f"время вышло ({крайний:%H:%M}), остановлено на {сделано} партиях", flush=True)
        break
    т = time.time()
    print(f"\n=== {сделано + 1}. {os.path.relpath(путь, РЕЗ)}  "
          f"{datetime.now():%H:%M}", flush=True)
    r = subprocess.run([sys.executable, os.path.join(КОРЕНЬ, "разбор_трассы.py"),
                        путь, "--факты"], capture_output=True, text=True)
    хвост = [с for с in (r.stdout or "").splitlines() if "находок" in с or "модель" in с]
    print("    " + " | ".join(хвост) if хвост else "    " + (r.stderr or "")[-200:],
          flush=True)
    сделано += 1
    print(f"    {time.time() - т:.0f} с", flush=True)
print(f"\nГОТОВО: разобрано {сделано} партий")
