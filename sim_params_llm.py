# -*- coding: utf-8 -*-
"""Параметры юнитов и зданий для симулятора — читает ЛОКАЛЬНАЯ МОДЕЛЬ, проверяет код.

Зачем так. Числа механик лежат в `lib/unit.script`, в `_unit_InitBase`: одна
ветка `case` на юнит, внутри позиционные вызовы `SetObjBaseWeapon(...)`,
`SetObjBasePrice(...)`, `SetObjBaseProtection(...)` и вложенные `case nation of`
с национальными поправками. Модель читает ветку целиком и раскладывает её в
таблицу; питон делает две проверки, без которых числу модели верить нельзя
(правило 3 проекта: механики из кода, не из слов модели):

  1. КАЖДОЕ число ответа должно стоять в тексте ветки как отдельное слово —
     иначе оно помечается «не из кода» и в симулятор не идёт;
  2. базовые значения четырёх сеттеров (hp, цена, оружие, защита, время найма)
     параллельно разбираются регулярным выражением, и ответ модели сверяется с
     ними поле за полем. Доля совпадений печатается — это и есть цена доверия к
     местной модели на чтении кода, измеренная, а не предполагаемая.

Правки по нациям (`case nation of`, `case objprop.sid of` внутри ветки) регуляркой
не разбираются намеренно — это как раз то, ради чего зовётся модель.

    python3 sim_params_llm.py "<путь к игре>" [--model qwen2.5:14b] [--limit N] [--out sim/параметры_юнитов.json]

Пишет после КАЖДОЙ ветки и умеет продолжать: перезапуск доделает недостающее.
Единицы в ответе — как в коде: пауза в кадрах (1 кадр = gc_frames_to_time с),
радиусы в пикселях (делить на gc_pixels_to_tile), время найма — как в
`SetObjBaseSearchBuildVisionScore`, второе число (`_misc_BuildtimeToTime`:
val * gc_frames_to_time * gc_buildtime_modifier). Константы кладутся рядом.
"""
import json
import os
import re
import sys
import time
import urllib.request

АДРЕС = os.environ.get("OLLAMA_URL", "http://localhost:11434")
МОДЕЛЬ = "qwen2.5:14b"
ИСХОДНИК = os.path.join("data", "scripts", "lib", "unit.script")
ГЛОБАЛ = os.path.join("data", "scripts", "dmscript.global")

СХЕМА_ЗНАЧЕНИЙ = {
    "type": "object",
    "properties": {
        "maxhp": {"type": ["integer", "null"]},
        "price": {"type": "object", "properties": {k: {"type": ["integer", "null"]}
                  for k in ("food", "wood", "stone", "gold", "iron", "coal")},
                  "required": ["food", "wood", "stone", "gold", "iron", "coal"]},
        "weapons": {"type": "array", "items": {"type": "object", "properties": {
            "index": {"type": ["integer", "null"]},
            "damage": {"type": ["integer", "null"]},
            "pause_frames": {"type": ["integer", "null"]},
            "radiusmin_px": {"type": ["integer", "null"]},
            "radiusmax_px": {"type": ["integer", "null"]},
            "kind": {"type": ["string", "null"]},
            "shot_cost_iron": {"type": ["integer", "null"]},
            "shot_cost_coal": {"type": ["integer", "null"]}}}},
        "protection": {"type": "object", "properties": {k: {"type": ["integer", "null"]}
                       for k in ("pike", "sword", "bullet", "cannister", "arrow", "cannonball")},
                       "required": ["pike", "sword", "bullet", "cannister", "arrow", "cannonball"]},
        "buildtime": {"type": ["number", "null"]},
        "costpercent": {"type": ["number", "null"]},
        "usage": {"type": ["string", "null"]},
        "aiforce": {"type": ["integer", "null"]},
        "is_building": {"type": ["boolean", "null"]},
    },
    "required": ["maxhp", "price", "weapons", "protection", "buildtime", "costpercent", "usage", "aiforce", "is_building"],
}
СХЕМА = {
    "type": "object",
    "properties": {
        "sids": {"type": "array", "items": {"type": "string"}},
        "base": СХЕМА_ЗНАЧЕНИЙ,
        "overrides": {"type": "array", "items": {"type": "object", "properties": {
            "when": {"type": "string"}, "values": СХЕМА_ЗНАЧЕНИЙ}, "required": ["when", "values"]}},
    },
    "required": ["sids", "base", "overrides"],
}

