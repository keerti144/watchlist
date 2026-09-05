import asyncio
import base64
import hashlib
import hmac
import json
import math
import os
import random
import time
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yfinance as yf
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Float, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# ============================================================================
# 1. DATABASE SETUP (SQLite Persistence via SQLAlchemy)
# ============================================================================

DATABASE_URL = "sqlite:///./watchlist.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=True)
    created_at = Column(Float, default=time.time)

    watchlist_items = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan")
    session = relationship("UserSession", back_populates="user", uselist=False, cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), default="default_user", index=True)
    symbol = Column(String, nullable=False, index=True)
    added_at = Column(Float, default=time.time)

    user = relationship("User", back_populates="watchlist_items")


class UserSession(Base):
    __tablename__ = "user_sessions"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    last_viewed_at = Column(Float, default=time.time)

    user = relationship("User", back_populates="session")


class DailyClose(Base):
    __tablename__ = "daily_closes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False, index=True)
    date = Column(String, nullable=False)
    close_price = Column(Float, nullable=False)


Base.metadata.create_all(bind=engine)


def ensure_schema_columns():
    with engine.connect() as conn:
        existing_user_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()}
        if "password_hash" not in existing_user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN password_hash VARCHAR")
        if "created_at" not in existing_user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN created_at FLOAT")
        conn.commit()


ensure_schema_columns()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# 2. AUTHENTICATION (Lightweight JWT + PBKDF2 Password Hashing)
# ============================================================================

JWT_SECRET = os.getenv("WATCHLIST_JWT_SECRET", "dev-smart-watchlist-secret-change-me")
JWT_TTL_SECONDS = 7 * 24 * 60 * 60
auth_scheme = HTTPBearer()


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"pbkdf2_sha256${b64url_encode(salt)}${b64url_encode(digest)}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, salt_b64, digest_b64 = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = hash_password(password, b64url_decode(salt_b64)).split("$", 2)[2]
        return hmac.compare_digest(expected, digest_b64)
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + JWT_TTL_SECONDS}
    signing_input = f"{b64url_encode(json.dumps(header, separators=(',', ':')).encode())}.{b64url_encode(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{b64url_encode(signature)}"


def decode_access_token(token: str) -> str:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(b64url_encode(expected_signature), signature_b64):
            raise ValueError("Invalid token signature")
        payload = json.loads(b64url_decode(payload_b64))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("Token expired")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing token subject")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
) -> User:
    user_id = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


# ============================================================================
# 3. DEFAULT SYMBOLS & NORMALIZATION
# ============================================================================

DEFAULT_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "TATAMOTORS.NS", "ITC.NS",
    "SBIN.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "NVDA", "AAPL", "MSFT"
]

STATIC_NSE_MAP = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS", "HDFCBANK": "HDFCBANK.NS",
    "TATAMOTORS": "TATAMOTORS.NS", "ITC": "ITC.NS", "SBIN": "SBIN.NS", "ICICIBANK": "ICICIBANK.NS",
    "BHARTIARTL": "BHARTIARTL.NS", "KOTAKBANK": "KOTAKBANK.NS", "LT": "LT.NS", "MARUTI": "MARUTI.NS"
}


def normalize_symbol(symbol: str) -> str:
    """Normalizes symbol names (e.g., RELIANCE -> RELIANCE.NS if Indian stock)."""
    sym = symbol.upper().strip()
    if sym in STATIC_NSE_MAP:
        return STATIC_NSE_MAP[sym]
    if not sym.endswith(".NS") and len(sym) >= 4 and sym not in ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]:
        return f"{sym}.NS"
    return sym


# ============================================================================
# 3. LIVE & REPLAY MARKET ENGINE CLASS
# ============================================================================

