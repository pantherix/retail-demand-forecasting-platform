import sqlite3

def main():
    conn = sqlite3.connect('retailgpt.db')
    cursor = conn.cursor()
    
    # 1. Product details
    cursor.execute("SELECT id, sku, name, reorder_point, safety_stock, base_price, unit_cost, supplier_id, lead_time_days FROM products WHERE sku='CUST001'")
    prod = cursor.fetchone()
    print("PRODUCT:", prod)
    if not prod:
        return
        
    prod_id = prod[0]
    
    # 2. Inventory Items
    cursor.execute("SELECT id, warehouse_id, current_stock FROM inventory WHERE product_id=?", (prod_id,))
    inv = cursor.fetchall()
    print("INVENTORY ITEMS:", inv)
    print("TOTAL STOCK SUM:", sum(x[2] for x in inv if x[2] is not None))
    
    # 3. Forecasts
    cursor.execute("SELECT COUNT(*), SUM(expected_demand) FROM forecasts_new WHERE product_id=?", (prod_id,))
    forecast = cursor.fetchone()
    print("FORECASTS:", forecast)

    # 4. Sales
    cursor.execute("SELECT COUNT(*), SUM(quantity) FROM sales WHERE product_id=?", (prod_id,))
    sales = cursor.fetchone()
    print("SALES:", sales)

if __name__ == '__main__':
    main()
