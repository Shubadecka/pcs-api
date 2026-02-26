# pcs-api

Backend API for a personal journal transcription [app](https://github.com/Shubadecka/palmer-cloud-storage-js). Users upload images of handwritten journal pages, transcribe them into individual dated entries, and manage their journal archive. Will require an OCR model running on ollama for the transcription piece eventually.

## Tech Stack

- **Framework:** FastAPI (Python 3.12+)
- **Database:** PostgreSQL 16 (async via asyncpg + SQLAlchemy)
- **Auth:** JWT tokens in httpOnly cookies
- **File storage:** Local filesystem (`./uploads`)
- **Server:** Uvicorn (ASGI)

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL instance running (or use Docker Compose)

### Local setup

```bash
# Clone and enter the project
git clone <repo-url>
cd pcs-api

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your database credentials and JWT secret

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 1442
```

The API will be available at `http://localhost:1442`.  
Interactive docs: `http://localhost:1442/docs`

### Docker Compose

```bash
docker-compose up --build
```

This starts both the API and a PostgreSQL container. Ports:
- API: `localhost:1442`
- PostgreSQL: `localhost:1456`

### Running tests

```bash
pip install -r requirements-test.txt
pytest
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_HOST` | `localhost` | PostgreSQL host |
| `DATABASE_PORT` | `1456` | PostgreSQL port |
| `DATABASE_NAME` | `journal_db` | Database name |
| `DATABASE_USER` | `postgres` | Database user |
| `DATABASE_PASSWORD` | — | Database password |
| `JWT_SECRET_KEY` | — | Secret key for signing JWT tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRY_HOURS` | `24` | Token lifetime in hours |
| `RESTRICT_EMAIL_DOMAINS` | `false` | Restrict registration to specific domains |
| `ALLOWED_EMAIL_DOMAINS` | — | Comma-separated list of allowed email domains |

## API Endpoints

All routes are prefixed with `/api`.

### Auth — `/api/auth`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Log in (sets httpOnly cookie) |
| `POST` | `/api/auth/logout` | Log out (clears cookie) |
| `GET` | `/api/auth/me` | Get current user info |

### Pages — `/api/pages`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/pages` | Upload a journal page image |
| `GET` | `/api/pages` | List all pages (optional date filter) |
| `GET` | `/api/pages/{page_id}` | Get a specific page |
| `DELETE` | `/api/pages/{page_id}` | Delete a page and its entries |

### Entries — `/api/entries`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/entries` | List all entries (date filter + pagination) |
| `GET` | `/api/entries/{entry_id}` | Get a specific entry |
| `PUT` | `/api/entries/{entry_id}` | Update an entry |
| `DELETE` | `/api/entries/{entry_id}` | Delete an entry |

### Utility

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root / status check |
| `GET` | `/health` | Health check |
| `GET` | `/uploads/{filename}` | Serve uploaded images |

## Database Schema

```sql
users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
)

pages (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    image_path TEXT NOT NULL,
    uploaded_date DATE,
    page_start_date DATE,
    page_end_date DATE,
    notes TEXT,
    page_status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
)

entries (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    page_id UUID REFERENCES pages(id),
    entry_date DATE,
    transcription TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
```

## Project Structure

```
pcs-api/
├── app/
│   ├── core/           # Config, database, dependencies, models, security
│   ├── interfaces/     # Repository and service interface definitions
│   ├── repositories/   # Database access implementations
│   ├── routes/         # FastAPI route handlers (auth, entries, pages)
│   ├── schemas/        # Pydantic request/response models
│   └── services/       # Business logic (auth, entries, pages)
├── docker/             # PostgreSQL init scripts
├── tests/              # Pytest test suite
├── main.py             # Application entry point
├── Dockerfile
├── Dockerfile.postgres
├── docker-compose.yml
├── requirements.txt
└── requirements-test.txt
```

## Authentication

Passwords are hashed with bcrypt (with SHA-256 pre-hashing and a per-user salt). Authentication uses JWT tokens stored in httpOnly, SameSite=lax cookies — the frontend never touches the token directly.