ЛЕГЕНДА = """Сигнатуры сеттеров (позиционные аргументы, -1 или `default` означает «не задано» = null):
SetObjBaseWeapon(objprop, objbase, index, damage, pause, radiusmin, radiusmax, detectradiusmin, detectradiusmax, kind, bSearchMinAttackRadius)
SetObjBasePrice(objbase, food, wood, stone, gold, iron, coal)
SetObjBaseProtection(objbase, pike, sword, bullet, cannister, arrow, cannonball)
SetObjBaseSearchBuildVisionScore(objprop, objbase, searchradius, buildtime, vision, score)   -- buildtime это ВТОРОЕ число
SetObjBuildingExtProperties(objprop, objbase, maxhp, buildtime, costpercent, bcapture, score, usage, food, wood, stone, gold, iron, coal)
SetObjBuildingProperties(objprop, objbase, maxhp, buildtime, costpercent)
objbase.maxhp := N            -- здоровье
objprop.usage := gc_obj_usage_X  -- usage = "X"
objprop.aiforce := N
objprop.weapon[i].cost[gc_resource_type_iron] := N  -- shot_cost_iron оружия i (weapInd обычно 1)
kind: gc_obj_weapon_kind_pike -> "pike", _sword -> "sword", _bullet -> "bullet", и т.д.
Комментарии в {фигурных скобках} и после // — не код: {7}6 означает значение 6."""

ЗАДАНИЕ = """Ты читаешь ветку case из скрипта игры Cossacks 3 (язык похож на Pascal).
Разложи её в JSON по схеме. В `sids` — все имена юнитов из заголовка ветки.
В `base` — значения, заданные ДО первого вложенного `case`. В `overrides` — по одной записи
на каждую ветку вложенных `case nation of` / `case objprop.sid of`: `when` вида "nation=pol" или
"sid=musketeerpol" (несколько имён через запятую), `values` — только то, что там переопределено,
остальное null. Числа бери ТОЛЬКО из текста, ничего не вычисляй и не додумывай.
ОБЯЗАТЕЛЬНО перенеси в `base` каждый вызов SetObjBasePrice (шесть чисел в price) и
SetObjBaseProtection (шесть чисел в protection), если они есть в ветке до вложенного case:
пропущенная цена — это ошибка. `default` и -1 записывай как null, а не как -1.
Метка вида commonsid+'mil' — это постройка, общая для группы наций: пиши sid "common:mil",
is_building true; блоки `if (commonrus) then begin ... end` — это overrides с when "commonrus".
Метка вида csid+'cen' — постройка нации: sid "nation:cen", is_building true; блоки
`if (rus) then ...` или `case nation of` внутри — overrides с when "nation=rus".
"""


def читать(путь):
    return open(путь, encoding="latin-1").read().split("\n")


def ветки(строки):
    """Ветки верхнего уровня КАЖДОГО `case objprop.sid of` внутри _unit_InitBase.

    Юниты — один case с отступом 6 (метки `'pikeman', ... : begin`), постройки —
    ещё несколько case глубже (метки `commonsid+'mil' : begin`). Ветка тянется до
    `end;` на отступе метки; вложенные case внутри ветки уходят в неё целиком.
    """
    начало = None
    for i, s in enumerate(строки):
        if s.startswith("procedure _unit_InitBase"):
            начало = i
            break
    if начало is None:
        raise SystemExit("нет _unit_InitBase")
    из = []
    метка = re.compile(r"^(\s+)(?:commonsid\+|csid\+)?'[a-z0-9_]+'.*:\s*begin\s*$")
    кейс = re.compile(r"^(\s+)case objprop\.sid of\s*$")
    i = начало + 1
    while i < len(строки):
        s = строки[i]
        if s.startswith("procedure ") or s.startswith("function "):
            break
        m = кейс.match(s)
        if not m:
            i += 1
            continue
        отступ = len(m.group(1))
        конец_кейса = " " * отступ + "end;"
        j = i + 1
        while j < len(строки) and строки[j].rstrip() != конец_кейса:
            mm = метка.match(строки[j])
            if mm and len(mm.group(1)) == отступ + 3:
                конец_ветки = " " * (отступ + 3) + "end;"
                k = j + 1
                while k < len(строки) and строки[k].rstrip() != конец_ветки:
                    k += 1
                из.append((j + 1, k + 1, "\n".join(строки[j:k + 1])))
                j = k + 1
                continue
            j += 1
        i = j + 1
    return из


def спросить(модель, текст):
    тело = {"model": модель, "stream": False, "format": СХЕМА,
            "prompt": ЗАДАНИЕ + "\n" + ЛЕГЕНДА + "\n\nВЕТКА:\n" + текст,
            "options": {"temperature": 0, "num_predict": 6000, "num_ctx": 16384}}
    зап = urllib.request.Request(АДРЕС + "/api/generate", json.dumps(тело).encode(),
                                 {"Content-Type": "application/json"})
    t = time.time()
    d = json.loads(urllib.request.urlopen(зап, timeout=600).read())
    ответ = d.get("response") or d.get("thinking") or ""
    return без_минус_единиц(json.loads(ответ)), time.time() - t


