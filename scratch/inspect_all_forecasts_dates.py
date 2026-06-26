import sqlite3
from datetime import datetime

def main():
    conn = sqlite3.connect('retailgpt.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products WHERE sku='CUST001'")
    prod_id = cursor.fetchone()[0]
    cursor.execute("SELECT id, forecast_date, expected_demand FROM forecasts_new WHERE product_id=?", (prod_id,))
    rows = cursor.fetchall()
    print("TOTAL FORECAST ROWS FOR CUST001:", len(rows))
    for r in rows:
        d_str = r[1]
        try:
            # Parse SQLite format
            dt = datetime.strptime(d_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
            is_future = dt > datetime.utcnow()
            print(f"Row: {r[0]} | Date: {d_str} | Demand: {r[2]} | Parsed: {dt} | Future: {is_future}")
        except Exception as e:
            print(f"Failed to parse date string {d_str}: {e}")

if __name__ == '__main__':
    main()
