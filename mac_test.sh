#!/usr/bin/env bash
# Тест контейнера Cossacks 3 на Mac. Только macOS, только Colima x86_64.
#   bash mac_test.sh <эпизодов> <копий>
#   bash mac_test.sh --check          только проверка готовности, без запуска
set -u

CTX=colima-x86
VM=x86
IMAGE=coss3:2
PROFILE_SRC="$HOME/profile-mac"
ENV_FILE="$HOME/coss3.env"
# Память и ядра VM. 10 ГБ - число из первого запуска, а не замер: одна копия
# игры под Wine берёт обычно 2-3 ГБ. 18.09 хост с 24 ГБ стоял на нуле из-за
# браузеров, и macOS снимала сторожей прогона, пока VM держала свои десять.
# Реальное потребление контейнера теперь пишется в лог каждые две минуты -
# по нему и выбирать. Менять так: COSS3_VM_MEMORY=8 bash mac_test.sh 1 1
VM_MEMORY="${COSS3_VM_MEMORY:-10}"
VM_CPU="${COSS3_VM_CPU:-6}"
DEPLOY_KEY="${COSS3_DEPLOY_KEY:-$HOME/.ssh/coss3_deploy}"
RUNLOG="$HOME/io-mac-runner.log"

say() { printf '[мак-тест %s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$RUNLOG"; }
die() { printf '[мак-тест] СТОП: %s\n' "$*" | tee -a "$RUNLOG"; exit 1; }

[ "$(uname)" = "Darwin" ] || die "это не macOS. На Windows действует скилл coss3-farm, команды отсюда там не годятся."

CHECK_ONLY=0
case "${1:-}" in
  --check) CHECK_ONLY=1 ;;
  ''|*[!0-9]*) die "как запускать: bash mac_test.sh <эпизодов> <копий>   (или --check)" ;;
esac
if [ "$CHECK_ONLY" = 0 ]; then
  EPISODES=${1}
  COPIES=${2:-}
  case "$COPIES" in ''|*[!0-9]*) die "второй довод — число копий: bash mac_test.sh <эпизодов> <копий>" ;; esac
  [ "$EPISODES" -ge 1 ] || die "эпизодов должно быть хотя бы 1"
  [ "$COPIES" -ge 1 ] || die "копий должно быть хотя бы 1"
fi

: > "$RUNLOG"
say "проверяю готовность машины"

command -v colima >/dev/null || die "нет colima. Поставить: brew install colima qemu lima-additional-guestagents"
command -v docker >/dev/null || die "нет docker"
[ -f "$ENV_FILE" ] || die "нет $ENV_FILE с ключом модели (OPENROUTER_API_KEY)"
[ -d "$PROFILE_SRC/profiles" ] && [ -n "$(ls -A "$PROFILE_SRC/profiles" 2>/dev/null)" ] \
  || die "нет эталонного профиля игры в $PROFILE_SRC.
     Без него игра встанет на выборе профиля. Восстановить:
       1) поднять контейнер без тома /profile, дождаться окна configuration utility;
       2) DISPLAY=:99 xdotool mousemove 585 549 click 1
       3) docker --context $CTX cp <имя>:/wine/drive_c/users/root/Documents/cossacks/. $PROFILE_SRC/"

VM_YAML="$HOME/.colima/$VM/colima.yaml"
if [ -f "$VM_YAML" ] && ! colima status "$VM" >/dev/null 2>&1; then
  # Профиль есть и остановлен: colima start флаги памяти не читает, только yaml.
  HAD_MEM=$(awk '/^memory:/{print $2}' "$VM_YAML"); HAD_CPU=$(awk '/^cpu:/{print $2}' "$VM_YAML")
  if [ "$HAD_MEM" != "$VM_MEMORY" ] || [ "$HAD_CPU" != "$VM_CPU" ]; then
    sed -i '' -e "s/^memory: .*/memory: $VM_MEMORY/" -e "s/^cpu: .*/cpu: $VM_CPU/" "$VM_YAML"
    say "VM перенастроена: память $HAD_MEM -> $VM_MEMORY ГБ, ядер $HAD_CPU -> $VM_CPU (в $VM_YAML)"
  fi
