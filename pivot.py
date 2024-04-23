import pandas as pd

# Assuming 'data' is your DataFrame
data = pd.read_csv('path/to/your/data.csv')

# Create a pivot table
pivot_table = pd.pivot_table(data, 
                             values=['trade_id', 'amount'],  # Columns to aggregate
                             index='instrument_type',  # Rows (index of pivot table)
                             columns='customer_type',  # Columns of pivot table
                             aggfunc={'trade_id': 'count', 'amount': 'sum'},  # Aggregation functions
                             fill_value=0)  # Fill missing values with 0

# Rename columns
pivot_table.columns = [f'{col[0]}_{col[1]}' for col in pivot_table.columns]

# Save the pivot table to an Excel file
with pd.ExcelWriter('output_pivot_table.xlsx') as writer:
    pivot_table.to_excel(writer, sheet_name='Pivot Table')
    