#!/usr/bin/env python3
"""Ставит мост Python<->ИИ в Cossacks 3.

    python install_bridge.py "<путь к игре>" --outdir "C:\\coss3-io"
    python install_bridge.py "<путь к игре>" --reinstall --outdir "C:\\coss3-io"
    python install_bridge.py "<путь к игре>" --uninstall
    python install_bridge.py "<путь к игре>" --reinstall --outdir D --only-state
    python install_bridge.py "<путь к игре>" --reinstall --outdir D --min-loop
    python install_bridge.py "<путь к игре>" --reinstall --outdir D --queue-builds
    python install_bridge.py "<путь к игре>" --reinstall --outdir D --human-probe
    python install_bridge.py "<путь к игре>" --reinstall --outdir D --human-state
    python install_bridge.py "<путь к игре>" --reinstall --outdir D --human-state --human-cmd
    python install_bridge.py "<путь к игре>" --reinstall --outdir D --human-state --human-cmd --cmd-level 1
    python install_bridge.py "<путь к игре>" --reinstall --outdir D --human-only --human-state --human-cmd
    python install_bridge.py "<путь к игре>" --reinstall --human-only --human-state --human-cmd --endgame

--outdir задаёт КАТАЛОГ, куда игра пишет файлы моста. Важно: папка игры в
Program Files недоступна для записи, поэтому указывайте заведомо доступную
папку (каталог должен уже существовать - движок не умеет его создавать).
Без --outdir используется относительный путь (папка игры).

Ставит три блока в data/scripts/units/global.inc/progresseconomicai.inc:
  STATE  - состояние игры, безусловно каждый тик -> coss3_eco_P<n>.dat
  IMPORT - команды бота                          <-  coss3_cmd_P<n>.dat
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import os, sys, shutil, datetime

REL_ECO = os.path.join("data", "scripts", "units", "global.inc", "progresseconomicai.inc")
REL_WAR = os.path.join("data", "scripts", "units", "global.inc", "progresswarai.inc")
REL_GUI = os.path.join("data", "gui", "menu.inc", "doprogress.inc")   # бисекция и конец партии
REL_PRG = os.path.join("data", "scripts", "units", "global.inc", "progress.inc")
HERE = os.path.dirname(os.path.abspath(__file__))

# (целевой файл, файл блока, якорь, вставлять ПОСЛЕ якоря?, маркер начала, маркер конца)
# Внутри одного файла блоки идут СНИЗУ ВВЕРХ, иначе вставка сдвинет следующий якорь.
BLOCKS = [
    (REL_ECO, "block_import.inc",
     "_ai_ResourcesDistributionScript(plind, maincid, onFood, onWood, onStone);", True,
     "// === PEACE-TIME BUILD ORDER BRIDGE: import commands ===",
     "// === END BRIDGE IMPORT ==="),
    (REL_ECO, "block_state.inc",
     "if (gPlayer[plind].aidata.centerfound) then", False,
     "// === BRIDGE STATE",
     "// === END BRIDGE STATE ==="),
    # Военный ИИ — отдельное состояние со своей областью видимости:
    # _ai_CreateAgressorArmy из экономического блока не виден.
    (REL_WAR, "block_war.inc",
     "_ai_SendAgressors(plInd);", True,
     "// === BRIDGE ATTACK",
     "// === END BRIDGE ATTACK ==="),
    # Петля эпизодов живёт на игровой стороне: чтение файлов компилируется
    # только здесь, а до интерфейса дотягиваемся через GUIExecuteState.
    (REL_PRG, "block_gameloop.inc",
     "gPlayer[plind].progresstick := gPlayer[plind].progresstick+1;", False,
     "// === BRIDGE LOOP",
     "// === END BRIDGE LOOP ==="),
]

# Зонд человеческого слота: ставится флагом --human-probe. Тик progress.inc
# выполняется для КАЖДОГО игрока, а ИИ запускается строкой выше и только для
# bai или человека с советником — значит на человеческом слоте нативного мозга
# нет вовсе, и это единственное место, откуда бот сможет им играть.
HUMAN_BLOCK = (REL_PRG, "block_human.inc",
               "gPlayer[plind].progresstick := gPlayer[plind].progresstick+1;", False,
               "// === BRIDGE HUMAN PROBE", "// === END BRIDGE HUMAN PROBE ===")

# Боевое состояние человеческого слота: ставится ТОЛЬКО после того, как зонд
# показал, что из этого состояния виден мир. Вызовов здесь втрое больше, и
# каждый лишний — риск, что скрипт не скомпилируется и игра не запустится.
HSTATE_BLOCK = (REL_PRG, "block_hstate.inc",
                "gPlayer[plind].progresstick := gPlayer[plind].progresstick+1;", False,
                "// === BRIDGE HUMAN STATE", "// === END BRIDGE HUMAN STATE ===")

# Команды человеческого слота: ставятся ПОСЛЕ состояния. Здесь бот впервые
# отдаёт приказы сам — стройка, найм, добыча, атака — вызовами движка, а не
# через очередь идей нативного ИИ.
HCMD_BLOCK = (REL_PRG, "block_hcmd.inc",
              "gPlayer[plind].progresstick := gPlayer[plind].progresstick+1;", False,
              "// === BRIDGE HUMAN COMMANDS", "// === END BRIDGE HUMAN COMMANDS ===")

# Блоки бисекции для интерфейсного актора: ставятся только флагами --min-loop / --loop N
GUI_BLOCK = (REL_GUI, "block_loop.inc",
             "ExecuteStateByFlag(gbool_gui_debug, 'ShowEditorInfo', False);", True,
             "// === BRIDGE LOOP", "// === END BRIDGE LOOP ===")

# Конец партии, флаг --endgame. Ставится в ИНТЕРФЕЙСНЫЙ актор, и это не вкусовщина:
# когда партия кончается, движок зовёт SetProgressingPauseMode(True) (doprogress.inc,
# ветка victorystate<>none) и симуляция встаёт. Всё, что живёт в Progress, замирает
# вместе с ней — поэтому мост не видел поражения и не мог начать следующую партию.
# DoProgress интерфейса идёт сквозь эту паузу и сквозь главное меню.
ENDGAME_BLOCK = (REL_GUI, "block_endgame.inc",
                 "ExecuteStateByFlag(gbool_gui_debug, 'ShowEditorInfo', False);", True,
                 "// === BRIDGE ENDGAME", "// === END BRIDGE ENDGAME ===")

# BLOCKS меняется по флагам (--human-*, --human-only, бисекция), поэтому снимать
# и обнаруживать установленное по нему нельзя: `--uninstall` без флагов не знал
# про человеческие блоки и молча оставлял их в игре. Снятие обязано видеть ВСЁ,
# что этот установщик умеет ставить.
ALL_BLOCKS = tuple(BLOCKS) + (HUMAN_BLOCK, HSTATE_BLOCK, HCMD_BLOCK, GUI_BLOCK,
               ENDGAME_BLOCK)
# Уровни бисекции блока команд носят те же маркеры, что и полный блок, поэтому
# снятие и обнаружение работают для них без отдельных записей.


# Точечные замены в родном коде: вставкой блока их не сделать.
# (файл, как было, как стало). Обратимы: --uninstall возвращает как было.
REPLACES = [
    # Выключатель нативного билд-ордера. bprogressEconomy по умолчанию True,
    # поэтому без команды MODE поведение игры не меняется.
    (REL_ECO,
     "   if (gPlayer[plind].aidata.controllednations[i]) then",
     "   if (gPlayer[plind].aidata.controllednations[i]) and "
     "(gPlayer[plind].aidata.bprogressEconomy) then"),
    # Выключатель нативной АТАКИ. Гасим ровно `_ai_SendAgressors` и ничего
    # больше: `_ai_ExecuteArmies` должен работать, иначе наши собственные волны
    # никуда не пойдут, а `_ai_ProgressDefenders` держит оборону базы.
    # bprogressWar объявлен движком (classes.script:2616) и никем не читается —
    # тот же приём, что с bprogressEconomy. По умолчанию True, так что без
    # команды MODE с двумя аргументами поведение игры не меняется.
    (REL_WAR,
     "   _ai_SendAgressors(plInd);",
     "   if (gPlayer[plInd].aidata.bprogressWar) then _ai_SendAgressors(plInd);"),
]

# Необязательная замена, флаг --queue-builds. Третий параметр
# _player_OrderUnitsToBuild — это clrord, «сбросить прежние приказы»
# (readorder.inc: `if clrord then _unit_ClearOrders(handle)`). У игрока false
# получается при клике с Shift: приказ дописывается в очередь. В конвейере ИИ
# стоит true, поэтому вызов крестьян на ВТОРУЮ стройку сбрасывает им приказ на
# первую, и они её бросают. С false они достроят первую и пойдут на вторую.
#
# НЕ ПРОВЕРЕНО НА ЖИВОЙ ИГРЕ. Возможный риск: если конвейер зовёт крестьян на
# один и тот же проект повторно, приказы будут накапливаться. Поэтому по
# умолчанию выключено; снимается через --uninstall, как и всё остальное.
QUEUE_REPLACE = (
    REL_ECO,
    "_player_OrderUnitsToBuild(gPlayer[plind].aidata.ailist, trgHnd, true, false, true);",
    "_player_OrderUnitsToBuild(gPlayer[plind].aidata.ailist, trgHnd, false, false, true);")


# Маркеры прежних версий моста — чтобы --uninstall чистил и их тоже.
LEGACY_MARKS = [
    ("// === PEACE-TIME BUILD ORDER BRIDGE: export state ===", "// === END BRIDGE EXPORT ==="),
    ("// === BRIDGE HEARTBEAT", "// === END BRIDGE HEARTBEAT ==="),
]


def load_block(name: str, outdir: str) -> list[str]:
    with open(os.path.join(HERE, name), encoding="latin-1", newline="") as f:
        text = f.read()
    lines = text.replace("@@OUT@@", outdir).split("\r\n")
    while lines and lines[-1] == "":     # хвостовой перевод строки дал бы пустую
        lines.pop()                      # строку, которую --uninstall не снимает
    return lines


def find_line(lines: list[str], needle: str) -> int:
    hits = [i for i, l in enumerate(lines) if needle in l]
    if len(hits) != 1:
        raise SystemExit(f"якорь встречается {len(hits)} раз, ожидался 1:\n  {needle!r}\n"
                         "Версия игры отличается — правьте вручную.")
    return hits[0]


def counts(lines: list[str]) -> tuple[int, int]:
    seg = [l.split("[*] = ;", 1)[-1].strip() for l in lines]
    return sum(s == "begin" for s in seg), sum(s in ("end", "end;") for s in seg)


def strip_blocks(lines: list[str]) -> int:
    """Удаляет все установленные блоки. Возвращает число удалённых."""
    removed = 0
    pairs = [(b[4], b[5]) for b in ALL_BLOCKS] + LEGACY_MARKS
    for mark_a, mark_b in pairs:
        while any(mark_a in l for l in lines):
            i = next(k for k, l in enumerate(lines) if mark_a in l)
            j = next(k for k, l in enumerate(lines) if mark_b in l)
            if i > 0 and lines[i - 1].strip() == "":
                i -= 1
            del lines[i:j + 1]
            removed += 1
    return removed


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    argv = sys.argv[1:]
    game = argv[0]
    reinstall = "--reinstall" in argv
    uninstall = "--uninstall" in argv and not reinstall
    queue_builds = "--queue-builds" in argv
    outdir = ""
    if "--outdir" in argv:
        outdir = argv[argv.index("--outdir") + 1]
        if not os.path.isdir(outdir):
            raise SystemExit(f"каталог не существует: {outdir}\n"
                             "Создайте его — движок этого не умеет.")
        outdir = outdir.rstrip("\\/") + "\\"

    loop_level = ""
    if "--loop" in argv:
        loop_level = argv[argv.index("--loop") + 1]
        if loop_level not in ("1", "2", "3"):
            raise SystemExit("--loop принимает 1, 2 или 3")
        print(f"режим бисекции: блок петли уровня {loop_level}")
    min_loop = "--min-loop" in argv
    if min_loop or loop_level:
        BLOCKS.append(GUI_BLOCK)          # бисекция: дополнительно патчим интерфейс
    if min_loop:
        print("режим бисекции: вместо полного блока петли ставится минимальный зонд")

    # Правила хакатона: в игре не должно быть ничего, кроме нашего бота. С этим
    # флагом старые блоки для компьютерного слота не ставятся вовсе, и точечные
    # замены (выключатели нативного ИИ) тоже не нужны: на человеческом слоте
    # нативный ИИ не запускается сам.
    human_only = "--human-only" in argv
    if human_only:
        # Убираем блоки КОМПЬЮТЕРНОГО моста (состояние, импорт команд, атака) и
        # точечные замены. Петля эпизодов остаётся: она висит на интерфейсном
        # игроке, нативного ИИ не трогает и даёт NEW/END/пульс, без которых
        # llm_policy.py --episodes не сможет начать следующую партию.
        BLOCKS[:] = [b for b in BLOCKS if b[1] == "block_gameloop.inc"]
        print("только человеческий слот: блоки компьютерного моста не ставятся "
              "(петля эпизодов остаётся)")

    if "--endgame" in argv:
        BLOCKS.append(ENDGAME_BLOCK)
        print("конец партии: интерфейс пишет coss3_gui.dat и принимает NEW "
              "после победы или поражения")
    if "--human-probe" in argv:
        BLOCKS.append(HUMAN_BLOCK)
        print("зонд человеческого слота: пишет coss3_probe_P<n>.dat каждый тик")
    if "--human-state" in argv:
        BLOCKS.append(HSTATE_BLOCK)
        print("состояние человеческого слота: coss3_eco_P<n>.dat раз в игровую секунду")
    if "--human-cmd" in argv:
        # Бисекция блока команд. Он единственный, что разделяет работающую
        # ступень 2 и мёртвую ступень 3, а статические проверки в нём чисты —
        # значит режем и ищем половину, на которой тик перестаёт выполняться.
        уровень = ""
        if "--cmd-level" in argv:
            уровень = argv[argv.index("--cmd-level") + 1]
            УРОВНИ = ("1", "2", "3a", "3b", "3")
            if уровень not in УРОВНИ:
                raise SystemExit("--cmd-level принимает: " + ", ".join(УРОВНИ))
        if уровень:
            рел, _, якорь, после, м1, м2 = HCMD_BLOCK
            BLOCKS.append((рел, f"block_hcmd_{уровень}.inc", якорь, после, м1, м2))
            что = {"1": "только сторож и включение лога, файлы не читаются",
                   "2": "+ чтение файла команд, BUILD и TRAIN",
                   "3a": "+ только BALANCE на добычу (без шахт и UPGRADE)",
                   "3b": "+ шахты (без UPGRADE)",
                   "3": "+ BALANCE, шахты и UPGRADE (всё, кроме ATTACK)"}[уровень]
            print(f"бисекция команд, уровень {уровень}: {что}")
        else:
            BLOCKS.append(HCMD_BLOCK)
            print("команды человеческого слота: BUILD/TRAIN/BALANCE/ATTACK своими руками")

    only_state = "--only-state" in argv or "--only-heartbeat" in argv
    if only_state:
        print("режим бисекции: ставится ТОЛЬКО блок состояния (без импорта и атаки)")

    # Интерфейсный файл в списке всегда: даже когда мы туда ничего не ставим,
    # с него нужно снять блок, оставшийся от бисекции прошлых версий.
    targets = []                    # [(rel, [блоки этого файла])]
    for rel in dict.fromkeys([b[0] for b in ALL_BLOCKS] + [REL_GUI]):
        targets.append((rel, [b for b in BLOCKS if b[0] == rel]))

    for rel, _ in targets:
        if not os.path.isfile(os.path.join(game, rel)):
            raise SystemExit(f"не найден {os.path.join(game, rel)}\n"
                             "Укажите корень игры (где cossacks.exe).")

    # Молчаливый отброс неотличим от бездействия: если блок числится в BLOCKS,
    # но не попал ни в одну цель, установка обязана упасть здесь, а не оставить
    # игрока с "установлено" в консоли и пустым каталогом после боя.
    покрыты = {b[1] for _, bs in targets for b in bs}
    потеряны = [b[1] for b in BLOCKS if b[1] not in покрыты]
    if потеряны:
        raise SystemExit("блоки не попали ни в один файл: " + ", ".join(потеряны))


    # Проверка блоков ДО того, как тронули игру. Неизвестное имя или сбитый
    # баланс begin/end означает, что скрипт не скомпилируется, а игра не
    # запустится. Дешевле остановиться здесь, чем искать это потом в бою.
    if not uninstall:
        try:
            import verify_blocks
            корп, бин = verify_blocks.корпус(game)
            плохие = [b[1] for b in BLOCKS
                      if not verify_blocks.проверить(os.path.join(HERE, b[1]), корп, бин)]
            if плохие:
                raise SystemExit("проверка блоков не пройдена: " + ", ".join(плохие) +
                                 "\nставить нельзя — игра не запустится")
        except ImportError:
            print("verify_blocks.py рядом нет — ставлю без проверки блоков")

    plan = []                       # что писать, после того как всё сойдётся
    for rel, blocks in targets:
        path = os.path.join(game, rel)
        raw = open(path, "rb").read().decode("latin-1")
        if "\r\n" not in raw:
            raise SystemExit(f"{rel}: файл без CRLF — похоже, испорчен редактором. "
                             "Восстановите из бэкапа.")
        lines = raw.split("\r\n")
        all_marks = [b[4] for b in ALL_BLOCKS] + [m[0] for m in LEGACY_MARKS]
        installed = any(any(m in l for m in all_marks) for l in lines)
        before = counts(lines)

        # точечные замены для этого файла
        text = "\r\n".join(lines)
        # при снятии точечные замены откатываем всегда, даже с --human-only:
        # иначе флаг установки решал бы, что останется в игре после отката
        замены = [] if (human_only and not uninstall) else list(REPLACES)
        if queue_builds or uninstall:
            замены.append(QUEUE_REPLACE)   # при снятии откатываем всегда
        for rel_r, was, now in замены:
            if rel_r != rel:
                continue
            if uninstall:
                if text.count(now) == 1:
                    text = text.replace(now, was)
                    print(f"{rel}: замена откачена")
            else:
                if text.count(now) == 1:
                    pass                      # уже заменено
                elif text.count(was) == 1:
                    text = text.replace(was, now)
                    print(f"{rel}: точечная замена применена")
                elif (rel_r, was, now) == QUEUE_REPLACE:
                    print(f"{rel}: строку для --queue-builds не нашёл, пропускаю")
                else:
                    raise SystemExit(f"{rel}: не нашёл строку для замены ровно один раз "
                                     f"— версия игры отличается, правьте вручную")
        lines = text.split("\r\n")


        if uninstall:
            if not installed:
                print(f"{rel}: мост не установлен, нечего снимать")
                plan.append((path, rel, None, 0))
                continue
            n = strip_blocks(lines)
            print(f"{rel}: снято блоков {n}")
            plan.append((path, rel, lines, len(lines)))
            continue

        if installed and not reinstall:
            print(f"{rel}: мост уже установлен. Для обновления: --reinstall")
            plan.append((path, rel, None, 0))
            continue
        if installed:
            n = strip_blocks(lines)
            print(f"{rel}: старая версия снята (блоков {n})")
            before = counts(lines)

        use = [b for b in blocks if not only_state or b[1] == "block_state.inc"]
        delta = (0, 0)
        for _, fname, anchor, after, _, _ in use:      # снизу вверх по файлу
            if fname == "block_loop.inc":
                if min_loop:
                    fname = "block_loop_min.inc"
                elif loop_level:
                    fname = f"block_loop_{loop_level}.inc"
            blk = load_block(fname, outdir)
            d = counts(blk)
            delta = (delta[0] + d[0], delta[1] + d[1])
            at = find_line(lines, anchor)
            at = at + 1 if after else at
            lines[at:at] = [""] + blk        # всегда пустая строка перед блоком

        if not use and not installed:
            plan.append((path, rel, None, 0))    # тут нечего ставить и нечего снимать
            continue
        got, want = counts(lines), (before[0] + delta[0], before[1] + delta[1])
        if got != want:
            raise SystemExit(f"{rel}: целостность нарушена: begin/end {got}, "
                             f"ожидалось {want} — ни один файл не тронут")
        plan.append((path, rel, lines, len(lines)))

    action = "снят" if uninstall else "установлен"
    for path, rel, lines, nlines in plan:
        if lines is None:
            continue
        bak = f"{path}.bak-{datetime.datetime.now():%Y%m%d-%H%M%S}"
        shutil.copy2(path, bak)
        open(path, "wb").write("\r\n".join(lines).encode("latin-1"))
        print(f"мост {action}: {rel}")
        print(f"  бэкап: {os.path.basename(bak)}")
        print(f"  строк: {nlines}")
    # Последняя проверка — по тому, что реально лежит на диске. Установщик уже
    # один раз отрапортовал "мост установлен", не поставив зонд: список целей
    # собирался до разбора флагов. Читаем файлы заново и требуем маркер каждого
    # блока, который обещали поставить.
    if not uninstall:
        не_встали = []
        for _, fname, _, _, mark, _ in BLOCKS:
            путь = os.path.join(game, next(b[0] for b in BLOCKS if b[1] == fname))
            if mark not in open(путь, "rb").read().decode("latin-1"):
                не_встали.append(fname)
        if не_встали:
            raise SystemExit("ОБЕЩАНО, НО НЕ ВСТАЛО: " + ", ".join(не_встали) +
                             "\nИгра сейчас в промежуточном состоянии — "
                             "откатите: install_bridge.py <игра> --uninstall")
        print("проверка после записи: все блоки на месте (" +
              ", ".join(b[1] for b in BLOCKS) + ")")

    if action == "установлен":
        print(f"файлы моста: {outdir or '<папка игры>'}coss3_{{eco,map,cmd,atk}}_P<n>.dat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
