#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""СТРАТЕГИЯ ПРОТИВ ЗАПИСЕЙ ИГРОКА (18.10): одна мера поиска (`поиск_стратегии.мера`) для списка стратегий на списке
записей при нескольких видах противника — судья находок поиска. Вид «запись» — его армия из записи (профиль «живой игрок»
§32), остальные — агент (`тактик._настроить`): p3о, родной, осада_о, поток_о. Находка считается, если держится у всех.
    COSS3_WAVE_CONTRACT=1 python3 sim/против_записей.py sim/поиск/A.json [B.json ...] \
        [--записи "igrok_13_10_партияД5,igrok_16_10_партияД6,igrok_18_10_партияД7"] [--виды запись,p3о,родной,осада_о] [--зёрен 4]
"""
import json, os, statistics as St, sys
from multiprocessing import Pool
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.dirname(К))
import поиск_стратегии as ПС

def _з(з):
    п, d, seed, вид = з
    враг = None if вид == "запись" else "смесь:" + вид
    м = ПС._партия((п, d, seed, враг, вид == "запись"))
    м["вид"] = вид
    return м

def main():
    def опц(имя, умолч, тип=str):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    файлы = [a for a in sys.argv[1:] if a.endswith(".json")]
    записи = [os.path.expanduser(f"~/coss3-res-игрок-отл/{r}/1") for r in опц("--записи", "igrok_13_10_партияД5,igrok_16_10_партияД6,igrok_18_10_партияД7").split(",")]
    виды = опц("--виды", "запись,p3о,родной,осада_о").split(",")
    зёрен = опц("--зёрен", 4, int)
    стратегии = [("ярус 1 без войны", None)] + [(os.path.basename(f)[:34], json.load(open(f, encoding="utf-8"))["итог"]) for f in файлы]
    print(f"записи {len(записи)}, виды {виды}, зёрен {зёрен}; мера — поиск_стратегии.мера (тонкая: {os.environ.get('COSS3_FINE')}, крестьяне w {os.environ.get('COSS3_PEA_W')})")
    with Pool(12) as пул:
        for имя, п in стратегии:
            print(f"\n== {имя}")
            по_виду = {}
            for вид in виды:
                р = пул.map(_з, [(п, d, 100 * s + i, вид) for s in range(зёрен) for i, d in enumerate(записи)])
                по_виду[вид] = р
                print(f"  {вид:9} {ПС.свод(р)}  | наших крестьян {St.median(x['наши_крест'] for x in р):3.0f}")
            print(f"  худший вид: {min(St.mean(x['награда'] for x in р) for р in по_виду.values()):+5.2f}, средняя по видам {St.mean(St.mean(x['награда'] for x in р) for р in по_виду.values()):+5.2f}")

if __name__ == "__main__":
    main()
