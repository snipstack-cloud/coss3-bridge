# -*- coding: utf-8 -*-
"""Прогреть локальную модель ДО старта прогона и удержать её в памяти.

Правило игрока, 22.09: событийную модель на маке греют ЗАРАНЕЕ, а не оставляют
загружаться первым событием партии.

МОДЕЛЬ ПО УМОЛЧАНИЮ — `qwen2.5:7b` (решение игрока 22.09 по замерам ниже).
Сначала стояла `llama3.1:8b`, но замер на ПРОГРЕТЫХ моделях, 8 зачётных
вызовов на одинаковом промпте, показал обратное:

    qwen2.5:7b      медиана 0,63 с   худший 1,37
    qwen2.5:14b     медиана 0,71 с   худший 0,92
    mistral:latest  медиана 1,20 с   худший 1,63
    llama3.1:8b     медиана 1,58 с   худший 1,68

По качеству (стенды рук и найма, 21 и 11 задач) годность у всех одинакова —
21/21 и 11/11, брака нет ни у одной. Различает остальное: `mistral` четырежды
из одиннадцати выбрал стрелков там, где угольной шахты нет (у прочих ноль);
`llama3.1:8b` раздаёт людей вдвое скупее — медиана 5 человек против 10, при
свободных 3-22. `qwen2.5:7b` ближе всех к облаку сразу по всем колонкам:
те же 10 розданных, те же 12/21 в просевшее направление, ноль стрелков без
угля — и он же самый быстрый.

Две причины, обе замерены:
  * первый вызов платит загрузкой модели в память (4,9 ГБ) — эти секунды
    попадают прямо в такт;
  * `OLLAMA_KEEP_ALIVE` по умолчанию 5 минут, а события приходят раз в ~5,3
    минуты реального времени (замер 22.09: интервал 320 игровых секунд).
    Модель выгружается почти между каждой парой событий, и загрузка платится
    снова. Поэтому `keep_alive` задаётся на всю партию, а не умолчанием.

ЧЕГО ЭТО НЕ ЛЕЧИТ: медленность самого вызова. На ЗАВЕДОМО прогретой модели
короткий запрос занял 3,9 с, в живой партии события шли 5,6 и 6,7 с против
1,5 с медианы у облака. Стенды мерили `/api/generate` СО СХЕМОЙ, а мост зовёт
`/v1/chat/completions` без неё — модель генерирует до лимита вместо строгого
JSON. Пока схема не передаётся на событийном вызове, грей не грей.

    python3 warm_local.py                         # qwen2.5:7b, 30 минут
    python3 warm_local.py llama3.1:8b --minutes 40
    python3 warm_local.py --host 10.41.3.31 --check   # только показать, что в памяти
"""
import argparse, json, sys, time, urllib.request, urllib.error

МОДЕЛЬ = "qwen2.5:7b"
АДРЕС = "10.41.3.31"


def запрос(url, тело=None, таймаут=300):
    данные = json.dumps(тело).encode() if тело is not None else None
    req = urllib.request.Request(url, данные, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=таймаут) as r:
        return json.load(r)


def в_памяти(база):
    try:
        return запрос(f"{база}/api/ps", таймаут=10).get("models", [])
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"не достучался до {база}: {e}")
        print("  на маке нужен OLLAMA_HOST=0.0.0.0:11434 ollama serve —")
        print("  иначе он слушает только петлю и снаружи молчит")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("модель", nargs="?", default=МОДЕЛЬ)
    ap.add_argument("--host", default=АДРЕС)
    ap.add_argument("--minutes", type=int, default=30,
                    help="сколько держать в памяти; партия идёт около 20 минут")
    ap.add_argument("--check", action="store_true",
                    help="не греть, только показать, что сейчас в памяти")
    a = ap.parse_args()
    база = f"http://{a.host}:11434"

    сейчас = в_памяти(база)
    if сейчас is None:
        return 2
    print(f"в памяти сейчас: {len(сейчас)}")
    for м in сейчас:
        print(f"  {м.get('name')}  {м.get('size_vram', 0) / 1e9:.1f} ГБ  "
              f"до выгрузки {str(м.get('expires_at', ''))[11:19]}")
    if a.check:
        return 0

    print(f"грею {a.модель} на {a.minutes} мин...")
    t = time.time()
    try:
        d = запрос(f"{база}/api/generate",
                   {"model": a.модель, "prompt": "ok", "stream": False,
                    "keep_alive": f"{a.minutes}m",
                    "options": {"num_predict": 1}})
    except urllib.error.HTTPError as e:
        тело = e.read().decode("utf-8", "replace")[:200]
        print(f"ОТКАЗ {e.code}: {тело}")
        print(f"  моделей на сервере: см. {база}/api/tags")
        return 1
    except (urllib.error.URLError, OSError) as e:
        print(f"не дозвонился: {e}")
        return 2
    прошло = time.time() - t
    print(f"загрузилась за {прошло:.1f} с")

    после = в_памяти(база) or []
    сел = [м for м in после if м.get("name", "").startswith(a.модель.split(":")[0])]
    if not сел:
        print("ПРЕДУПРЕЖДЕНИЕ: модели нет в /api/ps — прогрев не удержался")
        return 1
    for м in сел:
        print(f"  ГОТОВО: {м.get('name')} в памяти, {м.get('size_vram', 0) / 1e9:.1f} ГБ, "
              f"до выгрузки {str(м.get('expires_at', ''))[11:19]}")
    print("теперь можно поднимать контейнеры:")
    print(f"  --event-model {a.модель} --event-base-url {база}/v1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
