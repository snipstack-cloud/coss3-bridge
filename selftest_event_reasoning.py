# -*- coding: utf-8 -*-
"""Выключатель думания на СОБЫТИЙНОМ вызове: `--event-reasoning none`.

Повод, 23.09. `qwen2.5:7b` на событиях отвечает «ЖДУ» в 5 случаях из 9, где
облако нанимает ни разу не отказав из 20 (плечо local_events, разобрано с
мака). Кандидат на замену — думающая `qwen3:30b-a3b`, и через `/v1` она без
этого ключа отвечает ПУСТЫМ content за 48 с: схема думание не выключает, а
рассуждение съедает MAX_TOKENS. Замер 22.09 на одном вопросе найма: 48 с и
пусто со схемой; 28,8 с и JSON после 864 токенов рассуждения без схемы;
1,1 с и 19 токенов со схемой и `reasoning_effort="none"`.

Что проверяется:
  1. ключ есть у разбора командной строки и по умолчанию ПУСТ;
  2. ask() без «усилие» собирает запрос как раньше — обычный такт не задет;
  3. с «усилие» ключ уходит в extra_body ровно тем значением;
  4. переспрос после мусорного ответа НЕ теряет ни роль, ни схему, ни
     выключатель: до 23.09 второй вызов уходил с ролью общего такта, без
     схемы и с думанием обратно включённым, то есть заведомо в пустоту;
  5. отказ провайдера от extra_body при заданном усилии говорится ВСЛУХ.
"""
import io, os, re, sys
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

print("1. ключ заведён и по умолчанию пуст")
проверить('"--event-reasoning"' in ИСХОДНИК, "ключ --event-reasoning есть")
проверить(re.search(r'--event-reasoning",\s*default=""', ИСХОДНИК) is not None,
          "по умолчанию пусто: облачным вызовам ключ чужой")
проверить("_усилие_событий" in ИСХОДНИК, "значение кладётся на `a` рядом с моделью событий")
проверить(re.search(r'_ус = \(getattr\(a, "_усилие_событий", ""\)\s*\n\s*if getattr\(a, "_client_событий", None\) else ""\)',
                    ИСХОДНИК) is not None,
          "усилие уходит ТОЛЬКО локальному клиенту событий, как и схема")


class _Кл:
    """Клиент, который запоминает kw и обрывает вызов до сети."""
    ответ = None                            # None — бросить RuntimeError

    class chat:
        class completions:
            последний = {}
            вызовов = 0

            @staticmethod
            def create(**kw):
                _Кл.chat.completions.последний = kw
                _Кл.chat.completions.вызовов += 1
                if _Кл.ответ is None:
                    raise RuntimeError("стоп: kw собраны, дальше сеть не нужна")
                return _Кл.ответ


def позвать(**kw):
    try:
        return L.ask(_Кл(), "m", "p", **kw)
    except RuntimeError:
        return None


print("2. без усилия запрос прежний")
было_схемой = L.СХЕМОЙ
L.СХЕМОЙ = False
позвать()
kw = _Кл.chat.completions.последний
проверить("reasoning_effort" not in kw.get("extra_body", {}),
          "ask() без «усилие»: reasoning_effort не ставится")

print("3. с усилием ключ уходит в тело запроса")
позвать(усилие="none")
kw = _Кл.chat.completions.последний
проверить(kw.get("extra_body", {}).get("reasoning_effort") == "none",
          "extra_body.reasoning_effort = 'none'")
проверить(kw["extra_body"].get("reasoning", {}) == {"enabled": False},
          "прежние выключатели на месте: ключ добавлен, а не заменил их")

print("4. переспрос после мусора несёт роль, схему и усилие")


class _Пустой:
    """Ответ без JSON — мост обязан переспросить."""
    class choices:
        pass


сообщение = type("M", (), {"content": "никакого json тут нет"})
выбор = type("C", (), {"message": сообщение, "finish_reason": "stop"})
_Кл.ответ = type("R", (), {"choices": [выбор], "usage": None, "provider": ""})
_Кл.chat.completions.вызовов = 0
схема = {"type": "object", "properties": {"role": {"type": "string"}},
         "required": ["role"], "additionalProperties": False}
try:
    L.ask(_Кл(), "m", "p", system="РОЛЬ СОБЫТИЯ", схема=схема, усилие="none")
except Exception:
    pass
проверить(_Кл.chat.completions.вызовов >= 2,
          f"переспрос состоялся ({_Кл.chat.completions.вызовов} вызова)")
kw = _Кл.chat.completions.последний
проверить(kw["messages"][0]["content"] == "РОЛЬ СОБЫТИЯ",
          "у переспроса та же роль, а не общий SYSTEM такта")
проверить(kw.get("response_format", {}).get("json_schema", {}).get("schema") is схема,
          "у переспроса та же схема")
проверить(kw.get("extra_body", {}).get("reasoning_effort") == "none",
          "у переспроса тот же выключатель думания")
_Кл.ответ = None
L.СХЕМОЙ = было_схемой

print("5. отказ от extra_body при заданном усилии говорится вслух")
хвост = ИСХОДНИК[ИСХОДНИК.index('kw.pop("extra_body")'):][:700]
проверить("если усилие" not in хвост and "if усилие:" in хвост,
          "после снятия extra_body проверяется, было ли усилие")
проверить("думание НЕ выключено" in хвост,
          "сказано, чем это грозит: молчание неотличимо от отвергнутого ключа")

print()
print("ошибок:", ошибок)
sys.exit(1 if ошибок else 0)
