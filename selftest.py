#!/usr/bin/env python3
"""Самопроверка команд моста на ЖИВОЙ игре: доходят ли они до неё.

    python selftest.py                       # все проверки по очереди
    python selftest.py --only build,attack
    python selftest.py --list

Зачем. Когда модель не проходит цепочку, причин две: она не пользуется
командой, или команда не работает. Различить это по логу партии нельзя, потому
что молчаливый отказ выглядит так же, как нежелание. Здесь команды шлются
напрямую, без модели, и результат сверяется со счётчиками состояния.

ВНИМАНИЕ: проверка МЕНЯЕТ идущую партию — строит, нанимает, шлёт волну,
переставляет крестьян. Пускать только на тестовом бою, не на важном.

Нужна идущая схватка с компьютерным противником: без неё смотреть нечего.

На mock_game.py гонять смысла мало: мок понимает BUILD и TRAIN, а BALANCE,
UPGRADE и ATTACK не реализует — по ним будет «НЕТ», и это про мок, не про мост.
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import os
import time

from coss3_bridge import Bridge, build, train, upgrade, mode, balance
from llm_policy import find_ai_plind, diagnose


def свежее(br: Bridge, было: dict, timeout: float = 25.0) -> dict:
    """Ждём состояние, отличающееся от прежнего по игровому времени."""
    гр = time.monotonic() + timeout
    последнее = было
    while time.monotonic() < гр:
        try:
            st = br.wait_state(timeout=min(8.0, timeout))
        except TimeoutError:
            break
        последнее = st
        if int(st.get("gametime", 0)) > int(было.get("gametime", -1)):
            return st
    return последнее


def отправить(br: Bridge, cmds: list, попыток: int = 12) -> bool:
    """Слать, пока игра не забрала предыдущий файл команд.

    Bridge.send отказывается писать поверх незабранного файла и возвращает
    False. Без этого повтора первая же проверка падала с «файл не записался»,
    выходила не дождавшись, и следующие падали так же — каскадом.
    """
    for _ in range(попыток):
        if br.send(cmds):
            return True
        time.sleep(1.0)
    return False


def дождаться_ратушу(br: Bridge, сек: int) -> tuple[bool, str]:
    """Ждём, пока заказанная ратуша достроится.

    BUILD только НАЧИНАЕТ стройку: слот занимается сразу, а centers растёт
    через десятки секунд. Без ожидания проверки кузницы и найма пропускались
    с «нет ратуши», хотя она уже строилась.
    """
    гр = time.monotonic() + сек
    try:
        st = br.read_state() or br.wait_state(timeout=10)
    except TimeoutError:
        return False, "состояние не обновляется — партия идёт?"
    последнее = -1
    while time.monotonic() < гр:
        c = _ц(st, "centers")
        if c >= 1:
            return True, f"ратуша готова через {int(сек - (гр - time.monotonic()))} с"
        занято = _ц(st, "build_slots_used")
        if занято != последнее:
            последнее = занято
            print(f"      жду ратушу: слотов занято {занято}, "
                  f"игровое время {st.get('gametime')}", flush=True)
        st = свежее(br, st, timeout=10)
    return False, f"за {сек} с ратуша не достроилась (слотов занято " \
                  f"{_ц(st, 'build_slots_used')})"


def обстановка(st: dict) -> str:
    """Почему могло не сработать: ресурсы и предпосылки, одной строкой.

    BUILD и TRAIN идут через _ai_TryUnit и оба требуют РАТУШУ: кузница требует
    центр, крестьян нанимает центр. Без центров обе команды провалятся молча, а
    BALANCE — нет, ему здания не нужны. Поэтому центры печатаем первыми.
    """
    ч = [f"центров={st.get('centers')}",
         f"centerfound={st.get('centerfound')}",
         f"крестьян={st.get('peasants')}",
         f"на еде/дереве/камне={st.get('on_food')}/{st.get('on_wood')}/{st.get('on_stone')}",
         f"слоты={st.get('build_slots_used')}/{st.get('build_slots_total')}",
         f"еда={st.get('food')}", f"дерево={st.get('wood')}",
         f"камень={st.get('stone')}", f"золото={st.get('gold')}"]
    м = st.get("my_farm")
    if м is not None:
        ч.append(f"мест={st.get('my_farmused')}/{м}")
    if not int(float(st.get("centers", 0) or 0)):
        ч.append("<-- ЦЕНТРОВ НЕТ: ни постройка, ни найм крестьян невозможны")
    if str(st.get("centerfound", "")).lower() in ("0", "false", "нет", ""):
        ч.append("<-- centerfound=false: ИИ ещё не признал базу своей, "
                 "его конвейер идей может не работать")
    св = _ц(st, "peasants") - _ц(st, "on_food") - _ц(st, "on_wood") - _ц(st, "on_stone")
    if св <= 0:
        ч.append(f"<-- СВОБОДНЫХ КРЕСТЬЯН НЕТ (все {_ц(st, 'peasants')} заняты): "
                 f"BALANCE перераспределяет только свободных и потому не подействует")
    return " ".join(ч)


def _ц(st: dict, key: str) -> int:
    try:
        return int(float(st.get(key, 0)))
    except (TypeError, ValueError):
        return 0


# (имя, что шлём, ожидаемые сдвиги, пояснение)
# Сдвиг: (ключ, "+" вырос | "-" упал). Годится ЛЮБОЙ из перечисленных, но
# только в нужную сторону: иначе за успех сойдёт естественный дрейф чисел.
# Своё окно ожидания на проверку: у найма оно ДОЛГОЕ. Крестьянин появляется
# примерно раз в 15 с и только когда хватает ресурсов, так что 25 с — окно, в
# которое он может не успеть. На этом я уже ошибся и решил, что найм не работает.
ОКНО = {"train": 90, "upgrade": 60}

ПРОВЕРКИ = [
    ("center",  "BUILD center 1",    [("centers", "+"), ("build_slots_used", "+")],
     "ратуша: без неё ни постройка, ни найм не работают"),
    ("build",   "BUILD smith 1",     [("smiths", "+"), ("build_slots_used", "+")],
     "постройка: кузница или занятый слот стройки"),
    ("train",   "TRAIN peasant +3",  [("peasants", "+")],
     "найм: число крестьян"),
    ("balance", "BALANCE stone 70",  [("on_stone", "+"), ("on_wood", "-")],
     "распределение: крестьян на камне больше или на дереве меньше"),
    ("upgrade", "UPGRADE food140",   [("upg_food140", "+")],
     "апгрейд: отметка о выполнении (нужна мельница!)"),
    ("attack",  "ATTACK 1",          [("my_agressors", "+"), ("my_freewar", "-")],
     "атака: агрессоров больше или свободных меньше"),
]


def одна(br: Bridge, имя: str, ждать: int) -> tuple[str, str]:
    """Возвращает (итог, пояснение). Итог: РАБОТАЕТ | НЕТ | ПРОПУЩЕНА."""
    до = br.read_state() or br.wait_state(timeout=20)
    сдвиги = next(к for н, _, к, _ in ПРОВЕРКИ if н == имя)
    ключи = [k for k, _ in сдвиги]
    было = {k: _ц(до, k) for k in ключи}

    if имя == "center":
        ok = отправить(br, [build("center", _ц(до, "centers") + 1)])
    elif имя == "build":
        if not _ц(до, "centers"):
            return "ПРОПУЩЕНА", "нет ратуши, а кузница её требует — сперва center"
        ok = отправить(br, [build("smith", _ц(до, "smiths") + 1)])
    elif имя == "train":
        if not _ц(до, "centers"):
            return "ПРОПУЩЕНА", "нет ратуши, а крестьян нанимает она — сперва center"
        ok = отправить(br, [train("peasant", _ц(до, "peasants") + 3)])
    elif имя == "balance":
        ok = отправить(br, [balance("stone", 70), balance("wood", 30)])
    elif имя == "upgrade":
        if not _ц(до, "mills"):
            return "ПРОПУЩЕНА", "нет мельницы, а food140 — её апгрейд"
        if _ц(до, "upg_food140"):
            return "ПРОПУЩЕНА", "food140 уже сделан"
        ok = отправить(br, [upgrade("food140")])
    elif имя == "attack":
        if до.get("peacemode"):
            return "ПРОПУЩЕНА", "перемирие: атака запрещена игрой"
        if _ц(до, "my_freewar") < 1:
            return "ПРОПУЩЕНА", "нет свободных бойцов"
        if _ц(до, "my_agressors") > 0:
            return "ПРОПУЩЕНА", "волна уже в пути, новая её сломает"
        ok = br.attack(1)
    else:
        return "ПРОПУЩЕНА", "неизвестная проверка"

    if not ok:
        return "НЕТ", ("игра не забирает файл команд 12 секунд. Мост установлен "
                       "и партия идёт? Проверьте: python run_episodes.py --check")
    if имя != "attack":
        if not br.wait_consumed(timeout=20):
            return "НЕТ", ("файл команды записан, но игра его не забрала за 20 с — "
                           "блок импорта не работает или партия на паузе")

    гр = time.monotonic() + ждать
    st = до
    мимо = []
    while time.monotonic() < гр:
        st = свежее(br, st, timeout=10)
        стало = {k: _ц(st, k) for k in ключи}
        годные, прочие = [], []
        for k, знак in сдвиги:
            if стало[k] == было[k]:
                continue
            строка = f"{k} {было[k]}->{стало[k]}"
            выросло = стало[k] > было[k]
            (годные if (выросло == (знак == "+")) else прочие).append(строка)
        if годные:
            return "РАБОТАЕТ", ", ".join(годные)
        мимо = прочие
    итог = ", ".join(f"{k}={было[k]}" for k in ключи)
    хвост = f"; менялось не туда: {', '.join(мимо)}" if мимо else ""
    совет = ""
    if имя == "train":
        совет = ("\n      найм идёт ~1 крестьянин за 15 с и только при ресурсах: "
                 "если дерево и камень на нуле, это не поломка команды.\n"
                 "      проверить долгим удержанием: "
                 "python send.py train:peasant=40 --ticks 40")
    return "НЕТ", (f"за {ждать} с нужного сдвига не было ({итог}){хвост}\n"
                   f"      обстановка: {обстановка(st)}{совет}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expandvars(os.path.expanduser("~/coss3-io")))
    ap.add_argument("--plind", type=int, default=None)
    ap.add_argument("--only", default="", help="через запятую: center,build,train,balance,upgrade,attack")
    ap.add_argument("--wait", type=int, default=25, help="сек на подтверждение одной команды")
    ap.add_argument("--wait-center", type=int, default=180,
                    metavar="сек",
                    help="сколько ждать достройки ратуши перед проверкой кузницы и найма")
    ap.add_argument("--no-mode", action="store_true", help="не выключать нативный ИИ")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        for имя, что, сдвиги, зачем in ПРОВЕРКИ:
            по = ", ".join(f"{k}{з}" for k, з in сдвиги)
            print(f"  {имя:8s} {что:18s} ждём {по:34s} {зачем}")
        return 0

    d = os.path.expandvars(a.dir)
    plind = a.plind if a.plind is not None else find_ai_plind(d)
    if plind is None:
        diagnose(d)
        return 1
    br = Bridge(d, plind)
    st = br.read_state() or br.wait_state(timeout=30)
    print(f"слот P{plind}, игровое время {st.get('gametime')} с")
    print("ВНИМАНИЕ: проверка меняет идущую партию — строит, нанимает, бьёт\n")

    if not a.no_mode:
        if отправить(br, [mode(True)]) and br.wait_consumed(timeout=20):
            print("нативный билд-ордер выключен, чтобы он не мешал считать\n")
        else:
            print("MODE не ушёл: игра не забирает файл команд. Мост установлен?\n"
                  "  проверить: python run_episodes.py --check\n")
            return 1

    выбор = [x.strip() for x in a.only.split(",") if x.strip()] or [н for н, *_ in ПРОВЕРКИ]
    итоги = []
    for имя in выбор:
        # Кузница и найм требуют ГОТОВУЮ ратушу, а BUILD только начинает
        # стройку. Если её заказали в этом же прогоне — ждём достройки.
        текущее = br.read_state() or st
        if имя in ("build", "train") and not _ц(текущее, "centers") \
                and "center" in выбор and a.wait_center > 0:
            ок, почему = дождаться_ратушу(br, a.wait_center)
            print(f"      {почему}", flush=True)
        что = next((ч for н, ч, *_ in ПРОВЕРКИ if н == имя), None)
        if что is None:
            print(f"  {имя}: неизвестная проверка, пропускаю")
            continue
        ждать = max(a.wait, ОКНО.get(имя, 0))
        сколько = f" (жду до {ждать} с)" if ждать != a.wait else ""
        print(f"  {имя:9s} шлю {что}{сколько} …", flush=True)
        итог, почему = одна(br, имя, ждать)
        знак = {"РАБОТАЕТ": "+", "НЕТ": "!", "ПРОПУЩЕНА": "~"}[итог]
        print(f"  {знак} {имя:9s} {итог}: {почему}\n", flush=True)
        итоги.append((имя, итог, почему))

    print("=" * 60)
    работают = [и for и, т, _ in итоги if т == "РАБОТАЕТ"]
    нет = [и for и, т, _ in итоги if т == "НЕТ"]
    мимо = [и for и, т, _ in итоги if т == "ПРОПУЩЕНА"]
    if работают:
        print(f"работают: {', '.join(работают)}")
    if мимо:
        print(f"не проверены: {', '.join(мимо)} — условия не сложились, см. выше")
    if нет:
        print(f"НЕ РАБОТАЮТ: {', '.join(нет)}")
        print("  Если модель не пользуется этими командами — виноват не промпт,")
        print("  а мост. Смотреть блок в progresseconomicai.inc и лог игры.")
        return 1
    print("все проверенные команды доходят до игры")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