def без_минус_единиц(з):
    """-1 в коде значит «не задано» (const default = -1): в таблице это null."""
    if isinstance(з, dict):
        return {k: без_минус_единиц(v) for k, v in з.items()}
    if isinstance(з, list):
        return [без_минус_единиц(v) for v in з]
    if isinstance(з, (int, float)) and not isinstance(з, bool) and з == -1:
        return None
    return з


def числа_в(текст):
    return set(re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])", текст))


def все_числа(значение, путь=""):
    if isinstance(значение, dict):
        for k, v in значение.items():
            yield from все_числа(v, f"{путь}.{k}")
    elif isinstance(значение, list):
        for i, v in enumerate(значение):
            yield from все_числа(v, f"{путь}[{i}]")
    elif isinstance(значение, (int, float)) and not isinstance(значение, bool):
        yield путь, значение


def база_регуляркой(текст):
    """Первые сеттеры до вложенного case — детерминированно, для сверки."""
    голова = re.split(r"\n\s+case ", текст, maxsplit=1)[0]
    голова = re.sub(r"\{[^}]*\}", "", голова)
    голова = re.sub(r"//[^\n]*", "", голова)
    из = {}
    m = re.search(r"objbase\.maxhp := (\d+)", голова)
    if m:
        из["maxhp"] = int(m.group(1))
    m = re.search(r"SetObjBasePrice\(objbase, ([^)]*)\)", голова)
    if m:
        ч = [x.strip() for x in m.group(1).split(",")]
        if len(ч) == 6 and all(re.fullmatch(r"-?\d+", x) for x in ч):
            из["price"] = dict(zip(("food", "wood", "stone", "gold", "iron", "coal"), map(int, ч)))
    m = re.search(r"SetObjBaseProtection\(objbase, ([^)]*)\)", голова)
    if m:
        ч = [x.strip() for x in m.group(1).split(",")]
        if len(ч) == 6 and all(re.fullmatch(r"-?\d+", x) for x in ч):
            из["protection"] = dict(zip(("pike", "sword", "bullet", "cannister", "arrow", "cannonball"), map(int, ч)))
    m = re.search(r"SetObjBaseWeapon\(objprop, objbase, ([^)]*)\)", голова)
    if m:
        ч = [x.strip() for x in m.group(1).split(",")]
        if len(ч) == 9:
            def н(x):
                return int(x) if re.fullmatch(r"-?\d+", x) else None
            из["weapon0"] = {"damage": н(ч[1]), "pause_frames": н(ч[2]),
                             "radiusmin_px": н(ч[3]), "radiusmax_px": н(ч[4]),
                             "kind": ч[7].replace("gc_obj_weapon_kind_", "") if ч[7].startswith("gc_") else None}
    m = re.search(r"SetObjBaseSearchBuildVisionScore\(objprop, objbase, ([^)]*)\)", голова)
    if m:
        ч = [x.strip() for x in m.group(1).split(",")]
        if len(ч) == 4 and re.fullmatch(r"-?\d+(\.\d+)?", ч[1]):
            из["buildtime"] = float(ч[1])
    m = re.search(r"SetObjBuildingProperties\(objprop, objbase, ([^)]*)\)", голова)
    if m:
        ч = [x.strip() for x in m.group(1).split(",")]
        if len(ч) == 3:
            def н3(x):
                return float(x) if re.fullmatch(r"-?\d+(\.\d+)?", x) else None
            if н3(ч[0]) is not None:
                из["maxhp"] = int(н3(ч[0]))
            из["buildtime"] = н3(ч[1])
            из["costpercent"] = н3(ч[2])
            из["is_building"] = True
    m = re.search(r"SetObjBuildingExtProperties\(objprop, objbase, ([^)]*)\)", голова)
    if m:
        ч = [x.strip() for x in m.group(1).split(",")]
        if len(ч) == 12:
            def н(x):
                return float(x) if re.fullmatch(r"-?\d+(\.\d+)?", x) else None
            из["maxhp"] = int(н(ч[0])) if н(ч[0]) is not None else None
            из["buildtime"] = н(ч[1])
            из["costpercent"] = н(ч[2])
            if all(re.fullmatch(r"-?\d+", x) for x in ч[6:12]):
                из["price"] = dict(zip(("food", "wood", "stone", "gold", "iron", "coal"), map(int, ч[6:12])))
            из["is_building"] = True
    return из