class LiveMarketEngine:
    def __init__(self):
        self.latest: Dict[str, Dict[str, Any]] = {}
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self.news: Dict[str, List[Dict[str, str]]] = {}
        self.last_seq: Dict[str, int] = {}
        self.last_live_poll: Dict[str, float] = {}
        
        # Mode tracking & volatility calibration
        self.data_mode: Dict[str, str] = {}  # "live" | "replay"
        self.symbol_volatility: Dict[str, float] = {}
        
        # Adaptive EWMA price trackers
        self.ewma_price: Dict[str, float] = {}
        self.ewma_var: Dict[str, float] = {}
        self.alpha: float = 0.05

    def get_market_timezone(self, symbol: str):
        norm_sym = normalize_symbol(symbol)
        if norm_sym.endswith(".NS"):
            try:
                return ZoneInfo("Asia/Kolkata")
            except ZoneInfoNotFoundError:
                return timezone(timedelta(hours=5, minutes=30))

        try:
            return ZoneInfo("America/New_York")
        except ZoneInfoNotFoundError:
            return timezone(timedelta(hours=-5))

    def update_ewma(self, symbol: str, price: float):
        if symbol not in self.ewma_price:
            self.ewma_price[symbol] = price
            self.ewma_var[symbol] = 1.0
        else:
            delta = price - self.ewma_price[symbol]
            self.ewma_price[symbol] += self.alpha * delta
            self.ewma_var[symbol] = (1.0 - self.alpha) * (self.ewma_var[symbol] + self.alpha * (delta ** 2))

    def get_ewma_deviation(self, symbol: str, current_price: float) -> float:
        mean = self.ewma_price.get(symbol, current_price)
        var = self.ewma_var.get(symbol, 1.0)
        std_dev = math.sqrt(max(var, 1e-4))
        return (current_price - mean) / std_dev

    def is_market_open(self, symbol: str, now: Optional[datetime] = None) -> bool:
        """
        Market status detection:
        - NSE (.NS): Mon-Fri 09:15-15:30 IST (UTC+5:30)
        - US: Mon-Fri 09:30-16:00 ET (UTC-4 EDT / UTC-5 EST)
        Fail-safe: returns False on error.
        """
        try:
            now_utc = now or datetime.now(timezone.utc)
            if now_utc.tzinfo is None:
                now_utc = now_utc.replace(tzinfo=timezone.utc)
            norm_sym = normalize_symbol(symbol)
            
            if norm_sym.endswith(".NS"):
                now_ist = now_utc.astimezone(self.get_market_timezone(symbol))
                if now_ist.weekday() >= 5:  # Sat=5, Sun=6
                    return False
                open_time = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
                close_time = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
                return open_time <= now_ist <= close_time
            else:
                now_et = now_utc.astimezone(self.get_market_timezone(symbol))
                if now_et.weekday() >= 5:
                    return False
                open_time = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                close_time = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
                return open_time <= now_et <= close_time
        except Exception:
            return False

    def calibrate_volatility(self, symbol: str):
        """Computes historical volatility (stdev of log returns) across 5-day 15m candles."""
        hist = self.history.get(symbol, [])
        log_returns = []
        
        for i in range(1, len(hist)):
            p_prev = hist[i - 1]["price"]
            p_curr = hist[i]["price"]
            if p_prev > 0 and p_curr > 0:
                log_returns.append(math.log(p_curr / p_prev))
        
        if len(log_returns) >= 2:
            mean_r = sum(log_returns) / len(log_returns)
            var_r = sum((r - mean_r) ** 2 for r in log_returns) / (len(log_returns) - 1)
            vol = math.sqrt(max(var_r, 1e-6))
        else:
            vol = 0.0015  # Fallback default ~0.15% 15m return stddev
            
        self.symbol_volatility[symbol] = vol

    def fetch_60d_daily_closes(self, symbol: str, db: Session):
        """Fetches 60 days of daily close prices via yfinance and seeds DailyClose SQLite table."""
        norm_sym = normalize_symbol(symbol)
        try:
            ticker = yf.Ticker(norm_sym)
            df_daily = ticker.history(period="60d", interval="1d")
            if not df_daily.empty:
                for idx, row in df_daily.iterrows():
                    date_str = idx.strftime('%Y-%m-%d')
                    close_p = round(float(row["Close"]), 2)
                    
                    existing = db.query(DailyClose).filter(
                        DailyClose.symbol == norm_sym,
                        DailyClose.date == date_str
                    ).first()
                    
                    if not existing:
                        db.add(DailyClose(symbol=norm_sym, date=date_str, close_price=close_p))
                db.commit()
        except Exception as e:
            print(f"DailyClose fetch notice for {symbol}: {e}")

    def initialize_stock(self, symbol: str, db: Optional[Session] = None):
        """Fetches 5-day historical 15m candles, news, computes volatility, and seeds 60d daily closes."""
        norm_sym = normalize_symbol(symbol)
        try:
            ticker = yf.Ticker(norm_sym)
            df = ticker.history(period="5d", interval="15m")
            if df.empty:
                df = ticker.history(period="1mo", interval="1d")
            
            hist = []
            cum_vol = 0
            cum_val = 0.0
            seq = 0
            
            if not df.empty:
                for idx, row in df.iterrows():
                    seq += 1
                    p = float(row["Close"])
                    v = int(row["Volume"]) if row["Volume"] > 0 else 1000
                    cum_vol += v
                    cum_val += (p * v)
                    vwap = cum_val / cum_vol if cum_vol > 0 else p
                    
                    hist_tick = {
                        "symbol": symbol,
                        "price": round(p, 2),
                        "volume": v,
                        "vwap": round(vwap, 2),
                        "ts": idx.timestamp(),
                        "timestamp": idx.timestamp(),
                        "seq": seq
                    }
                    hist.append(hist_tick)
                    self.update_ewma(symbol, p)

            self.history[symbol] = hist
            self.last_seq[symbol] = seq
            
            # Calibrate volatility from 5d candles
            self.calibrate_volatility(symbol)
            
            # Mode tracking initial state
            is_open = self.is_market_open(symbol)
            self.data_mode[symbol] = "live" if is_open else "replay"

            # Fetch real news headlines
            news_items = []
            try:
                if hasattr(ticker, "news") and ticker.news:
                    for item in ticker.news[:3]:
                        content = item.get("content", {}) if isinstance(item, dict) else {}
                        title = item.get("title") or content.get("title") or ""
                        publisher = item.get("publisher") or content.get("provider", {}).get("displayName", "")
                        link = item.get("link") or content.get("canonicalUrl", {}).get("url", "")
                        
                        if title:
                            news_items.append({
                                "title": title,
                                "publisher": publisher,
                                "link": link
                            })
            except Exception as news_err:
                print(f"News fetch notice for {symbol}: {news_err}")

            self.news[symbol] = news_items

            if hist:
                latest_p = hist[-1]["price"]
                self.latest[symbol] = {
                    **hist[-1],
                    "circuit_limit": round(latest_p * 1.10, 2),
                    "upper_circuit_limit": round(latest_p * 1.10, 2),
                    "last_updated": time.time()
                }
            else:
                base_p = 1000.0
                self.latest[symbol] = {
                    "symbol": symbol, "price": base_p, "volume": 5000, "vwap": base_p,
                    "ts": time.time(), "timestamp": time.time(), "seq": 1,
                    "circuit_limit": round(base_p * 1.10, 2), "upper_circuit_limit": round(base_p * 1.10, 2),
                    "last_updated": time.time()
                }
                self.history[symbol] = [self.latest[symbol]]

            # Populate 60d daily closes into SQLite if DB session passed
            if db:
                self.fetch_60d_daily_closes(symbol, db)

        except Exception as e:
            print(f"Error initializing stock data for {symbol}: {e}")
            self.seed_fallback_stock(symbol)

    def seed_fallback_stock(self, symbol: str):
        """Creates a usable replay baseline when all upstream data fetches fail."""
        now = time.time()
        base_p = 1000.0
        self.last_seq[symbol] = max(self.last_seq.get(symbol, 0), 1)
        tick = {
            "symbol": symbol,
            "price": base_p,
            "volume": 5000,
            "vwap": base_p,
            "ts": now,
            "timestamp": now,
            "seq": self.last_seq[symbol],
            "circuit_limit": round(base_p * 1.10, 2),
            "upper_circuit_limit": round(base_p * 1.10, 2),
            "last_updated": now
        }
        self.latest[symbol] = tick
        self.history[symbol] = [tick]
        self.news[symbol] = []
        self.symbol_volatility[symbol] = self.symbol_volatility.get(symbol, 0.0015)
        self.data_mode[symbol] = "replay"
        self.update_ewma(symbol, base_p)

    def generate_replay_tick(self, symbol: str) -> Dict[str, Any]:
        """Generates a geometric random walk tick anchored to last known price."""
        last_tick = self.latest.get(symbol, {"price": 1000.0, "vwap": 1000.0, "volume": 5000})
        prev_price = last_tick["price"]
        volatility = self.symbol_volatility.get(symbol, 0.0015)
        
        # Geometric random walk: next_price = last_price * exp(N(0, vol))
        price_change_factor = math.exp(random.gauss(0, volatility))
        next_price = round(max(1.0, prev_price * price_change_factor), 2)
        
        # Simulated volume with occasional 5% anomaly spike
        recent_volumes = [h.get("volume", 0) for h in self.history.get(symbol, [])[-32:] if h.get("volume", 0) > 0]
        baseline_volume = int(sum(recent_volumes) / len(recent_volumes)) if recent_volumes else 5000
        is_spike = (random.random() < 0.05)
        if is_spike:
            vol = int(baseline_volume * random.uniform(4.0, 9.0))
        else:
            vol = max(1, int(random.gauss(baseline_volume, max(1.0, baseline_volume * 0.18))))

        vwap = round((last_tick.get("vwap", next_price) * 0.96) + (next_price * 0.04), 2)
        seq = self.last_seq.get(symbol, 0) + 1
        self.last_seq[symbol] = seq

        tick = {
            "symbol": symbol,
            "price": next_price,
            "volume": vol,
            "vwap": vwap,
            "ts": time.time(),
            "timestamp": time.time(),
            "seq": seq,
            "circuit_limit": last_tick.get("circuit_limit", round(next_price * 1.10, 2)),
            "upper_circuit_limit": last_tick.get("circuit_limit", round(next_price * 1.10, 2)),
            "last_updated": time.time()
        }
        return tick

    async def poll_live_data(self):
        """
        Centralized background worker:
        - Evaluates market status for each symbol.
        - If live: polls yfinance every 15s.
        - If replay: generates geometric random walk ticks every 2s.
        - Logs mode switches clearly.
        """
        while True:
            db = SessionLocal()
            try:
                items = db.query(WatchlistItem.symbol).distinct().all()
                symbols = [row[0] for row in items] if items else DEFAULT_SYMBOLS

                for sym in symbols:
                    if sym not in self.latest or not self.history.get(sym):
                        self.initialize_stock(sym, db)

                    market_is_open = self.is_market_open(sym)
                    new_mode = "live" if market_is_open else "replay"
                    old_mode = self.data_mode.get(sym, "replay")

                    # Log mode transition clearly
                    if old_mode != new_mode:
                        print(f"[MODE SWITCH] {sym}: {old_mode.upper()} -> {new_mode.upper()}")
                        self.data_mode[sym] = new_mode

                    if new_mode == "live":
                        loop_time = time.time()
                        if loop_time - self.last_live_poll.get(sym, 0) < 15:
                            continue
                        self.last_live_poll[sym] = loop_time

                        # Fetch genuine quote via yfinance
                        try:
                            norm_sym = normalize_symbol(sym)
                            ticker = yf.Ticker(norm_sym)
                            fast_info = getattr(ticker, "fast_info", None)
                            
                            price = self.latest[sym]["price"]
                            vol = self.latest[sym]["volume"]

                            if fast_info:
                                price = float(fast_info.last_price or price)
                                vol = int(fast_info.last_volume or vol)

                            seq = self.last_seq.get(sym, 0) + 1
                            self.last_seq[sym] = seq
                            
                            updated_tick = {
                                "symbol": sym,
                                "price": round(price, 2),
                                "volume": vol,
                                "vwap": self.latest[sym]["vwap"],
                                "ts": time.time(),
                                "timestamp": time.time(),
                                "seq": seq,
                                "circuit_limit": self.latest[sym].get("circuit_limit", round(price * 1.10, 2)),
                                "upper_circuit_limit": self.latest[sym].get("circuit_limit", round(price * 1.10, 2)),
                                "last_updated": time.time()
                            }
                            
                            self.latest[sym] = updated_tick
                            self.history[sym].append(updated_tick)
                            self.update_ewma(sym, price)
                        except Exception as fetch_err:
                            # Fallback to replay on fetch exception
                            print(f"[FETCH ERROR Fallback to REPLAY] {sym}: {fetch_err}")
                            if self.data_mode.get(sym) != "replay":
                                print(f"[MODE SWITCH] {sym}: LIVE -> REPLAY")
                            self.data_mode[sym] = "replay"
                            tick = self.generate_replay_tick(sym)
                            self.latest[sym] = tick
                            self.history[sym].append(tick)
                            self.update_ewma(sym, tick["price"])
                    else:
                        # Market closed or fail-safe -> generate replay tick
                        tick = self.generate_replay_tick(sym)
                        self.latest[sym] = tick
                        self.history[sym].append(tick)
                        self.update_ewma(sym, tick["price"])

            except Exception as ex:
                print(f"Error in poll_live_data loop: {ex}")
            finally:
                db.close()
                
            # Run 2-second sleep so replay ticks feel responsive and live
            await asyncio.sleep(2)


