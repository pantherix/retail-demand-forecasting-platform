import sys, os
sys.path.insert(0, os.path.abspath('backend'))

from database.session import get_db
from api.enterprise import get_reorder_recommendations

def main():
    db = next(get_db())
    res = get_reorder_recommendations(db=db, current_user=None)
    for item in res:
        doc = item.get('days_of_cover')
        if doc is not None and doc != 999.0:
            print(f"SKU: {item['sku']}, Name: {item['product_name']}, Cover: {doc}, Reorder Qty: {item['recommended_reorder_qty']}, Rev Exposure: {item['revenue_exposure']}")

if __name__ == '__main__':
    main()
