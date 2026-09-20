# -*- coding: utf-8 -*-
"""Годится ли локальная модель для СОБЫТИЙНОГО вызова «кого нанимать».

Событийный вызов (20.09) — узкий: запрос около 940 символов против ~6800 у
обычного такта, ответ короткой схемой {"role","total","why"}. Именно такая
форма и могла бы уехать на локальную модель: полный запрос моста семи- и
восьмимиллиардные модели не держат вовсе (замер 20.09).

Что проверяется, и почему именно это. У вопроса «кого нанимать» НЕТ единственно
верного ответа — выбор зависит от замысла. Поэтому меряется не совпадение с
чьим-то мнением, а ГОДНОСТЬ ответа: примет ли его мост и не навредит ли он.

  1. JSON разобрался;
  2. роль — из кандидатов ИМЕННО этого здания (казарма не кует драгун);
  3. `total` это -1 или положительное число;
  4. ответ проходит `to_commands` — то есть превращается в настоящую TRAIN.

Отдельно, как наблюдение, а не как ошибка: выбрал ли стрелков там, где угольной
шахты нет и уголь кончится. Это вопрос вкуса, но дорогого.

    python3 стенд_найма.py <модель> [<модель> ...]      # локальные, через ollama
    python3 стенд_найма.py --облако <id>                # через OPENROUTER_BASE_URL
"""
import json, os, sys, time, urllib.request, statistics as stx
sys.path.insert(0, '/Users/gs/coss3-bridge')
import llm_policy as L

АДРЕС = "http://localhost:11434/api/generate"


def спросить_локально(модель, промпт, таймаут=180, кандидаты=None):
    """Со СХЕМОЙ — это не поблажка, а то, как и надо звать локальную модель.

    Единственная ошибка, которую они делают на этом вопросе, — выдуманное имя
    роли («pikeman» вместо «infantry17», «dragoon» вместо «dragoon17»).
    Схема с перечислением кандидатов закрывает её целиком, и это ровно тот
    список, который мост уже знает (`КОГО_КУЕТ`).
    """
    # keep_alive: без него ollama выгружает модель между вызовами, и каждый
    # замер меряет ЗАГРУЗКУ С ДИСКА, а не работу. 21.09 это дало ложный вывод
    # «локальная медленнее облака»: первый вызов 5,9 с (2,9 загрузка + 2,4
    # чтение + 0,6 ответ), второй — 0,6 с.
    тело = {"model": модель, "prompt": L.SYSTEM_НАЙМ + "\n\n" + промпт,
            "stream": False, "keep_alive": "10m",
            "options": {"num_predict": 80, "num_ctx": 2048, "temperature": 0}}
    if кандидаты:
        тело["format"] = {"type": "object",
                          "properties": {"role": {"type": "string", "enum": list(кандидаты) + ["wait"]},
                                         "total": {"type": "integer"},
                                         "why": {"type": "string"}},
                          "required": ["role", "total"]}
    тело = json.dumps(тело).encode()
    t = time.time()
    d = json.load(urllib.request.urlopen(urllib.request.Request(
        АДРЕС, тело, {"Content-Type": "application/json"}), timeout=таймаут))
    return d.get("response", ""), time.time() - t


def спросить_облако(клиент, модель, промпт):
    t = time.time()
    # `system` — именно так мост подменяет роль для событийного вопроса
    # (ask(..., system=SYSTEM_НАЙМ)). Через spare_system стенд спрашивал
    # облако ОБЫЧНЫМ системным промптом, и оно отвечало полной схемой
    # {"commands":[...]} — 0 из 13 было ошибкой стенда, а не модели.
    d = L.ask(клиент, модель, промпт, False, system=L.SYSTEM_НАЙМ)
    return json.dumps(d, ensure_ascii=False), time.time() - t


def разобрать(текст):
    i, j = текст.find("{"), текст.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(текст[i:j + 1])
    except json.JSONDecodeError:
        return None


def годен(d, з):
    """Примет ли мост этот ответ. Возвращает (годен, причина)."""
    if d is None:
        return False, "не JSON"
    роль = d.get("role")
    if not роль:
        return False, "нет поля role"
    if str(роль).strip().lower() in ("wait", "ждать"):
        return True, ""            # законный ответ с 21.09
    if роль not in з["кандидаты"]:
        return False, f"роль {роль} это здание не кует"
    всего = d.get("total", -1)
    try:
        всего = int(всего)
    except (TypeError, ValueError):
        return False, f"total={всего!r} не число"
    if всего == 0:
        return False, "total=0 — заказ ни на кого"
    # как мост: перевести в TRAIN и прогнать разбор
    данные = {"commands": [{"cmd": "TRAIN", "role": роль, "total": всего}],
              "why": "проверка"}
    cmds = L.to_commands(данные)[0]
    if not any(c.cmd == "TRAIN" for c in cmds):
        return False, "to_commands команду отбросил"
    return True, ""


def прогнать(имя, задачи, спросить):
    годных = стрелки_без_угля = 0
    времена, причины, выборы = [], [], []
    for з in задачи:
        try:
            try:
                о, дт = спросить(з["запрос"], к=з["кандидаты"])
            except TypeError:
                о, дт = спросить(з["запрос"])
        except Exception as e:
            причины.append(f"сбой: {str(e)[:60]}")
            continue
        времена.append(дт)
        d = разобрать(о)
        ок, почему = годен(d, з)
        годных += ок
        if не_ок := (not ок):
            причины.append(почему)
        if ок and d.get("role") == "musk17" and not з["шахта_угля"]:
            стрелки_без_угля += 1
        выборы.append((d or {}).get("role") if ок else None)
    return dict(модель=имя, задач=len(задачи), годных=годных,
                стрелки_без_угля=стрелки_без_угля,
                медиана=(stx.median(времена) if времена else None),
                максимум=(max(времена) if времена else None),
                причины=причины, выборы=выборы, времена=времена)


def main(argv):
    задачи = json.load(open("задачи_найма.json"))
    print(f"задач {len(задачи)} (казарма/конюшня, запрос ~940 символов)\n")
    print(f'{"модель":26s} {"годных":>7s} {"медиана":>8s} {"макс":>7s} {"стрелки без угля":>17s}')
    итоги = []
    облако = "--облако" in argv
    имена = [a for a in argv if not a.startswith("--")]
    клиент = None
    if облако:
        from openai import OpenAI
        клиент = OpenAI(base_url=L.BASE_URL, api_key=os.environ["OPENROUTER_API_KEY"])
    for м in имена:
        схема = "--схема" in argv
        f = ((lambda p, м=м: спросить_облако(клиент, м, p)) if облако
             else (lambda p, м=м, к=None: спросить_локально(м, p, кандидаты=к)))
        r = прогнать(м, задачи, f)
        итоги.append(r)
        print(f'{r["модель"][:26]:26s} {r["годных"]:>3d}/{r["задач"]:<3d} '
              f'{(f"{r["медиана"]:.1f} с" if r["медиана"] else "—"):>8s} '
              f'{(f"{r["максимум"]:.1f} с" if r["максимум"] else "—"):>7s} '
              f'{r["стрелки_без_угля"]:>17d}')
        for п in r["причины"][:4]:
            print(f'      × {п}')
    json.dump(итоги, open("итоги_найма.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
