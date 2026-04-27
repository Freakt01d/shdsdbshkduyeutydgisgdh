"""
Extract every Trader_IGGID value from redservice.t_raw_detail_audit
for the date range 20-Apr-2026 to 24-Apr-2026, all 15 systems.

Hits the 15 monthly system sub-partitions directly
(t_raw_detail_audit_<s>_202604) instead of the parent, so we don't
depend on the planner choosing partition pruning correctly. Postgres
prunes the daily sub-partitions inside each monthly partition.

Output: trader_iggid_20apr_24apr_2026.xlsx (one column).
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

OUTPUT_XLSX = "trader_iggid_20apr_24apr_2026.xlsx"

# Build a UNION ALL across the 15 monthly system partitions.
# audit_date filter triggers daily partition pruning inside each.
def build_sql():
    parts = []
    for sys_name in SYSTEMS:
        table = f"redservice.t_raw_detail_audit_{sys_name}_{YYYYMM}"
        parts.append(f"""
            SELECT (regexp_matches(
                        request,
                        'Name="Trader_IGGID"\\s+Value="([^"]*)"',
                        'g'
                   ))[1] AS trader_iggid
            FROM {table}
            WHERE audit_date BETWEEN {START_DATE} AND {END_DATE}
              AND request LIKE '%Trader_IGGID%'
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
        ws = wb.create_sheet("Trader_IGGID")
        ws.append(["Trader_IGGID"])

        count = 0
        for (val,) in cur:
            if val:
                ws.append([val])
                count += 1

        cur.close()
        wb.save(OUTPUT_XLSX)
        print(f"Wrote {count} Trader_IGGID values to {OUTPUT_XLSX}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
