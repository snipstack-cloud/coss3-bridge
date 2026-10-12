import os, sys, json, statistics as St
from collections import Counter
from multiprocessing import Pool
К = os.path.expanduser("~/coss3-bridge")
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
R_ = "/Users/gs/coss3-results/2026-10-11/igrok_11_10_партияД4/1"
ВЕХИ = {229: (330, 400, 480), 276: (330, 400, 480), 316: (360, 400, 480)}

def прогон(з):
    t, вид, кто, seed = з
    import numpy as np
    import развилка as R, кейсы as КС, sim as SIM
    th = np.array(json.load(open(os.path.join(К, "nets", "tactic_v3_dagger.json"), encoding="utf-8"))["theta"])
    сим, _ = R.построить(R_, float(t), вид, seed)
    к, ядро = КС._контроллер(кто, КС._хоз(), seed, сим.t, th)
    вехи, решения, приказы = {}, [], []
    while сим.t < 480 and not сим.исход:
        st = сим.состояние()
        if кто == "учитель":
            os.environ["COSS3_WAVE_CONTRACT"] = "1"
        кк = к(st) or []
        for c in кк:
            if c.get("cmd") in ("ATTACK", "MOVE", "RETREAT", "ENGAGE", "STAGE") and len(приказы) < 6:
                приказы.append((int(сим.t), c.get("cmd"), c.get("count"), c.get("cx", c.get("aim"))))
        сим.команды(кк)
        сим.такт()
        for в in ВЕХИ[t]:
            if в not in вехи and сим.t >= в:
                вехи[в] = (сим.my_mil_lost, сим.убито_бойцов)
    if ядро is not None:
        решения = [(int(d["t"]), d["решение"]) for d in ядро.диагностика if d["решение"] != "ничего"][:6]
    SIM.ФОРМА_ВРАГА = None
    return dict(t=t, вид=вид, кто=кто, seed=seed, вехи=вехи, наши=сим.my_mil_lost, его=сим.убито_бойцов, решения=решения, приказы=приказы)

if __name__ == "__main__":
    os.chdir(К)
    зад = [(t, вид, кто, 100 + s) for t in (229, 276, 316) for вид in ("p3", "p3о", "p2") for кто in ("клон", "учитель") for s in range(4)]
    with Pool(12) as пул:
        р = пул.map(прогон, зад)
    for t in (229, 276, 316):
        print(f"\n##### развилка {t//60}:{t%60:02d}")
        for кто in ("клон", "учитель"):
            for вид in ("p3", "p3о", "p2"):
                рр = [x for x in р if x["t"] == t and x["кто"] == кто and x["вид"] == вид]
                стр = " | ".join(f"{в//60}:{в%60:02d} {St.median(x['вехи'].get(в, (0,0))[0] for x in рр):3.0f}/{St.median(x['вехи'].get(в, (0,0))[1] for x in рр):3.0f}" for в in ВЕХИ[t])
                print(f"  {кто:8} {вид:4} {стр} | конец {St.median(x['наши'] for x in рр):3.0f}/{St.median(x['его'] for x in рр):3.0f}")
            for x in [x for x in р if x["t"] == t and x["кто"] == кто][:3]:
                print(f"     {x['вид']} seed {x['seed']}: решения {x['решения']}  приказы {x['приказы']}")
