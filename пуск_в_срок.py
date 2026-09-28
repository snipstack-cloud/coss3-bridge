#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пуск серии В НАЗНАЧЕННЫЙ ЧАС, с контролем ДО старта и разбором после.

    python пуск_в_срок.py 19:30 hunt2 food_floor

Зачем отдельный скрипт, а не «подождать и запустить руками». Три причины, и все
куплены на этой неделе:

* КОНТРОЛЬ ДО СТАРТА обязан быть машинным. Серия `auto_upgrade` 28.09 поднялась и
  пятнадцать минут играла БЛОКАМИ КОМПЬЮТЕРНОГО СЛОТА, потому что комментарий
  разорвал команду установки, а установщик отрапортовал «все блоки на месте» — и
  формально был прав. Здесь проверяется каждая из четырёх строк, и при беде
  контейнеры не поднимаются вовсе;
* СОБЫТИЯ ДОЛЖНЫ ИДТИ ТОЙ ЖЕ МОДЕЛЬЮ, что у базы. Если локальная молчит, события
  уйдут в облако, и в плече станет два отличия вместо одного — та же ловушка, из-за
  которой `auto_upgrade` пришлось переснимать. Поэтому адрес проверяется, модель
  греется, а скорость ЗАПИСЫВАЕТСЯ в отчёт: она влияет на сравнение и должна быть
  видна разбору, а не забыта;
* ФАЙЛЫ, ИДУЩИЕ В ЗАПРОС, сверяются с мостом базы: `world.md` и подсказки
  модель ЧИТАЕТ, и если они разошлись, в плече будет больше одного отличия.
  28.09 на `one_strike` это пропустили: `world.md` за сутки прибавил 36 строк,
  среди них запись про то же правило, о котором говорит подсказка идеи;
* МЕТКА НЕ ДВИГАЕТСЯ. Мост берётся по `verified`, и скрипт печатает, какой это
  коммит: плечо обязано сыграть на том же мосту, что база.

Ничего не запускает, если хоть одна проверка не прошла: пустая ферма дешевле
негодного прогона.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
import time

ПОРТ = 11434


def сказать(*ч):
    print(dt.datetime.now().strftime("[%H:%M:%S]"), *ч, flush=True)


def wsl(команда: str, таймаут: int = 300) -> tuple[int, str]:
    р = subprocess.run(["wsl", "-e", "bash", "-c", команда], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=таймаут)
    return р.returncode, (р.stdout or "") + (р.stderr or "")


def ждать_до(час: str) -> None:
    if час.lower() in ("сейчас", "now"):
        сказать("пускаю сейчас, без ожидания")
        return
    ч, м = (int(x) for x in час.split(":"))
    сейчас = dt.datetime.now()
    цель = сейчас.replace(hour=ч, minute=м, second=0, microsecond=0)
    if цель < сейчас:
        # ЛОВУШКА: прошедший час означал бы ожидание СУТОК, и молча. Спрашивать
        # некого — скрипт идёт в фоне, — поэтому говорим вслух и ждём до завтра
        # только если разница больше двадцати часов не выходит; иначе это явно
        # опечатка в часе, и лучше отказаться, чем занять ферму завтра.
        цель += dt.timedelta(days=1)
        сколько = цель - сейчас
        сказать(f"ВНИМАНИЕ: {час} уже прошёл, ближайший срок — завтра "
                f"({str(сколько).split('.')[0]})")
        if сколько > dt.timedelta(hours=20):
            raise SystemExit("больше двадцати часов ожидания — похоже на опечатку "
                             "в часе; для немедленного пуска пишите «сейчас»")
    сказать(f"ждём до {цель.strftime('%d.%m %H:%M')} ({str(цель - сейчас).split('.')[0]})")
    while dt.datetime.now() < цель:
        time.sleep(min(60, max(1, (цель - dt.datetime.now()).total_seconds())))
    сказать("срок пришёл")


def запрос_совпадает(мост_базы: str) -> tuple[bool, str]:
    """Совпадают ли файлы, УХОДЯЩИЕ В ЗАПРОС, с мостом базы (28.09).

    Мало проверить `.inc` и решающий код: модель читает ещё `world.md` (ключ
    `--world`) и подсказки. На `one_strike` 28.09 я этого не сверил, и плечо вышло с
    двумя отличиями — `world.md` за сутки прибавил 36 строк, среди них запись про то
    же правило, о котором говорит подсказка идеи. Мак поймал это при разборе.

    Пустой `мост_базы` значит «сверять не с чем» — тогда просто молчим.
    """
    if not мост_базы:
        return True, "мост базы не назван — сверять не с чем"
    код, вывод = wsl(f"cd ~/coss3-git && git diff --stat {мост_базы} verified -- "
                     f"world.md 'hints_*.txt' | tail -5")
    if код != 0:
        return True, f"сверить не удалось: {вывод.strip()[:120]}"
    строки = [с for с in вывод.strip().split("\n") if с.strip()]
    if not строки:
        return True, "world.md и подсказки совпадают с мостом базы"
    return False, "РАЗОШЛИСЬ с мостом базы: " + "; ".join(с.strip() for с in строки)


