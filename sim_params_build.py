# -*- coding: utf-8 -*-
"""Собрать параметры симулятора в один файл: код побеждает модель, темпы — из трасс.

Вход: `sim/параметры_юнитов.json` (локальная модель + регулярка, `sim_params_llm.py`)
и `sim/темпы.json` (`sim_rates.py`). Выход: `sim/параметры.json` — на каждый sid
разрешённые значения ДЛЯ НАШЕЙ НАЦИИ и у каждого поля источник:

    код         — число прочитано регуляркой из вызова сеттера (истина);
    модель      — число дала модель, и оно стоит в тексте ветки как слово;
    модель!     — модель дала число, которого в тексте ветки НЕТ: в симулятор не идёт.

Правила разрешения:
  * где регулярка и модель расходятся, берётся код, расхождение записывается;
  * цена всегда задаётся шестью числами (`SetObjBasePrice`): null внутри заданной
    цены — это 0 (модель пишет null вместо нуля в 54 полях из 600);
  * поправки нации: записи `overrides` с `when` вида nation=net / sid=...net /
    commoneur — накладываются поверх базы; наша нация — 13 = net (`match.dat`,
    `_country_IDToBoolean`: net = 13), группа общих построек — eur;
  * производные единицы: время в секундах (кадр = gc_frames_to_time, стройка ещё
    на gc_buildtime_modifier), радиусы в клетках (gc_pixels_to_tile).

    python3 sim_params_build.py [--nation net] [--out sim/параметры.json]
"""
import json
import os
import sys

НАЦИЯ = "net"
ГРУППА = {"rus": "rus", "ukr": "ukr", "tur": "tur", "alg": "tur", "spa": "spa", "por": "spa"}


def цена_без_null(p):
    if not isinstance(p, dict) or all(v is None for v in p.values()):
        return None
    return {k: (0 if v is None else v) for k, v in p.items()}


def наложить(база, значения, источник, поля_источников):
    for k, v in (значения or {}).items():
        if v is None or v == [] or v == {}:
            continue
        if k == "price":
            v = цена_без_null(v)
            if v is None:
                continue
        if k == "protection" and all(x is None for x in v.values()):
            continue
        база[k] = v
        поля_источников[k] = источник


def разрешить(ветка, нация, группа, не_из_кода):
    ответ = ветка.get("ответ") or {}
    рег = ветка.get("регулярка") or {}
    поля = {}
    база = {}
    # 1. модель — база
    наложить(база, ответ.get("base"), "модель", поля)
    # 2. код побеждает
    for k, v in рег.items():
        if k == "weapon0":
            оружие = база.get("weapons") or [{}]
            w = dict(оружие[0]) if оружие else {}
            for kk, vv in v.items():
                if vv is not None:
                    w[kk] = vv
            w.setdefault("index", 0)
            база["weapons"] = [w] + list(оружие[1:])
            поля["weapons[0]"] = "код"
        elif v is not None:
            база[k] = v
            поля[k] = "код"
    # 3. поправки нации
    метки = {f"nation={нация}", f"common{группа}", нация}
    применено = []
    for o in ответ.get("overrides") or []:
        when = str(o.get("when") or "")
        части = {x.strip() for x in when.replace(";", ",").split(",")}
        подходит = bool(части & метки) or any(x.startswith("sid=") and x.endswith(нация) for x in части)
        if подходит:
            наложить(база, o.get("values"), f"модель, поправка {when}", поля)
            применено.append(when)
    # 4. числа не из кода — пометить
    плохие = {x["поле"] for x in не_из_кода}
    for k in list(поля):
        if any(k.split("[")[0] in п for п in плохие) and поля[k].startswith("модель"):
            поля[k] += "!"
    return база, поля, применено


def производные(база, к):
    из = {}
    if база.get("buildtime") is not None:
        из["buildtime_s"] = round(база["buildtime"] * к["gc_frames_to_time"] * к["gc_buildtime_modifier"], 2)
    оружие = []
    for w in база.get("weapons") or []:
        d = dict(w)
        if d.get("pause_frames") is not None:
            d["pause_s"] = round(d["pause_frames"] * к["gc_frames_to_time"], 3)
        for a in ("radiusmin_px", "radiusmax_px"):
            if d.get(a) is not None:
                d[a.replace("_px", "_tiles")] = round(d[a] / к["gc_pixels_to_tile"], 3)
        оружие.append(d)
    if оружие:
        из["weapons"] = оружие
    return из


