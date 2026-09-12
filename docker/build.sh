#!/usr/bin/env bash
# Собрать образ на маке и перенести на сервер.
#
#   ./docker/build.sh                        build_image
#   ./docker/build.sh --push reg.example/coss3:1     через реестр (быстрее)
#   ./docker/build.sh --ship user@server             прямо по ssh, без реестра
#
# Собирать можно на Apple Silicon: сборка — это распаковка пакетов и
# копирование файлов, эмуляция x86 её переживает (медленно, но один раз).
# ЗАПУСТИТЬ собранный образ на маке нельзя и не нужно: цель — сервер.
set -euo pipefail

# ВНИМАНИЕ: имена переменных здесь только латиницей. bash не допускает
# многобайтовые символы в именах (в отличие от Python, где проект их
# использует), и «ИГРА=...» он молча принимает за команду — падает в рантайме,
# а `bash -n` этого не ловит. Проверено на себе 12.09.

GAME_SRC="${COSS3_GAME_SRC:-/Users/gs/Downloads/Cossacks 3. Digital Deluxe Edition v2.2.3.92.6008 (23969) [GOG]}"
TAG="${COSS3_TAG:-coss3:1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

[ -f "$GAME_SRC/cossacks.exe" ] || { echo "не вижу cossacks.exe в: $GAME_SRC"; exit 1; }

# Поставка должна быть GOG, а не Steam. Причина не во вкусах: стимовская копия
# завязана на клиент Steam, а в контейнере его нет и не будет. GOG-версия
# (Digital Deluxe) свободна от DRM — именно поэтому вся затея с образом и
# возможна. Признак: есть galaxy.dll, нет steam_api.dll.
if ls "$GAME_SRC"/steam_api*.dll >/dev/null 2>&1; then
    echo "СТОП: это копия из Steam (найден steam_api.dll)."
    echo "  В контейнере она не заработает: ей нужен клиент Steam."
    echo "  Нужна поставка GOG (Digital Deluxe), она без DRM."
    echo "  Путь задаётся переменной COSS3_GAME_SRC."
    exit 1
fi
if [ ! -f "$GAME_SRC/galaxy.dll" ]; then
    echo "ВНИМАНИЕ: нет galaxy.dll — не похоже на поставку GOG."
    echo "  Собираю дальше, но если игра в контейнере не стартует — смотреть сюда первым."
fi

build_image() {
    echo "собираю $TAG под linux/amd64 из «${GAME_SRC}»"
    docker buildx build --platform linux/amd64 \
        --build-context "game=$GAME_SRC" \
        -t "$TAG" -f "$ROOT/docker/Dockerfile" "$@" "$ROOT"
}

case "${1:-}" in
  --push)
    [ -n "${2:-}" ] || { echo "--push требует адрес: reg.example/coss3:1"; exit 1; }
    TAG="$2"; build_image --push ;;
  --ship)
    [ -n "${2:-}" ] || { echo "--ship требует user@server"; exit 1; }
    build_image --load
    echo "переношу образ на $2 (сжатие zstd, ~12 ГБ до сжатия)"
    # docker save отдаёт tar; жмём на лету, чтобы не класть 12 ГБ на диск мака,
    # где свободно всего 59 ГБ.
    docker save "$TAG" | zstd -T0 -3 | ssh "$2" 'zstd -d | docker load'
    echo "готово. На сервере: docker compose up -d" ;;
  "") build_image --load ;;
  *) echo "не знаю ключ «$1»; есть --push и --ship"; exit 1 ;;
esac