live_engine = LiveMarketEngine()


# ============================================================================
# 4. LIFECYCLE INITIALIZATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        # Initialize default stocks with volatility calibration & 60d DailyCloses
        for s in ["RELIANCE", "TATAMOTORS", "INFY", "HDFCBANK", "ITC", "TCS"]:
            live_engine.initialize_stock(s, db)

        # Seed default user & session in SQLite
        user = db.query(User).filter(User.id == "default_user").first()
        if not user:
            user = User(id="default_user", name="Default Trader")
            db.add(user)
            db.commit()

        sess = db.query(UserSession).filter(UserSession.user_id == "default_user").first()
        if not sess:
            sess = UserSession(user_id="default_user", last_viewed_at=time.time() - 3600.0)
            db.add(sess)
            db.commit()

        existing_items = db.query(WatchlistItem).filter(WatchlistItem.user_id == "default_user").all()
        if not existing_items:
            default_symbols = ["RELIANCE", "TATAMOTORS", "INFY", "HDFCBANK", "ITC", "TCS"]
            now = time.time()
            for s in default_symbols:
                db.add(WatchlistItem(user_id="default_user", symbol=s, added_at=now))
            db.commit()

    finally:
        db.close()

    bg_task = asyncio.create_task(live_engine.poll_live_data())
    yield
    bg_task.cancel()


