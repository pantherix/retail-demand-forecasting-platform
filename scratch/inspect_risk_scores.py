import sqlite3

def main():
    conn = sqlite3.connect('retailgpt.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, p.sku, r.revenue_at_risk, r.recommended_action, r.expected_stockout_days, r.reorder_quantity
        FROM risk_scores r
        JOIN products p ON r.product_id = p.id
        WHERE p.sku = 'CUST001'
    """)
    print("RISK SCORE FOR CUST001:")
    print(cursor.fetchone())

if __name__ == '__main__':
    main()
