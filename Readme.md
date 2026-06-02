# 🚛 Truck Cargo Management System

## ⚡ Quick Start (Every Time You Return)

### Step 1 — Open terminal in project folder
```cmd
cd D:\software\CMIT Internship\WebDevelopment\Truck_Cargo_Management_Python\truck-cargo
```

### Step 2 — Activate virtual environment
```cmd
venv\Scripts\activate
```
You should see `(venv)` at the start of your prompt.

### Step 3 — Start Docker services (PostgreSQL + Redis + RabbitMQ)
```cmd
docker compose up -d
```
Verify all 3 are running:
```cmd
docker compose ps
```

### Step 4 — Open 3 terminals in VS Code (Ctrl + `)

**Terminal 1 — API Server:**
```cmd
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Cargo Worker:**
```cmd
venv\Scripts\activate
python -m app.workers.cargo_worker
```

**Terminal 3 — DB Listener (PG → RabbitMQ bridge):**
```cmd
venv\Scripts\activate
python -m app.workers.db_listener
```

### Step 5 — Open in browser
| Service | URL |
|---|---|
| API Docs (Swagger) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| RabbitMQ UI | http://localhost:15672 (cargo / cargo) |
| Frontend | http://localhost:3000 |

---

## 🏗️ Project Structure
```
truck-cargo/
├── app/
│   ├── api/
│   │   └── routes.py          # REST endpoints (trucks, cargos)
│   ├── core/
│   │   ├── config.py          # Settings from .env
│   │   ├── events.py          # RabbitMQ publish helper
│   │   └── logging.py         # Loguru setup
│   ├── db/
│   │   └── session.py         # SQLAlchemy async engine
│   ├── models/
│   │   └── cargo.py           # Truck, Cargo, CargoEvent models
│   ├── schemas/
│   │   └── cargo.py           # Pydantic request/response schemas
│   ├── services/
│   │   └── cargo_service.py   # Business logic (reusable)
│   ├── workers/
│   │   ├── cargo_worker.py    # RabbitMQ consumer + retry + DLQ
│   │   ├── notify_worker.py   # WebSocket + push notifications
│   │   └── db_listener.py     # PostgreSQL LISTEN/NOTIFY → RabbitMQ
│   └── main.py                # FastAPI app entry point
├── alembic/                   # DB migrations
│   ├── versions/              # Migration files
│   └── env.py                 # Alembic config
├── nginx/                     # Nginx reverse proxy config
├── tests/                     # Test files
├── logs/                      # App logs (auto-created)
├── .env                       # Environment variables (never commit)
├── docker-compose.yml         # PostgreSQL + Redis + RabbitMQ
├── alembic.ini                # Alembic settings
└── requirements.txt           # Python dependencies
```

---

## 🏛️ Architecture

```
Browser
  └── Nginx (reverse proxy)
        └── FastAPI (REST + WebSocket)
              ├── PostgreSQL (data + triggers)
              │     └── LISTEN/NOTIFY → db_listener worker
              │                              └── RabbitMQ (cargo_events exchange)
              │                                    ├── cargo.jobs queue → cargo_worker
              │                                    │     └── retry (exp. backoff) → DLQ
              │                                    └── cargo.dlq (dead letter queue)
              └── Redis (cache + pub/sub)
```

---

## 🔑 Environment Variables (`.env`)
```env
DATABASE_URL=postgresql+asyncpg://cargo_user:cargo_pass@localhost/cargo_db
SYNC_DATABASE_URL=postgresql://cargo_user:cargo_pass@localhost/cargo_db
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://cargo:cargo@localhost/
SECRET_KEY=supersecretkey123
APP_NAME=TruckCargoMS
DEBUG=True
DB_PASSWORD=Bani193ch@
```

---

## 🗄️ Database

### Run migrations (first time or after model changes)
```cmd
alembic upgrade head
```

### Create a new migration after changing models
```cmd
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

### Reset database (WARNING: deletes all data)
```cmd
alembic downgrade base
alembic upgrade head
```

---

## 📦 API Endpoints

| Method | URL | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /api/v1/trucks | Add a truck |
| GET | /api/v1/trucks | List all trucks |
| POST | /api/v1/cargos | Create cargo |
| GET | /api/v1/cargos | List all cargos |
| PATCH | /api/v1/cargos/{id} | Update cargo status |
| WS | /ws/cargo | Real-time cargo updates |

### Test with curl
```cmd
curl -X POST http://localhost:8000/api/v1/trucks -H "Content-Type: application/json" -d "{\"plate\": \"ABC-123\", \"driver_name\": \"Ahmed\", \"capacity_kg\": 5000}"

curl -X POST http://localhost:8000/api/v1/cargos -H "Content-Type: application/json" -d "{\"description\": \"Electronics\", \"weight_kg\": 500}"
```

---

## 🛑 Stopping Everything
```cmd
docker compose stop
```
To fully remove containers:
```cmd
docker compose down
```

---

## 🐛 Common Errors & Fixes

| Error | Fix |
|---|---|
| `password authentication failed` | Check DB_PASSWORD in .env matches pgAdmin user |
| `connection refused :5432` | Run `docker compose up -d` |
| `connection refused :5672` | RabbitMQ not running — `docker compose up -d` |
| `Target database is not up to date` | Run `alembic stamp head` then retry |
| `ModuleNotFoundError` | Run `venv\Scripts\activate` first |
| `(venv)` not showing | Run `venv\Scripts\activate` |

---

## 📋 Build Progress

- [x] Project structure
- [x] FastAPI app with WebSocket
- [x] PostgreSQL models (Truck, Cargo, CargoEvent)
- [x] Alembic migrations + DB trigger (LISTEN/NOTIFY)
- [x] RabbitMQ event publishing
- [x] Cargo worker with retry + Dead Letter Queue
- [x] DB listener (PG → RabbitMQ bridge)
- [ ] Alembic upgrade head (in progress)
- [ ] Notion-style frontend
- [ ] Nginx config
- [ ] Full test suite

---

## 🔧 Install Dependencies (first time only)
```cmd
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn[standard] sqlalchemy asyncpg alembic aio-pika redis loguru prometheus-client httpx python-dotenv pydantic-settings psycopg2-binary boto3 websockets asyncpg
```