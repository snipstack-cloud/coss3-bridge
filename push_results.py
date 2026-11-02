#!/usr/bin/env python3
"""Отправить результат прогона в git, чтобы он пережил контейнер.

    python3 push_results.py --io /io --repo git@github.com:кто/coss3-results.git \
        --key /ssh/results_key --branch results --name wave40/3

Зачем. Прогон живёт в контейнере: погасили — и нет ни трассы, ни отчёта. На
ферме из десяти копий это значит, что сравнивать нечего уже через сутки.

Что уезжает: отчёт, трасса, квитанция условий, SHA моста, описание идеи и
ХВОСТЫ логов. Целиком логи не отправляются: `game.log` под Wine бывает
мегабайтным, а нужен из него последний экран.

Три правила, которые здесь важнее удобства:

1. **Сначала обыск, потом отправка.** Отправка публикует; отозвать уже
   опубликованное нельзя. Если в файлах найдено похожее на ключ — не
   отправляется НИЧЕГО, и называется файл со строкой.
2. **Своя ветка и свой каталог у каждой копии.** Десять копий пишут
   одновременно; каждая трогает только `<ветка>/<дата>/<опыт>/<копия>/`, а
   столкновения разводятся перечитыванием и повтором.
3. **Молчать нельзя.** Не смог отправить — сказал, почему, и вернул ненулевой
   код. Прогон при этом не считается пропавшим: файлы остались в /io.
"""
from __future__ import annotations
import argparse
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

# Что отправляем целиком: маленькое и самое ценное.
ЦЕЛИКОМ = ["отчёт.md", "coss3_bot.jsonl", "match.dat", "bridge.sha",
           "опыт.json", "policy.rc", "ack_last.dat",
           # Файл мира с вопросами модели. Клон моста в контейнере одноразовый,
           # и без этой строки вопрос, ради которого всё затевалось, сгинул бы
           # вместе с контейнером.
           "world.md",
           # Разбор партии критиком (--critic): одна-две строки на партию, но
           # это единственное место, где модель говорит о партии целиком.
           "разбор.md",
           # ЖУРНАЛ ТЕНИ ТАКТИКА (2.10, --shadow-log). Мак просил присылать его
           # ВМЕСТЕ с записью партии: сеть считает решение по живому снимку и
           # только пишет его, и сверять её с симулятором можно лишь по этому
           # файлу. Первая отправка 2.10 ушла БЕЗ него — список здесь жёсткий, и
           # новый файл в него надо вносить руками, иначе он молча не уедет.
           "coss3_shadow.jsonl",
           # СОСТОЯНИЕ ОБЕИХ СТОРОН ПОСЛЕ ПАРТИИ (2.10, итог_партии.py). Трасса и
           # снимок кончаются вместе с эпизодом БОТА, а игрок играет дальше: в
           # проверке 2 в записи у него было 4 ступени защиты мушкетёра и ни одной
           # драгунской, а на 21:35 — шесть, две драгунских, 14 конных и 107
           # крестьян против 41 в записи. «Чем игрок закончил» отсутствовало ПО
           # ПОСТРОЕНИЮ, и узнали мы это только с его слов.
           "после_партии.json",
           # Строки моста из лога игры: единственный способ увидеть, что мост
           # сказал движку и что тот ответил.
           "мост_в_игре.log",
           "после_горизонта.jsonl",      # 28.10: кольцо гибели после горизонта (Windows досылала его руками)
           # Поиск первого бойца без модели (opening.py): партии и сводка.
           "opening.jsonl", "opening.md", "scout.md",
           # ЧАСТЫЙ СНИМОК СОСТОЯНИЯ (--snap-every). Трасса пишется раз в такт,
           # то есть медианно раз в 21 игровую секунду; игра же переписывает
           # состояние каждую секунду. Без этого файла любой счёт по партии —
           # простой, жизнь волны, время под порогом еды — считается по трём
           # точкам на минуту. Около 150 КБ на партию при шаге 5 с.
           "coss3_snap.jsonl",
           # ВТОРОЙ БОТ (2.11, бот против бота: поле `флаги2` идеи, `llm_policy._второй_бот`) — его трасса и снимок,
           # слот 1. Нет второго бота — файлов нет, и строка ничего не меняет.
           "coss3_bot_P1.jsonl", "coss3_snap_P1.jsonl"]
# Что отправляем хвостом: строк и сколько.
ХВОСТОМ = {"policy.log": 400, "coss3_llm.log": 400, "game.log": 300,
           "install.log": 200, "report.txt": 800, "policy_P1.log": 400}

