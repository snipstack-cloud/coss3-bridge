#!/usr/bin/env python3
"""Страница для разбора результатов: сравнить идею с базой, прочитать партию.

    python3 results_ui.py --pull                  обновить клон и собрать
    python3 results_ui.py --out ~/coss3.html      куда положить
    python3 results_ui.py --repo ./мои-результаты собрать из готового каталога

Делает ОДИН самодостаточный html: ни сети, ни внешних файлов. Данные в него
вшиты, поэтому страницу можно открыть на машине без клона и без интернета — и
поэтому же она не уезжает никуда наружу.

Читает то, что кладёт `push_results.py`: `<дата>/<идея>/<копия>/` с отчётом,
трассой, квитанцией условий и описанием идеи.

Чего эта страница НЕ делает и не должна: не считает статистику значимой. Две
копии против трёх — это наблюдение. Число копий показано рядом с каждым числом
именно поэтому.
"""
from __future__ import annotations
import argparse
import html
import json
import os
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

РЕПО = "git@github.com:snipstack-cloud/coss3-results.git"
ВЕТКА = "results"
ПОЗДНО = 15          # первый ход позже этой секунды — прогон не сравним

# Поля снимка, которые попадают в страницу. Не весь снимок: трасса на сотню
# тактов иначе раздувает файл, а смотрят всегда эти.
СНИМОК = ("peasants", "mil_inf", "mil_shooters", "food", "wood", "stone",
          "gold", "iron", "centers", "mills", "smiths", "ba17", "my_farmused",
          "wip", "last_fail")


def выполнить(аргс, где="", ключ="", терпеть=False):
    окр = dict(os.environ)
    if ключ:
        окр["GIT_SSH_COMMAND"] = f"ssh -i {ключ} -o IdentitiesOnly=yes -o BatchMode=yes"
    р = subprocess.run(аргс, cwd=где or None, env=окр, capture_output=True, text=True)
    if р.returncode and not терпеть:
        print(f"  ! {' '.join(аргс[:3])}: {(р.stdout + р.stderr).strip()[:300]}")
    return р.returncode, р.stdout + р.stderr


def взять_клон(репо: str, ключ: str, куда: str) -> str:
    """Свежий клон ветки результатов. Возвращает путь или пустую строку."""
    # Каталог бывает двух видов, и спутать их — значит молча собрать пустую
    # страницу: голый репозиторий (objects/) и обычный клон (.git/) надо
    # КЛОНИРОВАТЬ, а дерево с результатами читать как есть.
    репозиторий = (os.path.isdir(os.path.join(репо, "objects"))
                   or os.path.isdir(os.path.join(репо, ".git")))
    if os.path.isdir(репо) and not репозиторий:
        return репо                       # готовое дерево, ничего не тянем
    код, _ = выполнить(["git", "clone", "--quiet", "--depth", "1",
                        "--branch", ВЕТКА, репо, куда], ключ=ключ, терпеть=True)
    if код:
        print(f"не смог взять {репо} @ {ВЕТКА}.\n"
              f"  Либо ветки ещё нет — тогда ни один прогон не отправлен,\n"
              f"  либо нет доступа: нужен ключ (--key ~/.ssh/coss3_results).")
        return ""
    return куда