def main():
    нация = НАЦИЯ
    выход = os.path.join("sim", "параметры.json")
    for i, a in enumerate(sys.argv):
        if a == "--nation":
            нация = sys.argv[i + 1]
        if a == "--out":
            выход = sys.argv[i + 1]
    группа = ГРУППА.get(нация, "eur")
    юниты = json.load(open(os.path.join("sim", "параметры_юнитов.json"), encoding="utf-8"))
    темпы = json.load(open(os.path.join("sim", "темпы.json"), encoding="utf-8"))
    к = юниты["константы"]
    итог = {"нация": нация, "группа_построек": группа, "константы": к,
            "темпы_из_трасс": {k: v for k, v in темпы.items() if k not in ("источник", "как_читать")},
            "объекты": {}, "расхождения_модели_с_кодом": [], "чисел_не_из_кода": 0,
            "открытые_вопросы": [
                "buildtime пикинёра 144 -> 45 с по формуле движка, а казарма выпускает 10,9 в минуту "
                "(5,5 с на бойца) по 1901 такту трасс: второе число SetObjBaseSearchBuildVisionScore — "
                "не время найма. В симулятор идёт темп из трасс.",
                "добыча в трассах — верхняя оценка (только шаги с приростом); стройка и найм списывают "
                "ресурсы в те же шаги."]}
    for ключ, ветка in юниты["ветки"].items():
        if "ответ" not in ветка:
            continue
        база, поля, применено = разрешить(ветка, нация, группа, ветка.get("не_из_кода") or [])
        база.update(производные(база, к))
        sids = ветка.get("sids_в_коде") or []
        первая = ветка["ответ"].get("sids") or sids
        имя = (первая[0] if первая else ключ)
        итог["объекты"][имя] = {"sids": sids or первая, "строки": ветка["строки"], "значения": база,
                                "источники": поля, "поправки_нации": применено}
        for р in ветка["сверка"]["расхождение"]:
            итог["расхождения_модели_с_кодом"].append(f"{имя}: {р}")
        итог["чисел_не_из_кода"] += len(ветка.get("не_из_кода") or [])
    os.makedirs(os.path.dirname(выход) or ".", exist_ok=True)
    json.dump(итог, open(выход, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"объектов {len(итог['объекты'])}, расхождений модели с кодом {len(итог['расхождения_модели_с_кодом'])}, "
          f"чисел не из кода {итог['чисел_не_из_кода']} (помечены '!')")
    print("%-14s %5s %6s %-30s %-22s %s" % ("sid", "hp", "стр,с", "цена f/w/s/g/i/c", "оружие dmg/pause_s/rmax", "защита p/s/b"))
    for имя in ("pikeman", "musketeer", "dragoon", "officer", "drummer", "peaeng", "peasant", "cen", "bar", "bla", "aca", "mil", "gol", "hou", "sto"):
        o = итог["объекты"].get(имя)
        if not o:
            for k, v in итог["объекты"].items():
                if имя in v["sids"]:
                    o = v
                    break
        if not o:
            continue
        з = o["значения"]
        p = з.get("price") or {}
        w = (з.get("weapons") or [{}])[0]
        pr = з.get("protection") or {}
        print("%-14s %5s %6s %-30s %-22s %s" % (
            имя, з.get("maxhp"), з.get("buildtime_s"),
            "/".join(str(p.get(k, "-")) for k in ("food", "wood", "stone", "gold", "iron", "coal")) if p else "-",
            f"{w.get('damage', '-')}/{w.get('pause_s', '-')}/{w.get('radiusmax_tiles', '-')}" if w else "-",
            f"{pr.get('pike', '-')}/{pr.get('sword', '-')}/{pr.get('bullet', '-')}" if pr else "-"))
    print(f"файл: {выход}")


if __name__ == "__main__":
    main()
