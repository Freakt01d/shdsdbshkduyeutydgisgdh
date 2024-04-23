import pandas as pd

# Assuming 'data' is your DataFrame
data = pd.read_csv('path/to/your/data.csv')

# Create a pivot table
pivot_table = pd.pivot_table(data, 
                             values='trade_id',  # Column to aggregate
                             index='instrument_type',  # Rows (index of pivot table)
                             columns='customer_type',  # Columns of pivot table
                             aggfunc=lambda x: len(pd.unique(x[pd.notna(x)])) if 'customer' in x.name else None)

# Save the pivot table to an Excel file
with pd.ExcelWriter('output_pivot_table.xlsx') as writer:
    pivot_table.to_excel(writer, sheet_name='Pivot Table')