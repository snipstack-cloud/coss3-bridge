#!/usr/bin/env python3
"""Разбор `coss3_llm.log`: что модель ДЕЛАЛА, а не что писала.

    python log_review.py coss3_llm.log
    python log_review.py coss3_llm.log --replay-out ответы.jsonl

Появился после 11.09.2026, когда вопрос «отдавала ли модель BALANCE и TRAIN
крестьян, или только рассуждала про них» пришлось разбирать руками через grep
и это заняло полразговора. Всё, что там считалось глазами, считается здесь.

Главное, что печатается, — команды, которых НЕ БЫЛО НИ РАЗУ, и такты, где
модель назвала команду в тексте, но не отдала её. Лог показывает только
отданные команды, поэтому ненаписанная команда в нём невидима: её нет, и в
глаза это не бросается.

`--replay-out` восстанавливает из лога JSON-ответы модели (why/ok/stuck/cause +
команды) — их принимает `llm_policy.py --replay` и проигрывает против
`mock_game.py`. Так проверяется мост, а не модель: прогон на настоящих
исторических ответах показывает, ругается ли он теперь там, где раньше молчал.
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import json
import os
import re
from collections import Counter

sys_path = os.path.dirname(os.path.abspath(__file__))
if sys_path not in _sys.path:
    _sys.path.insert(0, sys_path)

from coss3_bridge import ROLE, RESOURCE
import llm_policy as LP

ИМЯ_РОЛИ = {v: k for k, v in ROLE.items()}
ИМЯ_РЕСУРСА = {v: k for k, v in RESOURCE.items()}

ТАКТ = re.compile(r"^(\d+):(\d\d)\s\s(.*)$")
ЭПИЗОД = re.compile(r"^=== эпизод (\d+) из (\d+)")
КОМАНДА = re.compile(r"^\s+(BUILD|TRAIN|BALANCE|UPGRADE|MODE|SET_RES)\s+(-?\d+)"
                     r"\s+->\s+(-?\d+)(?:\s+(\S+))?\s*$")
АТАКА = re.compile(r"^\s+ATTACK\s+(\d+)(?:\s*->\s*\S+)?\s*$")
ПОЯСНЕНИЕ = re.compile(r"^\s+(идёт|не идёт|почему):\s*(.*)$")
ПОЛЕ = {"идёт": "ok", "не идёт": "stuck", "почему": "cause"}


class Такт:
    def __init__(self, gt: int, why: str):
        self.gt, self.why = gt, why
        self.поля: dict[str, str] = {"why": why}
        self.команды: list[tuple[str, str, int]] = []   # (cmd, роль, число)
        self.атака_отвергнута: list[str] = []
        self.урок = ""
        self.урок_отброшен = ""
        self.расхождение_моста: list[str] = []   # строки нового формата, если есть
        self.медленно = ""

    @property
    def отдано(self) -> set[str]:
        return {c for c, _r, _n in self.команды}

    @property
    def текст(self) -> str:
        return " ".join(v for v in self.поля.values() if v)


def разобрать(путь: str) -> tuple[list[list[Такт]], list[str], list[str], list[str]]:
    """Эпизоды (списки тактов), шапка, исходы, неразобранные строки.

    Серию делим по строкам «=== эпизод N из M»: без этого ряды повторов
    склеиваются через границу партий и врут.
    """
    эпизоды: list[list[Такт]] = [[]]
    исходы: list[str] = []
    шапка: list[str] = []
    прочее: list[str] = []
    т: Такт | None = None
    for сырая in open(путь, encoding="utf-8", errors="replace"):
        строка = сырая.rstrip("\n")
        if not строка.strip():
            continue
        if ЭПИЗОД.match(строка.strip()):
            if эпизоды[-1]:
                эпизоды.append([])
            т = None
            continue
        m = ТАКТ.match(строка)
        if m:
            т = Такт(int(m.group(1)) * 60 + int(m.group(2)), m.group(3).strip())
            эпизоды[-1].append(т)
            continue
        if not строка.startswith(" "):
            s_ = строка.strip()
            if (s_.startswith("ЦЕЛЬ ДОСТИГНУТА") or s_.startswith("горизонт ")
                    or s_.startswith("игра писала состояние") or s_.startswith("итого:")):
                исходы.append(s_)
            else:
                шапка.append(s_)
            continue
        if т is None:
            шапка.append(строка.strip())
            continue
        m = КОМАНДА.match(строка)
        if m:
            вид, a1, a2, апг = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
            if вид == "BALANCE":
                роль = ИМЯ_РЕСУРСА.get(a1, str(a1))
            elif вид == "UPGRADE":
                роль = апг or ""
            else:
                роль = ИМЯ_РОЛИ.get(a1, str(a1))
            т.команды.append((вид, роль, a2))
            continue
        m = АТАКА.match(строка)
        if m:
            т.команды.append(("ATTACK", "", int(m.group(1))))
            continue
        m = ПОЯСНЕНИЕ.match(строка)
        if m:
            т.поля[ПОЛЕ[m.group(1)]] = m.group(2).strip()
            continue
        s = строка.strip()
        if s.startswith("ATTACK ") and (" не отправлен" in s or " отправлен, но" in s):
            т.атака_отвергнута.append(s.split(":", 1)[-1].strip() if ":" in s else s)
        elif s.startswith("УРОК ОТБРОШЕН"):
            т.урок_отброшен = s.split(":", 1)[-1].strip()
        elif s.startswith("УРОК ->"):
            т.урок = s.split(":", 1)[-1].strip()
            т.поля["lesson"] = т.урок
        elif s.startswith("сказано, но не сделано"):
            for слово in LP.КОМАНДЫ_СЛОВА:
                if слово in s:
                    т.расхождение_моста.append(слово)
        elif s.startswith("решение готовилось"):
            т.медленно = s
        else:
            прочее.append(s)
    return эпизоды, шапка, исходы, прочее


def длиннейший_ряд(такты: list[Такт]) -> list[tuple[str, int, int, int]]:
    """Ряды одной и той же команды подряд: (что, длина, с какой секунды, по какую).
    Повтор сам по себе не грех — BUILD декларативен и шлётся каждый такт
    нарочно. Смотреть надо на длину: восемь подряд означают, что заказ не
    проходит и модель этого не замечает."""
    ряды: dict[str, list] = {}
    итог = []
    прошлые = set()
    начало: dict[str, int] = {}
    длина: dict[str, int] = {}
    for т in такты:
        текущие = {f"{c} {r} {n}" for c, r, n in т.команды}
        for ключ in текущие:
            if ключ in прошлые:
                длина[ключ] += 1
            else:
                длина[ключ], начало[ключ] = 1, т.gt
        for ключ in прошлые - текущие:
            итог.append((ключ, длина[ключ], начало[ключ], т.gt))
        прошлые = текущие
    for ключ in прошлые:
        итог.append((ключ, длина[ключ], начало[ключ], такты[-1].gt if такты else 0))
    return sorted(итог, key=lambda x: -x[1])


def мм(gt: int) -> str:
    m, s = divmod(gt, 60)
    return f"{m}:{s:02d}"


def отчёт(такты: list[Такт], шапка: list[str], прочее: list[str]) -> None:
    print("=" * 72)
    for с in шапка[:6]:
        print(" ", с)
    print("=" * 72)
    if not такты:
        print("тактов не нашлось — это лог того формата?")
        return
    print(f"\nТАКТОВ: {len(такты)}, с {мм(такты[0].gt)} по {мм(такты[-1].gt)}")

    счёт = Counter(f"{c} {r}".strip() for т in такты for c, r, _n in т.команды)
    всего = sum(счёт.values())
    print(f"\nКОМАНДЫ ({всего} за эпизод):")
    for имя, n in счёт.most_common():
        print(f"  {n:3}×  {имя}")

    # Главное: чего не было ни разу. Отсутствие в логе не бросается в глаза.
    молчание = []
    if not any(c == "BALANCE" for т in такты for c, _r, _n in т.команды):
        молчание.append("BALANCE — ни одной за эпизод: доля крестьян по ресурсам "
                        "оставалась нативной")
    if not any(c == "TRAIN" and r == "peasant"
               for т in такты for c, r, _n in т.команды):
        молчание.append("TRAIN peasant — ни одной за эпизод: крестьян не заказывали")
    if not any(c == "ATTACK" for т in такты for c, _r, _n in т.команды):
        молчание.append("ATTACK — ни одной за эпизод: волны не собирались")
    if молчание:
        print("\nЧЕГО НЕ БЫЛО НИ РАЗУ:")
        for с in молчание:
            print(f"  {с}")

    # Сказано в тексте, но не отдано командой. Считаем сами по правилу моста,
    # чтобы разбирались и старые логи, снятые до появления этой проверки.
    строки = []
    for т in такты:
        нет = LP.названо_но_не_отдано(т.текст, т.отдано)
        if нет:
            строки.append((т.gt, нет, "мост заметил" if т.расхождение_моста else ""))
    print(f"\nСКАЗАНО, НО НЕ СДЕЛАНО: {len(строки)} тактов из {len(такты)}")
    for gt, нет, помета in строки:
        print(f"  {мм(gt)}  {', '.join(нет)}" + (f"   [{помета}]" if помета else ""))
    if строки and not any(п for _g, _н, п in строки):
        print("  (мост об этом молчал — лог снят до правки от 11.09.2026)")

    ряды = [р for р in длиннейший_ряд(такты) if р[1] >= 3]
    print(f"\nОДНА И ТА ЖЕ КОМАНДА ПОДРЯД (от трёх раз): {len(ряды)}")
    for ключ, n, с, по in ряды:
        print(f"  {n}× подряд  {ключ}   с {мм(с)} по {мм(по)}")

    отвергнуто = [(т.gt, п) for т in такты for п in т.атака_отвергнута]
    if отвергнуто:
        print(f"\nATTACK ОТВЕРГНУТ: {len(отвергнуто)}")
        for gt, п in отвергнуто:
            print(f"  {мм(gt)}  {п[:90]}")

    уроки = [(т.gt, т.урок) for т in такты if т.урок]
    брак = [(т.gt, т.урок_отброшен) for т in такты if т.урок_отброшен]
    print(f"\nУРОКИ: записано {len(уроки)}, отброшено мостом {len(брак)}")
    for gt, у in уроки:
        подозрение = LP.притязание_без_команды(
            у, {c for c, _r, _n in next(т for т in такты if т.gt == gt).команды})
        метка = f"   <- ПРИТЯЗАНИЕ БЕЗ КОМАНДЫ ({подозрение[1]})" if подозрение else ""
        print(f"  {мм(gt)}  {у[:80]}{метка}")
    for gt, у in брак:
        print(f"  {мм(gt)}  ОТБРОШЕН: {у[:80]}")

    медленно = [т for т in такты if т.медленно]
    if медленно:
        print(f"\nРЕШЕНИЕ НЕ УЛОЖИЛОСЬ В ТАКТ: {len(медленно)}")
        for т in медленно[:5]:
            print(f"  {мм(т.gt)}  {т.медленно[:90]}")

    if прочее:
        print(f"\nНЕ РАЗОБРАНО {len(прочее)} строк "
              f"(показаны первые 5 — если их много, парсер отстал от лога):")
        for с in прочее[:5]:
            print(f"  {с[:100]}")


def ответы(такты: list[Такт], путь: str) -> None:
    """Восстановить ответы модели для `llm_policy.py --replay`."""
    with open(путь, "w", encoding="utf-8") as f:
        for т in такты:
            data = {k: v for k, v in т.поля.items() if v}
            cmds = []
            for c, r, n in т.команды:
                if c == "ATTACK":
                    cmds.append({"cmd": "ATTACK", "count": n})
                elif c == "UPGRADE":
                    cmds.append({"cmd": "UPGRADE", "role": r})
                else:
                    cmds.append({"cmd": c, "role": r, "total": n})
            data["commands"] = cmds
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    print(f"\nответы для --replay: {путь} ({len(такты)} шт.)")


def трасса(путь: str, только_мысли: bool = False) -> int:
    """Разбор coss3_bot.jsonl — машинной трассы решений.

    Лог партии писан для человека и живёт одну партию; трасса писана ДЛЯ
    ОБУЧЕНИЯ: в каждой строке снимок мира, итог прошлого хода, рассуждение
    модели целиком, её урок и гипотеза, и что реально ушло в игру. По ней
    можно и воспроизвести решение, и оценить его задним числом — ровно то,
    что по TRAINING_PLAN нужно роли L2.
    """
    строки = []
    for л in open(путь, encoding="utf-8"):
        л = л.strip()
        if л:
            try:
                строки.append(json.loads(л))
            except ValueError:
                pass
    if not строки:
        print(f"{путь}: пусто")
        return 2
    # Партии режем по откату игрового времени: трасса пишется в один файл.
    партии, тек = [], []
    for р in строки:
        if тек and р.get("gt", 0) < тек[-1].get("gt", 0):
            партии.append(тек)
            тек = []
        тек.append(р)
    партии.append(тек)

    for n, п in enumerate(партии, 1):
        print("\n" + "#" * 70)
        # Записи о конце партии тактами не считаем: иначе число тактов растёт
        # там, где бот как раз перестал ходить.
        _концы = [р for р in п if р.get("finish")]
        _итог = ("".join(", " + {"win": "ПОБЕДА", "lose": "ПОРАЖЕНИЕ"}.get(
            str(р["finish"]), str(р["finish"])) for р in _концы))
        print(f"# ПАРТИЯ {n} из {len(партии)}: тактов {len(п) - len(_концы)}{_итог}, "
              f"до {п[-1].get('gt', 0)} игровой секунды")
        print("#" * 70)
        for р in п:
            gt = int(р.get("gt", 0))
            # Запись о конце партии — не такт, а его отсутствие: у неё нет ни
            # рассуждения, ни команд. Не показать её нельзя (ради неё всё и
            # затевалось), а считать тактом — значит испортить статистику
            # «тактов молча».
            if р.get("finish"):
                слово = {"win": "ПОБЕДА", "lose": "ПОРАЖЕНИЕ"}.get(
                    str(р["finish"]), str(р["finish"]))
                print(f"\n{gt // 60}:{gt % 60:02d}  === ПАРТИЯ КОНЧИЛАСЬ: {слово} ===")
                сост = р.get("state") or {}
                if сост:
                    print("        " + ", ".join(f"{k}={v}" for k, v in сост.items()))
                continue
            print(f"\n{gt // 60}:{gt % 60:02d}  {р.get('why', '')}")
            for ключ, подпись in (("ok", "идёт"), ("stuck", "не идёт"),
                                  ("cause", "почему")):
                т = str(р.get(ключ, "") or "").strip()
                if т:
                    print(f"        {подпись}: {т}")
            for ключ, подпись in (("lesson", "УРОК"), ("idea", "ГИПОТЕЗА")):
                т = str(р.get(ключ, "") or "").strip()
                if т:
                    print(f"        {подпись}: {т}")
            if только_мысли:
                continue
            for x in р.get("outcome_prev", [])[:3]:
                print(f"        итог прошлого: {x[:110]}")
            если = р.get("cmds", [])
            if если:
                print("        отдано: " + ", ".join(
                    f"{c['cmd']} {c['a1']}->{c['a2']}" for c in если))
            if р.get("attack"):
                # Без пометки про вето разбор считал бы заниженную волну ушедшей
                # и снова искал причину провала не там, где она есть.
                вето = str(р.get("veto", "") or "")
                print(f"        ATTACK {р['attack']} -> {р.get('target', '')}"
                      + (" — ОТВЕРГНУТА МОСТОМ" if вето else ""))
                if вето:
                    print(f"          {вето[:150]}")
            for б in р.get("rejected", []):
                print(f"        НЕ УШЛО: {б}")

    print("\n" + "=" * 70)
    print("ГИПОТЕЗЫ ЗА ВСЕ ПАРТИИ (их НЕ возвращают в запрос — они для проверки)")
    print("=" * 70)
    идеи = [(р.get("gt", 0), str(р.get("idea", "") or "").strip()) for р in строки]
    идеи = [(g, i) for g, i in идеи if i]
    if идеи:
        for g, i in идеи:
            print(f"  {int(g) // 60}:{int(g) % 60:02d}  {i}")
    else:
        print("  ни одной. Поле idea появилось 12.09 — на старых трассах его нет")

    print("\n" + "=" * 70)
    print("УРОКИ ЗА ВСЕ ПАРТИИ")
    print("=" * 70)
    уроки = [(р.get("gt", 0), str(р.get("lesson", "") or "").strip()) for р in строки]
    уроки = [(g, u) for g, u in уроки if u]
    for g, u in уроки:
        print(f"  {int(g) // 60}:{int(g) % 60:02d}  {u}")
    if not уроки:
        print("  ни одного")

    молча = sum(1 for р in строки
                if not р.get("finish") and not str(р.get("why", "")).strip())
    print(f"\nвсего тактов {sum(1 for р in строки if not р.get('finish'))}, "
          f"гипотез {len(идеи)}, уроков {len(уроки)}"
          + (f", без объяснения {молча}" if молча else ""))
    return 0

def main() -> int:
    p = argparse.ArgumentParser(description="разбор coss3_llm.log")
    p.add_argument("лог", nargs="?", default="coss3_llm.log")
    p.add_argument("--replay-out", default="", metavar="FILE",
                   help="восстановить ответы модели для llm_policy.py --replay")
    p.add_argument("--trace", default="", metavar="FILE",
                   help="разобрать машинную трассу coss3_bot.jsonl: рассуждения, "
                        "гипотезы, уроки и что реально ушло в игру")
    p.add_argument("--ideas", action="store_true",
                   help="с --trace: только мысли модели, без команд и итогов")
    a = p.parse_args()
    if a.trace:
        if not os.path.exists(a.trace):
            print(f"нет файла {a.trace}")
            return 2
        return трасса(a.trace, a.ideas)
    if not os.path.exists(a.лог):
        print(f"нет файла {a.лог}")
        return 2
    эпизоды, шапка, исходы, прочее = разобрать(a.лог)
    эпизоды = [э for э in эпизоды if э]
    for n, такты in enumerate(эпизоды, 1):
        if len(эпизоды) > 1:
            print("\n" + "#" * 70 + f"\n# ЭПИЗОД {n} из {len(эпизоды)}\n" + "#" * 70)
        отчёт(такты, шапка if n == 1 else [],
              прочее if n == len(эпизоды) else [])
    if исходы:
        print("\nИСХОДЫ ПО СЕРИИ:")
        for и in исходы:
            print(f"  {и}")
    if a.replay_out:
        ответы([т for э in эпизоды for т in э], a.replay_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
