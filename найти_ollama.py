# -*- coding: utf-8 -*-
"""Найти ollama в сети и сказать, чем её прописать.

Повод, 23.09. Мак переехал с `10.41.3.31` на `10.41.2.77` (DHCP), и полчаса
ушло не на переезд, а на то, чем его проверяли: `ping` на Windows печатает
«0 процентов потерь», отвечая ОТ ШЛЮЗА «Destination host unreachable», а имя
мака из WSL не резолвится ни по NetBIOS, ни по mDNS. Живость сервера
проверяется ПОРТОМ, а не пингом, — этим и занят скрипт.

    python найти_ollama.py                  # искать рядом с последним адресом
    python найти_ollama.py 10.41.2 10.41.3  # искать в этих /24
"""
import concurrent.futures as fut
import json, socket, sys, urllib.request

ПОРТ = 11434
ПОСЛЕДНИЙ = "10.41.2.77"        # обновлять здесь, когда мак переедет снова


def живой(адрес, таймаут=1.5):
    try:
        with socket.create_connection((адрес, ПОРТ), таймаут):
            return адрес
    except OSError:
        return None


def модели(адрес):
    try:
        with urllib.request.urlopen(f"http://{адрес}:{ПОРТ}/api/tags", timeout=5) as r:
            return [м.get("name") for м in json.load(r).get("models", [])]
    except Exception:
        return []


def искать(сети):
    адреса = [f"{с}.{i}" for с in сети for i in range(1, 255)]
    with fut.ThreadPoolExecutor(max_workers=128) as пул:
        return [а for а in пул.map(живой, адреса) if а]


if __name__ == "__main__":
    сети = sys.argv[1:] or [".".join(ПОСЛЕДНИЙ.split(".")[:3])]
    if not sys.argv[1:]:
        # Соседняя подсеть: мак уже переезжал между 10.41.2 и 10.41.3.
        третий = int(ПОСЛЕДНИЙ.split(".")[2])
        сети += [".".join(ПОСЛЕДНИЙ.split(".")[:2] + [str(третий + 1)]),
                 ".".join(ПОСЛЕДНИЙ.split(".")[:2] + [str(третий - 1)])]
    if живой(ПОСЛЕДНИЙ):
        print(f"прежний адрес жив: {ПОСЛЕДНИЙ}")
        найдено = [ПОСЛЕДНИЙ]
    else:
        print(f"прежний адрес {ПОСЛЕДНИЙ} молчит, ищу в {', '.join(с + '.0/24' for с in сети)}...")
        найдено = искать(сети)
    for а in найдено:
        имена = модели(а)
        print(f"  {а}:{ПОРТ} — моделей {len(имена)}: {', '.join(x for x in имена[:6] if x)}")
    if найдено:
        print("\nпрописать контейнерам (WSL, ~/coss3.env):")
        print(f"  COSS3_EVENT_URL=http://{найдено[0]}:{ПОРТ}/v1")
        print("и поправить ПОСЛЕДНИЙ в этом файле, чтобы поиск начинался с него")
    else:
        print("не нашёл. На маке нужен: OLLAMA_HOST=0.0.0.0:11434 ollama serve")
