# MCSR Event Leaderboard

**English** | [Русский](README.ru.md)

A self-hosted leaderboard for [MCSR Ranked](https://mcsrranked.com/) events. Tracks player Elo, win/loss records, and completion times (both ranked and casual) within a configurable event period.

## Features

- Real-time leaderboard with auto-refresh
- Tracks ranked and casual match statistics
- Event date filtering (only counts matches within the event period)
- Sortable columns with tiebreaker logic
- Admin API for managing players (add/remove via API key)
- Manual private run times support
- Redis caching with incremental match fetching
- Docker deployment ready

## Quick Start

### Prerequisites

- Docker & Docker Compose

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MoDDyChat/mcsr-ranked-event-leaderboard.git
   cd mcsr-ranked-event-leaderboard
   ```

2. **Create configuration files from examples:**
   ```bash
   cp .env.example .env
   cp config.yaml.example config.yaml
   ```

3. **Edit `.env`** — generate a secret API key:
   ```bash
   # Generate a secure API key:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   # or: openssl rand -base64 32
   ```
   ```
   ADMIN_API_KEY=your-generated-key
   ```

4. **Edit `config.yaml`** — add player nicknames and event dates:
   ```yaml
   event_start: '2026-02-01'
   event_end: '2026-02-28'
   players:
   - MoDDyChat
   - Dushenka_
   ```

5. **Start the application:**
   ```bash
   docker compose up -d
   ```

6. **Open** `http://localhost:7500` in your browser.

## Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `REFRESH_INTERVAL_SECONDS` | `60` | How often to fetch new data from MCSR API |
| `ADMIN_API_KEY` | — | Secret key for admin API endpoints |

### Event Config (`config.yaml`)

| Field | Description |
|---|---|
| `event_start` | Start date (UTC, `YYYY-MM-DD`) |
| `event_end` | End date (UTC, inclusive) |
| `players` | List of MCSR Ranked nicknames to track |
| `casual_runs` | (Optional) Manual casual run times per player (`MM:SS.mmm`) |

## Admin API

All admin endpoints require the `X-Api-Key` header.

### Add a player
```bash
curl -X POST http://localhost:7500/api/admin/players \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: your-secret-key" \
  -d '{"nickname": "PlayerName"}'
```

### Remove a player
```bash
curl -X DELETE http://localhost:7500/api/admin/players \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: your-secret-key" \
  -d '{"nickname": "PlayerName"}'
```

### List players
```bash
curl http://localhost:7500/api/admin/players \
  -H "X-Api-Key: your-secret-key"
```


## Reverse Proxy

The app listens on port `8000` inside the container (mapped to `7500` by default). To serve behind a reverse proxy (e.g., Caddy, Nginx), point the proxy to `localhost:7500` and add a `networks` section to `docker-compose.yml` if needed.

## Credits

This project uses the [MCSR Ranked](https://mcsrranked.com/) API. Special thanks to **RedLime**, **OliverMCSR**, and the rest of the MCSR Ranked Team for building and maintaining the platform.

## License

MIT