app = FastAPI(
    title="Live & Replay Context-Aware Smart Watchlist API",
    description="Market-hours-independent engine with yfinance quotes, replay simulation, news feeds, and 5-factor scoring.",
    version="2.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 5. EVALUATION & 5-FACTOR SCORING ENGINE
# ============================================================================

def evaluate_symbol(symbol: str, since_ts: float, db: Session) -> Optional[Dict[str, Any]]:
    now = time.time()
    latest = live_engine.latest.get(symbol)
    hist = live_engine.history.get(symbol, [])
    news = live_engine.news.get(symbol, [])
    data_mode = live_engine.data_mode.get(symbol, "replay")

    if not latest or not hist:
        return None

    # Check long-absence (> 30 days)
    is_long_absence = (now - since_ts) > (30 * 86400)
    
    if is_long_absence:
        norm_symbol = normalize_symbol(symbol)
        db_close = db.query(DailyClose).filter(DailyClose.symbol == norm_symbol).order_by(DailyClose.date.asc()).first()
        past_price = db_close.close_price if db_close else hist[0]["price"]
        past_vwap = hist[0]["vwap"]
    else:
        past_tick = min(hist, key=lambda x: abs(x.get("ts", x.get("timestamp", 0)) - since_ts))
        past_price = past_tick["price"]
        past_vwap = past_tick.get("vwap", past_price)

    current_price = latest["price"]
    delta_pct = round(((current_price - past_price) / past_price) * 100.0, 2) if past_price > 0 else 0.0

    # Volume Ratio & Z-score
    vols = [h["volume"] for h in hist]
    mean_v = sum(vols) / len(vols) if vols else 1000.0
    var_v = sum((v - mean_v) ** 2 for v in vols) / len(vols) if len(vols) > 1 else 100.0
    std_v = math.sqrt(max(var_v, 1.0))
    vol_ratio = round(latest["volume"] / mean_v, 2) if mean_v > 0 else 1.0
    volume_zscore = round((latest["volume"] - mean_v) / std_v, 2)

    # EWMA Deviation
    ewma_dev = round(live_engine.get_ewma_deviation(symbol, current_price), 2)
    ewma_price = round(live_engine.ewma_price.get(symbol, current_price), 2)

    # Circuit limit check
    circuit_limit = latest.get("circuit_limit", round(current_price * 1.10, 2))
    dist_to_circuit = ((circuit_limit - current_price) / current_price) * 100.0 if current_price > 0 else 10.0
    is_near_circuit = (dist_to_circuit <= 0.75)

    # VWAP Cross check
    prev_above = past_price >= past_vwap
    curr_above = current_price >= latest["vwap"]
    vwap_crossed = (prev_above != curr_above)
    vwap_cross_type = "BULLISH" if (not prev_above and curr_above) else (
        "BEARISH" if (prev_above and not curr_above) else "NONE"
    )

    # Flags & Scoring
    tags = []
    score = 0.0

    if abs(delta_pct) >= 2.0:
        score += 35.0
        tags.append("HIGH_VOLATILITY")
    if vol_ratio >= 2.0 or volume_zscore >= 2.0:
        score += 25.0
        tags.append(f"UNUSUAL_VOLUME_{vol_ratio}x")
    if vwap_crossed:
        score += 20.0
        tags.append(f"{vwap_cross_type}_VWAP_CROSS" if vwap_cross_type != "NONE" else "VWAP_CROSS")
    if abs(ewma_dev) >= 2.5:
        score += 15.0
        tags.append("EWMA_DRIFT")
    if is_near_circuit:
        score += 15.0
        tags.append("CIRCUIT_ALERT")

    attention_score = round(min(100.0, max(0.0, score)), 1)
    
    # Tick Staleness (In replay mode ticks update every 2s, so is_stale remains False)
    tick_age = round(now - latest.get("last_updated", now), 1)
    is_stale = tick_age > 60.0 if data_mode == "live" else False

    return {
        "symbol": symbol,
        "current_price": current_price,
        "ref_price": past_price,
        "past_price": past_price,
        "session_delta_pct": delta_pct,
        "delta_pct": delta_pct,
        "volume": latest["volume"],
        "vol_ratio": vol_ratio,
        "volume_zscore": volume_zscore,
        "vwap": latest["vwap"],
        "vwap_crossed": vwap_crossed,
        "vwap_cross_type": vwap_cross_type,
        "ewma_price": ewma_price,
        "ewma_deviation": ewma_dev,
        "upper_circuit_limit": circuit_limit,
        "circuit_limit": circuit_limit,
        "is_near_circuit": is_near_circuit,
        "attention_score": attention_score,
        "anomaly_tags": tags,
        "tags": tags,
        "news": news,
        "data_mode": data_mode,
        "is_stale": is_stale,
        "tick_age_seconds": tick_age,
        "last_updated": latest.get("last_updated", now),
        "is_long_absence": is_long_absence
    }


# ============================================================================
# 6. REST API ENDPOINTS
# ============================================================================

class SymbolRequest(BaseModel):
    user_id: str = Field(default="default_user", example="default_user")
    symbol: Optional[str] = Field(default="", example="RELIANCE")


class AuthRequest(BaseModel):
    email: str = Field(example="trader@example.com")
    password: str = Field(min_length=6, example="secret123")
    name: Optional[str] = Field(default=None, example="Keerti")


def auth_payload(user: User) -> Dict[str, Any]:
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.id,
            "name": user.name
        }
    }


