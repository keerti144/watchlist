# Context-Aware Smart Watchlist

A full-stack smart stock watchlist built with FastAPI, SQLite, yfinance, React, Vite, and Tailwind CSS.

The app tracks a user's personal watchlist, continuously scores symbols for attention-worthy movement, and keeps working even when markets are closed by switching into an off-hours replay simulation mode. It is designed for hackathon/demo use, but the core architecture is realistic: authenticated users, persistent watchlists, historical baselines, market-hours awareness, live quote polling, replay ticks, news, and anomaly scoring.

## What This App Does

Most watchlists only show price changes. This app tries to answer a better question:

> "Since I last checked, which stocks actually need my attention?"

For every stock in the signed-in user's watchlist, the backend calculates:

- Current price
- Baseline/reference price
- Session delta percentage
- Volume ratio
- Volume Z-score
- VWAP cross direction
- EWMA price deviation
- Distance from upper circuit limit
- Attention score
- Anomaly tags
- Live or replay data mode
- News headlines from Yahoo Finance/yfinance when available

The frontend then turns those signals into a fast scanning dashboard with sorting, badges, time-travel debugging, live polling controls, and per-user watchlists.

## Key Features

### User Authentication

- Email/password registration and login.
- JWT-style bearer tokens signed with HMAC SHA-256.
- Passwords are stored as PBKDF2-SHA256 hashes with per-user salts.
- Auth token is saved in browser `localStorage`.
- Each authenticated user has their own watchlist and session baseline.

This is intentionally lightweight. It is strong enough for a local/demo project, but not meant to replace a production identity provider.

### Personal Watchlists

- Every user gets an independent watchlist stored in SQLite.
- Users can add/remove supported stock symbols from the React UI.
- The backend no longer relies on a single global `default_user` for real app usage.

### Live + Replay Market Engine

The `LiveMarketEngine` in `backend/main.py` runs as a background worker.

It supports two data modes:

- `live`: Market is open, so the engine polls yfinance quote data.
- `replay`: Market is closed, yfinance is unavailable, or live quote fetching fails, so the engine generates realistic simulated ticks.

The mode is attached to every insight item as:

```json
{
  "data_mode": "live"
}
```

or:

```json
{
  "data_mode": "replay"
}
```

The frontend displays this as a `LIVE` or `REPLAY` badge beside each symbol.

### Market-Hours Awareness

The backend uses timezone-aware market checks:

- NSE symbols ending in `.NS`: Monday to Friday, 09:15 to 15:30 Asia/Kolkata time.
- US symbols like `AAPL`, `MSFT`, `NVDA`, `TSLA`: Monday to Friday, 09:30 to 16:00 America/New_York time.
- US daylight saving time is handled with Python `zoneinfo`.
- Any failure defaults to `False`, which safely triggers replay mode.

### Replay Tick Simulation

When markets are closed, the app still feels alive.

Replay ticks are generated every 2 seconds using a geometric random walk:

```text
P_next = P_current * exp(N(0, sigma_symbol))
```

Where `sigma_symbol` is calibrated from historical 15-minute candle log returns:

```text
r_t = ln(P_t / P_t-1)
sigma = stdev(r_t)
```

Replay volume is also simulated, including occasional 5 percent spikes to exercise unusual-volume scoring.

### Historical Pre-Seeding

On startup, the engine fetches:

- 5 days of 15-minute candles for short-term history and volatility calibration.
- 60 days of daily closes for long-absence fallback calculations.

Daily closes are persisted in the `DailyClose` SQLite table.

### Time Travel Debugger

The frontend includes a time-travel slider that changes the baseline timestamp used for scoring.

Presets include:

- 15 minutes
- 1 hour
- 4 hours
- 1 day
- 35 days, which exercises the 30+ day long-absence fallback

The slider uses anchored mapping so the visual labels line up with the actual selected baseline.

### Attention Scoring

Each stock receives an attention score from `0` to `100`.

The score considers:

- Absolute price move from baseline
- Unusual volume ratio or Z-score
- VWAP cross
- EWMA deviation
- Near-circuit alert

Generated tags can include:

- `HIGH_VOLATILITY`
- `UNUSUAL_VOLUME_...x`
- `BULLISH_VWAP_CROSS`
- `BEARISH_VWAP_CROSS`
- `EWMA_DRIFT`
- `CIRCUIT_ALERT`

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite
- yfinance
- Uvicorn

### Frontend

- React
- Vite
- Tailwind CSS
- lucide-react icons

## Project Structure

```text
groww/
  backend/
    main.py                  # FastAPI app, auth, database models, market engine, scoring
    requirements.txt         # Python dependencies
    test_engine.py           # Direct backend/engine verification
    test_http_endpoints.py   # HTTP endpoint smoke tests
    inspect_db.py            # Utility script for inspecting SQLite data
    watchlist.db             # Local SQLite database, ignored by git

  frontend/
    src/
      App.jsx
      hooks/
        useWatchlistPolling.js
      components/
        SummaryBanner.jsx
        TimeTravelBar.jsx
        WatchlistControls.jsx
        WatchlistTable.jsx
      index.css
      main.jsx
    package.json
    vite.config.js

  README.md
  .gitignore
```

## Getting Started

### Prerequisites

Install:

- Python 3.11 or newer
- Node.js 18 or newer
- npm

### 1. Clone The Repository

```bash
git clone https://github.com/keerti144/watchlist.git
cd watchlist
```

If you are already inside the local project folder, you can skip this step.

### 2. Backend Setup

