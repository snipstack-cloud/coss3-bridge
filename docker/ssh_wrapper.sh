#!/usr/bin/env bash
# GIT_SSH_COMMAND для контейнера: ходить в GitHub только по deploy key и только
# к известному хосту.
#
# StrictHostKeyChecking НЕ выключаем. Отключить проверку — значит согласиться
# брать код у кого угодно, кто перехватит соединение, а этот код потом правит
# файлы игры и гоняет партии. Ключи хоста github.com вшиты в образ и сверены
# при сборке с отпечатками, опубликованными GitHub.
#
# IdentitiesOnly=yes обязательно: без него ssh сначала переберёт все ключи
# агента, GitHub ответит на первый подошедший, и окажется, что контейнер ходит
# не тем ключом, каким мы думали.
exec ssh \
    -i /ssh/deploy_key \
    -o IdentitiesOnly=yes \
    -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile=/etc/ssh/ssh_known_hosts \
    -o PasswordAuthentication=no \
    -o BatchMode=yes \
    "$@"