fi
if ! colima status "$VM" >/dev/null 2>&1; then
  say "VM $VM не поднята — поднимаю (ядро x86_64 под QEMU, это несколько минут)"
  colima start --profile "$VM" --arch x86_64 --vm-type qemu --cpu "$VM_CPU" --memory "$VM_MEMORY" --disk 80 >>"$RUNLOG" 2>&1 \
    || die "colima не поднялась, смотри $RUNLOG"
fi
docker --context "$CTX" info >/dev/null 2>&1 || die "докер в VM не отвечает (контекст $CTX)"
say "VM на месте: $(docker --context "$CTX" version --format '{{.Server.Os}}/{{.Server.Arch}}')"

if ! docker --context "$CTX" image inspect "$IMAGE" >/dev/null 2>&1; then
  say "образа $IMAGE в VM нет — перегоняю из Docker Desktop (~6 минут)"
  docker --context desktop-linux image inspect "$IMAGE" >/dev/null 2>&1 \
    || die "образа $IMAGE нет и в Docker Desktop. Собрать по docker/Dockerfile моста."
  docker --context desktop-linux save "$IMAGE" | docker --context "$CTX" load >>"$RUNLOG" 2>&1 \
    || die "перегон образа не удался, смотри $RUNLOG"
fi
say "образ на месте: $IMAGE"

CPUS=$(docker --context "$CTX" info --format '{{.NCPU}}' 2>/dev/null)
say "ядер в VM: $CPUS (одна копия занимает ~3,7 ядра)"

if [ "$CHECK_ONLY" = 1 ]; then
  say "готовность подтверждена, ничего не запускал"
  exit 0
fi

if [ "$COPIES" -gt 2 ]; then
  say "ВНИМАНИЕ: копий $COPIES при $CPUS ядрах. Темп просядет ниже 1,00, партии растянутся."
fi

say "запускаю: копий $COPIES, эпизодов в каждой $EPISODES"
docker --context "$CTX" rm -f $(docker --context "$CTX" ps -aq --filter name=coss3-mac) >/dev/null 2>&1

n=1
while [ "$n" -le "$COPIES" ]; do
  io="$HOME/io-mac-$n"; prof="$HOME/profile-mac-$n"
  rm -rf "$io" "$prof"; mkdir -p "$io" "$prof"
  cp -a "$PROFILE_SRC"/. "$prof"/
  vnc=$((5899 + n))
  EXTRA=()
  [ -n "${COSS3_EXTRA_FLAGS:-}" ] && EXTRA=(-e "COSS3_EXTRA_FLAGS=$COSS3_EXTRA_FLAGS")
  # Мост из git — документированный путь (docker/README.md). Без него контейнер
  # берёт мост, запечённый в образ: для проверки машины годится, для опыта нет.
  # Приватный репозиторий открывается deploy key, и ключ ТОЛЬКО монтируется —
  # в образ он не попадает, иначе слой с ключом остался бы в истории навсегда.
  if [ -n "${COSS3_BRIDGE_GIT:-}" ]; then
    EXTRA+=(-e "COSS3_BRIDGE_GIT=$COSS3_BRIDGE_GIT")
    EXTRA+=(-e "COSS3_BRIDGE_REF=${COSS3_BRIDGE_REF:-verified}")
    case "$COSS3_BRIDGE_GIT" in
      git@*|ssh://*)
        [ -f "$DEPLOY_KEY" ] || die "мост просят из git по ssh ($COSS3_BRIDGE_GIT),
     а ключа нет: $DEPLOY_KEY. Указать свой — COSS3_DEPLOY_KEY=/путь/к/ключу."
        EXTRA+=(-v "$DEPLOY_KEY:/ssh/deploy_key:ro") ;;
    esac
    [ "$n" = 1 ] && say "мост из git: $COSS3_BRIDGE_GIT @ ${COSS3_BRIDGE_REF:-verified}"
  fi
  # Правка моста в python проверяется ЗДЕСЬ: подкладываем местный файл поверх
  # запечённого в образ. Для .inc это не годится — те живут в игре и
  # проверяются на Windows.
  if [ "${COSS3_BRIDGE_LOCAL:-0}" = 1 ]; then
    # ВСЕ местные .py, а не список руками. 16.09 список отстал: правка уехала
    # в coss3_map.py, контейнер взял его из образа, и партия оборвалась на
    # AttributeError через четыре минуты. Список, который надо помнить, —
    # это список, который однажды забудут.
    for f in $(cd "$HOME/coss3-bridge" && ls *.py 2>/dev/null) \
             block_hstate.inc block_hcmd.inc block_gameloop.inc \
             block_endgame.inc block_human.inc; do
      [ -f "$HOME/coss3-bridge/$f" ] && EXTRA+=(-v "$HOME/coss3-bridge/$f:/opt/bridge/$f:ro")
    done
    [ "$n" = 1 ] && say "мост python берётся МЕСТНЫЙ из ~/coss3-bridge (COSS3_BRIDGE_LOCAL=1)"
  fi
  docker --context "$CTX" run -d --name "coss3-mac-$n" \
    --env-file "$ENV_FILE" ${EXTRA[@]+"${EXTRA[@]}"} \
    -e COSS3_VNC=1 -e COSS3_KEEP_ALIVE=1 \
    -e COSS3_EPISODES="$EPISODES" \
    -e COSS3_HB_TIMEOUT=900 -e COSS3_NEW_TIMEOUT=600 \
    -p "$vnc":5900 \
    -v "$io":/io -v "$prof":/profile \
    "$IMAGE" >/dev/null || die "копия $n не поднялась"
  say "копия $n поднята: том $io, VNC на localhost:$vnc"
  n=$((n+1))
