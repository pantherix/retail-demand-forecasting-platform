import sqlite3

def check_db(name):
    print(f"=== CHECKING {name} ===")
    conn = sqlite3.connect(name)
    cursor = conn.cursor()
    cursor.execute("SELECT sku, reorder_point, safety_stock FROM products WHERE sku='CUST001'")
    print("CUST001 PRODUCT:", cursor.fetchone())
    
    cursor.execute("SELECT COUNT(*) FROM products")
    print("TOTAL PRODUCTS:", cursor.fetchone())
    
    # Query all active reorders (tot_stock < reorder_point)
    # Let's count how many products have stock < reorder_point
    cursor.execute("""
        SELECT p.sku, p.reorder_point, SUM(i.current_stock) as tot_stock 
        FROM products p 
        LEFT JOIN inventory i ON p.id = i.product_id 
        GROUP BY p.id
    """)
    rows = cursor.fetchall()
    needs_reorder = 0
    for r in rows:
        sku, r_point, stock = r
        if stock is None: stock = 0.0
        if r_point is None: r_point = 0.0
        if stock < r_point:
            needs_reorder += 1
            if sku == 'CUST001':
                print(f"CUST001 needs reorder: stock={stock}, ROP={r_point}")
    print("TOTAL NEEDING REORDER (based on static ROP):", needs_reorder)

if __name__ == '__main__':
    check_db('retailgpt.db')
    check_db('retailgpt_test.db')
