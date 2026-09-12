#!/usr/bin/env python3
"""Проверка блоков .inc до установки в игру: баланс, кодировка, имена.

    python3 verify_blocks.py "<путь к игре>" block_*.inc

Каждое имя ищется СНАЧАЛА в data/scripts (там живут скриптовые функции), потом
в строках cossacks.exe (там движковые). Если нет нигде — блок не ставить:
неизвестное имя не компилируется, а несобравшийся скрипт не даёт игре
запуститься. Это ровно тот случай, когда «проверю на игре» стоит вечера.
"""
import re, sys, os

ВСТРОЕННЫЕ = {
    "IntToStr","FloatToStr","BoolToStr","Round","Min","Max","Abs","Sqr","Floor",
    "StrLength","SameText","Cos","Sin","TObj","TRes","TArmy","TSquad","TObjProp",
}

# Границы наших вставок. Всё между ними — не игра, а мы, и в корпус проверки
# имён такое попадать не должно.
МАРКЕРЫ = [("// === BRIDGE", "// === END BRIDGE"),
           ("// === PEACE-TIME BUILD ORDER BRIDGE", "// === END BRIDGE")]


def без_наших_блоков(d: str) -> str:
    for нач, кон in МАРКЕРЫ:
        while нач in d:
            i = d.index(нач)
            j = d.find(кон, i)
            if j < 0:
                d = d[:i]
                break
            k = d.find("\n", j)
            d = d[:i] + (d[k:] if k >= 0 else "")
    return d


def корпус(игра):
    """Тексты скриптов игры и строки её бинарника — одной парой.

    Без grep и strings: этот скрипт запускается на Windows, где их нет, и
    падение верификатора останавливало установку на ровном месте.
    """
    куски = []
    корень = os.path.join(игра, "data", "scripts")
    for путь, _, файлы in os.walk(корень):
        for имя in файлы:
            # .bak-* — старые копии наших же правок, по ним проверять нельзя
            if имя.endswith((".script", ".inc")) and ".bak" not in имя:
                try:
                    with open(os.path.join(путь, имя), "rb") as f:
                        d = f.read().decode("latin-1", "replace")
                except OSError:
                    continue
                # Вырезаем НАШИ блоки, а файл оставляем: иначе имя, которого в
                # игре нет, нашлось бы в нашем же установленном коде и прошло бы
                # как существующее. Целиком файл выбрасывать нельзя — в
                # progresseconomicai.inc объявлены родные _ai_TryUnit и другие.
                куски.append(без_наших_блоков(d))
    т = "\n".join(куски)
    # Имена движковых функций лежат в exe как обычный ASCII: подстрочного
    # поиска по всему файлу достаточно, разбирать формат не нужно.
    try:
        with open(os.path.join(игра, "cossacks.exe"), "rb") as f:
            б = f.read().decode("latin-1", "replace")
    except OSError:
        б = ""
        print("   ~ cossacks.exe не прочитан: движковые имена проверить нечем")
    return т, б


def область_видимости(строки):
    """Переменная, объявленная внутри begin..end и использованная после его
    закрытия. Для движка это ошибка КОМПИЛЯЦИИ, и падает вся секция — ровно так
    в 2018-м не работал первый мост (PROGRESS.md 5.4), и ровно так 12.09 встала
    игра: три заблудившихся `end;` вынесли BALANCE, шахты и UPGRADE наружу из
    цикла по командам, где их hccmd/hca1/hca2 уже не существовали.

    ВНИМАНИЕ: это ПОДСКАЗКА, а не приговор. Проверено 12.09: родной код игры
    даёт 10 таких мест в progress.inc и 517 в progresswarai.inc, то есть диалект
    так переменные НЕ ограничивает и сама по себе находка ошибкой не является.
    Ценность в другом: у наших блоков, написанных строже, счётчик обычно ноль,
    и его рост означает, что структура поехала — например, лишний `end;` вынес
    ветку наружу. Именно так нашлись три заблудившихся `end;` в block_hcmd.inc.
    Поэтому — предупреждение, не СТОП.
    """
    стек = [set()]
    объявлены = set()
    беда = []
    for н, л in enumerate(строки, 1):
        if "[*] = " not in л:
            continue
        c = л.split("[*] = ", 1)[1]
        c = c[1:] if c.startswith(";") else c
        c = re.sub(r"//.*$", "", c)
        for м in re.finditer(r"\bvar\s+([A-Za-z_][A-Za-z0-9_, ]*?)\s*:", c):
            for имя in м.group(1).split(","):
                стек[-1].add(имя.strip())
                объявлены.add(имя.strip())
        for имя in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", c):
            if имя in объявлены and not any(имя in s for s in стек):
                беда.append((н, имя))
        for t in re.findall(r"\b(begin|case|end)\b", c):
            if t in ("begin", "case"):
                стек.append(set())
            elif len(стек) > 1:
                стек.pop()
    return беда

