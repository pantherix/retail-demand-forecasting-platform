import sqlite3

def main():
    conn = sqlite3.connect('retailgpt.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.sku, COUNT(f.id) 
        FROM products p 
        JOIN forecasts_new f ON p.id = f.product_id 
        WHERE f.forecast_date > '2026-06-17' 
        GROUP BY p.sku
    """)
    rows = cursor.fetchall()
    print("PRODUCTS WITH FUTURE FORECASTS:", len(rows))
    for r in rows[:10]:
        print(r)

if __name__ == '__main__':
    main()
