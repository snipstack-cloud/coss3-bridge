# Cossacks 3 + мост, один контейнер = одна копия игры.
#
# Считано на СЕРВЕР x86_64 Linux с /dev/kvm... точнее, без него: здесь нет
# виртуальной машины вовсе. Игра — 32-битное Windows-приложение, на x86_64
# Linux она исполняется Wine НАПРЯМУЮ, без эмуляции процессора. Поэтому
# десять копий стоят десять процессов, а не десять Windows.
#
# Собирать ТОЛЬКО под linux/amd64: Wine здесь не эмулятор, и на ARM эта
# конструкция смысла не имеет.
#
#   docker buildx build --platform linux/amd64 \
#     --build-context game="/путь/к/Cossacks 3..." \
#     -t coss3:1 -f docker/Dockerfile .
#
# Игра запекается в образ НАРОЧНО: слои Docker общие, поэтому десять
# контейнеров из одного образа делят те же 8 ГБ, а каждый пишет только свою
# разницу. Монтировать игру томом не нужно, и патч скриптов (6 МБ) ляжет в
# тонкий верхний слой копированием-на-запись.
FROM --platform=linux/amd64 debian:bookworm-slim

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# i386 обязателен: cossacks.exe — 32-битный (проверено по заголовку PE,
# machine=0x14c). Без i386-слоя Wine не запустит его вообще.
RUN dpkg --add-architecture i386 \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates wget gnupg2 xz-utils \
 && install -d -m0755 /etc/apt/keyrings \
 && wget -qO /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key \
 && wget -qO /etc/apt/sources.list.d/winehq-bookworm.sources \
      https://dl.winehq.org/wine-builds/debian/dists/bookworm/winehq-bookworm.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends winehq-staging \
 && rm -rf /var/lib/apt/lists/*

# Экран, звук-пустышка, софтверный Vulkan и инструменты отладки.
#   xvfb        — экрана на сервере нет, а игра без окна не живёт;
#   lavapipe    — Vulkan на процессоре (пакет mesa-vulkan-drivers), нужен,
#                 когда на сервере нет видеокарты. С картой контейнер возьмёт
#                 драйвер хоста через /dev/dri, менять ничего не надо;
#   libGL/libEGL — САМ ЗАГРУЗЧИК OpenGL, а не драйверы. Ловушка debian-slim:
#                 libgl1-mesa-dri даёт драйверы, но libGL.so.1 и libEGL.so.1
#                 приходят отдельными пакетами, и без них Wine пишет
#                 "Failed to load libGL", а игра падает с page fault ДО всякой
#                 графики. cossacks.exe импортирует opengl32.dll и GLU32.dll,
#                 то есть работает с OpenGL напрямую, помимо Direct3D — поэтому
#                 падение было одинаковым и с DXVK, и с WineD3D. Версии :i386
#                 обязательны: игра 32-битная;
#   x11vnc      — подсмотреть, что на экране: первый бой всё равно заводить руками;
#   mesa-utils  — glxinfo. 12.09 именно он показал, что OpenGL исправен
#                 (llvmpipe 4.5), и снял подозрение с графики;
#   imagemagick — import, снимок экрана. На ферме из десяти копий это
#                 единственный способ понять, что видит зависшая копия: лезть
#                 в каждую VNC-клиентом никто не станет. И именно вес снимка
#                 (212 байт против 99 килобайт) отличал чёрный экран от живого;
#   xdotool     — клики по меню, когда дойдёт до автоматизации старта партии.
RUN apt-get update && apt-get install -y --no-install-recommends \
      xvfb x11vnc xdotool x11-utils \
      mesa-utils imagemagick \
      mesa-vulkan-drivers mesa-vulkan-drivers:i386 \
      libvulkan1 libvulkan1:i386 vulkan-tools \
      libgl1-mesa-dri libgl1-mesa-dri:i386 \
      libgl1 libgl1:i386 \
      libglx-mesa0 libglx-mesa0:i386 \
      libegl1 libegl1:i386 \
      libglu1-mesa libglu1-mesa:i386 \
      python3 python3-venv python3-pip \
      git openssh-client \
      cabextract p7zip-full procps net-tools tini \
 && rm -rf /var/lib/apt/lists/*

# DXVK: D3D9 -> Vulkan. Не украшение — на этой самой игре он уже поднимался
# (лог cossacks_d3d9.log из попытки под Wine: "DXVK: v1.10.3", "Game:
# cossacks.exe", устройство опознано). Штатный WineD3D (D3D9 -> OpenGL)
# остаётся запасным путём, переключается COSS3_D3D=wined3d.
ARG DXVK_VERSION=2.4.1
RUN wget -qO /tmp/dxvk.tar.gz \
      "https://github.com/doitsujin/dxvk/releases/download/v${DXVK_VERSION}/dxvk-${DXVK_VERSION}.tar.gz" \
 && tar -xzf /tmp/dxvk.tar.gz -C /opt \
 && mv "/opt/dxvk-${DXVK_VERSION}" /opt/dxvk \
 && rm /tmp/dxvk.tar.gz

# Игра. Копируем ПООБЪЕКТНО, а не целиком, и список тут выстраданный: папка
# игры за годы стала свалкой. Что НЕ берём и почему:
#   Бонусные материалы  842 МБ  обои и саундтрек;
#   __redist            100 МБ  установщик DirectX, в Wine не нужен;
#   cosaks222           1,0 ГБ  ЧУЖОЙ репозиторий hermes-agent — не игра вовсе.
#                               Скрипты игры не ссылаются на него ни разу;
#   DLC                 257 МБ  установщики GOG (.exe), а не контент. Сам
#                               контент уже лежит в data/ и dlcs/;
#   agency-agents         8 МБ  ещё один чужой репозиторий;
#   tmp, extracted       99 МБ  мусор прошлых распаковок.
# Итого 2,3 ГБ, которые уехали бы на сервер без всякой пользы. Первая редакция
# этого файла брала cosaks222 и DLC — поймано полным сканом собранного образа.
WORKDIR /opt/cossacks
COPY --from=game data          ./data
COPY --from=game dlcs          ./dlcs
COPY --from=game app           ./app
COPY --from=game commonappdata ./commonappdata
COPY --from=game scripts       ./scripts
COPY --from=game cossacks.exe config.exe modman.exe ./
COPY --from=game fmod.dll galaxy.dll ogg.dll openal32.dll vorbis.dll vorbisfile.dll ./

# Мост кладём в образ как ЗАПАСНОЙ вариант, а рабочий приезжает из git при
# старте контейнера (COSS3_BRIDGE_GIT). Почему так:
#   * мост правится каждый день, игра — никогда. Запекать мост в образ значит
#     пересобирать и перегонять 3,85 ГБ ради правки в одном .py;
#   * на сервере проверяются ИДЕИ, и каждая идея — это своя ветка или коммит
#     моста. Образ обязан уметь взять любой ref, не пересобираясь;
#   * версия моста должна быть ПРИВЯЗАНА К ТРАССЕ. Контейнер печатает точный
#     SHA и кладёт его в /io/bridge.sha — иначе через неделю не скажешь, какой
#     мост дал какой результат, и вся ферма опытов бессмысленна.
# Запасная копия нужна, чтобы образ работал и без сети, и без репозитория.
#
# Список ЯВНЫЙ, а не «*.txt», и это не педантизм: рядом лежит nim_key.txt с
# рабочим ключом OpenRouter, и глоб утащил бы его в слой образа. Из слоя ключ
# достаёт любой, у кого есть образ, и удаление файла следующим слоем НЕ
# помогает — слой остаётся в истории. Ключ приходит переменной окружения.
# Вторая страховка — .dockerignore, третья — проверка ниже.
COPY *.py *.inc /opt/bridge/
COPY hints_human.txt hints.txt lessons.txt /opt/bridge/
COPY docker/entrypoint.sh docker/firstrun.sh docker/clean_game.py /opt/bridge/
RUN chmod +x /opt/bridge/entrypoint.sh /opt/bridge/firstrun.sh

# Зависимости моста. venv, потому что Debian 12 запрещает pip в системный
# python (PEP 668), а падать на этом при сборке образа глупо.
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir openai \
 && ln -s /opt/venv/bin/python /usr/local/bin/coss3-python

# Ключи хоста github.com и обёртка ssh для deploy key. Проверка при сборке
# сверяет отпечатки с опубликованными GitHub — если GitHub их сменит (такое
# было в 2023 с RSA), сборка упадёт, и это правильно: молча взять новый ключ
# хоста значит согласиться на подмену.
COPY docker/github_known_hosts /etc/ssh/ssh_known_hosts
COPY docker/ssh_wrapper.sh /opt/bridge/ssh_wrapper.sh
RUN chmod +x /opt/bridge/ssh_wrapper.sh \
 && ssh-keygen -lf /etc/ssh/ssh_known_hosts \
 && for fp in "SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU" \
              "SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s" \
              "SHA256:p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM"; do \
      ssh-keygen -lf /etc/ssh/ssh_known_hosts | grep -qF "$fp" \
        || { echo "СТОП: отпечаток ключа github.com не совпал: $fp"; exit 1; }; \
    done \
 && echo "ключи хоста github.com сверены с опубликованными"

ENV COSS3_BRIDGE_GIT="" \
    COSS3_BRIDGE_REF=master \
    WINEPREFIX=/wine \
    WINEARCH=win32 \
    WINEDEBUG=-all \
    DISPLAY=:99 \
    COSS3_GAME=/opt/cossacks \
    COSS3_D3D=dxvk \
    COSS3_RES=800x600 \
    COSS3_VNC=0 \
    PATH=/opt/venv/bin:$PATH

# WINEARCH=win32 намеренно: игра 32-битная, 64-битный префикс ей не нужен и
# тянет вдвое больше файлов. Если понадобится 64-битный софт рядом — win64.

# Префикс Wine стараемся создать ЗДЕСЬ: холодный wineboot — это десятки секунд,
# и платить их десять раз при запуске десяти копий незачем.
#
# Но шаг НЕОБЯЗАТЕЛЬНЫЙ, и вот почему. Образ собирают на Apple Silicon через
# эмуляцию x86, а под ней Xvfb зависает: процесс жив, экран не отвечает
# (проверено, 60 секунд ожидания). На родном x86_64 хосте этого нет. Ронять
# сборку из-за сборочной машины неправильно — поэтому при неудаче оставляем
# метку, и префикс создаётся при первом старте контейнера, уже на сервере.
# Молчком это не делается: и сборка, и контейнер говорят, какой путь выбран.
RUN if /opt/bridge/firstrun.sh; then \
      echo "сборка: префикс Wine запечён в образ"; \
    else \
      echo "сборка: префикс Wine НЕ создан (обычно это эмуляция x86 на сборочной машине)."; \
      echo "        Контейнер создаст его при первом старте — на 20-30 секунд дольше."; \
      touch /opt/bridge/.prefix-deferred; \
    fi

# ОЧИСТКА ИГРЫ от старой компьютерной ветки моста — подробности в
# clean_game.py. Валит сборку, если следы остались: лучше здесь, чем на сервере
# после переноса 12 ГБ.
RUN python3 /opt/bridge/clean_game.py /opt/cossacks /opt/bridge

# Проверка на сборке: Wine видит 32-битный exe игры. Дешевле поймать здесь,
# чем на сервере после переноса 12 ГБ.
# Ключей в образе быть не должно. Проверка на сборке, потому что образ уедет
# на сервер, а то и в реестр, и там ловить поздно.
# Смотрим ВЕСЬ /opt, а не только /opt/bridge. Первая редакция проверяла лишь
# наши файлы — и пропустила бы чужой репозиторий, приехавший внутри папки игры
# (он там был, с ключеподобными строками в документации). Пропускаем только
# data/ — это 6,9 ГБ бинарных ассетов игры, где секретам взяться неоткуда, а
# скан их заметно тормозит.
RUN if grep -rlE "sk-(or|proj|ant)-[A-Za-z0-9_-]{10}" /opt \
        --exclude-dir=data 2>/dev/null | grep -q .; then \
      echo "СТОП: в образ попал файл, похожий на ключ API:"; \
      grep -rlE "sk-(or|proj|ant)-[A-Za-z0-9_-]{10}" /opt --exclude-dir=data; \
      exit 1; \
    else echo "секретов в образе не найдено (проверен весь /opt кроме data/)"; fi

RUN test -f /opt/cossacks/cossacks.exe \
 && test -f /opt/dxvk/x32/d3d9.dll \
 && wine --version \
 && echo "сборка: wine и файлы игры на месте"

VOLUME ["/io"]
EXPOSE 5900

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/bridge/entrypoint.sh"]
