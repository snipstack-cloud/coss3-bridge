#!/usr/bin/env python3
"""Консоль опытов: выбрать идею и проверить её на N копиях игры разом.

    ./docker/exp.py list                    какие есть идеи
    ./docker/exp.py run wave40              запустить (сколько копий — из ini)
    ./docker/exp.py run wave40 --copies 3   перебить число копий
    ./docker/exp.py status                  что идёт прямо сейчас
    ./docker/exp.py report wave40           свести результат, сравнить с базой
    ./docker/exp.py stop wave40             погасить

Замысел фермы. Мастер-мост живёт и правится на Windows — там его отлаживают на
живой игре. Сюда приезжает уже проверенная там версия, по git. Идея — это
ветка/коммит моста плюс набор флагов. Десять копий дают десять партий разом, и
мастер при этом не простаивает.

Зависимостей нет: только стандартная библиотека и docker в PATH.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

КОРЕНЬ = os.path.dirname(os.path.abspath(__file__))
ИНИ = os.path.join(КОРЕНЬ, "experiments.ini")
IO = os.path.join(КОРЕНЬ, "io")
ОБРАЗ = os.environ.get("COSS3_TAG", "coss3:1")
МЕТКА = "coss3.exp"          # docker label, по нему находим свои контейнеры


def идеи() -> configparser.ConfigParser:
    if not os.path.isfile(ИНИ):
        sys.exit(f"нет файла идей: {ИНИ}")
    c = configparser.ConfigParser()
    c.read(ИНИ, encoding="utf-8")
    return c


def docker(*аргс: str, тихо: bool = False) -> str:
    р = subprocess.run(["docker", *аргс], capture_output=True, text=True)
    if р.returncode and not тихо:
        sys.exit(f"docker {' '.join(аргс[:2])}: {р.stderr.strip()}")
    return р.stdout.strip()


def контейнеры(ид: str | None = None) -> list[dict]:
    фильтр = f"label={МЕТКА}" + (f"={ид}" if ид else "")
    вывод = docker("ps", "-a", "--filter", фильтр, "--format",
                   "{{.Names}}\t{{.Status}}\t{{.Label \"coss3.exp\"}}", тихо=True)
    из = []
    for строка in вывод.splitlines():
        части = строка.split("\t")
        if len(части) >= 3:
            из.append({"имя": части[0], "статус": части[1], "опыт": части[2]})
    return из


# --------------------------------------------------------------------------- list
def команда_list(_) -> int:
    c = идеи()
    идут = {к["опыт"] for к in контейнеры() if к["статус"].startswith("Up")}
    print(f"{'id':<12} {'ref':<16} {'копий':>5}  что")
    print("-" * 78)
    for имя in c.sections():
        s = c[имя]
        помета = "  <-- ИДЁТ СЕЙЧАС" if имя in идут else ""
        print(f"{имя:<12} {s.get('ref', 'master'):<16} "
              f"{s.get('копий', '10'):>5}  {s.get('что', '')}{помета}")
    print()
    print("Запустить:  ./docker/exp.py run <id>")
    return 0


# ---------------------------------------------------------------------------- run
def команда_run(a) -> int:
    c = идеи()
    if a.ид not in c:
        sys.exit(f"нет такой идеи: {a.ид}. Что есть — ./docker/exp.py list")
    s = c[a.ид]
    копий = a.copies or int(s.get("копий", "10"))
    ref = s.get("ref", "master")
    флаги = (s.get("флаги", "") or "").split()

    репо = os.environ.get("COSS3_BRIDGE_GIT", "")
    if not репо:
        print("ВНИМАНИЕ: COSS3_BRIDGE_GIT не задан — мост возьмётся из образа.")
        print("  Для опыта это негодно: версия моста ничем не подтверждена, и")
        print("  через неделю будет не сказать, что именно проверялось.")
        print("  Задать:  export COSS3_BRIDGE_GIT=https://.../coss3-bridge.git")
        if not a.force:
            sys.exit("  Настаиваете — добавьте --force.")

    уже = [к for к in контейнеры(a.ид) if к["статус"].startswith("Up")]
    if уже:
        sys.exit(f"опыт {a.ид} уже идёт ({len(уже)} копий). "
                 f"Погасить: ./docker/exp.py stop {a.ид}")

    docker("rm", "-f", *[к["имя"] for к in контейнеры(a.ид)], тихо=True) \
        if контейнеры(a.ид) else None

    есть_gpu = os.path.exists("/dev/dri")
    print(f"опыт {a.ид}: {s.get('что', '')}")
    print(f"  мост {ref} из {репо or 'образа'}, флаги: {' '.join(флаги) or '—'}")
    print(f"  копий {копий}, видеокарта: {'есть' if есть_gpu else 'НЕТ (рендер на CPU)'}")

    начало = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for n in range(копий):
        каталог = os.path.join(IO, a.ид, str(n))
        os.makedirs(каталог, exist_ok=True)
        with open(os.path.join(каталог, "опыт.json"), "w", encoding="utf-8") as f:
            json.dump({"опыт": a.ид, "что": s.get("что", ""), "ref": ref,
                       "флаги": флаги, "копия": n, "начало": начало,
                       "база": s.get("база", "")}, f, ensure_ascii=False, indent=1)
        аргс = ["run", "-d",
                "--name", f"coss3-{a.ид}-{n}",
                "--label", f"{МЕТКА}={a.ид}",
                "--hostname", f"coss3-{n}",
                "-v", f"{os.path.abspath(каталог)}:/io",
                "-e", f"COSS3_BRIDGE_REF={ref}",
                "-e", f"COSS3_EXTRA_FLAGS={' '.join(флаги)}",
                "-p", f"{5900 + n}:5900"]
        if репо:
            аргс += ["-e", f"COSS3_BRIDGE_GIT={репо}"]
        if есть_gpu:
            аргс += ["--device", "/dev/dri:/dev/dri"]
        for пер in ("COSS3_MODEL", "COSS3_EVERY", "COSS3_WAVE_MIN", "COSS3_D3D",
                    "COSS3_RES", "COSS3_VNC", "NVIDIA_API_KEY", "NIM_BASE_URL"):
            if os.environ.get(пер):
                аргс += ["-e", f"{пер}={os.environ[пер]}"]
        аргс.append(ОБРАЗ)
        docker(*аргс)
    print(f"\nподнято {копий} копий. VNC: порты {5900}..{5900 + копий - 1}")
    print(f"  ПЕРВЫЙ БОЙ В КАЖДОЙ КОПИИ ЗАВОДИТСЯ РУКАМИ — тик Progress идёт")
    print(f"  только в бою. Дальше партии начинаются сами (команда NEW).")
    print(f"  смотреть:  ./docker/exp.py status")
    print(f"  результат: ./docker/exp.py report {a.ид}")
    return 0


# ------------------------------------------------------------------------- status
def команда_status(_) -> int:
    все = контейнеры()
    if не_пусто := [к for к in все]:
        по_опытам: dict[str, list] = {}
        for к in не_пусто:
            по_опытам.setdefault(к["опыт"], []).append(к)
        for опыт, спис in sorted(по_опытам.items()):
            живых = sum(1 for к in спис if к["статус"].startswith("Up"))
            print(f"{опыт}: {живых} из {len(спис)} копий живы")
            for к in спис:
                трасса = os.path.join(IO, опыт, к["имя"].rsplit("-", 1)[-1],
                                      "coss3_bot.jsonl")
                тактов = сумма_строк(трасса)
                gt = последнее_время(трасса)
                print(f"   {к['имя']:<24} {к['статус']:<22} "
                      f"тактов {тактов:>4}  игровое время {gt}")
    else:
        print("опытов не запущено")
    return 0


def сумма_строк(путь: str) -> int:
    try:
        with open(путь, encoding="utf-8") as f:
            return sum(1 for l in f if l.strip())
    except OSError:
        return 0


def последнее_время(путь: str) -> str:
    try:
        with open(путь, encoding="utf-8") as f:
            строки = [l for l in f if l.strip()]
        if not строки:
            return "—"
        gt = json.loads(строки[-1]).get("gt", 0)
        return f"{gt // 60}:{gt % 60:02d}"
    except (OSError, ValueError):
        return "—"


# ------------------------------------------------------------------------- report
def свод(опыт: str) -> list[dict]:
    """По копии на строку: что выросло, что ушло, взята ли цель."""
    корень = os.path.join(IO, опыт)
    если = []
    if not os.path.isdir(корень):
        return если
    for копия in sorted(os.listdir(корень), key=lambda x: (len(x), x)):
        путь = os.path.join(корень, копия, "coss3_bot.jsonl")
        строки = []
        try:
            with open(путь, encoding="utf-8") as f:
                строки = [json.loads(l) for l in f if l.strip()]
        except OSError:
            continue
        if not строки:
            если.append({"копия": копия, "тактов": 0})
            continue
        первый, последний = строки[0], строки[-1]

        def вражьи(р):
            s = р.get("state", {})
            свои = [v for k, v in s.items()
                    if k.endswith("_peasants") and not k.startswith("my")]
            return max(свои) if свои else None

        враг0, враг1 = вражьи(первый), вражьи(последний)
        волн = sum(1 for р in строк_с_волной(строки))
        брака = sum(len(р.get("rejected") or []) for р in строки)
        вето = sum(1 for р in строки if р.get("veto"))
        sha = прочесть(os.path.join(корень, копия, "bridge.sha"))
        если.append({
            "копия": копия,
            "тактов": len(строки),
            "время": последний.get("gt", 0),
            "крестьян": последний.get("state", {}).get("peasants"),
            "армия": (последний.get("state", {}).get("mil_inf") or 0)
                     + (последний.get("state", {}).get("mil_shooters") or 0),
            "враг0": враг0, "враг1": враг1,
            "убито": (враг0 - враг1) if (враг0 is not None and враг1 is not None) else None,
            "волн": волн, "брак": брака, "вето": вето,
            "мост": (sha or "?")[:8],
        })
    return если


def строк_с_волной(строки):
    """Волна считается ушедшей, если ATTACK был и мост его не отверг."""
    return [р for р in строки if р.get("attack") and not р.get("veto")]


def прочесть(путь: str) -> str:
    try:
        return open(путь, encoding="utf-8").read().strip()
    except OSError:
        return ""


def напечатать_свод(опыт: str, строки: list[dict]) -> None:
    if not строки:
        print(f"  {опыт}: данных нет")
        return
    печ = [с for с in строки if с.get("тактов")]
    print(f"  {'копия':<6}{'тактов':>7}{'время':>7}{'крест':>7}{'армия':>7}"
          f"{'враг':>10}{'убито':>7}{'волн':>6}{'брак':>6}{'вето':>6}  мост")
    for с in строки:
        if not с.get("тактов"):
            print(f"  {с['копия']:<6}   пусто — партия не началась?")
            continue
        gt = с["время"]
        print(f"  {с['копия']:<6}{с['тактов']:>7}{gt // 60:>5}:{gt % 60:02d}"
              f"{с['крестьян'] or 0:>7}{с['армия']:>7}"
              f"{str(с['враг0']) + '->' + str(с['враг1']):>10}"
              f"{с['убито'] if с['убито'] is not None else '—':>7}"
              f"{с['волн']:>6}{с['брак']:>6}{с['вето']:>6}  {с['мост']}")
    if печ:
        def сред(ключ):
            зн = [с[ключ] for с in печ if с.get(ключ) is not None]
            return sum(зн) / len(зн) if зн else 0
        взяли = sum(1 for с in печ if (с["убито"] or 0) > 0)
        print(f"  {'ИТОГО':<6}{'':>7}{'':>7}{сред('крестьян'):>7.0f}"
              f"{сред('армия'):>7.0f}{'':>10}{сред('убито'):>7.1f}"
              f"{сред('волн'):>6.1f}{сред('брак'):>6.1f}{сред('вето'):>6.1f}")
        print(f"  цель взята в {взяли} копиях из {len(печ)}")


def команда_report(a) -> int:
    c = идеи()
    строки = свод(a.ид)
    что = c[a.ид].get("что", "") if a.ид in c else ""
    print(f"\nОПЫТ {a.ид}: {что}")
    print("=" * 78)
    напечатать_свод(a.ид, строки)

    база = c[a.ид].get("база", "") if a.ид in c else ""
    if база:
        строки_б = свод(база)
        if строки_б:
            print(f"\nБАЗА {база}: {c[база].get('что', '') if база in c else ''}")
            print("-" * 78)
            напечатать_свод(база, строки_б)
            сравнить(строки, строки_б)
        else:
            print(f"\nбаза {база} ещё не прогонялась — сравнивать не с чем")
    print()
    print("  Осторожно с выводами: единичные прогоны — это наблюдения, а не")
    print("  измерение. Сравнивать имеет смысл только равные по числу копий.")
    return 0


def сравнить(опыт: list[dict], база: list[dict]) -> None:
    о = [с for с in опыт if с.get("тактов")]
    б = [с for с in база if с.get("тактов")]
    if not о or not б:
        return
    print(f"\nРАЗНИЦА (опыт минус база), копий {len(о)} против {len(б)}:")
    for ключ, имя in (("убито", "убито крестьян врага"), ("волн", "волн"),
                      ("армия", "армия"), ("крестьян", "своих крестьян")):
        def сред(с, к):
            зн = [x[к] for x in с if x.get(к) is not None]
            return sum(зн) / len(зн) if зн else 0
        д = сред(о, ключ) - сред(б, ключ)
        знак = "+" if д >= 0 else ""
        print(f"  {имя:<24} {знак}{д:.1f}")


# --------------------------------------------------------------------------- stop
def команда_stop(a) -> int:
    к = контейнеры(a.ид)
    if not к:
        print(f"опыт {a.ид} не запущен")
        return 0
    docker("rm", "-f", *[x["имя"] for x in к])
    print(f"погашено копий: {len(к)}. Трассы остались в {os.path.join(IO, a.ид)}")
    return 0


def main() -> int:
    if not shutil.which("docker"):
        sys.exit("docker не найден в PATH")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    под = ap.add_subparsers(dest="команда", required=True)
    под.add_parser("list", help="какие есть идеи").set_defaults(_=команда_list)
    р = под.add_parser("run", help="запустить идею")
    р.add_argument("ид")
    р.add_argument("--copies", type=int, default=0)
    р.add_argument("--force", action="store_true",
                   help="запустить без git-версии моста (для опыта негодно)")
    р.set_defaults(_=команда_run)
    под.add_parser("status", help="что идёт").set_defaults(_=команда_status)
    р = под.add_parser("report", help="свести результат")
    р.add_argument("ид")
    р.set_defaults(_=команда_report)
    р = под.add_parser("stop", help="погасить")
    р.add_argument("ид")
    р.set_defaults(_=команда_stop)
    a = ap.parse_args()
    return a._(a)


if __name__ == "__main__":
    raise SystemExit(main())