def объявления(т):
    """имя -> (мин, макс) параметров. `a, b : T` считается за два."""
    из = {}
    for m in re.finditer(r"\b(?:procedure|function)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", т):
        имя, пар = m.group(1), m.group(2).strip()
        n = 0
        for группа in пар.split(";") if пар else []:
            n += len([x for x in группа.split(":")[0].split(",") if x.strip()])
        было = из.get(имя)
        из[имя] = (min(было[0], n), max(было[1], n)) if было else (n, n)
    return из


def _аргументов(текст, поз):
    глуб = 0; n = 1; строка = None; i = поз
    while i < len(текст):
        c = текст[i]
        if строка:
            if c == строка: строка = None
        elif c in "'\"": строка = c
        elif c in "([": глуб += 1
        elif c in ")]":
            глуб -= 1
            if глуб == 0:
                return 0 if not текст[поз+1:i].strip() else n
        elif c == "," and глуб == 1: n += 1
        i += 1
    return None


def арность(строки, декл):
    """Число аргументов в вызове против объявления в игре и в движке."""
    склеен = ""; карта = []
    for н, л in enumerate(строки, 1):
        if "[*] = " not in л: continue
        c = л.split("[*] = ", 1)[1]
        c = c[1:] if c.startswith(";") else c
        карта.append((len(склеен), н))
        склеен += re.sub(r"//.*$", "", c) + " "
    def номер(поз):
        m = 0
        for p, н in карта:
            if p <= поз: m = н
            else: break
        return m
    беды = []
    for m in re.finditer(r"\b([A-Za-z_]\w{3,})\s*\(", склеен):
        имя = m.group(1)
        if имя not in декл: continue
        n = _аргументов(склеен, m.end()-1)
        if n is None: continue
        мин, макс = декл[имя]
        if not (мин <= n <= макс):
            беды.append((номер(m.start()), имя, n, мин, макс))
    return беды

def дом_функций(игра):
    """Где объявлена каждая функция игры. Нужно, чтобы отличить lib/ (видно из
    ЛЮБОГО состояния) от функций, объявленных внутри конкретного состояния.

    Куплено дорого 12.09: `_order_OrderUnitsToGainResource` живёт внутри
    progresseconomicai.inc, из состояния Progress не видна, и один такой вызов
    уронил весь тик — игра переставала играть, а верификатор говорил ОК, потому
    что имя-то в data/scripts есть.
    """
    дом = {}
    корень = os.path.join(игра, "data", "scripts")
    for путь, _, файлы in os.walk(корень):
        for имя in файлы:
            if not имя.endswith((".script", ".inc")) or ".bak" in имя:
                continue
            п = os.path.join(путь, имя)
            try:
                d = open(п, "rb").read().decode("latin-1", "replace")
            except OSError:
                continue
            d = re.sub(r"//.*$", "", d, flags=re.M)
            отн = os.path.relpath(п, корень).replace("\\", "/")
            for m in re.finditer(r"\b(?:procedure|function)\s+([A-Za-z_]\w*)\s*\(", d):
                дом.setdefault(m.group(1), set()).add(отн)
    return дом


# Приведения типов, а не вызовы: писать их можно, объявления функции у них нет.
ТИПЫ = {"TObj", "TRes", "TArmy", "TSquad", "TObjProp", "TPlayerArgs", "TEnemyInfo"}

# Куда какой блок ставится. Функция, объявленная в ЭТОМ же файле, блоку видна —
# именно поэтому компьютерный мост законно зовёт _ai_TryUnit. Таблица повторяет
# BLOCKS из install_bridge.py; при расхождении верить установщику.
ЦЕЛЬ = {
    "block_import.inc": "units/global.inc/progresseconomicai.inc",
    "block_state.inc":  "units/global.inc/progresseconomicai.inc",
    "block_war.inc":    "units/global.inc/progresswarai.inc",
}


def цель_блока(файл: str) -> str:
    имя = os.path.basename(файл)
    if имя in ЦЕЛЬ:
        return ЦЕЛЬ[имя]
    if имя.startswith("block_loop"):
        return "../gui/menu.inc/doprogress.inc"        # интерфейсный актор
    return "units/global.inc/progress.inc"             # человеческий слот и петля

