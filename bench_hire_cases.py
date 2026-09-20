# -*- coding: utf-8 -*-
"""Собирает НАСТОЯЩИЕ запросы события «кого нанимать» из состояний отыгранных партий.

Событий в трассах ещё нет — правка от 20.09 вечера. Поэтому запрос строится тем
же кодом, каким его строит мост (`запрос_найма`), но на снимках состояния из
настоящих партий. Берутся разные моменты: с углём и без, со стрелками и без,
ранние и поздние — чтобы задача не выродилась в один и тот же ответ.
"""
import json, glob, sys
sys.path.insert(0, '/Users/gs/coss3-bridge')
import llm_policy as L

состояния = []
for f in sorted(glob.glob('res4/2026-09-20/*/*/coss3_bot.jsonl')):
    for l in open(f):
        l = l.strip()
        if not l:
            continue
        x = json.loads(l)
        st = x.get('state')
        if not st or 'finish' in x:
            continue
        состояния.append((f, x.get('gt'), st))

print('состояний всего:', len(состояния))

# Отбираем разнообразные: казарма есть, и разные по углю/стрелкам/времени
отобраны, видели = [], set()
for f, gt, st in состояния:
    if not L._чис(st.get('ba17')):
        continue
    уголь = L._чис(st.get('coal'))
    стрелков = L._чис(st.get('mil_shooters'))
    шахта = L._чис(st.get('mines_coal'))
    ключ = (уголь > 500, стрелков > 20, шахта > 0, L._чис(st.get('gametime')) > 600)
    if ключ in видели:
        continue
    видели.add(ключ)
    отобраны.append({'файл': f, 'gt': gt, 'st': st})

print('отобрано разных обстановок:', len(отобраны))
задачи = []
for о in отобраны:
    st = о['st']
    for роль in ('ba17', 'stables'):
        if not L._чис(st.get(роль)):
            continue
        текст = L.запрос_найма(st, {}, роль, 1)
        задачи.append({'роль': роль, 'gt': о['gt'], 'запрос': текст,
                       'кандидаты': list(L.КОГО_КУЕТ[роль]),
                       'еда': L._чис(st.get('food')), 'уголь': L._чис(st.get('coal')),
                       'шахта_угля': L._чис(st.get('mines_coal')),
                       'стрелков': L._чис(st.get('mil_shooters'))})
json.dump(задачи, open('задачи_найма.json', 'w'), ensure_ascii=False, indent=1)
print('задач собрано:', len(задачи))
if задачи:
    print('длина запроса: медиана', sorted(len(з['запрос']) for з in задачи)[len(задачи)//2], 'символов')
    print('\n--- пример ---')
    print(задачи[0]['запрос'][:900])
