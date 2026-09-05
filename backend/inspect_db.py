import sqlite3
from datetime import datetime

def inspect_database():
    conn = sqlite3.connect('watchlist.db')
    cursor = conn.cursor()

    print("==================================================")
    print("      WATCHLIST.DB - SQLITE DATABASE INSPECTION   ")
    print("==================================================")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\nTables found: {', '.join(tables)}\n")

    print("--- 1. TABLE: users ---")
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    for u in users:
        print(f"  User ID: {u[0]} | Name: {u[1]}")

    print("\n--- 2. TABLE: user_sessions ---")
    cursor.execute("SELECT * FROM user_sessions")
    sessions = cursor.fetchall()
    for s in sessions:
        ts_str = datetime.fromtimestamp(s[1]).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  User ID: {s[0]} | Last Viewed At: {s[1]} ({ts_str})")

    print("\n--- 3. TABLE: watchlist_items ---")
    cursor.execute("SELECT * FROM watchlist_items")
    items = cursor.fetchall()
    for item in items:
        added_str = datetime.fromtimestamp(item[3]).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  ID: {item[0]} | User: {item[1]} | Symbol: {item[2]} | Added At: {added_str}")

    print("\n--- 4. TABLE: daily_closes (Sample 10 items) ---")
    cursor.execute("SELECT * FROM daily_closes LIMIT 10")
    closes = cursor.fetchall()
    for c in closes:
        print(f"  ID: {c[0]} | Symbol: {c[1]} | Date: {c[2]} | Close Price: Rs. {c[3]:.2f}")

    conn.close()

if __name__ == "__main__":
    inspect_database()
