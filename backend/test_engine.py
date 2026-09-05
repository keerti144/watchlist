import asyncio
import time
from datetime import datetime, timezone
from main import (
    app, live_engine, evaluate_symbol,
    SessionLocal, User, WatchlistItem, UserSession, DailyClose,
    get_watchlist, add_symbol, remove_symbol, update_session, get_insights,
    SymbolRequest
)

def run_tests():
    print("==================================================")
    print("RUNNING COMPREHENSIVE LIVE YFINANCE ENGINE TESTS")
    print("==================================================")

    # 1. Initialize sample stocks
    print("\n[TEST 1] Live Engine Stock Initialization & yfinance fetch")
    sample_sym = "RELIANCE"
    live_engine.initialize_stock(sample_sym)
    assert sample_sym in live_engine.latest, "Stock should be initialized in live_engine.latest"
    assert len(live_engine.history[sample_sym]) > 0, "Stock should have historical candles"
    print(f" -> Successfully fetched live/historical candles for {sample_sym}: Price Rs. {live_engine.latest[sample_sym]['price']}")

    # 2. Database Seeding & Handlers Setup
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == "default_user").first()
        if not user:
            user = User(id="default_user", name="Default Trader")
            db.add(user)
            db.commit()

        session = db.query(UserSession).filter(UserSession.user_id == "default_user").first()
        if not session:
            session = UserSession(user_id="default_user", last_viewed_at=time.time() - 3600.0)
            db.add(session)
            db.commit()

        existing_items = db.query(WatchlistItem).filter(WatchlistItem.user_id == "default_user").all()
        if not existing_items:
            default_symbols = ["RELIANCE", "TATAMOTORS", "INFY", "HDFCBANK", "ITC", "TCS"]
            now = time.time()
            for sym in default_symbols:
                db.add(WatchlistItem(user_id="default_user", symbol=sym, added_at=now))
            db.commit()

        existing_closes = db.query(DailyClose).count()
        if existing_closes == 0:
            for sym in ["RELIANCE", "TATAMOTORS", "INFY", "HDFCBANK", "ITC", "TCS"]:
                p = live_engine.latest.get(sym, {}).get("price", 1000.0)
                db.add(DailyClose(symbol=sym, date="2026-08-01", close_price=round(p * 0.96, 2)))
            db.commit()

        print("\n[TEST 2] EWMA Price & Deviation Check")
        ewma_p = live_engine.ewma_price[sample_sym]
        ewma_v = live_engine.ewma_var[sample_sym]
        ewma_dev = live_engine.get_ewma_deviation(sample_sym, live_engine.latest[sample_sym]["price"])
        print(f" -> EWMA Price: {ewma_p:.2f}, EWMA Var: {ewma_v:.4f}, EWMA Deviation: {ewma_dev:.2f} stddev")
        assert isinstance(ewma_dev, float)

        print("\n[TEST 2B] Replay Engine Calibration & Market Hours")
        assert sample_sym in live_engine.symbol_volatility
        assert live_engine.symbol_volatility[sample_sym] > 0
        assert live_engine.is_market_open("RELIANCE.NS", now=datetime(2026, 9, 7, 4, 0, tzinfo=timezone.utc)) is True
        assert live_engine.is_market_open("AAPL", now=datetime(2026, 9, 7, 14, 0, tzinfo=timezone.utc)) is True
        replay_tick = live_engine.generate_replay_tick(sample_sym)
        assert replay_tick["seq"] > live_engine.history[sample_sym][-1]["seq"]
        assert replay_tick["price"] > 0
        assert replay_tick["volume"] > 0
        print(f" -> Volatility: {live_engine.symbol_volatility[sample_sym]:.6f}; Replay tick seq={replay_tick['seq']} price={replay_tick['price']}")

        print("\n[TEST 3] REST API: get_watchlist handler")
        res = get_watchlist(user_id="default_user", db=db, current_user=user)
        print(f" -> Initial default_user watchlist: {res['symbols']}")
        assert "RELIANCE" in res["symbols"]

        print("\n[TEST 4] REST API: add_symbol handler")
        res = add_symbol(SymbolRequest(user_id="default_user", symbol="SBIN"), db=db, current_user=user)
        assert "SBIN" in res["symbols"]
        print(f" -> Updated watchlist after adding SBIN: {res['symbols']}")

        print("\n[TEST 5] REST API: remove_symbol handler")
        res = remove_symbol(SymbolRequest(user_id="default_user", symbol="SBIN"), db=db, current_user=user)
        assert "SBIN" not in res["symbols"]
        print(f" -> Watchlist after removing SBIN: {res['symbols']}")

        print("\n[TEST 6] REST API: update_session handler")
        res = update_session(SymbolRequest(user_id="default_user"), db=db, current_user=user)
        print(f" -> Session updated last_viewed_at: {res['last_viewed_at']}")
        assert res["status"] == "ok"

        print("\n[TEST 7] REST API: get_insights handler & News Payload")
        insights = get_insights(user_id="default_user", as_of=None, sort="attention", db=db, current_user=user)
        print(f" -> Insights Summary: {insights['summary']}")
        print(f" -> Number of items: {len(insights['items'])}")
        assert len(insights["items"]) > 0
        first_item = insights["items"][0]
        print(f" -> Top Attention Item: {first_item['symbol']} (Score: {first_item['attention_score']}) | Tags: {first_item['tags']}")
        print(f" -> News items attached: {len(first_item.get('news', []))}")
        assert "attention_score" in first_item
        assert "tags" in first_item
        assert "news" in first_item
        assert first_item.get("data_mode") in ["live", "replay"]

        print("\n[TEST 8] Long Absence (> 30 days) Fallback Check")
        very_old_as_of = time.time() - (35 * 86400)
        old_data = get_insights(user_id="default_user", as_of=very_old_as_of, sort="attention", db=db, current_user=user)
        assert old_data["items"][0]["is_long_absence"] is True
        print(f" -> Verified long absence fallback trigger for as_of 35d ago: is_long_absence={old_data['items'][0]['is_long_absence']}")

    finally:
        db.close()

    print("\n==================================================")
    print("ALL LIVE ENGINE TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
