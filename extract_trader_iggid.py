"""
Extract every Trader_IGGID and Sales_IGGID value from
redservice.t_raw_detail_audit for the date range 20-Apr-2026 to
24-Apr-2026, all 15 system partitions.

Single regex pass per row captures both id types at once
(combined alternation in the pattern).

Output: trader_sales_iggid_20apr_24apr_2026.xlsx
        Sheet 1: Trader_IGGID  (one column, one value per row)
        Sheet 2: Sales_IGGID   (one column, one value per row)
Empty Value="" matches are skipped.
"""

import psycopg2
from openpyxl import Workbook

# ----------------------------------------------------------------------
# Connection
# ----------------------------------------------------------------------
CONN = {
    "host":     "redhist-db.postgres.database.azure.com",
    "port":     5432,
    "dbname":   "redservice",
    "user":     "<user>",
    "password": "<password>",
    "sslmode":  "require",
}

# ----------------------------------------------------------------------
# Range
# ----------------------------------------------------------------------
YYYYMM     = "202604"
START_DATE = 20260420
END_DATE   = 20260424

SYSTEMS = [
    "astro", "bga", "demeter", "efts", "eliot",
    "gold", "iridium", "lma", "onyx", "pdc",
    "riskserver", "sge", "test", "xone", "xonepayment",
]

OUTPUT_XLSX = "trader_sales_iggid_20apr_24apr_2026.xlsx"

# Combined regex: capture group 1 = id type, group 2 = value.
# regexp_matches with 'g' returns one row per match (per request).
def build_sql():
    parts = []
    for sys_name in SYSTEMS:
        table = f"redservice.t_raw_detail_audit_{sys_name}_{YYYYMM}"
        parts.append(f"""
            SELECT m[1] AS id_type, m[2] AS id_value
            FROM (
                SELECT regexp_matches(
                           request,
                           'Name="(Trader_IGGID|Sales_IGGID)"\\s+Value="([^"]*)"',
                           'g'
                       ) AS m
                FROM {table}
                WHERE audit_date BETWEEN {START_DATE} AND {END_DATE}
                  AND request LIKE '%_IGGID%'
            ) x
        """)
    return "\nUNION ALL\n".join(parts)


def main():
    sql = build_sql()

    conn = psycopg2.connect(**CONN)
    try:
        cur = conn.cursor(name="iggid_cursor")
        cur.itersize = 5000
        cur.execute(sql)

        wb = Workbook(write_only=True)
        ws_trader = wb.create_sheet("Trader_IGGID")
        ws_sales  = wb.create_sheet("Sales_IGGID")
        ws_trader.append(["Trader_IGGID"])
        ws_sales.append(["Sales_IGGID"])

        n_trader = 0
        n_sales  = 0
        for id_type, id_value in cur:
            if not id_value:
                continue
            if id_type == "Trader_IGGID":
                ws_trader.append([id_value])
                n_trader += 1
            elif id_type == "Sales_IGGID":
                ws_sales.append([id_value])
                n_sales += 1

        cur.close()
        wb.save(OUTPUT_XLSX)
        print(f"Trader_IGGID: {n_trader} values")
        print(f"Sales_IGGID:  {n_sales} values")
        print(f"Saved -> {OUTPUT_XLSX}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
