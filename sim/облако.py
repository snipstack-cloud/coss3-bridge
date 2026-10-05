#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ОБЛАЧНАЯ МОДЕЛЬ ИЗ РАЗВИЛКИ — что сделала бы модель моста из сохранённого состояния живой партии (5.10, §99).

Из снимка момента (как `развилка.построить`: армии, хозяйство, прокачки из записи; его найм и форма
по записи, реакции — агент) симулятор ведёт партию, а решения раз в ШАГ секунд принимает ОБЛАЧНАЯ
модель через тот же путь, что живой мост: `llm_policy.situation` строит промпт от состояния (с
подсказками `hints_vs_player.txt` и системным промптом человеческого слота), `llm_policy.ask`
зовёт модель через OpenRouter (ключ `nim_key.txt`), `llm_policy.to_commands` разбирает ответ в
приказы, которые симулятор исполняет как мост. Сравниваются модели между собой и с ветками
`развилка.py` (ждать / удар). Цена: ~16 вызовов на партию при шаге 15 с.

    python3 sim/облако.py ~/coss3-res-игрок-отл/igrok_04_10_p5/1 --t 660 --модели deepseek/deepseek-v4.1-flash,anthropic/claude-fable-5 --зёрен 2
"""
import json
import os
import statistics as St
import sys

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
sys.path.insert(0, os.path.dirname(К))

ШАГ = 15.0
ВЕХИ = (780.0, 827.0, 900.0)


def _команды_из(ответ, st, LP):
    """Ответ модели → приказы симулятора, тем же разбором, что мост (`to_commands`), и тем же
    переводом ударов и движений, что в живом цикле."""
    from tier1 import в_словарь
    (cmds, attack, why, брак, цель_атаки, движение, цель_движения, клетка, контракт,
     кем_атака, кем_движение) = LP.to_commands(ответ, None, LP.взятые_апгрейды(st), st=st)
    из = [в_словарь(c) for c in cmds]
    кл = клетка if isinstance(клетка, (list, tuple)) and len(клетка) == 2 else (None, None)
    if attack and attack > 0:
        d = {"cmd": "ATTACK", "count": int(attack), "target": str(цель_атаки or "base")}
        if кем_атака:
            d["who"] = str(кем_атака)
        if d["target"] == "cell" and кл[0] is not None:
            d["cx"], d["cy"] = int(кл[0]), int(кл[1])
        if isinstance(контракт, dict) and контракт.get("via"):
            d["via"] = контракт["via"]
        из.append(d)
    if движение and движение > 0:
        ц = str(цель_движения or "")
        if ц.startswith("engage:"):
            d = {"cmd": "ENGAGE", "target": ц.split(":", 1)[1]}
            if d["target"] == "cell" and кл[0] is not None:
                d["cx"], d["cy"] = int(кл[0]), int(кл[1])
        elif ц in ("retreat", "retreat_cell"):
            d = {"cmd": "RETREAT", "count": int(движение)}
        else:
            d = {"cmd": "MOVE", "count": int(движение), "target": ц or "home"}
            if ц == "cell" and кл[0] is not None:
                d["cx"], d["cy"] = int(кл[0]), int(кл[1])
        if кем_движение:
            d["who"] = str(кем_движение)
        из.append(d)
    return из, why, брак


def партия(каталог, t, модель, seed, вид="p3о", сухо=False, журнал=None):
    import llm_policy as LP
    import развилка as РВ
    import sim as SIM
    сим, куча = РВ.построить(каталог, t, вид, seed)
    подсказки = LP.load_hints(os.path.join(os.path.dirname(К), "hints_vs_player.txt"))
    система = LP.SYSTEM + LP.SYSTEM_HUMAN
    client = None
    if not сухо:
        from openai import OpenAI
        key, _ = LP.load_key("")
        client = OpenAI(base_url=LP.BASE_URL, api_key=key)
    history, вехи, решения, отказов = [], {}, [], [0]
    конец = float(сим.з.снапы[-1]["gametime"])
    след = сим.t
    while сим.t < конец and not сим.исход:
        if сим.t >= след:
            st = сим.состояние()
            prompt = LP.situation(st, {}, history, подсказки)
            if сухо:
                ответ = {"commands": [], "why": "сухо"}
            else:
                try:
                    ответ = LP.ask(client, модель, prompt, False, system=система)
                except Exception as e:
                    # отказ провайдера (content_filter и т.п.) — такт без приказов, но вслух
                    ответ = {"commands": [], "why": f"ОТКАЗ МОДЕЛИ: {str(e)[:90]}"}
                    отказов[0] += 1
            из, why, брак = _команды_из(ответ, st, LP)
            сим.команды(из)
            сводка = ", ".join(f"{c.get('cmd')} {c.get('count', c.get('total', ''))} {c.get('target', c.get('role', ''))}{(' who=' + c['who']) if c.get('who') else ''}" for c in из if c.get("cmd") in ("ATTACK", "MOVE", "RETREAT", "ENGAGE", "STAGE"))
            решения.append((int(сим.t), сводка or "—", str(why or "")[:80], len(брак)))
            history.append(f"{int(сим.t // 60)}:{int(сим.t % 60):02d} {сводка or 'без приказов волне'}")
            history = history[-6:]
            if журнал is not None:
                журнал.append((int(сим.t), prompt, ответ, из))
            след += ШАГ
        сим.такт()
        for в in ВЕХИ:
            if в not in вехи and сим.t >= в:
                вехи[в] = (сим.my_mil_lost, сим.убито_бойцов, sum(sum(г["состав"].values()) for г in сим.группы), сим.враг.всего())
    SIM.ФОРМА_ВРАГА = None
    return dict(модель=модель, seed=seed, вехи=вехи, наши=сим.my_mil_lost, его=сим.убито_бойцов, отказов=отказов[0],
                армия=sum(sum(г["состав"].values()) for г in сим.группы), его_армия=сим.враг.всего(), решения=решения)


def main():
    каталог = os.path.expanduser(next(a for a in sys.argv[1:] if not a.startswith("--")))
    t = float(sys.argv[sys.argv.index("--t") + 1]) if "--t" in sys.argv else 660.0
    зёрен = int(sys.argv[sys.argv.index("--зёрен") + 1]) if "--зёрен" in sys.argv else 2
    модели = (sys.argv[sys.argv.index("--модели") + 1] if "--модели" in sys.argv else "deepseek/deepseek-v4.1-flash").split(",")
    вид = sys.argv[sys.argv.index("--вид") + 1] if "--вид" in sys.argv else "p3о"
    сухо = "--сухо" in sys.argv
    вых = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    все = []
    for м in модели:
        for s in range(зёрен):
            р = партия(каталог, t, м, 100 + s, вид, сухо)
            все.append(р)
            строка = " | ".join(f"{int(в // 60)}:{int(в % 60):02d} {р['вехи'][в][0]:3.0f}/{р['вехи'][в][1]:3.0f}" for в in ВЕХИ if в in р["вехи"])
            print(f"{м:32} зерно {s}: {строка} | конец {р['наши']:.0f}/{р['его']:.0f} армии {р['армия']:.0f}/{р['его_армия']:.0f}" + (f" | ОТКАЗОВ МОДЕЛИ {р['отказов']}" if р.get('отказов') else ""), flush=True)
            for tt, св, why, бр in р["решения"][:8]:
                print(f"    {tt // 60}:{tt % 60:02d} {св}" + (f"   [{why}]" if why else "") + (f" брак {бр}" if бр else ""), flush=True)
    if вых:
        json.dump(все, open(вых, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("\nМЕДИАНЫ по моделям (потери с 11:00 наши/его к 13:00, 13:47, 15:00; размен):")
    for м in модели:
        рр = [x for x in все if x["модель"] == м]
        print(f"  {м:32} " + " | ".join(f"{int(в // 60)}:{int(в % 60):02d} {St.median(x['вехи'][в][0] for x in рр if в in x['вехи']):3.0f}/{St.median(x['вехи'][в][1] for x in рр if в in x['вехи']):3.0f}" for в in ВЕХИ)
              + f" | размен {sum(x['его'] for x in рр) / max(sum(x['наши'] for x in рр), 1):.2f} | армии {St.median(x['армия'] for x in рр):.0f}/{St.median(x['его_армия'] for x in рр):.0f}")


if __name__ == "__main__":
    main()