def ensure_user_session(db: Session, user_id: str):
    sess = db.query(UserSession).filter(UserSession.user_id == user_id).first()
    if not sess:
        sess = UserSession(user_id=user_id, last_viewed_at=time.time() - 3600.0)
        db.add(sess)
        db.commit()
    return sess


@app.post("/api/auth/register")
def register(req: AuthRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid email address")

    exists = db.query(User).filter(User.id == email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Account already exists")

    user = User(
        id=email,
        name=req.name.strip() if req.name and req.name.strip() else email.split("@")[0],
        password_hash=hash_password(req.password),
        created_at=time.time()
    )
    db.add(user)
    db.commit()
    ensure_user_session(db, user.id)
    return auth_payload(user)


@app.post("/api/auth/login")
def login(req: AuthRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    user = db.query(User).filter(User.id == email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    ensure_user_session(db, user.id)
    return auth_payload(user)


@app.get("/api/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.id,
        "name": current_user.name
    }


@app.get("/api/watchlist")
def get_watchlist(
    user_id: str = Query("default_user"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    user_id = current_user.id if current_user else user_id
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id).all()
    symbols = [item.symbol for item in items]
    return {
        "user_id": user_id,
        "symbols": symbols
    }


@app.post("/api/watchlist/add")
def add_symbol(
    req: SymbolRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    req.user_id = current_user.id if current_user else req.user_id
    sym = req.symbol.upper().strip()
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        user = User(id=req.user_id, name="User " + req.user_id)
        db.add(user)
        db.commit()

    exists = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == req.user_id,
        WatchlistItem.symbol == sym
    ).first()

    if not exists:
        live_engine.initialize_stock(sym, db)
        item = WatchlistItem(user_id=req.user_id, symbol=sym, added_at=time.time())
        db.add(item)
        db.commit()

    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == req.user_id).all()
    return {
        "status": "ok",
        "message": f"Added {sym} to watchlist.",
        "user_id": req.user_id,
        "symbols": [it.symbol for it in items]
    }


@app.post("/api/watchlist/remove")
def remove_symbol(
    req: SymbolRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    req.user_id = current_user.id if current_user else req.user_id
    sym = req.symbol.upper().strip()
    item = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == req.user_id,
        WatchlistItem.symbol == sym
    ).first()

    if item:
        db.delete(item)
        db.commit()

    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == req.user_id).all()
    return {
        "status": "ok",
        "message": f"Removed {sym} from watchlist.",
        "user_id": req.user_id,
        "symbols": [it.symbol for it in items]
    }


@app.post("/api/session/update")
def update_session(
    req: SymbolRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    req.user_id = current_user.id if current_user else req.user_id
    now = time.time()
    sess = db.query(UserSession).filter(UserSession.user_id == req.user_id).first()
    if not sess:
        sess = UserSession(user_id=req.user_id, last_viewed_at=now)
        db.add(sess)
    else:
        sess.last_viewed_at = now
    
    db.commit()
    return {
        "status": "ok",
        "user_id": req.user_id,
        "last_viewed_at": now
    }


@app.get("/api/watchlist/insights")
def get_insights(
    user_id: str = Query("default_user"),
    as_of: Optional[float] = Query(None),
    sort: Optional[str] = Query("attention"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    user_id = current_user.id if current_user else user_id
    sess = db.query(UserSession).filter(UserSession.user_id == user_id).first()
    since_ts = as_of if as_of else (sess.last_viewed_at if sess else time.time() - 3600.0)

    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id).all()
    symbols = [i.symbol for i in items]

    evaluated = [evaluate_symbol(s, since_ts, db) for s in symbols]
    evaluated = [e for e in evaluated if e is not None]

    # Sorting
    if sort == "attention":
        evaluated.sort(key=lambda x: x["attention_score"], reverse=True)
    elif sort == "delta":
        evaluated.sort(key=lambda x: abs(x["delta_pct"]), reverse=True)
    elif sort == "symbol":
        evaluated.sort(key=lambda x: x["symbol"])

    # Synthesize Natural Language Summary
    anomalies = [e for e in evaluated if e["attention_score"] > 0 or e["tags"]]
    mins_ago = int((time.time() - since_ts) // 60)
    time_label = f"{mins_ago}m" if mins_ago < 60 else f"{round(mins_ago / 60, 1)}h"

    if anomalies:
        top = anomalies[0]
        direction = "jumped" if top["delta_pct"] >= 0 else "dropped"
        tags_str = f" ({', '.join(top['tags'])})" if top['tags'] else ""
        mode_label = f"[{top.get('data_mode', 'live').upper()}] "
        summary = f"Since baseline ({time_label} ago): {len(anomalies)} of {len(evaluated)} stocks trigger alerts. {mode_label}**{top['symbol']}** {direction} {abs(top['delta_pct'])}%{tags_str}."
    else:
        summary = f"Since baseline ({time_label} ago): All {len(evaluated)} stocks remain within normal volatility bands."

    return {
        "user_id": user_id,
        "as_of": since_ts,
        "server_time": time.time(),
        "summary": summary,
        "items": evaluated
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
