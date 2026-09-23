# -*- coding: utf-8 -*-
"""РОДНОЙ путь ollama для событийного вопроса: схема грамматикой.

Повод, 23.09. Думающая `qwen3:30b-a3b` через `/v1/chat/completions` сперва
рассуждает: 700-1400 токенов, 48-344 с на девяти настоящих событийных
запросах, один вызов сорвался по таймауту, другой занял 1190 токенов при
потолке 1200 — то есть был в десяти токенах от обрыва, а обрыв в трассе
неотличим от молчания. Шесть выключателей думания на этом пути не работают.

На `/api/generate` схема становится ГРАММАТИКОЙ: модель не может выдать токен
вне JSON. Те же запросы — 2,2-2,5 с и 27 токенов. Негодна была не модель, а
путь.

Что проверяется:
  1. `Родной` отсекает хвост `/v1` — OpenAI-клиенту он нужен, родному пути нет;
  2. `ask()` с таким клиентом идёт на `/api/generate`, кладёт схему в `format`
     и потолок в `options.num_predict`, а не собирает запрос для `/v1`;
  3. ответ берётся из `thinking`, когда `response` пуст: со схемой ollama
     кладёт готовый JSON именно туда, и это НЕ молчание модели;
  4. обрыв по длине назван ОБРЫВОМ, а не «не JSON» — иначе причина теряется;
  5. ключ `--event-native` есть и по умолчанию включён;
  6. запасное облако работает и с родным клиентом (очередь пар).
"""
import io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm_policy as L

ошибок = 0


def проверить(условие, что):
    global ошибок
    if not условие:
        ошибок += 1
        print("  СБОЙ:", что)
    else:
        print("  ок:", что)


ИСХОДНИК = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "llm_policy.py"), encoding="utf-8").read()
СХЕМА = {"type": "object", "properties": {"role": {"type": "string"}},
         "required": ["role"], "additionalProperties": False}

print("1. адрес приводится к корню")
проверить(L.Родной("http://мак:11434/v1").база == "http://мак:11434", "хвост /v1 отсечён")
проверить(L.Родной("http://мак:11434/").база == "http://мак:11434", "лишняя косая убрана")

print("2-4. запрос и разбор ответа")
последний = {}


class Ответ:
    def __init__(self, тело):
        self.тело = тело
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self):
        return json.dumps(self.тело).encode()


def подмена(тело_ответа):
    def urlopen(req, timeout=None):
        последний["url"] = req.full_url
        последний["тело"] = json.loads(req.data.decode())
        последний["таймаут"] = timeout
        return Ответ(тело_ответа)
    return urlopen


было = L.urllib.request.urlopen
L.urllib.request.urlopen = подмена({"response": '{"role": "infantry17"}',
                                    "eval_count": 27})
о = L.ask(L.Родной("http://мак:11434/v1"), "qwen3:30b-a3b", "спрос",
          system="роль", схема=СХЕМА)
проверить(последний["url"].endswith("/api/generate"), "пошли на /api/generate")
проверить(последний["тело"].get("format") == СХЕМА, "схема ушла в format — это грамматика")
проверить(последний["тело"]["options"]["num_predict"] == 200, "потолок 200 токенов")
проверить(последний["тело"].get("stream") is False, "без потока: ответ нужен целиком")
проверить(последний["тело"].get("system") == "роль", "роль повода передана")
проверить(о == {"role": "infantry17"}, "ответ разобран")
проверить(L.LAST_TOKENS == 27, "токены записаны — по ним считают стоимость и обрыв")
проверить(L.LAST_PROVIDER == "ollama", "в трассе видно, что отвечал родной путь")

L.urllib.request.urlopen = подмена({"response": "", "thinking": '{"role": "musk17"}',
                                    "eval_count": 30})
о = L.ask(L.Родной("http://мак:11434"), "qwen3:30b-a3b", "спрос", схема=СХЕМА)
проверить(о == {"role": "musk17"}, "пустой response при непустом thinking — не молчание, а ответ")

L.urllib.request.urlopen = подмена({"response": '{"role": "infan',
                                    "done_reason": "length", "eval_count": 200})
беда = ""
try:
    L.ask(L.Родной("http://мак:11434"), "qwen3:30b-a3b", "спрос", схема=СХЕМА, retry=0)
except Exception as e:
    беда = str(e)
проверить("ОБРЫВ" in беда, f"обрыв назван обрывом, а не «не JSON»: {беда[:60]}")
L.urllib.request.urlopen = было

print("5. ключ заведён и включён по умолчанию")
проверить('"--event-native"' in ИСХОДНИК, "ключ --event-native есть")
проверить(re.search(r'--event-native",\s*type=int,\s*default=1', ИСХОДНИК) is not None,
          "по умолчанию 1: если адрес — ollama, идём родным путём")
проверить("isinstance(a._client_событий, Родной)" in ИСХОДНИК,
          "проверка через /v1 не повторяется, когда выбран родной путь")

print("6. запасное облако работает и с родным клиентом")


class Облако:
    def __init__(self):
        self.звали = 0
        сам = self
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    сам.звали += 1
                    class M: content = '{"role": "cloud", "why": "запасным путём"}'
                    class C: message = M(); finish_reason = "stop"
                    class R: choices = [C()]; usage = None; provider = "облако"
                    return R()
        self.chat = chat


def мёртвый(req, timeout=None):
    raise OSError("Connection refused")


L.urllib.request.urlopen = мёртвый
обл, ящик = Облако(), {}
L.think_worker(ящик, L.Родной("http://мак:11434"), "qwen3:30b-a3b", "спрос",
               False, tries=1, схема=СХЕМА, запас=(обл, "cloud/model"))
L.urllib.request.urlopen = было
проверить(обл.звали == 1 and (ящик.get("data") or {}).get("role") == "cloud",
          "ollama не отвечает — вопрос ушёл облаком, повод не потерян")

print()
print("ошибок:", ошибок)
sys.exit(1 if ошибок else 0)