def проверить(файл, т, б, декл=None, дом=None):
    сырое = open(файл,"rb").read()
    текст = сырое.decode("latin-1")
    строки = текст.split("\r\n") if "\r\n" in текст else текст.split("\n")
    сырое_тело = "\n".join(l.split("[*] = ;",1)[-1] for l in строки)
    # Комментарии выкидываем: в них и «end», и слова со скобками, и кириллица.
    # Иначе инструмент кричит на собственную документацию.
    тело = "\n".join(re.sub(r"//.*$", "", l) for l in сырое_тело.split("\n"))
    # begin/end считаем СЛОВАМИ по всему телу: в этом диалекте пишут и
    # `if ... then begin` одной строкой, и построчный счёт врёт.
    # `case ... of ... end` закрывается тем же end, что и begin: считаем оба.
    beg = len(re.findall(r"\bbegin\b", тело)) + len(re.findall(r"\bcase\b", тело))
    end = len(re.findall(r"\bend\b", тело))
    плохо = []
    # Форма строки. Каждая строка блока обязана быть ровно одним `[*] = ` и кодом
    # после него: движок читает файл как список «ключ = значение», и строка без
    # префикса просто не станет кодом, а строка с ДВУМЯ префиксами станет кодом
    # `[*] = ;` — синтаксической ошибкой. И то и другое роняет всё состояние
    # скрипта, то есть игру. 12.09 в block_hcmd.inc нашлись обе беды разом
    # (объявление hccid без префикса и два сдвоенных префикса), и верификатор их
    # пропустил: он снимал префикс split'ом и дальше про форму строки не думал.
    кривые = []
    for н, л in enumerate(строки, 1):
        if not л.strip():
            continue
        if л.count("[*] = ") != 1 or л.split("[*] = ", 1)[0].strip():
            кривые.append(н)
    if кривые:
        плохо.append("строки не в форме `[*] = <код>`: " +
                     ", ".join(str(н) for н in кривые[:8]) +
                     ("..." if len(кривые) > 8 else ""))
    if beg != end: плохо.append(f"баланс begin/end: {beg}/{end}")
    вне = область_видимости(строки)
    if вне:
        видно = ", ".join(f"{и} (строка {н})" for н, и in вне[:4])
        print(f"   ~ {os.path.basename(файл)}: {len(вне)} имён используются после "
              f"закрытия своего begin..end — {видно}. Это ПОДСКАЗКА, не ошибка: "
              "так пишет и сама игра. Но если у этого блока раньше был ноль, "
              "значит структура поехала — ищите лишний или недостающий end;")
    # Не-ASCII в КОДЕ ломает latin-1 чтение установщиком; в комментариях —
    # только уродует лог игры, это предупреждение, а не стоп.
    if any(ord(c) > 127 for c in тело):
        плохо.append("не-ASCII в коде")
    elif any(b > 127 for b in сырое):
        print(f"   ~ {os.path.basename(файл)}: не-ASCII только в комментариях "
              f"(в игре будет мусор вместо букв, но код цел)")
    # Свои переменные не проверяем: `var x : Integer` и `var x, y : Float`.
    свои = set()
    for м in re.finditer(r"\bvar\s+([A-Za-z_][A-Za-z0-9_, ]*?)\s*:", тело):
        свои |= {и.strip() for и in м.group(1).split(",")}
    # Обращение к элементу массива — не вызов функции: берём только имена со
    # скобкой, а квадратные исключаем, иначе локальные массивы лезут в отчёт.
    имена = set(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]{3,})\s*\(', тело))
    неизвестные = [n for n in sorted(имена)
                   if n not in ВСТРОЕННЫЕ and n not in свои and n not in т and n not in б]
    if неизвестные: плохо.append("нет в игре: " + ", ".join(неизвестные))
    if дом:
        мины = []
        for н in sorted(имена):
            if н in ВСТРОЕННЫЕ or н in ТИПЫ or н in свои:
                continue
            места = дом.get(н)
            своя = цель_блока(файл)
            if места and not any(м.startswith("lib") or м == своя for м in места):
                мины.append(f"{н} (объявлена в {sorted(места)[0]})")
        if мины:
            плохо.append("функция локальна для ЧУЖОГО состояния скрипта, из нашего "
                         "она не видна и вызов не скомпилируется: " + ", ".join(мины))
    if декл:
        ар = арность(строки, декл)
        if ар:
            плохо.append("неверное число аргументов: " + "; ".join(
                f"{и} на строке {н}: передано {д}, объявлено "
                + (str(мин) if мин == макс else f"{мин}..{макс}")
                for н, и, д, мин, макс in ар[:4]))
    print(f"{os.path.basename(файл):22} строк {len(строки):4}  begin/end {beg}/{end}  "
          f"имён {len(имена):3}  {'ОК' if not плохо else 'СТОП'}")
    for p in плохо: print("   !", p)
    return not плохо

if __name__ == "__main__":
    игра = sys.argv[1]
    т, б = корпус(игра)
    # Объявления берём и из скриптов, и из строк движка в exe: около 5700 штук.
    декл = объявления(т)
    for имя, (мин, макс) in объявления(б).items():
        если = декл.get(имя)
        декл[имя] = (min(если[0], мин), max(если[1], макс)) if если else (мин, макс)
    дом = дом_функций(игра)
    ок = all([проверить(f, т, б, декл, дом) for f in sys.argv[2:]])
    raise SystemExit(0 if ок else 1)
