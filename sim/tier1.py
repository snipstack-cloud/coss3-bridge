# -*- coding: utf-8 -*-
"""Ярус 1 в симуляторе: скриптовый дебют моста (`debut.py`) плюс поддержание без модели.

Проверяется то, что в живой игре включается ключами `--debut 20 --auto-train 1
--auto-seed 1 --auto-food 1` (в мосте — одним ключом `--tier1`): пока бойцов
меньше двадцати, команды даёт `debut.Дебют`, модель молчит; дальше правила
поддержания — бесконечный найм крестьян при еде выше 500, посев при пустом поле,
люди на еду, добор шахтёров. Стратегических решений (волны, апгрейды, вторая
казарма) здесь НЕТ намеренно: это ярус 3.

Сравнение с командами записи (то, что модель делала в облаке) по тем же
партиям: экономика и армия на 300 и 600 с, первый боец, простой, и сколько
вызовов облака дебют снимает.

ПРОВЕРЕНО ЖИВОЙ СЕРИЕЙ 25.09 (tier1, 3 копии, против base28; разбор
`разборы/ЯРУС1_ПРОТИВ_BASE28.md`): вызовов облака 42 против 58, первый боец 78 с
против 215, двадцатый 164 против 326, цена $0,33 против $0,45 — сошлось с
симулятором. НЕ сошлись две планки, и это ошибки симулятора, не игры:
  * дерево здесь голодало (43 против 764) из-за МОЕГО правила поддержания
    (свободных — еде и золоту); в игре ярус 1 работает правилами моста
    (--auto-food и прочие), и дерево там СИЛЬНОЕ: 1114 против 590;
  * планка простоя «38–42 %» была из base27 и считалась иначе; у base28 простой
    первых 200 с — 19,3 %, ярус 1 даёт 22,7 %.
Правило поддержания ниже приведено к мостовому смыслу: свободных не отдавать
еде и золоту целиком.

    python3 sim/tier1.py <корень с прогонами> [ещё...]
"""
import glob
import os
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/coss3-bridge"))
import sim as SIM       # noqa: E402
import replay as R      # noqa: E402
import debut as D       # noqa: E402
from coss3_bridge import ROLE, RESOURCE  # noqa: E402

ОБР_РОЛЬ = {v: k for k, v in ROLE.items()}
ОБР_РЕС = {v: k for k, v in RESOURCE.items()}


def в_словарь(c) -> dict:
    """Command моста -> словарь, который читает `sim.команда`."""
    d = {"cmd": c.cmd, "a1": c.a1, "a2": c.a2}
    if c.upg:
        d["upg"] = c.upg
    return d


