"""
Convert the multi-sheet xlsx (with sheets exceeding Excel's row limit)
into two CSVs - one per sheet. Streams in read-only mode so memory stays flat.
"""
import csv
from openpyxl import load_workbook

INPUT_XLSX = "trader_sales_iggid_01apr_17apr_2026.xlsx"
OUTPUT_TRADER = "trader_iggid_01apr_17apr_2026.csv"
OUTPUT_SALES  = "sales_iggid_01apr_17apr_2026.csv"

wb = load_workbook(INPUT_XLSX, read_only=True)

mapping = {
    "Trader_IGGID": OUTPUT_TRADER,
    "Sales_IGGID":  OUTPUT_SALES,
}

for sheet_name, out_path in mapping.items():
    ws = wb[sheet_name]
    print(f"Converting {sheet_name} -> {out_path}", flush=True)
    n = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in ws.iter_rows(values_only=True):
            w.writerow(row)
            n += 1
            if n % 500_000 == 0:
                print(f"  {n} rows", flush=True)
    print(f"  Done: {n} rows in {out_path}", flush=True)

wb.close()
print("All done.")
