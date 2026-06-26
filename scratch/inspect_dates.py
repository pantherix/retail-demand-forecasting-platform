import sqlite3
from datetime import datetime

def main():
    conn = sqlite3.connect('retailgpt.db')
    cursor = conn.cursor()
    
    # Get product id
    cursor.execute("SELECT id FROM products WHERE sku='CUST001'")
    prod_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*), SUM(expected_demand) FROM forecasts_new WHERE product_id=? AND forecast_date > ?", (prod_id, '2026-06-17'))
    print("FORECASTS FOR CUST001 AFTER 2026-06-17:", cursor.fetchone())
    
    cursor.execute("SELECT COUNT(*), SUM(expected_demand) FROM forecasts_new WHERE product_id=?", (prod_id,))
    print("ALL FORECASTS FOR CUST001:", cursor.fetchone())

if __name__ == '__main__':
    main()