def прочесть(путь: str) -> str:
    try:
        with open(путь, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def разбор_dat(текст: str) -> dict:
    из = {}
    for строка in текст.splitlines():
        если = строка.split("=", 1)
        if len(если) == 2:
            из[если[0].strip()] = если[1].strip()
    return из


def чис(v, поумолчанию=0) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return поумолчанию


def враг(запись: dict):
    с = запись.get("state") or {}
    свои = [чис(v) for k, v in с.items()
            if k.endswith("_peasants") and not k.startswith("my") and v is not None]
    return max(свои) if свои else None


def собрать_прогон(каталог: str, дата: str, идея: str, копия: str) -> dict | None:
    трасса = []
    for строка in прочесть(os.path.join(каталог, "coss3_bot.jsonl")).splitlines():
        строка = строка.strip()
        if строка:
            try:
                трасса.append(json.loads(строка))
            except ValueError:
                pass
    опыт = {}
    try:
        опыт = json.loads(прочесть(os.path.join(каталог, "опыт.json")) or "{}")
    except ValueError:
        pass
    матч = разбор_dat(прочесть(os.path.join(каталог, "match.dat")))
    ходы = [р for р in трасса if not р.get("finish")]
    концы = [str(р["finish"]) for р in трасса if р.get("finish")]
    посл = (трасса[-1].get("state") or {}) if трасса else {}
    в0 = next((в for в in (враг(р) for р in трасса) if в is not None), None)
    в1 = next((в for в in (враг(р) for р in reversed(трасса)) if в is not None), None)
    # Убитые считаются от БЕГУЩЕГО МАКСИМУМА, а не «первое минус последнее».
    # Враг растёт с 18 до 90-150, поэтому прежняя формула давала отрицательное
    # число в каждой партии, и «цель взята» не показывалась НИКОГДА. 14.09 так
    # пропала цель, взятая на 12:07. Та же ошибка жила в llm_policy (починена
    # 13.09) и в run_report (14.09) — третье место подряд.
    # Считать надо ВНУТРИ партии. В прогоне их бывает пять подряд, и при смене
    # партии крестьяне врага падают с 90 до 18 — если считать по всей трассе,
    # этот сброс выглядит как 72 убитых. Первая версия правки так и дала
    # «убито 24817», что абсурдно.
    убито, пик, прежнее_gt = 0, None, -1
    for р in трасса:
        gt = чис(р.get("gt"))
        if gt < прежнее_gt or р.get("finish"):
            пик = None                      # новая партия: счёт с чистого листа
        прежнее_gt = gt
        в = враг(р)
        if в is None:
            continue
        if пик is not None and в < пик:
            убито += пик - в
        пик = в if пик is None else max(пик, в)
    # Цель проверяется КАЖДУЮ секунду, а трасса пишется раз в двадцать: падение
    # может не попасть в неё вовсе. Поэтому отметка моста и лог прогона важнее
    # арифметики по трассе.
    лог = прочесть(os.path.join(каталог, "policy.log"))
    цель = ("цель" in концы) or (убито > 0) or ("ЦЕЛЬ ДОСТИГНУТА" in лог)
    return {
        "дата": дата, "идея": идея, "копия": копия,
        "что": опыт.get("что", ""),
        "флаги": опыт.get("флаги", ""),
        "база": опыт.get("база", ""),
        "sha": (прочесть(os.path.join(каталог, "bridge.sha")).strip() or "?")[:8],
        "условия": {k: матч.get(k, "") for k in ("res", "peace", "ai1", "nat0")},
        "старт": чис(ходы[0].get("gt")) if ходы else 0,
        "тактов": len(ходы),
        "время": чис(трасса[-1].get("gt")) if трасса else 0,
        "исходы": концы,
        "крестьян": чис(посл.get("peasants")),
        "армия": чис(посл.get("mil_inf")) + чис(посл.get("mil_shooters")),
        "враг0": в0, "враг1": в1,
        "убито": убито,
        "цель": цель,
        "волн": sum(1 for р in трасса if р.get("attack") and not р.get("veto")),
        "брак": sum(len(р.get("rejected") or []) for р in трасса),
        "вето": sum(1 for р in трасса if р.get("veto")),
        "вмешательств": sum(1 for р in трасса if р.get("forced")),
        "отчёт": прочесть(os.path.join(каталог, "отчёт.md")),
        "такты": [{
            "gt": чис(р.get("gt")),
            "why": str(р.get("why", "") or ""),
            "ok": str(р.get("ok", "") or ""),
            "stuck": str(р.get("stuck", "") or ""),
            "cause": str(р.get("cause", "") or ""),
            "lesson": str(р.get("lesson", "") or ""),
            "idea": str(р.get("idea", "") or ""),
            "finish": str(р.get("finish", "") or ""),
            "cmds": [f"{c.get('cmd')} {c.get('a1')}->{c.get('a2')}"
                     for c in (р.get("cmds") or [])],
            "attack": чис(р.get("attack")),
            "veto": str(р.get("veto", "") or ""),
            "forced": str(р.get("forced", "") or ""),
            "rejected": [str(x) for x in (р.get("rejected") or [])],
            "state": {k: (р.get("state") or {}).get(k)
                      for k in СНИМОК if (р.get("state") or {}).get(k) is not None},
        } for р in трасса],
    }


def найти_прогоны(корень: str) -> list[dict]:
    из = []
    for дата in sorted(os.listdir(корень)):
        п1 = os.path.join(корень, дата)
        if дата.startswith(".") or not os.path.isdir(п1):
            continue
        for идея in sorted(os.listdir(п1)):
            п2 = os.path.join(п1, идея)
            if not os.path.isdir(п2):
                continue
            for копия in sorted(os.listdir(п2)):
                п3 = os.path.join(п2, копия)
                if not os.path.isdir(п3):
                    continue
                п = собрать_прогон(п3, дата, идея, копия)
                if п:
                    из.append(п)
    return из


ШАБЛОН = """<title>Результаты прогонов Cossacks 3</title>
<style>
:root {
  --фон: #f7f7f5; --карточка: #fff; --текст: #1a1a1a; --тихий: #6b6b6b;
  --рамка: #e0ded9; --акцент: #2b6cb0; --плохо: #b03a2e; --хорошо: #1e7d4a;
  --тень: 0 1px 2px rgba(0,0,0,.06);
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --фон: #16171a; --карточка: #1e2024; --текст: #e8e6e3; --тихий: #9a9894;
  --рамка: #32353b; --акцент: #6aa8e8; --плохо: #e8796b; --хорошо: #5ac08a;
  --тень: none;
} }
* { box-sizing: border-box; }
body { margin: 0; background: var(--фон); color: var(--текст);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.обёртка { max-width: 1180px; margin: 0 auto; padding: 24px 18px 72px; }
h1 { font-size: 21px; margin: 0 0 4px; letter-spacing: -.01em; }
h2 { font-size: 16px; margin: 32px 0 10px; }
.тихо { color: var(--тихий); font-size: 13px; }
.карточка { background: var(--карточка); border: 1px solid var(--рамка);
  border-radius: 10px; padding: 16px; box-shadow: var(--тень); margin-bottom: 14px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { text-align: right; padding: 6px 9px; border-bottom: 1px solid var(--рамка); }
th:first-child, td:first-child { text-align: left; }
th { font-weight: 600; font-size: 12px; color: var(--тихий);
  text-transform: uppercase; letter-spacing: .03em; }
tbody tr:hover { background: color-mix(in srgb, var(--акцент) 7%, transparent); }
.прокрутка { overflow-x: auto; }
select, button { font: inherit; padding: 6px 10px; border-radius: 7px;
  border: 1px solid var(--рамка); background: var(--карточка); color: var(--текст); }
button { cursor: pointer; }
button:hover { border-color: var(--акцент); }
.ряд { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.плохо { color: var(--плохо); } .хорошо { color: var(--хорошо); }
.метка { display: inline-block; padding: 1px 7px; border-radius: 20px;
  font-size: 12px; border: 1px solid var(--рамка); }
.ссылка { color: var(--акцент); cursor: pointer; text-decoration: underline;
  text-underline-offset: 2px; }
.предупреждение { border-left: 3px solid var(--плохо); padding-left: 12px;
  color: var(--плохо); margin: 10px 0; }
pre { background: var(--фон); border: 1px solid var(--рамка); border-radius: 8px;
  padding: 12px; overflow-x: auto; font-size: 12.5px; }
.такт { border-bottom: 1px solid var(--рамка); padding: 10px 0; }
.такт:last-child { border-bottom: 0; }
.время { color: var(--тихий); font-variant-numeric: tabular-nums;
  font-weight: 600; margin-right: 8px; }
.поле { color: var(--тихий); font-size: 12.5px; margin-left: 22px; }
.скрыт { display: none; }
</style>
<div class="обёртка">
<h1>Результаты прогонов</h1>
<div class="тихо" id="шапка"></div>
<div id="корень"></div>
</div>
<script id="данные" type="application/json">@@ДАННЫЕ@@</script>
<script>
const ПОЗДНО = @@ПОЗДНО@@;
const данные = JSON.parse(document.getElementById('данные').textContent);
const прогоны = данные.прогоны;
const корень = document.getElementById('корень');

const мм = с => `${Math.floor(с/60)}:${String(с%60).padStart(2,'0')}`;
// Экранирование через textContent: данные приходят из трассы модели, и её
// текст попадает в разметку. Ручные замены тут рано или поздно что-нибудь
// пропустят.
function э(т){ const d=document.createElement('div'); d.textContent=т==null?'':String(т); return d.innerHTML; }

document.getElementById('шапка').textContent =
  `${прогоны.length} прогонов, ${new Set(прогоны.map(p=>p.идея)).size} идей. ` +
  `Собрано ${данные.собрано}. Источник: ${данные.репо}`;

// --- свод по идее ---------------------------------------------------------
const ПОКАЗАТЕЛИ = [
  ['убито','убито крестьян врага','больше'],
  ['волн','волн ушло','больше'],
  ['армия','армия в конце','больше'],
  ['крестьян','своих крестьян','больше'],
  ['время','дожили до','больше'],
  ['брак','брак команд','меньше'],
  ['вето','вето волн','меньше'],
];

function поидеям(){
  const м = new Map();
  for (const п of прогоны){ if(!м.has(п.идея)) м.set(п.идея,[]); м.get(п.идея).push(п); }
  return м;
}
const средн = (сп,к) => { const з=сп.map(x=>x[к]).filter(v=>v!=null);
  return з.length ? з.reduce((a,b)=>a+b,0)/з.length : null; };

function нарисовать(){
  const м = поидеям();
  const идеи = [...м.keys()];
  корень.innerHTML = '';

  // Сравнение
  const c = document.createElement('div'); c.className='карточка';
  c.innerHTML = `<h2 style="margin-top:0">Сравнить идею с базой</h2>
    <div class="ряд">
      <label>идея <select id="сИдея"></select></label>
      <label>база <select id="сБаза"></select></label>
    </div>
    <div id="сравнение"></div>`;
  корень.appendChild(c);
  const sИ=c.querySelector('#сИдея'), sБ=c.querySelector('#сБаза');
  for(const и of идеи){
    sИ.appendChild(new Option(и+` (${м.get(и).length})`, и));
    sБ.appendChild(new Option(и+` (${м.get(и).length})`, и));
  }
  const базаПоум = идеи.includes('baseline') ? 'baseline' : идеи[идеи.length-1];
  sБ.value = базаПоум;
  sИ.value = идеи.find(x=>x!==базаПоум) || идеи[0];
  const обнови = () => сравнить(м, sИ.value, sБ.value, c.querySelector('#сравнение'));
  sИ.onchange = sБ.onchange = обнови; обнови();

  // Все прогоны
  const t = document.createElement('div'); t.className='карточка';
  t.innerHTML = `<h2 style="margin-top:0">Все прогоны</h2><div class="прокрутка">
    <table><thead><tr>
      <th>прогон</th><th>старт</th><th>тактов</th><th>до</th><th>исход</th>
      <th>крест</th><th>армия</th><th>враг</th><th>убито</th>
      <th>волн</th><th>брак</th><th>вето</th><th>мост</th>
    </tr></thead><tbody></tbody></table></div>`;
  const tb = t.querySelector('tbody');
  прогоны.forEach((п,i)=>{
    const tr = document.createElement('tr');
    const поздно = п.старт > ПОЗДНО;
    tr.innerHTML =
      `<td><span class="ссылка" data-i="${i}">${э(п.дата)}/${э(п.идея)}/${э(п.копия)}</span></td>
       <td class="${поздно?'плохо':''}" title="${поздно?'подключились поздно — прогон не сравним':''}">${мм(п.старт)}${поздно?' !':''}</td>
       <td>${п.тактов}</td><td>${мм(п.время)}</td>
       <td>${п.исходы.map(x=>x==='lose'?'П':x==='win'?'В':'?').join(',')||'—'}</td>
       <td>${п.крестьян}</td><td>${п.армия}</td>
       <td>${п.враг0==null?'—':п.враг0+'→'+п.враг1}</td>
       <td class="${п.цель?'хорошо':''}">${п.цель?('ЦЕЛЬ'+((п.убито||0)>0?' '+п.убито:'')):(п.убито||0)}</td>
       <td>${п.волн}</td><td>${п.брак}</td><td>${п.вето}</td>
       <td class="тихо">${э(п.sha)}</td>`;
    tb.appendChild(tr);
  });
  корень.appendChild(t);
  tb.querySelectorAll('.ссылка').forEach(э2=>{
    э2.onclick = () => подробно(прогоны[+э2.dataset.i]);
  });

  const д = document.createElement('div'); д.className='карточка'; д.id='подробно';
  д.innerHTML = '<span class="тихо">Выберите прогон в таблице, чтобы прочитать партию по тактам.</span>';
  корень.appendChild(д);
}

function сравнить(м, идея, база, куда){
  const о = м.get(идея)||[], б = м.get(база)||[];
  if(идея===база){ куда.innerHTML='<p class="тихо">Выберите разные идеи.</p>'; return; }
  const поздниеО = о.filter(п=>п.старт>ПОЗДНО), поздниеБ = б.filter(п=>п.старт>ПОЗДНО);
  let пред = '';
  if(поздниеО.length||поздниеБ.length)
    пред += `<div class="предупреждение">Копий с поздним подключением: ${поздниеО.length+поздниеБ.length}.
      В них бот начал играть не с начала партии, и разница будет не про идею.</div>`;
  if(о.length<3||б.length<3)
    пред += `<div class="предупреждение">Копий мало (${о.length} против ${б.length}).
      Это наблюдение, а не измерение: единичный прогон случаен.</div>`;
  let строки = '';
  for(const [к,имя,куда_лучше] of ПОКАЗАТЕЛИ){
    const a=средн(о,к), b=средн(б,к);
    if(a==null&&b==null) continue;
    const д = (a??0)-(b??0);
    const лучше = куда_лучше==='больше' ? д>0 : д<0;
    const цвет = Math.abs(д)<1e-9 ? '' : (лучше?'хорошо':'плохо');
    const пок = к==='время' ? мм(Math.round(a??0))+' / '+мм(Math.round(b??0))
                            : (a==null?'—':a.toFixed(1))+' / '+(b==null?'—':b.toFixed(1));
    строки += `<tr><td>${э(имя)}</td><td>${пок}</td>
      <td class="${цвет}">${д>=0?'+':''}${д.toFixed(1)}</td></tr>`;
  }
  const целиО = о.filter(п=>п.цель).length, целиБ = б.filter(п=>п.цель).length;
  куда.innerHTML = пред + `
    <p class="тихо">${э(о[0]?.что||'')}</p>
    <div class="прокрутка"><table><thead><tr>
      <th>показатель</th><th>${э(идея)} / ${э(база)}</th><th>разница</th>
    </tr></thead><tbody>${строки}
    <tr><td>цель взята в копиях</td><td>${целиО} из ${о.length} / ${целиБ} из ${б.length}</td>
    <td class="${целиО/Math.max(1,о.length) > целиБ/Math.max(1,б.length)?'хорошо':''}"></td></tr>
    </tbody></table></div>`;
}

function подробно(п){
  const д = document.getElementById('подробно');
  let h = `<h2 style="margin-top:0">${э(п.дата)}/${э(п.идея)}/${э(п.копия)}</h2>
    <p class="тихо">${э(п.что)}<br>флаги: ${э(п.флаги||'—')} · мост ${э(п.sha)}
    · условия: res=${э(п.условия.res)} peace=${э(п.условия.peace)} ai=${э(п.условия.ai1)} нация=${э(п.условия.nat0)}</p>`;
  if(п.старт>ПОЗДНО)
    h += `<div class="предупреждение">Первый ход на ${мм(п.старт)} — бот начал играть не с начала партии.</div>`;
  h += `<div class="ряд"><button id="кОтчёт">Отчёт</button><button id="кТакты">По тактам</button>
        <span class="тихо">тактов ${п.тактов}, вмешательств моста ${п.вмешательств}</span></div>
        <div id="телоОтчёт"></div><div id="телоТакты" class="скрыт"></div>`;
  д.innerHTML = h;
  д.querySelector('#телоОтчёт').innerHTML = `<pre>${э(п.отчёт||'отчёта нет')}</pre>`;
  д.querySelector('#телоТакты').innerHTML = п.такты.map(т=>{
    if(т.finish) return `<div class="такт"><span class="время">${мм(т.gt)}</span>
      <b>=== ПАРТИЯ КОНЧИЛАСЬ: ${т.finish==='lose'?'ПОРАЖЕНИЕ':'ПОБЕДА'} ===</b></div>`;
    let s = `<div class="такт"><span class="время">${мм(т.gt)}</span>${э(т.why)}`;
    for(const [к,подпись] of [['ok','идёт'],['stuck','не идёт'],['cause','почему'],
                              ['lesson','УРОК'],['idea','ГИПОТЕЗА']])
      if(т[к]) s += `<div class="поле">${подпись}: ${э(т[к])}</div>`;
    if(т.cmds.length) s += `<div class="поле">отдано: ${э(т.cmds.join(', '))}</div>`;
    if(т.attack) s += `<div class="поле">ATTACK ${т.attack}${т.veto?' — ОТВЕРГНУТА МОСТОМ':''}</div>`;
    if(т.veto) s += `<div class="поле плохо">${э(т.veto)}</div>`;
    if(т.forced) s += `<div class="поле">МОСТ ВМЕШАЛСЯ: ${э(т.forced)}</div>`;
    for(const б of т.rejected) s += `<div class="поле плохо">НЕ УШЛО: ${э(б)}</div>`;
    const ст = Object.entries(т.state).map(([k,v])=>`${k}=${v}`).join(', ');
    if(ст) s += `<div class="поле тихо">${э(ст)}</div>`;
    return s + '</div>';
  }).join('') || '<span class="тихо">трассы нет</span>';
  const по=д.querySelector('#телоОтчёт'), пт=д.querySelector('#телоТакты');
  д.querySelector('#кОтчёт').onclick = ()=>{по.classList.remove('скрыт'); пт.classList.add('скрыт');};
  д.querySelector('#кТакты').onclick = ()=>{пт.classList.remove('скрыт'); по.classList.add('скрыт');};
  д.scrollIntoView({behavior:'smooth', block:'start'});
}

if(прогоны.length) нарисовать();
else корень.innerHTML = `<div class="карточка">
  <b>Ни одного прогона.</b>
  <p class="тихо">Ветка <code>results</code> пуста или её ещё нет. Значит ни один
  контейнер не отправил результат. Проверьте, что заданы COSS3_RESULTS_GIT и
  смонтирован ключ с правом записи, и что прогон дошёл до конца.</p></div>`;
</script>
"""


def main() -> int:
    p = argparse.ArgumentParser(description="страница разбора результатов")
    p.add_argument("--repo", default=РЕПО,
                   help="адрес git или готовый каталог с результатами")
    p.add_argument("--key", default=os.path.expanduser("~/.ssh/coss3_results"),
                   help="ssh-ключ для клонирования")
    p.add_argument("--pull", action="store_true",
                   help="взять свежий клон (иначе тоже берётся, это для ясности)")
    p.add_argument("--out", default="результаты.html")
    p.add_argument("--from", dest="откуда", default="", metavar="каталог",
                   help="взять готовый клон результатов вместо git clone — "
                        "полезно, когда ключа нет на этой машине или надо "
                        "пересобрать страницу по уже скачанному")
    a = p.parse_args()

    ключ = a.key if os.path.isfile(a.key) else ""
    врем = tempfile.mkdtemp(prefix="coss3-ui-")
    try:
        if a.откуда:
            корень = os.path.expanduser(a.откуда)
            if not os.path.isdir(корень):
                print(f"нет каталога {корень}")
                return 1
            print(f"беру готовый клон: {корень}")
        else:
            корень = взять_клон(a.repo, ключ, os.path.join(врем, "репо"))
            if not корень:
                return 1
        прогоны = найти_прогоны(корень)
        данные = {"прогоны": прогоны, "репо": a.repo,
                  "собрано": datetime.now().strftime("%Y-%m-%d %H:%M")}
        # </script> внутри данных закрыл бы тег раньше времени и сломал бы
        # страницу молча — единственная опасная последовательность здесь.
        сырое = json.dumps(данные, ensure_ascii=False).replace("</", "<\\/")
        текст = ШАБЛОН.replace("@@ДАННЫЕ@@", сырое).replace("@@ПОЗДНО@@", str(ПОЗДНО))
        путь = os.path.expanduser(a.out)
        with open(путь, "w", encoding="utf-8") as f:
            f.write(текст)
        идей = len({п["идея"] for п in прогоны})
        print(f"страница: {путь}")
        print(f"  прогонов {len(прогоны)}, идей {идей}, "
              f"{os.path.getsize(путь) / 1024:.0f} КБ")
        поздние = [п for п in прогоны if п["старт"] > ПОЗДНО]
        if поздние:
            print(f"  ВНИМАНИЕ: {len(поздние)} прогонов с поздним подключением — "
                  f"они помечены и в сравнении не годятся")
        if not прогоны:
            print("  ветка пуста: ни один контейнер ещё не отправил результат")
        return 0
    finally:
        import shutil
        shutil.rmtree(врем, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
