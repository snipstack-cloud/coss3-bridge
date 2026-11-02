#!/usr/bin/env python3
"""БОТ ПРОТИВ БОТА (2.11): `llm_policy._второй_бот` и поле идеи `флаги2`.

Слово игрока: «двух ботов с разной постройкой — только чтобы это не нарушило бот против ИИ и бот против человека».
Второй бот запускается ТОЛЬКО при непустом `флаги2` в `опыт.json` И `COSS3_MATCH_AI=-1`; иначе функция ничего не
делает и слот не трогает. Запуск процесса подменён — проверяются условия и аргументы второго бота.
    python3 selftest_бот_против_бота.py"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm_policy as L  # noqa: E402

ошибок = 0


def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл


запуски = []


class _Поддельный:
    def __init__(self, argv, **kw):
        запуски.append((argv, kw))

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


subprocess.Popen = _Поддельный


def случай(опыт, ai, ребёнок=False):
    запуски.clear()
    d = tempfile.mkdtemp()
    if опыт is not None:
        json.dump(опыт, open(os.path.join(d, "опыт.json"), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(d, "world.md"), "w").write("мир")
    a = argparse.Namespace(plind=None, botlog=os.path.join(d, "coss3_bot.jsonl"), snaplog=os.path.join(d, "coss3_snap.jsonl"),
                           log=os.path.join(d, "coss3_llm.log"), lessons="lessons.txt", world=os.path.join(d, "world.md"))
    os.environ.pop("COSS3_BOT2_CHILD", None)
    if ai is None:
        os.environ.pop("COSS3_MATCH_AI", None)
    else:
        os.environ["COSS3_MATCH_AI"] = ai
    if ребёнок:
        os.environ["COSS3_BOT2_CHILD"] = "1"
    sys.argv = ["llm_policy.py", "--human", "--strategy", "sim/поиск/база.json", "--botlog", a.botlog, "--snaplog", a.snaplog,
                "--log", a.log, "--world", a.world, "--horizon", "1800"]
    р = L._второй_бот(a)
    return р, a, d


р, a, _ = случай(None, "3")
проверить(р is None and a.plind is None and not запуски, "(1) нет опыт.json — ничего, слот не тронут")
р, a, _ = случай({"опыт": "x", "флаги2": ""}, "3")
проверить(р is None and a.plind is None and not запуски, "(2) бот против ИИ без флаги2 — как было")
р, a, _ = случай({"опыт": "x", "флаги2": ""}, "-1")
проверить(р is None and a.plind is None and not запуски, "(3) бот против человека (AI=-1) без флаги2 — как было")
р, a, d = случай({"опыт": "x", "флаги2": "--strategy sim/поиск/второй.json"}, "3")
проверить(р is not None and a.plind == 0 and len(запуски) == 1, "(5) флаги2 — второй бот запущен (слот 1 send.py отдаёт мосту), этот на слоте 0")
if запуски:
    argv = запуски[0][0][3:]
    проверить(argv[argv.index("--plind") + 1] == "1", f"(6) второй — слот 1")
    проверить(argv[-2:] == ["--strategy", "sim/поиск/второй.json"], "(7) флаги2 в конце — перебивают стратегию первого")
    проверить(argv.count("--botlog") == 1 and argv[argv.index("--botlog") + 1].endswith("coss3_bot_P1.jsonl")
              and argv[argv.index("--snaplog") + 1].endswith("coss3_snap_P1.jsonl")
              and argv[argv.index("--log") + 1].endswith("coss3_llm_P1.log")
              and argv[argv.index("--world") + 1].endswith("world_P1.md")
              and argv[argv.index("--lessons") + 1].endswith("lessons_P1.txt"), "(8) у второго свои файлы, по одному разу")
    проверить(os.path.exists(os.path.join(d, "world_P1.md")), "(9) мир второго — копия мира первого")
    проверить(запуски[0][1]["env"].get("COSS3_BOT2_CHILD") == "1", "(10) второй помечен — третьего не запустит")
р, a, _ = случай({"опыт": "x", "флаги2": "--strategy sim/поиск/второй.json"}, "-1", ребёнок=True)
проверить(р is None and not запуски, "(11) внутри второго бота третий не запускается")
# send.py: botslot только при флаги2
import send as S  # noqa: E402
for опыт, ждём, что in ((None, False, "(12) send.py: нет опыт.json — botslot не шлётся"),
                       ({"флаги2": ""}, False, "(13) send.py: пустое флаги2 — botslot не шлётся"),
                       ({"флаги2": "--strategy x.json"}, True, "(14) send.py: флаги2 — botslot 1")):
    d = tempfile.mkdtemp()
    if опыт is not None:
        json.dump(опыт, open(os.path.join(d, "опыт.json"), "w", encoding="utf-8"), ensure_ascii=False)
    os.environ["COSS3_IO"] = d
    проверить(S.второй_бот_в_опыте() == ждём, что)
print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
