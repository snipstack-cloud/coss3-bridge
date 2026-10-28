#!/bin/bash
# СЕРИЯ «ТОЛЬКО ОБОРОНА» ПО НАЦИЯМ ПРОТИВНИКА (28.10, задание игрока).
#
# Одна копия на нацию, одна партия, бот версии Д20 без атаки
# (idea defense_nations в experiments.ini, ветка idea/defense-nations).
# Живых контейнеров не больше MAX (правило фермы — четыре): следующая нация
# поднимается, когда одна из прежних отыграла и погасла (COSS3_KEEP_ALIVE=0).
#
# Запуск в WSL (из любого каталога):
#   nohup bash ~/coss3-git/docker/defense_nations.sh > ~/defense_nations.log 2>&1 &
# Следить:
#   tail -f ~/defense_nations.log
#   docker ps --filter name=coss3-d- --format '{{.Names}} {{.Status}}'
#   docker logs coss3-d-pol 2>&1 | grep -E 'мост обновлён|идея|флаги|пульс|партия идёт|nat1|отправлено'
# Отчёт и трасса каждой нации остаются на томе ~/io-d-<sid> и уезжают в
# coss3-results как defense_nations/<sid>.
#
# Нации — sid из country.script; net (наша) не играется против себя.
# tat и lit в _country_IsCountryAvailable не играбельны, их нет.
set -u
NATIONS="${NATIONS:-aus fra eng spa rus ukr pol swe pru ven tur alg den por pie sax bav hun swi sco}"
MAX="${MAX:-4}"
STAGGER="${STAGGER:-90}"          # пауза между подъёмами: четыре игры под Wine стартуют не разом
REF="${REF:-idea/defense-nations}"
IDEA="${IDEA:-defense_nations}"
REPO="${REPO:-$HOME/coss3-git}"

log() { echo "$(date '+%H:%M:%S') $*"; }
running() { docker ps --filter name=coss3-d- --format '{{.Names}}' | wc -l; }

log "серия $IDEA, мост $REF, нации: $NATIONS, одновременно не больше $MAX"
for nat in $NATIONS; do
    while [ "$(running)" -ge "$MAX" ]; do sleep 30; done
    name="coss3-d-$nat"
    docker rm -f "$name" >/dev/null 2>&1
    rm -rf "$HOME/io-d-$nat" "$HOME/profile-d-$nat"
    mkdir -p "$HOME/io-d-$nat" "$HOME/profile-d-$nat"
    cp -a "$HOME/profile/." "$HOME/profile-d-$nat/"
    # -e перебивает --env-file независимо от порядка (docker так устроен):
    # из ~/coss3.env берутся ключи, адреса и COSS3_MATCH_RES/PEACE/AI/NATION.
    # COSS3_MATCH_CANNONS=0 — как в Д20 (стены и пушки разрешены, игрок 1.10).
    # COSS3_KITE=0.35 — то, что ставит против_игрока.py, то есть Д20.
    if docker run -d --name "$name" --env-file "$HOME/coss3.env" --entrypoint /usr/bin/tini \
        -e COSS3_BRIDGE_GIT=git@github.com:snipstack-cloud/coss3-bridge.git \
        -e COSS3_BRIDGE_REF="$REF" \
        -e COSS3_EXPERIMENT="$IDEA" \
        -e COSS3_RESULTS_NAME="$IDEA/$nat" \
        -e COSS3_RESULTS_GIT=git@github.com:snipstack-cloud/coss3-results.git \
        -e COSS3_RESULTS_KEY=/ssh/results_key \
        -e COSS3_MATCH_NATION2="$nat" \
        -e COSS3_MATCH_CANNONS=0 \
        -e COSS3_KITE=0.35 \
        -e COSS3_KEEP_ALIVE=0 \
        -v "$HOME/io-d-$nat:/io" -v "$HOME/profile-d-$nat:/profile" \
        -v "$HOME/.ssh/coss3_deploy:/ssh/deploy_key:ro" \
        -v "$HOME/.ssh/coss3_results:/ssh/results_key:ro" \
        -v "$REPO/docker/entrypoint.sh:/opt/bridge/entrypoint.sh:ro" \
        coss3:2 -- /bin/bash /opt/bridge/entrypoint.sh >/dev/null; then
        log "поднят $name (живых: $(running))"
    else
        log "НЕ ПОДНЯЛСЯ $name"
    fi
    sleep "$STAGGER"
done

while [ "$(running)" -gt 0 ]; do sleep 60; done
log "все отыграли"
for nat in $NATIONS; do
    printf '%s: ' "$nat"
    # Контейнер без --rm: после выхода его лог ещё читается.
    docker logs "coss3-d-$nat" 2>&1 | grep -m1 "отправлено: results/" || echo "результат не уехал — смотреть docker logs coss3-d-$nat и ~/io-d-$nat"
done