# Похожее на ключ. Список нарочно шире, чем «наши» ключи: в логи попадает то,
# чего туда не клали, и обыск должен ловить чужое тоже.
СЕКРЕТЫ = [
    (re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}"), "ключ OpenRouter"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "ключ вида sk-..."),
    (re.compile(r"nvapi-[A-Za-z0-9_-]{16,}"), "ключ NVIDIA"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "токен GitHub"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "токен GitHub (fine-grained)"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "ключ AWS"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "приватный ключ"),
]


def выполнить(аргс: list[str], где: str = "", ключ: str = "",
              терпеть: bool = False) -> tuple[int, str]:
    окр = dict(os.environ)
    if ключ:
        # IdentitiesOnly: иначе ssh переберёт ключи агента и может уйти не тем.
        окр["GIT_SSH_COMMAND"] = (
            f"ssh -i {ключ} -o IdentitiesOnly=yes -o BatchMode=yes")
    р = subprocess.run(аргс, cwd=где or None, env=окр,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    вывод = р.stdout + р.stderr
    if р.returncode and not терпеть:
        print(f"  ! {' '.join(аргс[:3])}: {вывод.strip()[:400]}")
    return р.returncode, вывод


def хвост(путь: str, строк: int) -> str:
    try:
        with open(путь, encoding="utf-8", errors="replace") as f:
            все = f.readlines()
    except OSError:
        return ""
    если = все[-строк:]
    шапка = (f"# последние {len(если)} строк из {len(все)}\n"
             if len(все) > len(если) else "")
    return шапка + "".join(если)


def собрать(io: str, куда: str) -> list[str]:
    """Складывает то, что поедет, и возвращает список файлов."""
    os.makedirs(куда, exist_ok=True)
    собрано = []
    for имя in ЦЕЛИКОМ:
        и = os.path.join(io, имя)
        if os.path.isfile(и) and os.path.getsize(и) > 0:
            shutil.copy2(и, os.path.join(куда, имя))
            собрано.append(имя)
    for имя, строк in ХВОСТОМ.items():
        т = хвост(os.path.join(io, имя), строк)
        if т.strip():
            with open(os.path.join(куда, имя), "w", encoding="utf-8") as f:
                f.write(т)
            собрано.append(имя)
    return собрано


def обыск(каталог: str) -> list[str]:
    """Похожее на секрет. Пусто — значит отправлять можно.

    Отдельно ищем ЗНАЧЕНИЕ ключа из окружения: это самая надёжная проверка,
    потому что не зависит от того, угадали ли мы форму ключа.
    """
    свои = []
    for пер in ("OPENROUTER_API_KEY", "NVIDIA_API_KEY", "COSS3_RESULTS_TOKEN"):
        зн = (os.environ.get(пер) or "").strip()
        if len(зн) >= 12:
            свои.append((зн, f"значение {пер} из окружения"))
    находки = []
    for путь, _, файлы in os.walk(каталог):
        if ".git" in путь.split(os.sep):
            continue
        for имя in файлы:
            п = os.path.join(путь, имя)
            try:
                with open(п, encoding="utf-8", errors="replace") as f:
                    текст = f.read()
            except OSError:
                continue
            for i, строка in enumerate(текст.splitlines(), 1):
                for рег, что in СЕКРЕТЫ:
                    if рег.search(строка):
                        находки.append(f"{имя}:{i} — {что}")
                for зн, что in свои:
                    if зн in строка:
                        находки.append(f"{имя}:{i} — {что}")
    return находки


def main() -> int:
    p = argparse.ArgumentParser(description="отправить результат прогона в git")
    p.add_argument("--io", required=True, help="каталог прогона")
    p.add_argument("--repo", required=True, help="куда отправлять (ssh или https)")
    p.add_argument("--branch", default="results", help="ветка результатов")
    p.add_argument("--key", default="", help="ssh-ключ С ПРАВОМ ЗАПИСИ")
    p.add_argument("--name", required=True,
                   help="имя прогона: <опыт>/<копия> или любое своё")
    p.add_argument("--tries", type=int, default=5,
                   help="сколько раз повторить при столкновении с другой копией")
    a = p.parse_args()

    if not os.path.isdir(a.io):
        print(f"нет каталога прогона: {a.io}")
        return 1
    if a.key and not os.path.isfile(a.key):
        print(f"ключа нет: {a.key}. Для записи нужен ключ С ПРАВОМ ЗАПИСИ — "
              f"тот, что монтируется для чтения моста, не подойдёт.")
        return 1

    врем = tempfile.mkdtemp(prefix="coss3-res-")
    try:
        # --- собрать и ОБЫСКАТЬ до всякой сети -----------------------------
        ветка_путь = os.path.join(врем, "груз")
        собрано = собрать(a.io, ветка_путь)
        if not собрано:
            print(f"в {a.io} нечего отправлять")
            return 1
        находки = обыск(ветка_путь)
        if находки:
            print("ОТПРАВКА ОТМЕНЕНА: в файлах прогона найдено похожее на ключ.")
            for н in находки[:10]:
                print(f"  {н}")
            print("Отправка публикует, отозвать опубликованное нельзя. "
                  "Уберите ключ из логов и повторите.")
            return 2
        print(f"обыск чист, отправляю файлов: {len(собрано)} "
              f"({', '.join(собрано)})")

        # --- клон ветки ----------------------------------------------------
        клон = os.path.join(врем, "репо")
        код, _ = выполнить(["git", "clone", "--quiet", "--depth", "1",
                            "--branch", a.branch, a.repo, клон],
                           ключ=a.key, терпеть=True)
        if код:
            # Ветки ещё нет — заводим пустую. Не master: результаты не должны
            # ехать туда, где живёт код.
            код, вывод = выполнить(["git", "clone", "--quiet", "--depth", "1",
                                    a.repo, клон], ключ=a.key)
            if код:
                print(f"не смог клонировать {a.repo}: доступ или адрес")
                return 1
            выполнить(["git", "checkout", "--orphan", a.branch], где=клон)
            выполнить(["git", "rm", "-rq", "--cached", "."], где=клон, терпеть=True)
            for имя in os.listdir(клон):
                if имя != ".git":
                    п = os.path.join(клон, имя)
                    shutil.rmtree(п) if os.path.isdir(п) else os.unlink(п)
            with open(os.path.join(клон, "README.md"), "w", encoding="utf-8") as f:
                f.write("# Результаты прогонов\n\nСюда пишут контейнеры. "
                        "Кода здесь нет — только отчёты, трассы и хвосты логов.\n")
            print(f"ветки {a.branch} не было — завёл пустую")

        куда_отн = os.path.join(datetime.now().strftime("%Y-%m-%d"), a.name)
        for попытка in range(1, a.tries + 1):
            куда = os.path.join(клон, куда_отн)
            os.makedirs(куда, exist_ok=True)
            for имя in os.listdir(ветка_путь):
                shutil.copy2(os.path.join(ветка_путь, имя),
                             os.path.join(куда, имя))
            выполнить(["git", "config", "user.email", "coss3@container"], где=клон)
            выполнить(["git", "config", "user.name", "coss3 container"], где=клон)
            выполнить(["git", "add", "-A"], где=клон)
            код, _ = выполнить(["git", "diff", "--cached", "--quiet"],
                               где=клон, терпеть=True)
            if код == 0:
                print("нечего коммитить: такой результат уже лежит")
                return 0
            выполнить(["git", "commit", "--quiet", "-m",
                       f"прогон {a.name} от {datetime.now():%Y-%m-%d %H:%M}"],
                      где=клон)
            код, вывод = выполнить(["git", "push", "--quiet", "origin",
                                    f"HEAD:{a.branch}"], где=клон, ключ=a.key,
                                   терпеть=True)
            if код == 0:
                print(f"отправлено: {a.branch}/{куда_отн}")
                return 0
            if попытка == a.tries:
                print(f"не отправилось за {a.tries} попыток: {вывод.strip()[:300]}")
                print(f"Файлы целы в {a.io} — прогон не пропал.")
                return 1
            # Столкнулись с другой копией. Перечитываем и повторяем; пауза
            # вразнобой, иначе десять копий столкнутся снова все разом.
            пауза = random.uniform(1, 4) * попытка
            print(f"  попытка {попытка}: ветка ушла вперёд, "
                  f"перечитываю через {пауза:.0f} с")
            time.sleep(пауза)
            выполнить(["git", "fetch", "--quiet", "origin", a.branch],
                      где=клон, ключ=a.key, терпеть=True)
            выполнить(["git", "reset", "--hard", "--quiet",
                       f"origin/{a.branch}"], где=клон, терпеть=True)
        return 1
    finally:
        shutil.rmtree(врем, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
