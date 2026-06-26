import sys, os
sys.path.insert(0, os.path.abspath('backend'))

from database.session import get_db
from api.enterprise import get_reorder_recommendations

def main():
    db = next(get_db())
    res = get_reorder_recommendations(db=db, current_user=None)
    positive_reorders = [item for item in res if item['recommended_reorder_qty'] > 0]
    print(f"TOTAL REORDERS NEEDED: {len(positive_reorders)}")
    for item in positive_reorders[:10]:
        print(f"SKU: {item['sku']}, Reorder Qty: {item['recommended_reorder_qty']}, Cover: {item['days_of_cover']}, Rev Exposure: {item['revenue_exposure']}")

if __name__ == '__main__':
    main()