def сверка(модель_база, рег):
    """Поле за полем: совпало / расхождение / модель промолчала."""
    итог = {"совпало": 0, "расхождение": [], "нет_у_модели": []}

    def пара(имя, а, б):
        if б is None:
            return
        if а is None:
            итог["нет_у_модели"].append(имя)
        elif (isinstance(а, float) or isinstance(б, float)) and abs(float(а) - float(б)) < 1e-6 or а == б:
            итог["совпало"] += 1
        else:
            итог["расхождение"].append(f"{имя}: модель {а}, код {б}")

    пара("maxhp", модель_база.get("maxhp"), рег.get("maxhp"))
    пара("buildtime", модель_база.get("buildtime"), рег.get("buildtime"))
    пара("costpercent", модель_база.get("costpercent"), рег.get("costpercent"))
    for блок in ("price", "protection"):
        if рег.get(блок):
            мб = модель_база.get(блок) or {}
            for k, v in рег[блок].items():
                пара(f"{блок}.{k}", мб.get(k), v)
    if рег.get("weapon0"):
        оружие = [w for w in (модель_база.get("weapons") or []) if w.get("index") in (0, None)]
        w = оружие[0] if оружие else {}
        for k, v in рег["weapon0"].items():
            пара(f"weapon0.{k}", w.get(k), v)
    return итог


def константы(путь):
    из = {}
    for s in читать(путь):
        m = re.match(r"\s*(gc_obj_speed_\w+|gc_frames_to_time|gc_buildtime_modifier|gc_pixels_to_tile|gc_unit_meleeattackradius)\s*=\s*([\d.]+)", s)
        if m:
            из[m.group(1)] = float(m.group(2))
    return из


def main():
    арг = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not арг:
        raise SystemExit(__doc__)
    игра = арг[0]
    модель = МОДЕЛЬ
    предел = None
    выход = os.path.join("sim", "параметры_юнитов.json")
    for i, a in enumerate(sys.argv):
        if a == "--model":
            модель = sys.argv[i + 1]
        if a == "--limit":
            предел = int(sys.argv[i + 1])
        if a == "--out":
            выход = sys.argv[i + 1]
    строки = читать(os.path.join(игра, ИСХОДНИК))
    все = ветки(строки)
    print(f"веток в _unit_InitBase: {len(все)}; модель {модель}")
    os.makedirs(os.path.dirname(выход) or ".", exist_ok=True)
    данные = {"источник": ИСХОДНИК, "модель": модель, "константы": константы(os.path.join(игра, ГЛОБАЛ)),
              "ветки": {}}
    if os.path.exists(выход):
        try:
            данные = json.load(open(выход, encoding="utf-8"))
            данные["константы"] = константы(os.path.join(игра, ГЛОБАЛ))
        except json.JSONDecodeError:
            pass
    сделано = 0
    всего_совп = всего_расх = всего_нет = 0
    for нач, кон, текст in все:
        ключ = f"{нач}-{кон}"
        if ключ in данные["ветки"] and данные["ветки"][ключ].get("ответ"):
            continue
        if предел is not None and сделано >= предел:
            break
        try:
            ответ, сек = спросить(модель, текст)
        except Exception as e:
            print(f"  {ключ}: модель не ответила: {e!r}")
            данные["ветки"][ключ] = {"строки": [нач, кон], "ошибка": repr(e)}
            json.dump(данные, open(выход, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            continue
        слова = числа_в(текст)
        не_из_кода = [(п, з) for п, з in все_числа(ответ)
                      if str(int(з) if float(з).is_integer() else з) not in слова and str(з) not in слова]
        рег = база_регуляркой(текст)
        св = сверка(ответ.get("base") or {}, рег)
        всего_совп += св["совпало"]
        всего_расх += len(св["расхождение"])
        всего_нет += len(св["нет_у_модели"])
        данные["ветки"][ключ] = {"строки": [нач, кон], "sids_в_коде": re.findall(r"'([a-z0-9_]+)'", текст.split("\n")[0]),
                                 "ответ": ответ, "регулярка": рег, "сверка": св,
                                 "не_из_кода": [{"поле": п, "число": з} for п, з in не_из_кода],
                                 "секунд": round(сек, 1)}
        json.dump(данные, open(выход, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        сделано += 1
        имя = (ответ.get("sids") or ["?"])[0]
        print(f"  {ключ:>11} {имя:<22} {сек:5.1f} с  совпало {св['совпало']:2d}  расх {len(св['расхождение'])}  "
              f"молчит {len(св['нет_у_модели'])}  не из кода {len(не_из_кода)}"
              + (f"  | {св['расхождение'][0]}" if св["расхождение"] else ""))
    print(f"\nсделано веток: {сделано}; всего в файле: {len(данные['ветки'])} из {len(все)}")
    if всего_совп + всего_расх + всего_нет:
        print(f"сверка базовых значений с регуляркой: совпало {всего_совп}, расхождений {всего_расх}, "
              f"модель промолчала {всего_нет} → доля верных "
              f"{100 * всего_совп / (всего_совп + всего_расх + всего_нет):.0f}%")
    print(f"файл: {выход}")


if __name__ == "__main__":
    main()
