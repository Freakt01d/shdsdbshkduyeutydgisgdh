"""
Read a CSV with one value per row, write a new CSV with only unique values.
Preserves the header row.
"""
import csv

INPUT_CSV  = "trader_iggid_01apr_17apr_2026.csv"
OUTPUT_CSV = "trader_iggid_unique_01apr_17apr_2026.csv"

seen = set()
n_in = 0
n_out = 0

with open(INPUT_CSV, "r", newline="", encoding="utf-8") as fin, \
     open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fout:
    r = csv.reader(fin)
    w = csv.writer(fout)

    header = next(r, None)
    if header is not None:
        w.writerow(header)

    for row in r:
        n_in += 1
        if not row:
            continue
        val = row[0]
        if not val or val in seen:
            continue
        seen.add(val)
        w.writerow([val])
        n_out += 1
        if n_in % 500_000 == 0:
            print(f"  read {n_in}, unique so far {n_out}", flush=True)

print(f"Done: {n_in} read -> {n_out} unique -> {OUTPUT_CSV}")
