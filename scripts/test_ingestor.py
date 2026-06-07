import sys
sys.path.insert(0, 'c:/Users/statu/Downloads/my projects/retail-demand-forecasting-platform')

import pandas as pd
from io import StringIO
from src.data.ingestor import ingest, preview_mapping

# Simulate the Kaggle retail sales dataset
data = """Transaction ID,Date,Customer ID,Gender,Age,Product Category,Quantity,Price per Unit,Total Amount
1,2023-11-24,CUST001,Male,34,Beauty,3,50,150
2,2023-02-27,CUST002,Female,26,Clothing,2,500,1000
3,2023-01-13,CUST003,Male,50,Electronics,1,30,30
4,2023-05-21,CUST004,Male,37,Clothing,1,500,500
5,2023-05-06,CUST005,Male,30,Beauty,2,50,100
6,2023-04-25,CUST006,Female,45,Beauty,1,30,30
7,2023-03-13,CUST007,Male,46,Clothing,2,25,50
8,2023-02-22,CUST008,Male,30,Electronics,4,25,100"""

df = pd.read_csv(StringIO(data))
print("=== Input ===")
print(f"Columns: {list(df.columns)}")
print(f"Rows: {len(df)}")

print("\n=== Detection ===")
mapping = preview_mapping(df)
for k, v in mapping.items():
    print(f"  {k}: {v}")

print("\n=== Ingestion ===")
out, meta = ingest(df)
print(f"Format detected : {meta['format_detected']}")
print(f"Output rows     : {meta['output_rows']}")
print(f"SKUs            : {meta['skus']}")
print(f"Date range      : {meta['date_range']}")

print("\n=== Output Sample ===")
print(out[['date','product_id','category','units_sold','stock_on_hand','unit_cost']].head(10).to_string())

# Test with native format
print("\n\n=== Test: Native Format ===")
native = pd.read_csv('c:/Users/statu/Downloads/my projects/retail-demand-forecasting-platform/data/retail_sales_sample.csv')
out2, meta2 = ingest(native)
print(f"Format: {meta2['format_detected']} | Rows: {meta2['output_rows']} | SKUs: {meta2['sku_count']}")