done

LIMIT=$(( EPISODES * 40 + 25 ))     # минут, с запасом на загрузку игры
say "жду до $LIMIT минут; проверяю каждые 2 минуты"
say "память контейнеров пишу каждые 2 минуты: столбец «память» - сколько реально занято"

min=0
while [ "$min" -lt "$LIMIT" ]; do
  sleep 120; min=$((min+2))
  done_count=0
  n=1
  while [ "$n" -le "$COPIES" ]; do
    name="coss3-mac-$n"
    if docker --context "$CTX" logs "$name" 2>&1 | grep -q "пишу документ прогона"; then
      done_count=$((done_count+1))
      n=$((n+1)); continue
    fi
    gt=$(docker --context "$CTX" exec "$name" sh -c \
         "grep -o 'gametime = [0-9]*' /opt/cossacks/coss3_hb.dat 2>/dev/null | head -1" 2>/dev/null)
    last=$(docker --context "$CTX" logs "$name" 2>&1 | grep -E "^[0-9]+:[0-9]+" | tail -1 | cut -c1-90)
    mem=$(docker --context "$CTX" stats --no-stream --format '{{.MemUsage}}' "coss3-mac-$n" 2>/dev/null | cut -d/ -f1 | tr -d ' ')
    say "  копия $n: ${gt:-пульса ещё нет} | память ${mem:-?} | ${last:-модель ещё не ходила}"
    n=$((n+1))
  done
  [ "$done_count" -ge "$COPIES" ] && { say "все копии отыграли"; break; }
done

say "==== ИТОГ ===="
n=1
while [ "$n" -le "$COPIES" ]; do
  rep="$HOME/io-mac-$n/отчёт.md"
  if [ -f "$rep" ]; then
    say "копия $n: $rep"
    grep -E "^\| [0-9]|Цель|версия моста" "$rep" | sed 's/^/    /' | tee -a "$RUNLOG"
  else
    say "копия $n: отчёта НЕТ — смотреть: docker --context $CTX logs coss3-mac-$n | tail -40"
  fi
  n=$((n+1))
done
say "контейнеры оставлены живыми. Погасить:"
say "  docker --context $CTX rm -f \$(docker --context $CTX ps -aq --filter name=coss3-mac)"
