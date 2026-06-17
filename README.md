# Chronos

**Chronos** — App usage tracker and task manager that runs on PC startup and provides real-time app/tab monitoring, task management, and productivity analytics.

## Features

- Real-time window/app tracking (5-second intervals)
- Browser tab tracking via Chrome extension
- Local SQLite database with normalized schema
- Daily/weekly analytics and productivity scoring (0-100)
- Task management with reminders
- Cross-platform notifications
- CLI companion tool
- Electron desktop dashboard with system tray
- Start on boot (Windows/macOS/Linux)

## Installation

```bash
# Install the Python package
pip install -e .

# Initialize the database
chronos setup

# Verify installation
chronos --help
```

## Quick Start

```bash
# Initialize Chronos
chronos setup

# View today's report
chronos report daily

# Weekly report
chronos report weekly

# Add a task
chronos task add "Fix login bug" --due 2025-06-20 --estimate 2h --priority high

# Complete a task
chronos task complete 1

# Set app time limit (120 min/day for Chrome)
chronos limit set chrome 120

# Start focus mode
chronos focus start --duration 90 --task "Deep work" --block slack,discord

# View streaks
chronos streaks

# Analyze interruptions
chronos interruptions --analyze

# Start the API server
chronos serve
```

## CLI Commands

```
chronos setup              Initialize Chronos database
chronos report daily       Show daily productivity report
chronos report weekly      Show weekly productivity report
chronos task add           Add a new task
chronos task complete      Mark task as complete
chronos task list          List all tasks
chronos limit set          Set daily app time limit
chronos focus start        Start a focus session
chronos streaks            View productivity streaks
chronos interruptions      View interruption patterns
chronos serve              Start API server
```

## Configuration

Configuration is stored at `~/.chronos/config.yml` and the database at `~/.chronos/chronos.db`.

Environment variables (via `.env` or system):
- `CHRONOS_ENV`: development/production
- `CHRONOS_DB_PATH`: path to SQLite database
- `CHRONOS_CONFIG_PATH`: path to config file
- `FLASK_PORT`: API server port (default: 5000)
- `FLASK_DEBUG`: enable debug mode

## Project Structure

```
chronos/
├─ src/
│  └─ chronos/
│     ├─ monitoring/     # Window tracking, native messaging
│     ├─ analytics/      # Productivity scoring, reports
│     ├─ tasks/          # Task management and reminders
│     ├─ api/            # Flask REST API
│     ├─ notifications/  # Cross-platform notifications
│     ├─ cli/            # Click CLI interface
│     └─ models/         # SQLAlchemy ORM models
├─ frontend/             # Electron + React app
├─ chrome-extension/     # Browser tab tracking
├─ tests/                # Pytest test suite
├─ scripts/              # Startup registration scripts
└─ Dockerfile            # Container support
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/dashboard/today | Today's dashboard data |
| GET | /api/dashboard/week | Weekly productivity report |
| GET | /api/tasks | List all tasks |
| POST | /api/tasks | Create new task |
| POST | /api/tasks/:id/complete | Mark task complete |
| GET | /api/goals | List productivity goals |
| POST | /api/goals | Set productivity goal |

## Docker Deployment

```bash
docker-compose up -d
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=chronos

# Verbose
pytest -v
```

## Chrome Extension

The Chrome extension for browser tab tracking is in `chrome-extension/`. To install:
1. Open Chrome and go to `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `chrome-extension/` directory

## License

MIT