From the project root:

```bash
cd backend
python -m venv ../.venv
```

Activate the virtual environment.

On Windows PowerShell:

```powershell
..\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Run the backend:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Backend API docs will be available at:

```text
http://127.0.0.1:8000/docs
```

### 3. Frontend Setup

Open another terminal from the project root:

```bash
cd frontend
npm install
npm run dev
```

Frontend app:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` requests to:

```text
http://localhost:8000
```

## How To Use

1. Start the backend server.
2. Start the frontend dev server.
3. Open `http://127.0.0.1:5173`.
4. Register a new account or log in.
5. Add stocks to your watchlist.
6. Watch the dashboard update every few seconds.
7. Use the time-travel debugger to compare against older baselines.
8. Sort by attention, delta, or symbol.
9. Check `LIVE` or `REPLAY` badges to know where the data is coming from.

## API Overview

Most app endpoints require:

```http
Authorization: Bearer <access_token>
```

### Register

```http
POST /api/auth/register
```

Body:

```json
{
  "email": "trader@example.com",
  "password": "secret123",
  "name": "Trader"
}
```

Returns:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "trader@example.com",
    "email": "trader@example.com",
    "name": "Trader"
  }
}
```

### Login

```http
POST /api/auth/login
```

Body:

```json
{
  "email": "trader@example.com",
  "password": "secret123"
}
```

### Current User

```http
GET /api/auth/me
```

### Get Watchlist

```http
GET /api/watchlist
```

### Add Symbol

```http
POST /api/watchlist/add
```

Body:

```json
{
  "symbol": "INFY"
}
```

### Remove Symbol

```http
POST /api/watchlist/remove
```

Body:

```json
{
  "symbol": "INFY"
}
```

### Update Session Baseline

```http
POST /api/session/update
```

This updates the user's `last_viewed_at` timestamp to now.

### Get Insights

```http
GET /api/watchlist/insights?sort=attention
```

Optional query parameters:

- `sort=attention`
- `sort=delta`
- `sort=symbol`
- `as_of=<unix_timestamp>`

Example response shape:

```json
{
  "user_id": "trader@example.com",
  "as_of": 1788616721.39,
  "server_time": 1788616900.12,
  "summary": "Since baseline...",
  "items": [
    {
      "symbol": "INFY",
      "current_price": 1530.5,
      "ref_price": 1500.0,
      "delta_pct": 2.03,
      "volume_zscore": 2.4,
      "attention_score": 60.0,
      "tags": ["HIGH_VOLATILITY", "UNUSUAL_VOLUME_2.2x"],
      "data_mode": "replay"
    }
  ]
}
```

## Verification

### Backend Engine Test

From `backend/`:

```bash
python test_engine.py
```

This verifies:

- Stock initialization
- Historical candle loading
- Volatility calibration
- Market-hours detection
- Replay tick generation
- EWMA calculations
- Watchlist handlers
- Insights response
- `data_mode` presence
- Long-absence fallback

### Frontend Build

From `frontend/`:

```bash
npm run build
```

This verifies that the React app compiles successfully for production.

### HTTP Endpoint Test

Start the backend first:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Then, in another terminal from `backend/`:

```bash
python test_http_endpoints.py
```

This registers a test user, authenticates with a bearer token, and exercises the main HTTP API endpoints.

## Environment Variables

### `WATCHLIST_JWT_SECRET`

Used to sign bearer tokens.

For local development, the app has a default secret. For anything beyond local demos, set your own:

```bash
WATCHLIST_JWT_SECRET="replace-this-with-a-long-random-secret"
```

On Windows PowerShell:

```powershell
$env:WATCHLIST_JWT_SECRET="replace-this-with-a-long-random-secret"
```

## Database Notes

The app uses SQLite:

```text
backend/watchlist.db
```

The database is created automatically when the backend starts.

Tables include:

- `users`
- `watchlist_items`
- `user_sessions`
- `daily_closes`

The local database file is ignored by git because it contains local user/session/watchlist data.

## Symbol Handling

The backend normalizes common Indian stock symbols.

Examples:

- `RELIANCE` becomes `RELIANCE.NS`
- `TCS` becomes `TCS.NS`
- `INFY` becomes `INFY.NS`

Recognized US symbols such as `AAPL`, `MSFT`, `NVDA`, and `TSLA` are kept as US tickers.

## Important Limitations

- yfinance is useful for demos and prototypes, but it is not a guaranteed low-latency market-data feed.
- The replay engine is a simulation, not investment advice and not a prediction engine.
- The authentication system is intentionally lightweight for this project. Production apps should use stronger secret management, HTTPS-only cookies or hardened token storage, rate limiting, password reset flows, email verification, and monitoring.
- Holiday calendars are not fully modeled. Weekends and normal market hours are handled; yfinance failures also push the system into replay mode.

## Git Hygiene

The `.gitignore` excludes generated and local-only files:

- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `dist/`
- `__pycache__/`
- `*.pyc`
- `backend/watchlist.db`
- `.vite/`

Recommended first commit:

```bash
git add .gitignore README.md backend frontend
git commit -m "Initial smart watchlist app"
git push -u origin main
```

## Future Improvements

Good next steps:

- Add refresh-token rotation or cookie-based auth.
- Add real exchange holiday calendars.
- Add more US ticker suggestions in the frontend search.
- Add charts for replay/live ticks.
- Add a portfolio grouping view.
- Add Playwright UI smoke tests.
- Add rate limiting on auth endpoints.
- Add Docker Compose for one-command local startup.