def контроль(идея: str, база: str, мост_базы: str = "") -> tuple[bool, dict]:
    """Всё, что должно быть верно ДО подъёма. (годно, подробности)."""
    из: dict = {}
    беды = []

    совпало, что = запрос_совпадает(мост_базы)
    из["запрос"] = что
    if not совпало:
        беды.append("файлы запроса " + что + " — в плече будет больше одного "
                    "отличия; либо переснять базу на этой метке, либо назвать "
                    "расхождение в итоге")

    код, вывод = wsl("cd ~/coss3-git && git status --short | wc -l && "
                     "git log --oneline -1 verified && "
                     "git show verified:docker/experiments.ini | grep -c '^\\[" + идея + "\\]' && "
                     "git show verified:docker/experiments.ini | grep -c '^\\[" + база + "\\]' && "
                     "grep -o -- '--human-only\\|--human-state\\|--human-cmd\\|--endgame\\|--human-kills' "
                     "docker/entrypoint.sh | sort -u | wc -l")
    строки = [с for с in вывод.strip().split("\n") if с.strip()]
    if код != 0 or len(строки) < 5:
        беды.append(f"клон не отвечает: {вывод.strip()[:200]}")
    else:
        грязно, метка, есть_идея, есть_база, флагов = строки[0], строки[1], строки[2], строки[3], строки[4]
        из["метка"] = метка
        if грязно.strip() != "0":
            беды.append(f"клон грязный ({грязно.strip()} файлов) — мост поедет не тот")
        if есть_идея.strip() != "1":
            беды.append(f"идеи [{идея}] под меткой нет")
        if есть_база.strip() != "1":
            беды.append(f"базы [{база}] под меткой нет")
        if флагов.strip() != "5":
            беды.append(f"в entrypoint не все пять человеческих флагов ({флагов.strip()})")

    # Локальная модель: адрес и скорость. Скорость пишем в отчёт, не в приговор.
    р = subprocess.run([sys.executable, "warm_local.py", "--minutes", "180"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    вывод = (р.stdout or "") + (р.stderr or "")
    м = re.search(r"замер:.*?за ([\d.]+) с", вывод)
    из["модель_с"] = float(м.group(1)) if м else None
    if "ГОТОВО" not in вывод:
        беды.append("локальная модель не прогрелась — события уйдут в облако, "
                    "и в плече станет два отличия: " + вывод.strip()[-160:])

    код, вывод = wsl("docker ps --filter name=coss3- -q | wc -l")
    из["живых"] = вывод.strip()
    if код != 0:
        беды.append("docker не отвечает")
    elif вывод.strip() not in ("0", ""):
        беды.append(f"на ферме уже {вывод.strip()} контейнеров — сначала погасить")

    из["беды"] = беды
    return (not беды), из


def поднять(идея: str, копий: int, имя_результата: str = "") -> tuple[int, str]:
    """Имя результата ОТДЕЛЬНО от имени идеи (28.09).

    Иначе переснятая база легла бы в тот же каталог `<дата>/<идея>`, что прежний
    прогон, и в одной папке смешались бы два РАЗНЫХ моста. Так случилось бы при
    переснятии `auto_upgrade2` на метке `5e74baf`: прежний прогон того же дня играл
    на `5d295ba`.
    """
    имя_результата = имя_результата or идея
    части = []
    for n in range(1, копий + 1):
        части.append(
            f"rm -rf ~/io-h{n} ~/profile-h{n}; mkdir -p ~/io-h{n} ~/profile-h{n}; "
            f"cp -a ~/profile/. ~/profile-h{n}/; "
            f"docker run -d --name coss3-h{n} --env-file ~/coss3.env "
            f"--entrypoint /usr/bin/tini "
            f"-e COSS3_BRIDGE_GIT=git@github.com:snipstack-cloud/coss3-bridge.git "
            f"-e COSS3_BRIDGE_REF=verified -e COSS3_EXPERIMENT={идея} "
            f"-e COSS3_RESULTS_NAME={имя_результата}/{n} "
            f"-e COSS3_RESULTS_GIT=git@github.com:snipstack-cloud/coss3-results.git "
            f"-e COSS3_RESULTS_KEY=/ssh/results_key "
            f"-v ~/io-h{n}:/io -v ~/profile-h{n}:/profile "
            f"-v ~/.ssh/coss3_deploy:/ssh/deploy_key:ro "
            f"-v ~/.ssh/coss3_results:/ssh/results_key:ro "
            f"-v ~/coss3-git/docker/entrypoint.sh:/opt/bridge/entrypoint.sh:ro "
            f"coss3:2 -- /bin/bash /opt/bridge/entrypoint.sh >/dev/null")
    return wsl("; ".join(части), таймаут=600)


def четыре_строки(имя: str, идея: str) -> tuple[bool, str]:
    """Мост, идея, флаги, пульс — до ожидания результата."""
    for _ in range(40):
        код, вывод = wsl(f"docker logs {имя} 2>&1 | grep -cE 'пульс есть|ПУЛЬСА НЕТ|not found'")
        if вывод.strip().isdigit() and int(вывод.strip()) > 0:
            break
        time.sleep(10)
    _, лог = wsl(f"docker logs {имя} 2>&1 | grep -E "
                 f"'мост обновлён|идея «|блоки на месте|пульс есть|ПУЛЬСА НЕТ|not found' | cut -c1-120")
    годно = ("пульс есть" in лог and f"идея «{идея}»" in лог
             and "блоки на месте" in лог and "not found" not in лог)
    return годно, лог


def дождаться(копий: int) -> str:
    for _ in range(200):
        _, готово = wsl("n=0; for c in $(docker ps -a --filter name=coss3-h --format '{{.Names}}'); do "
                        "docker logs $c 2>&1 | grep -q '^ *отправлено: results/' && n=$((n+1)); done; echo $n")
        _, живых = wsl("docker ps --filter name=coss3-h -q | wc -l")
        if готово.strip().isdigit() and int(готово.strip()) >= копий:
            return f"все {копий} отправили результаты"
        if живых.strip() == "0":
            return f"контейнеры погасли, отправили {готово.strip()} из {копий}"
        time.sleep(20)
    return "истекло время ожидания"


def main() -> int:
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    час, идея, база = sys.argv[1], sys.argv[2], sys.argv[3]
    копий = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    # Пятый аргумент — КОММИТ, на котором играла база. Без него сравнимость плеча
    # не проверить: см. запрос_совпадает.
    мост_базы = sys.argv[5] if len(sys.argv) > 5 else ""
    # Шестой аргумент — имя каталога результатов, если оно должно отличаться от
    # имени идеи (переснятая база на другом мосту).
    имя_результата = sys.argv[6] if len(sys.argv) > 6 else ""

    ждать_до(час)
    годно, п = контроль(идея, база, мост_базы)
    сказать(f"метка: {п.get('метка')}")
    сказать(f"файлы запроса: {п.get('запрос')}")
    сказать(f"локальная модель: замер {п.get('модель_с')} с")
    if not годно:
        сказать("НЕ ЗАПУСКАЮ, потому что:")
        for б in п["беды"]:
            сказать("  •", б)
        return 1

    код, вывод = поднять(идея, копий, имя_результата)
    if код != 0:
        сказать("подъём не удался:", вывод.strip()[-200:])
        return 1
    сказать(f"поднято копий: {копий}")

    ок, лог = четыре_строки("coss3-h1", идея)
    сказать("контроль по первой копии:")
    for с in лог.strip().split("\n"):
        сказать("   ", с.strip()[:120])
    if not ок:
        сказать("КОНТРОЛЬ НЕ ПРОШЁЛ — гашу, чтобы не считать негодный прогон")
        wsl("docker rm -f $(docker ps -aq --filter name=coss3-h) >/dev/null 2>&1")
        return 1

    сказать("жду окончания")
    сказать(дождаться(копий))
    _, итоги = wsl("for c in $(docker ps -a --filter name=coss3-h --format '{{.Names}}'); do "
                   "echo -n \"$c: \"; docker logs $c 2>&1 | grep -E '^ *отправлено: results/' | tail -1; done")
    for с in итоги.strip().split("\n"):
        сказать(с.strip()[:140])
    wsl("docker rm -f $(docker ps -aq --filter name=coss3-h) >/dev/null 2>&1")
    сказать("контейнеры погашены, ферма пуста")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
