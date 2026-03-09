# MCSR Event Leaderboard

[English](README.md) | **Русский**

Self-Hosted таблица лидеров для ивентов по [MCSR Ranked](https://mcsrranked.com/). Отслеживает Elo игроков, статистику побед/поражений и время прохождения (ranked и casual) в рамках настраиваемого периода ивента.

## Возможности

- Таблица лидеров в реальном времени с автообновлением
- Статистика ranked и casual матчей
- Фильтрация по датам ивента (учитываются только матчи в заданный период)
- Сортировка по столбцам с логикой тайбрейков
- Admin API для управления игроками (добавление/удаление по API-ключу)
- Поддержка ручного ввода private-ранов
- Кэширование в Redis с инкрементальной загрузкой матчей
- Готов к деплою через Docker

## Быстрый старт

### Требования

- Docker и Docker Compose

### Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/MoDDyChat/mcsr-ranked-event-leaderboard.git
   cd mcsr-ranked-event-leaderboard
   ```

2. **Создайте конфигурационные файлы из примеров:**
   ```bash
   cp .env.example .env
   cp config.yaml.example config.yaml
   ```

3. **Отредактируйте `.env`** — сгенерируйте секретный API-ключ:
   ```bash
   # Сгенерировать безопасный API-ключ:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   # или: openssl rand -base64 32
   ```
   ```
   ADMIN_API_KEY=ваш-сгенерированный-ключ
   ```

4. **Отредактируйте `config.yaml`** — добавьте никнеймы игроков и даты ивента:
   ```yaml
   event_start: '2026-02-01'
   event_end: '2026-02-28'
   players:
   - MoDDyChat
   - Dushenka_
   ```

5. **Запустите приложение:**
   ```bash
   docker compose up -d
   ```

6. **Откройте** `http://localhost:7500` в браузере.

## Конфигурация

### Переменные окружения (`.env`)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379` | URL подключения к Redis |
| `REFRESH_INTERVAL_SECONDS` | `60` | Интервал обновления данных из MCSR API (сек.) |
| `ADMIN_API_KEY` | — | Секретный ключ для admin API |

### Конфиг ивента (`config.yaml`)

| Поле | Описание |
|---|---|
| `event_start` | Дата начала (UTC, `YYYY-MM-DD`) |
| `event_end` | Дата окончания (UTC, включительно) |
| `players` | Список никнеймов MCSR Ranked для отслеживания |
| `casual_runs` | (Опционально) Ручной ввод casual-прохождений (`MM:SS.mmm`) |

## Admin API

Все admin-эндпоинты требуют заголовок `X-Api-Key`.

### Добавить игрока
```bash
curl -X POST http://localhost:7500/api/admin/players \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: ваш-ключ" \
  -d '{"nickname": "PlayerName"}'
```

### Удалить игрока
```bash
curl -X DELETE http://localhost:7500/api/admin/players \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: ваш-ключ" \
  -d '{"nickname": "PlayerName"}'
```

### Список игроков
```bash
curl http://localhost:7500/api/admin/players \
  -H "X-Api-Key: ваш-ключ"
```

## Обратный прокси

Приложение слушает порт `8000` внутри контейнера (по умолчанию проброшен на `7500`). Для работы за обратным прокси (Caddy, Nginx и т.д.) направьте прокси на `localhost:7500` и при необходимости добавьте секцию `networks` в `docker-compose.yml`.

## Благодарности

Этот проект использует API [MCSR Ranked](https://mcsrranked.com/). Отдельная благодарность **RedLime**, **OliverMCSR** и остальной команде MCSR Ranked за создание и поддержку платформы.

## Лицензия

MIT
