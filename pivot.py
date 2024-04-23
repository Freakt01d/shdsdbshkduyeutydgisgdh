import pandas as pd

# Sample DataFrames
data_csv = pd.DataFrame({
    'common_key_column': [1, 2, 1, 2],
    'instrument_type': ['Bond', 'Stock', 'Bond', 'Stock'],
    'customer_type': ['customer', 'non_customer', 'customer', 'non_customer'],
    'trade_id': [101, 102, 103, 104],
    'amount': [1000, 2000, 1500, 2500]
})

data_xlsx = pd.DataFrame({
    'common_key_column': [1, 2],
    'other_info': [200, 400]
})

# Merge DataFrames
merged_data = pd.merge(data_csv, data_xlsx, on='common_key_column', how='inner')

# Create Pivot Table
pivot_table = pd.pivot_table(merged_data,
                             values=['trade_id', 'amount'],
                             index='instrument_type',
                             columns='customer_type',
                             aggfunc={'trade_id': pd.Series.nunique, 'amount': 'sum'},
                             fill_value=0)

# Adding new total columns for each instrument_type
pivot_table['Total_trades'] = pivot_table[('trade_id', 'customer')] + pivot_table[('trade_id', 'non_customer')]
pivot_table['Total_amount'] = pivot_table[('amount', 'customer')] + pivot_table[('amount', 'non_customer')]

# Add grand total row at the bottom
pivot_table.loc['Grand Total'] = pivot_table.sum()

# Optionally, rename the columns to be more descriptive if needed
pivot_table.columns = [f'{col[0]}_{col[1]}' for col in pivot_table.columns]

# Save the pivot table to an Excel file
with pd.ExcelWriter('output_pivot_table_with_totals.xlsx') as writer:
    pivot_table.to_excel(writer, sheet_name='Pivot Table with Totals')
   