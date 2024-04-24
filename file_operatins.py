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

# Calculate new table values
vm7_data = pd.DataFrame({
    'count': pivot_table['trade_id_customer'] / pivot_table['Total_trades'],
    'amount': pivot_table['amount_customer'] / pivot_table['Total_amount']
})

# Optionally, rename the index
vm7_data.index.name = 'instrument_type'

# Save the pivot table to an Excel file with formatting
with pd.ExcelWriter('output_pivot_table_with_totals.xlsx', engine='xlsxwriter') as writer:
    pivot_table.to_excel(writer, sheet_name='Pivot Table with Totals', startrow=0, startcol=0)

    # Start vm7_data right after the last column of pivot_table
    vm7_start_col = len(pivot_table.columns) + 2  # Plus 2 for a little space

    vm7_data.to_excel(writer, sheet_name='Pivot Table with Totals', startrow=0, startcol=vm7_start_col)

    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['Pivot Table with Totals']

    # Define formats
    header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1})
    number_format = workbook.add_format({'num_format': '#,##0.00'})
    total_format = workbook.add_format({'bold': True, 'bg_color': '#FFA07A', 'border': 1, 'num_format': '#,##0'})
    vm7_header_format = workbook.add_format({'bold': True, 'fg_color': '#ADD8E6', 'align': 'center'})  # Light blue for the vm7 header

    # Apply formatting to existing pivot table
    for col_num, value in enumerate(pivot_table.columns.values):
        worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(col_num, col_num, 18, number_format)

    # Format the 'Grand Total' row
    for col_num in range(len(pivot_table.columns)):
        worksheet.write(len(pivot_table), col_num, pivot_table.iloc[-1, col_num], total_format)

    # Apply vm7 header format and spacing
    worksheet.merge_range(0, vm7_start_col, 0, vm7_start_col + 1, 'vm7', vm7_header_format)

    # Apply number formatting to vm7_data
    for col_num, col_name in enumerate(vm7_data.columns):
        worksheet.set_column(vm7_start_col + col_num, vm7_start_col + col_num, 18, number_format)
        