class Ярус1:
    def __init__(self, n=20):
        self.дебют = D.Дебют(n)
        self.решений_дебюта = 0
        self.решений_всего = 0
        self.готов_gt = None
        self.посев_gt = -1000

    def __call__(self, st: dict) -> list:
        gt = int(float(st.get("gametime") or 0))
        self.решений_всего += 1
        if not self.дебют.готов(st):
            self.решений_дебюта += 1
            cmds, _ = self.дебют.такт(st, gt)
            return [в_словарь(c) for c in cmds]
        if self.готов_gt is None:
            self.готов_gt = gt
        # --- поддержание (то же, что --auto-* в мосте) ---
        из = []
        еда = float(st.get("food") or 0)
        очередь = str(st.get("train_now") or "")
        if float(st.get("centers") or 0) > 0 and еда >= 500 and "pea" not in очередь:
            из.append({"cmd": "TRAIN", "role": "peasant", "total": -1})
        if float(st.get("ba17") or 0) > 0 and "pikeman" not in очередь:
            из.append({"cmd": "TRAIN", "role": "infantry17", "total": -1})
        if float(st.get("mills") or 0) > 0 and int(float(st.get("food_ready") or 0)) == 0 and gt - self.посев_gt >= 60:
            из.append({"cmd": "SEED", "total": 2})
            self.посев_gt = gt
        # расширение хозяйства без стратегии: шахта золота, когда шахтёры заняли все места
        # (модель делала это в каждой партии, 382 BUILD minegold на 52 партии), дом при
        # полном жилье — иначе найм крестьян встаёт
        шахт = float(st.get("mines_gold") or 0)
        if (шахт < 4 and float(st.get("on_gold") or 0) >= 5 * шахт and float(st.get("building_now") or 0) == 0
                and float(st.get("wood") or 0) >= 100 and float(st.get("stone") or 0) >= 100):
            из.append({"cmd": "BUILDERS", "total": 5})
            из.append({"cmd": "BUILD", "role": "minegold", "total": int(шахт) + 1})
        if (float(st.get("my_farm") or 0) - float(st.get("my_farmused") or 0) <= 5 and float(st.get("building_now") or 0) == 0
                and float(st.get("wood") or 0) >= 100 and float(st.get("stone") or 0) >= 100):
            из.append({"cmd": "BUILDERS", "total": 5})
            из.append({"cmd": "BUILD", "role": "house", "total": int(float(st.get("houses") or 0)) + 1})
        простой = float(st.get("idle_pea") or 0)
        if простой >= 4:
            # свободных — на еду, пока на еде меньше трети деревни, иначе на дерево и камень
            крест = max(float(st.get("peasants") or 1), 1)
            # ДВЕ ТРЕТИ НА ЕДЕ ДО 7:00 (27.09, §16 — разгадка первой победы). Прежде
            # целью была ТРЕТЬ, и это ровно поведение проигравших копий: в живой серии
            # early_push победитель держал на еде 16 крестьян из 25 (64 %) и еда падала
            # под порог 500 лишь в 29 % тактов, а проигравшие — 12 из 22 и 7 из 22 при
            # 74 % тактов под порогом. Порог глушит найм целиком, поэтому казарма стояла
            # готовой и не производила. После 7:00 треть, как было: армия уже собрана, а
            # еда нужна на апгрейды.
            цель_еды = (2 * крест / 3) if gt < 420 else (крест / 3)
            if float(st.get("on_food") or 0) < цель_еды:
                # еде — не всех свободных, а до трети деревни; остальным дерево и камень
                до_трети = max(0.0, цель_еды - float(st.get("on_food") or 0))
                на_еду = min(простой, до_трети)
                из.append({"cmd": "BALANCE", "role": "food", "total": int(float(st.get("on_food") or 0) + на_еду)})
                остаток = простой - на_еду
                if остаток >= 2:
                    из.append({"cmd": "BALANCE", "role": "wood", "total": int(float(st.get("on_wood") or 0) + остаток // 2)})
                    из.append({"cmd": "BALANCE", "role": "stone", "total": int(float(st.get("on_stone") or 0) + остаток - остаток // 2)})
            elif float(st.get("on_gold") or 0) < 5 * float(st.get("mines_gold") or 0):
                из.append({"cmd": "BALANCE", "role": "gold", "total": int(5 * float(st.get("mines_gold") or 0))})
            else:
                из.append({"cmd": "BALANCE", "role": "wood", "total": int(float(st.get("on_wood") or 0) + простой // 2)})
                из.append({"cmd": "BALANCE", "role": "stone", "total": int(float(st.get("on_stone") or 0) + простой - простой // 2)})
        return из


def срез(история, t):
    for s in история:
        if float(s["gametime"]) >= t:
            return s
    return история[-1]


def первый_боец(история):
    for s in история:
        if float(s.get("mil_inf") or 0) >= 1:
            return float(s["gametime"])
    return None


def main(корни):
    каталоги = []
    for корень in корни:
        каталоги += sorted(os.path.dirname(x) for x in glob.glob(os.path.join(корень, "**", "coss3_snap.jsonl"), recursive=True))
    поля = ("food", "wood", "stone", "gold", "iron", "peasants", "mil_inf", "idle_pea")
    итог = {"ярус1": {300: {k: [] for k in поля}, 600: {k: [] for k in поля}, "боец": [], "дебют_решений": [], "всего_решений": [], "готов": []},
            "запись": {300: {k: [] for k in поля}, 600: {k: [] for k in поля}, "боец": []}}
    n = 0
    for d in каталоги:
        try:
            з = SIM.Запись(d)
        except Exception:
            continue
        if len(з.снапы) < 20 or len(з.такты) < 5:
            continue
        n += 1
        пол = Ярус1()
        сим, ист = SIM.партия(d, пол, seed=n)
        for t in (300, 600):
            s = срез(ист, t)
            for k in поля:
                итог["ярус1"][t][k].append(float(s.get(k) or 0))
        итог["ярус1"]["боец"].append(первый_боец(ист) or 1200)
        итог["ярус1"]["дебют_решений"].append(пол.решений_дебюта)
        итог["ярус1"]["всего_решений"].append(пол.решений_всего)
        итог["ярус1"]["готов"].append(пол.готов_gt or 1200)
        # запись: в том же симуляторе, её командами
        r = R.прогнать(d, n)
        if r:
            сим2 = r[2]
            # у replay нет истории — восстановим срезы по её снимкам факта
            for t in (300, 600):
                f = з.снимок_до(t)
                for k in поля:
                    итог["запись"][t][k].append(float(f.get(k) or 0))
            итог["запись"]["боец"].append(next((float(x["gametime"]) for x in з.снапы if float(x.get("mil_inf") or 0) >= 1), 1200))
    print(f"партий {n}. Ярус 1 в симуляторе против ФАКТА записи (модель в облаке), медианы:")
    for t in (300, 600):
        print(f"  на {t} с:  " + "  ".join(f"{k} {S.median(итог['ярус1'][t][k]):.0f}/{S.median(итог['запись'][t][k]):.0f}" for k in поля))
    print(f"  первый боец: {S.median(итог['ярус1']['боец']):.0f} / {S.median(итог['запись']['боец']):.0f} с")
    print(f"  дебют готов (20 бойцов) на {S.median(итог['ярус1']['готов']):.0f} с; решений дебюта без облака "
          f"{S.median(итог['ярус1']['дебют_решений']):.0f} из {S.median(итог['ярус1']['всего_решений']):.0f} "
          f"({100 * S.median(итог['ярус1']['дебют_решений']) / S.median(итог['ярус1']['всего_решений']):.0f} %)")


if __name__ == "__main__":
    арг = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not арг:
        raise SystemExit(__doc__)
    main(арг)
